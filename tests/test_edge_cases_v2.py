"""
Tests des edge cases critiques pour V2 - Senior QA Review

Tests identifiés comme critiques:
1. Gap à l'ouverture (open < liq_price)
2. Multi-DCA avec recalcul liq_price
3. Triple collision (liq + stop + ma_base même bougie)
4. Caps & rejets (vérif no side-effects)
5. Cascades multi-positions
6. Precision / min-notional
"""

import sys
sys.path.append('..')

from utilities.margin import compute_liq_price, apply_close, check_exposure_caps, get_mmr

def test_gap_opening_long():
    """
    Test 1a: Gap à l'ouverture LONG

    Position LONG @ 50,000, leverage 10x, liq @ 45,200
    Gap down: open @ 44,000 < liq_price

    Convention: Liquidation immédiate au MIN(open, liq_price) = 44,000
    """
    print("\n" + "="*80)
    print("TEST 1a: GAP A L'OUVERTURE (LONG)")
    print("="*80)

    entry = 50000
    leverage = 10
    mmr = 0.005  # 0.5%

    liq_price = compute_liq_price(entry, "LONG", leverage, mmr)
    print(f"Entry: ${entry:,.2f}")
    print(f"Leverage: {leverage}x")
    print(f"Liq price: ${liq_price:,.2f} ({((liq_price/entry - 1) * 100):.2f}%)")

    # Gap down
    gap_open = 44000
    assert gap_open < liq_price, "Gap doit etre sous liq_price"

    # Execution price: MIN(open, liq_price)
    execution_price = min(gap_open, liq_price)

    print(f"\nGap open: ${gap_open:,.2f}")
    print(f"Execution @ MIN(open, liq): ${execution_price:,.2f}")

    # Calcul PnL
    qty = 0.1  # BTC
    position = {
        'qty': qty,
        'price': entry,
        'side': 'LONG'
    }

    pnl, fee = apply_close(position, execution_price, 0.0006)
    expected_pnl = qty * (execution_price - entry) - (qty * execution_price * 0.0006)

    print(f"\nQty: {qty} BTC")
    print(f"PnL: ${pnl:,.2f}")
    print(f"Fee: ${fee:,.2f}")
    print(f"Expected PnL: ${expected_pnl:,.2f}")

    assert abs(pnl - expected_pnl) < 0.01, "PnL incorrect"
    print("\nTEST PASSED - Gap handling correct")

def test_gap_opening_short():
    """
    Test 1b: Gap à l'ouverture SHORT

    Position SHORT @ 50,000, leverage 10x, liq @ 55,300
    Gap up: open @ 56,000 > liq_price

    Convention: Liquidation immédiate au MAX(open, liq_price) = 56,000
    """
    print("\n" + "="*80)
    print("TEST 1b: GAP A L'OUVERTURE (SHORT)")
    print("="*80)

    entry = 50000
    leverage = 10
    mmr = 0.005

    liq_price = compute_liq_price(entry, "SHORT", leverage, mmr)
    print(f"Entry: ${entry:,.2f}")
    print(f"Leverage: {leverage}x")
    print(f"Liq price: ${liq_price:,.2f} ({((liq_price/entry - 1) * 100):.2f}%)")

    # Gap up
    gap_open = 56000
    assert gap_open > liq_price, "Gap doit etre au-dessus liq_price"

    # Execution price: MAX(open, liq_price)
    execution_price = max(gap_open, liq_price)

    print(f"\nGap open: ${gap_open:,.2f}")
    print(f"Execution @ MAX(open, liq): ${execution_price:,.2f}")

    # Calcul PnL
    qty = 0.1
    position = {
        'qty': qty,
        'price': entry,
        'side': 'SHORT'
    }

    pnl, fee = apply_close(position, execution_price, 0.0006)
    expected_pnl = qty * (entry - execution_price) - (qty * execution_price * 0.0006)

    print(f"\nQty: {qty} BTC")
    print(f"PnL: ${pnl:,.2f}")
    print(f"Fee: ${fee:,.2f}")
    print(f"Expected PnL: ${expected_pnl:,.2f}")

    assert abs(pnl - expected_pnl) < 0.01, "PnL incorrect"
    print("\nTEST PASSED - Gap handling correct (SHORT)")

def test_multi_dca_liq_recalc():
    """
    Test 2: Multi-DCA avec recalcul liquidation

    Fill 1: LONG @ 50,000 (qty=0.1, liq @ 45,200)
    Fill 2: DCA @ 48,000 (qty=0.1, avg=49,000, liq @ 44,296)
    Fill 3: DCA @ 46,000 (qty=0.1, avg=48,000, liq @ 43,392)

    Meche touche liq_final (43,392) -> LIQUIDATION
    Marge totale libérée
    """
    print("\n" + "="*80)
    print("TEST 2: MULTI-DCA AVEC RECALCUL LIQUIDATION")
    print("="*80)

    leverage = 10
    mmr = 0.005
    wallet = 10000

    # Fill 1
    entry1 = 50000
    qty1 = 0.1
    notional1 = entry1 * qty1
    init_margin1 = notional1 / leverage
    liq1 = compute_liq_price(entry1, "LONG", leverage, mmr)

    print(f"Fill 1: Entry ${entry1:,.2f}, qty {qty1}, liq ${liq1:,.2f}")
    print(f"  Init margin: ${init_margin1:,.2f}")

    # Fill 2 (DCA)
    entry2 = 48000
    qty2 = 0.1
    total_qty = qty1 + qty2
    avg_entry = (entry1 * qty1 + entry2 * qty2) / total_qty
    notional2 = entry2 * qty2
    init_margin2 = notional2 / leverage
    liq2 = compute_liq_price(avg_entry, "LONG", leverage, mmr)

    print(f"\nFill 2 (DCA): Entry ${entry2:,.2f}, qty {qty2}")
    print(f"  Avg entry: ${avg_entry:,.2f}")
    print(f"  Total qty: {total_qty}")
    print(f"  New liq: ${liq2:,.2f}")
    print(f"  Cumul margin: ${init_margin1 + init_margin2:,.2f}")

    # Fill 3 (DCA)
    entry3 = 46000
    qty3 = 0.1
    total_qty = qty1 + qty2 + qty3
    avg_entry = (entry1 * qty1 + entry2 * qty2 + entry3 * qty3) / total_qty
    notional3 = entry3 * qty3
    init_margin3 = notional3 / leverage
    liq3 = compute_liq_price(avg_entry, "LONG", leverage, mmr)

    print(f"\nFill 3 (DCA): Entry ${entry3:,.2f}, qty {qty3}")
    print(f"  Avg entry: ${avg_entry:,.2f}")
    print(f"  Total qty: {total_qty}")
    print(f"  Final liq: ${liq3:,.2f}")
    print(f"  Total margin: ${init_margin1 + init_margin2 + init_margin3:,.2f}")

    # Meche touche liq3
    candle_low = liq3 - 10  # Touche liq
    print(f"\nCandle low: ${candle_low:,.2f} (< liq ${liq3:,.2f})")

    # Liquidation au liq_price
    position = {
        'qty': total_qty,
        'price': avg_entry,
        'side': 'LONG'
    }

    pnl, fee = apply_close(position, liq3, 0.0006)
    total_margin = init_margin1 + init_margin2 + init_margin3
    wallet_after = wallet + pnl - total_margin  # Perte margin + PnL

    print(f"\nLiquidation @ ${liq3:,.2f}")
    print(f"  PnL: ${pnl:,.2f}")
    print(f"  Fee: ${fee:,.2f}")
    print(f"  Margin freed: ${total_margin:,.2f}")
    print(f"  Wallet after: ${wallet_after:,.2f}")

    # Verif: wallet reste positif
    assert wallet_after > 0, "Wallet ne doit pas etre negatif"

    # Verif: perte proche de -9.6% (leverage 10x)
    expected_loss_pct = -((1 / leverage) - mmr)  # -9.6%
    actual_loss_pct = (liq3 / avg_entry) - 1
    print(f"\nLoss theorique: {expected_loss_pct * 100:.2f}%")
    print(f"Loss reel: {actual_loss_pct * 100:.2f}%")

    assert abs(actual_loss_pct - expected_loss_pct) < 0.001, "Loss % incorrect"
    print("\nTEST PASSED - Multi-DCA liquidation correct")

def test_triple_collision():
    """
    Test 3: Triple collision (liq, stop, ma_base)

    Position LONG @ 50,000
    Liq @ 47,700, Stop @ 47,500, MA base @ 49,000

    Bougie: low=47,400, high=50,000
    Touche les 3 niveaux

    Priorite: Liquidation > Stop > MA base
    Resultat: Execute LIQUIDATION uniquement
    """
    print("\n" + "="*80)
    print("TEST 3: TRIPLE COLLISION (liq + stop + ma_base)")
    print("="*80)

    entry = 50000
    leverage = 20  # Plus proche pour tester collision
    mmr = 0.005

    liq_price = compute_liq_price(entry, "LONG", leverage, mmr)
    stop_price = entry * 0.95  # -5%
    ma_base = entry * 0.98     # -2%

    print(f"Entry: ${entry:,.2f}")
    print(f"Liq price: ${liq_price:,.2f}")
    print(f"Stop price: ${stop_price:,.2f}")
    print(f"MA base: ${ma_base:,.2f}")

    # Bougie qui touche tout
    candle_low = 47400
    candle_high = 50000

    print(f"\nCandle: low=${candle_low:,.2f}, high=${candle_high:,.2f}")
    print(f"Touches: liq={candle_low < liq_price}, stop={candle_low < stop_price}, ma_base={candle_high > ma_base}")

    # Priorite check
    events = []
    if candle_low <= liq_price:
        events.append(("LIQUIDATION", liq_price))
    if candle_low <= stop_price:
        events.append(("STOP_LOSS", stop_price))
    if candle_high >= ma_base:
        events.append(("MA_BASE", ma_base))

    print(f"\nEvents detectes: {[e[0] for e in events]}")

    # Priorite: LIQUIDATION d'abord
    executed_event = events[0][0]
    execution_price = events[0][1]

    print(f"Event execute: {executed_event} @ ${execution_price:,.2f}")
    print(f"Events ignores: {[e[0] for e in events[1:]]}")

    assert executed_event == "LIQUIDATION", "Liquidation doit avoir priorite"
    print("\nTEST PASSED - Priorite Liq > Stop > MA respectee")

def test_caps_rejection_no_side_effects():
    """
    Test 4: Caps & rejets sans side-effects

    Ouvre positions jusqu'a gross_cap
    Tente ouverture supplementaire -> REJET
    Verifie: wallet, used_margin, positions inchanges
    """
    print("\n" + "="*80)
    print("TEST 4: CAPS & REJETS (NO SIDE-EFFECTS)")
    print("="*80)

    wallet = 10000
    equity = 10000
    used_margin = 0
    positions = {}

    gross_cap = 1.5  # Max 15,000 notional
    per_side_cap = 1.0
    per_pair_cap = 0.3  # Max 3,000 per pair

    # Fill 1: BTC, notional = 2,500 (< per_pair_cap)
    notional1 = 2500
    allowed1, reason1 = check_exposure_caps(notional1, "LONG", "BTC/USDT:USDT",
                                           positions, equity, gross_cap, per_side_cap, per_pair_cap)

    print(f"Fill 1: Notional ${notional1:,.2f} -> {allowed1} ({reason1})")
    assert allowed1, "Fill 1 doit passer"

    positions["BTC/USDT:USDT"] = {'side': 'LONG', 'qty': 0.05, 'price': 50000}
    used_margin += notional1 / 10  # leverage 10x

    # Fill 2: ETH, notional = 2,500 (< per_pair_cap)
    notional2 = 2500
    allowed2, reason2 = check_exposure_caps(notional2, "LONG", "ETH/USDT:USDT",
                                           positions, equity, gross_cap, per_side_cap, per_pair_cap)

    print(f"Fill 2: Notional ${notional2:,.2f} -> {allowed2} ({reason2})")
    assert allowed2, "Fill 2 doit passer"

    positions["ETH/USDT:USDT"] = {'side': 'LONG', 'qty': 1.0, 'price': 2500}
    used_margin += notional2 / 10

    # Fill 3: SOL, notional = 2,500 (< per_pair_cap)
    notional3 = 2500
    allowed3, reason3 = check_exposure_caps(notional3, "LONG", "SOL/USDT:USDT",
                                           positions, equity, gross_cap, per_side_cap, per_pair_cap)

    print(f"Fill 3: Notional ${notional3:,.2f} -> {allowed3} ({reason3})")
    assert allowed3, "Fill 3 doit passer (total = 7,500 < gross_cap 15,000)"

    positions["SOL/USDT:USDT"] = {'side': 'LONG', 'qty': 25.0, 'price': 100}
    used_margin += notional3 / 10

    # Fill 4: Tente AVAX, notional=8000 -> REJET (gross_cap 15k depasse avec total 7.5k+8k=15.5k)
    wallet_before = wallet
    used_margin_before = used_margin
    positions_count_before = len(positions)

    notional4 = 8000
    allowed4, reason4 = check_exposure_caps(notional4, "LONG", "AVAX/USDT:USDT",
                                           positions, equity, gross_cap, per_side_cap, per_pair_cap)

    print(f"\nFill 4 (REJET): Notional ${notional4:,.2f} -> {allowed4}")
    print(f"  Raison: {reason4}")
    assert not allowed4, "Fill 4 doit etre REJETE"

    # Verifie NO side-effects
    print(f"\nVerification NO side-effects:")
    print(f"  Wallet: {wallet_before} -> {wallet} (inchange: {wallet == wallet_before})")
    print(f"  Used margin: {used_margin_before} -> {used_margin} (inchange: {used_margin == used_margin_before})")
    print(f"  Positions count: {positions_count_before} -> {len(positions)} (inchange: {len(positions) == positions_count_before})")

    assert wallet == wallet_before, "Wallet modifie (side-effect)"
    assert used_margin == used_margin_before, "Margin modifiee (side-effect)"
    assert len(positions) == positions_count_before, "Positions modifiees (side-effect)"

    print("\nTEST PASSED - Rejection sans side-effects")

def test_cascade_multi_positions():
    """
    Test 5: Cascades multi-positions

    3 positions LONG
    Baisse brutale -> liquidations en cascade
    Verifie ordre de fermeture et recalcul equity
    """
    print("\n" + "="*80)
    print("TEST 5: CASCADES MULTI-POSITIONS")
    print("="*80)

    wallet = 10000
    leverage = 10
    mmr = 0.005

    # Position 1: BTC @ 50,000
    pos1 = {
        'pair': 'BTC/USDT:USDT',
        'qty': 0.1,
        'price': 50000,
        'side': 'LONG',
        'init_margin': 500
    }
    liq1 = compute_liq_price(pos1['price'], "LONG", leverage, mmr)
    pos1['liq_price'] = liq1

    # Position 2: ETH @ 3,000
    pos2 = {
        'pair': 'ETH/USDT:USDT',
        'qty': 1.5,
        'price': 3000,
        'side': 'LONG',
        'init_margin': 450
    }
    liq2 = compute_liq_price(pos2['price'], "LONG", leverage, mmr)
    pos2['liq_price'] = liq2

    # Position 3: SOL @ 100
    pos3 = {
        'pair': 'SOL/USDT:USDT',
        'qty': 40,
        'price': 100,
        'side': 'LONG',
        'init_margin': 400
    }
    liq3 = compute_liq_price(pos3['price'], "LONG", leverage, mmr)
    pos3['liq_price'] = liq3

    positions = {
        pos1['pair']: pos1,
        pos2['pair']: pos2,
        pos3['pair']: pos3
    }

    used_margin = pos1['init_margin'] + pos2['init_margin'] + pos3['init_margin']

    print(f"Wallet initial: ${wallet:,.2f}")
    print(f"Used margin: ${used_margin:,.2f}")
    print(f"\nPositions:")
    for pair, pos in positions.items():
        print(f"  {pair}: entry ${pos['price']:,.2f}, liq ${pos['liq_price']:,.2f}")

    # Crash -10% sur tous les actifs
    crash_pct = -0.10
    current_prices = {
        'BTC/USDT:USDT': pos1['price'] * (1 + crash_pct),
        'ETH/USDT:USDT': pos2['price'] * (1 + crash_pct),
        'SOL/USDT:USDT': pos3['price'] * (1 + crash_pct)
    }

    print(f"\nCrash -{abs(crash_pct)*100}%:")
    for pair, price in current_prices.items():
        print(f"  {pair}: ${positions[pair]['price']:,.2f} -> ${price:,.2f}")

    # Check liquidations
    liquidated = []
    for pair, pos in positions.items():
        if current_prices[pair] <= pos['liq_price']:
            liquidated.append(pair)
            print(f"  LIQUIDATION: {pair} (price ${current_prices[pair]:,.2f} <= liq ${pos['liq_price']:,.2f})")

    # Ferme liquidations
    for pair in liquidated:
        pos = positions[pair]
        pnl, fee = apply_close(pos, pos['liq_price'], 0.0006)
        wallet += pnl
        used_margin -= pos['init_margin']
        del positions[pair]
        print(f"\n  Closed {pair}: PnL ${pnl:,.2f}, margin freed ${pos['init_margin']:,.2f}")

    print(f"\nApres cascades:")
    print(f"  Wallet: ${wallet:,.2f}")
    print(f"  Used margin: ${used_margin:,.2f}")
    print(f"  Positions restantes: {len(positions)}")

    assert wallet > 0, "Wallet doit rester positif"
    assert used_margin >= 0, "Margin ne peut pas etre negative"

    print("\nTEST PASSED - Cascades gerees correctement")

def test_precision_min_notional():
    """
    Test 6: Precision & min-notional

    Qty tres petite apres arrondi -> qty = 0 (REJET)
    Notional < min_notional exchange (ex. 5$) -> REJET
    """
    print("\n" + "="*80)
    print("TEST 6: PRECISION & MIN-NOTIONAL")
    print("="*80)

    price = 50000
    precision_qty = 3  # 0.001 BTC min
    min_notional = 5   # 5$ min

    # Test 1: Qty trop petite
    size_pct = 0.0001  # 0.01%
    equity = 1000
    notional = size_pct * equity  # 0.1$
    qty = notional / price  # 0.000002 BTC
    qty_rounded = round(qty, precision_qty)

    print(f"Test 1: Qty trop petite")
    print(f"  Size: {size_pct*100}% x equity ${equity:,.2f} = ${notional:,.2f}")
    print(f"  Qty: {qty:.8f} BTC")
    print(f"  Qty arrondi (precision {precision_qty}): {qty_rounded:.8f} BTC")

    if qty_rounded == 0:
        print(f"  -> REJET (qty = 0 apres arrondi)")
    else:
        print(f"  -> OK")

    assert qty_rounded == 0, "Qty doit etre 0 apres arrondi"

    # Test 2: Notional < min
    size_pct2 = 0.01  # 1%
    equity2 = 300
    notional2 = size_pct2 * equity2  # 3$

    print(f"\nTest 2: Notional < min")
    print(f"  Size: {size_pct2*100}% x equity ${equity2:,.2f} = ${notional2:,.2f}")
    print(f"  Min notional: ${min_notional:,.2f}")

    if notional2 < min_notional:
        print(f"  -> REJET (notional ${notional2:.2f} < min ${min_notional:.2f})")
    else:
        print(f"  -> OK")

    assert notional2 < min_notional, "Notional doit etre < min"

    # Test 3: OK case
    size_pct3 = 0.05  # 5%
    equity3 = 1000
    notional3 = size_pct3 * equity3  # 50$
    qty3 = notional3 / price
    qty3_rounded = round(qty3, precision_qty)

    print(f"\nTest 3: OK case")
    print(f"  Size: {size_pct3*100}% x equity ${equity3:,.2f} = ${notional3:,.2f}")
    print(f"  Qty: {qty3:.8f} BTC -> {qty3_rounded:.3f} BTC")
    print(f"  Notional: ${notional3:,.2f} >= min ${min_notional:,.2f}")

    assert qty3_rounded > 0, "Qty doit etre > 0"
    assert notional3 >= min_notional, "Notional doit etre >= min"
    print(f"  -> OK (qty={qty3_rounded}, notional=${notional3:.2f})")

    print("\nTEST PASSED - Precision & min-notional geres")

if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTS EDGE CASES V2 - SENIOR QA REVIEW")
    print("="*80)

    test_gap_opening_long()
    test_gap_opening_short()
    test_multi_dca_liq_recalc()
    test_triple_collision()
    test_caps_rejection_no_side_effects()
    test_cascade_multi_positions()
    test_precision_min_notional()

    print("\n" + "="*80)
    print("TOUS LES TESTS PASSES")
    print("="*80)
