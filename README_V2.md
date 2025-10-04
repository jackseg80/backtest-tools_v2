# Guide d'Utilisation - Système V2 avec Marge et Liquidation

## 🚀 Démarrage Rapide

### 1. Ouvrir le notebook
```
strategies/envelopes/multi_envelope.ipynb
```

### 2. Choisir la version du moteur (Cellule 1)
```python
ENGINE_VERSION = "v2"  # Pour le nouveau système corrigé
# ENGINE_VERSION = "v1"  # Pour l'ancien système (legacy)
```

### 3. Configurer le backtest (Cellule 4)
```python
# Paramètres standards
initial_wallet = 1000
leverage = 10          # ⚠️ Attention : 100x très risqué !
stop_loss = 0.2
type = ["long", "short"]

# Paramètres V2 (nouveaux)
gross_cap = 1.5        # Exposition brute max (1.5x equity)
per_side_cap = 1.0     # Expo max par côté (1.0x equity)
per_pair_cap = 0.3     # Expo max par paire (0.3x equity)
use_kill_switch = True # Pause après drawdown
```

### 4. Lancer le backtest
Exécuter la cellule → Les résultats s'affichent automatiquement

## 📋 Différences V1 vs V2

| Aspect | V1 (Legacy) | V2 (Nouveau) |
|--------|-------------|--------------|
| **Liquidation** | Après clôture trade (trop tard) | Intra-bougie (vérifie low/high) |
| **Prix liquidation** | Non calculé | Calculé avec formule exchange |
| **Marge** | Non gérée | `init_margin` réservé |
| **Exposure caps** | Aucune limite | Caps automatiques |
| **Kill-switch** | Non | -8% day / -12% hour |
| **Leverage** | Bug (résultats impossibles) | Correct (réaliste) |

## 🎯 Exemples de Résultats

### Exemple 1 : Leverage 100x (risque extrême)

**V1** :
```
Wallet final: 337,758$ (+33,675%) ❌ IMPOSSIBLE
Max drawdown: -30%
Trades: 5415
```

**V2** :
```
Wallet final: 0$ (liquidation)  ✅ RÉALISTE
Liquidation: 2020-03-12 (COVID crash)
Prix BTC entry: 8,000$
Prix liquidation: 7,952$ (-0.6%)
```

### Exemple 2 : Leverage 10x (modéré)

**V1** :
```
Wallet final: 5,234$
Sous-estime le risque de liquidation
```

**V2** :
```
Wallet final: 4,892$
2 liquidations détectées (crashes majeurs)
Liquidation à -9.6% du prix d'entrée
```

## 🔍 Analyse des Liquidations (V2 uniquement)

Après le backtest, une cellule dédiée affiche :

```
⚠️ LIQUIDATIONS DÉTECTÉES : 2 trades liquidés
================================================================================

📉 BTC/USDT:USDT - LONG
   Date: 2020-03-12 (COVID crash)
   Entry: 8,000.00$
   Liquidation: 7,952.00$
   Drop: -0.60%
   Wallet après: 0.00$

📉 DOGE/USDT:USDT - SHORT
   Date: 2021-05-08 (Elon tweet pump)
   Entry: 0.6500$
   Liquidation: 0.6539$
   Rise: +0.60%
   Wallet après: 0.00$
```

## ⚙️ Configuration Avancée

### Ajuster les Exposure Caps

Pour un profil **conservateur** :
```python
gross_cap = 1.0        # Max 1x equity total
per_side_cap = 0.5     # Max 0.5x par côté
per_pair_cap = 0.2     # Max 0.2x par paire
```

Pour un profil **agressif** :
```python
gross_cap = 2.0        # Max 2x equity total
per_side_cap = 1.5     # Max 1.5x par côté
per_pair_cap = 0.5     # Max 0.5x par paire
```

### Ajuster le Kill-Switch

Plus conservateur :
```python
# Dans utilities/margin.py, modifier KillSwitch
KillSwitch(day_pnl_threshold=-0.05, hour_pnl_threshold=-0.08, pause_hours=48)
# Déclenche à -5% day / -8% hour, pause 48h
```

Plus agressif :
```python
KillSwitch(day_pnl_threshold=-0.12, hour_pnl_threshold=-0.15, pause_hours=12)
# Déclenche à -12% day / -15% hour, pause 12h
```

Désactiver complètement :
```python
use_kill_switch = False
```

### Modifier la Table MMR

Dans `utilities/margin.py` :
```python
MMR_TABLE = {
    "BTC/USDT:USDT": 0.004,   # 0.4%
    "ETH/USDT:USDT": 0.005,   # 0.5%
    "SOL/USDT:USDT": 0.0075,  # 0.75%
    # ... ajouter vos paires
    "default": 0.010          # 1.0% pour les alts
}
```

## 📊 Comparaison V1 vs V2

### Méthode
1. Lancer backtest avec `ENGINE_VERSION = "v1"`
2. Noter les résultats (wallet, sharpe, max DD)
3. Changer pour `ENGINE_VERSION = "v2"`
4. Relancer et comparer

### Cas d'usage

**Quand utiliser V1** :
- Backtests historiques (comparaison)
- Leverage = 1x (pas d'impact du bug)
- Validation de stratégie sans leverage

**Quand utiliser V2** :
- **Tous les backtests avec leverage > 1x**
- Production / trading réel
- Analyse de risque réaliste
- Validation finale avant déploiement

## 🧪 Tests Disponibles

### Tests unitaires complets
```bash
python tests/test_margin.py
```
Résultat attendu : `24/24 tests passed`

### Tests rapides
```bash
python tests/test_v2_quick.py
```
Vérifie les calculs de liquidation

### Tests d'intégration
```bash
python tests/test_envelopeMulti_v2_integration.py
```
Teste le moteur complet avec scénarios

## ⚠️ Avertissements Importants

### Leverage Élevé
- **100x** : Liquidation à -0.6% → Extrêmement risqué
- **50x** : Liquidation à -1.2%
- **20x** : Liquidation à -3.0%
- **10x** : Liquidation à -9.6% → Recommandé maximum

### Backtests vs Réalité
Les backtests V2 sont plus réalistes mais ne tiennent **pas compte** de :
- Slippage important sur ordres gros
- Liquidité limitée (orderbook depth)
- Latence réseau / exchange
- Funding rates
- Changements de MMR par l'exchange

### Production
Avant de trader en réel :
1. ✅ Valider avec V2 (pas V1 !)
2. ✅ Tester avec leverage conservateur (5x max)
3. ✅ Activer kill-switch
4. ✅ Configurer exposure caps stricts
5. ✅ Backtester sur plusieurs cycles de marché

## 📚 Documentation Complète

- **CHANGELOG_V2.md** : Détails techniques des changements
- **utilities/margin.py** : Code source avec docstrings
- **tests/** : Exemples d'utilisation

## 🆘 Troubleshooting

### Erreur : "cannot import EnvelopeMulti_v2"
→ Vérifier que `ENGINE_VERSION = "v2"` dans la cellule 1

### Wallet = 0 immédiatement
→ Leverage trop élevé, réduire à 10x ou moins

### Pas de trades
→ Vérifier que les données sont chargées (`df_list` non vide)

### "Exposure cap exceeded"
→ Augmenter les caps ou réduire les `size` dans params

### Kill-switch se déclenche trop
→ Réduire les thresholds ou désactiver (`use_kill_switch=False`)

## 📞 Support

Pour toute question sur V2 :
1. Lire `CHANGELOG_V2.md` (détails techniques)
2. Consulter les tests (`tests/test_*.py`)
3. Vérifier la configuration dans le notebook

---

**Version** : 2.0.0
**Date** : 2025-01-03
**Status** : ✅ Production Ready
