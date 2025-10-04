"""
Utilitaire de comparaison V1 vs V2

Génère un tableau comparatif détaillé des résultats backtests entre les deux versions.
Usage: Appeler après avoir run les deux versions avec mêmes paramètres.
"""

import pandas as pd
from typing import Dict, Any


def compare_v1_v2(result_v1: Dict[str, Any], result_v2: Dict[str, Any],
                  config: Dict[str, Any]) -> pd.DataFrame:
    """
    Compare les résultats V1 vs V2 et retourne un DataFrame formaté.

    Parameters:
    -----------
    result_v1 : dict
        Résultats du backtest V1
    result_v2 : dict
        Résultats du backtest V2
    config : dict
        Configuration du backtest (leverage, fees, etc.)

    Returns:
    --------
    pd.DataFrame
        Tableau comparatif formaté
    """

    # Helper pour extraire metrics
    def safe_get(d, key, default=0):
        return d.get(key, default) if isinstance(d, dict) else default

    # Extraction metrics V1
    v1_wallet = safe_get(result_v1, 'wallet', 0)
    v1_sharpe = safe_get(result_v1, 'sharpe_ratio', 0)
    v1_sortino = safe_get(result_v1, 'sortino_ratio', 0)
    v1_calmar = safe_get(result_v1, 'calmar_ratio', 0)
    v1_max_dd = safe_get(result_v1, 'max_drawdown', 0)
    v1_max_dd_day = safe_get(result_v1, 'max_drawdown_day', 0)
    v1_nb_trades = len(result_v1.get('trades', []))
    v1_win_rate = safe_get(result_v1, 'win_rate', 0)

    # Extraction metrics V2
    v2_wallet = safe_get(result_v2, 'wallet', 0)
    v2_sharpe = safe_get(result_v2, 'sharpe_ratio', 0)
    v2_sortino = safe_get(result_v2, 'sortino_ratio', 0)
    v2_calmar = safe_get(result_v2, 'calmar_ratio', 0)
    v2_max_dd = safe_get(result_v2, 'max_drawdown', 0)
    v2_max_dd_day = safe_get(result_v2, 'max_drawdown_day', 0)
    v2_nb_trades = len(result_v2.get('trades', []))
    v2_win_rate = safe_get(result_v2, 'win_rate', 0)

    # V2-specific: Liquidations & caps
    df_trades_v2 = result_v2.get('trades', pd.DataFrame())
    if isinstance(df_trades_v2, pd.DataFrame) and not df_trades_v2.empty:
        v2_nb_liquidations = len(df_trades_v2[df_trades_v2['close_reason'] == 'Liquidation'])
        v2_nb_stops = len(df_trades_v2[df_trades_v2['close_reason'] == 'Stop Loss'])
    else:
        v2_nb_liquidations = 0
        v2_nb_stops = 0

    # Build comparison data
    data = {
        'Métrique': [
            '══ PERFORMANCE ══',
            'Wallet final ($)',
            'Profit (%)',
            'Sharpe Ratio',
            'Sortino Ratio',
            'Calmar Ratio',
            '',
            '══ RISQUE ══',
            'Max Drawdown Trade (%)',
            'Max Drawdown Day (%)',
            'Win Rate (%)',
            '',
            '══ TRADES ══',
            'Nombre total trades',
            'Sorties Stop-Loss',
            'Liquidations',
            '',
            '══ RÉALISME ══',
            'Bug leverage',
            'Liquidation intra-bar',
            'Exposure caps',
            'Kill-switch',
        ],
        'V1 (Legacy)': [
            '',
            f'{v1_wallet:,.2f}',
            f'{((v1_wallet / config["initial_wallet"]) - 1) * 100:.1f}',
            f'{v1_sharpe:.2f}',
            f'{v1_sortino:.2f}',
            f'{v1_calmar:.2f}',
            '',
            '',
            f'{v1_max_dd * 100:.2f}',
            f'{v1_max_dd_day * 100:.2f}',
            f'{v1_win_rate * 100:.1f}',
            '',
            '',
            f'{v1_nb_trades}',
            '-',
            '-',
            '',
            '',
            'Oui (résultats impossibles)',
            'Non (check post-trade)',
            'Non',
            'Non',
        ],
        'V2 (Corrigé)': [
            '',
            f'{v2_wallet:,.2f}',
            f'{((v2_wallet / config["initial_wallet"]) - 1) * 100:.1f}',
            f'{v2_sharpe:.2f}',
            f'{v2_sortino:.2f}',
            f'{v2_calmar:.2f}',
            '',
            '',
            f'{v2_max_dd * 100:.2f}',
            f'{v2_max_dd_day * 100:.2f}',
            f'{v2_win_rate * 100:.1f}',
            '',
            '',
            f'{v2_nb_trades}',
            f'{v2_nb_stops}',
            f'{v2_nb_liquidations}',
            '',
            '',
            'Non (corrigé)',
            'Oui (low/high check)',
            'Oui (gross/side/pair)',
            'Oui (-8%/-12%)',
        ],
        'Delta (V2 - V1)': [
            '',
            f'{v2_wallet - v1_wallet:+,.2f}',
            f'{((v2_wallet / v1_wallet) - 1) * 100:+.1f}%',
            f'{v2_sharpe - v1_sharpe:+.2f}',
            f'{v2_sortino - v1_sortino:+.2f}',
            f'{v2_calmar - v1_calmar:+.2f}',
            '',
            '',
            f'{(v2_max_dd - v1_max_dd) * 100:+.2f} pp',
            f'{(v2_max_dd_day - v1_max_dd_day) * 100:+.2f} pp',
            f'{(v2_win_rate - v1_win_rate) * 100:+.1f} pp',
            '',
            '',
            f'{v2_nb_trades - v1_nb_trades:+d}',
            '-',
            f'{v2_nb_liquidations}',
            '',
            '',
            '✅',
            '✅',
            '✅',
            '✅',
        ]
    }

    df = pd.DataFrame(data)

    # Ajouter config
    config_text = f"""
Configuration du backtest:
  - Initial wallet: {config['initial_wallet']
}$
  - Leverage: {config['leverage']}x
  - Fees: maker {config['maker_fee']*100:.2f}%, taker {config['taker_fee']*100:.2f}%
  - Stop-loss: {config['stop_loss']*100:.0f}%
  - Période: {config.get('start_date', 'N/A')} → {config.get('end_date', 'N/A')}
"""

    return df, config_text


def print_comparison(result_v1: Dict[str, Any], result_v2: Dict[str, Any],
                     config: Dict[str, Any], show_config: bool = True):
    """
    Affiche la comparaison V1 vs V2 formatée.

    Parameters:
    -----------
    result_v1 : dict
        Résultats backtest V1
    result_v2 : dict
        Résultats backtest V2
    config : dict
        Configuration
    show_config : bool
        Afficher la config (default True)
    """

    df, config_text = compare_v1_v2(result_v1, result_v2, config)

    print("\n" + "="*100)
    print("COMPARAISON V1 vs V2 - Système de Marge et Liquidation")
    print("="*100)

    if show_config:
        print(config_text)

    # Print DataFrame with tabulate if available, otherwise basic print
    try:
        from tabulate import tabulate
        print(tabulate(df, headers='keys', tablefmt='grid', showindex=False))
    except ImportError:
        print(df.to_string(index=False))

    # Analyse rapide
    print("\n" + "="*100)
    print("ANALYSE:")
    print("="*100)

    v1_wallet = result_v1.get('wallet', 0)
    v2_wallet = result_v2.get('wallet', 0)
    leverage = config['leverage']

    if leverage >= 10:
        if v1_wallet > v2_wallet * 2:
            print("\n⚠️ ALERTE: V1 montre des résultats très supérieurs à V2 avec leverage élevé")
            print("   → Ceci indique que V1 a un BUG (résultats impossibles)")
            print("   → V2 est plus RÉALISTE avec gestion correcte de la liquidation")
        elif v2_wallet == 0 or v2_wallet < config['initial_wallet'] * 0.1:
            print("\n⚠️ V2: Liquidation totale ou quasi-totale détectée")
            print(f"   → Leverage {leverage}x trop risqué pour cette stratégie/période")
            print("   → Recommandation: Réduire leverage à 5x max ou ajuster params")
        else:
            print("\n✅ Résultats cohérents entre V1 et V2")
            print("   → Leverage modéré permet des résultats réalistes")

    # Exposure stats V2
    df_trades_v2 = result_v2.get('trades', pd.DataFrame())
    if isinstance(df_trades_v2, pd.DataFrame) and not df_trades_v2.empty:
        nb_liq = len(df_trades_v2[df_trades_v2['close_reason'] == 'Liquidation'])
        total_trades = len(df_trades_v2)
        liq_rate = (nb_liq / total_trades * 100) if total_trades > 0 else 0

        if liq_rate > 5:
            print(f"\n⚠️ V2: Taux de liquidation élevé ({liq_rate:.1f}%)")
            print("   → Considérer:")
            print("     • Réduire leverage")
            print("     • Augmenter stop-loss")
            print("     • Réduire exposition par trade (size)")
        elif liq_rate > 0:
            print(f"\n✅ V2: Quelques liquidations ({nb_liq} trades, {liq_rate:.1f}%)")
            print("   → Niveau acceptable, mais surveiller en production")
        else:
            print("\n✅ V2: Aucune liquidation sur la période")
            print("   → Configuration conservative adaptée")

    print("\n" + "="*100 + "\n")


def export_comparison(result_v1: Dict[str, Any], result_v2: Dict[str, Any],
                      config: Dict[str, Any], filepath: str = 'comparison_v1_v2.csv'):
    """
    Exporte la comparaison dans un fichier CSV.

    Parameters:
    -----------
    result_v1 : dict
        Résultats V1
    result_v2 : dict
        Résultats V2
    config : dict
        Configuration
    filepath : str
        Chemin du fichier de sortie
    """

    df, _ = compare_v1_v2(result_v1, result_v2, config)
    df.to_csv(filepath, index=False)
    print(f"\n✅ Comparaison exportée: {filepath}\n")


# Example usage
if __name__ == "__main__":
    print("""
Utilitaire de comparaison V1 vs V2
===================================

Usage dans un notebook:

    from utilities.compare_engines import print_comparison

    # Run V1
    strat_v1 = EnvelopeMulti(...)  # Version V1
    result_v1 = strat_v1.run_backtest(...)

    # Run V2
    strat_v2 = EnvelopeMulti_v2(...)  # Version V2
    result_v2 = strat_v2.run_backtest(...)

    # Compare
    config = {
        'initial_wallet': 1000,
        'leverage': 10,
        'maker_fee': 0.0002,
        'taker_fee': 0.0006,
        'stop_loss': 0.2,
        'start_date': '2020-04-01',
        'end_date': '2025-10-03'
    }

    print_comparison(result_v1, result_v2, config)

Voir README_V2.md pour plus d'exemples.
""")
