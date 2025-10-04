import sys
sys.path.append('../..')
import ta
import numpy as np
import pandas as pd
from utilities.bt_analysis import get_metrics
from utilities.margin import (
    compute_liq_price,
    update_equity,
    apply_close,
    check_exposure_caps,
    get_mmr,
    KillSwitch
)

def calculate_notional_per_level(equity, base_size, leverage, n_levels, risk_mode, max_expo_cap=2.0):
    """
    Calculate notional per envelope level according to risk_mode.

    Parameters:
    -----------
    equity : float
        Current account equity
    base_size : float
        Base size percentage (e.g., 0.06 = 6%)
    leverage : int
        Trading leverage
    n_levels : int
        Number of envelope levels (to split notional across)
    risk_mode : str
        "neutral" - Notional constant (base_size * equity)
        "scaling" - Notional scales with leverage (base_size * equity * leverage)
        "hybrid"  - Notional scales with leverage but capped at max_expo_cap * equity
    max_expo_cap : float
        (HYBRID only) Maximum total notional as multiple of equity

    Returns:
    --------
    float : Notional per level
    """
    if risk_mode == "neutral":
        # Notional constant regardless of leverage
        total_target_notional = equity * base_size
    elif risk_mode == "scaling":
        # Notional grows with leverage
        total_target_notional = equity * base_size * leverage
    elif risk_mode == "hybrid":
        # Notional grows with leverage but capped
        total_target_notional = min(equity * base_size * leverage, equity * max_expo_cap)
    else:
        raise ValueError(f"Unknown risk_mode: {risk_mode}")

    # Split across envelope levels
    return total_target_notional / n_levels

"""
EnvelopeMulti_v2 Strategy - DCA Envelope Mean Reversion with Proper Margin & Liquidation

VERSION 2 - Key Improvements:
==================================
1. Margin Management:
   - init_margin = notional / leverage (reserved at position opening)
   - used_margin = sum of all init_margins
   - equity = wallet + unrealized PnL (recalculated each bar)

2. Liquidation Price (intra-bar check):
   - LONG: liq_price = entry * (1 - (1/leverage) + mmr)
   - SHORT: liq_price = entry * (1 + (1/leverage) - mmr)
   - Checked against low/high BEFORE stop-loss

3. Stop-Loss in Price (not % of wallet):
   - LONG: stop_price = entry * (1 - stop_loss_pct)
   - SHORT: stop_price = entry * (1 + stop_loss_pct)

4. Exposure Caps:
   - gross_exposure_cap = 1.5 * equity
   - per_side_exposure_cap = 1.0 * equity
   - per_pair_exposure_cap = 0.3 * equity

5. Kill-Switch:
   - Pause new entries for 24h if:
     - day_PnL <= -8% OR rolling_1h_PnL <= -12%

Slippage Model:
- LONG Entry: Fill at ma_low (maker)
- SHORT Entry: Fill at ma_high (maker)
- LONG Close: Fill at ma_base (maker)
- SHORT Close: Fill at ma_base (maker)
- Liquidation: Fill at liq_price (taker)
- Stop Loss LONG: Fill at stop_price or low if worse (taker)
- Stop Loss SHORT: Fill at stop_price or high if worse (taker)

Priority: Liquidation > Stop-Loss > Normal Close
"""

class EnvelopeMulti_v2():
    def __init__(
        self,
        df_list,
        oldest_pair,
        type=None,
        params=None,
    ):
        self.df_list = df_list
        self.oldest_pair = oldest_pair
        if type is None:
            type = ["long"]
        if params is None:
            params = {}
        self.use_long = True if "long" in type else False
        self.use_short = True if "short" in type else False
        self.params = params

        
    def populate_indicators(self):
        for pair in self.df_list:
            params = self.params[pair]
            df = self.df_list[pair]
            df.drop(
                columns=df.columns.difference(['open','high','low','close','volume']), 
                inplace=True
            )
            
            # -- Populate indicators --
            if params["src"] == "close":
                src = df["close"]
            elif params["src"] == "ohlc4":
                src = (df["close"] + df["high"] + df["low"] + df["open"]) / 4
            else:
                # Default to close if invalid src
                src = df["close"]

            df['ma_base'] = ta.trend.sma_indicator(close=src, window=params["ma_base_window"]).shift(1)
            # Calculate envelopes without round() asymmetry
            for i in range(1, len(params["envelopes"]) + 1):
                e = params["envelopes"][i-1]
                df[f'ma_high_{i}'] = df['ma_base'] / (1 - e)
                df[f'ma_low_{i}'] = df['ma_base'] * (1 - e)
        
            self.df_list[pair] = df
                
        return self.df_list[self.oldest_pair]
    
    def populate_buy_sell(self): 
        data_open_long = []
        data_close_long = []
        data_open_short = []
        data_close_short = []

        for pair in self.df_list:
            params = self.params[pair]
            df = self.df_list[pair]
            # -- Initiate populate --
            df["close_long"] = False
            df["close_short"] = False
            for i in range(1, len(params["envelopes"]) + 1):
                df[f"open_short_{i}"] = False
                df[f"open_long_{i}"] = False
            df["pair"] = pair
            df["null"] = np.nan
            
            
            if self.use_long:
                for i in range(1, len(params["envelopes"]) + 1):
                    df.loc[
                        (df['low'] <= df[f'ma_low_{i}'])
                        , f"open_long_{i}"
                    ] = True
                
                # -- Populate close long --
                df.loc[
                    (df['high'] >= df['ma_base'])
                    , "close_long"
                ] = True
                
            
            if self.use_short:
                for i in range(1, len(params["envelopes"]) + 1):
                    df.loc[
                        (df['high'] >= df[f'ma_high_{i}'])
                        , f"open_short_{i}"
                    ] = True
                
                df.loc[
                    (df['low'] <= df['ma_base'])
                    , "close_short"
                ] = True
                
                
            # -- Populate pair list per date (do not touch)--
            data_open_long.append(
                df.loc[
                (df['open_long_1']  == True) 
                ]['pair']
            )
            data_close_long.append(
                df.loc[
                (df['close_long']  == True) 
                ]['pair']
            )
            data_open_short.append(
                df.loc[
                (df['open_short_1']  == True) 
                ]['pair']
            )
            data_close_short.append(
                df.loc[
                (df['close_short']  == True)
                ]['pair']
            )

        data_open_long.append(self.df_list[self.oldest_pair]['null'])
        data_close_long.append(self.df_list[self.oldest_pair]['null'])
        data_open_short.append(self.df_list[self.oldest_pair]['null'])
        data_close_short.append(self.df_list[self.oldest_pair]['null'])

        for pair in self.df_list:
            df = self.df_list[pair]
            del df["pair"]
            del df["null"]
            self.df_list[pair] = df
        df_open_long = pd.concat(data_open_long, axis=1)
        df_open_long['combined']= df_open_long.values.tolist()
        df_open_long['combined'] = [[i for i in j if i == i] for j in list(df_open_long['combined'])]
        df_close_long = pd.concat(data_close_long, axis=1)
        df_close_long['combined']= df_close_long.values.tolist()
        df_close_long['combined'] = [[i for i in j if i == i] for j in list(df_close_long['combined'])]
        df_open_short = pd.concat(data_open_short, axis=1)
        df_open_short['combined']= df_open_short.values.tolist()
        df_open_short['combined'] = [[i for i in j if i == i] for j in list(df_open_short['combined'])]
        df_close_short = pd.concat(data_close_short, axis=1)
        df_close_short['combined']= df_close_short.values.tolist()
        df_close_short['combined'] = [[i for i in j if i == i] for j in list(df_close_short['combined'])]
        self.open_long_obj = df_open_long['combined']
        self.close_long_obj = df_close_long['combined']
        self.open_short_obj = df_open_short['combined']
        self.close_short_obj = df_close_short['combined']
         
        return self.df_list[self.oldest_pair]
        
    def run_backtest(self, initial_wallet=1000, leverage=1, maker_fee=0.0002, taker_fee=0.0006, stop_loss=1, reinvest=True, liquidation=True,
                     gross_cap=1.5, per_side_cap=1.0, per_pair_cap=0.3, margin_cap=0.8, use_kill_switch=True,
                     auto_adjust_size=True, extreme_leverage_threshold=50,
                     risk_mode="neutral", base_size=None, max_expo_cap=2.0, params_adapter=None):
        """
        Run backtest with V2 margin system and configurable risk mode.

        Parameters:
        -----------
        risk_mode : str
            "neutral" - Notional constant regardless of leverage (size/leverage)
            "scaling" - Notional scales with leverage (size*leverage)
            "hybrid"  - Notional scales with leverage but capped at max_expo_cap

        base_size : float, optional
            Base size percentage (e.g., 0.06 = 6% of equity).
            If None, uses params[pair]["size"] for backward compatibility.

        max_expo_cap : float
            (HYBRID mode only) Maximum total notional as multiple of equity.
            Example: 2.0 means max notional = 2x equity

        params_adapter : ParamsAdapter, optional
            Dynamic parameter adapter that modifies params based on date/pair.
            If None, uses static self.params throughout the backtest.
            Example: RegimeBasedAdapter to adapt envelopes based on market regime
        """
        params = self.params
        df_ini = self.df_list[self.oldest_pair][:]
        wallet = initial_wallet
        maker_fee = maker_fee
        taker_fee = taker_fee
        stop_loss_pourcent = stop_loss
        reinvest = reinvest
        use_liquidation = liquidation
        trades = []
        days = []
        current_day = 0
        previous_day = 0
        current_positions = {}
        is_liquidated = False

        # V2: Validate risk_mode
        if risk_mode not in ["neutral", "scaling", "hybrid"]:
            raise ValueError(f"Invalid risk_mode: {risk_mode}. Must be 'neutral', 'scaling', or 'hybrid'")

        # V2: Base-size resolver (priority: arg > params.base_size > params.size)
        def _resolve_base_size(pair: str) -> float:
            """Resolve base_size for a pair with fallback chain."""
            if base_size is not None:
                return float(base_size)
            p = params[pair]
            if 'base_size' in p:
                return float(p['base_size'])
            if 'size' in p:
                return float(p['size'])
            raise KeyError(f"Missing size for {pair}: need 'base_size' or legacy 'size'.")

        # V2: Margin management
        used_margin = 0.0
        equity = initial_wallet

        # V2: Risk mode configuration
        # print(f"[Risk Mode] {risk_mode.upper()} (leverage={leverage}x)")

        # if risk_mode == "neutral":
        #     print(f"  -> Neutral mode: notional = equity * base_size (constant)")
        # elif risk_mode == "scaling":
        #     if auto_adjust_size:
        #         print(f"  -> Scaling mode: ignoring auto_adjust_size (notional scales with leverage)")
        #     print(f"  -> Scaling mode: notional = equity * base_size * leverage")
        # elif risk_mode == "hybrid":
        #     print(f"  -> Hybrid mode: notional = min(equity * base_size * leverage, equity * {max_expo_cap})")

        # V2: Adjust per_pair_cap for extreme leverage (optional hardening)
        effective_per_pair_cap = per_pair_cap
        if leverage > extreme_leverage_threshold:
            leverage_factor = (leverage / extreme_leverage_threshold) ** 0.5
            effective_per_pair_cap = per_pair_cap / leverage_factor
            print(f"[Extreme leverage] per_pair_cap reduced: {per_pair_cap:.2f} -> {effective_per_pair_cap:.2f}")

        # V2: Kill-switch
        kill_switch = KillSwitch(day_pnl_threshold=-0.08, hour_pnl_threshold=-0.12, pause_hours=24) if use_kill_switch else None

        # V2: Event counters & reporting
        event_counters = {
            'rejected_by_gross_cap': 0,
            'rejected_by_per_side_cap': 0,
            'rejected_by_per_pair_cap': 0,
            'rejected_by_margin_cap': 0,
            'hit_liquidation': 0,
            'hit_stop_loss': 0,
            'close_ma_base': 0,
            'maker_fills': 0,
            'taker_fills': 0,
            'total_maker_fees': 0.0,
            'total_taker_fees': 0.0,
            'added_margin': 0.0,
            'released_margin': 0.0
        }

        # V2: Exposure & margin tracking
        exposure_history = []
        margin_history = []

        for index, row in df_ini.iterrows():
            if is_liquidated:
                break

            # V2: Update equity based on current prices
            last_prices = {}
            for pair in current_positions:
                if index in self.df_list[pair].index:
                    last_prices[pair] = self.df_list[pair].loc[index]['open']
            equity = update_equity(wallet, current_positions, last_prices)

            # V2: Check kill-switch
            if kill_switch:
                is_paused = kill_switch.update(index, equity, initial_wallet)
                if is_paused:
                    # Skip opening new positions but continue managing existing ones
                    pass

            # -- Add daily report --
            current_day = index.day
            if previous_day != current_day:
                temp_wallet = wallet
                long_exposition = 0
                short_exposition = 0
                for pair in current_positions:
                    if index not in self.df_list[pair].index:
                        continue
                    actual_row = self.df_list[pair].loc[index]
                    if current_positions[pair]['side'] == "LONG":
                        close_price = actual_row['open']
                        trade_result = (close_price - current_positions[pair]['price']) / current_positions[pair]['price']
                        close_size = current_positions[pair]['size'] + current_positions[pair]['size'] * trade_result
                        temp_wallet += close_size - current_positions[pair]['size']
                        long_exposition += current_positions[pair]['size']

                    elif current_positions[pair]['side'] == "SHORT":
                        close_price = actual_row['open']
                        trade_result = (current_positions[pair]['price'] - close_price) / current_positions[pair]['price']
                        close_size = current_positions[pair]['size'] + current_positions[pair]['size'] * trade_result
                        temp_wallet += close_size - current_positions[pair]['size']
                        short_exposition += current_positions[pair]['size']

                # V2: Use equity for liquidation check
                if use_liquidation and equity <= 0:
                    liquidation_date = str(index.year) + "-" + str(index.month) + "-" + str(index.day)
                    print(f"Liquidation le {liquidation_date}: Equity <= 0 (wallet={wallet:.2f}, equity={equity:.2f})")
                    wallet = 0
                    equity = 0
                    days.append({
                        "day":str(index.year)+"-"+str(index.month)+"-"+str(index.day),
                        "wallet":0,
                        "price":row['open'],
                        "long_exposition":0,
                        "short_exposition":0,
                    })
                    is_liquidated = True
                    break

                days.append({
                    "day":str(index.year)+"-"+str(index.month)+"-"+str(index.day),
                    "wallet":temp_wallet,
                    "price":row['open'],
                    "long_exposition":long_exposition,
                    "short_exposition":short_exposition,
                })
    
            previous_day = current_day

            closed_pair = []

            # V2: -- Check Liquidation Price FIRST (highest priority) --
            if use_liquidation and len(current_positions) > 0:
                for pair in list(current_positions.keys()):
                    if pair in closed_pair:
                        continue
                    if index not in self.df_list[pair].index:
                        continue
                    if 'liq_price' not in current_positions[pair]:
                        continue  # Legacy positions without liq_price

                    actual_row = self.df_list[pair].loc[index]
                    liq_price = current_positions[pair]['liq_price']

                    # Check LONG liquidation: if low touches liq_price
                    if current_positions[pair]['side'] == "LONG" and actual_row['low'] <= liq_price:
                        close_price = liq_price  # Liquidation executes AT liquidation price

                        # Use apply_close for proper PnL/fee calculation
                        pnl, fee = apply_close(current_positions[pair], close_price, taker_fee, is_taker=True)
                        wallet += pnl
                        released = current_positions[pair].get('init_margin', 0)
                        used_margin = max(0.0, used_margin - released)
                        event_counters['released_margin'] += released

                        # Force wallet to 0 if negative (total loss)
                        if wallet < 0:
                            wallet = 0

                        liquidation_date = str(index.year) + "-" + str(index.month) + "-" + str(index.day)
                        # print(f"LIQUIDATION {liquidation_date}: {pair} LONG @ {liq_price:.2f} (entry: {current_positions[pair]['price']:.2f})")

                        trades.append({
                            "pair": pair,
                            "open_date": current_positions[pair]['date'],
                            "close_date": index,
                            "position": current_positions[pair]['side'],
                            "open_reason": current_positions[pair]['reason'],
                            "close_reason": "Liquidation",
                            "open_price": current_positions[pair]['price'],
                            "close_price": close_price,
                            "open_fee": current_positions[pair]['fee'],
                            "close_fee": fee,
                            "open_trade_size": current_positions[pair]['size'],
                            "close_trade_size": current_positions[pair]['size'] + pnl,
                            "wallet": wallet,
                        })
                        del current_positions[pair]
                        closed_pair.append(pair)

                        # Check if total liquidation (wallet = 0)
                        if wallet == 0:
                            is_liquidated = True
                            if len(days) > 0:
                                days[-1]['wallet'] = 0
                                days[-1]['long_exposition'] = 0
                                days[-1]['short_exposition'] = 0
                            break
                        continue

                    # Check SHORT liquidation: if high touches liq_price
                    if current_positions[pair]['side'] == "SHORT" and actual_row['high'] >= liq_price:
                        close_price = liq_price

                        pnl, fee = apply_close(current_positions[pair], close_price, taker_fee, is_taker=True)
                        wallet += pnl
                        released = current_positions[pair].get('init_margin', 0)
                        used_margin = max(0.0, used_margin - released)
                        event_counters['released_margin'] += released

                        if wallet < 0:
                            wallet = 0

                        liquidation_date = str(index.year) + "-" + str(index.month) + "-" + str(index.day)
                        # print(f"LIQUIDATION {liquidation_date}: {pair} SHORT @ {liq_price:.2f} (entry: {current_positions[pair]['price']:.2f})")

                        trades.append({
                            "pair": pair,
                            "open_date": current_positions[pair]['date'],
                            "close_date": index,
                            "position": current_positions[pair]['side'],
                            "open_reason": current_positions[pair]['reason'],
                            "close_reason": "Liquidation",
                            "open_price": current_positions[pair]['price'],
                            "close_price": close_price,
                            "open_fee": current_positions[pair]['fee'],
                            "close_fee": fee,
                            "open_trade_size": current_positions[pair]['size'],
                            "close_trade_size": current_positions[pair]['size'] + pnl,
                            "wallet": wallet,
                        })
                        del current_positions[pair]
                        closed_pair.append(pair)

                        if wallet == 0:
                            is_liquidated = True
                            if len(days) > 0:
                                days[-1]['wallet'] = 0
                                days[-1]['long_exposition'] = 0
                                days[-1]['short_exposition'] = 0
                            break
                        continue

            # Exit if liquidated before checking stop-loss
            if is_liquidated:
                break

            # -- Check Stop Loss independently (CRITICAL FIX) --
            if len(current_positions) > 0:
                for pair in list(current_positions.keys()):
                    if pair in closed_pair:
                        continue
                    if index not in self.df_list[pair].index:
                        continue
                    actual_row = self.df_list[pair].loc[index]

                    # Check LONG stop loss
                    if current_positions[pair]['side'] == "LONG" and actual_row['low'] <= current_positions[pair]['stop_loss']:
                        close_price = actual_row['low']
                        trade_result = (close_price - current_positions[pair]['price']) / current_positions[pair]['price']
                        close_size = current_positions[pair]['size'] + current_positions[pair]['size'] * trade_result
                        fee = close_size * taker_fee  # Use taker_fee for SL
                        wallet += close_size - current_positions[pair]['size'] - fee

                        # Check if liquidated and clamp wallet before recording trade
                        if use_liquidation and wallet <= 0:
                            wallet = 0
                            liquidation_date = str(index.year) + "-" + str(index.month) + "-" + str(index.day)
                            print(f"Liquidation le {liquidation_date}: Plus d'argent dans le portefeuille.")

                        trades.append({
                            "pair": pair,
                            "open_date": current_positions[pair]['date'],
                            "close_date": index,
                            "position": current_positions[pair]['side'],
                            "open_reason": current_positions[pair]['reason'],
                            "close_reason": "Stop Loss",
                            "open_price": current_positions[pair]['price'],
                            "close_price": close_price,
                            "open_fee": current_positions[pair]['fee'],
                            "close_fee": fee,
                            "open_trade_size": current_positions[pair]['size'],
                            "close_trade_size": close_size,
                            "wallet": wallet,
                        })
                        del current_positions[pair]
                        closed_pair.append(pair)

                        # Break if liquidated
                        if wallet == 0 and use_liquidation:
                            is_liquidated = True
                            # Update last day in days to reflect liquidation
                            if len(days) > 0:
                                days[-1]['wallet'] = 0
                                days[-1]['long_exposition'] = 0
                                days[-1]['short_exposition'] = 0
                            break
                        continue

                    # Check SHORT stop loss
                    if current_positions[pair]['side'] == "SHORT" and actual_row['high'] >= current_positions[pair]['stop_loss']:
                        close_price = actual_row['high']
                        trade_result = (current_positions[pair]['price'] - close_price) / current_positions[pair]['price']
                        close_size = current_positions[pair]['size'] + current_positions[pair]['size'] * trade_result
                        fee = close_size * taker_fee  # Use taker_fee for SL
                        wallet += close_size - current_positions[pair]['size'] - fee

                        # Check if liquidated and clamp wallet before recording trade
                        if use_liquidation and wallet <= 0:
                            wallet = 0
                            liquidation_date = str(index.year) + "-" + str(index.month) + "-" + str(index.day)
                            print(f"Liquidation le {liquidation_date}: Plus d'argent dans le portefeuille.")

                        trades.append({
                            "pair": pair,
                            "open_date": current_positions[pair]['date'],
                            "close_date": index,
                            "position": current_positions[pair]['side'],
                            "open_reason": current_positions[pair]['reason'],
                            "close_reason": "Stop Loss",
                            "open_price": current_positions[pair]['price'],
                            "close_price": close_price,
                            "open_fee": current_positions[pair]['fee'],
                            "close_fee": fee,
                            "open_trade_size": current_positions[pair]['size'],
                            "close_trade_size": close_size,
                            "wallet": wallet,
                        })
                        del current_positions[pair]
                        closed_pair.append(pair)

                        # Break if liquidated
                        if wallet == 0 and use_liquidation:
                            is_liquidated = True
                            # Update last day in days to reflect liquidation
                            if len(days) > 0:
                                days[-1]['wallet'] = 0
                                days[-1]['long_exposition'] = 0
                                days[-1]['short_exposition'] = 0
                            break
                        continue

            # Exit completely if liquidated - no more trading possible
            if is_liquidated:
                break

            # -- Close positions at ma_base --
            close_long_row = self.close_long_obj.loc[index]
            close_short_row = self.close_short_obj.loc[index]
            if len(current_positions) > 0:
                # -- Close LONG at ma_base --
                long_position_to_close = set({k: v for k,v in current_positions.items() if v['side'] == "LONG"}).intersection(set(close_long_row))
                for pair in long_position_to_close:
                    if pair in closed_pair:
                        continue
                    if index not in self.df_list[pair].index:
                        continue
                    actual_row = self.df_list[pair].loc[index]

                    close_price = actual_row['ma_base']
                    trade_result = (close_price - current_positions[pair]['price']) / current_positions[pair]['price']
                    close_size = current_positions[pair]['size'] + current_positions[pair]['size'] * trade_result
                    fee = close_size * maker_fee
                    wallet += close_size - current_positions[pair]['size'] - fee
                    released = current_positions[pair].get('init_margin', 0)
                    used_margin = max(0.0, used_margin - released)
                    event_counters['released_margin'] += released

                    # Check if liquidated and clamp wallet before recording trade
                    if use_liquidation and wallet <= 0:
                        wallet = 0
                        liquidation_date = str(index.year) + "-" + str(index.month) + "-" + str(index.day)
                        print(f"Liquidation le {liquidation_date}: Plus d'argent dans le portefeuille.")

                    trades.append({
                        "pair": pair,
                        "open_date": current_positions[pair]['date'],
                        "close_date": index,
                        "position": current_positions[pair]['side'],
                        "open_reason": current_positions[pair]['reason'],
                        "close_reason": "Market",
                        "open_price": current_positions[pair]['price'],
                        "close_price": close_price,
                        "open_fee": current_positions[pair]['fee'],
                        "close_fee": fee,
                        "open_trade_size":current_positions[pair]['size'],
                        "close_trade_size":close_size,
                        "wallet": wallet,
                    })
                    del current_positions[pair]
                    closed_pair.append(pair)

                    # Break if liquidated
                    if wallet == 0 and use_liquidation:
                        is_liquidated = True
                        break

                # -- Close SHORT at ma_base --
                short_position_to_close = set({k: v for k,v in current_positions.items() if v['side'] == "SHORT"}).intersection(set(close_short_row))
                for pair in short_position_to_close:
                    if pair in closed_pair:
                        continue
                    if index not in self.df_list[pair].index:
                        continue
                    actual_row = self.df_list[pair].loc[index]

                    close_price = actual_row['ma_base']
                    trade_result = (current_positions[pair]['price'] - close_price) / current_positions[pair]['price']
                    close_size = current_positions[pair]['size'] + current_positions[pair]['size'] * trade_result
                    fee = close_size * maker_fee
                    wallet += close_size - current_positions[pair]['size'] - fee
                    released = current_positions[pair].get('init_margin', 0)
                    used_margin = max(0.0, used_margin - released)
                    event_counters['released_margin'] += released

                    # Check if liquidated and clamp wallet before recording trade
                    if use_liquidation and wallet <= 0:
                        wallet = 0
                        liquidation_date = str(index.year) + "-" + str(index.month) + "-" + str(index.day)
                        print(f"Liquidation le {liquidation_date}: Plus d'argent dans le portefeuille.")

                    trades.append({
                        "pair": pair,
                        "open_date": current_positions[pair]['date'],
                        "close_date": index,
                        "position": current_positions[pair]['side'],
                        "open_reason": current_positions[pair]['reason'],
                        "close_reason": "Market",
                        "open_price": current_positions[pair]['price'],
                        "close_price": close_price,
                        "open_fee": current_positions[pair]['fee'],
                        "close_fee": fee,
                        "open_trade_size":current_positions[pair]['size'],
                        "close_trade_size":close_size,
                        "wallet": wallet,
                    })
                    del current_positions[pair]
                    closed_pair.append(pair)

                    # Break if liquidated
                    if wallet == 0 and use_liquidation:
                        is_liquidated = True
                        break

            # Exit completely if liquidated - no opening new positions
            if is_liquidated:
                break

            # V2: Skip opening if kill-switch is active
            is_paused = kill_switch.is_paused if kill_switch else False

            # -- Check for opening position --
            # -- Open LONG market --
            open_long_row = self.open_long_obj.loc[index]
            for pair in open_long_row:
                if is_paused:
                    break  # Skip all new positions if kill-switch active

                # Check if index exists in pair's dataframe
                if index not in self.df_list[pair].index:
                    continue
                actual_position = None
                actual_row = self.df_list[pair].loc[index]

                # V2: Get adapted params if adapter provided
                effective_params = params_adapter.get_params_at_date(index, pair) if params_adapter else params[pair]

                for i in range(1, len(effective_params["envelopes"]) + 1):
                    if pair in current_positions:
                        actual_position = current_positions[pair]
                    if (actual_position and actual_position["side"] == "SHORT") or (actual_row[f"open_long_{i}"] == False) or (pair in closed_pair):
                        break
                    # Skip if already at this envelope level or higher (can't add more at same/higher level)
                    if actual_position and actual_position["envelope"] >= i:
                        continue
                    if actual_row[f"open_long_{i}"]:
                        # V2: Recalculate envelope price with adapted params
                        ma_base = actual_row['ma_base']
                        envelope_pct = effective_params["envelopes"][i-1]
                        open_price = ma_base * (1 - envelope_pct)

                        # V2: Calculate notional and qty based on equity (not wallet)
                        if reinvest or (wallet <= initial_wallet):
                            base_capital = equity
                        else:
                            base_capital = initial_wallet

                        # V2: Calculate notional according to risk_mode (use effective_params)
                        eff_base = _resolve_base_size(pair)
                        notional = calculate_notional_per_level(
                            equity=base_capital,
                            base_size=eff_base,
                            leverage=leverage,
                            n_levels=len(effective_params["envelopes"]),
                            risk_mode=risk_mode,
                            max_expo_cap=max_expo_cap
                        )

                        qty = notional / open_price
                        init_margin = notional / leverage

                        # V2: Check exposure caps BEFORE opening
                        allowed, reason = check_exposure_caps(
                            notional, "LONG", pair, current_positions, equity,
                            gross_cap, per_side_cap, effective_per_pair_cap
                        )
                        if not allowed:
                            # Track rejection reason
                            if "Gross exposure" in reason:
                                event_counters['rejected_by_gross_cap'] += 1
                            elif "Per-side exposure" in reason:
                                event_counters['rejected_by_per_side_cap'] += 1
                            elif "Per-pair exposure" in reason:
                                event_counters['rejected_by_per_pair_cap'] += 1
                            break

                        # V2: Check margin cap (protection against margin cascade)
                        if used_margin + init_margin > equity * margin_cap:
                            event_counters['rejected_by_margin_cap'] += 1
                            break

                        # Calculate fees and pos_size
                        fee = notional * maker_fee
                        pos_size = notional - fee
                        wallet -= fee
                        used_margin += init_margin
                        event_counters['added_margin'] += init_margin

                        # Check if liquidated after paying fees
                        if use_liquidation and wallet <= 0:
                            wallet = 0
                            used_margin = max(0.0, used_margin - init_margin)  # Rollback margin with clamp
                            event_counters['added_margin'] -= init_margin  # Rollback counter
                            liquidation_date = str(index.year) + "-" + str(index.month) + "-" + str(index.day)
                            print(f"Liquidation le {liquidation_date}: Plus d'argent dans le portefeuille.")
                            is_liquidated = True
                            break

                        # V2: Calculate liquidation price
                        mmr = get_mmr(pair)
                        liq_price = compute_liq_price(open_price, "LONG", leverage, mmr)

                        # Stop-loss price (not % of wallet, but price level)
                        stop_loss = open_price - stop_loss_pourcent * open_price

                        if actual_position:
                            # Averaging down: recalculate weighted average entry price
                            actual_position["price"] = (actual_position["size"] * actual_position["price"] + open_price * pos_size) / (actual_position["size"] + pos_size)
                            actual_position["size"] = actual_position["size"] + pos_size
                            actual_position["fee"] = actual_position["fee"] + fee
                            actual_position["envelope"] = i
                            actual_position["reason"] = f"Limit Envelop {i}"
                            actual_position["init_margin"] = actual_position.get("init_margin", 0) + init_margin
                            # V2: Recalculate liq_price based on new average entry
                            actual_position["liq_price"] = compute_liq_price(actual_position["price"], "LONG", leverage, mmr)
                            # Keep the lowest stop loss (most protective) when averaging down
                            if stop_loss < actual_position["stop_loss"]:
                                actual_position["stop_loss"] = stop_loss
                        else:
                            current_positions[pair] = {
                                "size": pos_size,
                                "date": index,
                                "price": open_price,
                                "fee": fee,
                                "reason": f"Limit Envelop {i}",
                                "side": "LONG",
                                "envelope": i,
                                "stop_loss": stop_loss,
                                "liq_price": liq_price,  # V2
                                "init_margin": init_margin,  # V2
                                "qty": qty,  # V2
                            }

            # -- Open SHORT market --
            open_short_row = self.open_short_obj.loc[index]
            for pair in open_short_row:
                if is_paused:
                    break  # Skip all new positions if kill-switch active

                # Check if index exists in pair's dataframe
                if index not in self.df_list[pair].index:
                    continue
                actual_position = None
                actual_row = self.df_list[pair].loc[index]

                # V2: Get adapted params if adapter provided
                effective_params = params_adapter.get_params_at_date(index, pair) if params_adapter else params[pair]

                for i in range(1, len(effective_params["envelopes"]) + 1):
                    if pair in current_positions:
                        actual_position = current_positions[pair]
                    if (actual_position and actual_position["side"] == "LONG") or actual_row[f"open_short_{i}"] == False or (pair in closed_pair):
                        break
                    if actual_position and actual_position["envelope"] >= i:
                        continue
                    if actual_row[f"open_short_{i}"]:
                        # V2: Recalculate envelope price with adapted params
                        ma_base = actual_row['ma_base']
                        envelope_pct = effective_params["envelopes"][i-1]
                        open_price = ma_base / (1 - envelope_pct)

                        # V2: Calculate notional and qty based on equity (not wallet)
                        if reinvest or (wallet <= initial_wallet):
                            base_capital = equity
                        else:
                            base_capital = initial_wallet

                        # V2: Calculate notional according to risk_mode (use effective_params)
                        eff_base = _resolve_base_size(pair)
                        notional = calculate_notional_per_level(
                            equity=base_capital,
                            base_size=eff_base,
                            leverage=leverage,
                            n_levels=len(effective_params["envelopes"]),
                            risk_mode=risk_mode,
                            max_expo_cap=max_expo_cap
                        )

                        qty = notional / open_price
                        init_margin = notional / leverage

                        # V2: Check exposure caps BEFORE opening
                        allowed, reason = check_exposure_caps(
                            notional, "SHORT", pair, current_positions, equity,
                            gross_cap, per_side_cap, effective_per_pair_cap
                        )
                        if not allowed:
                            # print(f"❌ Position rejected: {reason}")
                            break

                        # V2: Check margin cap (protection against margin cascade)
                        if used_margin + init_margin > equity * margin_cap:
                            # print(f"❌ Margin cap exceeded: {used_margin + init_margin:.2f} > {equity * margin_cap:.2f}")
                            break

                        # Calculate fees and pos_size
                        fee = notional * maker_fee
                        pos_size = notional - fee
                        wallet -= fee
                        used_margin += init_margin
                        event_counters['added_margin'] += init_margin

                        # Check if liquidated after paying fees
                        if use_liquidation and wallet <= 0:
                            wallet = 0
                            used_margin = max(0.0, used_margin - init_margin)  # Rollback margin with clamp
                            event_counters['added_margin'] -= init_margin  # Rollback counter
                            liquidation_date = str(index.year) + "-" + str(index.month) + "-" + str(index.day)
                            print(f"Liquidation le {liquidation_date}: Plus d'argent dans le portefeuille.")
                            is_liquidated = True
                            break

                        # V2: Calculate liquidation price
                        mmr = get_mmr(pair)
                        liq_price = compute_liq_price(open_price, "SHORT", leverage, mmr)

                        # Stop-loss price (SHORT: above entry)
                        stop_loss = open_price + stop_loss_pourcent * open_price

                        if actual_position:
                            # Averaging down: recalculate weighted average entry price
                            actual_position["price"] = (actual_position["size"] * actual_position["price"] + open_price * pos_size) / (actual_position["size"] + pos_size)
                            actual_position["size"] = actual_position["size"] + pos_size
                            actual_position["fee"] = actual_position["fee"] + fee
                            actual_position["envelope"] = i
                            actual_position["reason"] = f"Limit Envelop {i}"
                            actual_position["init_margin"] = actual_position.get("init_margin", 0) + init_margin
                            # V2: Recalculate liq_price based on new average entry
                            actual_position["liq_price"] = compute_liq_price(actual_position["price"], "SHORT", leverage, mmr)
                            # Keep the highest stop loss (most protective) when averaging down SHORT
                            if stop_loss > actual_position["stop_loss"]:
                                actual_position["stop_loss"] = stop_loss
                        else:
                            current_positions[pair] = {
                                "size": pos_size,
                                "date": index,
                                "price": open_price,
                                "fee": fee,
                                "reason": f"Limit Envelop {i}",
                                "side": "SHORT",
                                "envelope": i,
                                "stop_loss": stop_loss,
                                "liq_price": liq_price,  # V2
                                "init_margin": init_margin,  # V2
                                "qty": qty,  # V2
                            }          
                        
        df_days = pd.DataFrame(days)
        df_days['day'] = pd.to_datetime(df_days['day'])
        df_days = df_days.set_index(df_days['day'])

        df_trades = pd.DataFrame(trades)

        # Guard against no trades
        if len(trades) == 0:
            return {
                "wallet": wallet,
                "trades": df_trades,
                "days": df_days
            }

        df_trades['open_date'] = pd.to_datetime(df_trades['open_date'])
        df_trades = df_trades.set_index(df_trades['open_date'])

        # V2: Calculate final reporting metrics
        df_exposure = pd.DataFrame(exposure_history) if exposure_history else pd.DataFrame()
        df_margin = pd.DataFrame(margin_history) if margin_history else pd.DataFrame()

        return get_metrics(df_trades, df_days) | {
            "wallet": wallet,
            "trades": df_trades,
            "days": df_days,
            # V2: Additional reporting
            "event_counters": event_counters,
            "exposure_history": df_exposure,
            "margin_history": df_margin,
            "config": {
                "leverage": leverage,
                "gross_cap": gross_cap,
                "per_side_cap": per_side_cap,
                "per_pair_cap": per_pair_cap,
                "effective_per_pair_cap": effective_per_pair_cap,
                "margin_cap": margin_cap,
                "auto_adjust_size": auto_adjust_size,
                "extreme_leverage_threshold": extreme_leverage_threshold,
                # Risk mode config
                "risk_mode": risk_mode,
                "base_size": base_size,
                "max_expo_cap": max_expo_cap
            }
        } 