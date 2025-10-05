"""
Unit tests for mode_router module.
Tests regime-to-mode mapping logic.
"""

import unittest

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.regime_selector import Regime
from core.mode_router import Mode, get_mode_for_regime


class TestModeRouter(unittest.TestCase):
    """Test mode routing logic."""

    def test_bull_regime_maps_to_long_only(self):
        """Test that BULL regime maps to LONG_ONLY mode."""
        mode = get_mode_for_regime(Regime.BULL, simplified=False)
        self.assertEqual(mode, Mode.LONG_ONLY)

        mode_simplified = get_mode_for_regime(Regime.BULL, simplified=True)
        self.assertEqual(mode_simplified, Mode.LONG_ONLY)

    def test_recovery_regime_maps_to_long_only(self):
        """Test that RECOVERY regime maps to LONG_ONLY mode."""
        mode = get_mode_for_regime(Regime.RECOVERY, simplified=False)
        self.assertEqual(mode, Mode.LONG_ONLY)

        mode_simplified = get_mode_for_regime(Regime.RECOVERY, simplified=True)
        self.assertEqual(mode_simplified, Mode.LONG_ONLY)

    def test_bear_regime_maps_to_long_short(self):
        """Test that BEAR regime maps to LONG_SHORT by default."""
        mode = get_mode_for_regime(Regime.BEAR, simplified=False)
        self.assertEqual(mode, Mode.LONG_SHORT)

    def test_bear_regime_simplified_maps_to_short_only(self):
        """Test that BEAR regime maps to SHORT_ONLY when simplified=True."""
        mode = get_mode_for_regime(Regime.BEAR, simplified=True)
        self.assertEqual(mode, Mode.SHORT_ONLY)

    def test_all_regimes_covered(self):
        """Test that all regimes have a defined mode mapping."""
        for regime in Regime:
            mode_normal = get_mode_for_regime(regime, simplified=False)
            mode_simplified = get_mode_for_regime(regime, simplified=True)

            self.assertIsInstance(mode_normal, Mode)
            self.assertIsInstance(mode_simplified, Mode)


if __name__ == '__main__':
    unittest.main()
