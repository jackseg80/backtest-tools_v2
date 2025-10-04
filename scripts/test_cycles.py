"""
Test de la strategie EnvelopeMulti sur differentes phases de cycles crypto
"""
import sys
import os
# Force UTF-8 encoding for Windows console
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

sys.path.append('.')
import pandas as pd
pd.options.mode.chained_assignment = None
import nest_asyncio
nest_asyncio.apply()

from utilities.strategies.envelopeMulti_v2 import EnvelopeMulti_v2 as EnvelopeMulti
from utilities.data_manager import ExchangeDataManager
from utilities.bt_analysis import multi_backtest_analysis

# Configuration identique au notebook (alignée avec le live)
BACKTEST_LEVERAGE = 10

ma_base_window_std = 7
envelope_std = [0.07, 0.1, 0.15, 0.2]
size_std = 0.06

# Params live (seront ajustés automatiquement)
params_live = {
    "BTC/USDT:USDT": {"src": "close", "ma_base_window": 7, "envelopes": [0.07, 0.1, 0.15], "size": 0.1},
    "ETH/USDT:USDT": {"src": "close", "ma_base_window": 7, "envelopes": [0.07, 0.1, 0.12], "size": 0.1},
    "BNB/USDT:USDT": {"src": "close", "ma_base_window": 8, "envelopes": [0.07, 0.1, 0.12], "size": 0.1},
    "SOL/USDT:USDT": {"src": "close", "ma_base_window": ma_base_window_std, "envelopes": [0.07, 0.1, 0.12], "size": size_std},
    "ADA/USDT:USDT": {"src": "close", "ma_base_window": 8, "envelopes": [0.07, 0.1, 0.14, 0.18], "size": 0.1},
    "AVAX/USDT:USDT": {"src": "close", "ma_base_window": 6, "envelopes": [0.08, 0.1, 0.15, 0.2], "size": 0.1},
    "DOGE/USDT:USDT": {"src": "close", "ma_base_window": ma_base_window_std, "envelopes": envelope_std, "size": size_std},
}

# Ajustement automatique des size pour backtest V2
params = {}
for pair, p in params_live.items():
    params[pair] = p.copy()
    params[pair]["size"] = p["size"] / BACKTEST_LEVERAGE

# Phases de cycles crypto (basees sur l'historique Bitcoin)
cycles = {
    "Bull 2020-2021": {"start": "2020-04-01", "end": "2021-11-30", "description": "COVID bottom to ATH 69k"},
    "Bear 2022": {"start": "2022-01-01", "end": "2022-12-31", "description": "Crash Luna, FTX, crypto winter"},
    "Recovery 2023": {"start": "2023-01-01", "end": "2023-12-31", "description": "Bottom 15k to Recovery 44k"},
    "Bull 2024": {"start": "2024-01-01", "end": "2024-12-31", "description": "ETF Bitcoin, new ATH"},
}

# Paramètres backtest
initial_wallet = 1000
leverage = BACKTEST_LEVERAGE
stop_loss = 0.25
reinvest = True  # Aligné avec le live
liquidation = True
type_strat = ["long", ""]
maker_fee, taker_fee = 0.0002, 0.0006

# Paramètres V2
gross_cap = 5
per_side_cap = 4
per_pair_cap = 1.2
margin_cap = 0.9
use_kill_switch = False
risk_mode = "scaling"
max_expo_cap = 2.5
auto_adjust_size = False
extreme_leverage_threshold = 50

# Charger les données
print("Chargement des donnees...")
exchange = ExchangeDataManager(exchange_name="binance", path_download="./database/exchanges")
pair_list = list(params.keys())
oldest_pair = "BTC/USDT:USDT"
tf = '1h'

df_list_full = {}
for pair in pair_list:
    df = exchange.load_data(pair, tf)
    df_list_full[pair] = df.loc["2020-04-01":]

print("Donnees chargees\n")

# Résultats par cycle
results = {}

for cycle_name, cycle_info in cycles.items():
    print(f"\n{'='*60}")
    print(f"TEST: {cycle_name}")
    print(f"Periode: {cycle_info['start']} -> {cycle_info['end']}")
    print(f"Info: {cycle_info['description']}")
    print(f"{'='*60}\n")

    # Filtrer les données pour cette période
    df_list = {}
    for pair in pair_list:
        df_list[pair] = df_list_full[pair].loc[cycle_info['start']:cycle_info['end']]

    # Verifier si on a des donnees
    if df_list[oldest_pair].empty:
        print(f"Pas de donnees pour cette periode\n")
        continue

    # Exécuter le backtest avec V2
    strat = EnvelopeMulti(df_list=df_list, oldest_pair=oldest_pair, type=type_strat, params=params)
    strat.populate_indicators()
    strat.populate_buy_sell()
    bt_result = strat.run_backtest(
        initial_wallet=initial_wallet,
        leverage=leverage,
        maker_fee=maker_fee,
        taker_fee=taker_fee,
        stop_loss=stop_loss,
        reinvest=reinvest,
        liquidation=liquidation,
        gross_cap=gross_cap,
        per_side_cap=per_side_cap,
        per_pair_cap=per_pair_cap,
        margin_cap=margin_cap,
        use_kill_switch=use_kill_switch,
        auto_adjust_size=auto_adjust_size,
        extreme_leverage_threshold=extreme_leverage_threshold,
        risk_mode=risk_mode,
        max_expo_cap=max_expo_cap
    )

    # Analyser les résultats
    df_trades, df_days = multi_backtest_analysis(
        trades=bt_result['trades'],
        days=bt_result['days'],
        leverage=leverage,
        general_info=True,
        trades_info=False,
        days_info=False,
        long_short_info=False,
        entry_exit_info=False,
        exposition_info=False,
        pair_info=False,
        indepedant_trade=False
    )

    # Stocker les métriques clés
    if not df_trades.empty:
        results[cycle_name] = {
            "wallet_final": bt_result['wallet'],
            "performance": ((bt_result['wallet'] - initial_wallet) / initial_wallet) * 100,
            "sharpe": bt_result['sharpe_ratio'],
            "nb_trades": len(df_trades),
            "win_rate": (df_trades['trade_result'] > 0).sum() / len(df_trades) * 100,
            "profit_moyen": df_trades['trade_result_pct'].mean() * 100,
            "pire_trade": df_trades['trade_result_pct'].min() * 100,
            "meilleur_trade": df_trades['trade_result_pct'].max() * 100,
            "stop_loss": (df_trades['close_reason'] == 'Stop Loss').sum(),
            "jours": len(df_days)
        }

        # Sauvegarder les trades detailles pour ce cycle
        cycle_safe_name = cycle_name.replace(" ", "_").replace("-", "_")
        output_dir = "scripts/resultats"
        trades_file = f"{output_dir}/trades_{cycle_safe_name}.csv"
        days_file = f"{output_dir}/days_{cycle_safe_name}.csv"

        df_trades.to_csv(trades_file, encoding='utf-8')
        df_days.to_csv(days_file, encoding='utf-8')

        print(f"  -> Trades sauvegardes: {trades_file}")
        print(f"  -> Jours sauvegardes: {days_file}")
    else:
        results[cycle_name] = {"error": "Aucun trade"}

    print(f"\n")

# Comparaison finale
print("\n" + "="*80)
print("COMPARAISON DES CYCLES")
print("="*80 + "\n")

comparison = pd.DataFrame(results).T
comparison = comparison.round(2)
print(comparison.to_string())

# Sauvegarder les resultats en CSV
output_file = "scripts/resultats/backtest_cycles_results.csv"
comparison.to_csv(output_file, encoding='utf-8')
print(f"\nResultats sauvegardes dans: {output_file}")

print("\n" + "="*80)
print("ANALYSE COMPARATIVE")
print("="*80 + "\n")

for cycle_name, metrics in results.items():
    if 'error' not in metrics:
        print(f"\n{cycle_name}:")
        print(f"   Performance: {metrics['performance']:.2f}% (Sharpe: {metrics['sharpe']:.2f})")
        print(f"   Trades: {metrics['nb_trades']} (Win rate: {metrics['win_rate']:.1f}%)")
        print(f"   Stop Loss declenches: {metrics['stop_loss']}")
        print(f"   Range P&L: {metrics['pire_trade']:.2f}% -> {metrics['meilleur_trade']:.2f}%")
