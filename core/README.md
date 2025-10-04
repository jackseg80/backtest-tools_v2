# Système de Régime Adaptatif

Système de détection automatique de régime de marché (BULL/BEAR/RECOVERY) avec adaptation dynamique des paramètres de trading.

## 📋 Vue d'ensemble

Ce système détecte automatiquement le régime de marché en utilisant BTC comme proxy global et adapte :
- **Le mode de trading** (LONG_ONLY, LONG_SHORT, SHORT_ONLY)
- **Les paramètres d'enveloppe** (largeur, TP/SL, trailing stop)
- **La gestion des positions** (fermeture automatique lors de transitions)

## 🏗️ Architecture

### Modules core

```
core/
├── __init__.py              # Exports publics
├── regime_selector.py       # Détection de régime
├── mode_router.py           # Mapping régime → mode
├── params_registry.py       # Paramètres par régime
└── regime_transitions.py    # Gestion des transitions
```

### Régimes détectés

| Régime | Conditions | Mode par défaut |
|--------|-----------|-----------------|
| **BULL** | close > EMA200 AND ema50 > EMA200 AND slope(EMA200) ≥ 0 | LONG_ONLY |
| **BEAR** | close < EMA200 AND ema50 < EMA200 AND slope(EMA200) < 0 | LONG_SHORT |
| **RECOVERY** | Autres cas (transitions, consolidations) | LONG_ONLY |

### Paramètres par régime

| Paramètre | BULL | RECOVERY | BEAR |
|-----------|------|----------|------|
| **Envelope std** | 0.12 | 0.10 | 0.07 |
| **TP multiplier** | 2.5 | 2.0 | 1.6 |
| **SL multiplier** | 1.2 | 1.0 | 0.9 |
| **Trailing stop** | 0.8 | 0.7 | 0.6 |
| **Allow shorts** | ❌ | ✅ | ✅ |

## 🚀 Usage

### Import basique

```python
from core import (
    Regime,
    Mode,
    calculate_regime_series,
    get_mode_for_regime,
    DEFAULT_PARAMS
)
```

### Détection de régime

```python
import pandas as pd

# Charger données BTC avec EMAs
df_btc = load_btc_data()  # Doit contenir: close, ema50, ema200

# Détecter régimes avec hystérésis
regimes = calculate_regime_series(
    df_btc=df_btc[['close', 'ema50', 'ema200']],
    confirm_n=12  # 12 barres pour confirmer changement
)

# Résultat: Series[datetime → Regime]
print(regimes.value_counts())
```

### Récupérer mode et paramètres

```python
# Pour une date donnée
regime = regimes.loc['2024-01-01']
mode = get_mode_for_regime(regime, simplified=False)
params = DEFAULT_PARAMS[regime]

print(f"Régime: {regime.value}")
print(f"Mode: {mode.value}")
print(f"Envelope std: {params.envelope_std}")
print(f"Allow shorts: {params.allow_shorts}")
```

### Gérer les transitions

```python
from core import handle_regime_change

# Simuler positions ouvertes
open_positions = {
    'long': [{'id': 'L1', 'size': 0.1}],
    'short': [{'id': 'S1', 'size': 0.05}]
}

# Détecter transition BEAR → BULL
old_regime = Regime.BEAR
new_regime = Regime.BULL
params = DEFAULT_PARAMS[new_regime]

# Générer ordres de clôture
closing_orders = handle_regime_change(
    old_regime=old_regime,
    new_regime=new_regime,
    mode_simplified=False,
    params=params,
    open_positions=open_positions
)

# Résultat: Liste d'ordres pour fermer shorts (interdits en LONG_ONLY)
for order in closing_orders:
    print(f"Close {order['side']} position {order['id']}: {order['reason']}")
```

## 📊 Exemples

### Notebook démo complet

Voir [strategies/envelopes/multi_envelope_adaptive.ipynb](../strategies/envelopes/multi_envelope_adaptive.ipynb) pour :
- Chargement données BTC proxy
- Calcul régimes sur période 2020-2025
- Visualisation régimes/transitions avec Plotly
- Export décisions CSV pour backtest

### Smoke test runner

```bash
python backtests/backtest_runner.py
```

Teste la détection sur 3 périodes synthétiques :
- Bull 2020-2021 → BULL détecté ✅
- Bear 2022 → BEAR détecté ✅
- Recovery 2023 → RECOVERY détecté ✅

## 🧪 Tests

### Tests unitaires

```bash
# Tous les tests (33 tests)
pytest tests/test_regime_selector.py \
       tests/test_mode_router.py \
       tests/test_params_registry.py \
       tests/test_regime_transitions.py -v

# Tests spécifiques
pytest tests/test_regime_selector.py::TestRegimeDetection::test_bull_regime_detection -v
```

### Couverture

| Module | Tests | Couverture |
|--------|-------|------------|
| regime_selector | 11 | Cas limites, transitions, séries réelles |
| mode_router | 5 | Tous régimes, simplified True/False |
| params_registry | 10 | Types, valeurs, ranges |
| regime_transitions | 7 | Positions, closures, flags |

## ⚙️ Configuration

### Ajuster l'hystérésis

```python
# Plus sensible (changements rapides)
regimes = calculate_regime_series(df_btc, confirm_n=5)

# Plus stable (évite flip-flop)
regimes = calculate_regime_series(df_btc, confirm_n=20)
```

### Mode simplifié

```python
# BEAR → SHORT_ONLY au lieu de LONG_SHORT
mode = get_mode_for_regime(Regime.BEAR, simplified=True)
# Result: Mode.SHORT_ONLY
```

### Personnaliser paramètres

```python
from dataclasses import replace
from core import DEFAULT_PARAMS, Regime

# Modifier params BULL
custom_bull_params = replace(
    DEFAULT_PARAMS[Regime.BULL],
    envelope_std=0.15,  # Plus large
    allow_shorts=True   # Activer shorts
)
```

## 📈 Intégration backtest

### 1. Détection régime global (proxy BTC)

```python
df_btc = load_btc_with_emas()
regimes = calculate_regime_series(df_btc, confirm_n=12)
```

### 2. Routing par date dans backtest

```python
for date in backtest_dates:
    # Récupérer régime du jour
    regime = regimes.loc[date]
    mode = get_mode_for_regime(regime)
    params = DEFAULT_PARAMS[regime]

    # Désactiver signaux interdits
    if mode == Mode.LONG_ONLY:
        # Ignorer open_short_* signals
        ...
    elif mode == Mode.SHORT_ONLY:
        # Ignorer open_long_* signals
        ...

    # Appliquer params dynamiques
    envelope_width = params.envelope_std
    tp_mult = params.tp_mult
    sl_mult = params.sl_mult
```

### 3. Gérer transitions

```python
if regime != prev_regime:
    closing_orders = handle_regime_change(
        old_regime=prev_regime,
        new_regime=regime,
        mode_simplified=False,
        params=DEFAULT_PARAMS[regime],
        open_positions=current_positions
    )
    # Exécuter closures à la barre suivante
    for order in closing_orders:
        close_position(order['id'])
```

## 🔧 Troubleshooting

### Problème : Trop de flip-flop entre régimes

**Solution** : Augmenter `confirm_n`

```python
regimes = calculate_regime_series(df_btc, confirm_n=18)  # Au lieu de 12
```

### Problème : Régime RECOVERY sur 100% des barres

**Cause** : EMAs mal calculées ou données insuffisantes

**Solution** :
```python
# Vérifier EMAs
assert df_btc['ema50'].notna().all()
assert df_btc['ema200'].notna().all()

# S'assurer de min_periods pour données récentes
df_btc['ema200'] = df_btc['close'].ewm(span=200, min_periods=1).mean()
```

### Problème : Positions non fermées lors de transition

**Cause** : `close_opposite_on_switch=False`

**Solution** :
```python
from dataclasses import replace

params = replace(DEFAULT_PARAMS[regime], close_opposite_on_switch=True)
```

## 📚 Références

- **Logique de détection** : Voir docstrings dans `regime_selector.py`
- **Exemples visuels** : Notebook `multi_envelope_adaptive.ipynb`
- **Tests de référence** : `tests/test_regime_selector.py`

## 🚧 Limitations actuelles

1. **Régime global uniquement** : Utilise BTC comme proxy pour tous les assets
2. **Pas de machine learning** : Règles déterministes EMA-based
3. **Paramètres fixes** : `DEFAULT_PARAMS` non optimisés par grid search
4. **Pas de confiance** : Pas de score de confiance du régime détecté

## 🔮 Améliorations futures

- [ ] Grid search pour optimiser `envelope_std` par régime
- [ ] Régime par asset (au lieu de global)
- [ ] Score de confiance (0-1) pour chaque détection
- [ ] Multi-timeframe (4h + daily pour confirmation)
- [ ] Indicateurs additionnels (volume, ATR, RSI)
