"""
Benchmark: CPU Single-Core vs Multi-Core pour backtests
Compare le temps d'exécution avec et sans parallélisation
"""
import sys
sys.path.append('../..')

import time
import pandas as pd
from concurrent.futures import ProcessPoolExecutor, as_completed
from utilities.strategies.envelopeMulti_v2 import EnvelopeMulti_v2
from utilities.data_manager import ExchangeDataManager
from core import calculate_regime_series, DEFAULT_PARAMS
from core.params_adapter import FixedParamsAdapter, RegimeBasedAdapter

# Configuration
BACKTEST_LEVERAGE = 10
START_DATE = "2020-01-01"  # Periode plus longue
END_DATE = "2024-12-31"

# 4 paires pour test rapide
TEST_PAIRS = {
    "BTC/USDT:USDT": {"size": 0.1, "ma_base_window": 7, "envelopes": [0.07, 0.1, 0.15]},
    "ETH/USDT:USDT": {"size": 0.1, "ma_base_window": 7, "envelopes": [0.07, 0.1, 0.15]},
    "SOL/USDT:USDT": {"size": 0.1, "ma_base_window": 7, "envelopes": [0.07, 0.1, 0.15]},
    "AVAX/USDT:USDT": {"size": 0.1, "ma_base_window": 7, "envelopes": [0.07, 0.1, 0.15]},
}

# Conversion pour backtest
params_coin = {}
for pair, p in TEST_PAIRS.items():
    params_coin[pair] = {
        "ma_base_window": p["ma_base_window"],
        "envelopes": p["envelopes"],
        "src": "close",
        "size": p["size"] / BACKTEST_LEVERAGE
    }

backtest_params = {
    "initial_wallet": 1000,
    "leverage": BACKTEST_LEVERAGE,
    "maker_fee": 0.0002,
    "taker_fee": 0.0006,
    "stop_loss": 0.25,
    "reinvest": True,
    "liquidation": True,
    "risk_mode": "scaling",
}


def run_single_backtest(adapter_name, adapter):
    """Exécute un backtest avec un adaptateur donné"""
    # Charger données
    exchange = ExchangeDataManager(
        exchange_name="binance",
        path_download="../database/exchanges"
    )

    df_list = {}
    for pair in params_coin.keys():
        df = exchange.load_data(pair, "1h", start_date=START_DATE, end_date=END_DATE)
        df_list[pair] = df

    oldest_pair = min(df_list, key=lambda p: df_list[p].index.min())

    # Stratégie
    strategy = EnvelopeMulti_v2(
        df_list=df_list,
        oldest_pair=oldest_pair,
        type=["long", "short"],
        params=params_coin
    )

    strategy.populate_indicators()
    strategy.populate_buy_sell()

    # Backtest
    result = strategy.run_backtest(**backtest_params, params_adapter=adapter)

    return {
        'name': adapter_name,
        'final_wallet': result['days']['wallet'].iloc[-1],
        'n_trades': len(result['trades'])
    }


def benchmark_sequential(configs):
    """Exécution séquentielle (1 core)"""
    print("\n" + "="*80)
    print("BENCHMARK SÉQUENTIEL (Single-Core)")
    print("="*80)

    start = time.time()
    results = []

    for i, (name, adapter) in enumerate(configs.items(), 1):
        print(f"[{i}/{len(configs)}] Running {name}...", end=" ", flush=True)
        t0 = time.time()
        result = run_single_backtest(name, adapter)
        t1 = time.time()
        print(f"OK {t1-t0:.1f}s")
        results.append(result)

    elapsed = time.time() - start
    print(f"\nTemps total: {elapsed:.1f}s")

    return results, elapsed


def benchmark_parallel(configs, max_workers=None):
    """Exécution parallèle (multi-core)"""
    print("\n" + "="*80)
    print(f"BENCHMARK PARALLÈLE (Multi-Core, workers={max_workers or 'auto'})")
    print("="*80)

    start = time.time()
    results = []

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(run_single_backtest, name, adapter): name
            for name, adapter in configs.items()
        }

        for i, future in enumerate(as_completed(futures), 1):
            name = futures[future]
            print(f"[{i}/{len(configs)}] {name} completed", flush=True)
            results.append(future.result())

    elapsed = time.time() - start
    print(f"\nTemps total: {elapsed:.1f}s")

    return results, elapsed


if __name__ == "__main__":
    print("="*80)
    print("BENCHMARK: CPU Single-Core vs Multi-Core")
    print("="*80)
    print(f"Paires testees: {len(TEST_PAIRS)}")
    print(f"Periode: {START_DATE} -> {END_DATE}")

    # Charger données BTC pour régime
    exchange = ExchangeDataManager(
        exchange_name="binance",
        path_download="../database/exchanges"
    )
    df_btc = exchange.load_data("BTC/USDT:USDT", "1h", start_date=START_DATE, end_date=END_DATE)
    regime_series = calculate_regime_series(df_btc, confirm_n=12)

    # Configs à tester (16 configs pour benchmark réaliste)
    configs = {
        "Fixed_Baseline": FixedParamsAdapter(params_coin),
    }

    # Générer plusieurs configs adaptives
    for std in [0.06, 0.08, 0.10, 0.12, 0.14]:
        for mult_tp in [True, False]:
            for mult_trail in [True, False]:
                mults = {'envelope_std': True}
                if mult_tp:
                    mults['tp_mult'] = True
                if mult_trail:
                    mults['trailing'] = True

                name = f"Adpt_s{int(std*100):02d}_tp{int(mult_tp)}_tr{int(mult_trail)}"
                configs[name] = RegimeBasedAdapter(
                    base_params=params_coin,
                    regime_series=regime_series,
                    regime_params=DEFAULT_PARAMS,
                    multipliers=mults,
                    base_std=std
                )

                if len(configs) >= 16:  # Limiter à 16 configs
                    break
            if len(configs) >= 16:
                break
        if len(configs) >= 16:
            break

    print(f"Configs testees: {len(configs)}\n")

    # Test séquentiel
    results_seq, time_seq = benchmark_sequential(configs)

    # Test parallèle (auto-detect cores)
    results_par, time_par = benchmark_parallel(configs, max_workers=None)

    # Résultats
    print("\n" + "="*80)
    print("RÉSULTATS")
    print("="*80)
    print(f"Sequential: {time_seq:.1f}s")
    print(f"Parallel:   {time_par:.1f}s")
    print(f"\nSpeedup: {time_seq/time_par:.2f}x")

    # Vérification cohérence
    print("\nVérification des résultats (doivent être identiques):")
    df_seq = pd.DataFrame(results_seq).set_index('name').sort_index()
    df_par = pd.DataFrame(results_par).set_index('name').sort_index()

    print(df_seq)
    print("\nDifférence avec parallel:")
    print((df_par - df_seq).abs())
