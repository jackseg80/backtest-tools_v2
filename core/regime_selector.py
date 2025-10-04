"""
Regime detection module for adaptive trading strategies.

Detects market regime (BULL, BEAR, RECOVERY) based on EMA crossovers and price action.
Uses hysteresis to prevent flip-flopping between regimes.
"""

from enum import Enum
import pandas as pd
import numpy as np


class Regime(str, Enum):
    """Market regime classification."""
    BULL = "bull"
    BEAR = "bear"
    RECOVERY = "recovery"


def slope_norm(series: pd.Series, window: int = 20) -> pd.Series:
    """
    Calculate normalized slope of a series to detect trends.

    The slope is normalized by the series value to make it scale-independent,
    avoiding sensitivity to absolute volatility.

    Args:
        series: Price or indicator series
        window: Lookback window for slope calculation (default 20)

    Returns:
        Series of normalized slopes (percentage change per period)

    Notes:
        - Uses window-period difference instead of single-period diff for smoother results
        - Normalizes by series value to get relative slope
        - Fills NaN values with 0.0
    """
    raw_slope = series.diff(window) / window
    normalized = (raw_slope / series).fillna(0.0)
    return normalized


def calculate_regime_series(
    df_btc: pd.DataFrame,
    confirm_n: int = 12
) -> pd.Series:
    """
    Calculate market regime for each timestamp in the dataframe.

    Uses BTC as global market proxy. Regime is determined by:
    - BULL: close > ema200 AND ema50 > ema200 AND slope(ema200) >= 0
    - BEAR: close < ema200 AND ema50 < ema200 AND slope(ema200) < 0
    - RECOVERY: Otherwise (e.g., close > ema200 but bull conditions incomplete)

    Applies hysteresis: regime change requires confirm_n consecutive bars
    confirming the new regime to prevent flip-flopping.

    Args:
        df_btc: DataFrame with columns ['close', 'ema50', 'ema200']
                Must have datetime index
        confirm_n: Number of consecutive bars required to confirm regime change
                   (default 12, adjust based on timeframe)

    Returns:
        Series[datetime -> Regime] with same index as df_btc

    Example:
        >>> df = df_btc[['close', 'ema50', 'ema200']].copy()
        >>> regimes = calculate_regime_series(df, confirm_n=12)
        >>> print(regimes.value_counts())

    Notes:
        - First confirm_n-1 bars may use forward-fill from first valid detection
        - Requires pre-calculated EMA50 and EMA200 in df_btc
        - Hysteresis prevents rapid switching in choppy markets
    """
    # Extract required columns
    close = df_btc["close"]
    ema50 = df_btc["ema50"]
    ema200 = df_btc["ema200"]

    # Calculate normalized slope of EMA200
    slope = slope_norm(ema200, window=20)

    # Define regime conditions
    cond_bull = (close > ema200) & (ema50 > ema200) & (slope >= 0)
    cond_bear = (close < ema200) & (ema50 < ema200) & (slope < 0)

    # Initial classification (no hysteresis yet)
    raw_regime = pd.Series(Regime.RECOVERY, index=df_btc.index)
    raw_regime[cond_bull] = Regime.BULL
    raw_regime[cond_bear] = Regime.BEAR

    # Apply hysteresis: regime change requires confirm_n consecutive confirmations
    regime = raw_regime.copy()
    last_regime = regime.iloc[0]

    for i in range(len(raw_regime)):
        current_raw = raw_regime.iloc[i]

        # Check if we have enough history to validate a regime change
        if i >= confirm_n - 1:
            # Count consecutive bars of the new regime
            window_start = i - confirm_n + 1
            window = raw_regime.iloc[window_start:i+1]

            # Regime change validated if all confirm_n bars agree
            if (window == current_raw).all():
                last_regime = current_raw

        # Apply validated regime (or keep previous if not confirmed)
        regime.iloc[i] = last_regime

    return regime
