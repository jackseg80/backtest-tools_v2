"""
Unit tests for params_registry module.
Tests parameter definitions and validation.
"""

import unittest

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.regime_selector import Regime
from core.params_registry import EnvelopeParams, DEFAULT_PARAMS, get_params_for_regime


class TestEnvelopeParams(unittest.TestCase):
    """Test EnvelopeParams dataclass."""

    def test_params_dataclass_creation(self):
        """Test creating EnvelopeParams instance."""
        params = EnvelopeParams(
            ma_base_window=7,
            envelope_std=0.10,
            tp_mult=2.0,
            sl_mult=1.0,
            trailing=0.7,
            position_size=0.06,
            allow_shorts=True,
            close_opposite_on_switch=True
        )

        self.assertEqual(params.ma_base_window, 7)
        self.assertEqual(params.envelope_std, 0.10)
        self.assertTrue(params.allow_shorts)
        self.assertTrue(params.close_opposite_on_switch)

    def test_params_optional_trailing(self):
        """Test that trailing can be None."""
        params = EnvelopeParams(
            ma_base_window=7,
            envelope_std=0.10,
            tp_mult=2.0,
            sl_mult=1.0,
            trailing=None,
            position_size=0.06,
            allow_shorts=True
        )

        self.assertIsNone(params.trailing)


class TestDefaultParams(unittest.TestCase):
    """Test DEFAULT_PARAMS registry."""

    def test_all_regimes_have_params(self):
        """Test that all regimes have defined parameters."""
        for regime in Regime:
            self.assertIn(regime, DEFAULT_PARAMS)
            params = DEFAULT_PARAMS[regime]
            self.assertIsInstance(params, EnvelopeParams)

    def test_bull_params_no_shorts(self):
        """Test that BULL regime disallows shorts."""
        params = DEFAULT_PARAMS[Regime.BULL]
        self.assertFalse(params.allow_shorts)

    def test_recovery_params_allow_shorts(self):
        """Test that RECOVERY regime allows shorts (bidirectional)."""
        params = DEFAULT_PARAMS[Regime.RECOVERY]
        self.assertTrue(params.allow_shorts)

    def test_bear_params_allow_shorts(self):
        """Test that BEAR regime allows shorts."""
        params = DEFAULT_PARAMS[Regime.BEAR]
        self.assertTrue(params.allow_shorts)

    def test_params_have_close_opposite_on_switch(self):
        """Test that all params have close_opposite_on_switch attribute."""
        for regime in Regime:
            params = DEFAULT_PARAMS[regime]
            self.assertTrue(hasattr(params, 'close_opposite_on_switch'))
            self.assertIsInstance(params.close_opposite_on_switch, bool)

    def test_params_ranges_valid(self):
        """Test that parameter values are in valid ranges."""
        for regime, params in DEFAULT_PARAMS.items():
            # Window should be positive
            self.assertGreater(params.ma_base_window, 0)

            # Envelope std should be positive and reasonable
            self.assertGreater(params.envelope_std, 0)
            self.assertLess(params.envelope_std, 1.0)  # Less than 100%

            # Multipliers should be positive
            self.assertGreater(params.tp_mult, 0)
            self.assertGreater(params.sl_mult, 0)

            # Trailing if set should be between 0 and 1
            if params.trailing is not None:
                self.assertGreaterEqual(params.trailing, 0)
                self.assertLessEqual(params.trailing, 1)

            # Position size should be reasonable
            self.assertGreater(params.position_size, 0)
            self.assertLessEqual(params.position_size, 1.0)

    def test_bear_tighter_than_bull(self):
        """Test that bear market has tighter envelope than bull."""
        bull_params = DEFAULT_PARAMS[Regime.BULL]
        bear_params = DEFAULT_PARAMS[Regime.BEAR]

        # Bear should have tighter envelope (lower std)
        self.assertLess(bear_params.envelope_std, bull_params.envelope_std)

    def test_get_params_for_regime_function(self):
        """Test get_params_for_regime helper function."""
        params = get_params_for_regime(Regime.BULL)
        self.assertEqual(params, DEFAULT_PARAMS[Regime.BULL])

        params = get_params_for_regime(Regime.BEAR)
        self.assertEqual(params, DEFAULT_PARAMS[Regime.BEAR])


if __name__ == '__main__':
    unittest.main()
