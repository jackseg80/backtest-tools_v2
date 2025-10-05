# 📋 Instructions d'exécution - optimize_multi_envelope.ipynb

## 🧪 MODE TEST RAPIDE (2-3 minutes)

### Cellules à exécuter dans l'ordre :

| Cell | Description | Temps | Action |
|------|-------------|-------|--------|
| **Cell-2** | Imports | 2s | ✅ Exécuter |
| **Cell-3** | Config (`TEST_MODE = True`) | 1s | ✅ Exécuter |
| **Cell-5** | Grids par profil | 1s | ✅ Exécuter |
| **Cell-6** | Chargement données (4 paires) | 10s | ✅ Exécuter |
| **Cell-17** | Fonctions filtrage | 1s | ✅ Exécuter |
| **Cell-18** | Fonction score composite | 1s | ✅ Exécuter |
| **Cell-19** | 🚀 Walk-Forward par profil | **2-3 min** | ✅ Exécuter |
| **Cell-20** | Agrégation résultats par profil | 2s | ✅ Exécuter |
| **Cell-21** | Gate : Profil vs Global | 2s | ✅ Exécuter |
| Cell-22 à Cell-37 | ❌ OBSOLÈTES (approche globale) | - | ⏭️ **IGNORER** |

### ⚠️ IMPORTANT

**ARRÊTER après Cell-21 !**

Les cellules 22-37 ne sont plus utilisées avec l'optimisation par profil. Elles étaient pour l'ancienne approche globale.

---

## ✅ MODE PRODUCTION (30-60 minutes)

Même ordre, mais avec `TEST_MODE = False` dans Cell-3.

### Cellules à exécuter :

1. **Cell-2** : Imports
2. **Cell-3** : Config (`TEST_MODE = False`) ← **CHANGER ICI**
3. **Cell-5** : Grids par profil (36 configs au lieu de 4)
4. **Cell-6** : Chargement données (8 paires)
5. **Cell-17** : Fonctions filtrage
6. **Cell-18** : Fonction score composite
7. **Cell-19** : Walk-Forward par profil (~30-60 min, 504 backtests)
8. **Cell-20** : Agrégation résultats par profil
9. **Cell-21** : Gate : Profil vs Global

**STOP ICI** (pas besoin Phase B/Hold-out pour l'instant)

---

## 📊 Résultats attendus (MODE TEST)

Après Cell-21, vous devriez voir :

```
🏆 MEILLEURES CONFIGURATIONS PAR PROFIL
================================================================================

MAJOR:
   MA: 7, Env: [0.056, 0.08, 0.12], Size: 0.10, SL: 0.25
   Adaptive: False/True
   Train Sharpe: X.XX, Test Sharpe: X.XX
   Test Score: X.XXX, Consistency: X.XX
   Trades: XXX

MID-CAP:
   MA: 7, Env: [0.07, 0.10, 0.15], Size: 0.10, SL: 0.25
   ...

VOLATILE:
   MA: 7, Env: [0.098, 0.14, 0.21], Size: 0.10, SL: 0.25
   ...

LOW:
   MA: 7, Env: [0.07, 0.10, 0.15], Size: 0.10, SL: 0.25
   ...
```

Puis le **GATE** :

```
📊 GATE : Optimisation Profil vs Optimisation Globale
================================================================================

🔵 OPTIMISATION GLOBALE (Étape 1)
   MA: 5, Env: [0.07, 0.10, 0.15], Size: 0.12
   Test Score: 2.940
   Test Sharpe: 3.13

🟢 OPTIMISATION PAR PROFIL (Étape 2)
   Weighted Avg Score: X.XXX
   Weighted Avg Sharpe: X.XX

================================================================================
Δ Score:  +X.XXX
Δ Sharpe: +X.XX
================================================================================

✅/❌ GATE PASSÉ/ÉCHOUÉ: ...
   → Recommandation: Adopter configs par profil / Garder config globale
```

---

## ❓ FAQ

### Q: Pourquoi Cell-22 à Cell-37 donnent des erreurs ?

**R:** Ces cellules utilisent des variables de l'ancienne approche globale (`df_wf_avg`, `df_portfolio`, `top3`, etc.) qui n'existent plus avec l'optimisation par profil.

**Solution** : Ne pas les exécuter. Elles seront supprimées dans une version future du notebook.

### Q: Comment tester que tout fonctionne ?

**R:** Exécuter Cell-2 à Cell-21 avec `TEST_MODE = True`. Si aucune erreur et que Cell-21 affiche le Gate → ✅ Tout fonctionne.

### Q: Dois-je exécuter Phase B (28 paires) et Hold-out ?

**R:** **Pas maintenant.** Ces phases seront implémentées différemment pour l'optimisation par profil (appliquer les 4 configs sur 28 paires).

### Q: Les résultats du MODE TEST sont-ils utilisables ?

**R:** **Non.** MODE TEST sert uniquement à vérifier que le code fonctionne (2-3 min). Les résultats réels viennent du MODE PRODUCTION (`TEST_MODE = False`).

---

## 🎯 Prochaines étapes après validation

1. ✅ Valider CODE : `TEST_MODE = True` → Cell-2 à Cell-21
2. ✅ Optimisation RÉELLE : `TEST_MODE = False` → Cell-2 à Cell-21
3. ✅ Analyser Gate : Profil > Global ?
4. ✅ Si Gate OK → Appliquer configs par profil dans `multi_envelope.ipynb`
5. ✅ Paper trading puis déploiement live
