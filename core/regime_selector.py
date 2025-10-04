"""
Regime detection module for adaptive trading strategies.

Detects market regime (BULL, BEAR, RECOVERY) based on EMA crossovers and price action.
Uses hysteresis to prevent flip-flopping between regimes.
"""

from enum import Enum
import pandas as pd
import numpy as np
import ta


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


def prepare_regime_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Prepare dataframe for regime detection by calculating EMAs if missing.

    Args:
        df: DataFrame with at least 'close' column

    Returns:
        DataFrame with 'close', 'ema50', 'ema200' columns added

    Example:
        >>> df = exchange.load_data("BTC/USDT:USDT", "1h")
        >>> df_prepared = prepare_regime_data(df)
        >>> regime_series = calculate_regime_series(df_prepared)
    """
    df = df.copy()

    # Calculate EMAs if not present
    if 'ema50' not in df.columns:
        df['ema50'] = ta.trend.ema_indicator(df['close'], window=50)

    if 'ema200' not in df.columns:
        df['ema200'] = ta.trend.ema_indicator(df['close'], window=200)

    return df


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
                Must have datetime index. If EMAs missing, use prepare_regime_data() first.
        confirm_n: Number of consecutive bars required to confirm regime change
                   (default 12, adjust based on timeframe)

    Returns:
        Series[datetime -> Regime] with same index as df_btc

    Example:
        >>> df = exchange.load_data("BTC/USDT:USDT", "1h")
        >>> df = prepare_regime_data(df)  # Calculate EMAs if needed
        >>> regimes = calculate_regime_series(df, confirm_n=12)
        >>> print(regimes.value_counts())

    Notes:
        - First confirm_n-1 bars may use forward-fill from first valid detection
        - Use prepare_regime_data() to auto-calculate EMAs if missing
        - Hysteresis prevents rapid switching in choppy markets
    """
    # Auto-prepare if EMAs missing
    if 'ema50' not in df_btc.columns or 'ema200' not in df_btc.columns:
        df_btc = prepare_regime_data(df_btc)

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
