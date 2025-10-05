# 🎯 Intégration Système de Régime Adaptatif dans multi_envelope.ipynb

## Option 1 : Cellule Simple (Paramètres Adaptatifs Uniquement)

**Insérer cette cellule APRÈS la cellule 2 (chargement données) et AVANT la cellule de backtest**

```python
# ============================================================
# 🆕 ADAPTATION AUTOMATIQUE DES PARAMÈTRES PAR RÉGIME
# ============================================================

# Activer/désactiver le système adaptatif
USE_ADAPTIVE_REGIME = True  # False = utiliser params fixes de cellule 2

if USE_ADAPTIVE_REGIME:
    print("=" * 80)
    print("SYSTÈME DE RÉGIME ADAPTATIF ACTIVÉ")
    print("=" * 80)

    # Import du système de régime
    from core import (
        Regime,
        Mode,
        calculate_regime_series,
        get_mode_for_regime,
        DEFAULT_PARAMS
    )

    # 1. Charger données BTC pour détection régime global
    df_btc = df_list["BTC/USDT:USDT"].copy()

    # 2. Calculer EMAs pour détection
    df_btc['ema50'] = df_btc['close'].ewm(span=50, adjust=False).mean()
    df_btc['ema200'] = df_btc['close'].ewm(span=200, adjust=False).mean()

    # 3. Détecter régimes (hystérésis = 12 barres)
    regimes = calculate_regime_series(
        df_btc=df_btc[['close', 'ema50', 'ema200']],
        confirm_n=12  # Ajuster selon timeframe (12 pour 1h, 18-24 pour 4h)
    )

    # 4. Analyser distribution des régimes
    regime_counts = regimes.value_counts()
    print(f"\n📊 Distribution des régimes détectés:")
    for regime, count in regime_counts.items():
        pct = count / len(regimes) * 100
        print(f"   {regime.value.upper():10s}: {count:5d} barres ({pct:5.1f}%)")

    # 5. Adapter les paramètres d'enveloppe par régime
    # On va générer des params dynamiques basés sur le régime dominant de chaque période

    # Stratégie: Utiliser le régime DOMINANT de la période pour adapter les envelopes
    dominant_regime = regimes.mode()[0]
    regime_params = DEFAULT_PARAMS[dominant_regime]

    print(f"\n🎯 Régime dominant détecté: {dominant_regime.value.upper()}")
    print(f"   Mode de trading: {get_mode_for_regime(dominant_regime).value}")
    print(f"   Paramètres appliqués:")
    print(f"      Envelope base: {regime_params.envelope_std:.3f}")
    print(f"      TP multiplier: {regime_params.tp_mult:.1f}x")
    print(f"      SL multiplier: {regime_params.sl_mult:.1f}x")
    print(f"      Trailing stop: {regime_params.trailing:.1f}" if regime_params.trailing else "      Trailing stop: None")
    print(f"      Shorts autorisés: {'OUI' if regime_params.allow_shorts else 'NON'}")

    # 6. Adapter les enveloppes en fonction du régime
    # On multiplie les enveloppes de base par le ratio envelope_std du régime
    base_envelope_std = 0.10  # Valeur de référence (recovery)
    envelope_multiplier = regime_params.envelope_std / base_envelope_std

    print(f"\n⚙️  Adaptation des enveloppes (multiplier: {envelope_multiplier:.2f}x)")

    # Créer nouveaux params adaptés
    params_adaptive = {}
    for pair, p in params.items():
        params_adaptive[pair] = p.copy()

        # Adapter les enveloppes
        original_envelopes = params_live[pair]['envelopes']
        adapted_envelopes = [env * envelope_multiplier for env in original_envelopes]
        params_adaptive[pair]['envelopes'] = adapted_envelopes

        # Afficher pour debug (premières 3 paires)
        if pair in list(params.keys())[:3]:
            print(f"   {pair}:")
            print(f"      Original: {original_envelopes}")
            print(f"      Adapté:   {[f'{e:.3f}' for e in adapted_envelopes]}")

    # 7. Adapter le mode de trading (LONG_ONLY / LONG_SHORT)
    mode = get_mode_for_regime(dominant_regime)

    if mode == Mode.LONG_ONLY and regime_params.allow_shorts == False:
        # Forcer LONG ONLY (désactiver shorts)
        type = ["long", ""]
        print(f"\n🔒 Mode LONG_ONLY activé (shorts désactivés)")
    elif mode == Mode.LONG_SHORT:
        # Autoriser LONG + SHORT
        type = ["long", "short"]
        print(f"\n🔓 Mode LONG_SHORT activé (longs + shorts)")
    elif mode == Mode.SHORT_ONLY:
        # SHORT ONLY (rare, uniquement si simplified=True en bear)
        type = ["", "short"]
        print(f"\n📉 Mode SHORT_ONLY activé (shorts uniquement)")

    # 8. Remplacer params par params_adaptive
    params = params_adaptive

    print(f"\n✅ Paramètres adaptatifs appliqués avec succès!")
    print(f"   {len(params)} paires configurées avec régime {dominant_regime.value.upper()}")
    print("=" * 80)

else:
    print("\n⏭️  Système adaptatif désactivé - utilisation params fixes de cellule 2\n")
```

## Option 2 : Cellule Avancée (Adaptation par Période)

**Pour adapter dynamiquement les params PENDANT le backtest (plus complexe)**

```python
# ============================================================
# 🆕 ADAPTATION DYNAMIQUE PAR PÉRIODE (AVANCÉ)
# ============================================================

USE_ADAPTIVE_BY_PERIOD = True

if USE_ADAPTIVE_BY_PERIOD:
    from core import Regime, calculate_regime_series, DEFAULT_PARAMS

    # Charger et détecter régimes
    df_btc = df_list["BTC/USDT:USDT"].copy()
    df_btc['ema50'] = df_btc['close'].ewm(span=50, adjust=False).mean()
    df_btc['ema200'] = df_btc['close'].ewm(span=200, adjust=False).mean()
    regimes = calculate_regime_series(df_btc[['close', 'ema50', 'ema200']], confirm_n=12)

    # Découper en périodes par régime
    regime_changes = (regimes != regimes.shift()).cumsum()
    periods = []

    for period_id in regime_changes.unique():
        mask = regime_changes == period_id
        period_dates = regimes.index[mask]
        period_regime = regimes[mask].iloc[0]

        periods.append({
            'start': period_dates[0],
            'end': period_dates[-1],
            'regime': period_regime,
            'duration': len(period_dates)
        })

    print(f"📅 {len(periods)} périodes de régime détectées:")
    for i, p in enumerate(periods[:10]):  # Afficher les 10 premières
        print(f"   #{i+1}: {p['start'].date()} → {p['end'].date()} | {p['regime'].value.upper()} ({p['duration']} barres)")

    # Pour chaque période, on va lancer un backtest séparé
    print(f"\n🔄 Backtests multi-périodes avec params adaptatifs...")

    all_trades = []
    all_days = []

    for period in periods:
        # Filtrer données pour cette période
        df_list_period = {
            pair: df.loc[period['start']:period['end']]
            for pair, df in df_list.items()
        }

        # Adapter params pour ce régime
        regime_params = DEFAULT_PARAMS[period['regime']]
        envelope_mult = regime_params.envelope_std / 0.10

        params_period = {}
        for pair, p in params.items():
            params_period[pair] = p.copy()
            params_period[pair]['envelopes'] = [
                env * envelope_mult
                for env in params_live[pair]['envelopes']
            ]

        # Lancer backtest pour cette période
        # ... (code de backtest)

    print(f"✅ Backtests multi-périodes terminés!")
```

## 📝 Instructions d'Utilisation

### Étape 1 : Copier la cellule

1. Ouvrir [multi_envelope.ipynb](multi_envelope.ipynb)
2. Positionner le curseur **APRÈS la cellule 2** (chargement données)
3. Créer une **nouvelle cellule**
4. Copier-coller le code de **Option 1** (recommandé pour commencer)

### Étape 2 : Exécuter le notebook

```python
# Cellule 1: Imports
# Cellule 2: Chargement données
# 🆕 Cellule 3: Système adaptatif (NOUVELLE)
# Cellule 4: Backtest (utilise les params adaptés)
```

### Étape 3 : Comparer les résultats

Pour comparer **avec/sans** adaptation :

```python
# Dans la nouvelle cellule, changer:
USE_ADAPTIVE_REGIME = False  # Désactiver
# puis
USE_ADAPTIVE_REGIME = True   # Activer

# Relancer le backtest et comparer les métriques
```

## 🎯 Paramètres par Régime (Rappel)

| Régime | Envelope Std | TP/SL | Mode | Exemple Période |
|--------|-------------|-------|------|-----------------|
| **BULL** | 0.12 (+20%) | 2.5x/1.2x | LONG_ONLY | 2020-2021, 2024 |
| **RECOVERY** | 0.10 (base) | 2.0x/1.0x | LONG_ONLY | 2023 |
| **BEAR** | 0.07 (-30%) | 1.6x/0.9x | LONG_SHORT | 2022 |

## ⚙️ Configuration Avancée

### Ajuster l'hystérésis

```python
# Plus sensible (changements rapides)
regimes = calculate_regime_series(df_btc, confirm_n=5)

# Plus stable (évite flip-flop)
regimes = calculate_regime_series(df_btc, confirm_n=20)
```

### Adapter par paire (au lieu de global)

```python
# Pour chaque paire, détecter son propre régime
for pair in pair_list:
    df_pair = df_list[pair].copy()
    df_pair['ema50'] = df_pair['close'].ewm(span=50, adjust=False).mean()
    df_pair['ema200'] = df_pair['close'].ewm(span=200, adjust=False).mean()

    regime_pair = calculate_regime_series(df_pair[['close', 'ema50', 'ema200']], confirm_n=12)
    # Adapter params spécifiquement pour cette paire
```

## 🔬 Comparaison Résultats Attendus

**Sans adaptation (params fixes):**
- Sharpe: ~4.38
- Performance: ~1672%
- Win Rate: ~73%

**Avec adaptation (régime global):**
- Sharpe: **potentiellement meilleur** (plus adapté aux conditions)
- Performance: **similaire ou supérieure** (moins de trades en bear mal configuré)
- Win Rate: **potentiellement meilleur** (enveloppes adaptées)

## 📚 Références

- [core/README.md](../../core/README.md) - Documentation complète
- [multi_envelope_adaptive.ipynb](multi_envelope_adaptive.ipynb) - Notebook démo complet
- [backtests/backtest_runner.py](../../backtests/backtest_runner.py) - Smoke test

---

**Bon backtest ! 🚀**
