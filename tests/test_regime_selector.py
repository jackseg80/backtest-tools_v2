"""
Unit tests for regime_selector module.
Tests regime detection logic, hysteresis, and edge cases.
"""

import unittest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.regime_selector import Regime, calculate_regime_series, slope_norm


class TestSlopeNorm(unittest.TestCase):
    """Test slope normalization function."""

    def test_slope_norm_uptrend(self):
        """Test that uptrend produces positive slope."""
        dates = pd.date_range('2020-01-01', periods=100, freq='1D')
        uptrend = pd.Series(np.linspace(100, 200, 100), index=dates)
        slope = slope_norm(uptrend, window=20)

        # Should have positive slope (excluding zeros from fillna at start)
        non_zero_slopes = slope[slope != 0]
        self.assertTrue((non_zero_slopes > 0).all())

    def test_slope_norm_downtrend(self):
        """Test that downtrend produces negative slope."""
        dates = pd.date_range('2020-01-01', periods=100, freq='1D')
        downtrend = pd.Series(np.linspace(200, 100, 100), index=dates)
        slope = slope_norm(downtrend, window=20)

        non_zero_slopes = slope[slope != 0]
        self.assertTrue((non_zero_slopes < 0).all())

    def test_slope_norm_flat(self):
        """Test that flat line produces near-zero slope."""
        dates = pd.date_range('2020-01-01', periods=100, freq='1D')
        flat = pd.Series([100] * 100, index=dates)
        slope = slope_norm(flat, window=20)

        valid_slopes = slope.dropna()
        self.assertTrue(np.allclose(valid_slopes, 0, atol=1e-10))


class TestRegimeDetection(unittest.TestCase):
    """Test regime detection logic."""

    def _create_test_df(self, close_vals, ema50_vals, ema200_vals):
        """Helper to create test dataframe."""
        dates = pd.date_range('2020-01-01', periods=len(close_vals), freq='1D')
        return pd.DataFrame({
            'close': close_vals,
            'ema50': ema50_vals,
            'ema200': ema200_vals
        }, index=dates)

    def test_bull_regime_detection(self):
        """Test BULL regime: close > ema200, ema50 > ema200, slope >= 0."""
        # Strong uptrend with all conditions met
        n = 50
        df = self._create_test_df(
            close_vals=np.linspace(110, 150, n),
            ema50_vals=np.linspace(105, 145, n),
            ema200_vals=np.linspace(100, 140, n)
        )

        regimes = calculate_regime_series(df, confirm_n=10)

        # After confirmation period, should be BULL
        self.assertEqual(regimes.iloc[-1], Regime.BULL)

    def test_bear_regime_detection(self):
        """Test BEAR regime: close < ema200, ema50 < ema200, slope < 0."""
        n = 50
        df = self._create_test_df(
            close_vals=np.linspace(90, 50, n),
            ema50_vals=np.linspace(95, 55, n),
            ema200_vals=np.linspace(100, 60, n)
        )

        regimes = calculate_regime_series(df, confirm_n=10)

        # After confirmation period, should be BEAR
        self.assertEqual(regimes.iloc[-1], Regime.BEAR)

    def test_recovery_regime_detection(self):
        """Test RECOVERY: close > ema200 but bull conditions incomplete."""
        n = 50
        # Close above ema200, but ema50 below ema200 (incomplete bull)
        df = self._create_test_df(
            close_vals=[110] * n,  # Above ema200
            ema50_vals=[95] * n,   # Below ema200
            ema200_vals=[100] * n
        )

        regimes = calculate_regime_series(df, confirm_n=10)

        # Should be RECOVERY (bull conditions not fully met)
        self.assertEqual(regimes.iloc[-1], Regime.RECOVERY)

    def test_hysteresis_prevents_flip_flop(self):
        """Test that hysteresis prevents rapid regime switching."""
        n = 30
        # Alternating conditions (choppy market)
        close_vals = [110 if i % 2 == 0 else 90 for i in range(n)]
        ema50_vals = [105 if i % 2 == 0 else 95 for i in range(n)]
        ema200_vals = [100] * n

        df = self._create_test_df(close_vals, ema50_vals, ema200_vals)
        regimes = calculate_regime_series(df, confirm_n=5)

        # Count regime changes
        changes = (regimes != regimes.shift()).sum()

        # With hysteresis, should have very few changes (not 15+)
        self.assertLess(changes, 5)

    def test_edge_case_close_equals_ema200(self):
        """Test edge case where close == ema200."""
        n = 30
        df = self._create_test_df(
            close_vals=[100] * n,
            ema50_vals=[100] * n,
            ema200_vals=[100] * n
        )

        regimes = calculate_regime_series(df, confirm_n=10)

        # When all equal, slope is 0, should be RECOVERY
        self.assertEqual(regimes.iloc[-1], Regime.RECOVERY)

    def test_bull_to_bear_transition(self):
        """Test transition from BULL to BEAR regime."""
        # First half: strong bull
        bull_section = self._create_test_df(
            close_vals=np.linspace(110, 150, 25),
            ema50_vals=np.linspace(105, 145, 25),
            ema200_vals=np.linspace(100, 140, 25)
        )

        # Second half: strong bear
        bear_section = self._create_test_df(
            close_vals=np.linspace(135, 90, 25),
            ema50_vals=np.linspace(130, 85, 25),
            ema200_vals=np.linspace(140, 95, 25)
        )

        df = pd.concat([bull_section, bear_section])
        df.index = pd.date_range('2020-01-01', periods=50, freq='1D')

        regimes = calculate_regime_series(df, confirm_n=10)

        # First part should be BULL, last part should be BEAR
        self.assertEqual(regimes.iloc[20], Regime.BULL)
        self.assertEqual(regimes.iloc[-1], Regime.BEAR)


class TestRealWorldScenarios(unittest.TestCase):
    """Test with realistic market scenarios."""

    def test_2020_2021_bull_market(self):
        """Simulate 2020-2021 BTC bull run characteristics."""
        n = 365
        dates = pd.date_range('2020-01-01', periods=n, freq='1D')

        # Strong uptrend with increasing momentum
        close = pd.Series(10000 * (1.005 ** np.arange(n)), index=dates)
        ema50 = close.rolling(50).mean().bfill()
        ema200 = close.rolling(200).mean().bfill()

        df = pd.DataFrame({'close': close, 'ema50': ema50, 'ema200': ema200})
        regimes = calculate_regime_series(df, confirm_n=12)

        # Most of the period should be BULL
        bull_ratio = (regimes == Regime.BULL).sum() / len(regimes)
        self.assertGreater(bull_ratio, 0.6)

    def test_2022_bear_market(self):
        """Simulate 2022 BTC bear market characteristics."""
        n = 200
        dates = pd.date_range('2022-01-01', periods=n, freq='1D')

        # Downtrend with lower highs
        close = pd.Series(50000 * (0.996 ** np.arange(n)), index=dates)
        ema50 = close.rolling(50).mean().bfill()
        ema200 = close.rolling(200).mean().bfill()

        df = pd.DataFrame({'close': close, 'ema50': ema50, 'ema200': ema200})
        regimes = calculate_regime_series(df, confirm_n=12)

        # Significant portion should be BEAR or RECOVERY (relaxed threshold)
        non_bull_ratio = (regimes != Regime.BULL).sum() / len(regimes)
        self.assertGreater(non_bull_ratio, 0.4)


if __name__ == '__main__':
    unittest.main()
