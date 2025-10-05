"""
Système d'adaptation dynamique des paramètres de stratégie.

Permet de modifier les paramètres pendant l'exécution du backtest selon différentes stratégies :
- Adaptation basée sur le régime de marché détecté
- Adaptation fixe (baseline)
- Adaptation custom selon logique utilisateur

Usage:
    # Adapter selon régime détecté
    adapter = RegimeBasedAdapter(base_params, regime_series, multipliers={'envelope_std': True})

    # Pas d'adaptation (baseline)
    adapter = FixedParamsAdapter(base_params)

    # Dans le backtest
    for date in dates:
        params = adapter.get_params_at_date(date, pair)
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import pandas as pd
from core import Regime, DEFAULT_PARAMS


class ParamsAdapter(ABC):
    """Classe abstraite pour adaptateurs de paramètres."""

    def __init__(self, base_params: Dict[str, Dict[str, Any]]):
        """
        Args:
            base_params: Dictionnaire {pair: {param: value}} des paramètres de référence
        """
        self.base_params = base_params

    @abstractmethod
    def get_params_at_date(self, date: pd.Timestamp, pair: str) -> Dict[str, Any]:
        """
        Retourne les paramètres adaptés pour une date et paire donnée.

        Args:
            date: Date du backtest
            pair: Paire tradée (ex: "BTC/USDT:USDT")

        Returns:
            Dictionnaire des paramètres {param: value}
        """
        pass

    @abstractmethod
    def get_description(self) -> str:
        """Retourne une description de la stratégie d'adaptation."""
        pass


class FixedParamsAdapter(ParamsAdapter):
    """Adaptateur qui retourne toujours les mêmes paramètres (baseline)."""

    def get_params_at_date(self, date: pd.Timestamp, pair: str) -> Dict[str, Any]:
        return self.base_params[pair].copy()

    def get_description(self) -> str:
        return "Fixed parameters (baseline)"


class RegimeBasedAdapter(ParamsAdapter):
    """
    Adaptateur qui modifie les paramètres selon le régime de marché détecté.

    Applique des multiplicateurs basés sur les paramètres du régime actif.
    """

    def __init__(
        self,
        base_params: Dict[str, Dict[str, Any]],
        regime_series: pd.Series,
        regime_params: Optional[Dict[Regime, Any]] = None,
        multipliers: Optional[Dict[str, bool]] = None,
        base_std: float = 0.10
    ):
        """
        Args:
            base_params: Paramètres de référence {pair: {param: value}}
            regime_series: Série temporelle des régimes détectés
            regime_params: Paramètres par régime (DEFAULT_PARAMS si None)
            multipliers: Quels paramètres adapter {'envelope_std': True, ...}
            base_std: Valeur de référence pour envelope_std (normalement RECOVERY)
        """
        super().__init__(base_params)
        self.regime_series = regime_series
        self.regime_params = regime_params or DEFAULT_PARAMS
        self.base_std = base_std

        # Par défaut, adapter seulement envelope_std
        self.multipliers = multipliers or {
            'envelope_std': True,
            'tp_mult': False,
            'sl_mult': False,
            'trailing': False
        }

    def get_params_at_date(self, date: pd.Timestamp, pair: str) -> Dict[str, Any]:
        """Adapte les paramètres selon le régime actif à cette date."""
        # Copier les paramètres de base
        params = self.base_params[pair].copy()

        # Détecter le régime actif
        try:
            regime = self.regime_series.asof(date)
            if pd.isna(regime):
                # Pas de régime disponible, garder params de base
                return params
        except (KeyError, IndexError):
            # Date hors du range de la série
            return params

        # Récupérer les paramètres du régime
        regime_param = self.regime_params.get(regime)
        if regime_param is None:
            return params

        # Appliquer les multiplicateurs
        if self.multipliers.get('envelope_std', False) and 'envelopes' in params:
            # Adapter les envelopes selon le régime
            multiplier = regime_param.envelope_std / self.base_std
            params['envelopes'] = [env * multiplier for env in params['envelopes']]

        # TODO: Ajouter adaptation d'autres paramètres si nécessaire
        # if self.multipliers.get('tp_mult', False):
        #     params['tp'] = base_tp * regime_param.tp_mult

        return params

    def get_description(self) -> str:
        adapted = [k for k, v in self.multipliers.items() if v]
        return f"Regime-based adaptation ({', '.join(adapted)})"

    def get_regime_at_date(self, date: pd.Timestamp) -> Optional[Regime]:
        """Utilitaire pour obtenir le régime à une date donnée."""
        try:
            regime = self.regime_series.asof(date)
            return regime if not pd.isna(regime) else None
        except (KeyError, IndexError):
            return None


class CustomAdapter(ParamsAdapter):
    """
    Adaptateur custom avec fonction utilisateur.

    Permet de définir une logique d'adaptation personnalisée.
    """

    def __init__(
        self,
        base_params: Dict[str, Dict[str, Any]],
        adapter_func: callable,
        description: str = "Custom adaptation"
    ):
        """
        Args:
            base_params: Paramètres de référence
            adapter_func: Fonction (date, pair, base_params) -> adapted_params
            description: Description de la stratégie
        """
        super().__init__(base_params)
        self.adapter_func = adapter_func
        self.description = description

    def get_params_at_date(self, date: pd.Timestamp, pair: str) -> Dict[str, Any]:
        return self.adapter_func(date, pair, self.base_params[pair].copy())

    def get_description(self) -> str:
        return self.description
