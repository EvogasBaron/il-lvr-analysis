"""
Evaluation Metrics and Statistical Tests for Point, Quantile, and Probability Forecasts.
Includes:
- Pinball Loss, Empirical Quantile Coverage, Brier Score
- Split Conformal Quantile Calibration (fit strictly on Validation set)
- Diebold-Mariano (DM) Test with Bartlett Newey-West HAC variance up to lag `h - 1`
  and Harvey-Leybourne-Newbold (1997) finite-sample adjustment.
"""
from typing import Dict, Tuple

import numpy as np
from scipy import stats


def compute_point_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    """Compute RMSE, MAE, and R2 for point predictions."""
    yt = np.asarray(y_true, dtype="float64")
    yp = np.asarray(y_pred, dtype="float64")
    mask = ~(np.isnan(yt) | np.isnan(yp))
    yt, yp = yt[mask], yp[mask]
    if len(yt) == 0:
        return {"rmse": np.nan, "mae": np.nan, "r2": np.nan}

    err = yt - yp
    mse = float(np.mean(np.square(err)))
    rmse = float(np.sqrt(mse))
    mae = float(np.mean(np.abs(err)))
    ss_tot = float(np.sum(np.square(yt - np.mean(yt))))
    r2 = float(1.0 - np.sum(np.square(err)) / ss_tot) if ss_tot > 1e-18 else 0.0
    return {"rmse": rmse, "mae": mae, "r2": r2}


def pinball_loss(y_true: np.ndarray, y_quantile_pred: np.ndarray, alpha: float) -> float:
    """
    Compute Pinball Loss (Check Loss) for quantile `alpha in (0, 1)`:
      L_alpha(y, q) = max(alpha * (y - q), (alpha - 1) * (y - q))
    """
    yt = np.asarray(y_true, dtype="float64")
    yq = np.asarray(y_quantile_pred, dtype="float64")
    mask = ~(np.isnan(yt) | np.isnan(yq))
    diff = yt[mask] - yq[mask]
    if len(diff) == 0:
        return np.nan
    loss = np.maximum(alpha * diff, (alpha - 1.0) * diff)
    return float(np.mean(loss))


def empirical_quantile_coverage(y_true: np.ndarray, y_quantile_pred: np.ndarray) -> float:
    """Compute empirical fraction of observations where `y_true <= y_quantile_pred`."""
    yt = np.asarray(y_true, dtype="float64")
    yq = np.asarray(y_quantile_pred, dtype="float64")
    mask = ~(np.isnan(yt) | np.isnan(yq))
    if np.sum(mask) == 0:
        return np.nan
    return float(np.mean(yt[mask] <= yq[mask]))


def conformal_calibrate_quantile(
    y_val: np.ndarray,
    q_val_pred: np.ndarray,
    q_test_pred: np.ndarray,
    alpha: float,
) -> Tuple[np.ndarray, float]:
    """
    Split Conformal Quantile Regression (CQR) calibration:
    Computes conformity scores `r_val = y_val - q_val_pred` strictly on the Validation set,
    finds the finite-sample quantile offset `delta_alpha`, and shifts `q_test_pred` by `delta_alpha`.
    Never touches `y_test`.
    """
    yv = np.asarray(y_val, dtype="float64")
    qv = np.asarray(q_val_pred, dtype="float64")
    qt = np.asarray(q_test_pred, dtype="float64")
    mask = ~(np.isnan(yv) | np.isnan(qv))
    residuals = yv[mask] - qv[mask]
    if len(residuals) < 5:
        return np.clip(qt, 0.0, None), 0.0

    n_val = len(residuals)
    level = min(0.995, float(alpha) * (1.0 + 1.0 / n_val))
    delta = float(np.quantile(residuals, level))
    calibrated_test = np.clip(qt + delta, 0.0, None)
    return calibrated_test, delta


def brier_score(y_binary_true: np.ndarray, y_prob_pred: np.ndarray) -> float:
    """Compute Brier Score for binary exceedance probability predictions."""
    yt = np.asarray(y_binary_true, dtype="float64")
    yp = np.clip(np.asarray(y_prob_pred, dtype="float64"), 0.0, 1.0)
    mask = ~(np.isnan(yt) | np.isnan(yp))
    if np.sum(mask) == 0:
        return np.nan
    return float(np.mean(np.square(yt[mask] - yp[mask])))


def diebold_mariano_test(
    y_true: np.ndarray,
    pred_model: np.ndarray,
    pred_benchmark: np.ndarray,
    horizon_lags: int = 1,
    loss_type: str = "squared",
) -> Dict[str, float]:
    """
    Diebold-Mariano test comparing predictive accuracy of `pred_model` vs `pred_benchmark`.
    Uses loss differential `d_t = L(e_benchmark, t) - L(e_model, t)` so that:
      - `dm_stat > 0` means `pred_model` has LOWER loss (better accuracy) than `pred_benchmark`.
    Applies Bartlett Newey-West HAC covariance up to lag `min(horizon_lags - 1, n // 3)`
    AND the Harvey, Leybourne & Newbold (1997) finite-sample adjustment.
    """
    yt = np.asarray(y_true, dtype="float64")
    pm = np.asarray(pred_model, dtype="float64")
    pb = np.asarray(pred_benchmark, dtype="float64")
    mask = ~(np.isnan(yt) | np.isnan(pm) | np.isnan(pb))
    yt, pm, pb = yt[mask], pm[mask], pb[mask]
    n = len(yt)
    n_eff = max(1, int(n // max(horizon_lags, 1)))
    err_m = yt - pm
    err_b = yt - pb
    if loss_type == "squared":
        d = (err_b ** 2) - (err_m ** 2)
    else:
        d = np.abs(err_b) - np.abs(err_m)

    d_bar = float(np.mean(d)) if n > 0 else 0.0
    # Guard against under-powered long-horizon splits: require at least 10 independent non-overlapping observations
    if n < 10 or n_eff < 10:
        return {"dm_stat": float("nan"), "p_value": float("nan"), "mean_loss_diff": d_bar, "n_eff": n_eff}

    d_centered = d - d_bar

    # Full overlapping horizon lag bandwidth with Bartlett weights to guarantee positive semi-definiteness
    max_lag = min(max(1, int(horizon_lags) - 1), max(1, n // 3))
    gamma_0 = float(np.sum(d_centered ** 2) / n)
    var_d = gamma_0
    for k in range(1, max_lag + 1):
        weight = 1.0 - k / (max_lag + 1.0)
        gamma_k = float(np.sum(d_centered[k:] * d_centered[:-k]) / n)
        var_d += 2.0 * weight * gamma_k

    var_d = max(var_d, 1e-24)
    dm_raw = d_bar / np.sqrt(var_d / n)

    # Harvey, Leybourne & Newbold (1997) small-sample factor
    h_eff = min(max(1, int(horizon_lags)), max(1, n // 3))
    hln_num = n + 1.0 - 2.0 * h_eff + (h_eff * (h_eff - 1.0)) / n
    hln_factor = float(np.sqrt(max(0.10, hln_num / n)))
    dm_hln = float(dm_raw * hln_factor)

    df_t = max(1, n - 1)
    p_value = float(2.0 * (1.0 - stats.t.cdf(abs(dm_hln), df=df_t)))
    return {
        "dm_stat": dm_hln,
        "p_value": p_value,
        "mean_loss_diff": d_bar,
        "n_eff": n_eff,
    }
