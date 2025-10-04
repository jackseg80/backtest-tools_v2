# Guide de Comparaison Multi-Stratégies

Ce guide explique comment utiliser le nouveau système de comparaison pour tester plusieurs configurations de paramètres et identifier la meilleure stratégie.

## 🎯 Vue d'ensemble

Le système permet de :
- **Comparer N stratégies** avec différents paramètres
- **Adapter dynamiquement** les paramètres pendant le backtest (ex: selon régime de marché)
- **Générer automatiquement** un rapport comparatif avec recommandation
- **Réutiliser facilement** le code pour de nouvelles comparaisons

## 📦 Architecture

```
core/
├── params_adapter.py         # Adaptateurs de paramètres
├── backtest_comparator.py    # Comparateur multi-stratégies
└── __init__.py               # Exports publics

strategies/envelopes/
└── compare_strategies.ipynb  # Notebook de démonstration
```

## 🚀 Quick Start

### Option 1 : Notebook clé en main

Le plus simple est d'utiliser le notebook pré-configuré :

```bash
jupyter notebook strategies/envelopes/compare_strategies.ipynb
```

Le notebook exécute automatiquement :
1. Chargement des données
2. Détection du régime de marché (BTC)
3. Exécution de plusieurs backtests (fixed, adaptive, etc.)
4. Génération du rapport comparatif
5. Sauvegarde des résultats en CSV

### Option 2 : Code Python custom

```python
from core import RegimeBasedAdapter, FixedParamsAdapter, BacktestComparator
from utilities.strategies.envelopeMulti_v2 import EnvelopeMulti_v2

# 1. Configurer les adaptateurs
adapters = {
    "Baseline": FixedParamsAdapter(params_coin),
    "Adaptive": RegimeBasedAdapter(params_coin, regime_series, ...)
}

# 2. Exécuter les backtests
comparator = BacktestComparator(initial_wallet=1000)

for name, adapter in adapters.items():
    strategy = EnvelopeMulti_v2(df_list, oldest_pair, type=["long", "short"], params=params_coin)
    strategy.populate_indicators()
    strategy.populate_buy_sell()

    df_trades, df_days = strategy.run_backtest(
        leverage=10,
        params_adapter=adapter  # 🔑 Adaptation dynamique
    )

    comparator.add_backtest(name, df_trades, df_days)

# 3. Analyser les résultats
comparator.print_summary()
comparator.save_comparison("results.csv")
```

## 📚 Adaptateurs disponibles

### 1. FixedParamsAdapter (Baseline)

Retourne toujours les mêmes paramètres (pas d'adaptation).

```python
adapter = FixedParamsAdapter(params_coin)
```

**Usage** : Baseline pour comparaison

### 2. RegimeBasedAdapter (Adaptatif)

Adapte les paramètres selon le régime de marché détecté (BULL/BEAR/RECOVERY).

```python
from core import calculate_regime_series, DEFAULT_PARAMS

# Détecter le régime sur BTC
regime_series = calculate_regime_series(df_btc, confirm_n=12)

adapter = RegimeBasedAdapter(
    base_params=params_coin,
    regime_series=regime_series,
    regime_params=DEFAULT_PARAMS,
    multipliers={'envelope_std': True},  # Adapter seulement les envelopes
    base_std=0.10  # Référence (RECOVERY)
)
```

**Logique d'adaptation** :
- **BULL** (envelope_std=0.12) : Élargit les envelopes de 20% (0.12/0.10 = 1.2x)
- **BEAR** (envelope_std=0.07) : Resserre les envelopes de 30% (0.07/0.10 = 0.7x)
- **RECOVERY** (envelope_std=0.10) : Pas de changement (1.0x)

**Exemple concret** :
```python
# Envelopes de base : [0.07, 0.10, 0.15]

# En BULL (1.2x) : [0.084, 0.12, 0.18]
# En RECOVERY (1.0x) : [0.07, 0.10, 0.15]
# En BEAR (0.7x) : [0.049, 0.07, 0.105]
```

### 3. CustomAdapter (Logique personnalisée)

Permet de définir votre propre logique d'adaptation.

```python
def aggressive_strategy(date, pair, params):
    """Élargit les envelopes en fin de mois."""
    params = params.copy()
    if date.day > 25:
        params['envelopes'] = [e * 1.5 for e in params['envelopes']]
    return params

adapter = CustomAdapter(
    base_params=params_coin,
    adapter_func=aggressive_strategy,
    description="Aggressive end-of-month"
)
```

## 📊 BacktestComparator

Classe utilitaire pour comparer N backtests.

### Méthodes principales

#### `add_backtest(name, df_trades, df_days, metadata=None)`

Ajoute un backtest à la comparaison.

```python
comparator.add_backtest(
    name="Regime Adaptive",
    df_trades=df_trades,
    df_days=df_days,
    metadata={"leverage": 10, "description": "..."}
)
```

#### `compare() -> pd.DataFrame`

Génère le tableau comparatif complet.

```python
results = comparator.compare()
print(results)
```

**Colonnes calculées** :
- Final Wallet, Total Perf (%)
- Sharpe Ratio, Max DD (%)
- Win Rate (%), N Trades
- Avg PnL (%), Max Win (%), Max Loss (%)
- Total Fees, Avg Exposition
- Avg Duration (h)

#### `rank(metric='Total Perf (%)') -> pd.DataFrame`

Trie les stratégies par métrique.

```python
# Top stratégies par Sharpe
print(comparator.rank('Sharpe Ratio').head())
```

#### `score(weights=None) -> pd.DataFrame`

Calcule un score composite pondéré.

```python
# Score par défaut
scored = comparator.score()

# Score custom
scored = comparator.score(weights={
    'Total Perf (%)': 0.4,
    'Sharpe Ratio': 0.3,
    'Max DD (%)': 0.3
})
```

**Pondérations par défaut** :
- Total Perf: 30%
- Sharpe Ratio: 25%
- Max DD: 20%
- Win Rate: 15%
- Avg PnL: 10%

#### `recommend() -> str`

Retourne automatiquement la meilleure stratégie.

```python
best = comparator.recommend()
print(f"Recommandation: {best}")
```

#### `save_comparison(path)`

Sauvegarde les résultats en CSV.

```python
comparator.save_comparison("backtest_comparison_results.csv")
```

#### `print_summary()`

Affiche un résumé formaté dans la console.

```python
comparator.print_summary()
# ===================================
# 🔍 COMPARAISON DES BACKTESTS
# ===================================
# [Tableau avec toutes les métriques]
#
# ✅ RECOMMANDATION: Regime Adaptive
```

## 🔧 Modification de EnvelopeMulti_v2

Le moteur de backtest a été modifié pour accepter un adaptateur de paramètres.

### Nouveau paramètre : `params_adapter`

```python
def run_backtest(
    self,
    ...,
    params_adapter=None  # 🆕 Adaptateur de paramètres
):
    """
    params_adapter : ParamsAdapter, optional
        Si fourni, adapte dynamiquement les paramètres à chaque date.
        Si None, utilise self.params statiques.
    """
```

### Fonctionnement interne

```python
# Dans la boucle principale
for index, row in df_ini.iterrows():
    for pair in open_long_row:
        # Récupérer les params adaptés pour cette date
        effective_params = (
            params_adapter.get_params_at_date(index, pair)
            if params_adapter
            else params[pair]
        )

        # Recalculer les prix d'entrée avec les params adaptés
        envelope_pct = effective_params["envelopes"][i-1]
        open_price = ma_base * (1 - envelope_pct)  # LONG
        # open_price = ma_base / (1 - envelope_pct)  # SHORT
```

**Avantages** :
- ✅ Aucune modification de `populate_indicators()` requise
- ✅ Calcul dynamique au moment de l'exécution
- ✅ Compatible avec ancienne API (params_adapter=None)
- ✅ Supporte N adaptateurs différents

## 📖 Exemples d'utilisation

### Exemple 1 : Comparer Fixed vs Adaptive

```python
from core import FixedParamsAdapter, RegimeBasedAdapter, BacktestComparator, DEFAULT_PARAMS

# Détecter régime
regime_series = calculate_regime_series(df_btc, confirm_n=12)

# Définir adaptateurs
adapters = {
    "Baseline": FixedParamsAdapter(params_coin),
    "Regime Adaptive": RegimeBasedAdapter(
        params_coin, regime_series, DEFAULT_PARAMS,
        multipliers={'envelope_std': True}, base_std=0.10
    )
}

# Comparer
comparator = BacktestComparator(initial_wallet=1000)

for name, adapter in adapters.items():
    strategy = EnvelopeMulti_v2(df_list, oldest_pair, ["long", "short"], params_coin)
    strategy.populate_indicators()
    strategy.populate_buy_sell()

    df_trades, df_days = strategy.run_backtest(
        initial_wallet=1000,
        leverage=10,
        maker_fee=0.0002,
        taker_fee=0.0006,
        params_adapter=adapter
    )

    comparator.add_backtest(name, df_trades, df_days)

# Résultats
comparator.print_summary()
```

### Exemple 2 : Tester plusieurs variations

```python
# Tester différentes références (base_std)
base_stds = [0.08, 0.10, 0.12]

for std in base_stds:
    adapter = RegimeBasedAdapter(
        params_coin, regime_series, DEFAULT_PARAMS,
        multipliers={'envelope_std': True}, base_std=std
    )

    # ... run_backtest ...

    comparator.add_backtest(f"Adaptive base={std}", df_trades, df_days)

# Voir le meilleur
print(comparator.rank('Sharpe Ratio').head())
```

### Exemple 3 : Adapter selon volatilité

```python
def volatility_adapter(date, pair, params):
    """Élargit les envelopes si haute volatilité."""
    params = params.copy()

    # Calculer ATR ou autre mesure de volatilité
    # (simplifié ici)
    volatility = calculate_volatility(date, pair)

    if volatility > 0.05:  # Haute volatilité
        params['envelopes'] = [e * 1.3 for e in params['envelopes']]

    return params

adapter = CustomAdapter(params_coin, volatility_adapter, "Volatility-based")
```

## 🧪 Tests unitaires

Tous les composants sont testés :

```bash
# Tests des adaptateurs (15 tests)
pytest tests/test_params_adapter.py -v

# Tests du comparateur (24 tests)
pytest tests/test_backtest_comparator.py -v

# Tous les tests
pytest tests/ -v
```

**Couverture** :
- ✅ FixedParamsAdapter : 3 tests
- ✅ RegimeBasedAdapter : 7 tests
- ✅ CustomAdapter : 3 tests
- ✅ BacktestComparator : 24 tests
- ✅ Integration tests : 2 tests

## 📁 Fichiers créés

```
core/
├── params_adapter.py           # Système d'adaptation (300 lignes)
├── backtest_comparator.py      # Comparateur (350 lignes)
└── __init__.py                 # Exports mis à jour

utilities/strategies/
└── envelopeMulti_v2.py         # Modifié (+ params_adapter support)

strategies/envelopes/
├── compare_strategies.ipynb    # Notebook de démonstration
└── INTEGRATION_REGIME_ADAPTATIF.md  # Guide d'intégration (legacy)

tests/
├── test_params_adapter.py      # 15 tests (tous ✅)
└── test_backtest_comparator.py # 24 tests (tous ✅)

GUIDE_COMPARAISON_STRATEGIES.md # Ce guide
```

## 🎯 Workflow recommandé

1. **Définir vos hypothèses**
   - Quels paramètres adapter ?
   - Selon quels critères (régime, volatilité, date) ?

2. **Créer les adaptateurs**
   - Baseline : `FixedParamsAdapter`
   - Variations : `RegimeBasedAdapter` ou `CustomAdapter`

3. **Exécuter les backtests**
   - Un adaptateur = un backtest
   - Garder tous les autres paramètres identiques

4. **Analyser les résultats**
   - `comparator.print_summary()` pour vue d'ensemble
   - `comparator.rank(metric)` pour classement
   - `comparator.score()` pour score composite

5. **Affiner et réitérer**
   - Ajuster les paramètres des adaptateurs
   - Tester sur différentes périodes
   - Valider en walk-forward

## 💡 Bonnes pratiques

### ✅ À faire

- **Tester sur plusieurs périodes** (bull, bear, sideways)
- **Garder un baseline fixe** pour comparaison
- **Documenter la logique** de chaque adaptateur
- **Sauvegarder les résultats** en CSV pour traçabilité
- **Valider statistiquement** (éviter overfitting)

### ❌ À éviter

- **Over-engineering** : Commencer simple (fixed vs adaptive)
- **Trop de paramètres** : Adapter un paramètre à la fois
- **Optimiser sur tout l'historique** : Risque d'overfitting
- **Ignorer les fees/slippage** : Garder réaliste
- **Modifier params_coin entre tests** : Fausse les comparaisons

## 🔮 Extensions futures

Idées pour étendre le système :

1. **Multi-timeframe adaptation**
   ```python
   def mtf_adapter(date, pair, params):
       regime_1h = get_regime(date, "1h")
       regime_4h = get_regime(date, "4h")
       # Adapter selon confluence
   ```

2. **ML-based adaptation**
   ```python
   def ml_adapter(date, pair, params):
       features = extract_features(date, pair)
       prediction = model.predict(features)
       params['envelopes'] = prediction
   ```

3. **Portfolio-level adaptation**
   ```python
   def portfolio_adapter(date, pair, params):
       total_exposure = calculate_total_exposure(date)
       if total_exposure > threshold:
           params['size'] *= 0.5  # Réduire sizing
   ```

## 📞 Support

Pour toute question :
1. Lire [core/README.md](core/README.md) pour détails sur le régime detection
2. Consulter [INTEGRATION_REGIME_ADAPTATIF.md](strategies/envelopes/INTEGRATION_REGIME_ADAPTATIF.md) pour intégration dans notebook existant
3. Examiner [compare_strategies.ipynb](strategies/envelopes/compare_strategies.ipynb) pour exemple complet

## 🎉 Conclusion

Le système de comparaison multi-stratégies vous permet de :
- ✅ **Tester rapidement** différentes configurations
- ✅ **Comparer objectivement** avec métriques standardisées
- ✅ **Automatiser** le processus de sélection
- ✅ **Réutiliser** le code pour de nouveaux tests

**Next step** : Ouvrir [compare_strategies.ipynb](strategies/envelopes/compare_strategies.ipynb) et lancer votre première comparaison !
