# Workflow Optimisation Multi-Envelope

Guide pratique pour optimiser la stratégie multi-envelope avec détection de régime.

## Vue d'ensemble

```
1. compare_strategies.ipynb      → Test GO/NO-GO rapide (Fixed vs Adaptive)
2. optimize_multi_envelope.ipynb → Optimisation Walk-Forward complète
3. multi_envelope.ipynb          → Configuration production (28 paires)
```

## 1️⃣ Test GO/NO-GO Rapide

**Fichier**: `compare_strategies.ipynb`

**Objectif**: Vérifier si l'adaptation aux régimes améliore la performance

**Durée**: ~5-10 min

**Période**: 2020-2024 (couvre BULL 2020-21, BEAR 2022, RECOVERY 2023, BULL 2024)

**Ce que ça fait**:
- Teste Fixed vs Adaptive sur 8 paires stratifiées
- Bootstrap IC95% pour significativité statistique
- Analyse par classe d'actifs (majors, mid-caps, volatiles, low)
- Heatmap Delta PnL par régime

**Résultat attendu**:
- ✅ Si Adaptive > Fixed avec IC95% positif → Continuer
- ❌ Si pas de différence significative → Revoir les paramètres de régime

---

## 2️⃣ Optimisation Walk-Forward

**Fichier**: `optimize_multi_envelope.ipynb`

**Objectif**: Trouver les meilleurs paramètres sans overfitting

**Durée**: Variable selon grid size
- Grid réduit (2 configs) : ~5-10 min
- **Grid intermédiaire (18 configs) : ~15-20 min** ⭐ (recommandé Étape 1)
- Grid par profil (96 configs) : ~30-60 min (Étape 2)
- Grid fine (200+ configs) : 1-3h

**Période**: 2020-2025 (optimisation) + 2025-H2 (hold-out)

**Méthodologie anti-overfitting**:

### Phase A: Optimisation sur 8 paires
- Walk-Forward Expanding Window (5 folds - couvre tous les cycles)
  1. Train 2020-2021 → Test 2022-H1 (BULL → BEAR)
  2. Train 2020-2022-H1 → Test 2022-H2
  3. Train 2020-2022 → Test 2023-H1 (→ RECOVERY)
  4. Train 2020-2023-H1 → Test 2023-H2 (→ BULL)
  5. Train 2020-2023 → Test 2024-H1 (→ BULL)
- Teste toutes les combinaisons de paramètres
- Sélectionne top-3 par score composite

### Phase B: Validation portfolio (28 paires)
- Teste le top-3 sur portfolio complet
- Vérifie robustesse sur toutes les paires

### Phase C: Hold-out final
- Test UNE SEULE FOIS sur période intouchable (2024-H2)
- Confirmation qu'il n'y a pas d'overfitting

**Accélération multi-core (CPU)**:
Le notebook utilise **ProcessPoolExecutor** pour paralléliser les backtests.
- Gain: **~4-5x** sur i9-14900HX (24 cores)
- Automatique, pas de configuration nécessaire

**⚠️ Optimisation GPU (RTX 4080) - NON IMPLÉMENTÉ**:
- Actuellement: CPU multi-core uniquement
- GPU possible mais nécessite réécriture majeure (2-4h)
- Gain attendu: 3-5x supplémentaire (~10-20 min au lieu de 1-3h)
- **Recommandation**: Reporter jusqu'à validation de la méthodologie

**Paramètres optimisés**:
- `ma_base_window`: Réactivité du signal (5, 7, 10)
- `envelopes`: Distance d'entrée ([0.07, 0.10, 0.15], etc.)
- `size`: Risque par trade (0.08, 0.10, 0.12)
- `stop_loss`: Protection (0.20, 0.25, 0.30)

**🎯 Approche incrémentale recommandée**:

### ✅ Étape 1: Grid intermédiaire global (TERMINÉE)
- **État**: ✅ Complétée - Résultats dans `wf_results_summary_20251004_235003.csv`
- **Grid**: 18 configs (3 MA × 2 envelope_sets × 3 sizes)
- **Temps**: ~15-20 min avec multi-core
- **Résultat**: Meilleure config = MA=5, size=0.12, envelopes=[0.07, 0.10, 0.15]
- **Limitation**: ❌ Paramètres identiques pour BTC et DOGE (pas de sens)

### ✅ Étape 2: Optimisation par profil (IMPLÉMENTÉE)
- **État**: ✅ Implémentée avec multiplicateurs (garde-fou #10)
- **Profils**: 4 grids (major, mid-cap, volatile, low)
- **Multiplicateurs**: major=0.8, mid-cap=1.0, volatile=1.4, low=1.0
- **Grid**: 36 configs (8+8+16+4)
- **Temps**: ~27 min avec multi-core
- **Objectif**: BTC ≠ DOGE (envelopes adaptées à la volatilité)
- **Avantage**: Meilleur compromis performance/overfitting
- **Gate**: Validation automatique Profil vs Global

**Résultat attendu**:
- Meilleure config validée sur 28 paires + hold-out
- Export JSON avec paramètres optimaux

---

## 3️⃣ Application Production

**Fichier**: `multi_envelope.ipynb`

**Objectif**: Appliquer les paramètres optimisés au live bot

**Actions**:
1. Copier les paramètres du JSON généré par `optimize_multi_envelope.ipynb`
2. Mettre à jour `params_live` dans le notebook
3. Vérifier backtest complet sur 28 paires
4. Déployer en production si résultats conformes

---

## Exploration (optionnel)

**Fichier**: `explore_regime_detection.ipynb`

**Objectif**: Visualiser la détection de régime (éducatif)

**Contenu**:
- Graphique interactif BTC + régimes
- Distribution BULL/BEAR/RECOVERY
- Analyse des transitions
- Paramètres par régime

⚠️ **Ce notebook ne fait PAS de backtest**, uniquement de la visualisation.

---

## Conseils

### Réduire le temps d'optimisation

Si l'optimisation est trop longue, réduire le grid:

```python
PARAM_GRID = {
    "ma_base_window": [7],           # Au lieu de [5, 7, 10]
    "envelope_sets": [
        [0.07, 0.10, 0.15],          # Standard seulement
    ],
    "size": [0.10],                   # Au lieu de [0.08, 0.10, 0.12]
    "stop_loss": [0.25],              # Au lieu de [0.20, 0.25, 0.30]
}
```

### Interpréter les résultats

**Bon signe**:
- Train Sharpe ≈ Test Sharpe (écart < 0.5)
- Hold-out Sharpe proche du Phase B Sharpe
- Score composite élevé (> 0.5)
- Nombre de trades raisonnable (> 30 par fold)

**Mauvais signe**:
- Train Sharpe >> Test Sharpe (overfitting)
- Hold-out Sharpe diverge fortement
- Trop peu de trades (< 30)
- Max Drawdown > 20%

### Erreurs courantes

**Problème**: Notebook plante avec "MemoryError"
**Solution**: Réduire le nombre de paires ou de folds

**Problème**: "ProcessPoolExecutor" erreur sur Windows
**Solution**: Les fonctions worker doivent être top-level (déjà fait)

**Problème**: Tous les scores sont négatifs
**Solution**: Vérifier les paramètres de base, trop agressifs

---

## Structure des fichiers générés

```
strategies/envelopes/
├── backtest_comparison_results.csv     # Résultats compare_strategies
├── wf_results_detailed_YYYYMMDD.csv    # Tous les backtests Walk-Forward
├── wf_results_summary_YYYYMMDD.csv     # Résumé par config
├── best_config_YYYYMMDD.json           # Meilleure config à déployer
└── *.png                                # Graphiques (train vs test, etc.)
```

---

## Questions fréquentes

**Q: Pourquoi 8 paires au lieu de 28 ?**
R: Échantillon stratifié (majors, mid-caps, volatiles, low) réduit le temps tout en couvrant différents profils. La Phase B valide ensuite sur les 28 paires.

**Q: Pourquoi BTC comme proxy pour les régimes ?**
R: BTC représente le marché crypto global. Tous les altcoins suivent généralement le régime de BTC.

**Q: Peut-on optimiser la détection de régime aussi ?**
R: Oui, mais séparément. Modifier `DEFAULT_PARAMS` dans `core/__init__.py` pour tester d'autres valeurs d'envelope_std par régime.

**Q: Le multi-core fonctionne sur Mac/Linux ?**
R: Oui, ProcessPoolExecutor est cross-platform.

**Q: Pourquoi 2020-2025 au lieu de 2022-2025 ?**
R: Couvrir plus de cycles de marché (BULL 2020-21, BEAR 2022, RECOVERY 2023, BULL 2024-25) améliore la robustesse. Certaines cryptos n'existaient pas en 2020 mais sont automatiquement ignorées.

**Q: Optimisation globale vs par profil vs individuelle ?**
R:
- **Globale** (Étape 1): 1 set pour tous, simple et rapide, évite overfitting
- **Par profil** (Étape 2): 4 sets (majors/mid-caps/volatiles/low), meilleur compromis
- **Individuelle**: 28 sets, risque overfitting énorme, déconseillé

**Q: Faut-il directement faire l'optimisation par profil ?**
R: Non ! Approche incrémentale recommandée :
1. Tester grid intermédiaire global (18 configs, ~15 min)
2. Si résultats OK → Utiliser config globale (simple)
3. Si résultats insatisfaisants → Implémenter par profil (~30 min code + 30-60 min run)

**Q: Pourquoi ne pas utiliser le GPU RTX 4080 ?**
R: CPU multi-core suffit pour grids raisonnables. GPU nécessite réécriture majeure (2-4h) pour gain 3-5x. À implémenter seulement si temps devient critique (>3h).

---

## Support

Si tu rencontres des problèmes:
1. Vérifie que toutes les données sont chargées (pas de FileNotFoundError)
2. Réduis le grid pour tester rapidement
3. Regarde les messages d'erreur dans la cellule qui plante
