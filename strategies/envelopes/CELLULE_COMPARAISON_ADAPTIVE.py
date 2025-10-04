# ============================================================
# 🆚 COMPARAISON BACKTEST: PARAMS FIXES vs ADAPTATIFS
# ============================================================
# Cellule à insérer APRÈS la cellule 2 (chargement données)
# et AVANT la cellule de backtest dans multi_envelope.ipynb

import pandas as pd
from core import (
    Regime,
    Mode,
    calculate_regime_series,
    get_mode_for_regime,
    DEFAULT_PARAMS
)

print("=" * 100)
print("COMPARAISON: STRATÉGIE FIXE vs ADAPTATIVE PAR RÉGIME")
print("=" * 100)

# ============================================================
# 1️⃣ BACKTEST AVEC PARAMS FIXES (BASELINE)
# ============================================================

print("\n" + "=" * 100)
print("1️⃣  BACKTEST BASELINE (Params fixes - configuration actuelle)")
print("=" * 100)

# Utiliser les params de la cellule 2 (déjà chargés)
params_fixed = params.copy()

# Lancer backtest avec params fixes
strat_fixed = EnvelopeMulti(
    df_list=df_list,
    oldest_pair=oldest_pair,
    type=["long", ""],  # LONG ONLY (config actuelle)
    params=params_fixed
)

strat_fixed.populate_indicators()
strat_fixed.populate_buy_sell()

if ENGINE_VERSION == "v2":
    bt_fixed = strat_fixed.run_backtest(
        initial_wallet=initial_wallet,
        leverage=leverage,
        maker_fee=maker_fee,
        taker_fee=taker_fee,
        stop_loss=stop_loss,
        reinvest=reinvest,
        liquidation=liquidation,
        gross_cap=gross_cap,
        per_side_cap=per_side_cap,
        per_pair_cap=per_pair_cap,
        margin_cap=margin_cap,
        use_kill_switch=use_kill_switch,
        auto_adjust_size=auto_adjust_size,
        extreme_leverage_threshold=extreme_leverage_threshold,
        risk_mode=risk_mode,
        max_expo_cap=max_expo_cap
    )
else:
    bt_fixed = strat_fixed.run_backtest(
        initial_wallet=initial_wallet,
        leverage=leverage,
        maker_fee=maker_fee,
        taker_fee=taker_fee,
        stop_loss=stop_loss,
        reinvest=reinvest,
        liquidation=liquidation
    )

# Analyser résultats
df_trades_fixed, df_days_fixed = multi_backtest_analysis(
    trades=bt_fixed['trades'],
    days=bt_fixed['days'],
    leverage=leverage,
    general_info=True,
    trades_info=False,
    days_info=False,
    long_short_info=False,
    entry_exit_info=False,
    exposition_info=False,
    pair_info=False,
    indepedant_trade=False
)

# ============================================================
# 2️⃣ BACKTEST AVEC PARAMS ADAPTATIFS
# ============================================================

print("\n" + "=" * 100)
print("2️⃣  BACKTEST ADAPTATIF (Params ajustés selon régime de marché)")
print("=" * 100)

# Charger données BTC pour détection régime
df_btc = df_list["BTC/USDT:USDT"].copy()
df_btc['ema50'] = df_btc['close'].ewm(span=50, adjust=False).mean()
df_btc['ema200'] = df_btc['close'].ewm(span=200, adjust=False).mean()

# Détecter régimes
regimes = calculate_regime_series(
    df_btc=df_btc[['close', 'ema50', 'ema200']],
    confirm_n=12
)

# Analyser distribution
regime_counts = regimes.value_counts()
print(f"\n📊 Distribution des régimes sur la période:")
for regime, count in regime_counts.items():
    pct = count / len(regimes) * 100
    print(f"   {regime.value.upper():10s}: {count:5d} barres ({pct:5.1f}%)")

# Détecter régime dominant
dominant_regime = regimes.mode()[0]
regime_params = DEFAULT_PARAMS[dominant_regime]

print(f"\n🎯 Régime dominant: {dominant_regime.value.upper()}")
print(f"   Envelope std base: {regime_params.envelope_std:.3f}")
print(f"   TP/SL: {regime_params.tp_mult:.1f}x / {regime_params.sl_mult:.1f}x")

# Adapter les enveloppes
base_std = 0.10  # Référence (recovery)
envelope_multiplier = regime_params.envelope_std / base_std

print(f"\n⚙️  Multiplier envelope: {envelope_multiplier:.2f}x ({dominant_regime.value.upper()})")

params_adaptive = {}
for pair, p in params.items():
    params_adaptive[pair] = p.copy()

    # Adapter enveloppes
    original_envelopes = params_live[pair]['envelopes']
    adapted_envelopes = [env * envelope_multiplier for env in original_envelopes]
    params_adaptive[pair]['envelopes'] = adapted_envelopes

# Adapter le mode de trading
mode = get_mode_for_regime(dominant_regime)
if mode == Mode.LONG_ONLY:
    type_adaptive = ["long", ""]
    print(f"   Mode: LONG_ONLY (shorts désactivés)")
elif mode == Mode.LONG_SHORT:
    type_adaptive = ["long", "short"]
    print(f"   Mode: LONG_SHORT (longs + shorts)")
else:
    type_adaptive = ["", "short"]
    print(f"   Mode: SHORT_ONLY")

# Lancer backtest avec params adaptatifs
strat_adaptive = EnvelopeMulti(
    df_list=df_list,
    oldest_pair=oldest_pair,
    type=type_adaptive,
    params=params_adaptive
)

strat_adaptive.populate_indicators()
strat_adaptive.populate_buy_sell()

if ENGINE_VERSION == "v2":
    bt_adaptive = strat_adaptive.run_backtest(
        initial_wallet=initial_wallet,
        leverage=leverage,
        maker_fee=maker_fee,
        taker_fee=taker_fee,
        stop_loss=stop_loss,
        reinvest=reinvest,
        liquidation=liquidation,
        gross_cap=gross_cap,
        per_side_cap=per_side_cap,
        per_pair_cap=per_pair_cap,
        margin_cap=margin_cap,
        use_kill_switch=use_kill_switch,
        auto_adjust_size=auto_adjust_size,
        extreme_leverage_threshold=extreme_leverage_threshold,
        risk_mode=risk_mode,
        max_expo_cap=max_expo_cap
    )
else:
    bt_adaptive = strat_adaptive.run_backtest(
        initial_wallet=initial_wallet,
        leverage=leverage,
        maker_fee=maker_fee,
        taker_fee=taker_fee,
        stop_loss=stop_loss,
        reinvest=reinvest,
        liquidation=liquidation
    )

# Analyser résultats
df_trades_adaptive, df_days_adaptive = multi_backtest_analysis(
    trades=bt_adaptive['trades'],
    days=bt_adaptive['days'],
    leverage=leverage,
    general_info=True,
    trades_info=False,
    days_info=False,
    long_short_info=False,
    entry_exit_info=False,
    exposition_info=False,
    pair_info=False,
    indepedant_trade=False
)

# ============================================================
# 3️⃣ TABLEAU COMPARATIF
# ============================================================

print("\n" + "=" * 100)
print("3️⃣  TABLEAU COMPARATIF DES RÉSULTATS")
print("=" * 100)

comparison = pd.DataFrame({
    'Métrique': [
        'Wallet final ($)',
        'Performance (%)',
        'Sharpe Ratio',
        'Sortino Ratio',
        'Calmar Ratio',
        'Nombre de trades',
        'Win Rate (%)',
        'Profit moyen (%)',
        'Max Drawdown (%)',
        'Total frais ($)',
        'Performance vs B&H (%)',
    ],
    'PARAMS FIXES': [
        f"{bt_fixed['wallet']:.2f}",
        f"{((bt_fixed['wallet']/initial_wallet - 1)*100):.2f}",
        f"{bt_fixed['sharpe_ratio']:.2f}",
        f"{bt_fixed.get('sortino_ratio', 0):.2f}",
        f"{bt_fixed.get('calmar_ratio', 0):.2f}",
        f"{len(df_trades_fixed)}",
        f"{(df_trades_fixed['trade_result'] > 0).sum() / len(df_trades_fixed) * 100:.1f}",
        f"{df_trades_fixed['trade_result_pct'].mean() * 100:.2f}",
        f"{df_days_fixed['drawdown'].min() * 100:.2f}",
        f"{bt_fixed.get('total_fee', 0):.2f}",
        f"{bt_fixed.get('vs_hold_pct', 0):.2f}",
    ],
    'PARAMS ADAPTATIFS': [
        f"{bt_adaptive['wallet']:.2f}",
        f"{((bt_adaptive['wallet']/initial_wallet - 1)*100):.2f}",
        f"{bt_adaptive['sharpe_ratio']:.2f}",
        f"{bt_adaptive.get('sortino_ratio', 0):.2f}",
        f"{bt_adaptive.get('calmar_ratio', 0):.2f}",
        f"{len(df_trades_adaptive)}",
        f"{(df_trades_adaptive['trade_result'] > 0).sum() / len(df_trades_adaptive) * 100:.1f}",
        f"{df_trades_adaptive['trade_result_pct'].mean() * 100:.2f}",
        f"{df_days_adaptive['drawdown'].min() * 100:.2f}",
        f"{bt_adaptive.get('total_fee', 0):.2f}",
        f"{bt_adaptive.get('vs_hold_pct', 0):.2f}",
    ]
})

# Calculer différences
comparison['DIFFÉRENCE'] = ''
for idx, row in comparison.iterrows():
    if idx > 0:  # Skip header row
        try:
            fixed_val = float(row['PARAMS FIXES'].replace('%', '').replace('$', ''))
            adaptive_val = float(row['PARAMS ADAPTATIFS'].replace('%', '').replace('$', ''))
            diff = adaptive_val - fixed_val
            diff_pct = (diff / abs(fixed_val)) * 100 if fixed_val != 0 else 0

            if diff > 0:
                comparison.at[idx, 'DIFFÉRENCE'] = f"+{diff:.2f} ({diff_pct:+.1f}%)"
            elif diff < 0:
                comparison.at[idx, 'DIFFÉRENCE'] = f"{diff:.2f} ({diff_pct:+.1f}%)"
            else:
                comparison.at[idx, 'DIFFÉRENCE'] = "="
        except:
            comparison.at[idx, 'DIFFÉRENCE'] = "N/A"

print("\n" + comparison.to_string(index=False))

# ============================================================
# 4️⃣ ANALYSE & RECOMMANDATIONS
# ============================================================

print("\n" + "=" * 100)
print("4️⃣  ANALYSE & RECOMMANDATIONS")
print("=" * 100)

# Comparer performances
perf_fixed = (bt_fixed['wallet'] / initial_wallet - 1) * 100
perf_adaptive = (bt_adaptive['wallet'] / initial_wallet - 1) * 100
perf_diff = perf_adaptive - perf_fixed

sharpe_diff = bt_adaptive['sharpe_ratio'] - bt_fixed['sharpe_ratio']
dd_fixed = df_days_fixed['drawdown'].min() * 100
dd_adaptive = df_days_adaptive['drawdown'].min() * 100
dd_diff = dd_adaptive - dd_fixed

print(f"\n📊 Performance globale:")
if perf_diff > 5:
    print(f"   ✅ ADAPTATIF MEILLEUR: +{perf_diff:.2f}% de performance supplémentaire")
    print(f"      → Le système adaptatif améliore significativement les résultats")
elif perf_diff > 0:
    print(f"   ✅ ADAPTATIF LÉGÈREMENT MEILLEUR: +{perf_diff:.2f}%")
    print(f"      → Le système adaptatif apporte un gain marginal")
elif perf_diff > -5:
    print(f"   ⚖️  PERFORMANCES SIMILAIRES: {perf_diff:+.2f}%")
    print(f"      → Les deux approches donnent des résultats équivalents")
else:
    print(f"   ❌ PARAMS FIXES MEILLEURS: {perf_diff:+.2f}%")
    print(f"      → Le système adaptatif dégrade les performances")

print(f"\n📈 Ratio de Sharpe:")
if sharpe_diff > 0.5:
    print(f"   ✅ ADAPTATIF MEILLEUR: +{sharpe_diff:.2f} Sharpe")
    print(f"      → Meilleur rapport rendement/risque avec système adaptatif")
elif sharpe_diff > -0.5:
    print(f"   ⚖️  SHARPE SIMILAIRE: {sharpe_diff:+.2f}")
else:
    print(f"   ❌ PARAMS FIXES MEILLEURS: {sharpe_diff:+.2f} Sharpe")

print(f"\n📉 Drawdown:")
if dd_diff < -1:
    print(f"   ✅ ADAPTATIF MEILLEUR: {dd_diff:.2f}% de drawdown réduit")
    print(f"      → Risque mieux maîtrisé avec système adaptatif")
elif dd_diff < 1:
    print(f"   ⚖️  DD SIMILAIRE: {dd_diff:+.2f}%")
else:
    print(f"   ❌ PARAMS FIXES MEILLEURS: {dd_diff:+.2f}% de DD supplémentaire avec adaptatif")

# Recommandation finale
print(f"\n" + "=" * 100)
print("🎯 RECOMMANDATION FINALE")
print("=" * 100)

score = 0
if perf_diff > 5: score += 3
elif perf_diff > 0: score += 1
elif perf_diff < -5: score -= 3

if sharpe_diff > 0.5: score += 2
elif sharpe_diff < -0.5: score -= 2

if dd_diff < -1: score += 2
elif dd_diff > 1: score -= 2

if score >= 4:
    print(f"\n✅ RECOMMANDATION: UTILISER LE SYSTÈME ADAPTATIF")
    print(f"   Score: {score}/7")
    print(f"   Le système de régime adaptatif améliore significativement les performances.")
    print(f"   Avantages détectés:")
    if perf_diff > 0:
        print(f"      • Meilleure performance: +{perf_diff:.2f}%")
    if sharpe_diff > 0:
        print(f"      • Meilleur Sharpe: +{sharpe_diff:.2f}")
    if dd_diff < 0:
        print(f"      • Drawdown réduit: {dd_diff:.2f}%")
elif score >= 0:
    print(f"\n⚖️  RECOMMANDATION: LES DEUX APPROCHES SONT VALABLES")
    print(f"   Score: {score}/7")
    print(f"   Les performances sont similaires. Choisir selon:")
    print(f"      • Complexité: Params fixes = plus simple")
    print(f"      • Adaptabilité: Système adaptatif = meilleur en conditions changeantes")
else:
    print(f"\n❌ RECOMMANDATION: CONSERVER LES PARAMS FIXES")
    print(f"   Score: {score}/7")
    print(f"   Le système adaptatif dégrade les performances sur cette période.")
    print(f"   Raisons possibles:")
    print(f"      • Régime dominant mal détecté")
    print(f"      • Hystérésis trop lente (confirm_n trop élevé)")
    print(f"      • Paramètres DEFAULT_PARAMS non optimaux pour votre stratégie")

print(f"\n" + "=" * 100)
print("Comparaison terminée ! Vous pouvez maintenant choisir la meilleure approche.")
print("=" * 100 + "\n")

# ============================================================
# 5️⃣ STOCKER LES RÉSULTATS POUR ANALYSE ULTÉRIEURE
# ============================================================

# Stocker dans des variables globales pour utilisation dans les cellules suivantes
bt_result = bt_adaptive  # Utiliser adaptatif par défaut (changer si nécessaire)
df_trades = df_trades_adaptive
df_days = df_days_adaptive

# Optionnel: Sauvegarder comparaison en CSV
comparison.to_csv('backtest_comparison_fixed_vs_adaptive.csv', index=False)
print("💾 Comparaison sauvegardée dans: backtest_comparison_fixed_vs_adaptive.csv")
