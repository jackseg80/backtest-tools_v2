"""
Core modules for adaptive regime detection and routing.
"""

from .regime_selector import Regime, calculate_regime_series, slope_norm, prepare_regime_data
from .mode_router import Mode, get_mode_for_regime
from .params_registry import EnvelopeParams, DEFAULT_PARAMS
from .regime_transitions import handle_regime_change
from .params_adapter import (
    ParamsAdapter,
    FixedParamsAdapter,
    RegimeBasedAdapter,
    CustomAdapter
)
from .backtest_comparator import BacktestComparator

__all__ = [
    "Regime",
    "Mode",
    "EnvelopeParams",
    "DEFAULT_PARAMS",
    "calculate_regime_series",
    "prepare_regime_data",
    "slope_norm",
    "get_mode_for_regime",
    "handle_regime_change",
    "ParamsAdapter",
    "FixedParamsAdapter",
    "RegimeBasedAdapter",
    "CustomAdapter",
    "BacktestComparator",
]
