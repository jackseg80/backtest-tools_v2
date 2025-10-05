"""
Unit tests for regime_transitions module.
Tests position closing logic during regime changes.
"""

import unittest

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.regime_selector import Regime
from core.params_registry import DEFAULT_PARAMS
from core.regime_transitions import handle_regime_change


class TestRegimeTransitions(unittest.TestCase):
    """Test regime transition handling."""

    def test_bull_to_bear_closes_shorts_in_simplified_mode(self):
        """Test that switching to SHORT_ONLY closes long positions."""
        old_regime = Regime.BULL
        new_regime = Regime.BEAR
        params = DEFAULT_PARAMS[new_regime]

        open_positions = {
            'long': [{'id': 'L1', 'size': 0.1}],
            'short': []
        }

        # In simplified mode, BEAR → SHORT_ONLY
        orders = handle_regime_change(
            old_regime, new_regime, mode_simplified=True, params=params, open_positions=open_positions
        )

        # Should close the long position
        self.assertEqual(len(orders), 1)
        self.assertEqual(orders[0]['action'], 'close')
        self.assertEqual(orders[0]['side'], 'long')
        self.assertEqual(orders[0]['id'], 'L1')

    def test_bear_to_bull_closes_shorts(self):
        """Test that switching to LONG_ONLY closes short positions."""
        old_regime = Regime.BEAR
        new_regime = Regime.BULL
        params = DEFAULT_PARAMS[new_regime]

        open_positions = {
            'long': [],
            'short': [{'id': 'S1', 'size': 0.05}, {'id': 'S2', 'size': 0.03}]
        }

        orders = handle_regime_change(
            old_regime, new_regime, mode_simplified=False, params=params, open_positions=open_positions
        )

        # Should close both short positions
        self.assertEqual(len(orders), 2)
        self.assertTrue(all(o['action'] == 'close' for o in orders))
        self.assertTrue(all(o['side'] == 'short' for o in orders))

    def test_long_short_mode_no_closures(self):
        """Test that LONG_SHORT mode doesn't force closures."""
        old_regime = Regime.BULL
        new_regime = Regime.BEAR
        params = DEFAULT_PARAMS[new_regime]

        open_positions = {
            'long': [{'id': 'L1', 'size': 0.1}],
            'short': [{'id': 'S1', 'size': 0.05}]
        }

        # In normal mode, BEAR → LONG_SHORT (allows both)
        orders = handle_regime_change(
            old_regime, new_regime, mode_simplified=False, params=params, open_positions=open_positions
        )

        # LONG_SHORT allows both sides, no closures
        self.assertEqual(len(orders), 0)

    def test_close_opposite_on_switch_disabled(self):
        """Test that no closures occur if close_opposite_on_switch=False."""
        from dataclasses import replace

        old_regime = Regime.BEAR
        new_regime = Regime.BULL

        # Create params with close_opposite_on_switch=False (using dataclass replace)
        base_params = DEFAULT_PARAMS[new_regime]
        params = replace(base_params, close_opposite_on_switch=False)

        open_positions = {
            'long': [],
            'short': [{'id': 'S1', 'size': 0.05}]
        }

        orders = handle_regime_change(
            old_regime, new_regime, mode_simplified=False, params=params, open_positions=open_positions
        )

        # No closures when flag is disabled
        self.assertEqual(len(orders), 0)

    def test_empty_positions(self):
        """Test handling when no positions are open."""
        old_regime = Regime.BULL
        new_regime = Regime.BEAR
        params = DEFAULT_PARAMS[new_regime]

        open_positions = {'long': [], 'short': []}

        orders = handle_regime_change(
            old_regime, new_regime, mode_simplified=True, params=params, open_positions=open_positions
        )

        # No positions to close
        self.assertEqual(len(orders), 0)

    def test_recovery_to_bull_closes_shorts(self):
        """Test RECOVERY → BULL transition closes shorts."""
        old_regime = Regime.RECOVERY
        new_regime = Regime.BULL
        params = DEFAULT_PARAMS[new_regime]

        open_positions = {
            'long': [{'id': 'L1', 'size': 0.1}],
            'short': [{'id': 'S1', 'size': 0.05}]
        }

        orders = handle_regime_change(
            old_regime, new_regime, mode_simplified=False, params=params, open_positions=open_positions
        )

        # BULL → LONG_ONLY: should close shorts but keep longs
        self.assertEqual(len(orders), 1)
        self.assertEqual(orders[0]['side'], 'short')

    def test_order_structure(self):
        """Test that closing orders have correct structure."""
        old_regime = Regime.BEAR
        new_regime = Regime.BULL
        params = DEFAULT_PARAMS[new_regime]

        open_positions = {
            'long': [],
            'short': [{'id': 'S1', 'size': 0.05}]
        }

        orders = handle_regime_change(
            old_regime, new_regime, mode_simplified=False, params=params, open_positions=open_positions
        )

        order = orders[0]
        self.assertIn('action', order)
        self.assertIn('side', order)
        self.assertIn('id', order)
        self.assertIn('reason', order)

        self.assertEqual(order['action'], 'close')
        self.assertIn('regime_switch', order['reason'])


if __name__ == '__main__':
    unittest.main()
