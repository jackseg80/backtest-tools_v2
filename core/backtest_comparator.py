"""
Comparateur de backtests multi-stratégies.

Permet de comparer N backtests avec différentes configurations de paramètres
et génère un rapport comparatif automatique.

Usage:
    comparator = BacktestComparator()

    # Ajouter des backtests à comparer
    comparator.add_backtest("Baseline", bt_trades_1, bt_days_1)
    comparator.add_backtest("Regime Adaptive", bt_trades_2, bt_days_2)
    comparator.add_backtest("Optimized", bt_trades_3, bt_days_3)

    # Générer le rapport comparatif
    results_df = comparator.compare()
    print(results_df)

    # Sauvegarder
    comparator.save_comparison("backtest_comparison.csv")
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from utilities.bt_analysis import get_metrics


@dataclass
class BacktestResult:
    """Résultat d'un backtest avec métadonnées."""
    name: str
    df_trades: pd.DataFrame
    df_days: pd.DataFrame
    metadata: Optional[Dict[str, Any]] = None


class BacktestComparator:
    """
    Comparateur de backtests permettant d'évaluer plusieurs stratégies.

    Calcule automatiquement les métriques clés et génère des rapports comparatifs.
    """

    def __init__(self, initial_wallet: float = 1000):
        """
        Args:
            initial_wallet: Capital initial (pour calcul de performance)
        """
        self.initial_wallet = initial_wallet
        self.backtests: List[BacktestResult] = []
        self.comparison_df: Optional[pd.DataFrame] = None

    def add_backtest(
        self,
        name: str,
        df_trades: pd.DataFrame,
        df_days: pd.DataFrame,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Ajoute un backtest à la comparaison.

        Args:
            name: Nom descriptif de la stratégie
            df_trades: DataFrame des trades
            df_days: DataFrame de l'évolution quotidienne
            metadata: Métadonnées optionnelles (params, description, etc.)
        """
        result = BacktestResult(
            name=name,
            df_trades=df_trades,
            df_days=df_days,
            metadata=metadata or {}
        )
        self.backtests.append(result)

    def _calculate_metrics(self, bt: BacktestResult) -> Dict[str, float]:
        """Calcule toutes les métriques pour un backtest."""
        df_days = bt.df_days
        df_trades = bt.df_trades.copy()

        # Wallet final
        final_wallet = df_days['wallet'].iloc[-1] if len(df_days) > 0 else self.initial_wallet

        # Performance totale
        total_perf = ((final_wallet / self.initial_wallet) - 1) * 100

        # Calculer trade_result si absent (compatibilité avec EnvelopeMulti_v2)
        if len(df_trades) > 0 and 'trade_result' not in df_trades.columns:
            if all(col in df_trades.columns for col in ['close_trade_size', 'open_trade_size', 'open_fee', 'close_fee']):
                df_trades['trade_result'] = (
                    df_trades["close_trade_size"] -
                    df_trades["open_trade_size"] -
                    df_trades["open_fee"] -
                    df_trades["close_fee"]
                )
                df_trades['trade_result_pct'] = df_trades['trade_result'] / df_trades["open_trade_size"]
            else:
                # Fallback: pas de données de trades détaillées
                df_trades['trade_result'] = 0.0
                df_trades['trade_result_pct'] = 0.0

        # Win rate
        if len(df_trades) > 0:
            winning_trades = len(df_trades[df_trades['trade_result'] > 0])
            win_rate = (winning_trades / len(df_trades)) * 100
        else:
            win_rate = 0.0

        # Sharpe ratio (approximation basée sur daily returns)
        if len(df_days) > 1:
            df_days['daily_return'] = df_days['wallet'].pct_change()
            daily_returns = df_days['daily_return'].dropna()
            if len(daily_returns) > 0 and daily_returns.std() > 0:
                sharpe = (daily_returns.mean() / daily_returns.std()) * np.sqrt(365)
            else:
                sharpe = 0.0
        else:
            sharpe = 0.0

        # Max Drawdown
        if len(df_days) > 0:
            df_days['cummax'] = df_days['wallet'].cummax()
            df_days['drawdown'] = (df_days['wallet'] - df_days['cummax']) / df_days['cummax'] * 100
            max_dd = df_days['drawdown'].min()
        else:
            max_dd = 0.0

        # Exposition moyenne
        if len(df_days) > 0:
            avg_long_expo = df_days['long_exposition'].mean()
            avg_short_expo = df_days['short_exposition'].mean()
            avg_total_expo = avg_long_expo + avg_short_expo
        else:
            avg_long_expo = 0.0
            avg_short_expo = 0.0
            avg_total_expo = 0.0

        # Nombre de trades
        n_trades = len(df_trades)

        # Fees totaux (si présent dans df_trades)
        if 'fee' in df_trades.columns:
            total_fees = df_trades['fee'].sum()
        elif 'open_fee' in df_trades.columns and 'close_fee' in df_trades.columns:
            total_fees = df_trades['open_fee'].sum() + df_trades['close_fee'].sum()
        else:
            total_fees = 0.0

        # PnL moyen par trade (en %)
        if n_trades > 0 and 'trade_result_pct' in df_trades.columns:
            avg_pnl = df_trades['trade_result_pct'].mean() * 100
            max_win = df_trades['trade_result_pct'].max() * 100
            max_loss = df_trades['trade_result_pct'].min() * 100
        else:
            avg_pnl = 0.0
            max_win = 0.0
            max_loss = 0.0

        # Durée moyenne de holding (si dates présentes)
        if 'open_date' in df_trades.columns and 'close_date' in df_trades.columns:
            df_trades['duration'] = (
                pd.to_datetime(df_trades['close_date']) -
                pd.to_datetime(df_trades['open_date'])
            ).dt.total_seconds() / 3600  # en heures
            avg_duration_hours = df_trades['duration'].mean()
        else:
            avg_duration_hours = 0.0

        return {
            'Final Wallet': final_wallet,
            'Total Perf (%)': total_perf,
            'Sharpe Ratio': sharpe,
            'Max DD (%)': max_dd,
            'Win Rate (%)': win_rate,
            'N Trades': n_trades,
            'Avg PnL (%)': avg_pnl,
            'Max Win (%)': max_win,
            'Max Loss (%)': max_loss,
            'Total Fees': total_fees,
            'Avg Exposition': avg_total_expo,
            'Avg Long Expo': avg_long_expo,
            'Avg Short Expo': avg_short_expo,
            'Avg Duration (h)': avg_duration_hours
        }

    def compare(self) -> pd.DataFrame:
        """
        Génère un tableau comparatif de tous les backtests.

        Returns:
            DataFrame avec une ligne par backtest et colonnes = métriques
        """
        if len(self.backtests) == 0:
            raise ValueError("Aucun backtest ajouté. Utilisez add_backtest() d'abord.")

        comparison_data = []
        for bt in self.backtests:
            metrics = self._calculate_metrics(bt)
            metrics['Strategy'] = bt.name
            comparison_data.append(metrics)

        # Créer le DataFrame comparatif
        self.comparison_df = pd.DataFrame(comparison_data)

        # Réorganiser : Strategy en premier
        cols = ['Strategy'] + [c for c in self.comparison_df.columns if c != 'Strategy']
        self.comparison_df = self.comparison_df[cols]

        return self.comparison_df

    def rank(self, metric: str = 'Total Perf (%)') -> pd.DataFrame:
        """
        Trie les backtests selon une métrique.

        Args:
            metric: Métrique de classement (ex: 'Total Perf (%)', 'Sharpe Ratio')

        Returns:
            DataFrame trié par métrique décroissante
        """
        if self.comparison_df is None:
            self.compare()

        return self.comparison_df.sort_values(by=metric, ascending=False).reset_index(drop=True)

    def score(self, weights: Optional[Dict[str, float]] = None) -> pd.DataFrame:
        """
        Calcule un score composite basé sur plusieurs métriques pondérées.

        Args:
            weights: Pondérations {metric: weight}. Défaut:
                - Total Perf: 30%
                - Sharpe Ratio: 25%
                - Max DD: 20% (négatif = bon)
                - Win Rate: 15%
                - Avg PnL: 10%

        Returns:
            DataFrame avec colonne 'Score' ajoutée
        """
        if self.comparison_df is None:
            self.compare()

        # Pondérations par défaut
        if weights is None:
            weights = {
                'Total Perf (%)': 0.30,
                'Sharpe Ratio': 0.25,
                'Max DD (%)': 0.20,  # Négatif = bon
                'Win Rate (%)': 0.15,
                'Avg PnL (%)': 0.10
            }

        df = self.comparison_df.copy()

        # Normaliser chaque métrique entre 0 et 1
        normalized_scores = []
        for metric, weight in weights.items():
            if metric not in df.columns:
                continue

            values = df[metric]

            # Pour Max DD, inverser car négatif = meilleur
            if 'DD' in metric or 'Loss' in metric:
                # Invert: moins négatif = mieux
                normalized = 1 - ((values - values.min()) / (values.max() - values.min() + 1e-9))
            else:
                # Plus élevé = mieux
                normalized = (values - values.min()) / (values.max() - values.min() + 1e-9)

            normalized_scores.append(normalized * weight)

        # Score composite
        df['Score'] = sum(normalized_scores)
        df = df.sort_values(by='Score', ascending=False).reset_index(drop=True)

        return df

    def recommend(self) -> str:
        """
        Retourne une recommandation automatique basée sur le score.

        Returns:
            Nom de la meilleure stratégie
        """
        scored_df = self.score()
        best = scored_df.iloc[0]
        return best['Strategy']

    def save_comparison(self, path: str) -> None:
        """
        Sauvegarde le tableau comparatif en CSV.

        Args:
            path: Chemin du fichier CSV de sortie
        """
        if self.comparison_df is None:
            self.compare()

        self.comparison_df.to_csv(path, index=False)
        print(f"✅ Comparaison sauvegardée: {path}")

    def get_metadata(self, strategy_name: str) -> Optional[Dict[str, Any]]:
        """Récupère les métadonnées d'une stratégie."""
        for bt in self.backtests:
            if bt.name == strategy_name:
                return bt.metadata
        return None

    def print_summary(self) -> None:
        """Affiche un résumé textuel des résultats."""
        if self.comparison_df is None:
            self.compare()

        print("\n" + "=" * 80)
        print("🔍 COMPARAISON DES BACKTESTS")
        print("=" * 80)

        # Afficher le tableau
        print(self.comparison_df.to_string(index=False))

        # Afficher la recommandation
        print("\n" + "-" * 80)
        recommendation = self.recommend()
        print(f"✅ RECOMMANDATION: {recommendation}")
        print("-" * 80 + "\n")
