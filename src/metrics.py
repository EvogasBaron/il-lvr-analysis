"""
Financial and Econometric Metrics for Uniswap v3 Concentrated Liquidity.
Implements exact analytical formulas from:
- Adams et al. (2021), Uniswap v3 Core Whitepaper
- Heimbach, Schertenleib & Wattenhofer (2022), Risks and Returns of Uniswap V3 LPs
- Milionis, Moallemi, Roughgarden & Zhang (2022), Automated Market Making and Loss-Versus-Rebalancing (LVR)
"""
from typing import Dict, Optional, Tuple

import numpy as np
import pandas as pd


def compute_liquidity_for_capital(
    v0: float,
    p0: float,
    pa: float,
    pb: float,
) -> float:
    """
    Compute virtual liquidity L provided by initial capital `v0` (in numeraire units)
    at initial price `p0` for concentrated range `[pa, pb]` where `pa < pb`.
    """
    if pa <= 0 or pb <= 0 or pa >= pb:
        raise ValueError(f"Invalid price range: pa={pa}, pb={pb}. Must satisfy 0 < pa < pb.")
    if p0 <= 0:
        raise ValueError(f"Initial price p0 must be positive, got {p0}")

    sqrt_p0 = np.sqrt(p0)
    sqrt_pa = np.sqrt(pa)
    sqrt_pb = np.sqrt(pb)

    if p0 <= pa:
        denom = p0 * (1.0 / sqrt_pa - 1.0 / sqrt_pb)
    elif p0 >= pb:
        denom = sqrt_pb - sqrt_pa
    else:
        denom = 2.0 * sqrt_p0 - sqrt_pa - (p0 / sqrt_pb)

    if denom <= 0:
        raise ValueError("Non-positive denominator when computing liquidity L.")
    return float(v0 / denom)


def compute_token_amounts(
    liquidity: float,
    price: float | np.ndarray,
    pa: float,
    pb: float,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Compute token reserves (x, y) held by a Uniswap v3 position with liquidity `L`
    on range `[pa, pb]` at price(s) `price`.
    """
    p = np.asarray(price, dtype="float64")
    sqrt_p = np.sqrt(np.clip(p, 1e-18, None))
    sqrt_pa = np.sqrt(pa)
    sqrt_pb = np.sqrt(pb)

    x = np.where(
        p <= pa,
        liquidity * (1.0 / sqrt_pa - 1.0 / sqrt_pb),
        np.where(
            p >= pb,
            0.0,
            liquidity * (1.0 / sqrt_p - 1.0 / sqrt_pb),
        ),
    )
    y = np.where(
        p <= pa,
        0.0,
        np.where(
            p >= pb,
            liquidity * (sqrt_pb - sqrt_pa),
            liquidity * (sqrt_p - sqrt_pa),
        ),
    )
    return x, y


def compute_lp_and_hodl_values(
    price: float | np.ndarray,
    p0: float,
    pa: float,
    pb: float,
    v0: float = 1.0,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Compute `(V_LP(P), V_HODL(P))` at price(s) `price` given entry price `p0`,
    range `[pa, pb]`, and initial capital `v0`.
    Uses exact Uniswap v3 initial token inventory `(x0, y0)` at `p0`.
    """
    L = compute_liquidity_for_capital(v0=v0, p0=p0, pa=pa, pb=pb)
    x0, y0 = compute_token_amounts(L, p0, pa, pb)
    xt, yt = compute_token_amounts(L, price, pa, pb)

    p = np.asarray(price, dtype="float64")
    v_lp = xt * p + yt
    v_hodl = x0 * p + y0
    return v_lp, v_hodl


def compute_impermanent_loss(
    price: float | np.ndarray,
    p0: float,
    pa: float,
    pb: float,
    signed: bool = False,
) -> float | np.ndarray:
    """
    Compute concentrated liquidity Impermanent Loss (IL) relative to HODL:
      IL_signed = (V_LP(P) - V_HODL(P)) / V_HODL(P) <= 0
      IL_abs    = -IL_signed >= 0 (default when signed=False, representing loss magnitude)
    """
    v_lp, v_hodl = compute_lp_and_hodl_values(price=price, p0=p0, pa=pa, pb=pb, v0=1.0)
    il_signed = (v_lp - v_hodl) / np.maximum(v_hodl, 1e-18)
    il_signed = np.minimum(il_signed, 0.0)
    res = il_signed if signed else -il_signed
    if np.isscalar(price):
        return float(res)
    return res


def compute_uniswap_v2_il(price_ratio: float | np.ndarray, signed: bool = False) -> float | np.ndarray:
    """
    Standard full-range (Uniswap v2) Impermanent Loss for price ratio k = P_t / P_0:
      IL_v2_signed(k) = 2 * sqrt(k) / (1 + k) - 1 <= 0
    """
    k = np.asarray(price_ratio, dtype="float64")
    il_signed = (2.0 * np.sqrt(k)) / (1.0 + k) - 1.0
    res = il_signed if signed else -il_signed
    if np.isscalar(price_ratio):
        return float(res)
    return res


def compute_capital_efficiency(p0: float, pa: float, pb: float) -> float:
    """
    Compute capital efficiency factor eta >= 1 of concentrated range `[pa, pb]`
    relative to a full-range [0, inf) Uniswap v2 position at entry price `p0`:
      eta = L_v3(V0) / L_v2(V0) = (2 * sqrt(P0)) / (2 * sqrt(P0) - sqrt(Pa) - P0 / sqrt(Pb))
    """
    if not (pa < p0 < pb):
        raise ValueError(f"Entry price p0={p0} must lie strictly inside (pa={pa}, pb={pb})")
    l_v3 = compute_liquidity_for_capital(v0=1.0, p0=p0, pa=pa, pb=pb)
    l_v2 = 1.0 / (2.0 * np.sqrt(p0))
    return float(l_v3 / l_v2)


def compute_instantaneous_lvr(
    price: float | np.ndarray,
    sigma_hourly: float | np.ndarray,
    p0: float,
    pa: float,
    pb: float,
    v0: float = 1.0,
) -> float | np.ndarray:
    """
    Compute hourly Loss-Versus-Rebalancing (LVR, Milionis et al. 2022) normalized by initial capital `v0`.
    In continuous time:
      dLVR_t = 0.5 * sigma_t^2 * P_t^2 * |d^2 V_LP / dP^2| dt
    Since d^2 V_LP / dP^2 = -L / (2 * P^{3/2}) when Pa <= P <= Pb and 0 outside:
      LVR_step = 0.25 * L * sqrt(P_t) * sigma_hourly^2   (for Pa <= P_t <= Pb)
    Returns LVR_step / v0 >= 0.
    """
    L = compute_liquidity_for_capital(v0=v0, p0=p0, pa=pa, pb=pb)
    p = np.asarray(price, dtype="float64")
    sig = np.asarray(sigma_hourly, dtype="float64")

    in_range = (p >= pa) & (p <= pb)
    lvr_dollar = np.where(in_range, 0.25 * L * np.sqrt(np.maximum(p, 0.0)) * (sig ** 2), 0.0)
    res = lvr_dollar / v0
    if np.isscalar(price) and np.isscalar(sigma_hourly):
        return float(res)
    return res


def compute_position_raw_liquidity(
    v0_usd: float,
    p0: float,
    pa: float,
    pb: float,
    u0_usd: float,
    u1_usd: float,
    decimals0: int,
    decimals1: int,
) -> float:
    """
    Compute the exact on-chain raw Uniswap v3 liquidity `L_pos_raw` corresponding to a
    concentrated position of USD value `v0_usd` on range `[pa, pb]` at entry price `p0`:
      L_pos_raw = (v0_usd * eta(p0, pa, pb)) / (2 * sqrt(u0_usd * u1_usd)) * 10^((decimals0 + decimals1)/2)
    where `u0_usd` and `u1_usd` are the USD prices of 1 human token0 and 1 human token1.
    """
    eta = compute_capital_efficiency(p0=p0, pa=pa, pb=pb)
    denom = 2.0 * np.sqrt(max(u0_usd * u1_usd, 1e-18))
    l_human = (v0_usd * eta) / denom
    scale = 10.0 ** (0.5 * (decimals0 + decimals1))
    return float(l_human * scale)


def compute_hourly_fee_return(
    price: float | np.ndarray,
    pool_fees_usd: float | np.ndarray,
    pool_tvl_usd: float | np.ndarray,
    p0: float,
    pa: float,
    pb: float,
    pool_liquidity_raw: Optional[float | np.ndarray] = None,
    v0_usd: float = 10000.0,
    u0_usd: float = 1.0,
    u1_usd: float = 1.0,
    decimals0: int = 18,
    decimals1: int = 18,
) -> np.ndarray:
    """
    Compute hourly fee return (as a fraction of initial capital `v0_usd`) earned by a concentrated LP position.
    When `pool_liquidity_raw` is provided (from Subgraph `PoolHourData.liquidity`), computes the exact
    pro-rata share of active on-chain liquidity:
      fee_usd_t = feesUSD_t * (L_pos_raw / (L_pool_raw_t + L_pos_raw))   if Pa <= P_t <= Pb else 0
      fee_return_t = fee_usd_t / v0_usd
    """
    p = np.asarray(price, dtype="float64")
    fees = np.asarray(pool_fees_usd, dtype="float64")
    in_range = (p >= pa) & (p <= pb)

    if pool_liquidity_raw is not None:
        l_pool = np.asarray(pool_liquidity_raw, dtype="float64")
        l_pos = compute_position_raw_liquidity(
            v0_usd=v0_usd,
            p0=p0,
            pa=pa,
            pb=pb,
            u0_usd=u0_usd,
            u1_usd=u1_usd,
            decimals0=decimals0,
            decimals1=decimals1,
        )
        share = np.where(l_pool > 0, l_pos / (l_pool + l_pos), 0.0)
        fee_usd = np.where(in_range, fees * share, 0.0)
        return fee_usd / v0_usd

    tvl = np.maximum(np.asarray(pool_tvl_usd, dtype="float64"), 1.0)
    eta = compute_capital_efficiency(p0=p0, pa=pa, pb=pb)
    return np.where(in_range, (fees / tvl) * eta, 0.0)


def compute_max_drawdown(wealth_series: pd.Series | np.ndarray) -> float:
    """
    Compute Maximum Drawdown (MDD >= 0) of a positive wealth/value trajectory:
      MDD = max_t ((Peak_t - W_t) / Peak_t)
    """
    w = np.asarray(wealth_series, dtype="float64")
    if len(w) == 0:
        return 0.0
    peaks = np.maximum.accumulate(w)
    drawdowns = (peaks - w) / np.maximum(peaks, 1e-18)
    return float(np.max(drawdowns))


def compute_var_cvar(loss_series: pd.Series | np.ndarray, alpha: float = 0.95) -> Tuple[float, float]:
    """
    Compute historical Value-at-Risk (VaR_alpha) and Conditional Value-at-Risk (CVaR_alpha / Expected Shortfall)
    for a loss distribution `loss_series` (where larger positive values mean larger losses).
    """
    losses = np.asarray(loss_series, dtype="float64")
    losses = losses[~np.isnan(losses)]
    if len(losses) == 0:
        return 0.0, 0.0
    var_alpha = float(np.quantile(losses, alpha))
    tail = losses[losses >= var_alpha]
    cvar_alpha = float(np.mean(tail)) if len(tail) > 0 else var_alpha
    return var_alpha, cvar_alpha


def compute_sharpe_sortino(
    hourly_returns: pd.Series | np.ndarray,
    periods_per_year: float = 24.0 * 365.0,
) -> Dict[str, float]:
    """Compute annualized Sharpe and Sortino ratios from hourly net return series."""
    r = np.asarray(hourly_returns, dtype="float64")
    r = r[~np.isnan(r)]
    if len(r) < 2:
        return {"sharpe": 0.0, "sortino": 0.0}

    mean_r = float(np.mean(r))
    std_r = float(np.std(r, ddof=1))
    downside = r[r < 0.0]
    downside_std = float(np.sqrt(np.mean(np.square(downside)))) if len(downside) > 0 else 1e-12

    sharpe = (mean_r / std_r) * np.sqrt(periods_per_year) if std_r > 1e-12 else 0.0
    sortino = (mean_r / downside_std) * np.sqrt(periods_per_year) if downside_std > 1e-12 else 0.0
    return {"sharpe": float(sharpe), "sortino": float(sortino)}
