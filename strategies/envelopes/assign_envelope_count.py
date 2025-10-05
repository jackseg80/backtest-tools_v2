"""
Etape 1b: Assignment automatique du nombre d'enveloppes par pair

Calcule la volatilite realisee (30d rolling std) pour chaque pair et assigne
automatiquement le nombre d'enveloppes optimal :
- Volatilite > 5% -> 4 envelopes (meilleure granularite sur swings)
- Volatilite <= 5% -> 3 envelopes (suffisant pour mouvements standards)

Output: envelope_count_mapping.csv avec colonnes:
    - pair
    - vol_30d_mean (volatilite moyenne sur periode)
    - n_envelopes (3 ou 4)
    - profile (major, mid-cap, volatile, low)
    - vol_30d_std (ecart-type de la volatilite)
    - recommendation (justification)

Usage:
    python strategies/envelopes/assign_envelope_count.py
"""

import sys
import os
import pandas as pd
import numpy as np
from pathlib import Path

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from utilities.data_manager import ExchangeDataManager

# Configuration
EXCHANGE = "bitget"
TIMEFRAME = "1h"
START_DATE = "2020-04-01"
END_DATE = "2025-10-03"

# Seuil de volatilite pour decision nb envelopes
# NOTE: Sera calcule dynamiquement comme percentile de la distribution
VOL_THRESHOLD_PERCENTILE = 0.75  # Top 25% des pairs les plus volatiles -> 4 env

# Liste des pairs a analyser (depuis params_live)
PAIRS = [
    "BTC/USDT:USDT", "ETH/USDT:USDT", "BNB/USDT:USDT",
    "SOL/USDT:USDT", "ADA/USDT:USDT", "AR/USDT:USDT",
    "AVAX/USDT:USDT", "EGLD/USDT:USDT", "KSM/USDT:USDT",
    "ACH/USDT:USDT", "APE/USDT:USDT", "CRV/USDT:USDT",
    "DOGE/USDT:USDT", "DYDX/USDT:USDT", "ENJ/USDT:USDT",
    "FET/USDT:USDT", "GALA/USDT:USDT", "ICP/USDT:USDT",
    "IMX/USDT:USDT", "LDO/USDT:USDT", "MAGIC/USDT:USDT",
    "NEAR/USDT:USDT", "SAND/USDT:USDT", "SUSHI/USDT:USDT",
    "THETA/USDT:USDT", "TRX/USDT:USDT", "UNI/USDT:USDT",
    "XTZ/USDT:USDT"
]

# Mapping manuel des profils (depuis profiles_map.csv)
PROFILES_MAP = {
    "BTC/USDT:USDT": "major",
    "ETH/USDT:USDT": "major",
    "BNB/USDT:USDT": "mid-cap",
    "SOL/USDT:USDT": "mid-cap",
    "ADA/USDT:USDT": "mid-cap",
    "AVAX/USDT:USDT": "mid-cap",
    "AR/USDT:USDT": "mid-cap",
    "ATOM/USDT:USDT": "mid-cap",
    "MATIC/USDT:USDT": "mid-cap",
    "DOGE/USDT:USDT": "volatile",
    "SUSHI/USDT:USDT": "volatile",
    "GALA/USDT:USDT": "volatile",
    "TRX/USDT:USDT": "low",
    # Default pour les autres
}

def calculate_volatility(df):
    """
    Calcule la volatilite realisee 30d rolling

    Returns:
        vol_mean: Volatilite moyenne sur toute la periode
        vol_std: Ecart-type de la volatilite
        vol_median: Mediane de la volatilite
    """
    # Returns journaliers
    df['returns'] = df['close'].pct_change()

    # Volatilite 30d rolling (en heures : 30 jours * 24h)
    df['vol_30d'] = df['returns'].rolling(window=30*24).std()

    # Statistiques
    vol_mean = df['vol_30d'].mean()
    vol_std = df['vol_30d'].std()
    vol_median = df['vol_30d'].median()

    return vol_mean, vol_std, vol_median

def assign_envelopes(vol_mean, vol_threshold):
    """
    Assigne le nombre d'enveloppes selon volatilite

    Returns:
        n_envelopes: 3 ou 4
        recommendation: Justification
    """
    if vol_mean >= vol_threshold:
        return 4, f"Haute volatilite ({vol_mean*100:.2f}% >= {vol_threshold*100:.2f}%) - 4 env pour meilleure granularite"
    else:
        return 3, f"Volatilite standard ({vol_mean*100:.2f}% < {vol_threshold*100:.2f}%) - 3 env suffisantes"

def load_data(pair):
    """Charge les donnees pour une pair"""
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
    db_path = os.path.join(project_root, 'database', 'exchanges')

    exchange = ExchangeDataManager(
        exchange_name=EXCHANGE,
        path_download=db_path
    )

    try:
        df = exchange.load_data(coin=pair, interval=TIMEFRAME)

        # Filtrer periode
        df = df[(df.index >= START_DATE) & (df.index <= END_DATE)].copy()

        if len(df) < 30*24:  # Minimum 30 jours
            print(f"   WARN: {pair} - Pas assez de donnees ({len(df)} bougies)")
            return None

        return df

    except FileNotFoundError:
        print(f"   SKIP: {pair} - Fichier non trouve")
        return None
    except Exception as e:
        print(f"   ERROR: {pair} - {str(e)}")
        return None

def main():
    """Execute l'assignment automatique"""
    print("\n" + "="*80)
    print("ETAPE 1b: ASSIGNMENT AUTOMATIQUE NB ENVELOPES")
    print("="*80)
    print(f"Periode: {START_DATE} -> {END_DATE}")
    print(f"Methode: Seuil dynamique ({VOL_THRESHOLD_PERCENTILE*100:.0f}eme percentile)")
    print(f"Pairs a analyser: {len(PAIRS)}")
    print("="*80 + "\n")

    # ETAPE 1: Calculer volatilites pour toutes les pairs
    vol_data = []

    for i, pair in enumerate(PAIRS, 1):
        print(f"[{i}/{len(PAIRS)}] {pair:20s} ... ", end="", flush=True)

        # Charger donnees
        df = load_data(pair)

        if df is None:
            continue

        # Calculer volatilite
        vol_mean, vol_std, vol_median = calculate_volatility(df)

        # Profil
        profile = PROFILES_MAP.get(pair, "mid-cap")  # Default mid-cap si non specifie

        # Stocker resultats temporaires
        vol_data.append({
            'pair': pair,
            'vol_30d_mean': vol_mean,
            'vol_30d_std': vol_std,
            'vol_30d_median': vol_median,
            'profile': profile,
            'n_candles': len(df)
        })

        print(f"Vol={vol_mean*100:.2f}% ({profile})")

    # ETAPE 2: Calculer seuil dynamique (percentile)
    vol_values = [d['vol_30d_mean'] for d in vol_data]
    vol_threshold = np.quantile(vol_values, VOL_THRESHOLD_PERCENTILE)

    print(f"\n{'='*80}")
    print(f"SEUIL DYNAMIQUE CALCULE: {vol_threshold*100:.2f}% ({VOL_THRESHOLD_PERCENTILE*100:.0f}eme percentile)")
    print(f"{'='*80}\n")

    # ETAPE 3: Assigner nb envelopes avec seuil calcule
    results = []

    for data in vol_data:
        n_envelopes, recommendation = assign_envelopes(data['vol_30d_mean'], vol_threshold)

        results.append({
            **data,
            'n_envelopes': n_envelopes,
            'recommendation': recommendation
        })

        status = "4 env" if n_envelopes == 4 else "3 env"
        print(f"  {data['pair']:20s} -> {status}")

    # Creer DataFrame
    df_results = pd.DataFrame(results)

    # Trier par volatilite decroissante
    df_results = df_results.sort_values('vol_30d_mean', ascending=False)

    # Sauvegarder CSV
    output_file = Path(__file__).parent / 'envelope_count_mapping.csv'
    df_results.to_csv(output_file, index=False)

    print("\n" + "="*80)
    print("RESULTATS")
    print("="*80)
    print(f"\nPairs analysees: {len(df_results)}/{len(PAIRS)}")
    print(f"Seuil applique: {vol_threshold*100:.2f}% ({VOL_THRESHOLD_PERCENTILE*100:.0f}eme percentile)")

    # Statistiques
    n_4env = (df_results['n_envelopes'] == 4).sum()
    n_3env = (df_results['n_envelopes'] == 3).sum()
    pct_4env = (n_4env / len(df_results) * 100) if len(df_results) > 0 else 0

    print(f"\nDistribution nb envelopes:")
    print(f"  3 envelopes: {n_3env} pairs ({100-pct_4env:.1f}%)")
    print(f"  4 envelopes: {n_4env} pairs ({pct_4env:.1f}%)")

    print(f"\nDistribution par profil:")
    for profile in df_results['profile'].unique():
        df_prof = df_results[df_results['profile'] == profile]
        n_3env = (df_prof['n_envelopes'] == 3).sum()
        n_4env = (df_prof['n_envelopes'] == 4).sum()
        print(f"  {profile:10s}: {n_3env} x 3env, {n_4env} x 4env")

    print(f"\nVolatilite moyenne:")
    print(f"  Minimum : {df_results['vol_30d_mean'].min()*100:.2f}%")
    print(f"  Mediane : {df_results['vol_30d_mean'].median()*100:.2f}%")
    print(f"  Moyenne : {df_results['vol_30d_mean'].mean()*100:.2f}%")
    print(f"  Maximum : {df_results['vol_30d_mean'].max()*100:.2f}%")

    # Top 5 plus volatiles
    print(f"\nTop 5 plus volatiles (-> 4 envelopes):")
    for idx, row in df_results.head(5).iterrows():
        print(f"  {row['pair']:20s} Vol={row['vol_30d_mean']*100:.2f}% ({row['profile']})")

    # Top 5 moins volatiles
    print(f"\nTop 5 moins volatiles (-> 3 envelopes):")
    for idx, row in df_results.tail(5).iterrows():
        print(f"  {row['pair']:20s} Vol={row['vol_30d_mean']*100:.2f}% ({row['profile']})")

    # Comparaison avec params_live actuel
    print(f"\n" + "="*80)
    print("COMPARAISON AVEC PARAMS_LIVE ACTUEL")
    print("="*80)

    # Lire params_live depuis multi_envelope.ipynb (approximation)
    current_4env_pairs = ["ADA/USDT:USDT", "AR/USDT:USDT", "AVAX/USDT:USDT"]  # Connu du contexte

    recommended_4env = df_results[df_results['n_envelopes'] == 4]['pair'].tolist()

    # Pairs qui devraient passer a 4 env
    should_add_4env = [p for p in recommended_4env if p not in current_4env_pairs]

    # Pairs qui devraient passer a 3 env
    should_remove_4env = [p for p in current_4env_pairs if p in df_results['pair'].tolist() and df_results[df_results['pair'] == p]['n_envelopes'].iloc[0] == 3]

    if len(should_add_4env) > 0:
        print(f"\nPairs a passer a 4 envelopes ({len(should_add_4env)}):")
        for pair in should_add_4env:
            vol = df_results[df_results['pair'] == pair]['vol_30d_mean'].iloc[0]
            print(f"  + {pair:20s} (vol={vol*100:.2f}%)")

    if len(should_remove_4env) > 0:
        print(f"\nPairs a repasser a 3 envelopes ({len(should_remove_4env)}):")
        for pair in should_remove_4env:
            vol = df_results[df_results['pair'] == pair]['vol_30d_mean'].iloc[0]
            print(f"  - {pair:20s} (vol={vol*100:.2f}%)")

    if len(should_add_4env) == 0 and len(should_remove_4env) == 0:
        print("\nAucune modification necessaire - params_live coherent avec volatilite")

    print("\n" + "="*80)
    print(f"Fichier sauvegarde: {output_file}")
    print("="*80)

    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
