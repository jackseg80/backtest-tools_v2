# === TABLEAU COMPARATIF RISK_MODE x LEVERAGE ===
# Cellule a ajouter au notebook multi_envelope.ipynb

import pandas as pd
import numpy as np

print("\n" + "="*100)
print("TABLEAU COMPARATIF: RISK_MODE x LEVERAGE")
print("="*100)

# Configuration des tests
risk_modes_to_test = ["neutral", "scaling", "hybrid"]
leverages_to_test = [1, 10, 50, 100]

# Parametres fixes
test_wallet = 1000
test_base_size = 0.06
test_max_expo_cap = 2.0
test_stop_loss = 0.2
test_maker_fee = 0.0002
test_taker_fee = 0.0006

results = []

for risk_mode_test in risk_modes_to_test:
    for lev_test in leverages_to_test:
        print(f"\nRunning: risk_mode={risk_mode_test}, leverage={lev_test}x")

        # Reinitialize strategy
        strat = EnvelopeMulti(df_list=df_list, oldest_pair=oldest_pair, type=type, params=params)
        strat.populate_indicators()
        strat.populate_buy_sell()

        # Run backtest
        bt_result = strat.run_backtest(
            initial_wallet=test_wallet,
            leverage=lev_test,
            maker_fee=test_maker_fee,
            taker_fee=test_taker_fee,
            stop_loss=test_stop_loss,
            reinvest=False,
            liquidation=True,
            gross_cap=10.0,  # High to not interfere
            per_side_cap=10.0,
            per_pair_cap=5.0,
            margin_cap=0.9,
            use_kill_switch=False,  # Disable for clean comparison
            auto_adjust_size=True,
            extreme_leverage_threshold=50,
            risk_mode=risk_mode_test,
            base_size=test_base_size,
            max_expo_cap=test_max_expo_cap
        )

        df_trades_test = bt_result['trades']

        # Extract metrics
        if len(df_trades_test) > 0:
            perf_pct = ((bt_result['wallet'] / test_wallet) - 1) * 100
            sharpe = bt_result.get('sharpe_ratio', 0)
            sortino = bt_result.get('sortino_ratio', 0)
            trades_count = len(df_trades_test)
            liquidations_count = len(df_trades_test[df_trades_test['close_reason'] == 'Liquidation'])
            total_fees = (df_trades_test.get('open_fee', pd.Series([0])).sum() +
                         df_trades_test.get('close_fee', pd.Series([0])).sum())
            avg_notional = df_trades_test['open_trade_size'].mean()

            # Max drawdown (from days)
            df_days_test = bt_result['days']
            if len(df_days_test) > 0:
                max_dd = df_days_test['drawdown'].min()
            else:
                max_dd = 0

            # Avg used margin (if available)
            if not bt_result.get('margin_history', pd.DataFrame()).empty:
                avg_margin = bt_result['margin_history']['used_margin'].mean()
            else:
                avg_margin = 0
        else:
            perf_pct = 0
            sharpe = 0
            sortino = 0
            trades_count = 0
            liquidations_count = 0
            total_fees = 0
            avg_notional = 0
            max_dd = 0
            avg_margin = 0

        results.append({
            'risk_mode': risk_mode_test,
            'leverage': lev_test,
            'perf_%': perf_pct,
            'sharpe': sharpe,
            'sortino': sortino,
            '#trades': trades_count,
            '#liq': liquidations_count,
            'fees_$': total_fees,
            'avg_notional_$': avg_notional,
            'max_dd_%': max_dd * 100,
            'avg_margin_$': avg_margin
        })

# Create DataFrame
df_comparison = pd.DataFrame(results)

# Display
print("\n" + "="*100)
print("RESULTATS COMPARATIFS")
print("="*100)

# Format for display
df_display = df_comparison.copy()
df_display['perf_%'] = df_display['perf_%'].apply(lambda x: f"{x:.2f}%")
df_display['sharpe'] = df_display['sharpe'].apply(lambda x: f"{x:.2f}")
df_display['sortino'] = df_display['sortino'].apply(lambda x: f"{x:.2f}")
df_display['fees_$'] = df_display['fees_$'].apply(lambda x: f"${x:.2f}")
df_display['avg_notional_$'] = df_display['avg_notional_$'].apply(lambda x: f"${x:.0f}")
df_display['max_dd_%'] = df_display['max_dd_%'].apply(lambda x: f"{x:.1f}%")
df_display['avg_margin_$'] = df_display['avg_margin_$'].apply(lambda x: f"${x:.0f}")

print(df_display.to_string(index=False))

# Key insights
print("\n" + "="*100)
print("INSIGHTS CLES")
print("="*100)

# Neutral vs Scaling @ 10x
neutral_10x = df_comparison[(df_comparison['risk_mode']=='neutral') & (df_comparison['leverage']==10)]
scaling_10x = df_comparison[(df_comparison['risk_mode']=='scaling') & (df_comparison['leverage']==10)]

if len(neutral_10x) > 0 and len(scaling_10x) > 0:
    notional_ratio = scaling_10x['avg_notional_$'].values[0] / neutral_10x['avg_notional_$'].values[0]
    fees_ratio = scaling_10x['fees_$'].values[0] / neutral_10x['fees_$'].values[0]

    print(f"\n1. Neutral vs Scaling @ 10x:")
    print(f"   - Notional ratio: {notional_ratio:.2f}x (expected ~10x)")
    print(f"   - Fees ratio: {fees_ratio:.2f}x")
    print(f"   - Perf delta: {scaling_10x['perf_%'].values[0] - neutral_10x['perf_%'].values[0]:.2f}%")

# Neutrality check (notional constant across leverage)
neutral_results = df_comparison[df_comparison['risk_mode']=='neutral']
if len(neutral_results) > 1:
    notional_cv = (neutral_results['avg_notional_$'].std() / neutral_results['avg_notional_$'].mean()) * 100
    print(f"\n2. Neutralite (neutral mode):")
    print(f"   - CV notional across leverages: {notional_cv:.2f}% (expected <5%)")

# Hybrid cap activation
hybrid_results = df_comparison[df_comparison['risk_mode']=='hybrid']
if len(hybrid_results) > 0:
    cap_threshold = test_max_expo_cap / test_base_size  # 2.0 / 0.06 = 33.3x
    print(f"\n3. Hybrid cap:")
    print(f"   - Cap activates @ leverage > {cap_threshold:.0f}x")
    hybrid_high_lev = hybrid_results[hybrid_results['leverage'] > cap_threshold]
    if len(hybrid_high_lev) > 0:
        capped_notional = hybrid_high_lev['avg_notional_$'].values[0]
        expected_cap = test_wallet * test_max_expo_cap / 3  # 3 levels
        print(f"   - Capped notional: ${capped_notional:.0f} (expected ~${expected_cap:.0f})")

print("\n" + "="*100)
