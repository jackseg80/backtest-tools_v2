"""
Smoke test runner for adaptive regime system.

Validates that regime detection, mode routing, and parameter selection
work correctly across different market periods.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from core import (
    Regime,
    Mode,
    calculate_regime_series,
    get_mode_for_regime,
    DEFAULT_PARAMS
)


def create_synthetic_btc_data(start_date: str, periods: int, regime_type: str) -> pd.DataFrame:
    """
    Create synthetic BTC data for testing.

    Args:
        start_date: Start date as string 'YYYY-MM-DD'
        periods: Number of daily bars
        regime_type: 'bull', 'bear', or 'recovery'

    Returns:
        DataFrame with close, ema50, ema200 columns
    """
    dates = pd.date_range(start_date, periods=periods, freq='1D')

    if regime_type == 'bull':
        # Strong uptrend
        close = pd.Series(10000 * (1.005 ** np.arange(periods)), index=dates)
    elif regime_type == 'bear':
        # Downtrend
        close = pd.Series(50000 * (0.996 ** np.arange(periods)), index=dates)
    else:  # recovery
        # Sideways with noise
        base = 30000
        noise = np.random.normal(0, 500, periods)
        close = pd.Series(base + noise, index=dates)

    # Calculate EMAs
    ema50 = close.rolling(50, min_periods=1).mean()
    ema200 = close.rolling(200, min_periods=1).mean()

    return pd.DataFrame({
        'close': close,
        'ema50': ema50,
        'ema200': ema200
    })


def run_smoke_test():
    """Run smoke test across different market regimes."""

    print("=" * 80)
    print("ADAPTIVE REGIME SYSTEM - SMOKE TEST")
    print("=" * 80)
    print()

    test_scenarios = [
        {
            'name': 'Bull Market 2020-2021',
            'start': '2020-01-01',
            'periods': 365,
            'type': 'bull',
            'expected_regime': Regime.BULL
        },
        {
            'name': 'Bear Market 2022',
            'start': '2022-01-01',
            'periods': 200,
            'type': 'bear',
            'expected_regime': Regime.BEAR
        },
        {
            'name': 'Recovery 2023',
            'start': '2023-01-01',
            'periods': 180,
            'type': 'recovery',
            'expected_regime': Regime.RECOVERY
        }
    ]

    results = []

    for scenario in test_scenarios:
        print(f"\nTesting: {scenario['name']}")
        print("-" * 80)

        # Create synthetic data
        df = create_synthetic_btc_data(
            scenario['start'],
            scenario['periods'],
            scenario['type']
        )

        # Detect regime
        regimes = calculate_regime_series(df, confirm_n=12)

        # Analyze results
        regime_counts = regimes.value_counts()
        dominant_regime = regimes.mode()[0]
        mode = get_mode_for_regime(dominant_regime, simplified=False)
        params = DEFAULT_PARAMS[dominant_regime]

        print(f"  Period: {df.index[0].date()} to {df.index[-1].date()} ({len(df)} days)")
        print(f"  Dominant Regime: {dominant_regime.value.upper()}")
        print(f"  Trading Mode: {mode.value}")
        print()
        print(f"  Regime Distribution:")
        for reg, count in regime_counts.items():
            pct = count / len(regimes) * 100
            print(f"    {reg.value.capitalize():10} {count:4d} bars ({pct:5.1f}%)")
        print()
        print(f"  Parameters:")
        print(f"    MA Window: {params.ma_base_window}")
        print(f"    Envelope Std: {params.envelope_std:.3f}")
        print(f"    TP Multiplier: {params.tp_mult:.1f}")
        print(f"    SL Multiplier: {params.sl_mult:.1f}")
        print(f"    Trailing Stop: {params.trailing:.1f}" if params.trailing else "    Trailing Stop: None")
        print(f"    Position Size: {params.position_size:.2%}")
        print(f"    Allow Shorts: {'Yes' if params.allow_shorts else 'No'}")
        print()

        # Validation
        success = (dominant_regime == scenario['expected_regime'])
        status = "[PASS]" if success else "[FAIL]"
        print(f"  Validation: {status}")

        if not success:
            print(f"    Expected {scenario['expected_regime'].value.upper()}, "
                  f"got {dominant_regime.value.upper()}")

        results.append({
            'scenario': scenario['name'],
            'expected': scenario['expected_regime'],
            'detected': dominant_regime,
            'success': success,
            'mode': mode,
            'params': params
        })

    # Summary
    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()

    total = len(results)
    passed = sum(1 for r in results if r['success'])
    failed = total - passed

    print(f"  Total Tests: {total}")
    print(f"  Passed: {passed}")
    print(f"  Failed: {failed}")
    print()

    if failed == 0:
        print("  All smoke tests passed successfully!")
    else:
        print("  WARNING: Some tests failed. Review the output above.")

    print()
    print("=" * 80)

    return passed == total


if __name__ == '__main__':
    success = run_smoke_test()
    sys.exit(0 if success else 1)
