"""
PalaySense — Shared Model Evaluation Utilities
===============================================
Defense-grade evaluation helpers used by every training module:

1. Baseline comparison (Naive / Seasonal Naive) so model gains are provable.
2. Walk-forward (rolling-origin) evaluation reported as mean ± std across
   multiple origins, with MAPE in addition to MAE / RMSE / R².
3. Training-only bias estimation (no test-set leakage): the bias that gets
   added to future forecasts is estimated from TimeSeriesSplit validation
   folds of the TRAINING window only, never from the held-out test set.

All functions are defensive (NaN/zero-safe) and return plain JSON-serializable
numbers so the pipeline can write them straight into metrics.json.
"""
import numpy as np
import pandas as pd
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error
from sklearn.model_selection import TimeSeriesSplit


# ---------------------------------------------------------------------------
# METRICS
# ---------------------------------------------------------------------------
def compute_metrics(y_true, y_pred):
    """MAE, RMSE, R² and MAPE with a zero/NaN-safe MAPE.

    Returns a dict of plain floats. MAPE is expressed in percent and ignores
    any observation whose actual value is (near) zero to avoid div-by-zero.
    """
    y_true = np.asarray(y_true, dtype=float).ravel()
    y_pred = np.asarray(y_pred, dtype=float).ravel()

    mae = mean_absolute_error(y_true, y_pred)
    rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
    r2 = r2_score(y_true, y_pred)

    mask = np.abs(y_true) > 1e-9
    if mask.sum() > 0:
        mape = float(
            np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100.0
        )
    else:
        mape = float("nan")

    return {
        "mae": float(mae),
        "rmse": rmse,
        "r2": float(r2),
        "mape": mape,
    }


# ---------------------------------------------------------------------------
# BASELINES
# ---------------------------------------------------------------------------
def naive_predictions(y_train, n):
    """Persistent Naive baseline: repeat the last observed value ``n`` times."""
    if y_train is None or len(y_train) == 0:
        return np.full(int(n), np.nan)
    last = float(pd.Series(y_train).iloc[-1])
    return np.full(int(n), last)


def seasonal_naive_predictions(y, train_end, n, season):
    """Seasonal Naive baseline.

    For test index ``train_end + step - 1`` (1-indexed ``step``) the forecast is
    the value from ``season`` steps earlier. Unavailable lookbacks become NaN so
    they never count toward the metrics.
    """
    y = pd.Series(np.asarray(y)).reset_index(drop=True)
    preds = []
    for step in range(1, int(n) + 1):
        idx = int(train_end) + step - int(season)
        preds.append(float(y.iloc[idx]) if 0 <= idx < len(y) else np.nan)
    return np.array(preds)


def baseline_metrics(y_full, train_len, season):
    """Evaluate Naive and Seasonal Naive baselines on a held-out window.

    ``y_full`` is the complete (chronological) target series, ``train_len`` is
    the number of leading rows used for training; the remainder is the held-out
    window. Seasonal Naive uses the value from ``season`` steps back (which may
    fall inside the earlier part of the held-out window), exactly as the
    walk-forward evaluation does, so the two benchmarks are consistent.
    """
    y = pd.Series(np.asarray(y_full)).reset_index(drop=True)
    y_train = y.iloc[:train_len]
    y_test = y.iloc[train_len:]
    n = len(y_test)
    naive = naive_predictions(y_train, n)
    s_naive = seasonal_naive_predictions(y, train_len, n, season)
    return {
        "naive": compute_metrics(y_test, naive),
        "seasonal_naive": compute_metrics(y_test, s_naive),
    }


# ---------------------------------------------------------------------------
# TRAINING-ONLY BIAS (no test-set leakage)
# ---------------------------------------------------------------------------
def estimate_bias_cv(model_factory, X, y, n_splits=5):
    """Estimate the additive bias from TimeSeriesSplit validation residuals.

    ``residual = actual - prediction`` on validation folds of the training
    window only; the mean residual is the bias that should be added to future
    forecasts. ``model_factory`` must return an unfitted sklearn-style
    estimator with ``.fit(X, y)`` / ``.predict(X)`` (e.g. ``clone(model)``).
    """
    X = X.reset_index(drop=True) if hasattr(X, "reset_index") else X
    y = pd.Series(np.asarray(y)).reset_index(drop=True)

    if len(y) < n_splits + 1:
        n_splits = max(1, len(y) // 2)

    tscv = TimeSeriesSplit(n_splits=n_splits)
    residuals = []
    for tr_idx, va_idx in tscv.split(X):
        try:
            model = model_factory()
            model.fit(X.iloc[tr_idx], y.iloc[tr_idx])
            pred = np.asarray(model.predict(X.iloc[va_idx])).ravel()
            residuals.extend(y.iloc[va_idx].values - pred)
        except Exception as e:
            print(f"[evaluation] Bias CV fold failed: {e}")
            continue
    return float(np.mean(residuals)) if residuals else 0.0


def estimate_bias_cv_univariate(fit_forecast, y, n_splits=3):
    """Univariate (SARIMA-style) bias estimate, also training-only.

    ``fit_forecast(y_train)`` must return a fitted object exposing
    ``.forecast(steps=n)``. SARIMA does not use exogenous features during
    forecasting, so this path evaluates on the target series alone.
    """
    y = pd.Series(np.asarray(y)).reset_index(drop=True)

    if len(y) < n_splits + 1:
        n_splits = max(1, len(y) // 2)

    tscv = TimeSeriesSplit(n_splits=n_splits)
    residuals = []
    for tr_idx, va_idx in tscv.split(y):
        try:
            fitted = fit_forecast(y.iloc[tr_idx])
            pred = np.asarray(fitted.forecast(steps=len(va_idx))).ravel()
            residuals.extend(y.iloc[va_idx].values - pred)
        except Exception as e:
            print(f"[evaluation] Univariate bias CV fold failed: {e}")
            continue
    return float(np.mean(residuals)) if residuals else 0.0


# ---------------------------------------------------------------------------
# WALK-FORWARD (rolling-origin) EVALUATION
# ---------------------------------------------------------------------------
def _plan_origins(n, horizon, n_origins):
    """Return the sorted list of training-window sizes to use as origins.

    Each origin leaves exactly ``horizon`` test points after it. The first
    origin keeps at least 50% of the series (or ``horizon`` when the series is
    very short), and origins are spread evenly toward the end.
    """
    horizon = max(1, int(horizon))
    n = int(n)
    if n <= horizon:
        return [0]

    max_start = n - horizon
    min_train = max(horizon, int(n * 0.5))
    min_train = min(min_train, max_start)

    if n_origins <= 1:
        return [max_start]

    starts = np.linspace(min_train, max_start, n_origins).astype(int)
    out = []
    for s in starts:
        s = int(s)
        if not out or s > out[-1]:
            out.append(s)
    if out[-1] != max_start:
        out.append(max_start)
    return out


def _agg_metric(values):
    """mean ± std over per-origin values (std = 0 when there is one origin)."""
    values = [v for v in values if v is not None and not (isinstance(v, float) and np.isnan(v))]
    if not values:
        return {"mean": None, "std": None}
    if len(values) == 1:
        return {"mean": float(values[0]), "std": 0.0}
    arr = np.asarray(values, dtype=float)
    return {
        "mean": float(arr.mean()),
        "std": float(arr.std(ddof=1)),
    }


def _walk_forward_accumulate(starts, horizon, season, y, model_predict, results):
    """Run the origins and fill ``results`` with model + baseline metrics."""
    for start in starts:
        y_tr, y_te = y.iloc[:start], y.iloc[start:start + horizon]
        try:
            pred = np.asarray(model_predict(y_tr, y_te)).ravel()
        except Exception as e:
            print(f"[evaluation] Walk-forward origin {start} failed: {e}")
            continue

        m = compute_metrics(y_te, pred)
        for k in results["model"]:
            results["model"][k].append(m[k])

        naive = naive_predictions(y_tr, len(y_te))
        s_naive = seasonal_naive_predictions(y, start, len(y_te), season)
        nm = compute_metrics(y_te, naive)
        sm = compute_metrics(y_te, s_naive)
        for k in results["naive"]:
            results["naive"][k].append(nm[k])
        for k in results["seasonal_naive"]:
            results["seasonal_naive"][k].append(sm[k])


def _summarize_walk_forward(results, starts, horizon):
    return {
        "model": {k: _agg_metric(v) for k, v in results["model"].items()},
        "naive": {k: _agg_metric(v) for k, v in results["naive"].items()},
        "seasonal_naive": {k: _agg_metric(v) for k, v in results["seasonal_naive"].items()},
        "origins": len(starts),
        "horizon": horizon,
    }


def walk_forward_eval(model_factory, X, y, n_origins=4, horizon=6, season=12):
    """Rolling-origin evaluation for sklearn-style regressors.

    ``model_factory`` returns an unfitted estimator (e.g. ``clone(model)``).
    The selected model is retrained on each train-only origin and compared to
    the actuals, together with Naive / Seasonal Naive baselines on the same
    windows — a fair, apples-to-apples benchmark for the defense.
    """
    X = X.reset_index(drop=True) if hasattr(X, "reset_index") else X
    y = pd.Series(np.asarray(y)).reset_index(drop=True)
    starts = _plan_origins(len(y), horizon, n_origins)

    results = {
        "model": {"mae": [], "rmse": [], "r2": [], "mape": []},
        "naive": {"mae": [], "rmse": [], "r2": [], "mape": []},
        "seasonal_naive": {"mae": [], "rmse": [], "r2": [], "mape": []},
    }

    def _predict(y_tr, y_te):
        model = model_factory()
        model.fit(X.iloc[:len(y_tr)], y_tr)
        return model.predict(X.iloc[len(y_tr):len(y_tr) + len(y_te)])

    _walk_forward_accumulate(starts, horizon, season, y, _predict, results)
    return _summarize_walk_forward(results, starts, horizon)


def walk_forward_eval_univariate(fit_forecast, y, n_origins=4, horizon=6, season=12):
    """Rolling-origin evaluation for univariate models (SARIMA).

    ``fit_forecast(y_train)`` returns a fitted object with ``.forecast(steps)``.
    """
    y = pd.Series(np.asarray(y)).reset_index(drop=True)
    starts = _plan_origins(len(y), horizon, n_origins)

    results = {
        "model": {"mae": [], "rmse": [], "r2": [], "mape": []},
        "naive": {"mae": [], "rmse": [], "r2": [], "mape": []},
        "seasonal_naive": {"mae": [], "rmse": [], "r2": [], "mape": []},
    }

    def _predict(y_tr, y_te):
        fitted = fit_forecast(y_tr)
        return fitted.forecast(steps=len(y_te))

    _walk_forward_accumulate(starts, horizon, season, y, _predict, results)
    return _summarize_walk_forward(results, starts, horizon)
