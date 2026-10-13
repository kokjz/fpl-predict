"""Fixed I3 adaptations; no forecast entry point or automatic promotion."""
import numpy as np
from sklearn.ensemble import ExtraTreesRegressor, HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline

from fpl_model import CORE_FEATURES, estimator, fit_estimator, sample_weights


def positions(x):
    one_hot = x[[f"pos_{p}" for p in range(1, 5)]].to_numpy()
    if not np.isin(one_hot, [0, 1]).all() or not (one_hot.sum(axis=1) == 1).all():
        raise ValueError("Exactly one valid position is required per row")
    return one_hot.argmax(axis=1) + 1


class LightweightCore:
    def __init__(self, kind, seed=20260921):
        if kind not in ("incumbent", "position", "minutes_mixture", "extra_trees"):
            raise ValueError("Unknown fixed I3 candidate")
        self.kind = kind
        self.seed = seed

    def _regressor(self):
        model = estimator("hgb7")
        model.set_params(random_state=self.seed)
        return model

    def fit(self, x, rows):
        if not x.index.equals(rows.index):
            raise ValueError("Features and labels must have identical ordered indices")
        xx = x[CORE_FEATURES]
        weights = sample_weights(rows)
        y = rows.points_core
        if self.kind == "incumbent":
            self.model = fit_estimator("hgb7", xx, y, weights)
        elif self.kind == "position":
            pos = positions(x)
            self.models = {}
            for p in range(1, 5):
                mask = pos == p
                if not mask.any():
                    raise ValueError("Training must include all four positions")
                model = self._regressor()
                model.fit(xx.loc[mask], y.loc[mask], sample_weight=weights[mask])
                self.models[p] = model
        elif self.kind == "extra_trees":
            self.model = make_pipeline(SimpleImputer(strategy="median"),
                ExtraTreesRegressor(n_estimators=128, max_depth=12,
                    min_samples_leaf=40, max_features=.5, n_jobs=2,
                    random_state=self.seed))
            self.model.fit(xx, y, extratreesregressor__sample_weight=weights)
        else:
            states = np.where(rows.minutes >= 60, 2,
                              np.where(rows.minutes > 0, 1, 0))
            self.classifier = HistGradientBoostingClassifier(max_leaf_nodes=7,
                max_iter=200, learning_rate=.05, l2_regularization=20.,
                min_samples_leaf=60, early_stopping=False, random_state=self.seed)
            self.classifier.fit(xx, states, sample_weight=weights)
            self.models = {}
            for state in (1, 2):
                mask = states == state
                if mask.any():
                    model = self._regressor()
                    model.fit(xx.loc[mask], y.loc[mask], sample_weight=weights[mask])
                    self.models[state] = model
        return self

    def predict(self, x):
        xx = x[CORE_FEATURES]
        if self.kind in ("incumbent", "extra_trees"):
            out = self.model.predict(xx)
        elif self.kind == "position":
            pos = positions(x)
            out = np.empty(len(x))
            for p, model in self.models.items():
                mask = pos == p
                if mask.any():
                    out[mask] = model.predict(xx.loc[mask])
        else:
            probabilities = self.classifier.predict_proba(xx)
            out = np.zeros(len(x))
            for state, model in self.models.items():
                column = list(self.classifier.classes_).index(state)
                # Clip the composed expectation only: negative conditional
                # returns (cards etc.) are legitimate FPL outcomes.
                out += probabilities[:, column] * model.predict(xx)
        return np.clip(out, 0, 20)
