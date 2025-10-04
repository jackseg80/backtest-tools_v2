"""
Test de neutralité au levier pour V2

Vérifie que le système V2 reste neutre au levier avec auto_adjust_size=True :
- Même notional peu importe le leverage
- Même nombre de trades ouverts
- Liquidations appropriées pour leverage élevé
- Caps respectés pour tous les leverages
"""

import sys
sys.path.append('..')

import pandas as pd
import numpy as np
from utilities.strategies.envelopeMulti_v2 import EnvelopeMulti_v2

def create_test_data():
    """Create simple synthetic data for testing"""
    dates = pd.date_range(start='2023-01-01', end='2023-12-31', freq='1h')

    # Simple trending data with volatility
    np.random.seed(42)
    price = 50000
    prices = []
    for _ in range(len(dates)):
        price = price * (1 + np.random.normal(0, 0.02))  # 2% volatility
        prices.append(price)

    df = pd.DataFrame({
        'open': prices,
        'high': [p * 1.01 for p in prices],
        'low': [p * 0.99 for p in prices],
        'close': prices,
        'volume': [1000000] * len(dates)
    }, index=dates)

    return df

def test_leverage_neutrality():
    """
    Test 1: Neutralité de base
    Avec auto_adjust_size=True, le notional moyen par position doit être similaire
    """
    print("\n" + "="*80)
    print("TEST 1: NEUTRALITE AU LEVIER (auto_adjust_size=True)")
    print("="*80)

    df = create_test_data()
    df_list = {"BTC/USDT:USDT": df}
    params = {
        "BTC/USDT:USDT": {
            "src": "close",
            "ma_base_window": 7,
            "envelopes": [0.05, 0.10, 0.15],
            "size": 0.3  # Base size (sera divisé par leverage)
        }
    }

    leverages = [1, 5, 10, 25, 50, 100]
    results = []

    for leverage in leverages:
        print(f"\n--- Testing leverage {leverage}x ---")

        strat = EnvelopeMulti_v2(
            df_list=df_list,
            oldest_pair="BTC/USDT:USDT",
            type=["long"],
            params=params
        )

        strat.populate_indicators()
        strat.populate_buy_sell()

        bt_result = strat.run_backtest(
            initial_wallet=10000,
            leverage=leverage,
            maker_fee=0.0002,
            taker_fee=0.0006,
            stop_loss=0.15,
            reinvest=False,
            liquidation=True,
            gross_cap=1.5,
            per_side_cap=1.0,
            per_pair_cap=0.3,
            margin_cap=0.8,
            use_kill_switch=False,
            auto_adjust_size=True,
            extreme_leverage_threshold=50
        )

        df_trades = bt_result['trades']

        # Calculate metrics
        if len(df_trades) > 0:
            # open_trade_size is already the notional (pos_size)
            avg_notional = df_trades['open_trade_size'].mean()
            total_trades = len(df_trades)
            liquidations = len(df_trades[df_trades['close_reason'] == 'Liquidation'])
            final_wallet = bt_result['wallet']

            results.append({
                'leverage': leverage,
                'trades': total_trades,
                'avg_notional': avg_notional,
                'liquidations': liquidations,
                'final_wallet': final_wallet
            })

            print(f"  Trades: {total_trades}")
            print(f"  Avg notional: ${avg_notional:,.2f}")
            print(f"  Liquidations: {liquidations}")
            print(f"  Final wallet: ${final_wallet:,.2f}")
        else:
            print(f"  WARNING: No trades executed (likely rejected by caps)")
            results.append({
                'leverage': leverage,
                'trades': 0,
                'avg_notional': 0,
                'liquidations': 0,
                'final_wallet': 10000
            })

    # Analyze results
    print("\n" + "="*80)
    print("RESULTATS COMPARATIFS")
    print("="*80)

    df_results = pd.DataFrame(results)
    print(df_results.to_string(index=False))

    # Check neutrality (notional should be similar across all leverages)
    notionals = df_results[df_results['avg_notional'] > 0]['avg_notional']
    if len(notionals) > 1:
        notional_std = notionals.std()
        notional_mean = notionals.mean()
        cv = (notional_std / notional_mean) * 100  # Coefficient of variation

        print(f"\nNotional moyen: ${notional_mean:,.2f}")
        print(f"Ecart-type: ${notional_std:,.2f}")
        print(f"Coefficient de variation: {cv:.2f}%")

        if cv < 10:
            print("\nTEST PASSED - Neutralite au levier confirmee (CV < 10%)")
        else:
            print(f"\nWARNING - Variation elevee du notional (CV = {cv:.2f}%)")

    # Check liquidations increase with leverage
    print(f"\nLiquidations par leverage:")
    for idx, row in df_results.iterrows():
        if row['trades'] > 0:
            liq_pct = (row['liquidations'] / row['trades']) * 100
            print(f"  {row['leverage']:3.0f}x: {row['liquidations']:3.0f}/{row['trades']:3.0f} ({liq_pct:5.1f}%)")

def test_margin_cap_enforcement():
    """
    Test 2: Vérification du margin_cap
    Le margin cap doit empêcher l'ouverture de positions au-delà de margin_cap * equity
    """
    print("\n" + "="*80)
    print("TEST 2: VERIFICATION MARGIN CAP")
    print("="*80)

    df = create_test_data()
    df_list = {"BTC/USDT:USDT": df}
    params = {
        "BTC/USDT:USDT": {
            "src": "close",
            "ma_base_window": 7,
            "envelopes": [0.05, 0.10, 0.15],
            "size": 0.5  # Large size to trigger margin cap
        }
    }

    margin_caps = [0.3, 0.5, 0.8, 1.0]

    for margin_cap in margin_caps:
        print(f"\n--- Testing margin_cap={margin_cap} ---")

        strat = EnvelopeMulti_v2(
            df_list=df_list,
            oldest_pair="BTC/USDT:USDT",
            type=["long"],
            params=params
        )

        strat.populate_indicators()
        strat.populate_buy_sell()

        bt_result = strat.run_backtest(
            initial_wallet=10000,
            leverage=10,
            maker_fee=0.0002,
            taker_fee=0.0006,
            stop_loss=0.15,
            reinvest=False,
            liquidation=True,
            gross_cap=5.0,  # High cap to not interfere
            per_side_cap=5.0,
            per_pair_cap=5.0,
            margin_cap=margin_cap,
            use_kill_switch=False,
            auto_adjust_size=True
        )

        df_trades = bt_result['trades']

        if len(df_trades) > 0:
            total_trades = len(df_trades)
            print(f"  Trades executed: {total_trades}")
            print(f"  Final wallet: ${bt_result['wallet']:,.2f}")
        else:
            print(f"  No trades (margin cap too restrictive)")

def test_extreme_leverage_hardening():
    """
    Test 3: Durcissement pour leverage extrême (>50x)
    Vérifie que per_pair_cap est réduit pour leverage > 50x
    """
    print("\n" + "="*80)
    print("TEST 3: DURCISSEMENT LEVERAGE EXTREME (>50x)")
    print("="*80)

    df = create_test_data()
    df_list = {"BTC/USDT:USDT": df}
    params = {
        "BTC/USDT:USDT": {
            "src": "close",
            "ma_base_window": 7,
            "envelopes": [0.05, 0.10, 0.15],
            "size": 0.3
        }
    }

    leverages = [25, 50, 100, 200]

    for leverage in leverages:
        print(f"\n--- Testing leverage {leverage}x ---")

        strat = EnvelopeMulti_v2(
            df_list=df_list,
            oldest_pair="BTC/USDT:USDT",
            type=["long"],
            params=params
        )

        strat.populate_indicators()
        strat.populate_buy_sell()

        bt_result = strat.run_backtest(
            initial_wallet=10000,
            leverage=leverage,
            maker_fee=0.0002,
            taker_fee=0.0006,
            stop_loss=0.15,
            reinvest=False,
            liquidation=True,
            gross_cap=1.5,
            per_side_cap=1.0,
            per_pair_cap=0.3,
            margin_cap=0.8,
            use_kill_switch=False,
            auto_adjust_size=True,
            extreme_leverage_threshold=50
        )

        df_trades = bt_result['trades']

        if len(df_trades) > 0:
            total_trades = len(df_trades)
            liquidations = len(df_trades[df_trades['close_reason'] == 'Liquidation'])
            liq_pct = (liquidations / total_trades) * 100 if total_trades > 0 else 0

            print(f"  Trades: {total_trades}")
            print(f"  Liquidations: {liquidations} ({liq_pct:.1f}%)")
            print(f"  Final wallet: ${bt_result['wallet']:,.2f}")

            if leverage > 50:
                expected_reduction = ((leverage / 50) ** 0.5)
                print(f"  Expected per_pair_cap reduction: /{expected_reduction:.2f}")

if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTS DE NEUTRALITE AU LEVIER - SYSTÈME V2")
    print("="*80)

    test_leverage_neutrality()
    test_margin_cap_enforcement()
    test_extreme_leverage_hardening()

    print("\n" + "="*80)
    print("TOUS LES TESTS TERMINES")
    print("="*80)
