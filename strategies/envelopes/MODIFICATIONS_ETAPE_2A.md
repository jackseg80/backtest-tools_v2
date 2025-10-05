# Modifications Étape 2a : Multiplicateurs + Nb Envelopes Auto

## Objectif
Modifier `optimize_multi_envelope.ipynb` pour :
1. ✅ Charger le mapping automatique `envelope_count_mapping.csv`
2. ✅ Utiliser des **multiplicateurs** au lieu de valeurs absolues (réduction degrés de liberté)
3. ✅ Générer grilles avec **3 ou 4 envelopes** selon la pair
4. ✅ Appliquer le **scoring corrigé** (exclusions au lieu de pénalités -500)

---

## Modification 1 : Cell-2 (Imports et chargement mapping)

**Après les imports existants, ajouter :**

```python
# === ETAPE 2A : CHARGEMENT MAPPING NB ENVELOPES ===
import os
envelope_mapping_path = os.path.join(os.path.dirname(__file__), 'envelope_count_mapping.csv')

if os.path.exists(envelope_mapping_path):
    df_envelope_mapping = pd.read_csv(envelope_mapping_path, index_col='pair')
    print(f"✅ Mapping nb envelopes chargé : {len(df_envelope_mapping)} pairs")
    print(f"   4 envelopes : {(df_envelope_mapping['n_envelopes'] == 4).sum()} pairs")
    print(f"   3 envelopes : {(df_envelope_mapping['n_envelopes'] == 3).sum()} pairs")
else:
    print("⚠️  WARNING: envelope_count_mapping.csv non trouvé")
    print("   Exécutez d'abord : python assign_envelope_count.py")
    df_envelope_mapping = None
```

---

## Modification 2 : Cell-3b (Grilles par profil avec multiplicateurs)

**REMPLACER la Cell-3b existante par :**

```python
# === CELL-3b : GRILLES PAR PROFIL (MULTIPLICATEURS + NB ENV AUTO) ===

# Config globale de référence (issue de l'optimisation Étape 1)
BASE_CONFIG = {
    'ma_base_window': 5,           # Meilleure MA de l'optimisation globale
    'envelopes_3': [0.07, 0.1, 0.15],     # Base pour 3 envelopes
    'envelopes_4': [0.07, 0.1, 0.15, 0.20],  # Base pour 4 envelopes
    'size': 0.12,                  # Meilleur size de l'optimisation globale
    'stop_loss': 0.25
}

# Multiplicateurs par profil (au lieu de valeurs absolues)
# Objectif : Réduire l'espace de recherche tout en adaptant aux volatilités
PROFILE_MULTIPLIERS = {
    "major": {
        "mult": [0.8, 0.9, 1.0],        # BTC/ETH - envelopes plus tight
        "ma": [5, 7],                    # MA standard
        "size": [0.10, 0.12]             # Size conservateur
    },
    "mid-cap": {
        "mult": [1.0, 1.1, 1.2],        # SOL/AVAX - envelopes standard+
        "ma": [5, 7, 10],                # MA variable
        "size": [0.10, 0.12, 0.14]       # Size variable
    },
    "volatile": {
        "mult": [1.2, 1.3, 1.4],        # DOGE/SUSHI - envelopes larges
        "ma": [5, 7],                    # MA court pour réactivité
        "size": [0.12, 0.14]             # Size plus agressif
    },
    "low": {
        "mult": [1.0],                  # TRX - envelopes standard
        "ma": [7, 10],                   # MA long (peu de signaux)
        "size": [0.10]                   # Size conservateur
    }
}

# Fonction pour générer grilles par profil
def generate_profile_grid(profile, pairs_in_profile):
    """
    Génère la grille de configs pour un profil donné

    Args:
        profile: Nom du profil (major, mid-cap, volatile, low)
        pairs_in_profile: Liste des pairs dans ce profil

    Returns:
        List de dicts avec configs à tester
    """
    configs = []

    multipliers = PROFILE_MULTIPLIERS[profile]["mult"]
    ma_windows = PROFILE_MULTIPLIERS[profile]["ma"]
    sizes = PROFILE_MULTIPLIERS[profile]["size"]

    for mult in multipliers:
        for ma in ma_windows:
            for size in sizes:
                # Générer config pour chaque pair du profil
                pair_configs = {}

                for pair in pairs_in_profile:
                    # Déterminer nb envelopes depuis mapping
                    if df_envelope_mapping is not None and pair in df_envelope_mapping.index:
                        n_env = df_envelope_mapping.loc[pair, 'n_envelopes']
                    else:
                        # Fallback : 3 env par défaut
                        n_env = 3

                    # Sélectionner base selon nb envelopes
                    base_env = BASE_CONFIG[f'envelopes_{n_env}']

                    # Appliquer multiplicateur
                    envelopes = [round(e * mult, 3) for e in base_env]

                    pair_configs[pair] = {
                        'ma_base_window': ma,
                        'envelopes': envelopes,
                        'size': size / 10  # Ajusté pour leverage 10x (comme multi_envelope.ipynb)
                    }

                configs.append({
                    'profile': profile,
                    'mult': mult,
                    'ma': ma,
                    'size': size,
                    'stop_loss': BASE_CONFIG['stop_loss'],
                    'pair_configs': pair_configs,
                    'adaptive': False  # Fixed params par défaut
                })

    return configs

# Générer toutes les grilles par profil
PARAM_GRIDS_BY_PROFILE = {}

for profile in PROFILE_MULTIPLIERS.keys():
    # Filtrer pairs du profil
    pairs_in_profile = [pair for pair in PAIRS if PAIR_PROFILES.get(pair) == profile]

    if len(pairs_in_profile) > 0:
        grid = generate_profile_grid(profile, pairs_in_profile)
        PARAM_GRIDS_BY_PROFILE[profile] = grid

        print(f"Profil {profile:10s} : {len(grid):3d} configs × {len(pairs_in_profile)} pairs")

# Compter total configs
total_configs = sum(len(grid) for grid in PARAM_GRIDS_BY_PROFILE.values())
print(f"\n✅ Total configs profils : {total_configs}")

if not TEST_MODE:
    total_backtests = total_configs * len(WF_FOLDS) * 2  # Fixed + Adaptive
else:
    total_backtests = total_configs * len(WF_FOLDS)  # Fixed only en TEST_MODE

print(f"   Total backtests : {total_backtests} (Fixed + Adaptive)")
```

---

## Modification 3 : Cell-19 (Scoring corrigé)

**Dans la boucle Walk-Forward, REMPLACER les pénalités -500 par exclusions :**

**AVANT (ligne ~450) :**
```python
if n_trades < 10:
    score_test = -500
```

**APRÈS :**
```python
# === SCORING CORRIGÉ : Exclusions au lieu de pénalités ===
if n_trades_test < 10:
    print(f"      SKIP: < 10 trades ({n_trades_test})")
    continue  # Skip cette config au lieu de -500

# Poids réduit pour échantillons faibles
weight = 1.0
if n_trades_test < 50:
    weight = 0.25
    print(f"      LOW WEIGHT: {n_trades_test} trades (weight=0.25)")
```

**ET remplacer le calcul du score :**

**AVANT :**
```python
score_test = sharpe_test * 0.35 + ...
```

**APRÈS :**
```python
# Clips pour éviter outliers
consistency = np.clip(consistency, 0, 1)
pf = np.clip(pf, 0, 2)
dd_factor = np.clip(1 - max_dd/100, 0, 1)

# Score pondéré
score_test = (
    sharpe_test * 0.30 +
    consistency * 0.25 +
    calmar * 0.20 +
    dd_factor * 0.15 +
    win_rate * 0.05 +
    pf * 0.05
) * weight  # Appliquer le poids
```

---

## Modification 4 : Cell-20 (Agrégation par profil avec poids)

**REMPLACER le MIN_TRADES_PER_PROFILE par système de poids :**

**AVANT :**
```python
MIN_TRADES_PER_PROFILE = 50
df_profile = df_profile[df_profile['n_trades_test'] >= MIN_TRADES_PER_PROFILE]
```

**APRÈS :**
```python
# Pas de hard cutoff - utiliser poids à la place
# Les configs avec peu de trades ont déjà weight=0.25

# Calculer score pondéré par profil
df_profile['weighted_score'] = df_profile['score_test'] * df_profile.get('weight', 1.0)

# Top 3 par score pondéré
top3 = df_profile.nlargest(3, 'weighted_score')
```

---

## Modification 5 : Cell-21 (Gate v2 hiérarchique - NOUVELLE CELLULE)

**AJOUTER une nouvelle cellule après Cell-21 :**

```python
# === CELL-21b : GATE V2 HIÉRARCHIQUE ===

print("="*80)
print("GATE V2 : VALIDATION MULTI-NIVEAUX")
print("="*80)

# Calculer métriques globales
weighted_avg_score = (df_profile_scores['score'] * df_profile_scores['weight']).sum() / df_profile_scores['weight'].sum()
weighted_avg_sharpe = (df_profile_scores['sharpe'] * df_profile_scores['weight']).sum() / df_profile_scores['weight'].sum()

# Métriques de référence (optimisation globale Étape 1)
best_global_score = 2.943
best_global_sharpe = 3.13

# TIER 1 : HARD GATES (doivent passer)
tier1_trades = df_portfolio_total_trades >= 200
tier1_holdout = abs(weighted_avg_sharpe - best_global_sharpe) <= 0.7

tier1_pass = tier1_trades and tier1_holdout

print(f"\nTIER 1 (HARD) :")
print(f"  [{'✅' if tier1_trades else '❌'}] Trades >= 200 : {df_portfolio_total_trades}")
print(f"  [{'✅' if tier1_holdout else '❌'}] |Δ Sharpe holdout| <= 0.7 : {abs(weighted_avg_sharpe - best_global_sharpe):.2f}")

if not tier1_pass:
    print("\n❌ TIER 1 ÉCHOUÉ - Gate rejeté")
    RECOMMENDATION = "global"
else:
    # TIER 2 : SOFT GATES (2 sur 3 suffisent)
    tier2_score = weighted_avg_score > best_global_score
    tier2_sharpe = weighted_avg_sharpe > best_global_sharpe
    tier2_consistency = abs(sharpe_train_avg - sharpe_test_avg) <= 0.5

    tier2_pass = sum([tier2_score, tier2_sharpe, tier2_consistency]) >= 2

    print(f"\nTIER 2 (SOFT - 2/3 requis) :")
    print(f"  [{'✅' if tier2_score else '❌'}] Score > Global : {weighted_avg_score:.2f} vs {best_global_score:.2f}")
    print(f"  [{'✅' if tier2_sharpe else '❌'}] Sharpe > Global : {weighted_avg_sharpe:.2f} vs {best_global_sharpe:.2f}")
    print(f"  [{'✅' if tier2_consistency else '❌'}] |Δ Sharpe train-test| <= 0.5 : {abs(sharpe_train_avg - sharpe_test_avg):.2f}")
    print(f"  → Passed: {sum([tier2_score, tier2_sharpe, tier2_consistency])}/3")

    # TIER 3 : WARNING (log only)
    tier3_phase = abs(sharpe_phaseA - sharpe_phaseB) <= 0.5

    print(f"\nTIER 3 (WARNING) :")
    print(f"  [{'✅' if tier3_phase else '⚠️ '}] |Δ Sharpe Phase A-B| <= 0.5 : {abs(sharpe_phaseA - sharpe_phaseB):.2f}")

    # Décision finale
    if tier2_pass:
        RECOMMENDATION = "profil"
        print("\n✅ GATE V2 VALIDÉ - Utiliser optimisation par profils")
    else:
        RECOMMENDATION = "global"
        print("\n❌ GATE V2 ÉCHOUÉ - Utiliser optimisation globale")

print("="*80)
print(f"RECOMMANDATION FINALE : {RECOMMENDATION.upper()}")
print("="*80)

# Sauvegarder résultats
results_final = {
    'recommendation': RECOMMENDATION,
    'weighted_score_profile': weighted_avg_score,
    'weighted_sharpe_profile': weighted_avg_sharpe,
    'score_global': best_global_score,
    'sharpe_global': best_global_sharpe,
    'tier1_pass': tier1_pass,
    'tier2_pass': tier2_pass if tier1_pass else False,
    'tier3_pass': tier3_phase,
    'timestamp': pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')
}

# Exporter
import json
output_file = f"gate_v2_result_{results_final['timestamp']}.json"
with open(output_file, 'w') as f:
    json.dump(results_final, f, indent=2)

print(f"\n✅ Résultats sauvegardés : {output_file}")
```

---

## Résumé des Modifications

| Cell | Type | Description |
|------|------|-------------|
| **Cell-2** | Ajout | Import + chargement `envelope_count_mapping.csv` |
| **Cell-3b** | Remplacement | Grilles multiplicateurs + nb env auto |
| **Cell-19** | Modification | Scoring corrigé (exclusions, clips, poids) |
| **Cell-20** | Modification | Agrégation avec poids (pas de hard cutoff) |
| **Cell-21b** | Nouvelle | Gate v2 hiérarchique (Tier 1/2/3) |

---

## Instructions d'Application

### 1. Backup
```bash
cp optimize_multi_envelope.ipynb optimize_multi_envelope_backup_etape2a.ipynb
```

### 2. Ouvrir dans Jupyter/VS Code
- Ouvrir `optimize_multi_envelope.ipynb`

### 3. Appliquer modifications dans l'ordre
1. ✅ Cell-2 : Ajouter le bloc import mapping
2. ✅ Cell-3b : Remplacer par nouvelle version
3. ✅ Cell-19 : Modifier scoring (chercher `-500` et remplacer)
4. ✅ Cell-20 : Modifier agrégation (chercher `MIN_TRADES_PER_PROFILE`)
5. ✅ Cell-21b : Insérer nouvelle cellule Gate v2

### 4. Validation
- Exécuter Cell-2 : Vérifier mapping chargé
- Exécuter Cell-3b : Vérifier grilles générées
- **NE PAS** exécuter Cell-19 en MODE PRODUCTION tout de suite
- Tester d'abord en `TEST_MODE = True`

### 5. Test Mode
```python
# Cell-3 : Activer TEST_MODE
TEST_MODE = True  # 2-3 min pour validation

# Exécuter jusqu'à Cell-21b
# Vérifier que tout fonctionne
```

### 6. Mode Production
```python
# Cell-3 : Désactiver TEST_MODE
TEST_MODE = False  # MODE PRODUCTION (15-25 min avec Palier 1)

# Lancer optimisation complète
```

---

## Fichiers Générés

Après exécution complète :
- `gate_v2_result_YYYYMMDD_HHMMSS.json` - Résultat du gate
- `wf_results_detailed_v2_YYYYMMDD_HHMMSS.csv` - Résultats Walk-Forward
- `best_config_v2_YYYYMMDD.json` - Meilleure config par profil

---

## Temps Estimés

| Mode | Configs | Backtests | Temps |
|------|---------|-----------|-------|
| **TEST_MODE** | ~12 | ~24 | 2-3 min |
| **PRODUCTION** | ~60 | ~840 | 15-25 min |

*Avec optimisations Palier 1 (cache, numpy, early termination)*

---

## Prochaines Étapes

Après exécution réussie :
1. ✅ **Étape 2b** : Analyser résultats 3env vs 4env
2. ✅ **Étape 3** : Valider Gate v2 (déjà implémenté)
3. ✅ **Étape 4** : Harmoniser params_live avec résultats
