"""
Regime transition handler for managing position changes during regime switches.

When market regime changes (e.g., BULL → BEAR), this module generates
orders to close positions that are no longer allowed in the new mode.
"""

from typing import List, Dict, Any
from .regime_selector import Regime
from .mode_router import Mode, get_mode_for_regime
from .params_registry import EnvelopeParams


def handle_regime_change(
    old_regime: Regime,
    new_regime: Regime,
    mode_simplified: bool,
    params: EnvelopeParams,
    open_positions: Dict[str, List[Dict[str, Any]]]
) -> List[Dict[str, Any]]:
    """
    Generate closing orders when regime changes and positions are no longer allowed.

    Args:
        old_regime: Previous market regime
        new_regime: New market regime
        mode_simplified: Whether to use simplified mode (SHORT_ONLY in bear instead of LONG_SHORT)
        params: Strategy parameters for the new regime (must have close_opposite_on_switch attribute)
        open_positions: Dictionary with structure:
            {
                'long': [{'id': str, ...}, ...],   # List of open long positions
                'short': [{'id': str, ...}, ...]   # List of open short positions
            }

    Returns:
        List of closing orders to execute, each with structure:
            {
                'action': 'close',
                'side': 'long' or 'short',
                'id': position_id,
                'reason': 'regime_switch_to_*'
            }

    Example:
        >>> positions = {
        ...     'long': [{'id': 'L1', 'size': 0.1}],
        ...     'short': [{'id': 'S1', 'size': 0.05}]
        ... }
        >>> params = DEFAULT_PARAMS[Regime.BULL]
        >>> orders = handle_regime_change(
        ...     Regime.BEAR, Regime.BULL, False, params, positions
        ... )
        >>> # Returns closing order for short position (not allowed in LONG_ONLY)

    Notes:
        - Only generates orders if params.close_opposite_on_switch is True
        - LONG_ONLY mode: closes all shorts
        - SHORT_ONLY mode: closes all longs
        - LONG_SHORT mode: no automatic closures (both sides allowed)
    """
    orders = []

    # Skip if automatic closing is disabled
    if not params.close_opposite_on_switch:
        return orders

    # Determine new trading mode
    new_mode = get_mode_for_regime(new_regime, simplified=mode_simplified)

    # Generate closing orders based on new mode restrictions
    if new_mode == Mode.LONG_ONLY:
        # Close all short positions (not allowed in LONG_ONLY)
        for pos in open_positions.get('short', []):
            orders.append({
                'action': 'close',
                'side': 'short',
                'id': pos['id'],
                'reason': 'regime_switch_to_long_only'
            })

    elif new_mode == Mode.SHORT_ONLY:
        # Close all long positions (not allowed in SHORT_ONLY)
        for pos in open_positions.get('long', []):
            orders.append({
                'action': 'close',
                'side': 'long',
                'id': pos['id'],
                'reason': 'regime_switch_to_short_only'
            })

    # LONG_SHORT mode allows both sides, no closing needed

    return orders
