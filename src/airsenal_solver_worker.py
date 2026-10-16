"""Optional source-verified AIrsenal worker; no optional imports on module import.

Explicitly started trusted research process, not a security sandbox. Its database
contains origin-frozen aggregate forecast views, never physical fixture outcomes.
"""
import argparse
import builtins
import contextlib
import getpass
import hashlib
import importlib.metadata
import importlib.util
import json
import os
import random
import signal
import socket
import sys
import time
from collections import deque
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from opening_baseline import cheapest_opening
from native_solver_worker import MAX_MESSAGE,RESOURCES,read_json,validate_request,verified_sources

RECIPE=read_json((RESOURCES/'airsenal_solver_recipe.json').read_bytes())

class NativeBudgetExpired(Exception):pass

def expired(signum,frame):raise NativeBudgetExpired('Native request deadline')

class FairQueue:
    """Depth first within each immediate move family; rotate after a full plan."""
    def __init__(self,root,deadline,context):
        self.stacks={'root':[root]};self.order=deque(['root']);self.pending=[]
        self.deadline=deadline;self.context=context;self.processed=0
        self.rotate=False;self.truncated=False;self.finished_families=[]
    def get(self):
        if time.monotonic()>=self.deadline:
            self.truncated=any(self.stacks.values());return None
        if self.rotate and self.order:self.order.rotate(-1)
        self.rotate=False
        while self.order:
            family=self.order[0]
            if self.stacks[family]:
                node=self.stacks[family].pop();self.context(node);return node
            self.order.popleft();del self.stacks[family]
        return None
    def put(self,node):self.pending.append(node)
    def task_done(self):
        grouped={}
        for node in self.pending:
            prior=node[-1]
            family=node[0].label() if prior is not None and len(prior)==0 else prior.outcomes[0].move.label()
            grouped.setdefault(family,[]).append(node)
        for family,nodes in grouped.items():
            if family not in self.stacks:self.stacks[family]=[];self.order.append(family)
            self.stacks[family].extend(reversed(nodes))
        self.pending=[];self.processed+=1
    def completed_plan(self):
        if self.order:self.finished_families.append(self.order[0])
        self.rotate=True


def seed_population(optimizer,population,allowed):
    """Replace one random individual with a forecast-independent legal seed."""
    if not population:return False
    positions={'GK':1,'DEF':2,'MID':3,'FWD':4}
    rows=[dict(id=p.player_id,position=positions[p.position(optimizer.season)],
        team=p.team(optimizer.root_gameweek,optimizer.season),
        price_tenths=p.price(optimizer.root_gameweek,optimizer.season),can_buy=allowed(p.player_id)) for p in optimizer.players]
    try:ledger=cheapest_opening(SimpleNamespace(players=rows),optimizer.scoring.budget)
    except ValueError:return False
    selected=[index for index,p in enumerate(optimizer.players) if p.player_id in ledger]
    if len(selected)!=15:return False
    population[0][:]=selected
    return True


def bootstrap(root,directory):
    """Verify the actual import location before any upstream source executes."""
    global home
    root=Path(root).resolve();verified_sources(root,RECIPE['source_sha256'])
    spec=importlib.util.find_spec('airsenal')
    if spec is None or Path(spec.origin).resolve().parent.parent!=root:raise ValueError('Verified source differs from import location')
    if list(sys.version_info[:2])!=RECIPE['python_minor']:raise ValueError('Use declared optional Python runtime')
    versions={name:importlib.metadata.version(name) for name in ['airsenal',*RECIPE['optional_planner_dependencies'],*RECIPE['other_observed_dependencies']]}
    expected={'airsenal':RECIPE['package_version'],**RECIPE['optional_planner_dependencies'],**RECIPE['other_observed_dependencies']}
    if versions!=expected:raise ValueError('Optional runtime versions differ')
    dist=importlib.metadata.distribution('airsenal')
    licenses=[Path(dist.locate_file(f)).resolve() for f in dist.files if str(f).endswith('.dist-info/licenses/LICENSE')]
    if len(licenses)!=1 or not licenses[0].is_relative_to(root) or hashlib.sha256(licenses[0].read_bytes()).hexdigest()!=RECIPE['license_sha256']:raise ValueError('Source license differs')
    home=Path(directory).resolve();home.mkdir(parents=True,exist_ok=False)
    for key in tuple(os.environ):
        if key.startswith(('AIRSENAL_','FPL_')) or any(s in key.upper() for s in ('TOKEN','PASSWORD','SECRET','CREDENTIAL','API_KEY')):os.environ.pop(key)
    os.environ['AIRSENAL_HOME']=str(home);os.environ['AIRSENAL_DB_FILE']=str(home/'origin.sqlite')
    def deny(*args,**kwargs):raise RuntimeError('Network and account interaction disabled')
    socket.socket.connect=deny;socket.create_connection=deny;builtins.input=deny;getpass.getpass=deny
    import curl_cffi.requests as requests
    requests.Session.request=deny;requests.AsyncSession.request=deny
    import requests as python_requests
    python_requests.sessions.Session.request=deny
    import airsenal.remote.fpl_http as http
    http.get_json=deny;http.post_json=deny
    from airsenal.db.models import Player,PlayerAttributes,Fixture,PlayerPrediction
    from airsenal.db.session import get_session,configure_database
    from airsenal.optimization.moves import ChipSchedule,GameweekChips,GameweekMove
    from airsenal.game.enums import Chip
    from airsenal.optimization.squad_optimizers import GeneticSquadOptimizer,GeneticAlgorithmConfig
    from airsenal.optimization.squad_optimizers.genetic_algorithm import SquadOpt
    from airsenal.optimization.protocols import TransferSearchRequest,TransferConstraints
    from airsenal.optimization.squad_score import SquadScoringConfig,get_discount_factor
    from airsenal.optimization.transfer_optimizers.tree_search import TreeSearchConfig
    from airsenal.squad.squad import Squad,SubWeights
    from airsenal.optimization.transfer_optimizers import tree_search as tree
    from airsenal.optimization.strategies.full_squad import FullSquadStrategy
    # A dedicated serial worker owns these upstream bindings for its lifetime.
    names=['Player','PlayerAttributes','Fixture','PlayerPrediction','get_session','configure_database','ChipSchedule','GameweekChips','GameweekMove','Chip','GeneticSquadOptimizer','GeneticAlgorithmConfig','TransferSearchRequest','TransferConstraints','SquadScoringConfig','TreeSearchConfig','Squad','SubWeights']
    namespace=locals();globals().update({name:namespace[name] for name in names})
    get_discount_factor.__defaults__=(1.,);tree.StallWatchdog.start=lambda self:None
    return dict(status='ready',revision=RECIPE['revision'],source_sha256=RECIPE['source_sha256'],versions=versions,network_disabled=True,serial=True,discount=1.),(tree.next_gameweek_transfers,Squad.add_player,FullSquadStrategy.propose, SquadOpt._setup_deap)

def solve(src):
    started = time.monotonic()
    _,_,_,chips,profile = validate_request(src,RECIPE)
    random.seed(42)
    # Execute the original node expansion in this process; no fork wrapper.
    if src.get("schema_version") != 1 or src["market"]["season"] != "2025-26":
        raise ValueError("Unsupported schema/season")
    if set(src) - {"schema_version","market","state","xp","through","chip_schedule","opening_ids","seconds"}:
        raise ValueError("Unknown request fields")
    if set(src["state"]) - {"season","gameweek","holdings","bank","free_transfers","used_chips","previous_chip"}:
        raise ValueError("Unknown state fields, including past outcomes")
    if any(set(row) != {"id","position","team","price_tenths","can_buy"} for row in src["market"]["rows"]):
        raise ValueError("Unknown market fields")
    origin = src["market"]["gameweek"]
    through = src["through"]
    season = "2526"
    tag = "origin-frozen-aggregate-pgw-view"
    configure_database(f"sqlite:///{home / 'origin.sqlite'}")
    (home / 'origin.sqlite').unlink(missing_ok=True)
    db = get_session()
    positions = {1:"GK", 2:"DEF", 3:"MID", 4:"FWD"}
    for row in src["market"]["rows"]:
        p = Player(player_id=row["id"], fpl_api_id=row["id"], name=str(row["id"]), display_name=None, opta_code=None)
        for view_gw in range(origin,through+1):
            p.attributes.append(PlayerAttributes(season=season, gameweek=view_gw, price=row["price_tenths"], team=row["team"], position=positions[row["position"]]))
        db.add(p)
    fixtures = {}
    for gw in range(origin, through+1):
        f = Fixture(gameweek=gw, season=season, home_team="AGGREGATE_PGW_VIEW", away_team="NOT_PHYSICAL_FIXTURE", date=None, tag=tag)
        db.add(f)
        db.flush()
        fixtures[gw] = f.fixture_id
    for gw, pid, xp in src["xp"]:
        if gw <= through:
            db.add(PlayerPrediction(player_id=pid, fixture_id=fixtures[gw], predicted_points=xp, tag=tag))
    db.commit()
    state = src["state"]
    if origin==1 and (state["bank"]!=profile["initial_budget"] or state["free_transfers"]!=0 or state["used_chips"]):raise ValueError("Unaudited opening state")
    squad = Squad(budget=state["bank"]+sum(q for _,q in state["holdings"]), season=season)
    for pid, price in state["holdings"]:
        if not squad.add_player(pid,price=price,gameweek=origin,check_team=False,dbsession=db):raise ValueError("Illegal held roster")
    if squad.budget != state["bank"]:raise ValueError("Starting bank mismatch")
    request = TransferSearchRequest(starting_squad=squad, gameweeks=list(range(origin,through+1)), tag=tag,
        season=season, chip_schedule=ChipSchedule({int(g):GameweekChips(chip_to_play=Chip({"freehit":"free_hit","bboost":"bench_boost","3xc":"triple_captain","wildcard":"wildcard"}[c])) for g,c in src["chip_schedule"].items()}), num_free_transfers=state["free_transfers"],
        squad_optimizer=GeneticSquadOptimizer(GeneticAlgorithmConfig(random_state=42)),
        constraints=TransferConstraints(max_total_hit=8, allow_unused_transfers=True, max_opt_transfers=2),
        scoring=SquadScoringConfig(sub_weights=SubWeights(gk=.1, outfield=(.1,.1,.1))))
    from collections import deque
    from airsenal.optimization.moves import GameweekMove
    from airsenal.optimization.plan import TransferSearchResult
    from airsenal.optimization.transfer_optimizers.tree_search import optimize
    class Results:
        def __init__(self): self.plans = []
        def put(self, plan):
            self.plans.append(plan)
            queue.completed_plan()
    # Explicit compatibility layer; source files stay unchanged.
    import airsenal.optimization.transfer_optimizers.tree_search as tree
    from airsenal.optimization.strategies.full_squad import FullSquadStrategy
    from airsenal.optimization.squad_optimizers.genetic_algorithm import SquadOpt
    prices = {r["id"]:r["price_tenths"] for r in src["market"]["rows"]}
    unavailable = {r["id"] for r in src["market"]["rows"] if not r["can_buy"]}
    context = {"branch_gameweek":origin, "rebuild_held":None}
    raw_setup = SquadOpt._setup_deap
    def setup_with_seed(optimizer):
        raw_setup(optimizer)
        original_population=optimizer.toolbox.population
        def population(*args,**kwargs):
            values=original_population(*args,**kwargs)
            seed_population(optimizer,values,lambda i:i not in unavailable or i in (context['rebuild_held'] or set()))
            return values
        optimizer.toolbox.register('population',population)
    SquadOpt._setup_deap=setup_with_seed
    raw_next = tree.next_gameweek_transfers
    def next_with_reset(free_transfers,*args,**kwargs):
        reset = profile["ft_topups"].get(str(context["branch_gameweek"]))
        if reset is not None:
            free_transfers = reset
        return raw_next(free_transfers,*args,**kwargs)
    tree.next_gameweek_transfers = next_with_reset
    raw_add = Squad.add_player
    def eligible_add(self,p,*args,**kwargs):
        pid = p if isinstance(p,int) else getattr(p,"player_id",None)
        if pid in unavailable and pid not in (context["rebuild_held"] or set()):
            return False
        return raw_add(self,p,*args,**kwargs)
    Squad.add_player = eligible_add
    raw_full = FullSquadStrategy.propose
    def full_with_basis(self,request):
        old = {p.player_id:p.purchase_price for p in request.squad.players}
        context["rebuild_held"] = set(old)
        from dataclasses import replace
        from airsenal.core.caching import clear_query_caches
        from airsenal.optimization.protocols import progress_total
        class RetentionOfferOptimizer:
            def __init__(self,inner): self.inner = inner
            def num_increments(self,effort=None): return progress_total(self.inner,effort)
            def optimize(self,problem):
                # The native strategy has already computed the correct sale-value
                # budget. Holding an original player costs that selling value in
                # this accounting system, not a fresh purchase at market price.
                attributes = db.query(PlayerAttributes).filter(PlayerAttributes.player_id.in_(old)).all()
                saved = [(a,a.price) for a in attributes]
                try:
                    for a,_ in saved:
                        a.price = min(prices[a.player_id],old[a.player_id])+max(0,prices[a.player_id]-old[a.player_id])//2
                    db.commit(); clear_query_caches()
                    return self.inner.optimize(problem)
                finally:
                    for a,value in saved: a.price = value
                    db.commit(); clear_query_caches()
        try:
            proxy = RetentionOfferOptimizer(request.squad_optimizer or GeneticSquadOptimizer())
            proposal = raw_full(self,replace(request,squad_optimizer=proxy))
        finally:
            context["rebuild_held"] = None
        selected = {p.player_id for p in proposal.squad.players}
        proceeds = sum(min(prices[i],old[i])+max(0,prices[i]-old[i])//2 for i in old.keys()-selected)
        cost = sum(prices[i] for i in selected-old.keys())
        proposal.squad.budget = request.squad.budget+proceeds-cost
        if proposal.squad.budget<0:raise ValueError("Negative rebuild bank")
        for p in proposal.squad.players:
            p.purchase_price = old.get(p.player_id,prices[p.player_id])
        return proposal
    FullSquadStrategy.propose = full_with_basis
    prefix = None
    original_origin = origin
    opening_roster = None
    if origin == 1:
        from airsenal.optimization.protocols import SquadRequest
        from airsenal.optimization.plan import Plan, GameweekOutcome
        from airsenal.optimization.squad_score import get_discounted_squad_score
        if src["opening_ids"] is None:
            squad = GeneticSquadOptimizer(GeneticAlgorithmConfig(random_state=42)).optimize(
                SquadRequest(gameweeks=list(range(1,through+1)),tag=tag,season=season,root_gameweek=1,
                    scoring=request.scoring,remove_zero=False,effort=10,dbsession=db,
                    bench_boost_gameweek=1 if chips.get(1)=="bboost" else None,
                    triple_captain_gameweek=1 if chips.get(1)=="3xc" else None))
        else:
            squad = Squad(budget=profile["initial_budget"],season=season)
            for pid in src["opening_ids"]:
                if not squad.add_player(pid,gameweek=1,dbsession=db):raise ValueError("Illegal fixed opening")
        opening_roster = sorted(p.player_id for p in squad.players)
        first_chip = request.chip_schedule.for_gameweek(1).chip_to_play
        first_points = get_discounted_squad_score(squad,[1],tag,root_gameweek=1,
            bench_boost_gameweek=1 if chips.get(1)=="bboost" else None,
            triple_captain_gameweek=1 if chips.get(1)=="3xc" else None,
            sub_weights=request.scoring.sub_weights)
        prefix = GameweekOutcome(gameweek=1,move=GameweekMove(chip=first_chip),points=first_points,
            discount_factor=1.,points_hit=0,free_transfers=1,players_in=tuple(opening_roster),bank=squad.budget)
        request = replace(request,starting_squad=squad,gameweeks=list(range(2,through+1)),num_free_transfers=1)
        origin = 2
    def node_context(node):
        prior = node[-1]
        context["branch_gameweek"] = origin if prior is None else origin+len(prior)+1
    queue = FairQueue((GameweekMove(),request.num_free_transfers,0,0,squad,None),
                      started+src["seconds"],node_context)
    results = Results()
    stopped = None
    try:
        if request.gameweeks:
            optimize(queue,0,results,request,TreeSearchConfig(num_thread=1,num_iterations=10))
        else:
            results.plans.append(Plan(root_gameweek=1))
    except NativeBudgetExpired:
        queue.truncated = True
        stopped = "request deadline"
    if not results.plans:
        raise ValueError("No complete native plan within budget")
    if prefix is not None:
        results.plans = [Plan(root_gameweek=1,outcomes=(prefix,*p.outcomes)) for p in results.plans]
    result = TransferSearchResult.from_plans(results.plans)
    return dict(status="completed",seconds=time.monotonic()-started,
        revision=RECIPE["revision"],nodes=queue.processed,horizon=through-original_origin+1,
        truncated=queue.truncated,considered=len(result.considered),best=result.best.to_dict(),
        opening_roster=opening_roster,stopped=stopped,discount=1.,bound=None,
        explored_immediate_families=queue.finished_families,
        scope="Rule-adapted native tree/GA search; common mean objective, no optimality certificate")

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root',type=Path,required=True)
    parser.add_argument('--home',type=Path,required=True)
    args=parser.parse_args()
    if not hasattr(signal,'setitimer'):parser.error('Bounded worker requires a POSIX interval timer')
    with contextlib.redirect_stdout(sys.stderr):metadata,originals=bootstrap(args.source_root,args.home)
    import airsenal.optimization.transfer_optimizers.tree_search as tree
    from airsenal.optimization.strategies.full_squad import FullSquadStrategy
    from airsenal.optimization.squad_optimizers.genetic_algorithm import SquadOpt
    signal.signal(signal.SIGALRM,expired)
    print(json.dumps(metadata,allow_nan=False),flush=True)
    while raw:=sys.stdin.buffer.readline(MAX_MESSAGE+1):
        if len(raw)>MAX_MESSAGE or not raw.endswith(b'\n'):raise ValueError('Oversized or incomplete request')
        try:
            q=read_json(raw);validate_request(q,RECIPE)
            signal.setitimer(signal.ITIMER_REAL,q['seconds'])
            with contextlib.redirect_stdout(sys.stderr):answer=solve(q)
        except Exception as error:answer=dict(status='failed',error_type=type(error).__name__,message=str(error))
        finally:
            signal.setitimer(signal.ITIMER_REAL,0)
            tree.next_gameweek_transfers,Squad.add_player,FullSquadStrategy.propose,SquadOpt._setup_deap=originals
        print(json.dumps(answer,allow_nan=False),flush=True)

if __name__=='__main__':main()
