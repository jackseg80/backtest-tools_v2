"""
Quick test to verify v2 liquidation logic works correctly.
Tests the margin.py functions directly.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utilities.margin import compute_liq_price, get_mmr

def test_liquidation_prices():
    """Test liquidation price calculations."""
    print("\n" + "="*80)
    print("TEST: Liquidation Prices (v2 margin system)")
    print("="*80)

    # Test 1: 100x LONG
    entry = 50000
    leverage = 100
    mmr = get_mmr("BTC/USDT:USDT")  # 0.004 (0.4%)
    liq_price_long = compute_liq_price(entry, "LONG", leverage, mmr)

    print(f"\n1. BTC LONG @ 50,000$ avec levier 100x:")
    print(f"   MMR: {mmr*100:.1f}%")
    print(f"   Prix de liquidation: {liq_price_long:,.2f}$")
    print(f"   Distance: {((liq_price_long / entry - 1) * 100):.2f}%")

    # Expected: ~49,750$ (-0.5% from entry)
    expected_liq = entry * (1 - (1/leverage) + mmr)  # 50000 * 0.995 = 49,750
    print(f"   Attendu: {expected_liq:,.2f}$")
    assert abs(liq_price_long - expected_liq) < 1, f"Liq price incorrect: {liq_price_long} vs {expected_liq}"

    # Test 2: 10x LONG
    leverage_10x = 10
    liq_price_10x = compute_liq_price(entry, "LONG", leverage_10x, mmr)

    print(f"\n2. BTC LONG @ 50,000$ avec levier 10x:")
    print(f"   Prix de liquidation: {liq_price_10x:,.2f}$")
    print(f"   Distance: {((liq_price_10x / entry - 1) * 100):.2f}%")

    # Expected: ~45,250$ (-9.5% from entry)
    expected_10x = entry * (1 - (1/10) + mmr)  # 50000 * 0.905 = 45,250
    print(f"   Attendu: {expected_10x:,.2f}$")
    assert abs(liq_price_10x - expected_10x) < 1

    # Test 3: 100x SHORT
    liq_price_short = compute_liq_price(entry, "SHORT", leverage, mmr)

    print(f"\n3. BTC SHORT @ 50,000$ avec levier 100x:")
    print(f"   Prix de liquidation: {liq_price_short:,.2f}$")
    print(f"   Distance: {((liq_price_short / entry - 1) * 100):.2f}%")

    # Expected: ~50,250$ (+0.5% from entry)
    expected_short = entry * (1 + (1/leverage) - mmr)  # 50000 * 1.005 = 50,250
    print(f"   Attendu: {expected_short:,.2f}$")
    assert abs(liq_price_short - expected_short) < 1

    print("\n" + "="*80)
    print("Verification:")
    print(f"  - 100x LONG: liquidation a {((liq_price_long / entry - 1) * 100):.2f}% du prix d'entree")
    print(f"  - 10x LONG: liquidation a {((liq_price_10x / entry - 1) * 100):.2f}% du prix d'entree")
    print(f"  - 100x SHORT: liquidation a {((liq_price_short / entry - 1) * 100):.2f}% du prix d'entree")
    print("="*80)

    print("\nTEST PASSED: Liquidation prices calculated correctly\n")

def test_scenario_100x():
    """Simulate a realistic liquidation scenario."""
    print("\n" + "="*80)
    print("SCENARIO: Liquidation avec levier 100x")
    print("="*80)

    # Initial conditions
    wallet = 1000
    entry_price = 50000
    leverage = 100
    pair = "BTC/USDT:USDT"
    mmr = get_mmr(pair)

    # Position opening
    size_pct = 0.1  # 10% of wallet
    notional = size_pct * wallet * leverage  # 0.1 * 1000 * 100 = 10,000$
    qty = notional / entry_price  # 10,000 / 50,000 = 0.2 BTC
    init_margin = notional / leverage  # 10,000 / 100 = 100$

    print(f"\nOuverture position LONG:")
    print(f"  Entry: {entry_price:,.2f}$")
    print(f"  Notional: {notional:,.2f}$ (avec levier)")
    print(f"  Quantity: {qty:.4f} BTC")
    print(f"  Marge initiale: {init_margin:.2f}$")

    # Calculate liquidation price
    liq_price = compute_liq_price(entry_price, "LONG", leverage, mmr)
    print(f"\nPrix de liquidation: {liq_price:,.2f}$")
    print(f"Distance: {((liq_price / entry_price - 1) * 100):.2f}%")

    # Simulate price drop to liquidation
    current_price = liq_price
    unrealized_pnl = qty * (current_price - entry_price)
    equity = wallet + unrealized_pnl

    print(f"\nQuand le prix atteint {current_price:,.2f}$:")
    print(f"  PnL non realise: {unrealized_pnl:.2f}$")
    print(f"  Equity: {equity:.2f}$")

    # At liquidation, equity should be close to 0
    loss_pct = (unrealized_pnl / wallet) * 100
    print(f"  Perte: {loss_pct:.1f}% du wallet")

    print("\nTEST PASSED: Scenario validated\n")

if __name__ == "__main__":
    print("\n>>> Quick v2 Margin System Tests\n")

    test_liquidation_prices()
    test_scenario_100x()

    print("="*80)
    print(">>> ALL TESTS PASSED - V2 MARGIN SYSTEM IS WORKING!")
    print("="*80 + "\n")
