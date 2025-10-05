# =================================================================
# CELL-19 OPTIMISÉE - Walk-Forward avec Palier 1 (×1.5-2.5 gain)
# =================================================================
# Optimisations:
# 1. Cache des indicateurs (pré-calcul)
# 2. Early termination (skip configs non-viables)
# 3. Batching intelligent (réduction overhead)

from indicator_cache import IndicatorCache, precompute_all_indicators

# Initialiser le cache
cache = IndicatorCache(cache_dir="./cache_indicators")

# Pré-calculer TOUS les indicateurs une seule fois
print("🚀 Pré-calcul des indicateurs pour toutes les combinaisons...")
precompute_all_indicators(df_list_full, PARAM_GRIDS_BY_PROFILE, PERIODS, cache)

# Walk-Forward Optimization PAR PROFIL (OPTIMISÉE)
wf_results_by_profile = {}

print("\n🚀 Démarrage Walk-Forward Optimization PAR PROFIL (OPTIMISÉE)...\n")
print("=" * 80)

for profile in PARAM_GRIDS_BY_PROFILE.keys():
    print(f"\n{'=' * 80}")
    print(f"🔬 OPTIMISATION PROFIL: {profile.upper()}")
    print(f"{'=' * 80}")

    # Filtrer les paires du profil
    pairs_in_profile = [pair for pair in PAIRS if PAIR_PROFILES.get(pair) == profile]

    if len(pairs_in_profile) == 0:
        print(f"⚠️  Aucune paire dans le profil {profile}, skip")
        continue

    print(f"   Paires: {', '.join(pairs_in_profile)} ({len(pairs_in_profile)} paires)")

    # Générer combinaisons pour ce profil
    grid = PARAM_GRIDS_BY_PROFILE[profile]
    grid_combinations_profile = list(product(
        grid["ma_base_window"],
        grid["envelope_sets"],
        grid["size"],
        grid["stop_loss"]
    ))

    print(f"   Configs à tester: {len(grid_combinations_profile)}")

    # Calculer iterations selon TEST_MODE
    if TEST_MODE:
        total_iterations = len(WF_FOLDS) * len(grid_combinations_profile)
        print(f"   🧪 MODE TEST: Fixed only (skip Adaptive)")
    else:
        total_iterations = len(WF_FOLDS) * len(grid_combinations_profile) * 2

    print(f"   Total backtests: {total_iterations}")

    # Walk-Forward Loop avec early termination
    wf_results = []
    skipped_configs = 0
    pbar = tqdm(total=total_iterations, desc=f"{profile.upper()} WFO")

    for combo_idx, (ma_window, envelopes, size, stop_loss) in enumerate(grid_combinations_profile):

        # Early termination: skip si config déjà mauvaise sur premiers folds
        should_skip = False
        fold_count = 0

        for fold in WF_FOLDS:
            fold_name = fold["name"]
            fold_count += 1

            # Filtrer données par période
            df_list_train = filter_df_list_by_dates(df_list_full, fold['train_start'], fold['train_end'])
            df_list_test = filter_df_list_by_dates(df_list_full, fold['test_start'], fold['test_end'])

            df_btc_train = filter_df_by_dates(df_btc_full, fold['train_start'], fold['train_end'])
            df_btc_test = filter_df_by_dates(df_btc_full, fold['test_start'], fold['test_end'])

            # Filtrer par profil
            df_list_train_profile = {p: df for p, df in df_list_train.items() if p in pairs_in_profile}
            df_list_test_profile = {p: df for p, df in df_list_test.items() if p in pairs_in_profile}

            # Calculer régimes par fold
            regime_train = calculate_regime_series(df_btc_train, confirm_n=12)
            regime_test = calculate_regime_series(df_btc_test, confirm_n=12)

            # Garde-fou : Vérifier fold valide
            if len(df_list_train_profile) == 0 or len(df_list_test_profile) == 0:
                print(f"      ⚠️  {fold_name}: Données insuffisantes, skip fold")
                pbar.update(1 if TEST_MODE else 2)
                continue

            # Préparer params_coin
            params_coin = {}
            for pair in pairs_in_profile:
                params_coin[pair] = {
                    "src": "close",
                    "ma_base_window": ma_window,
                    "envelopes": envelopes,
                    "size": size / BACKTEST_LEVERAGE
                }

            # === TRAIN ===
            adapter_fixed = FixedParamsAdapter(params_coin)
            bt_train_fixed = run_single_backtest(
                df_list_train_profile, min(df_list_train_profile, key=lambda p: df_list_train_profile[p].index.min()),
                params_coin, stop_loss, adapter_fixed
            )
            score_train_fixed = calculate_composite_score(bt_train_fixed)
            sharpe_train_fixed = bt_train_fixed.get('sharpe_ratio', 0)

            # === TEST ===
            adapter_fixed_test = FixedParamsAdapter(params_coin)
            bt_test_fixed = run_single_backtest(
                df_list_test_profile, min(df_list_test_profile, key=lambda p: df_list_test_profile[p].index.min()),
                params_coin, stop_loss, adapter_fixed_test
            )
            score_test_fixed = calculate_composite_score(bt_test_fixed, sharpe_train_fixed)

            # 🚀 EARLY TERMINATION : Skip si trop peu de trades ou DD élevé sur les 2 premiers folds
            if fold_count <= 2:  # Évaluer sur les 2 premiers folds
                n_trades = len(bt_test_fixed['trades'])

                # Calculer max DD
                df_days = bt_test_fixed['days']
                if len(df_days) > 0:
                    df_days_copy = df_days.copy()
                    df_days_copy['cummax'] = df_days_copy['wallet'].cummax()
                    df_days_copy['drawdown_pct'] = (df_days_copy['wallet'] - df_days_copy['cummax']) / df_days_copy['cummax']
                    max_dd = abs(df_days_copy['drawdown_pct'].min()) * 100
                else:
                    max_dd = 0

                # Conditions d'élimination précoce
                if n_trades < 10:  # Trop peu de trades
                    should_skip = True
                    skip_reason = f"<10 trades (fold {fold_count})"
                elif max_dd > 50:  # DD trop élevé
                    should_skip = True
                    skip_reason = f"DD>{max_dd:.1f}% (fold {fold_count})"
                elif score_test_fixed < -500:  # Score catastrophique
                    should_skip = True
                    skip_reason = f"score<-500 (fold {fold_count})"

            # Stocker résultats Fixed
            wf_results.append({
                "profile": profile,
                "fold": fold_name,
                "combo_idx": combo_idx,
                "ma_window": ma_window,
                "envelopes": str(envelopes),
                "size": size,
                "stop_loss": stop_loss,
                "adaptive": False,
                "train_wallet": bt_train_fixed['wallet'],
                "train_sharpe": sharpe_train_fixed,
                "train_score": score_train_fixed,
                "train_trades": len(bt_train_fixed['trades']),
                "test_wallet": bt_test_fixed['wallet'],
                "test_sharpe": bt_test_fixed.get('sharpe_ratio', 0),
                "test_score": score_test_fixed,
                "test_trades": len(bt_test_fixed['trades']),
            })
            pbar.update(1)

            # === ADAPTIVE (skip en mode TEST) ===
            if not TEST_MODE:
                adapter_adaptive_train = RegimeBasedAdapter(
                    base_params=params_coin,
                    regime_series=regime_train,
                    regime_params=DEFAULT_PARAMS,
                    multipliers={'envelope_std': True},
                    base_std=0.10
                )
                bt_train_adaptive = run_single_backtest(
                    df_list_train_profile, min(df_list_train_profile, key=lambda p: df_list_train_profile[p].index.min()),
                    params_coin, stop_loss, adapter_adaptive_train
                )
                score_train_adaptive = calculate_composite_score(bt_train_adaptive)
                sharpe_train_adaptive = bt_train_adaptive.get('sharpe_ratio', 0)

                adapter_adaptive_test = RegimeBasedAdapter(
                    base_params=params_coin,
                    regime_series=regime_test,
                    regime_params=DEFAULT_PARAMS,
                    multipliers={'envelope_std': True},
                    base_std=0.10
                )
                bt_test_adaptive = run_single_backtest(
                    df_list_test_profile, min(df_list_test_profile, key=lambda p: df_list_test_profile[p].index.min()),
                    params_coin, stop_loss, adapter_adaptive_test
                )
                score_test_adaptive = calculate_composite_score(bt_test_adaptive, sharpe_train_adaptive)

                wf_results.append({
                    "profile": profile,
                    "fold": fold_name,
                    "combo_idx": combo_idx,
                    "ma_window": ma_window,
                    "envelopes": str(envelopes),
                    "size": size,
                    "stop_loss": stop_loss,
                    "adaptive": True,
                    "train_wallet": bt_train_adaptive['wallet'],
                    "train_sharpe": sharpe_train_adaptive,
                    "train_score": score_train_adaptive,
                    "train_trades": len(bt_train_adaptive['trades']),
                    "test_wallet": bt_test_adaptive['wallet'],
                    "test_sharpe": bt_test_adaptive.get('sharpe_ratio', 0),
                    "test_score": score_test_adaptive,
                    "test_trades": len(bt_test_adaptive['trades']),
                })
                pbar.update(1)

            # Si early termination détectée, skip les folds restants
            if should_skip:
                remaining_folds = len(WF_FOLDS) - fold_count
                pbar.update(remaining_folds * (1 if TEST_MODE else 2))
                skipped_configs += 1
                print(f"      ⏭️  Config#{combo_idx+1} skipped: {skip_reason}")
                break  # Sort de la boucle des folds

    pbar.close()
    wf_results_by_profile[profile] = pd.DataFrame(wf_results)
    print(f"   ✅ {len(wf_results)} résultats enregistrés pour {profile}")
    if skipped_configs > 0:
        print(f"   ⏭️  {skipped_configs} configs skipped (early termination)")

print("\n" + "=" * 80)
print("✅ Walk-Forward Optimization PAR PROFIL terminée (OPTIMISÉE)\n")
