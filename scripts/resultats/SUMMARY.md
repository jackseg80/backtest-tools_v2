# Résultats Comparatifs - Test Cycles Multi-Config

## Bull 2020-2021 (20 paires)

| Configuration | Performance | Sharpe | Trades | Win Rate | Max DD | Liquidations |
|---------------|-------------|--------|--------|----------|--------|--------------|
| **LONG ONLY** | +351.57% | 6.72 | 2,316 | 74.53% | -5.99% | 425 (18.4%) |
| **SHORT ONLY** | +55.21% | 3.70 | 2,218 | 64.70% | -3.60% | 432 (19.5%) |
| **LONG + SHORT** | +577.08% | 7.01 | 4,494 | 69.69% | -6.34% | 854 (19.0%) |

### Analyse Bull 2020-2021
- ✅ **LONG domine** : +351% vs +55% SHORT (normal en bull market)
- ✅ **LONG + SHORT = meilleure perf** : +577% grâce au cumul
- ⚠️ **SHORT sous-performe** : Win rate 64.7% vs 74.5% pour LONG
- 📊 **Conclusion** : En bull market, privilégier LONG ONLY

---

## Bear 2022 (25 paires)

| Configuration | Performance | Sharpe | Trades | Win Rate | Max DD | Note |
|---------------|-------------|--------|--------|----------|--------|------|
| **LONG ONLY** | +14.51% | 3.72 | 221 | 71.49% | -1.34% | ✅ Résiste bien |
| **SHORT ONLY** | +X% | X | X | X% | X% | 🔍 À analyser |
| **LONG + SHORT** | +X% | X | X | X% | X% | 🔍 À analyser |

---

## Recovery 2023 (28 paires)

| Configuration | Performance | Sharpe | Trades | Win Rate | Max DD |
|---------------|-------------|--------|--------|----------|--------|
| **LONG ONLY** | +10.83% | 3.15 | 94 | 91.49% | -0.83% |
| **SHORT ONLY** | +X% | X | X | X% | X% |
| **LONG + SHORT** | +X% | X | X | X% | X% |

---

## Bull 2024 (28 paires)

| Configuration | Performance | Sharpe | Trades | Win Rate | Max DD |
|---------------|-------------|--------|--------|----------|--------|
| **LONG ONLY** | +13.95% | 2.86 | 142 | 78.87% | -2.14% |
| **SHORT ONLY** | +X% | X | X | X% | X% |
| **LONG + SHORT** | +X% | X | X | X% | X% |

---

## Recommandations par Type de Marché

### 🟢 Bull Market (2020-2021, 2024)
- **Recommandation** : LONG ONLY ou LONG + SHORT
- **Éviter** : SHORT ONLY (sous-performance importante)

### 🔴 Bear Market (2022)
- **À analyser** : SHORT ONLY devrait mieux performer
- **Hypothèse** : SHORT profitable en vrai bear market

### 🟡 Recovery/Consolidation (2023)
- **Recommandation** : LONG ONLY (win rate 91%!)
- **Observation** : Peu de trades mais très efficaces

---

**Fichier complet** : `scripts/resultats/backtest_cycles_detailed.txt`
