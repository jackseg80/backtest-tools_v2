"""
Script de backtest multi-périodes pour la stratégie Envelope Multi
Teste la stratégie sur différentes périodes pour vérifier sa robustesse
"""

import sys
sys.path.append('../..')
import pandas as pd
import numpy as np
from datetime import datetime
pd.options.mode.chained_assignment = None

from utilities.strategies.envelopeMulti_v2 import EnvelopeMulti_v2 as EnvelopeMulti
from utilities.data_manager import ExchangeDataManager

# ============================================================
# CONFIGURATION (alignée avec le notebook)
# ============================================================
BACKTEST_LEVERAGE = 10

ma_base_window_std = 7
envelope_std = [0.07, 0.1, 0.15, 0.2]
size_std = 0.06

params_live = {
    "BTC/USDT:USDT":{ "src": "close", "ma_base_window": 7, "envelopes": [0.07, 0.1, 0.15], "size": 0.1,},
    "ETH/USDT:USDT":{ "src": "close", "ma_base_window": 7, "envelopes": [0.07, 0.1, 0.12], "size": 0.1,},
    "BNB/USDT:USDT":{ "src": "close", "ma_base_window": 8, "envelopes": [0.07, 0.1, 0.12], "size": 0.1,},
    "SOL/USDT:USDT":{ "src": "close", "ma_base_window": ma_base_window_std, "envelopes": [0.07, 0.1, 0.12], "size": size_std,},
    "ADA/USDT:USDT":{ "src": "close", "ma_base_window": 8, "envelopes": [0.07, 0.1, 0.14, 0.18], "size": 0.1,},
    "AR/USDT:USDT":{ "src": "close", "ma_base_window": 6, "envelopes": [0.05, 0.08, 0.1, 0.12], "size": size_std,},
    "AVAX/USDT:USDT":{ "src": "close", "ma_base_window": 6, "envelopes": [0.08, 0.1, 0.15, 0.2], "size": 0.1,},
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
    "NEAR/USDT:USDT":{ "src": "close", "ma_base_window": 5, "envelopes": envelope_std, "size": size_std,},
    "SAND/USDT:USDT":{ "src": "close", "ma_base_window": ma_base_window_std, "envelopes": envelope_std, "size": size_std,},
    "SUSHI/USDT:USDT":{ "src": "close", "ma_base_window": 8, "envelopes": envelope_std, "size": size_std,},
    "THETA/USDT:USDT":{ "src": "close", "ma_base_window": 5, "envelopes": envelope_std, "size": size_std,},
    "TRX/USDT:USDT": {"src": "close", "ma_base_window": 8, "envelopes": [0.08, 0.12, 0.15], "size": 0.05,},
    "UNI/USDT:USDT":{ "src": "close", "ma_base_window": ma_base_window_std, "envelopes": envelope_std, "size": size_std,},
    "XTZ/USDT:USDT":{ "src": "close", "ma_base_window": ma_base_window_std, "envelopes": envelope_std, "size": size_std,},
}

# Ajustement size pour backtest
params = {}
for pair, p in params_live.items():
    params[pair] = p.copy()
    params[pair]["size"] = p["size"] / BACKTEST_LEVERAGE

# ============================================================
# PÉRIODES À TESTER
# ============================================================
periods = [
    {"name": "2020 (COVID crash)", "start": "2020-01-01", "end": "2020-12-31"},
    {"name": "2021 (Bull run)", "start": "2021-01-01", "end": "2021-12-31"},
    {"name": "2022 (Bear market)", "start": "2022-01-01", "end": "2022-12-31"},
    {"name": "2023 (Recovery)", "start": "2023-01-01", "end": "2023-12-31"},
    {"name": "2024 (Halving)", "start": "2024-01-01", "end": "2024-12-31"},
    {"name": "2025 (YTD)", "start": "2025-01-01", "end": "2025-12-31"},
    {"name": "Full period", "start": "2020-01-01", "end": "2025-12-31"},
]

# Paramètres backtest
initial_wallet = 1000
leverage = BACKTEST_LEVERAGE
reinvest = True
stop_loss = 0.25
liquidation = True
type_trade = ["long", ""]
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

# ============================================================
# CHARGEMENT DES DONNÉES
# ============================================================
print("="*100)
print("BACKTEST MULTI-PÉRIODES - Stratégie Envelope Multi")
print("="*100)
print(f"\nChargement des données...")

exchange_name = "binance"
tf = '1h'
oldest_pair = "BTC/USDT:USDT"
pair_list = list(params.keys())

exchange = ExchangeDataManager(exchange_name=exchange_name, path_download="../../database/exchanges")

# Charger toutes les données disponibles
df_list_full = {}
for pair in pair_list:
    try:
        df = exchange.load_data(pair, tf)
        df_list_full[pair] = df
    except Exception as e:
        print(f"Erreur chargement {pair}: {e}")

print(f"✅ {len(df_list_full)} paires chargées")

# ============================================================
# EXÉCUTION DES BACKTESTS
# ============================================================
results = []

for period in periods:
    print(f"\n{'='*100}")
    print(f"PÉRIODE: {period['name']} ({period['start']} → {period['end']})")
    print(f"{'='*100}")

    # Filtrer les données pour la période
    df_list_period = {}
    for pair, df in df_list_full.items():
        try:
            df_period = df.loc[period['start']:period['end']]
            if len(df_period) > 100:  # Au moins 100 bougies
                df_list_period[pair] = df_period
        except:
            pass

    if len(df_list_period) == 0:
        print(f"⚠️  Aucune donnée disponible pour cette période")
        continue

    print(f"Paires disponibles: {len(df_list_period)}")

    # Ajuster params pour les paires disponibles
    params_period = {k: v for k, v in params.items() if k in df_list_period}

    try:
        # Initialiser stratégie
        strat = EnvelopeMulti(
            df_list=df_list_period,
            oldest_pair=oldest_pair if oldest_pair in df_list_period else list(df_list_period.keys())[0],
            type=type_trade,
            params=params_period
        )

        strat.populate_indicators()
        strat.populate_buy_sell()

        # Exécuter backtest
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

        # Extraire métriques
        df_trades = pd.DataFrame(bt_result['trades'])
        df_days = pd.DataFrame(bt_result['days'])

        if len(df_trades) > 0:
            final_wallet = bt_result['wallet']
            perf_pct = ((final_wallet / initial_wallet) - 1) * 100
            sharpe = bt_result.get('sharpe_ratio', 0)
            n_trades = len(df_trades)
            win_rate = (df_trades['trade_result'] > 0).sum() / n_trades * 100
            avg_trade = df_trades['trade_result_pct'].mean() * 100
            n_liquidations = len(df_trades[df_trades['close_reason'] == 'Liquidation'])
            max_dd = df_days['drawdown'].min() * 100 if len(df_days) > 0 else 0

            # Affichage
            print(f"\n📊 RÉSULTATS:")
            print(f"   Final: {final_wallet:,.2f}$ ({perf_pct:+.2f}%)")
            print(f"   Sharpe: {sharpe:.2f}")
            print(f"   Trades: {n_trades} | Win rate: {win_rate:.1f}% | Avg: {avg_trade:+.2f}%")
            print(f"   Liquidations: {n_liquidations} ({n_liquidations/n_trades*100:.1f}%)")
            print(f"   Max DD: {max_dd:.2f}%")

            results.append({
                'period': period['name'],
                'start': period['start'],
                'end': period['end'],
                'final_$': final_wallet,
                'perf_%': perf_pct,
                'sharpe': sharpe,
                'trades': n_trades,
                'win_rate_%': win_rate,
                'avg_trade_%': avg_trade,
                'liquidations': n_liquidations,
                'liq_rate_%': n_liquidations/n_trades*100,
                'max_dd_%': max_dd,
                'pairs': len(df_list_period)
            })
        else:
            print(f"⚠️  Aucun trade exécuté")

    except Exception as e:
        print(f"❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()

# ============================================================
# TABLEAU RÉCAPITULATIF
# ============================================================
if len(results) > 0:
    print(f"\n{'='*100}")
    print(f"TABLEAU RÉCAPITULATIF")
    print(f"{'='*100}\n")

    df_results = pd.DataFrame(results)

    # Formater pour affichage
    df_display = df_results.copy()
    df_display['final_$'] = df_display['final_$'].apply(lambda x: f"${x:,.0f}")
    df_display['perf_%'] = df_display['perf_%'].apply(lambda x: f"{x:+.1f}%")
    df_display['sharpe'] = df_display['sharpe'].apply(lambda x: f"{x:.2f}")
    df_display['win_rate_%'] = df_display['win_rate_%'].apply(lambda x: f"{x:.1f}%")
    df_display['avg_trade_%'] = df_display['avg_trade_%'].apply(lambda x: f"{x:+.2f}%")
    df_display['liq_rate_%'] = df_display['liq_rate_%'].apply(lambda x: f"{x:.1f}%")
    df_display['max_dd_%'] = df_display['max_dd_%'].apply(lambda x: f"{x:.1f}%")

    # Afficher colonnes pertinentes
    cols_to_show = ['period', 'perf_%', 'sharpe', 'trades', 'win_rate_%', 'liq_rate_%', 'max_dd_%']
    print(df_display[cols_to_show].to_string(index=False))

    # Statistiques globales
    print(f"\n{'='*100}")
    print(f"STATISTIQUES GLOBALES")
    print(f"{'='*100}")
    print(f"Perf moyenne: {df_results['perf_%'].mean():.2f}%")
    print(f"Sharpe moyen: {df_results['sharpe'].mean():.2f}")
    print(f"Win rate moyen: {df_results['win_rate_%'].mean():.1f}%")
    print(f"Taux liquidation moyen: {df_results['liq_rate_%'].mean():.1f}%")
    print(f"Max DD moyen: {df_results['max_dd_%'].mean():.1f}%")

    # Meilleure/Pire période
    best_period = df_results.loc[df_results['perf_%'].idxmax()]
    worst_period = df_results.loc[df_results['perf_%'].idxmin()]

    print(f"\n🏆 Meilleure période: {best_period['period']} ({best_period['perf_%']:.1f}%)")
    print(f"💀 Pire période: {worst_period['period']} ({worst_period['perf_%']:.1f}%)")

    print(f"\n{'='*100}")

else:
    print("\n❌ Aucun résultat généré")
