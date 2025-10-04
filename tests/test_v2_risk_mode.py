"""
Tests for V2 risk_mode (neutral/scaling/hybrid)

Validates:
1. Neutral vs Scaling (same leverage, different notional)
2. Hybrid cap enforcement
3. Neutrality across leverages (neutral mode)
4. Monotonicity of notional (scaling mode)
5. Margin & caps interaction
6. Performance/fees scaling
"""

import sys
sys.path.append('..')

import pandas as pd
import numpy as np
from utilities.strategies.envelopeMulti_v2 import EnvelopeMulti_v2, calculate_notional_per_level

def create_test_data():
    """Create synthetic data for testing"""
    dates = pd.date_range(start='2023-01-01', end='2023-12-31', freq='1h')

    np.random.seed(42)
    price = 50000
    prices = []
    for _ in range(len(dates)):
        price = price * (1 + np.random.normal(0, 0.02))
        prices.append(price)

    df = pd.DataFrame({
        'open': prices,
        'high': [p * 1.01 for p in prices],
        'low': [p * 0.99 for p in prices],
        'close': prices,
        'volume': [1000000] * len(dates)
    }, index=dates)

    return df

def test_neutral_vs_scaling():
    """
    Test 1: Neutral vs Scaling (same leverage)

    Neutral: notional = equity * base_size
    Scaling: notional = equity * base_size * leverage

    Expected: notional_scaling ≈ notional_neutral * leverage
    """
    print("\n" + "="*80)
    print("TEST 1: NEUTRAL VS SCALING (same leverage)")
    print("="*80)

    equity = 10000
    base_size = 0.06
    leverage = 10
    n_levels = 3

    notional_neutral = calculate_notional_per_level(
        equity=equity,
        base_size=base_size,
        leverage=leverage,
        n_levels=n_levels,
        risk_mode="neutral"
    )

    notional_scaling = calculate_notional_per_level(
        equity=equity,
        base_size=base_size,
        leverage=leverage,
        n_levels=n_levels,
        risk_mode="scaling"
    )

    print(f"Equity: ${equity:,.2f}")
    print(f"Base size: {base_size*100}%")
    print(f"Leverage: {leverage}x")
    print(f"Levels: {n_levels}")
    print(f"\nNotional per level:")
    print(f"  Neutral: ${notional_neutral:,.2f}")
    print(f"  Scaling: ${notional_scaling:,.2f}")
    print(f"  Ratio: {notional_scaling / notional_neutral:.2f}x")

    # Validation
    expected_ratio = leverage
    actual_ratio = notional_scaling / notional_neutral

    assert abs(actual_ratio - expected_ratio) < 0.01, \
        f"Scaling should be {expected_ratio}x neutral, got {actual_ratio:.2f}x"

    print(f"\nTEST PASSED - Scaling = {expected_ratio}x Neutral OK")

def test_hybrid_cap_enforcement():
    """
    Test 2: Hybrid cap enforcement

    Hybrid: notional = min(equity * base_size * leverage, equity * max_expo_cap)

    Expected: notional capped at equity * max_expo_cap when leverage is high
    """
    print("\n" + "="*80)
    print("TEST 2: HYBRID CAP ENFORCEMENT")
    print("="*80)

    equity = 10000
    base_size = 0.1  # 10%
    max_expo_cap = 2.0  # Max 2x equity
    n_levels = 3

    leverages = [1, 10, 20, 50, 100]
    results = []

    for lev in leverages:
        notional = calculate_notional_per_level(
            equity=equity,
            base_size=base_size,
            leverage=lev,
            n_levels=n_levels,
            risk_mode="hybrid",
            max_expo_cap=max_expo_cap
        )

        total_notional = notional * n_levels
        is_capped = total_notional >= equity * max_expo_cap - 0.01  # Tolerance

        results.append({
            'leverage': lev,
            'notional_per_level': notional,
            'total_notional': total_notional,
            'capped': is_capped
        })

        print(f"Leverage {lev:3d}x: total ${total_notional:7,.2f} " +
              f"({'CAPPED' if is_capped else 'uncapped'})")

    # Validation: high leverages should be capped
    df = pd.DataFrame(results)

    # Cap activates when leverage > max_expo_cap / base_size
    cap_threshold = max_expo_cap / base_size  # 2.0 / 0.1 = 20
    print(f"\nCap threshold: leverage > {cap_threshold:.0f}x")

    for idx, row in df.iterrows():
        if row['leverage'] > cap_threshold:
            assert row['capped'], \
                f"Leverage {row['leverage']}x should be capped (> {cap_threshold:.0f}x)"
            assert abs(row['total_notional'] - equity * max_expo_cap) < 1.0, \
                f"Capped notional should be ${equity * max_expo_cap:,.2f}"

    print(f"\nTEST PASSED - Hybrid cap enforced correctly OK")

def test_neutrality_across_leverages():
    """
    Test 3: Neutrality across leverages (neutral mode)

    Neutral mode: notional should remain constant regardless of leverage

    Expected: CV < 5% across leverages 1x-100x
    """
    print("\n" + "="*80)
    print("TEST 3: NEUTRALITY ACROSS LEVERAGES (neutral mode)")
    print("="*80)

    equity = 10000
    base_size = 0.06
    n_levels = 3

    leverages = [1, 5, 10, 25, 50, 100]
    notionals = []

    for lev in leverages:
        notional = calculate_notional_per_level(
            equity=equity,
            base_size=base_size,
            leverage=lev,
            n_levels=n_levels,
            risk_mode="neutral"
        )
        notionals.append(notional)
        print(f"Leverage {lev:3d}x: ${notional:,.2f} per level")

    # Validation: CV < 5%
    notionals_array = np.array(notionals)
    mean_notional = notionals_array.mean()
    std_notional = notionals_array.std()
    cv = (std_notional / mean_notional) * 100

    print(f"\nMean notional: ${mean_notional:,.2f}")
    print(f"Std dev: ${std_notional:,.2f}")
    print(f"CV: {cv:.2f}%")

    assert cv < 5.0, f"CV should be < 5% for neutral mode, got {cv:.2f}%"
    assert cv < 0.01, f"CV should be ~0% for neutral mode (formula is constant), got {cv:.2f}%"

    print(f"\nTEST PASSED - Neutrality confirmed (CV = {cv:.4f}%) OK")

def test_monotonicity_scaling():
    """
    Test 4: Monotonicity of notional (scaling mode)

    Scaling mode: notional should grow linearly with leverage

    Expected: notional(10x) = 2 * notional(5x)
    """
    print("\n" + "="*80)
    print("TEST 4: MONOTONICITY (scaling mode)")
    print("="*80)

    equity = 10000
    base_size = 0.05
    n_levels = 3

    leverages = [1, 5, 10, 25, 50]
    notionals = []

    for lev in leverages:
        notional = calculate_notional_per_level(
            equity=equity,
            base_size=base_size,
            leverage=lev,
            n_levels=n_levels,
            risk_mode="scaling"
        )
        notionals.append(notional)
        print(f"Leverage {lev:3d}x: ${notional:,.2f} per level")

    # Validation: linear growth
    for i in range(len(leverages) - 1):
        ratio_leverage = leverages[i+1] / leverages[i]
        ratio_notional = notionals[i+1] / notionals[i]

        print(f"\n  {leverages[i]}x -> {leverages[i+1]}x:")
        print(f"    Leverage ratio: {ratio_leverage:.2f}x")
        print(f"    Notional ratio: {ratio_notional:.2f}x")

        assert abs(ratio_leverage - ratio_notional) < 0.01, \
            f"Notional growth should match leverage growth"

    print(f"\nTEST PASSED - Linear growth confirmed OK")

def test_margin_and_caps_interaction():
    """
    Test 5: Margin & caps interaction with risk_mode

    Test that margin_cap and exposure caps still work correctly
    across different risk modes

    Expected: Positions rejected when caps exceeded, regardless of risk_mode
    """
    print("\n" + "="*80)
    print("TEST 5: MARGIN & CAPS INTERACTION")
    print("="*80)

    df = create_test_data()
    df_list = {"BTC/USDT:USDT": df}

    base_size = 0.5  # Large size to trigger caps
    leverage = 10
    margin_cap = 0.3  # Very restrictive (30% equity)

    for risk_mode in ["neutral", "scaling"]:
        print(f"\n--- Testing {risk_mode.upper()} mode ---")

        params = {
            "BTC/USDT:USDT": {
                "src": "close",
                "ma_base_window": 7,
                "envelopes": [0.05, 0.10, 0.15],
                "size": 0.5  # Legacy (ignored with base_size)
            }
        }

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
            gross_cap=5.0,  # High to not interfere
            per_side_cap=5.0,
            per_pair_cap=5.0,
            margin_cap=margin_cap,  # Restrictive
            use_kill_switch=False,
            risk_mode=risk_mode,
            base_size=base_size,
            max_expo_cap=2.0
        )

        # Check if margin_cap was triggered
        counters = bt_result['event_counters']
        rejected_margin = counters.get('rejected_by_margin_cap', 0)

        print(f"  Trades executed: {len(bt_result['trades'])}")
        print(f"  Rejected by margin_cap: {rejected_margin}")

        # In scaling mode, notional is higher -> more likely to hit margin_cap
        if risk_mode == "scaling":
            assert rejected_margin > 0, "Scaling mode should trigger margin_cap with large base_size"

    print(f"\nTEST PASSED - Caps enforced across all risk modes OK")

def test_performance_fees_scaling():
    """
    Test 6: Performance/fees scaling

    Scaling mode should have higher fees (proportional to notional)
    compared to neutral mode on same scenario

    Expected: fees_scaling > fees_neutral
    """
    print("\n" + "="*80)
    print("TEST 6: PERFORMANCE/FEES SCALING")
    print("="*80)

    df = create_test_data()
    df_list = {"BTC/USDT:USDT": df}

    base_size = 0.06
    leverage = 10

    params = {
        "BTC/USDT:USDT": {
            "src": "close",
            "ma_base_window": 7,
            "envelopes": [0.05, 0.10, 0.15],
            "size": 0.06  # Legacy (ignored)
        }
    }

    results = {}

    for risk_mode in ["neutral", "scaling"]:
        print(f"\n--- Running {risk_mode.upper()} backtest ---")

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
            gross_cap=10.0,
            per_side_cap=10.0,
            per_pair_cap=10.0,
            margin_cap=0.9,
            use_kill_switch=False,
            risk_mode=risk_mode,
            base_size=base_size,
            max_expo_cap=2.0
        )

        df_trades = bt_result['trades']

        if len(df_trades) > 0:
            avg_notional = df_trades['open_trade_size'].mean()
            total_fees = (df_trades.get('open_fee', pd.Series([0])).sum() +
                         df_trades.get('close_fee', pd.Series([0])).sum())
        else:
            avg_notional = 0
            total_fees = 0

        results[risk_mode] = {
            'trades': len(df_trades),
            'avg_notional': avg_notional,
            'total_fees': total_fees,
            'final_wallet': bt_result['wallet']
        }

        print(f"  Trades: {results[risk_mode]['trades']}")
        print(f"  Avg notional: ${results[risk_mode]['avg_notional']:,.2f}")
        print(f"  Total fees: ${results[risk_mode]['total_fees']:,.2f}")
        print(f"  Final wallet: ${results[risk_mode]['final_wallet']:,.2f}")

    # Validation
    print(f"\n--- COMPARISON ---")
    print(f"Notional scaling -> neutral ratio: {results['scaling']['avg_notional'] / results['neutral']['avg_notional']:.2f}x")
    print(f"Fees scaling -> neutral ratio: {results['scaling']['total_fees'] / results['neutral']['total_fees']:.2f}x")

    assert results['scaling']['avg_notional'] > results['neutral']['avg_notional'], \
        "Scaling mode should have higher notional"
    assert results['scaling']['total_fees'] > results['neutral']['total_fees'], \
        "Scaling mode should have higher fees (proportional to notional)"

    # Notional should be ~10x higher in scaling (leverage 10x)
    notional_ratio = results['scaling']['avg_notional'] / results['neutral']['avg_notional']
    assert 8 < notional_ratio < 12, \
        f"Notional scaling/neutral ratio should be ~10x (leverage), got {notional_ratio:.2f}x"

    print(f"\nTEST PASSED - Fees scale with notional OK")

if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTS V2 RISK_MODE")
    print("="*80)

    test_neutral_vs_scaling()
    test_hybrid_cap_enforcement()
    test_neutrality_across_leverages()
    test_monotonicity_scaling()
    test_margin_and_caps_interaction()
    test_performance_fees_scaling()

    print("\n" + "="*80)
    print("TOUS LES TESTS PASSES OK")
    print("="*80)
