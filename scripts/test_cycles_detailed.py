"""
Test de la strategie EnvelopeMulti avec sauvegarde dans un fichier texte
"""
import sys
import os
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

sys.path.append('.')
import pandas as pd
import numpy as np
pd.options.mode.chained_assignment = None
import nest_asyncio
nest_asyncio.apply()

from utilities.strategies.envelopeMulti_v2 import EnvelopeMulti_v2 as EnvelopeMulti
from utilities.data_manager import ExchangeDataManager
from utilities.bt_analysis import multi_backtest_analysis

# Configuration identique au notebook (alignée avec le live) - TOUTES LES 28 PAIRES
BACKTEST_LEVERAGE = 10

ma_base_window_std = 7
envelope_std = [0.07, 0.1, 0.15, 0.2]
size_std = 0.06

# Params live (seront ajustés automatiquement pour V2)
params_live = {
    "BTC/USDT:USDT":{ "src": "close", "ma_base_window": 7, "envelopes": [0.07, 0.1, 0.15], "size": 0.1,},
    "ETH/USDT:USDT":{ "src": "close", "ma_base_window": 7, "envelopes": [0.07, 0.1, 0.12], "size": 0.1,},
    "BNB/USDT:USDT":{ "src": "close", "ma_base_window": 8, "envelopes": [0.07, 0.1, 0.12], "size": 0.1,},
    "SOL/USDT:USDT":{ "src": "close", "ma_base_window": ma_base_window_std, "envelopes": [0.07, 0.1, 0.12], "size": size_std,},
    "ADA/USDT:USDT":{ "src": "close", "ma_base_window": 8, "envelopes": [0.07, 0.1, 0.14, 0.18], "size": 0.1,},
    "AR/USDT:USDT":{ "src": "close", "ma_base_window": 6, "envelopes": [0.05, 0.08, 0.1, 0.12], "size": size_std,},
    "AVAX/USDT:USDT":{ "src": "close", "ma_base_window": 6, "envelopes": [0.08, 0.1, 0.15, 0.2], "size": 0.1,},
    "TRX/USDT:USDT":{ "src": "close", "ma_base_window": 8, "envelopes": [0.08, 0.12, 0.15], "size": 0.05,},
    "EGLD/USDT:USDT":{ "src": "close", "ma_base_window": ma_base_window_std, "envelopes": envelope_std, "size": size_std,},
    "KSM/USDT:USDT":{ "src": "close", "ma_base_window": ma_base_window_std, "envelopes": envelope_std, "size": size_std,},
    "ACH/USDT:USDT":{ "src": "close", "ma_base_window": ma_base_window_std, "envelopes": envelope_std, "size": size_std,},
    "APE/USDT:USDT":{ "src": "close", "ma_base_window": ma_base_window_std, "envelopes": envelope_std, "size": size_std,},
    "CRV/USDT:USDT":{ "src": "close", "ma_base_window": ma_base_window_std, "envelopes": envelope_std, "size": size_std,},
    "DOGE/USDT:USDT":{ "src": "close", "ma_base_window": ma_base_window_std, "envelopes": envelope_std, "size": size_std,},
    "DYDX/USDT:USDT":{ "src": "close", "ma_base_window": ma_base_window_std, "envelopes": envelope_std, "size": size_std,},
    "ENJ/USDT:USDT":{ "src": "close", "ma_base_window": ma_base_window_std, "envelopes": envelope_std, "size": size_std,},
    "FET/USDT:USDT":{ "src": "close", "ma_base_window": ma_base_window_std, "envelopes": envelope_std, "size": size_std,},
    "GALA/USDT:USDT":{ "src": "close", "ma_base_window": 5, "envelopes": envelope_std, "size": size_std,},
    "ICP/USDT:USDT":{ "src": "close", "ma_base_window": ma_base_window_std, "envelopes": envelope_std, "size": size_std,},
    "IMX/USDT:USDT":{ "src": "close", "ma_base_window": ma_base_window_std, "envelopes": envelope_std, "size": size_std,},
    "LDO/USDT:USDT":{ "src": "close", "ma_base_window": ma_base_window_std, "envelopes": envelope_std, "size": size_std,},
    "MAGIC/USDT:USDT":{ "src": "close", "ma_base_window": ma_base_window_std, "envelopes": envelope_std, "size": size_std,},
    # "MATIC/USDT:USDT":{ "src": "close", "ma_base_window": ma_base_window_std, "envelopes": envelope_std, "size": size_std,},  # Désactivé en live
    "NEAR/USDT:USDT":{ "src": "close", "ma_base_window": 5, "envelopes": envelope_std, "size": size_std,},
    "SAND/USDT:USDT":{ "src": "close", "ma_base_window": ma_base_window_std, "envelopes": envelope_std, "size": size_std,},
    "SUSHI/USDT:USDT":{ "src": "close", "ma_base_window": 8, "envelopes": envelope_std, "size": size_std,},
    "THETA/USDT:USDT":{ "src": "close", "ma_base_window": 5, "envelopes": envelope_std, "size": size_std,},
    "UNI/USDT:USDT":{ "src": "close", "ma_base_window": ma_base_window_std, "envelopes": envelope_std, "size": size_std,},
    "XTZ/USDT:USDT":{ "src": "close", "ma_base_window": ma_base_window_std, "envelopes": envelope_std, "size": size_std,},
}

# Ajustement automatique des size pour backtest V2
params = {}
for pair, p in params_live.items():
    params[pair] = p.copy()
    params[pair]["size"] = p["size"] / BACKTEST_LEVERAGE

cycles = {
    "Bull 2020-2021": {"start": "2020-04-01", "end": "2021-11-30"},
    "Bear 2022": {"start": "2022-01-01", "end": "2022-12-31"},
    "Recovery 2023": {"start": "2023-01-01", "end": "2023-12-31"},
    "Bull 2024": {"start": "2024-01-01", "end": "2024-12-31"},
}

# Parametres backtest
initial_wallet = 1000
leverage = BACKTEST_LEVERAGE
stop_loss = 0.25
reinvest = True  # Aligné avec le live
liquidation = True
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

# Configurations de test
test_configs = [
    {"name": "LONG ONLY", "type": ["long", ""]},
    {"name": "LONG + SHORT", "type": ["long", "short"]}
]

# Charger les donnees
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

# Ouvrir le fichier texte pour ecrire les resultats
output_file = "scripts/resultats/backtest_cycles_detailed.txt"
with open(output_file, 'w', encoding='utf-8') as f:
    f.write("="*80 + "\n")
    f.write("BACKTESTS PAR CYCLES DE MARCHE\n")
    f.write("Strategie: EnvelopeMulti\n")
    f.write("="*80 + "\n\n")

for cycle_name, cycle_info in cycles.items():
    print(f"\n{'='*60}")
    print(f"TEST: {cycle_name}")
    print(f"Periode: {cycle_info['start']} -> {cycle_info['end']}")
    print(f"{'='*60}\n")

    # Filtrer les donnees et analyser la disponibilité
    df_list = {}
    excluded_pairs = []
    min_required_days = 30  # Minimum de jours requis pour inclure une paire

    for pair in pair_list:
        df_filtered = df_list_full[pair].loc[cycle_info['start']:cycle_info['end']]
        nb_days = len(df_filtered)

        if nb_days == 0:
            excluded_pairs.append({"pair": pair, "reason": "Aucune donnée disponible", "days": 0})
        elif nb_days < min_required_days:
            excluded_pairs.append({"pair": pair, "reason": f"Données insuffisantes ({nb_days} jours)", "days": nb_days})
        else:
            df_list[pair] = df_filtered

    if oldest_pair not in df_list or df_list[oldest_pair].empty:
        print(f"Pas de donnees pour {oldest_pair}\n")
        continue

    # Afficher les paires exclues
    if excluded_pairs:
        print(f"\n  Paires exclues pour ce cycle ({len(excluded_pairs)}):")
        for exc in excluded_pairs:
            print(f"    - {exc['pair']}: {exc['reason']}")
        print(f"\n  Paires incluses: {len(df_list)}/{len(pair_list)}")
        print(f"    -> {', '.join(list(df_list.keys()))}\n")

    # Sauvegarder les informations sur les paires dans le fichier
    with open(output_file, 'a', encoding='utf-8') as f:
        f.write("\n" + "="*80 + "\n")
        f.write(f"CYCLE: {cycle_name}\n")
        f.write(f"Periode: {cycle_info['start']} -> {cycle_info['end']}\n")
        f.write("="*80 + "\n\n")

        f.write(f"Paires testées: {len(df_list)}/{len(pair_list)}\n")
        f.write(f"Paires incluses: {', '.join(list(df_list.keys()))}\n\n")

        if excluded_pairs:
            f.write(f"Paires exclues ({len(excluded_pairs)}):\n")
            for exc in excluded_pairs:
                f.write(f"  - {exc['pair']}: {exc['reason']}\n")
            f.write("\n")

    # Tester avec LONG ONLY et LONG + SHORT
    for config in test_configs:
        print(f"  -> Test {config['name']}")

        # Backtest avec V2
        strat = EnvelopeMulti(df_list=df_list, oldest_pair=oldest_pair, type=config['type'], params=params)
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

        # Analyser et sauvegarder dans le fichier texte
        with open(output_file, 'a', encoding='utf-8') as f:
            f.write("\n" + "-"*80 + "\n")
            f.write(f"{config['name']}\n")
            f.write("-"*80 + "\n\n")

            # Capturer la sortie de multi_backtest_analysis
            import io
            from contextlib import redirect_stdout

            buffer = io.StringIO()
            with redirect_stdout(buffer):
                multi_backtest_analysis(
                    bt_result['trades'],
                    bt_result['days'],
                    leverage=leverage,
                    general_info=True,
                    trades_info=True,
                    days_info=True,
                    long_short_info=True,
                    entry_exit_info=True,
                    pair_info=True,
                    exposition_info=False,
                    indepedant_trade=True
                )

            # Ecrire dans le fichier
            f.write(buffer.getvalue())
            f.write("\n\n")

        print(f"  -> {config['name']}: Resultats sauvegardes")

print(f"\n{'='*80}")
print(f"Resultats sauvegardes dans: {output_file}")
print(f"{'='*80}")
