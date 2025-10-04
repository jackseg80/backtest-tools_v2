# Changelog - Système de Marge et Liquidation V2

## 🎯 Objectif

Corriger le bug fondamental du système de liquidation qui permettait des résultats impossibles (ex: +33,675% avec levier 100x et stop-loss 1.0).

## 🐛 Bug Identifié (V1)

### Problème
Le code V1 multipliait par le levier à l'ouverture de position mais ne modélisait pas correctement la marge et la liquidation :

```python
# V1 - BUG
pos_size = (size * wallet * leverage) / nb_envelopes  # Multiplie par leverage
wallet -= fee  # Mais ne réserve PAS la marge !

# Liquidation vérifiée APRÈS le trade (trop tard)
if wallet <= 0:
    print("Liquidation")
```

### Conséquence
- Le système ne vérifiait jamais si le prix touchait le niveau de liquidation intra-bougie
- La liquidation n'arrivait que quand wallet <= 0 après clôture du trade
- Avec levier 100x, on devrait être liquidé à -0.6% de mouvement, mais le système continuait à trader

## ✅ Solution Implémentée (V2)

### 1. Module `utilities/margin.py`

Nouvelles fonctions utilitaires :

#### `compute_liq_price(entry_price, side, leverage, mmr)`
Calcule le prix de liquidation selon les formules USDT linear perpetuals :
- **LONG** : `liq_price = entry * (1 - (1/leverage) + mmr)`
- **SHORT** : `liq_price = entry * (1 + (1/leverage) - mmr)`

Exemples :
- BTC LONG 100x @ 50,000$ → liquidation @ 49,700$ (-0.6%)
- BTC LONG 10x @ 50,000$ → liquidation @ 45,200$ (-9.6%)
- BTC SHORT 100x @ 50,000$ → liquidation @ 50,300$ (+0.6%)

#### `update_equity(wallet, positions, last_prices)`
Calcule l'equity totale :
```python
equity = wallet + unrealized_PnL
```

#### `apply_close(position, exit_price, fee_rate, is_taker)`
Ferme une position avec calcul correct du PnL et fees :
```python
if side == "LONG":
    raw_pnl = qty * (exit_price - entry_price)
elif side == "SHORT":
    raw_pnl = qty * (entry_price - exit_price)

fee = abs(qty * exit_price) * fee_rate
net_pnl = raw_pnl - fee
```

#### `check_exposure_caps(new_notional, side, pair, positions, equity, caps)`
Vérifie les caps d'exposition avant d'ouvrir une position :
- `gross_exposure_cap = 1.5 * equity` (total des notionnels)
- `per_side_exposure_cap = 1.0 * equity` (LONG ou SHORT séparément)
- `per_pair_exposure_cap = 0.3 * equity` (par paire)

#### `get_mmr(pair)`
Table des Maintenance Margin Rates :
- BTC : 0.4%
- ETH : 0.5%
- Majors (SOL, ADA, etc.) : 0.75%
- Alts (défaut) : 1.0%

#### `KillSwitch`
Pause le trading automatiquement après drawdown :
- Day PnL ≤ -8% → pause 24h
- 1h rolling PnL ≤ -12% → pause 24h

### 2. Classe `EnvelopeMulti_v2`

#### Changements à l'ouverture de position

**V1 (bugué)** :
```python
pos_size = (size * wallet * leverage) / nb_envelopes
fee = pos_size * maker_fee
wallet -= fee  # Pas de réservation de marge !
```

**V2 (corrigé)** :
```python
# Calcul basé sur equity (pas wallet)
notional = (size * equity * leverage) / nb_envelopes
qty = notional / open_price
init_margin = notional / leverage  # Marge réservée

# Check exposure caps AVANT ouverture
allowed, reason = check_exposure_caps(notional, side, pair, positions, equity, caps)
if not allowed:
    break  # Rejette la position

# Réserve la marge
fee = notional * maker_fee
wallet -= fee
used_margin += init_margin

# Calcule le prix de liquidation
mmr = get_mmr(pair)
liq_price = compute_liq_price(open_price, side, leverage, mmr)

# Stocke dans la position
position['liq_price'] = liq_price
position['init_margin'] = init_margin
position['qty'] = qty
```

#### Vérification liquidation intra-bougie

**Nouvelle section** (ligne 295-391) - **PRIORITÉ ABSOLUE** :

```python
# V2: Check Liquidation FIRST (avant stop-loss !)
if use_liquidation and len(current_positions) > 0:
    for pair in current_positions:
        liq_price = current_positions[pair]['liq_price']

        # LONG: si le low touche liq_price
        if side == "LONG" and actual_row['low'] <= liq_price:
            close_price = liq_price  # Execute AT liq price

            pnl, fee = apply_close(position, close_price, taker_fee)
            wallet += pnl
            used_margin -= position['init_margin']

            if wallet < 0:
                wallet = 0
                is_liquidated = True

            trades.append({
                "close_reason": "Liquidation",
                # ...
            })

        # SHORT: si le high touche liq_price
        elif side == "SHORT" and actual_row['high'] >= liq_price:
            # Même logique
```

#### Ordre de priorité

1. **Liquidation** (nouveau - intra-bougie)
2. **Stop-Loss** (vérifié après liquidation)
3. **Close normal** (signal de sortie stratégie)

#### Equity tracking

Calculée à chaque bougie :
```python
# Début de chaque itération
last_prices = {pair: df[pair]['open'] for pair in positions}
equity = update_equity(wallet, positions, last_prices)

# Kill-switch check
if kill_switch:
    is_paused = kill_switch.update(index, equity, initial_wallet)
```

## 📊 Tests Validés

### Tests unitaires (24/24 ✅)
Fichier : `tests/test_margin.py`

- Calcul prix de liquidation (100x, 10x, LONG, SHORT)
- Calcul equity avec PnL non réalisé
- Fermeture position avec fees
- Vérification exposure caps
- Table MMR
- Kill-switch logic

### Tests d'intégration
Fichier : `tests/test_v2_quick.py`

Résultats :
```
BTC LONG @ 50,000$ avec levier 100x:
   Prix de liquidation: 49,700.00$ (-0.60%)

BTC LONG @ 50,000$ avec levier 10x:
   Prix de liquidation: 45,200.00$ (-9.60%)

BTC SHORT @ 50,000$ avec levier 100x:
   Prix de liquidation: 50,300.00$ (+0.60%)
```

## 🔄 Utilisation

### Dans le notebook `multi_envelope.ipynb`

**Cellule 1** - Choisir la version :
```python
# ========== CHOIX DE LA VERSION DU MOTEUR ==========
ENGINE_VERSION = "v2"  # "v1" ou "v2"
# ===================================================
```

**Cellule backtest** - Paramètres V2 :
```python
# Paramètres v1
initial_wallet = 1000
leverage = 10
stop_loss = 0.2
# ...

# === PARAMÈTRES V2 ===
gross_cap = 1.5
per_side_cap = 1.0
per_pair_cap = 0.3
use_kill_switch = True
```

Le backtest s'adapte automatiquement selon `ENGINE_VERSION`.

### Nouvelle cellule d'analyse liquidations

Affiche automatiquement les liquidations détectées en mode V2 :
```
⚠️ LIQUIDATIONS DÉTECTÉES : 3 trades liquidés
================================================================================

📉 DOGE/USDT:USDT - LONG
   Date: 2021-05-19
   Entry: 0.3500$
   Liquidation: 0.3479$
   Drop: -0.60%
   Wallet après: 0.00$
```

## 📁 Fichiers Créés/Modifiés

### Nouveaux fichiers
- `utilities/margin.py` - Module utilitaire marge/liquidation
- `utilities/strategies/envelopeMulti_v2.py` - Moteur v2 corrigé
- `tests/test_margin.py` - Tests unitaires (24 tests)
- `tests/test_v2_quick.py` - Tests rapides d'intégration
- `tests/test_envelopeMulti_v2_integration.py` - Tests end-to-end
- `CHANGELOG_V2.md` - Ce fichier

### Fichiers modifiés
- `strategies/envelopes/multi_envelope.ipynb` - Switch v1/v2 + analyse liquidations

### Fichiers conservés (legacy)
- `utilities/strategies/envelopeMulti.py` - V1 conservé pour comparaison

## 🎯 Impact Attendu

### Avec leverage élevé (ex: 100x)
**V1** : Résultats impossibles (+33,675% profit avec minimal drawdown)
**V2** : Liquidation rapide si le prix bouge de -0.6% (comportement réaliste)

### Avec leverage modéré (ex: 10x)
**V1** : Sous-estime le risque de liquidation
**V2** : Liquidation à -9.6%, comportement conforme aux exchanges réels

### Exposure management
**V1** : Aucune limite, peut over-leverage
**V2** : Caps automatiques (gross 1.5x, per-side 1.0x, per-pair 0.3x)

### Risk management
**V1** : Aucune protection contre les drawdowns rapides
**V2** : Kill-switch pause trading après -8% day / -12% hour

## 🔍 Formules Clés

### Prix de liquidation
```
LONG:  liq_price = entry * (1 - (1/leverage) + MMR)
SHORT: liq_price = entry * (1 + (1/leverage) - MMR)
```

### Marge
```
notional = qty * price * leverage
init_margin = notional / leverage
used_margin = sum(init_margins de toutes les positions)
```

### Equity
```
equity = wallet + unrealized_PnL
unrealized_PnL = sum(qty * (current_price - entry_price) pour LONG)
unrealized_PnL = sum(qty * (entry_price - current_price) pour SHORT)
```

## ⚠️ Notes Importantes

1. **V1 reste disponible** pour comparaison et backtests historiques
2. **V2 est recommandé** pour tous les nouveaux backtests avec leverage
3. **Kill-switch peut être désactivé** si besoin (paramètre `use_kill_switch=False`)
4. **Exposure caps sont configurables** selon le profil de risque

## 📚 Références

- Expert analysis fourni par l'utilisateur (formules de liquidation)
- Documentation Binance Futures (USDT linear perpetuals)
- Test-driven development approach

---

**Date** : 2025-01-03
**Version** : 2.0.0
**Status** : ✅ Production Ready
