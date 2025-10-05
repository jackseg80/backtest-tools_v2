"""
Parameters registry for envelope strategies by market regime.

Defines strategy parameters (envelope width, TP/SL, position size, etc.)
optimized for different market regimes (bull, bear, recovery).
"""

from dataclasses import dataclass
from typing import Optional
from .regime_selector import Regime


@dataclass
class EnvelopeParams:
    """
    Strategy parameters for envelope-based trading.

    Attributes:
        ma_base_window: Moving average window for envelope calculation
        envelope_std: Envelope width (standard deviation or percentage)
        tp_mult: Take-profit multiplier (relative to envelope width)
        sl_mult: Stop-loss multiplier (relative to envelope width)
        trailing: Trailing stop percentage (0-1) or None to disable
        position_size: Position size as fraction of capital (e.g., 0.06 = 6%)
        allow_shorts: Whether short positions are allowed in this regime
        close_opposite_on_switch: Whether to close opposite positions when regime changes
                                 (e.g., close shorts when switching to LONG_ONLY mode)
    """
    ma_base_window: int
    envelope_std: float
    tp_mult: float
    sl_mult: float
    trailing: Optional[float]
    position_size: float
    allow_shorts: bool
    close_opposite_on_switch: bool = True


# Default parameters optimized for each regime
DEFAULT_PARAMS = {
    Regime.BULL: EnvelopeParams(
        ma_base_window=7,
        envelope_std=0.12,      # Wider bands to avoid noise in trending markets
        tp_mult=2.5,            # Generous take-profit
        sl_mult=1.2,            # Wider stop-loss
        trailing=0.8,           # 80% trailing stop
        position_size=0.06,     # 6% position size
        allow_shorts=False,     # No shorts in bull market
        close_opposite_on_switch=True
    ),

    Regime.RECOVERY: EnvelopeParams(
        ma_base_window=7,
        envelope_std=0.10,      # Intermediate width
        tp_mult=2.0,            # Moderate take-profit
        sl_mult=1.0,            # Tighter stop-loss (more volatility)
        trailing=0.7,           # 70% trailing stop
        position_size=0.06,     # 6% position size
        allow_shorts=True,      # Allow shorts (recovery = bidirectional)
        close_opposite_on_switch=True
    ),

    Regime.BEAR: EnvelopeParams(
        ma_base_window=7,
        envelope_std=0.07,      # Tighter bands to catch bear moves
        tp_mult=1.6,            # Smaller take-profit
        sl_mult=0.9,            # Tighter stop-loss
        trailing=0.6,           # 60% trailing stop
        position_size=0.06,     # 6% position size
        allow_shorts=True,      # Shorts allowed in bear market
        close_opposite_on_switch=True
    ),
}


def get_params_for_regime(regime: Regime) -> EnvelopeParams:
    """
    Get default parameters for a given regime.

    Args:
        regime: Market regime

    Returns:
        EnvelopeParams configured for the regime

    Example:
        >>> params = get_params_for_regime(Regime.BULL)
        >>> print(params.envelope_std)  # 0.12
    """
    return DEFAULT_PARAMS[regime]
