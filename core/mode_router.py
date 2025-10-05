"""
Mode routing module to map market regimes to trading modes.

Determines whether to trade LONG_ONLY, LONG_SHORT, or SHORT_ONLY
based on the detected market regime.
"""

from enum import Enum
from .regime_selector import Regime


class Mode(str, Enum):
    """Trading mode classification."""
    LONG_ONLY = "LONG_ONLY"
    LONG_SHORT = "LONG_SHORT"
    SHORT_ONLY = "SHORT_ONLY"


def get_mode_for_regime(regime: Regime, simplified: bool = False) -> Mode:
    """
    Map market regime to appropriate trading mode.

    Mapping logic:
    - BULL → LONG_ONLY (no shorts in bull market)
    - RECOVERY → LONG_ONLY (wait for trend confirmation, no shorts)
    - BEAR → LONG_SHORT (default) or SHORT_ONLY (if simplified=True)

    Args:
        regime: Detected market regime
        simplified: If True, use SHORT_ONLY in bear markets instead of LONG_SHORT
                   (default False, allows both sides in bear)

    Returns:
        Trading mode (LONG_ONLY, LONG_SHORT, or SHORT_ONLY)

    Example:
        >>> mode = get_mode_for_regime(Regime.BULL)
        >>> print(mode)  # LONG_ONLY

        >>> mode = get_mode_for_regime(Regime.BEAR, simplified=True)
        >>> print(mode)  # SHORT_ONLY
    """
    if regime == Regime.BEAR:
        return Mode.SHORT_ONLY if simplified else Mode.LONG_SHORT

    # BULL and RECOVERY both use LONG_ONLY
    return Mode.LONG_ONLY
