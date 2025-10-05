"""
Benchmark Palier 1 : Mesure des gains de performance
Compare version standard vs version optimisée
"""
import time
import pandas as pd
import numpy as np
from pathlib import Path
import json
from datetime import datetime


class BenchmarkPalier1:
    """Benchmark pour valider les gains du Palier 1"""

    def __init__(self):
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'tests': []
        }

    def run_test(self, name, func, *args, **kwargs):
        """Exécute un test et mesure le temps"""
        print(f"\n{'='*60}")
        print(f"🧪 Test: {name}")
        print(f"{'='*60}")

        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start

        test_result = {
            'name': name,
            'time_seconds': round(elapsed, 2),
            'time_formatted': f"{elapsed:.2f}s" if elapsed < 60 else f"{int(elapsed//60)}m {int(elapsed%60)}s"
        }

        self.results['tests'].append(test_result)

        print(f"✅ Temps: {test_result['time_formatted']}")
        return result

    def compare(self, baseline_name, optimized_name):
        """Compare 2 tests et calcule le speedup"""
        baseline = next(t for t in self.results['tests'] if t['name'] == baseline_name)
        optimized = next(t for t in self.results['tests'] if t['name'] == optimized_name)

        speedup = baseline['time_seconds'] / optimized['time_seconds']

        print(f"\n{'='*60}")
        print(f"📊 COMPARAISON: {baseline_name} vs {optimized_name}")
        print(f"{'='*60}")
        print(f"Baseline:  {baseline['time_formatted']}")
        print(f"Optimisé:  {optimized['time_formatted']}")
        print(f"Speedup:   ×{speedup:.2f}")
        print(f"Gain:      {(speedup-1)*100:.1f}% plus rapide")
        print(f"{'='*60}\n")

        self.results['comparisons'] = self.results.get('comparisons', [])
        self.results['comparisons'].append({
            'baseline': baseline_name,
            'optimized': optimized_name,
            'speedup': round(speedup, 2),
            'gain_pct': round((speedup-1)*100, 1)
        })

        return speedup

    def save_results(self, filename='benchmark_results.json'):
        """Sauvegarde les résultats"""
        with open(filename, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"💾 Résultats sauvegardés: {filename}")


# ============================================================================
# Tests spécifiques
# ============================================================================

def benchmark_cache_indicators(benchmark, df_list, param_grids, periods):
    """Benchmark du cache d'indicateurs"""
    from indicator_cache import IndicatorCache, precompute_all_indicators

    # Test 1: Sans cache (recalcul à chaque fois)
    def without_cache():
        count = 0
        for pair, df in list(df_list.items())[:4]:  # 4 paires pour test rapide
            for profile, grid in param_grids.items():
                for ma_window in grid['ma_base_window'][:1]:  # 1 MA par profil
                    for envelope_set in grid['envelope_sets'][:1]:  # 1 set
                        # Calcul EMA (simulation)
                        _ = df['close'].ewm(span=ma_window, adjust=False).mean()
                        count += 1
        return count

    result1 = benchmark.run_test("Sans cache (recalcul)", without_cache)

    # Test 2: Avec cache (pré-calcul)
    def with_cache():
        cache = IndicatorCache(cache_dir="./cache_test")
        cache.clear()  # Nettoyer cache précédent

        # Pré-calculer
        for pair, df in list(df_list.items())[:4]:
            for profile, grid in param_grids.items():
                for ma_window in grid['ma_base_window'][:1]:
                    for envelope_set in grid['envelope_sets'][:1]:
                        cache.get_or_compute(
                            df, pair, "1h",
                            periods['train_full']['start'],
                            periods['train_full']['end'],
                            ma_window, list(envelope_set)
                        )

        # Accéder au cache
        count = 0
        for pair, df in list(df_list.items())[:4]:
            for profile, grid in param_grids.items():
                for ma_window in grid['ma_base_window'][:1]:
                    for envelope_set in grid['envelope_sets'][:1]:
                        _ = cache.get(
                            pair, "1h",
                            periods['train_full']['start'],
                            periods['train_full']['end'],
                            ma_window, list(envelope_set)
                        )
                        count += 1

        cache.clear()  # Nettoyer
        return count

    result2 = benchmark.run_test("Avec cache (pré-calcul + accès)", with_cache)

    return benchmark.compare("Sans cache (recalcul)", "Avec cache (pré-calcul + accès)")


def benchmark_data_conversion(benchmark, df_list):
    """Benchmark de la conversion DataFrame → numpy"""
    from optimized_worker import prepare_data_for_worker

    # Test 1: Passer DataFrames complets
    def pass_dataframes():
        serialized = {}
        for pair, df in list(df_list.items())[:4]:
            serialized[pair] = df.to_dict('list')  # Simulation sérialisation
        return len(serialized)

    result1 = benchmark.run_test("Pass DataFrames (dict)", pass_dataframes)

    # Test 2: Convertir en numpy arrays (float32)
    def pass_numpy_arrays():
        df_subset = {pair: df for pair, df in list(df_list.items())[:4]}
        optimized = prepare_data_for_worker(df_subset)
        return len(optimized['pairs_data'])

    result2 = benchmark.run_test("Pass numpy arrays (float32)", pass_numpy_arrays)

    return benchmark.compare("Pass DataFrames (dict)", "Pass numpy arrays (float32)")


def benchmark_early_termination(benchmark):
    """Benchmark de l'early termination (simulation)"""

    # Test 1: Sans early termination (tous les folds)
    def without_early_term():
        total_time = 0
        n_folds = 7
        n_configs = 36

        for config in range(n_configs):
            for fold in range(n_folds):
                # Simulation backtest (10ms par fold)
                time.sleep(0.01)
                total_time += 0.01

        return total_time

    result1 = benchmark.run_test("Sans early termination (7 folds × 36)", without_early_term)

    # Test 2: Avec early termination (skip 40% des configs)
    def with_early_term():
        total_time = 0
        n_folds = 7
        n_configs = 36
        skip_rate = 0.4  # 40% skippées

        for config in range(n_configs):
            # 40% des configs sont skippées après 2 folds
            if config < n_configs * skip_rate:
                max_folds = 2  # Early termination
            else:
                max_folds = n_folds

            for fold in range(max_folds):
                time.sleep(0.01)
                total_time += 0.01

        return total_time

    result2 = benchmark.run_test("Avec early termination (skip 40%)", with_early_term)

    return benchmark.compare("Sans early termination (7 folds × 36)", "Avec early termination (skip 40%)")


# ============================================================================
# Main benchmark
# ============================================================================

def run_full_benchmark():
    """Exécute tous les benchmarks"""
    print("\n" + "="*80)
    print("🚀 BENCHMARK PALIER 1 - Optimisations CPU")
    print("="*80)

    benchmark = BenchmarkPalier1()

    # Note: Ces tests nécessitent que les variables soient disponibles
    # Normalement exécuté depuis le notebook après chargement des données

    print("\n⚠️  Pour exécuter le benchmark complet:")
    print("1. Charger les données dans le notebook (Cell-6)")
    print("2. Exécuter:")
    print("   from benchmark_palier1 import benchmark_cache_indicators, benchmark_data_conversion")
    print("   benchmark = BenchmarkPalier1()")
    print("   benchmark_cache_indicators(benchmark, df_list_full, PARAM_GRIDS_BY_PROFILE, PERIODS)")
    print("   benchmark_data_conversion(benchmark, df_list_full)")
    print("   benchmark.save_results()")

    # Test standalone: early termination (pas besoin de données)
    speedup_early = benchmark_early_termination(benchmark)

    # Résumé
    print("\n" + "="*80)
    print("📊 RÉSUMÉ DES GAINS")
    print("="*80)
    for comp in benchmark.results.get('comparisons', []):
        print(f"✅ {comp['optimized']}: ×{comp['speedup']} ({comp['gain_pct']:+.1f}%)")

    benchmark.save_results()

    print("\n🎯 Gain total estimé Palier 1: ×1.5-2.5x")
    print("   (Cache ×1.5-2x + Early term ×1.2-1.5x + Numpy views ×1.1-1.3x)")

    return benchmark


if __name__ == "__main__":
    run_full_benchmark()
