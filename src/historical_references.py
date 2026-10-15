"""Bounded, independently fitted external-method adaptations, never promotions."""
import argparse
import datetime as dt
import json
from pathlib import Path
import time
from importlib.resources import files

import numpy as np
import pandas as pd
from scipy.stats import poisson
from sklearn.linear_model import PoissonRegressor
from sklearn.preprocessing import KBinsDiscretizer, MinMaxScaler, OneHotEncoder
from threadpoolctl import threadpool_limits

from benchmark_evaluation import fixed_squad_report, paired_block_errors
from benchmark_metrics import point_scores
from experiment_runner import file_hash
from forecast import legal_squad
from native_history import NativeHistory
from native_reference import load_inputs
from conditional_reference import environment

KEYS = ["season", "gameweek", "fixture", "fpl_code"]
METHODS = ["reference", "native_reference", "conditional_reference",
           "openfpl_cv1_refit", "conjugate_poisson"]
POLICY = dict(schema_version=1, method="historical-external-adaptations-v2",
              train="through2025-26GW19", validation=[20, 27], test=[28, 38],
              target="actual2025-26fullpoints", seed=42, threads=2,
              openfpl="40 cv1 published members, chronological refits, median10/position",
              openfpl_bins=[2, 3, 4, 3], availability_unknown=-1.,
              openfpl_transform="training-only MinMax, numeric NaN0 inside model",
              age_weighting=False, refit_validation=False, search=False,
              component=dict(team_alpha=1., team_half_life_days=365.25,
                             prior_goals=35., epsilon_per_year=.2,
                             recent_minutes=3, residual_prior_minutes=900.,
                             cold_start_minutes=[45.,42.,38.,35.],
                             goalkeeper_goal_points={"through2023-24":6,"since2024-25":10}),
              panels=20, panel_seed=20261015, panel_budget=1000,
              benchmark_eligible=False, original_system=False, promotion=False)


def recipe():
    return json.loads(files("fpl_predict_resources").joinpath("openfpl_cv1_recipe.json").read_text())


def feature_name(name):
    if name == "status player availability":
        return "sig_chance_playing"
    return name.replace("opponent ", "opp ", 1).replace(" ", "_")


def openfpl_matrix(x, names):
    columns = [feature_name(n) for n in names]
    if len(set(columns)) != len(columns) or set(columns)-set(x):
        raise ValueError("Unsupported OpenFPL feature mapping")
    result = x[columns].copy()
    if "sig_chance_playing" in result:
        chance = result.sig_chance_playing
        if not chance.isin([-1, 0, 25, 50, 75, 100]).all():
            raise ValueError("Unsupported availability encoding")
        result["sig_chance_playing"] = chance.where(chance.eq(-1), chance/100)
    values = result.to_numpy(dtype=np.float32)
    if np.isinf(values).any():
        raise ValueError("Infinite model inputs")
    return np.nan_to_num(values, nan=0.)


def balanced_weights(y, bins):
    """Discretisation/weights learned only from training labels."""
    discretizer = KBinsDiscretizer(n_bins=bins, encode="ordinal", strategy="quantile",
                                 quantile_method="averaged_inverted_cdf", random_state=42)
    labels = discretizer.fit_transform(np.asarray(y).reshape(-1, 1)).astype(int).ravel()
    counts = np.bincount(labels)
    by_class = len(labels)/(len(counts)*counts)
    cap = float(np.quantile(by_class[labels], .95))
    norm = float(np.minimum(by_class[labels], cap).mean())

    def transform(values):
        group = discretizer.transform(np.asarray(values).reshape(-1, 1)).astype(int).ravel()
        return np.minimum(by_class[group], cap)/norm
    return transform(y), transform


def fit_openfpl(train, validation, xt, xv, xq, pos, progress, factory=None):
    if factory is None:
        from xgboost import XGBRegressor
        factory = XGBRegressor
    xs = MinMaxScaler().fit(xt)
    ys = MinMaxScaler().fit(train.total_points.to_numpy().reshape(-1, 1))
    xt, xv, xq = (xs.transform(a).astype(np.float32) for a in (xt, xv, xq))
    yt = ys.transform(train.total_points.to_numpy().reshape(-1, 1)).ravel()
    yv = ys.transform(validation.total_points.to_numpy().reshape(-1, 1)).ravel()
    weights, apply_weights = balanced_weights(yt, POLICY["openfpl_bins"][pos-1])
    validation_weights = apply_weights(yv)
    predictions = []
    for member in recipe()["members"][str(pos)]:
        params = {k:v for k,v in member.items() if k != "candidate"}
        model = factory(**params, random_state=42, n_jobs=2, tree_method="hist",
                        early_stopping_rounds=30, eval_metric="rmse")
        started = time.monotonic()
        model.fit(xt, yt, sample_weight=weights, eval_set=[(xv, yv)],
                  sample_weight_eval_set=[validation_weights], verbose=False)
        fit_seconds = time.monotonic()-started
        started = time.monotonic()
        predictions.append(ys.inverse_transform(model.predict(xq).reshape(-1, 1)).ravel())
        progress(dict(method="openfpl_cv1_refit", position=pos, member=member["candidate"],
                      fit_seconds=fit_seconds, prediction_seconds=time.monotonic()-started,
                      best_iteration=int(model.best_iteration)))
    return np.median(np.column_stack(predictions), axis=1)


def involvement_counts(history, cutoff):
    """AIrsenal-style minute-scaled goal/assist/neither counts, not its full system."""
    h = history[(history.minutes > 0) & (history.team_goals > 0)]
    if h.empty:
        return np.zeros(3)
    age = (cutoff-h.ts).dt.total_seconds().to_numpy()/86400/365.25
    w = np.exp(-POLICY["component"]["epsilon_per_year"]*age)
    w *= len(w)/w.sum()
    goals = float(np.dot(h.goals_scored, w)); assists = float(np.dot(h.assists, w))
    team = float(np.dot(h.team_goals, w))
    minutes = float(np.dot(h.minutes, w))
    return np.maximum([goals, assists, team*minutes/(90*w.sum())-goals-assists], 0.)


def residual_points(frame):
    """All special returns remain in a declared empirical residual, including DC."""
    minutes = frame.minutes.to_numpy(); pos = frame.position.to_numpy()
    gf = frame.goals_scored.to_numpy(); ga = frame.goals_conceded.to_numpy()
    goalkeeper_goal = np.where(frame.season.ge("2024-25"),10,6)
    goal_points = np.where(pos==1,goalkeeper_goal,np.choose(pos-1,[6,6,5,4]))
    standard = ((minutes > 0).astype(int)+(minutes >= 60).astype(int)
                + goal_points*gf+3*frame.assists.to_numpy()
                + np.choose(pos-1, [4,4,1,0])*((minutes >= 60)&(ga == 0))
                - (pos <= 2)*np.floor(ga/2)+(pos == 1)*np.floor(frame.saves.to_numpy()/3))
    return frame.total_points.to_numpy()-standard


def minute_points(minutes, scored, conceded, involvement, residual90, save90, position):
    """Exact Poisson expectations under the declared simplified component model."""
    m = np.asarray(minutes, dtype=float)
    fractions = m/90; active = m > 0; sixty = m >= 60
    gc = conceded*fractions
    result = active.astype(float)+sixty.astype(float)
    result += ((10 if position == 1 else 6 if position == 2 else 5 if position == 3 else 4)*involvement[0]
               +3*involvement[1])*scored*fractions
    result += (4 if position <= 2 else 1 if position == 3 else 0)*sixty*np.exp(-gc)
    if position <= 2:
        result -= gc/2-(1-np.exp(-2*gc))/4
    if position == 1:
        # E[floor(Poisson(lambda)/3)] = sum P(X >= 3k); bounded tail here <1e-12.
        lam = np.clip(save90*fractions, 0, 20)
        result += poisson.sf(np.arange(3, 121, 3)[:, None]-1, lam).sum(axis=0)
    return result+residual90*fractions


class ConjugatePoisson:
    """Declared AIrsenal-inspired variant: regularised Poisson replaces BPL."""
    def fit(self, players, teams, train_mask):
        self.players = players.copy()
        self.players["residual"] = residual_points(players)
        keys = players.loc[train_mask, ["season", "fixture"]].drop_duplicates()
        t = teams.merge(keys, on=["season", "fixture"], validate="many_to_one").copy()
        t["home_label"] = np.where(t.home, "home", "away")
        self.encoder = OneHotEncoder(handle_unknown="ignore")
        matrix = self.encoder.fit_transform(t[["team_name", "opponent_name", "home_label"]])
        weights = np.power(.5, (t.ts.max()-t.ts).dt.total_seconds()/86400/365.25)
        self.team_model = PoissonRegressor(alpha=1., max_iter=500, tol=1e-7)
        self.team_model.fit(matrix, t.goals_scored, sample_weight=weights)
        self.groups = {c:g.sort_values("ts") for c,g in self.players.groupby("fpl_code")}
        h = self.players[train_mask]
        cutoff = h.ts.max()+pd.Timedelta(hours=3)
        counts = np.sum([involvement_counts(g, cutoff) for _,g in h.groupby("fpl_code")], axis=0)
        if counts.sum() <= 0:
            raise ValueError("Empty training involvement prior")
        self.prior = 35*counts/counts.sum()
        self.rates = {}
        for pos,g in h.groupby("position"):
            total = float(g.minutes.sum())
            if total <= 0:
                raise ValueError("Missing positional exposure")
            self.rates[pos] = (float(g.residual.sum())*90/total, float(g.saves.sum())*90/total)
        self.fit_cutoff = cutoff
        return self

    def predict(self, query, chance):
        if not query.index.equals(chance.index):
            raise ValueError("Availability order differs")
        target = query[["team_name", "opponent_name"]].copy()
        target["home_label"] = np.where(query.home, "home", "away")
        scored = np.clip(self.team_model.predict(self.encoder.transform(target)), .05, 6.)
        reverse = target.rename(columns={"team_name":"opponent_name", "opponent_name":"team_name"})
        reverse["home_label"] = np.where(query.home, "away", "home")
        conceded = np.clip(self.team_model.predict(self.encoder.transform(reverse[target.columns])), .05, 6.)
        prediction = []
        for row, gf, ga in zip(query.itertuples(), scored, conceded):
            cutoff = row.deadline-pd.Timedelta(hours=3)
            if self.fit_cutoff >= row.deadline:
                raise ValueError("Team/prior fit reaches evaluation deadline")
            history = self.groups[row.fpl_code]
            history = history[history.ts < cutoff]
            minutes = (history.minutes.tail(3).to_numpy(dtype=float) if len(history)
                       else np.array([POLICY["component"]["cold_start_minutes"][row.position-1]]))
            if chance.loc[row.Index] == 0:
                minutes = np.zeros_like(minutes)
            posterior = self.prior+involvement_counts(history, cutoff)
            involvement = posterior/posterior.sum()
            prior_residual, prior_saves = self.rates[row.position]
            total = float(history.minutes.sum())+900
            residual90 = (float(history.residual.sum())*90+900*prior_residual)/total
            saves90 = (float(history.saves.sum())*90+900*prior_saves)/total
            prediction.append(float(minute_points(minutes, gf, ga, involvement,
                                                  residual90, saves90, row.position).mean()))
        return np.asarray(prediction)


def code_hashes():
    names = ("historical_references.py", "native_history.py", "native_reference.py",
             "conditional_reference.py", "benchmark_metrics.py", "benchmark_evaluation.py",
             "forecast.py", "points_replay.py")
    return {n:file_hash(Path(__file__).with_name(n)) for n in names}


def matched_inputs(entries):
    frames, masks, proof = load_inputs(entries)
    p = frames["players"]
    for name, column in (("native_predictions", "native_reference"),
                         ("conditional_predictions", "conditional_reference")):
        frame = pd.read_csv(entries[name]["path"])
        joined = frames["reference"].merge(frame[KEYS+["actual", "candidate", column]],
                      on=KEYS, how="outer", validate="one_to_one", indicator=True, suffixes=("", "_other"))
        if not joined._merge.eq("both").all() or not joined.actual.eq(joined.actual_other).all() or not joined.candidate.eq(joined.candidate_other).all():
            raise ValueError("Frozen comparison target/coverage/cohort differs")
        if not np.isfinite(joined[column]).all():
            raise ValueError("Nonfinite frozen comparison")
        frames["reference"] = joined.drop(columns=["actual_other", "candidate_other", "_merge"])
    teams = frames["teams"].copy(); teams["ts"] = pd.to_datetime(teams.ts, utc=True)
    venues = p[["season", "fixture", "team_name", "home"]].drop_duplicates()
    teams = teams.merge(venues, on=["season", "fixture", "team_name"], validate="one_to_one")
    if teams.home.isna().any():
        raise ValueError("Missing team venue")
    frames["teams"] = teams
    if {"frozen_openfpl","parent_manifest","parent_run"}&set(entries):
        if not {"frozen_openfpl","parent_manifest","parent_run"}<=set(entries):
            raise ValueError("Reuse requires frozen predictions, parent manifest and completed run")
        old=json.loads(Path(entries["parent_manifest"]["path"]).read_text())
        completed=json.loads(Path(entries["parent_run"]["path"]).read_text())
        if completed.get("status")!="completed" or completed.get("output_sha256",{}).get("predictions.csv")!=entries["frozen_openfpl"]["sha256"] or entries["parent_manifest"]["sha256"] not in completed.get("input_sha256",[]):
            raise ValueError("Parent completed-run hashes differ")
        prior_policy={**POLICY,"method":"historical-external-adaptations-v1",
                      "component":{k:v for k,v in POLICY["component"].items() if k!="goalkeeper_goal_points"}}
        original_inputs={k:v for k,v in entries.items() if k not in ("frozen_openfpl","parent_manifest","parent_run")}
        if old["policy"]!=prior_policy or old["recipe"]!=recipe() or old["inputs"]!=original_inputs:
            raise ValueError("Parent policy/recipe/input evidence differs")
        preserved=pd.read_csv(entries["frozen_openfpl"]["path"])
        joined=frames["reference"].merge(preserved[KEYS+["actual","candidate","openfpl_cv1_refit"]],
                  on=KEYS,how="outer",validate="one_to_one",indicator=True,suffixes=("","_parent"))
        if not joined._merge.eq("both").all() or not joined.actual.eq(joined.actual_parent).all() or not joined.candidate.eq(joined.candidate_parent).all() or not np.isfinite(joined.openfpl_cv1_refit).all():
            raise ValueError("Parent OpenFPL prediction coverage/targets differ")
        frames["preserved_openfpl"]=preserved
    return frames, masks, proof


def panels(players, snapshots, reference):
    """Freeze 20 legal squads from GW28 inputs, never observed point returns."""
    week = players[players.season.eq("2025-26") & players.gameweek.eq(28)]
    pool = week.merge(reference[KEYS+["candidate"]], on=KEYS, validate="one_to_one")
    pool = pool[pool.candidate].drop_duplicates("fpl_code")
    pool = pool.merge(snapshots[["season", "gameweek", "fpl_code", "value", "captured_at"]],
                      on=["season", "gameweek", "fpl_code"], validate="one_to_one")
    candidates = [dict(id=int(r.fpl_code), position=int(r.position), team=r.team_name,
                       price_tenths=int(r.value)) for r in pool.itertuples()
                  if np.isfinite(r.value) and r.value > 0 and float(r.value).is_integer()]
    rng = np.random.default_rng(POLICY["panel_seed"]); squads=[]; seen=set()
    for _ in range(10000):
        selected=[]
        for pos,n in ((1,2),(2,5),(3,5),(4,3)):
            choices=[p for p in candidates if p["position"]==pos]
            if len(choices)<n:
                raise ValueError("Insufficient opening panel candidates")
            selected += [choices[i] for i in rng.choice(len(choices), n, replace=False)]
        key=tuple(sorted(p["id"] for p in selected))
        if key not in seen and legal_squad(selected) and sum(p["price_tenths"] for p in selected)<=1000:
            squads.append(selected); seen.add(key)
            if len(squads)==POLICY["panels"]:
                break
    if len(squads)!=POLICY["panels"]:
        raise ValueError("Unable to freeze declared panel count")
    return dict(squads=squads, inputs_as_of=pd.to_datetime(pool.captured_at, utc=True).max().isoformat(),
                created_at=dt.datetime.now(dt.timezone.utc).isoformat())


def prepare(paths, output):
    if Path(output).exists():
        raise ValueError("Manifest exists")
    entries={k:dict(path=str(Path(v).resolve()), sha256=file_hash(v)) for k,v in paths.items()}
    frames,masks,_=matched_inputs(entries)
    for pos in range(1,5):
        if not (masks["train"]&frames["players"].position.eq(pos)).any() or not (masks["validation"]&frames["players"].position.eq(pos)).any():
            raise ValueError("Missing positional split")
    spec=dict(policy=POLICY, recipe=recipe(), code=code_hashes(), environment=environment(),
              inputs=entries, panels=panels(frames["players"], frames["snapshots"], frames["reference"]),
              created_at=dt.datetime.now(dt.timezone.utc).isoformat())
    with Path(output).open("x") as f:
        json.dump(spec, f, indent=2, allow_nan=False)
    return spec


def run(manifest, expected, directory):
    if file_hash(manifest)!=expected:
        raise ValueError("Manifest checksum mismatch")
    spec=json.loads(Path(manifest).read_text())
    if spec["policy"]!=POLICY or spec["code"]!=code_hashes() or spec["recipe"]!=recipe() or spec["environment"]!=environment():
        raise ValueError("Frozen policy/source/environment changed")
    out=Path(directory);out.mkdir(parents=True, exist_ok=True)
    if any((out/n).exists() for n in ("progress.jsonl", "predictions.csv", "results.json")):
        raise ValueError("Output exists")
    frames,masks,_=matched_inputs(spec["inputs"]);p=frames["players"];test=masks["test"]
    started=time.monotonic();x,evidence=NativeHistory(p, frames["teams"]).transform(p, frames["snapshots"])
    result=dict(policy=POLICY, feature_seconds=time.monotonic()-started, component={}, metrics={}, paired={})
    prediction=pd.Series(np.nan, index=p.index[test])
    with threadpool_limits(limits=2), (out/"progress.jsonl").open("x") as log:
        def progress(record):
            log.write(json.dumps(record)+"\n");log.flush()
            print("Completed "+record["method"]+" "+str(record.get("position", ""))+" "+str(record.get("member", "")), flush=True)
        if "preserved_openfpl" in frames:
            preserved=frames["preserved_openfpl"]
            aligned=p.loc[test,KEYS].merge(preserved[KEYS+["openfpl_cv1_refit"]],on=KEYS,validate="one_to_one")
            if not aligned[KEYS].equals(p.loc[test,KEYS].reset_index(drop=True)):
                raise ValueError("Parent OpenFPL key order differs")
            prediction.iloc[:]=aligned.openfpl_cv1_refit.to_numpy()
            result["openfpl_reused_sha256"]=spec["inputs"]["frozen_openfpl"]["sha256"]
        else:
            for pos in range(1,5):
                train=masks["train"]&p.position.eq(pos);val=masks["validation"]&p.position.eq(pos);query=test&p.position.eq(pos)
                names=recipe()["feature_schema"][str(pos)]
                matrix=openfpl_matrix(x, names)
                prediction.loc[p.index[query]]=fit_openfpl(p[train], p[val], matrix[train], matrix[val], matrix[query], pos, progress)
        if not np.isfinite(prediction).all():
            raise ValueError("Incomplete OpenFPL coverage")
        augmented=p.merge(frames["teams"][["season", "fixture", "team_name", "goals_scored"]],
                          on=["season", "fixture", "team_name"], how="left", validate="many_to_one", suffixes=("", "_team"))
        if len(augmented)!=len(p) or not augmented[KEYS].equals(p[KEYS]):
            raise ValueError("Component history key order differs")
        augmented["team_goals"]=augmented.goals_scored_team
        started=time.monotonic();component=ConjugatePoisson().fit(augmented, frames["teams"], masks["train"])
        result["component"]["fit_seconds"]=time.monotonic()-started
        started=time.monotonic();component_prediction=component.predict(p[test], x.loc[test, "sig_chance_playing"])
        result["component"]["prediction_seconds"]=time.monotonic()-started
        progress(dict(method="conjugate_poisson", **result["component"]))
    z=p.loc[test, KEYS+["position", "minutes", "deadline", "total_points"]].rename(columns={"total_points":"actual"}).copy()
    z["openfpl_cv1_refit"]=prediction.to_numpy();z["conjugate_poisson"]=component_prediction
    z["candidate"]=evidence.loc[test,"candidate"];z["snapshot_known"]=evidence.loc[test,"snapshot_present"]
    z=z.merge(frames["reference"][KEYS+["actual", "candidate", *METHODS[:3]]], on=KEYS,
              validate="one_to_one", suffixes=("", "_frozen"))
    if not z.actual.eq(z.actual_frozen).all() or not z.candidate.eq(z.candidate_frozen).all():
        raise ValueError("Comparison target/cohort mismatch")
    if not np.isfinite(z[METHODS]).all().all():
        raise ValueError("Incomplete comparison predictions")
    grouping=z.groupby(["season", "gameweek", "fpl_code"])
    if grouping.candidate.nunique().ne(1).any() or grouping.position.nunique().ne(1).any():
        raise ValueError("Double-GW metadata differs")
    g=grouping.agg({**{k:"sum" for k in ["actual", *METHODS]}, "candidate":"first",
                    "snapshot_known":"first", "position":"first"}).reset_index()
    for name,cohort in (("primary",g[g.candidate&g.snapshot_known]), ("all_candidates",g[g.candidate]), ("all_players",g)):
        result["metrics"][name]={m:point_scores(cohort,m) for m in METHODS}
    for m in METHODS[3:]:
        result["paired"][m]=paired_block_errors(g[g.candidate&g.snapshot_known],m,"reference")
    panel_spec=dict(schema_version=1, panels=[])
    for gw in sorted(g.gameweek.unique()):
        for i,squad in enumerate(spec["panels"]["squads"]):
            panel_spec["panels"].append(dict(id=f"gw{gw}-squad{i}", season="2025-26", gameweek=int(gw),
                   inputs_as_of=spec["panels"]["inputs_as_of"], created_at=spec["panels"]["created_at"],
                   origin="retrospective_fixed", players=[dict(fpl_code=v["id"], **{k:a for k,a in v.items() if k!="id"}) for v in squad]))
    # Existing replay limit is per100panels; aggregate20fixed squads x11weeks.
    result["fixed_squads"]=[]
    truth=z.copy();truth["deadline"]=pd.to_datetime(truth.deadline,utc=True)
    for start in range(0,len(panel_spec["panels"]),100):
        batch=dict(schema_version=1,panels=panel_spec["panels"][start:start+100])
        result["fixed_squads"].append(fixed_squad_report(g,truth,{m:m for m in METHODS},batch))
    z.to_csv(out/"predictions.csv", index=False, mode="x")
    result["manifest_sha256"]=expected;result["predictions_sha256"]=file_hash(out/"predictions.csv")
    with (out/"results.json").open("x") as f:
        json.dump(result,f,indent=2,allow_nan=False)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest="action",required=True)
    a=sub.add_parser("prepare")
    for n in ("players", "teams", "snapshots", "reference", "provenance", "native-predictions", "conditional-predictions", "output"):
        a.add_argument("--"+n, required=True, type=Path)
    for n in ("frozen-openfpl","parent-manifest","parent-run"):
        a.add_argument("--"+n,type=Path)
    b=sub.add_parser("run")
    for n in ("manifest", "manifest-sha256", "directory"):
        b.add_argument("--"+n, required=True)
    args=vars(parser.parse_args());action=args.pop("action")
    try:
        if action=="prepare":
            prepare({k:v for k,v in args.items() if k!="output" and v is not None},args["output"])
        else:
            run(args["manifest"],args["manifest_sha256"],args["directory"])
    except (ValueError,KeyError,TypeError,OSError,ImportError) as exc:
        parser.exit(2,f"Historical reference rejected: {exc}\n")
    print("Named retrospective references saved; no original-system ranking or promotion.")


if __name__=="__main__":
    main()
