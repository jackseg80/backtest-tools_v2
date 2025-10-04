"""
Margin & Liquidation Utilities for Leveraged Trading Backtests
================================================================

Provides functions for:
- Computing liquidation prices
- Updating equity (wallet + unrealized PnL)
- Applying position closes with fees
- Checking exposure caps
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple

# ============================================================================
# MMR (Maintenance Margin Rate) Configuration
# ============================================================================

MMR_TABLE = {
    # Major coins - Lower MMR (better margin)
    "BTC/USDT:USDT": 0.004,   # 0.40%
    "ETH/USDT:USDT": 0.005,   # 0.50%

    # Majors - Mid MMR
    "SOL/USDT:USDT": 0.0075,  # 0.75%
    "ADA/USDT:USDT": 0.0075,
    "AVAX/USDT:USDT": 0.0075,
    "BNB/USDT:USDT": 0.0075,
    "MATIC/USDT:USDT": 0.0075,
    "DOT/USDT:USDT": 0.0075,

    # Default for all other pairs
    "default": 0.010          # 1.00%
}


def get_mmr(pair: str) -> float:
    """
    Get Maintenance Margin Rate for a pair.

    Args:
        pair: Trading pair (e.g., "BTC/USDT:USDT")

    Returns:
        MMR value (e.g., 0.005 for 0.5%)
    """
    return MMR_TABLE.get(pair, MMR_TABLE["default"])


# ============================================================================
# Liquidation Price Calculation
# ============================================================================

def compute_liq_price(
    entry_price: float,
    side: str,
    leverage: float,
    mmr: float
) -> float:
    """
    Calculate liquidation price for a position.

    Formula (approximate, for USDT linear perpetuals):
    - LONG:  liq_price = entry * (1 - (1/leverage) + mmr)
    - SHORT: liq_price = entry * (1 + (1/leverage) - mmr)

    Args:
        entry_price: Entry price of the position
        side: "LONG" or "SHORT"
        leverage: Leverage used (e.g., 10 for 10x)
        mmr: Maintenance margin rate (e.g., 0.005 for 0.5%)

    Returns:
        Liquidation price

    Examples:
        >>> compute_liq_price(50000, "LONG", 100, 0.005)
        49750.0  # ~0.5% below entry

        >>> compute_liq_price(50000, "SHORT", 100, 0.005)
        50250.0  # ~0.5% above entry
    """
    if side == "LONG":
        return entry_price * (1 - (1 / leverage) + mmr)
    elif side == "SHORT":
        return entry_price * (1 + (1 / leverage) - mmr)
    else:
        raise ValueError(f"Invalid side: {side}. Must be 'LONG' or 'SHORT'")


# ============================================================================
# Equity Calculation (Wallet + Unrealized PnL)
# ============================================================================

def update_equity(
    wallet: float,
    positions: Dict,
    last_prices: Dict[str, float]
) -> float:
    """
    Calculate total equity = wallet + unrealized PnL from all open positions.

    Args:
        wallet: Current wallet balance (cash)
        positions: Dict of open positions {pair: {qty, entry_price, side, ...}}
        last_prices: Dict of current prices {pair: price}

    Returns:
        Total equity

    Example:
        >>> positions = {"BTC/USDT:USDT": {"qty": 0.1, "entry_price": 50000, "side": "LONG"}}
        >>> last_prices = {"BTC/USDT:USDT": 51000}
        >>> update_equity(1000, positions, last_prices)
        1100.0  # 1000 wallet + 100 unrealized PnL
    """
    unrealized_pnl = 0.0

    for pair, pos in positions.items():
        if pair not in last_prices:
            continue

        current_price = last_prices[pair]
        qty = pos.get('qty', 0)
        entry_price = pos.get('price', current_price)  # Fallback to current if no entry
        side = pos.get('side', 'LONG')

        if side == "LONG":
            pnl = qty * (current_price - entry_price)
        elif side == "SHORT":
            pnl = qty * (entry_price - current_price)
        else:
            pnl = 0

        unrealized_pnl += pnl

    return wallet + unrealized_pnl


# ============================================================================
# Position Close with Fees
# ============================================================================

def apply_close(
    position: Dict,
    exit_price: float,
    fee_rate: float,
    is_taker: bool = True
) -> Tuple[float, float]:
    """
    Calculate PnL and fees for closing a position.

    Args:
        position: Position dict with {qty, price (entry), side, size (notional)}
        exit_price: Exit price
        fee_rate: Fee rate (e.g., 0.0006 for 0.06%)
        is_taker: True for taker fees, False for maker fees

    Returns:
        (pnl, fee) tuple
        - pnl: Profit/Loss INCLUDING fees (negative means loss)
        - fee: Fee amount (always positive)

    Example:
        >>> pos = {"qty": 0.1, "price": 50000, "side": "LONG", "size": 5000}
        >>> apply_close(pos, 51000, 0.0006, is_taker=True)
        (69.4, 30.6)  # PnL = 100 - 30.6 fees
    """
    qty = position.get('qty', 0)
    entry_price = position.get('price', exit_price)
    side = position.get('side', 'LONG')

    # Calculate raw PnL (without fees)
    if side == "LONG":
        raw_pnl = qty * (exit_price - entry_price)
    elif side == "SHORT":
        raw_pnl = qty * (entry_price - exit_price)
    else:
        raw_pnl = 0

    # Calculate fee (on the exit notional)
    exit_notional = abs(qty * exit_price)
    fee = exit_notional * fee_rate

    # Net PnL = raw PnL - fees
    net_pnl = raw_pnl - fee

    return net_pnl, fee


# ============================================================================
# Exposure Caps Checking
# ============================================================================

def check_exposure_caps(
    new_notional: float,
    new_side: str,
    new_pair: str,
    current_positions: Dict,
    equity: float,
    gross_cap: float = 1.5,
    per_side_cap: float = 1.0,
    per_pair_cap: float = 0.3
) -> Tuple[bool, str]:
    """
    Check if adding a new position would violate exposure caps.

    Args:
        new_notional: Notional size of new position
        new_side: "LONG" or "SHORT"
        new_pair: Trading pair
        current_positions: Dict of current positions
        equity: Current equity
        gross_cap: Gross exposure cap (multiple of equity, e.g., 1.5)
        per_side_cap: Per-side exposure cap (e.g., 1.0 for 100% of equity per side)
        per_pair_cap: Per-pair exposure cap (e.g., 0.3 for 30% of equity per pair)

    Returns:
        (is_allowed, reason) tuple
        - is_allowed: True if position can be opened
        - reason: Explanation if rejected
    """
    # Calculate current exposures
    gross_exposure = 0.0
    long_exposure = 0.0
    short_exposure = 0.0
    pair_exposure = 0.0

    for pair, pos in current_positions.items():
        notional = pos.get('size', 0)  # Notional value
        side = pos.get('side', 'LONG')

        gross_exposure += notional

        if side == "LONG":
            long_exposure += notional
        elif side == "SHORT":
            short_exposure += notional

        if pair == new_pair:
            pair_exposure += notional

    # Add new position
    gross_after = gross_exposure + new_notional
    pair_after = pair_exposure + new_notional

    if new_side == "LONG":
        side_after = long_exposure + new_notional
    else:
        side_after = short_exposure + new_notional

    # Check caps
    if gross_after > gross_cap * equity:
        return False, f"Gross exposure cap exceeded: {gross_after:.0f} > {gross_cap * equity:.0f}"

    if side_after > per_side_cap * equity:
        return False, f"{new_side} exposure cap exceeded: {side_after:.0f} > {per_side_cap * equity:.0f}"

    if pair_after > per_pair_cap * equity:
        return False, f"Per-pair exposure cap exceeded for {new_pair}: {pair_after:.0f} > {per_pair_cap * equity:.0f}"

    return True, "OK"


# ============================================================================
# Kill-Switch Logic
# ============================================================================

class KillSwitch:
    """
    Kill-switch to pause trading after significant drawdown.
    """

    def __init__(
        self,
        day_pnl_threshold: float = -0.08,   # -8%
        hour_pnl_threshold: float = -0.12,  # -12%
        pause_hours: int = 24
    ):
        """
        Initialize kill-switch.

        Args:
            day_pnl_threshold: Daily PnL threshold (e.g., -0.08 for -8%)
            hour_pnl_threshold: Hourly PnL threshold (e.g., -0.12 for -12%)
            pause_hours: Hours to pause trading after trigger
        """
        self.day_threshold = day_pnl_threshold
        self.hour_threshold = hour_pnl_threshold
        self.pause_hours = pause_hours

        self.is_paused = False
        self.pause_until = None

        self.day_start_equity = None
        self.hour_start_equity = None

    def update(
        self,
        current_datetime,
        current_equity: float,
        initial_wallet: float
    ) -> bool:
        """
        Update kill-switch state and check if trading should be paused.

        Args:
            current_datetime: Current datetime
            current_equity: Current equity
            initial_wallet: Initial wallet for reference

        Returns:
            True if trading is paused, False otherwise
        """
        # Check if pause has expired
        if self.is_paused and self.pause_until:
            if current_datetime >= self.pause_until:
                self.is_paused = False
                self.pause_until = None
                print(f"Kill-switch expired at {current_datetime}. Trading resumed.")

        # If already paused, stay paused
        if self.is_paused:
            return True

        # Initialize tracking (first call of the day/hour)
        current_day = current_datetime.date()
        current_hour = current_datetime.hour

        if self.day_start_equity is None or current_datetime.date() != getattr(self, 'last_day', None):
            self.day_start_equity = current_equity
            self.last_day = current_day

        if self.hour_start_equity is None or current_datetime.hour != getattr(self, 'last_hour', None):
            self.hour_start_equity = current_equity
            self.last_hour = current_hour

        # Calculate PnL %
        day_pnl_pct = (current_equity - self.day_start_equity) / self.day_start_equity if self.day_start_equity > 0 else 0
        hour_pnl_pct = (current_equity - self.hour_start_equity) / self.hour_start_equity if self.hour_start_equity > 0 else 0

        # Check thresholds
        if day_pnl_pct <= self.day_threshold:
            self.is_paused = True
            self.pause_until = current_datetime + pd.Timedelta(hours=self.pause_hours)
            print(f"Kill-switch TRIGGERED (day PnL: {day_pnl_pct*100:.2f}%) at {current_datetime}. Paused until {self.pause_until}")
            return True

        if hour_pnl_pct <= self.hour_threshold:
            self.is_paused = True
            self.pause_until = current_datetime + pd.Timedelta(hours=self.pause_hours)
            print(f"Kill-switch TRIGGERED (1h PnL: {hour_pnl_pct*100:.2f}%) at {current_datetime}. Paused until {self.pause_until}")
            return True

        return False

    def reset(self):
        """Reset kill-switch state."""
        self.is_paused = False
        self.pause_until = None
        self.day_start_equity = None
        self.hour_start_equity = None
