"""
Tests unitaires pour le module margin.py
=========================================

Tests des fonctions critiques :
1. compute_liq_price() - Prix de liquidation
2. update_equity() - Calcul de l'equity
3. apply_close() - Fermeture avec fees
4. check_exposure_caps() - Vérification des caps d'exposition
5. KillSwitch - Pause trading sur drawdown
"""

import sys
sys.path.append('..')

import pytest
from utilities.margin import (
    compute_liq_price,
    update_equity,
    apply_close,
    check_exposure_caps,
    get_mmr,
    KillSwitch
)
import pandas as pd


# ============================================================================
# Tests compute_liq_price()
# ============================================================================

def test_liq_price_long_100x():
    """Test 1: LONG 100x, MMR 0.5% → liquidation à ~-0.5% du prix d'entrée"""
    entry = 50000
    liq = compute_liq_price(entry, "LONG", leverage=100, mmr=0.005)

    # Formula: entry * (1 - 1/100 + 0.005) = 50000 * (1 - 0.01 + 0.005) = 50000 * 0.995
    expected = 50000 * 0.995
    assert abs(liq - expected) < 1, f"Expected {expected}, got {liq}"

    # Vérification : une baisse de ~0.5% touche la liquidation
    pct_to_liq = (liq - entry) / entry * 100
    assert -0.6 < pct_to_liq < -0.4, f"Liquidation devrait être à ~-0.5%, got {pct_to_liq:.2f}%"


def test_liq_price_long_10x():
    """Test 2: LONG 10x, MMR 0.5% → liquidation à ~-9.5% du prix d'entrée"""
    entry = 50000
    liq = compute_liq_price(entry, "LONG", leverage=10, mmr=0.005)

    # Formula: entry * (1 - 1/10 + 0.005) = 50000 * (1 - 0.1 + 0.005) = 50000 * 0.905
    expected = 50000 * 0.905
    assert abs(liq - expected) < 1, f"Expected {expected}, got {liq}"

    pct_to_liq = (liq - entry) / entry * 100
    assert -9.6 < pct_to_liq < -9.4, f"Liquidation devrait être à ~-9.5%, got {pct_to_liq:.2f}%"


def test_liq_price_short_100x():
    """Test 3: SHORT 100x, MMR 0.5% → liquidation à ~+0.5% du prix d'entrée"""
    entry = 50000
    liq = compute_liq_price(entry, "SHORT", leverage=100, mmr=0.005)

    # Formula: entry * (1 + 1/100 - 0.005) = 50000 * 1.005
    expected = 50000 * 1.005
    assert abs(liq - expected) < 1, f"Expected {expected}, got {liq}"

    pct_to_liq = (liq - entry) / entry * 100
    assert 0.4 < pct_to_liq < 0.6, f"Liquidation devrait être à ~+0.5%, got {pct_to_liq:.2f}%"


def test_liq_price_short_10x():
    """Test 4: SHORT 10x, MMR 0.5% → liquidation à ~+9.5%"""
    entry = 50000
    liq = compute_liq_price(entry, "SHORT", leverage=10, mmr=0.005)

    expected = 50000 * 1.095
    assert abs(liq - expected) < 1, f"Expected {expected}, got {liq}"

    pct_to_liq = (liq - entry) / entry * 100
    assert 9.4 < pct_to_liq < 9.6, f"Liquidation devrait être à ~+9.5%, got {pct_to_liq:.2f}%"


# ============================================================================
# Tests update_equity()
# ============================================================================

def test_equity_no_positions():
    """Test 5: Equity = wallet quand aucune position ouverte"""
    wallet = 1000
    positions = {}
    last_prices = {}

    equity = update_equity(wallet, positions, last_prices)
    assert equity == wallet, f"Expected {wallet}, got {equity}"


def test_equity_long_profit():
    """Test 6: LONG en profit → equity > wallet"""
    wallet = 1000
    positions = {
        "BTC/USDT:USDT": {
            "qty": 0.1,
            "price": 50000,  # entry
            "side": "LONG"
        }
    }
    last_prices = {"BTC/USDT:USDT": 51000}  # +1000$ de profit (0.1 * 1000)

    equity = update_equity(wallet, positions, last_prices)
    expected = 1000 + 100  # wallet + unrealized PnL
    assert abs(equity - expected) < 0.01, f"Expected {expected}, got {equity}"


def test_equity_long_loss():
    """Test 7: LONG en perte → equity < wallet"""
    wallet = 1000
    positions = {
        "BTC/USDT:USDT": {
            "qty": 0.1,
            "price": 50000,
            "side": "LONG"
        }
    }
    last_prices = {"BTC/USDT:USDT": 49000}  # -100$ de perte

    equity = update_equity(wallet, positions, last_prices)
    expected = 1000 - 100
    assert abs(equity - expected) < 0.01, f"Expected {expected}, got {equity}"


def test_equity_short_profit():
    """Test 8: SHORT en profit → equity > wallet"""
    wallet = 1000
    positions = {
        "BTC/USDT:USDT": {
            "qty": 0.1,
            "price": 50000,
            "side": "SHORT"
        }
    }
    last_prices = {"BTC/USDT:USDT": 49000}  # Prix baisse → profit SHORT

    equity = update_equity(wallet, positions, last_prices)
    expected = 1000 + 100  # wallet + 100 profit
    assert abs(equity - expected) < 0.01, f"Expected {expected}, got {equity}"


def test_equity_multi_positions():
    """Test 9: Multiple positions avec profits/pertes mixtes"""
    wallet = 1000
    positions = {
        "BTC/USDT:USDT": {"qty": 0.1, "price": 50000, "side": "LONG"},   # +100 profit
        "ETH/USDT:USDT": {"qty": 1.0, "price": 3000, "side": "SHORT"},   # -200 loss
    }
    last_prices = {
        "BTC/USDT:USDT": 51000,  # BTC monte → +100 pour LONG
        "ETH/USDT:USDT": 3200,   # ETH monte → -200 pour SHORT
    }

    equity = update_equity(wallet, positions, last_prices)
    expected = 1000 + 100 - 200  # wallet + BTC profit - ETH loss
    assert abs(equity - expected) < 0.01, f"Expected {expected}, got {equity}"


# ============================================================================
# Tests apply_close()
# ============================================================================

def test_close_long_profit():
    """Test 10: Fermeture LONG avec profit"""
    position = {
        "qty": 0.1,
        "price": 50000,
        "side": "LONG",
        "size": 5000  # notional
    }
    exit_price = 51000
    fee_rate = 0.0006  # 0.06%

    pnl, fee = apply_close(position, exit_price, fee_rate, is_taker=True)

    # Raw PnL = 0.1 * (51000 - 50000) = 100
    # Fee = 0.1 * 51000 * 0.0006 = 3.06
    # Net PnL = 100 - 3.06 = 96.94

    expected_pnl = 100 - 3.06
    expected_fee = 3.06

    assert abs(pnl - expected_pnl) < 0.01, f"PnL: expected {expected_pnl}, got {pnl}"
    assert abs(fee - expected_fee) < 0.01, f"Fee: expected {expected_fee}, got {fee}"


def test_close_long_loss():
    """Test 11: Fermeture LONG avec perte"""
    position = {
        "qty": 0.1,
        "price": 50000,
        "side": "LONG",
        "size": 5000
    }
    exit_price = 49000
    fee_rate = 0.0006

    pnl, fee = apply_close(position, exit_price, fee_rate, is_taker=True)

    # Raw PnL = 0.1 * (49000 - 50000) = -100
    # Fee = 0.1 * 49000 * 0.0006 = 2.94
    # Net PnL = -100 - 2.94 = -102.94

    expected_pnl = -100 - 2.94
    expected_fee = 2.94

    assert abs(pnl - expected_pnl) < 0.01, f"PnL: expected {expected_pnl}, got {pnl}"
    assert abs(fee - expected_fee) < 0.01, f"Fee: expected {expected_fee}, got {fee}"


def test_close_short_profit():
    """Test 12: Fermeture SHORT avec profit"""
    position = {
        "qty": 0.1,
        "price": 50000,
        "side": "SHORT",
        "size": 5000
    }
    exit_price = 49000  # Prix baisse → profit SHORT
    fee_rate = 0.0006

    pnl, fee = apply_close(position, exit_price, fee_rate, is_taker=True)

    # Raw PnL = 0.1 * (50000 - 49000) = 100
    # Fee = 0.1 * 49000 * 0.0006 = 2.94
    # Net PnL = 100 - 2.94 = 97.06

    expected_pnl = 100 - 2.94

    assert abs(pnl - expected_pnl) < 0.01, f"PnL: expected {expected_pnl}, got {pnl}"


# ============================================================================
# Tests check_exposure_caps()
# ============================================================================

def test_exposure_cap_empty():
    """Test 13: Première position → toujours acceptée si < caps"""
    new_notional = 250  # 25% de l'equity → OK avec per_pair_cap=0.3
    current_positions = {}
    equity = 1000

    allowed, reason = check_exposure_caps(
        new_notional, "LONG", "BTC/USDT:USDT",
        current_positions, equity,
        gross_cap=1.5, per_side_cap=1.0, per_pair_cap=0.3
    )

    assert allowed, f"Should be allowed, got: {reason}"


def test_exposure_cap_gross_exceeded():
    """Test 14: Gross exposure cap dépassé → rejeté"""
    new_notional = 600
    current_positions = {
        "BTC/USDT:USDT": {"size": 1000, "side": "LONG"}
    }
    equity = 1000  # Gross cap = 1.5 * 1000 = 1500

    # Total après = 1000 + 600 = 1600 > 1500 → rejeté
    allowed, reason = check_exposure_caps(
        new_notional, "LONG", "ETH/USDT:USDT",
        current_positions, equity,
        gross_cap=1.5
    )

    assert not allowed, "Should be rejected (gross cap)"
    assert "Gross exposure" in reason


def test_exposure_cap_per_pair_exceeded():
    """Test 15: Per-pair cap dépassé → rejeté"""
    new_notional = 200
    current_positions = {
        "BTC/USDT:USDT": {"size": 200, "side": "LONG"}  # Déjà 200 sur BTC
    }
    equity = 1000  # Per-pair cap = 0.3 * 1000 = 300

    # Total BTC après = 200 + 200 = 400 > 300 → rejeté
    allowed, reason = check_exposure_caps(
        new_notional, "LONG", "BTC/USDT:USDT",
        current_positions, equity,
        per_pair_cap=0.3
    )

    assert not allowed, "Should be rejected (per-pair cap)"
    assert "Per-pair" in reason


def test_exposure_cap_per_side_exceeded():
    """Test 16: Per-side cap dépassé → rejeté"""
    new_notional = 600
    current_positions = {
        "BTC/USDT:USDT": {"size": 500, "side": "LONG"},
        "ETH/USDT:USDT": {"size": 300, "side": "SHORT"}
    }
    equity = 1000  # Per-side cap = 1.0 * 1000 = 1000

    # Total LONG après = 500 + 600 = 1100 > 1000 → rejeté
    allowed, reason = check_exposure_caps(
        new_notional, "LONG", "SOL/USDT:USDT",
        current_positions, equity,
        per_side_cap=1.0
    )

    assert not allowed, "Should be rejected (per-side cap)"
    assert "LONG exposure" in reason


# ============================================================================
# Tests get_mmr()
# ============================================================================

def test_mmr_btc():
    """Test 17: MMR pour BTC = 0.4%"""
    mmr = get_mmr("BTC/USDT:USDT")
    assert mmr == 0.004, f"Expected 0.004, got {mmr}"


def test_mmr_eth():
    """Test 18: MMR pour ETH = 0.5%"""
    mmr = get_mmr("ETH/USDT:USDT")
    assert mmr == 0.005, f"Expected 0.005, got {mmr}"


def test_mmr_major():
    """Test 19: MMR pour major (SOL) = 0.75%"""
    mmr = get_mmr("SOL/USDT:USDT")
    assert mmr == 0.0075, f"Expected 0.0075, got {mmr}"


def test_mmr_default():
    """Test 20: MMR pour token inconnu = 1.0% (default)"""
    mmr = get_mmr("RANDOM/USDT:USDT")
    assert mmr == 0.010, f"Expected 0.010, got {mmr}"


# ============================================================================
# Tests KillSwitch
# ============================================================================

def test_killswitch_no_trigger():
    """Test 21: Kill-switch ne se déclenche pas si PnL > seuils"""
    ks = KillSwitch(day_pnl_threshold=-0.08, hour_pnl_threshold=-0.12)

    dt = pd.Timestamp("2024-01-01 10:00:00")
    equity = 1000

    # Premier update → initialise
    is_paused = ks.update(dt, equity, 1000)
    assert not is_paused, "Should not be paused initially"

    # Equity monte légèrement → pas de trigger
    dt2 = pd.Timestamp("2024-01-01 11:00:00")
    equity2 = 980  # -2% → OK
    is_paused = ks.update(dt2, equity2, 1000)
    assert not is_paused, "Should not be paused with -2%"


def test_killswitch_day_trigger():
    """Test 22: Kill-switch se déclenche si day PnL <= -8%"""
    ks = KillSwitch(day_pnl_threshold=-0.08, hour_pnl_threshold=-0.12)

    dt = pd.Timestamp("2024-01-01 10:00:00")
    equity_start = 1000

    # Initialisation
    ks.update(dt, equity_start, 1000)

    # Equity chute de -10% dans la journée
    dt2 = pd.Timestamp("2024-01-01 15:00:00")
    equity2 = 900  # -10% du jour
    is_paused = ks.update(dt2, equity2, 1000)

    assert is_paused, "Should be paused with -10% day PnL"
    assert ks.pause_until is not None, "pause_until should be set"


def test_killswitch_hour_trigger():
    """Test 23: Kill-switch se déclenche si 1h PnL <= -12%"""
    ks = KillSwitch(day_pnl_threshold=-0.08, hour_pnl_threshold=-0.12)

    dt = pd.Timestamp("2024-01-01 10:00:00")
    equity_start = 1000

    # Initialisation heure
    ks.update(dt, equity_start, 1000)

    # Equity chute de -15% en 1 heure
    dt2 = pd.Timestamp("2024-01-01 10:30:00")
    equity2 = 850  # -15% en 30min (même heure)
    is_paused = ks.update(dt2, equity2, 1000)

    assert is_paused, "Should be paused with -15% hourly PnL"


def test_killswitch_unpause_after_24h():
    """Test 24: Kill-switch se désactive après 24h"""
    ks = KillSwitch(pause_hours=24)

    dt = pd.Timestamp("2024-01-01 10:00:00")
    ks.update(dt, 1000, 1000)

    # Trigger
    dt2 = pd.Timestamp("2024-01-01 11:00:00")
    ks.update(dt2, 900, 1000)  # -10% → pause

    assert ks.is_paused, "Should be paused"

    # 24h plus tard
    dt3 = pd.Timestamp("2024-01-02 12:00:00")  # 25h après trigger
    is_paused = ks.update(dt3, 950, 1000)

    assert not is_paused, "Should be unpaused after 24h"


# ============================================================================
# Exécution des tests
# ============================================================================

if __name__ == "__main__":
    print("="*80)
    print("TESTS UNITAIRES - margin.py")
    print("="*80)

    # Run all tests
    pytest.main([__file__, "-v", "--tb=short"])
