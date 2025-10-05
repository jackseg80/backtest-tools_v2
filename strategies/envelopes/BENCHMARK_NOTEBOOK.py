# =================================================================
# BENCHMARK À EXÉCUTER DANS LE NOTEBOOK
# =================================================================
# Copier-coller ce code dans une cellule pour mesurer les gains Palier 1

import time
import numpy as np
from indicator_cache import IndicatorCache
from optimized_worker import prepare_data_for_worker

print("="*80)
print("BENCHMARK PALIER 1 - Mesure des gains")
print("="*80)

# ============================================================================
# Test 1: Cache des indicateurs
# ============================================================================

print("\nTest 1: Cache des indicateurs")
print("-"*80)

# Sans cache (recalcul)
start = time.perf_counter()
for pair in list(df_list_full.keys())[:4]:  # 4 paires
    df = df_list_full[pair]
    for ma_window in [5, 7, 10]:  # 3 MA
        _ = df['close'].ewm(span=ma_window, adjust=False).mean()
time_without_cache = time.perf_counter() - start

# Avec cache
cache = IndicatorCache(cache_dir="./cache_benchmark")
cache.clear()

start = time.perf_counter()
for pair in list(df_list_full.keys())[:4]:
    df = df_list_full[pair]
    for ma_window in [5, 7, 10]:
        cache.get_or_compute(df, pair, "1h", "2024-01-01", "2025-10-03", ma_window, [0.07, 0.10, 0.15])

# 2ème accès (depuis cache)
for pair in list(df_list_full.keys())[:4]:
    df = df_list_full[pair]
    for ma_window in [5, 7, 10]:
        _ = cache.get(pair, "1h", "2024-01-01", "2025-10-03", ma_window, [0.07, 0.10, 0.15])

time_with_cache = time.perf_counter() - start
cache.clear()

speedup_cache = time_without_cache / time_with_cache
print(f"Sans cache:  {time_without_cache:.2f}s")
print(f"Avec cache:  {time_with_cache:.2f}s")
print(f"Speedup:     x{speedup_cache:.2f} ({(speedup_cache-1)*100:.0f}% gain)")

# ============================================================================
# Test 2: Conversion DataFrame → numpy
# ============================================================================

print("\nTest 2: Conversion donnees (DataFrame vs numpy)")
print("-"*80)

df_subset = {pair: df for pair, df in list(df_list_full.items())[:4]}

# DataFrame dict
start = time.perf_counter()
for _ in range(10):
    serialized = {pair: df.to_dict('list') for pair, df in df_subset.items()}
time_dataframe = time.perf_counter() - start

# Numpy arrays (float32)
start = time.perf_counter()
for _ in range(10):
    optimized = prepare_data_for_worker(df_subset)
time_numpy = time.perf_counter() - start

speedup_numpy = time_dataframe / time_numpy
print(f"DataFrame:   {time_dataframe:.2f}s")
print(f"Numpy:       {time_numpy:.2f}s")
print(f"Speedup:     x{speedup_numpy:.2f} ({(speedup_numpy-1)*100:.0f}% gain)")

# ============================================================================
# Test 3: Early termination (simulation)
# ============================================================================

print("\nTest 3: Early termination (simulation)")
print("-"*80)

n_configs = 36
n_folds = 7

# Sans early termination
time_per_fold = 0.01  # 10ms
time_without_early = n_configs * n_folds * time_per_fold

# Avec early termination (40% skip après fold 2)
skip_rate = 0.4
n_skipped = int(n_configs * skip_rate)
n_full = n_configs - n_skipped

time_with_early = (n_skipped * 2 * time_per_fold) + (n_full * n_folds * time_per_fold)

speedup_early = time_without_early / time_with_early
print(f"Sans early:  {time_without_early:.2f}s ({n_configs} configs x {n_folds} folds)")
print(f"Avec early:  {time_with_early:.2f}s ({n_skipped} skip @ fold 2, {n_full} complets)")
print(f"Speedup:     x{speedup_early:.2f} ({(speedup_early-1)*100:.0f}% gain)")

# ============================================================================
# RÉSUMÉ
# ============================================================================

print("\n" + "="*80)
print("RÉSUMÉ DES GAINS PALIER 1")
print("="*80)

# Gain composé
gain_total = speedup_cache * speedup_numpy * speedup_early

print(f"\n1. Cache indicateurs:       x{speedup_cache:.2f}")
print(f"2. Numpy views (float32):   x{speedup_numpy:.2f}")
print(f"3. Early termination:       x{speedup_early:.2f}")
print(f"\nGain total compose:         x{gain_total:.2f}")
print(f"\nTemps MODE PRODUCTION:")
print(f"  Avant (CPU multi-core):   ~30-60 min")
print(f"  Apres Palier 1:           ~{30/gain_total:.0f}-{60/gain_total:.0f} min")
print("\n" + "="*80)

# Estimation finale
if gain_total >= 2.0:
    print("VERDICT: Gain excellent (>= 2x), Palier 1 validé!")
elif gain_total >= 1.5:
    print("VERDICT: Gain satisfaisant (1.5-2x), Palier 1 validé!")
else:
    print("VERDICT: Gain modeste (<1.5x), considérer Palier 2 (GPU)")
