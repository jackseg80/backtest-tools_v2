import sys
sys.path.append('../..')
import ta
import numpy as np
import pandas as pd
from utilities.bt_analysis import get_metrics

class EnvelopeMulti():
    def __init__(
        self,
        df_list,
        oldest_pair,
        type=["long"],
        params={},
    ):
        self.df_list = df_list
        self.oldest_pair = oldest_pair
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

            df['ma_base'] = ta.trend.sma_indicator(close=src, window=params["ma_base_window"]).shift(1)
            high_envelopes = [round(1/(1-e)-1, 3) for e in params["envelopes"]]
            for i in range(1, len(params["envelopes"]) + 1):
                df[f'ma_high_{i}'] = df['ma_base'] * (1 + high_envelopes[i-1])
                df[f'ma_low_{i}'] = df['ma_base'] * (1 - params["envelopes"][i-1])
        
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
        
        del df["pair"]
        del df["null"]
        self.df_list[pair] = df

        data_open_long.append(self.df_list[self.oldest_pair]['null'])
        data_close_long.append(self.df_list[self.oldest_pair]['null'])
        data_open_short.append(self.df_list[self.oldest_pair]['null'])
        data_close_short.append(self.df_list[self.oldest_pair]['null'])
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
        
    def     run_backtest(self, initial_wallet=1000, leverage=1, maker_fee=0.0002, taker_fee=0.0006, stop_loss = 1, reinvest=True, liquidation=True):
        params = self.params
        df_ini = self.df_list[self.oldest_pair][:]
        wallet = initial_wallet
        long_exposition = 0
        short_exposition = 0
        maker_fee = maker_fee
        taker_fee = taker_fee
        stop_loss_pourcent = stop_loss
        reinvest = reinvest
        liquidation = liquidation
        trades = []
        days = []
        current_day = 0
        previous_day = 0
        current_positions = {}
        
        for index, row in df_ini.iterrows():
            # -- Add daily report --
            current_day = index.day
            if previous_day != current_day:
                temp_wallet = wallet
                for pair in current_positions:
                    actual_row = self.df_list[pair].loc[index]
                    if current_positions[pair]['side'] == "LONG":
                        close_price = actual_row['open']
                        trade_result = (close_price - current_positions[pair]['price']) / current_positions[pair]['price']
                        close_size = current_positions[pair]['size'] + current_positions[pair]['size']  * trade_result
                        fee = close_size * taker_fee
                        temp_wallet += close_size - current_positions[pair]['size'] - fee
                    
                    elif current_positions[pair]['side'] == "SHORT":                        
                        close_price = actual_row['open']
                        trade_result = (current_positions[pair]['price'] - close_price) / current_positions[pair]['price']
                        close_size = current_positions[pair]['size'] + current_positions[pair]['size']  * trade_result
                        fee = close_size * taker_fee
                        temp_wallet += close_size - current_positions[pair]['size'] - fee

                # Wallet est à 0 ? Si oui, on coupe tout et on ajoute le dernier jour au backtest
                if temp_wallet <= 0:
                    liquidation_date = str(index.year) + "-" + str(index.month) + "-" + str(index.day)
                    print(f"Liquidation le {liquidation_date}: Plus d'argent dans le portefeuille.")
                    days.append({
                        "day":str(index.year)+"-"+str(index.month)+"-"+str(index.day),
                        "wallet":temp_wallet,
                        "price":row['open'],
                        "long_exposition":0,
                        "short_exposition":0,
                        "risk":0,
                    })
                    break
                    
                days.append({
                    "day":str(index.year)+"-"+str(index.month)+"-"+str(index.day),
                    "wallet":temp_wallet,
                    "price":row['open'],
                    "long_exposition":0,
                    "short_exposition":0,
                    "risk":0,
                })
    
            previous_day = current_day 
            
            close_long_row = self.close_long_obj.loc[index]
            close_short_row = self.close_short_obj.loc[index]
            closed_pair = []
            if len(current_positions) > 0:
                # -- Close LONG --
                long_position_to_close = set({k: v for k,v in current_positions.items() if v['side'] == "LONG"}).intersection(set(close_long_row))
                for pair in long_position_to_close:
                    actual_row = self.df_list[pair].loc[index]
                    
                    # # Liquidation
                    # if liquidation:
                    #     # pnl = (actual_row['low'] - current_positions[pair]['price']) / current_positions[pair]['price']
                    #     pnl = (close_price - current_positions[pair]['price']) * close_size
                    #     if pnl < 0.9 * wallet:
                    #         liquidation_price = actual_row['low'] if current_positions[pair]['side'] == "LONG" else actual_row['high']
                    #         liquidation_date = str(index.year) + "-" + str(index.month) + "-" + str(index.day)
                    #         print(f"Liquidation le {liquidation_date}: Position {pair}")
                    #         trades.append({
                    #             "pair": pair,
                    #             "open_date": current_positions[pair]['date'],
                    #             "close_date": index,
                    #             "position": current_positions[pair]['side'],
                    #             "open_reason": current_positions[pair]['reason'],
                    #             "close_reason": "Liquidation",
                    #             "open_price": current_positions[pair]['price'],
                    #             "close_price": liquidation_price,
                    #             "open_fee": current_positions[pair]['fee'],
                    #             "close_fee": 0,
                    #             "open_trade_size": current_positions[pair]['size'],
                    #             "close_trade_size": current_positions[pair]['size'],
                    #             "wallet": wallet,
                    #         })
                    #         break

                    # Stop Loss
                    if 'stop_loss' in current_positions[pair] and actual_row['low'] <= current_positions[pair]['stop_loss']:
                        close_price = current_positions[pair]['stop_loss']
                    else:
                        close_price = actual_row['ma_base']

                    trade_result = (close_price - current_positions[pair]['price']) / current_positions[pair]['price']
                    close_size = current_positions[pair]['size'] + current_positions[pair]['size'] * trade_result
                    fee = close_size * maker_fee
                    wallet += close_size - current_positions[pair]['size'] - fee
                    trades.append({
                        "pair": pair,
                        "open_date": current_positions[pair]['date'],
                        "close_date": index,
                        "position": current_positions[pair]['side'],
                        "open_reason": current_positions[pair]['reason'],
                        "close_reason": "Stop Loss" if actual_row['low'] <= current_positions[pair]['stop_loss'] else "Market",
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
                    
                # -- Close SHORT market --
                short_position_to_close = set({k: v for k,v in current_positions.items() if v['side'] == "SHORT"}).intersection(set(close_short_row))
                for pair in short_position_to_close:
                    actual_row = self.df_list[pair].loc[index]

                    # Stop Loss
                    if 'stop_loss' in current_positions[pair] and actual_row['low'] >= current_positions[pair]['stop_loss']:
                        close_price = current_positions[pair]['stop_loss']
                    else:
                        close_price = actual_row['ma_base']

                    trade_result = (current_positions[pair]['price'] - close_price) / current_positions[pair]['price']
                    close_size = current_positions[pair]['size'] + current_positions[pair]['size'] * trade_result
                    fee = close_size * taker_fee
                    wallet += close_size - current_positions[pair]['size'] - fee
                    trades.append({
                        "pair": pair,
                        "open_date": current_positions[pair]['date'],
                        "close_date": index,
                        "position": current_positions[pair]['side'],
                        "open_reason": current_positions[pair]['reason'],
                        "close_reason": "Stop Loss" if actual_row['high'] >= current_positions[pair]['stop_loss'] else "Market",
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
                    
            # -- Check for opening position --
            # -- Open LONG market --
            open_long_row = self.open_long_obj.loc[index]
            for pair in open_long_row:
                actual_position = None
                actual_row = self.df_list[pair].loc[index]
                for i in range(1, len(params[pair]["envelopes"]) + 1):
                    if pair in current_positions:
                        actual_position = current_positions[pair]
                    if (actual_position and actual_position["side"] == "SHORT") or (actual_row[f"open_long_{i}"] == False) or (pair in closed_pair):
                        break
                    if actual_position and actual_position["envelope"] >= i:
                        continue
                    if actual_row[f"open_long_{i}"]:
                        open_price = actual_row[f'ma_low_{i}']
                        
                        # Réinvéstissement total du wallet ou toujours la même somme
                        if reinvest or (wallet <= initial_wallet):
                            pos_size = (params[pair]["size"] * wallet * leverage) / len(params[pair]["envelopes"])
                        else:
                            pos_size = (params[pair]["size"] * initial_wallet * leverage) / len(params[pair]["envelopes"])

                        fee = pos_size * maker_fee
                        pos_size -= fee
                        wallet -= fee
                                     
                        stop_loss = open_price - stop_loss_pourcent * open_price
                        
                        if actual_position:
                            actual_position["price"] = (actual_position["size"] * actual_position["price"] + open_price * pos_size) / (actual_position["size"] + pos_size)
                            actual_position["size"] = actual_position["size"] + pos_size
                            actual_position["fee"] = actual_position["fee"] + fee
                            actual_position["envelope"] = i
                            actual_position["reason"] = f"Limit Envelop {i}"
                            actual_position["stop_loss"] = stop_loss
                        else:
                            current_positions[pair] = {
                                "size": pos_size,
                                "date": index,
                                "price": open_price,
                                "fee":fee,
                                "reason": f"Limit Envelop {i}",
                                "side": "LONG",
                                "envelope": i,
                                "stop_loss": stop_loss,
                            }

            # -- Open SHORT market --
            open_short_row = self.open_short_obj.loc[index]
            for pair in open_short_row:
                actual_position = None
                actual_row = self.df_list[pair].loc[index]
                for i in range(1, len(params[pair]["envelopes"]) + 1):
                    if pair in current_positions:
                        actual_position = current_positions[pair]
                    if (actual_position and actual_position["side"] == "LONG") or actual_row[f"open_short_{i}"] == False or (pair in closed_pair):
                        break
                    if actual_position and actual_position["envelope"] >= i:
                        continue
                    if actual_row[f"open_short_{i}"]:
                        open_price = actual_row[f'ma_high_{i}']
                        
                        if reinvest or (wallet <= initial_wallet):
                            pos_size = (params[pair]["size"] * wallet * leverage) / len(params[pair]["envelopes"])
                        else:
                            pos_size = min(initial_wallet, (params[pair]["size"] * wallet * leverage) / len(params[pair]["envelopes"]))
                        
                        fee = pos_size * maker_fee
                        pos_size -= fee
                        wallet -= fee

                        stop_loss = open_price + stop_loss_pourcent * open_price
                            
                        if actual_position:
                            actual_position["price"] = (actual_position["size"] * actual_position["price"] + open_price * pos_size) / (actual_position["size"] + pos_size)
                            actual_position["size"] = actual_position["size"] + pos_size
                            actual_position["fee"] = actual_position["fee"] + fee
                            actual_position["envelope"] = i
                            actual_position["reason"] = f"Limit Envelop {i}"
                            actual_position["stop_loss"] = stop_loss
                        else:
                            current_positions[pair] = {
                                "size": pos_size,
                                "date": index,
                                "price": open_price,
                                "fee":fee,
                                "reason": f"Limit Envelop {i}",
                                "side": "SHORT",
                                "envelope": i,
                                "stop_loss": stop_loss,
                            }          
                        
        df_days = pd.DataFrame(days)
        df_days['day'] = pd.to_datetime(df_days['day'])
        df_days = df_days.set_index(df_days['day'])

        df_trades = pd.DataFrame(trades)
        df_trades['open_date'] = pd.to_datetime(df_trades['open_date'])
        df_trades = df_trades.set_index(df_trades['open_date'])   
        
        return get_metrics(df_trades, df_days) | {
            "wallet": wallet,
            "trades": df_trades,
            "days": df_days
        } 