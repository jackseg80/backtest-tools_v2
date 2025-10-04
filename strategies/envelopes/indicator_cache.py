"""
Système de cache pour pré-calcul des indicateurs
Gain attendu : ×1.5-2x sur le temps total
"""
import numpy as np
import pandas as pd
from pathlib import Path
import hashlib
import pickle
from typing import Dict, List, Tuple
import ta


class IndicatorCache:
    """Cache les indicateurs pré-calculés pour éviter les recalculs"""

    def __init__(self, cache_dir: str = "./cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)

    def _get_cache_key(self, pair: str, timeframe: str, start_date: str, end_date: str,
                       ma_window: int, envelopes: List[float]) -> str:
        """Génère une clé de cache unique"""
        key_str = f"{pair}_{timeframe}_{start_date}_{end_date}_{ma_window}_{envelopes}"
        return hashlib.md5(key_str.encode()).hexdigest()

    def _get_cache_path(self, cache_key: str) -> Path:
        """Retourne le chemin du fichier de cache"""
        return self.cache_dir / f"{cache_key}.npz"

    def get(self, pair: str, timeframe: str, start_date: str, end_date: str,
            ma_window: int, envelopes: List[float]) -> Dict[str, np.ndarray]:
        """Récupère les indicateurs du cache si disponibles"""
        cache_key = self._get_cache_key(pair, timeframe, start_date, end_date, ma_window, envelopes)
        cache_path = self._get_cache_path(cache_key)

        if cache_path.exists():
            # Charger depuis le cache
            data = np.load(cache_path)
            return {
                'ma_base': data['ma_base'],
                'ma_low': data['ma_low'],
                'ma_high': data['ma_high'],
                'index': data['index'],
                'open': data['open'],
                'high': data['high'],
                'low': data['low'],
                'close': data['close'],
            }
        return None

    def set(self, pair: str, timeframe: str, start_date: str, end_date: str,
            ma_window: int, envelopes: List[float], indicators: Dict[str, np.ndarray]):
        """Sauvegarde les indicateurs dans le cache"""
        cache_key = self._get_cache_key(pair, timeframe, start_date, end_date, ma_window, envelopes)
        cache_path = self._get_cache_path(cache_key)

        # Sauvegarder en format numpy compressé
        np.savez_compressed(
            cache_path,
            ma_base=indicators['ma_base'],
            ma_low=indicators['ma_low'],
            ma_high=indicators['ma_high'],
            index=indicators['index'],
            open=indicators['open'],
            high=indicators['high'],
            low=indicators['low'],
            close=indicators['close'],
        )

    def compute_indicators(self, df: pd.DataFrame, ma_window: int, envelopes: List[float]) -> Dict[str, np.ndarray]:
        """Calcule les indicateurs avec numpy (optimisé)"""
        # Convertir en numpy pour vitesse
        close_prices = df['close'].values.astype(np.float32)
        open_prices = df['open'].values.astype(np.float32)
        high_prices = df['high'].values.astype(np.float32)
        low_prices = df['low'].values.astype(np.float32)

        # Calcul EMA avec pandas (plus rapide que boucle manuelle)
        ma_base = df['close'].ewm(span=ma_window, adjust=False).mean().values.astype(np.float32)

        # Calculer envelopes
        ma_low = ma_base * (1 - envelopes[0])
        ma_high = ma_base * (1 + envelopes[0])

        return {
            'ma_base': ma_base,
            'ma_low': ma_low,
            'ma_high': ma_high,
            'index': df.index.values,
            'open': open_prices,
            'high': high_prices,
            'low': low_prices,
            'close': close_prices,
        }

    def get_or_compute(self, df: pd.DataFrame, pair: str, timeframe: str,
                       start_date: str, end_date: str, ma_window: int,
                       envelopes: List[float]) -> Dict[str, np.ndarray]:
        """Récupère du cache ou calcule et met en cache"""
        # Essayer de récupérer du cache
        cached = self.get(pair, timeframe, start_date, end_date, ma_window, envelopes)
        if cached is not None:
            return cached

        # Calculer et mettre en cache
        indicators = self.compute_indicators(df, ma_window, envelopes)
        self.set(pair, timeframe, start_date, end_date, ma_window, envelopes, indicators)
        return indicators

    def clear(self):
        """Vide le cache"""
        for cache_file in self.cache_dir.glob("*.npz"):
            cache_file.unlink()


def precompute_all_indicators(df_list: Dict[str, pd.DataFrame],
                              param_grids: Dict[str, Dict],
                              periods: Dict,
                              cache: IndicatorCache) -> None:
    """
    Pré-calcule tous les indicateurs pour toutes les combinaisons

    Args:
        df_list: Dict des DataFrames par paire
        param_grids: Grids de paramètres par profil
        periods: Périodes d'optimisation
        cache: Instance du cache
    """
    print("🔄 Pré-calcul des indicateurs...")

    # Collecter toutes les combinaisons uniques de MA windows et envelopes
    unique_configs = set()
    for profile, grid in param_grids.items():
        for ma_window in grid['ma_base_window']:
            for envelope_set in grid['envelope_sets']:
                unique_configs.add((ma_window, tuple(envelope_set)))

    total = len(df_list) * len(unique_configs)
    count = 0

    for pair, df in df_list.items():
        for ma_window, envelope_set in unique_configs:
            # Pré-calculer pour la période complète
            cache.get_or_compute(
                df, pair, "1h",
                periods['train_full']['start'],
                periods['train_full']['end'],
                ma_window,
                list(envelope_set)
            )
            count += 1
            if count % 10 == 0:
                print(f"   {count}/{total} combinaisons pré-calculées...")

    print(f"✅ {total} combinaisons d'indicateurs pré-calculées et mises en cache")


# Fonction helper pour récupérer les indicateurs optimisés
def get_cached_indicators_for_backtest(cache: IndicatorCache, df: pd.DataFrame,
                                       pair: str, ma_window: int,
                                       envelopes: List[float],
                                       start_date: str, end_date: str) -> Dict[str, np.ndarray]:
    """Récupère les indicateurs optimisés pour un backtest"""
    return cache.get_or_compute(df, pair, "1h", start_date, end_date, ma_window, envelopes)
