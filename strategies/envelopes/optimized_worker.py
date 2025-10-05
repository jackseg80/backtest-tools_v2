"""
Worker function optimisé pour CPU multi-processing
Utilise numpy views et mémoire partagée au lieu de DataFrames
"""
import numpy as np
import pandas as pd
from multiprocessing import shared_memory
from utilities.strategies.envelopeMulti_v2 import EnvelopeMulti_v2
from core.params_adapter import FixedParamsAdapter, RegimeBasedAdapter
from core import DEFAULT_PARAMS


def prepare_data_for_worker(df_list, regime_series=None):
    """
    Convertit DataFrames en numpy arrays pour passage efficace aux workers

    Returns:
        dict: Données optimisées pour multi-processing
    """
    data_optimized = {}

    for pair, df in df_list.items():
        # Convertir en float32 (divise la mémoire par 2)
        data_optimized[pair] = {
            'open': df['open'].values.astype(np.float32),
            'high': df['high'].values.astype(np.float32),
            'low': df['low'].values.astype(np.float32),
            'close': df['close'].values.astype(np.float32),
            'volume': df['volume'].values.astype(np.float32) if 'volume' in df.columns else None,
            'index': df.index.values,
            'ma_base': df.get('ma_base', pd.Series(index=df.index)).values.astype(np.float32),
            'ma_low': df.get('ma_low', pd.Series(index=df.index)).values.astype(np.float32),
            'ma_high': df.get('ma_high', pd.Series(index=df.index)).values.astype(np.float32),
        }

    regime_data = None
    if regime_series is not None:
        regime_data = {
            'values': regime_series.values,
            'index': regime_series.index.values
        }

    return {
        'pairs_data': data_optimized,
        'regime_data': regime_data
    }


def reconstruct_df_from_arrays(pair_data):
    """Reconstruit un DataFrame minimal depuis les arrays numpy"""
    df = pd.DataFrame({
        'open': pair_data['open'],
        'high': pair_data['high'],
        'low': pair_data['low'],
        'close': pair_data['close'],
    }, index=pd.DatetimeIndex(pair_data['index']))

    if pair_data['ma_base'] is not None and len(pair_data['ma_base']) > 0:
        df['ma_base'] = pair_data['ma_base']
        df['ma_low'] = pair_data['ma_low']
        df['ma_high'] = pair_data['ma_high']

    return df


def run_backtest_optimized_worker(args):
    """
    Worker optimisé utilisant numpy arrays au lieu de DataFrames complets

    Args:
        args: tuple (config, pairs_data_dict, params_coin, stop_loss, regime_data, is_adaptive)

    Returns:
        dict: Métriques du backtest (pas les DataFrames complets)
    """
    config, pairs_data, params_coin, stop_loss, regime_data, is_adaptive = args

    # Reconstruire DataFrames minimaux depuis arrays
    df_list = {}
    for pair, data in pairs_data.items():
        df_list[pair] = reconstruct_df_from_arrays(data)

    oldest_pair = min(df_list, key=lambda p: df_list[p].index.min())

    # Créer adapter
    if is_adaptive and regime_data is not None:
        regime_series = pd.Series(
            regime_data['values'],
            index=pd.DatetimeIndex(regime_data['index'])
        )
        adapter = RegimeBasedAdapter(
            base_params=params_coin,
            regime_series=regime_series,
            regime_params=DEFAULT_PARAMS,
            multipliers={'envelope_std': True},
            base_std=0.10
        )
    else:
        adapter = FixedParamsAdapter(params_coin)

    # Exécuter backtest
    strategy = EnvelopeMulti_v2(
        df_list=df_list,
        oldest_pair=oldest_pair,
        type=["long", "short"],
        params=params_coin
    )

    strategy.populate_indicators()
    strategy.populate_buy_sell()

    # Paramètres backtest
    from optimize_multi_envelope import BACKTEST_PARAMS, INITIAL_WALLET

    result = strategy.run_backtest(
        **BACKTEST_PARAMS,
        stop_loss=stop_loss,
        params_adapter=adapter
    )

    # Retourner UNIQUEMENT les métriques (pas les gros DataFrames)
    return {
        'config': config,
        'wallet': result['days']['wallet'].iloc[-1] if len(result['days']) > 0 else INITIAL_WALLET,
        'sharpe': result.get('sharpe_ratio', 0),
        'n_trades': len(result['trades']),
        'max_dd': calculate_max_dd_fast(result['days']) if len(result['days']) > 0 else 0,
    }


def calculate_max_dd_fast(df_days):
    """Calcul rapide du max drawdown depuis numpy array"""
    if len(df_days) == 0:
        return 0

    wallet = df_days['wallet'].values.astype(np.float32)
    cummax = np.maximum.accumulate(wallet)
    drawdown = (wallet - cummax) / cummax
    return abs(np.min(drawdown)) * 100 if len(drawdown) > 0 else 0


def run_backtests_parallel_optimized(configs, df_list, regime_series=None, max_workers=None):
    """
    Version optimisée du batching CPU avec numpy views

    Args:
        configs: Liste de configs à tester
        df_list: Dict de DataFrames
        regime_series: Series des régimes
        max_workers: Nombre de workers

    Returns:
        list: Résultats des backtests
    """
    from concurrent.futures import ProcessPoolExecutor, as_completed
    from tqdm.auto import tqdm

    # Préparer données optimisées (1 seule fois)
    data_optimized = prepare_data_for_worker(df_list, regime_series)

    # Préparer tasks
    tasks = []
    for config in configs:
        # Préparer params_coin
        params_coin = {}
        for pair in df_list.keys():
            params_coin[pair] = {
                "src": "close",
                "ma_base_window": config['ma_window'],
                "envelopes": config['envelopes'],
                "size": config['size'] / config.get('leverage', 10)
            }

        tasks.append((
            config,
            data_optimized['pairs_data'],
            params_coin,
            config['stop_loss'],
            data_optimized['regime_data'],
            config.get('adaptive', False)
        ))

    # Exécution parallèle optimisée
    results = []
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(run_backtest_optimized_worker, task): i
                   for i, task in enumerate(tasks)}

        for future in tqdm(as_completed(futures), total=len(futures),
                          desc="Backtests optimisés"):
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                print(f"Erreur backtest: {e}")
                results.append(None)

    return results


# Fonction helper pour batch processing
def batch_configs(configs, batch_size=12):
    """Groupe les configs en batches pour processing optimisé"""
    for i in range(0, len(configs), batch_size):
        yield configs[i:i + batch_size]


print("✅ Module optimized_worker chargé (numpy views + mémoire optimisée)")
