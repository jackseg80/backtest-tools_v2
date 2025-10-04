"""
Reporting utilities for V2 engine

Provides detailed analysis and comparison tools for V2 backtests
"""

import pandas as pd

def print_v2_report(bt_result):
    """
    Print detailed V2 reporting including:
    - Event counters (rejections, liquidations, fills)
    - Fee breakdown (maker/taker)
    - Exposure & margin stats
    - Config summary
    """

    if 'event_counters' not in bt_result:
        print("V1 result detected - no V2 reporting available")
        return

    counters = bt_result['event_counters']
    config = bt_result['config']

    print("\n" + "="*80)
    print("V2 ENGINE - DETAILED REPORTING")
    print("="*80)

    # Configuration
    print("\nCONFIGURATION:")
    print(f"  Leverage: {config['leverage']}x")
    print(f"  Auto-adjust size: {config['auto_adjust_size']}")
    print(f"  Gross cap: {config['gross_cap']:.2f}x")
    print(f"  Per-side cap: {config['per_side_cap']:.2f}x")
    print(f"  Per-pair cap: {config['per_pair_cap']:.2f}x")
    if config['leverage'] > config['extreme_leverage_threshold']:
        print(f"  Effective per-pair cap: {config['effective_per_pair_cap']:.2f}x (reduced for extreme leverage)")
    print(f"  Margin cap: {config['margin_cap']:.2f}x")

    # Event Counters
    print("\nEVENT COUNTERS:")

    total_rejections = (counters['rejected_by_gross_cap'] +
                       counters['rejected_by_per_side_cap'] +
                       counters['rejected_by_per_pair_cap'] +
                       counters['rejected_by_margin_cap'])

    if total_rejections > 0:
        print(f"  Total rejections: {total_rejections}")
        if counters['rejected_by_gross_cap'] > 0:
            print(f"    - Gross cap: {counters['rejected_by_gross_cap']}")
        if counters['rejected_by_per_side_cap'] > 0:
            print(f"    - Per-side cap: {counters['rejected_by_per_side_cap']}")
        if counters['rejected_by_per_pair_cap'] > 0:
            print(f"    - Per-pair cap: {counters['rejected_by_per_pair_cap']}")
        if counters['rejected_by_margin_cap'] > 0:
            print(f"    - Margin cap: {counters['rejected_by_margin_cap']}")
    else:
        print(f"  Total rejections: 0 (no caps hit)")

    print(f"\n  Liquidations: {counters.get('hit_liquidation', 0)}")
    print(f"  Stop-loss: {counters.get('hit_stop_loss', 0)}")
    print(f"  MA base closes: {counters.get('close_ma_base', 0)}")

    # Fees
    print("\nFEE BREAKDOWN:")
    total_fills = counters.get('maker_fills', 0) + counters.get('taker_fills', 0)
    total_fees = counters.get('total_maker_fees', 0) + counters.get('total_taker_fees', 0)

    if total_fills > 0:
        maker_pct = (counters.get('maker_fills', 0) / total_fills) * 100
        taker_pct = (counters.get('taker_fills', 0) / total_fills) * 100

        print(f"  Total fills: {total_fills}")
        print(f"    - Maker: {counters.get('maker_fills', 0)} ({maker_pct:.1f}%)")
        print(f"    - Taker: {counters.get('taker_fills', 0)} ({taker_pct:.1f}%)")

        print(f"\n  Total fees: ${total_fees:.2f}")
        print(f"    - Maker fees: ${counters.get('total_maker_fees', 0):.2f}")
        print(f"    - Taker fees: ${counters.get('total_taker_fees', 0):.2f}")
    else:
        print(f"  No fills recorded")

    # Exposure & Margin (if available)
    if not bt_result['exposure_history'].empty:
        df_exp = bt_result['exposure_history']
        print("\nEXPOSURE STATS:")
        print(f"  Max gross exposure: ${df_exp['gross_exposure'].max():,.2f}")
        print(f"  Avg gross exposure: ${df_exp['gross_exposure'].mean():,.2f}")
        print(f"  Max per-side (LONG): ${df_exp.get('long_exposure', pd.Series([0])).max():,.2f}")
        print(f"  Max per-side (SHORT): ${df_exp.get('short_exposure', pd.Series([0])).max():,.2f}")

    if not bt_result['margin_history'].empty:
        df_margin = bt_result['margin_history']
        print("\nMARGIN STATS:")
        print(f"  Max used margin: ${df_margin['used_margin'].max():,.2f}")
        print(f"  Avg used margin: ${df_margin['used_margin'].mean():,.2f}")
        max_margin_ratio = df_margin['margin_ratio'].max() if 'margin_ratio' in df_margin else 0
        print(f"  Max margin ratio: {max_margin_ratio:.1%}")

    print("\n" + "="*80)


def compare_v1_v2(result_v1, result_v2):
    """
    Compare V1 vs V2 results side-by-side

    Returns DataFrame with comparative metrics
    """

    metrics = {
        'Metric': [],
        'V1 (Legacy)': [],
        'V2 (Fixed)': [],
        'Delta': [],
        'Delta %': []
    }

    def add_metric(name, v1_val, v2_val, format_str=".2f", is_pct=False):
        metrics['Metric'].append(name)
        metrics['V1 (Legacy)'].append(v1_val)
        metrics['V2 (Fixed)'].append(v2_val)

        delta = v2_val - v1_val
        metrics['Delta'].append(delta)

        if v1_val != 0:
            delta_pct = (delta / abs(v1_val)) * 100
        else:
            delta_pct = 0 if delta == 0 else float('inf')
        metrics['Delta %'].append(delta_pct)

    # Core metrics
    add_metric("Final Wallet ($)", result_v1['wallet'], result_v2['wallet'])

    profit_pct_v1 = ((result_v1['wallet'] / 1000) - 1) * 100  # Assume initial 1000
    profit_pct_v2 = ((result_v2['wallet'] / 1000) - 1) * 100
    add_metric("Profit %", profit_pct_v1, profit_pct_v2)

    add_metric("Sharpe Ratio",
               result_v1.get('sharpe_ratio', 0),
               result_v2.get('sharpe_ratio', 0))

    add_metric("Win Rate %",
               result_v1.get('win_rate', 0) * 100,
               result_v2.get('win_rate', 0) * 100)

    add_metric("Total Trades",
               len(result_v1['trades']),
               len(result_v2['trades']))

    # V2-specific metrics
    if 'event_counters' in result_v2:
        liqs = result_v2['event_counters'].get('hit_liquidation', 0)
        add_metric("Liquidations (V2)", 0, liqs)

        stops = result_v2['event_counters'].get('hit_stop_loss', 0)
        add_metric("Stop-Loss (V2)", 0, stops)

    df = pd.DataFrame(metrics)

    # Format for display
    df['V1 (Legacy)'] = df.apply(lambda row: f"{row['V1 (Legacy)']:.2f}"
                                   if isinstance(row['V1 (Legacy)'], (int, float))
                                   else row['V1 (Legacy)'], axis=1)
    df['V2 (Fixed)'] = df.apply(lambda row: f"{row['V2 (Fixed)']:.2f}"
                                  if isinstance(row['V2 (Fixed)'], (int, float))
                                  else row['V2 (Fixed)'], axis=1)
    df['Delta'] = df.apply(lambda row: f"{row['Delta']:.2f}"
                           if isinstance(row['Delta'], (int, float))
                           else row['Delta'], axis=1)
    df['Delta %'] = df.apply(lambda row: f"{row['Delta %']:.1f}%"
                             if isinstance(row['Delta %'], (int, float)) and row['Delta %'] != float('inf')
                             else "N/A", axis=1)

    return df


def analyze_liquidations(bt_result):
    """
    Detailed liquidation analysis for V2

    Returns DataFrame with liquidation details
    """

    if 'event_counters' not in bt_result:
        print("V1 result - no liquidation tracking")
        return None

    df_trades = bt_result['trades']

    if df_trades.empty:
        print("No trades found")
        return None

    liq_trades = df_trades[df_trades['close_reason'] == 'Liquidation']

    if liq_trades.empty:
        print("No liquidations found")
        return None

    print(f"\n{'='*80}")
    print(f"LIQUIDATION ANALYSIS ({len(liq_trades)} liquidations)")
    print(f"{'='*80}\n")

    for idx, trade in liq_trades.iterrows():
        entry = trade['open_price']
        liq = trade['close_price']
        drop_pct = ((liq / entry) - 1) * 100

        print(f"{trade['pair']} - {trade['position']}")
        print(f"  Date: {trade['close_date']}")
        print(f"  Entry: ${entry:,.2f}")
        print(f"  Liquidation: ${liq:,.2f}")
        print(f"  Drop: {drop_pct:.2f}%")
        print(f"  Wallet after: ${trade['wallet']:,.2f}\n")

    return liq_trades[['pair', 'position', 'open_date', 'close_date',
                       'open_price', 'close_price', 'wallet']]
