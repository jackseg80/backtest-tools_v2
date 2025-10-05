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

# ============================================================================
# CONFIGURATION OPTIMISÉE FINALE (Validée 2025-10-05)
# ============================================================================
# MA = 5 (global)
# Size = 0.12 (uniforme - meilleure performance que size variable)
# Envelopes = 3 ou 4 selon volatilité (data-driven mapping)
# ============================================================================

BACKTEST_LEVERAGE = 10

# Config globale harmonisée
MA_OPTIMALE = 5
SIZE_UNIFORME = 0.12  # Validé: +11.96% perf vs size variable

# Mapping 3/4 envelopes basé sur volatilité (envelope_count_mapping.csv)
ENVELOPE_MAPPING = {
    # 4 envelopes (haute volatilité >= 1.21%)
    "BNB/USDT:USDT": [0.07, 0.1, 0.12, 0.15],
    "SUSHI/USDT:USDT": [0.07, 0.1, 0.12, 0.15],
    "FET/USDT:USDT": [0.07, 0.1, 0.12, 0.15],
    "MAGIC/USDT:USDT": [0.07, 0.1, 0.12, 0.15],
    "AR/USDT:USDT": [0.07, 0.1, 0.12, 0.15],
    "GALA/USDT:USDT": [0.07, 0.1, 0.12, 0.15],
    "DYDX/USDT:USDT": [0.07, 0.1, 0.12, 0.15],

    # 3 envelopes (volatilité standard < 1.21%)
    "BTC/USDT:USDT": [0.07, 0.1, 0.15],
    "ETH/USDT:USDT": [0.07, 0.1, 0.15],
    "SOL/USDT:USDT": [0.07, 0.1, 0.15],
    "ADA/USDT:USDT": [0.07, 0.1, 0.15],
    "AVAX/USDT:USDT": [0.07, 0.1, 0.15],
    "TRX/USDT:USDT": [0.07, 0.1, 0.15],
    "EGLD/USDT:USDT": [0.07, 0.1, 0.15],
    "KSM/USDT:USDT": [0.07, 0.1, 0.15],
    "ACH/USDT:USDT": [0.07, 0.1, 0.15],
    "APE/USDT:USDT": [0.07, 0.1, 0.15],
    "CRV/USDT:USDT": [0.07, 0.1, 0.15],
    "DOGE/USDT:USDT": [0.07, 0.1, 0.15],
    "ENJ/USDT:USDT": [0.07, 0.1, 0.15],
    "ICP/USDT:USDT": [0.07, 0.1, 0.15],
    "IMX/USDT:USDT": [0.07, 0.1, 0.15],
    "LDO/USDT:USDT": [0.07, 0.1, 0.15],
    "NEAR/USDT:USDT": [0.07, 0.1, 0.15],
    "SAND/USDT:USDT": [0.07, 0.1, 0.15],
    "THETA/USDT:USDT": [0.07, 0.1, 0.15],
    "UNI/USDT:USDT": [0.07, 0.1, 0.15],
    "XTZ/USDT:USDT": [0.07, 0.1, 0.15],
}

# Params optimisés (seront ajustés automatiquement pour V2)
params_live = {}
for pair, envelopes in ENVELOPE_MAPPING.items():
    params_live[pair] = {
        "src": "close",
        "ma_base_window": MA_OPTIMALE,
        "envelopes": envelopes,
        "size": SIZE_UNIFORME,
    }

# Ajustement automatique des size pour backtest V2
params = {}
for pair, p in params_live.items():
    params[pair] = p.copy()
    params[pair]["size"] = p["size"] / BACKTEST_LEVERAGE

cycles = {
    "Bull 2020-2021": {"start": "2020-03-13", "end": "2021-11-10"},
    "Bear 2021-2022": {"start": "2021-11-10", "end": "2022-11-21"},
    "Recovery 2023": {"start": "2022-11-22", "end": "2023-12-31"},
    "Bull 2024": {"start": "2024-01-01", "end": "2025-10-03"},
    "COMPLET 2020-2024": {"start": "2020-03-13", "end": "2025-10-03"},
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
    {"name": "SHORT ONLY", "type": ["", "short"]},
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
from datetime import datetime
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
output_file = f"scripts/resultats/backtest_cycles_detailed_{timestamp}.txt"
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
