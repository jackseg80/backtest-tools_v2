# Plan d'implémentation : Optimisation par profil

## ✅ Fichiers créés

1. **`profiles_map.csv`** - Mapping pair → profil (28 paires classifiées)

## 📋 Modifications à apporter au notebook

### Nouvelle Cell-3b (après Cell-3)

```python
# ======================
# OPTIMISATION PAR PROFIL
# ======================

# Charger le mapping pair → profil
df_profiles = pd.read_csv('profiles_map.csv')
PAIR_PROFILES = dict(zip(df_profiles['pair'], df_profiles['profile']))

# Définition du grid de référence (baseline)
BASE_ENVELOPE_SET = [0.07, 0.10, 0.15]  # Standard (référence)

# Multiplicateurs par profil (garde-fou #10)
PROFILE_MULTIPLIERS = {
    "major": 0.8,      # BTC, ETH - envelopes plus tight (-20%)
    "mid-cap": 1.0,    # SOL, AVAX, ADA - envelopes standard (référence)
    "volatile": 1.4,   # DOGE, SUSHI - envelopes plus wide (+40%)
    "low": 1.0,        # TRX - envelopes standard
}

# Grids par profil (basés sur multiplicateurs)
PARAM_GRIDS_BY_PROFILE = {}

for profile, multiplier in PROFILE_MULTIPLIERS.items():
    # Appliquer le multiplicateur au set de référence
    envelope_base = [round(x * multiplier, 3) for x in BASE_ENVELOPE_SET]
    envelope_wide = [round(x * multiplier * 1.3, 3) for x in BASE_ENVELOPE_SET]  # +30% supplémentaire

    PARAM_GRIDS_BY_PROFILE[profile] = {
        "ma_base_window": [5, 7] if profile in ["mid-cap", "volatile"] else [7, 10],
        "envelope_sets": [envelope_base, envelope_wide],
        "size": [0.10, 0.12] if profile in ["mid-cap", "volatile"] else [0.08, 0.10],
        "stop_loss": [0.25, 0.30] if profile == "volatile" else [0.25],
    }

# Afficher les grids générés
print("📊 GRIDS PAR PROFIL (avec multiplicateurs)")
print("=" * 80)
for profile, grid in PARAM_GRIDS_BY_PROFILE.items():
    print(f"\n{profile.upper()}:")
    print(f"   MA: {grid['ma_base_window']}")
    print(f"   Envelopes: {grid['envelope_sets']}")
    print(f"   Size: {grid['size']}")
    print(f"   Stop Loss: {grid['stop_loss']}")

    # Calculer nombre de configs
    n_configs = (len(grid['ma_base_window']) *
                 len(grid['envelope_sets']) *
                 len(grid['size']) *
                 len(grid['stop_loss']))
    print(f"   → {n_configs} configs par profil")

# Total configs
total_configs = sum(
    len(g['ma_base_window']) * len(g['envelope_sets']) * len(g['size']) * len(g['stop_loss'])
    for g in PARAM_GRIDS_BY_PROFILE.values()
)

print(f"\n{'=' * 80}")
print(f"TOTAL: {total_configs} configs × 7 folds × 2 (fixed+adaptive) = {total_configs * 7 * 2} backtests")
print(f"Temps estimé: ~{total_configs * 7 * 2 * 3 / 60:.0f} min avec multi-core")
```

### Modifier Cell-14 (remplacer le grid global)

```python
# ⚠️ CETTE CELLULE N'EST PLUS UTILISÉE POUR L'OPTIMISATION PAR PROFIL
# Les grids sont définis dans Cell-3b (PARAM_GRIDS_BY_PROFILE)

print("⏭️ Grid global remplacé par grids par profil (voir Cell-3b)")
```

### Modifier Cell-17 (Walk-Forward par profil)

Remplacer le loop global par un loop par profil :

```python
# Walk-Forward Optimization par PROFIL
wf_results_by_profile = {}

for profile in PARAM_GRIDS_BY_PROFILE.keys():
    print(f"\n{'=' * 80}")
    print(f"🔬 OPTIMISATION PROFIL: {profile.upper()}")
    print(f"{'=' * 80}")

    # Filtrer les paires du profil
    pairs_in_profile = [pair for pair in PAIRS if PAIR_PROFILES[pair] == profile]
    print(f"Paires: {', '.join(pairs_in_profile)}")

    if len(pairs_in_profile) == 0:
        print(f"⚠️ Aucune paire dans le profil {profile}, skip")
        continue

    # Générer combinaisons pour ce profil
    grid = PARAM_GRIDS_BY_PROFILE[profile]
    grid_combinations_profile = list(product(
        grid["ma_base_window"],
        grid["envelope_sets"],
        grid["size"],
        grid["stop_loss"]
    ))

    print(f"Configs à tester: {len(grid_combinations_profile)}")

    # Walk-Forward Loop (même structure que Cell-17 global)
    wf_results = []

    for fold in WF_FOLDS:
        # ... (même code que Cell-17, mais filter df_list par pairs_in_profile)

        df_list_train_profile = {p: df for p, df in df_list_train.items() if p in pairs_in_profile}
        df_list_test_profile = {p: df for p, df in df_list_test.items() if p in pairs_in_profile}

        for combo_idx, (ma_window, envelopes, size, stop_loss) in enumerate(grid_combinations_profile):
            # ... (même code de backtest)

            # Ajouter colonne 'profile' dans les résultats
            wf_results.append({
                "profile": profile,  # ← NOUVEAU
                "fold": fold_name,
                # ... (autres colonnes)
            })

    wf_results_by_profile[profile] = pd.DataFrame(wf_results)
```

### Nouvelle Cell-19b (Combiner résultats par profil)

```python
# Combiner les résultats de tous les profils
df_wf_all_profiles = pd.concat(list(wf_results_by_profile.values()), ignore_index=True)

# Meilleure config PAR PROFIL
best_configs_by_profile = {}

for profile in PARAM_GRIDS_BY_PROFILE.keys():
    df_profile = df_wf_all_profiles[df_wf_all_profiles['profile'] == profile]

    # Agréger par config
    df_profile_avg = df_profile.groupby(['ma_window', 'envelopes', 'size', 'stop_loss', 'adaptive']).agg({
        'test_score': 'mean',
        'test_sharpe': 'mean',
        'test_trades': 'sum',
    }).reset_index().sort_values('test_score', ascending=False)

    # Garde-fou #5 : Filtre trades minimum par profil
    MIN_TRADES_PER_PROFILE = 50
    df_profile_avg = df_profile_avg[df_profile_avg['test_trades'] >= MIN_TRADES_PER_PROFILE]

    if len(df_profile_avg) == 0:
        print(f"⚠️ Profil {profile}: Aucune config valide (< {MIN_TRADES_PER_PROFILE} trades)")
        continue

    best_configs_by_profile[profile] = df_profile_avg.iloc[0]

    print(f"\n✅ {profile.upper()} - Meilleure config:")
    print(f"   MA={best_configs_by_profile[profile]['ma_window']}, "
          f"Env={best_configs_by_profile[profile]['envelopes']}, "
          f"Size={best_configs_by_profile[profile]['size']}")
    print(f"   Test Score: {best_configs_by_profile[profile]['test_score']:.3f}")
    print(f"   Test Sharpe: {best_configs_by_profile[profile]['test_sharpe']:.2f}")
```

### Nouvelle Cell-19c (Gate : Profil > Global)

```python
# Garde-fou #6 : Valider que optimisation par profil > optimisation globale
# Charger résultats globaux (Étape 1)
df_wf_global = pd.read_csv('wf_results_summary_20251004_235003.csv')  # Résultat Étape 1

# Score global moyen
best_global_score = df_wf_global['test_score'].max()
best_global_sharpe = df_wf_global.loc[df_wf_global['test_score'].idxmax(), 'test_sharpe']

# Score profil moyen (moyenne pondérée par nombre de paires)
profile_scores = []
for profile, best_cfg in best_configs_by_profile.items():
    n_pairs = len([p for p in PAIRS if PAIR_PROFILES[p] == profile])
    profile_scores.append({
        'profile': profile,
        'score': best_cfg['test_score'],
        'sharpe': best_cfg['test_sharpe'],
        'weight': n_pairs
    })

df_profile_scores = pd.DataFrame(profile_scores)
weighted_avg_score = (df_profile_scores['score'] * df_profile_scores['weight']).sum() / df_profile_scores['weight'].sum()
weighted_avg_sharpe = (df_profile_scores['sharpe'] * df_profile_scores['weight']).sum() / df_profile_scores['weight'].sum()

print(f"\n📊 GATE: Profil vs Global")
print(f"=" * 80)
print(f"Global Best Score:  {best_global_score:.3f}")
print(f"Profil Avg Score:   {weighted_avg_score:.3f}")
print(f"Δ Score: {weighted_avg_score - best_global_score:+.3f}")
print(f"\nGlobal Best Sharpe: {best_global_sharpe:.2f}")
print(f"Profil Avg Sharpe:  {weighted_avg_sharpe:.2f}")
print(f"Δ Sharpe: {weighted_avg_sharpe - best_global_sharpe:+.2f}")

# Décision
if weighted_avg_score > best_global_score and abs(weighted_avg_sharpe - best_global_sharpe) <= 0.5:
    print(f"\n✅ GATE PASSÉ: Optimisation par profil améliore les résultats")
    print(f"   → Adopter configs par profil")
else:
    print(f"\n❌ GATE ÉCHOUÉ: Optimisation globale reste meilleure")
    print(f"   → Garder config globale unique")
```

## ⏱️ Temps d'exécution estimé

- **Profil major** : 8 configs × 7 folds × 2 = 112 backtests (~6 min)
- **Profil mid-cap** : 8 configs × 7 folds × 2 = 112 backtests (~6 min)
- **Profil volatile** : 16 configs × 7 folds × 2 = 224 backtests (~12 min)
- **Profil low** : 4 configs × 7 folds × 2 = 56 backtests (~3 min)

**TOTAL** : ~27 minutes avec multi-core

## 🎯 Prochaine étape

Voulez-vous que je modifie le notebook maintenant ou préférez-vous le faire manuellement avec ce plan ?
