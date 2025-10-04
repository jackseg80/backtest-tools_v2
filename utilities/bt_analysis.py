import pandas as pd
import seaborn as sns
import numpy as np
from tabulate import tabulate
from utilities.custom_indicators import get_n_columns  # Removed duplicate function

def get_metrics(df_trades, df_days):
    df_days_copy = df_days.copy()
    df_days_copy['evolution'] = df_days_copy['wallet'].diff()
    df_days_copy['daily_return'] = df_days_copy['evolution']/df_days_copy['wallet'].shift(1)
    sharpe_ratio = (365**0.5)*(df_days_copy['daily_return'].mean()/df_days_copy['daily_return'].std())
    
    df_days_copy['wallet_ath'] = df_days_copy['wallet'].cummax()
    df_days_copy['drawdown'] = df_days_copy['wallet_ath'] - df_days_copy['wallet']
    df_days_copy['drawdown_pct'] = df_days_copy['drawdown'] / df_days_copy['wallet_ath']
    max_drawdown = -df_days_copy['drawdown_pct'].max() * 100
    
    df_trades_copy = df_trades.copy()
    df_trades_copy['trade_result'] = df_trades_copy["close_trade_size"] - df_trades_copy["open_trade_size"] - df_trades_copy["open_fee"] - df_trades_copy["close_fee"]
    df_trades_copy['trade_result_pct'] = df_trades_copy['trade_result']/df_trades_copy["open_trade_size"]
    good_trades = df_trades_copy.loc[df_trades_copy['trade_result_pct'] > 0]
    win_rate = len(good_trades) / len(df_trades)
    avg_profit = df_trades_copy['trade_result_pct'].mean()
    
    return {
        "sharpe_ratio": sharpe_ratio,
        "win_rate": win_rate,
        "avg_profit": avg_profit,
        "total_trades": len(df_trades_copy),
        "max_drawdown": max_drawdown,
    }
            
def simple_backtest_analysis(
    trades, 
    days,
    pair,
    tf, 
    general_info=True, 
    trades_info=False,
    days_info=False,
    long_short_info=False,
    entry_exit_info=False,
    indepedant_trade=True
):
    df_trades = trades.copy()
    df_days = days.copy().loc[df_trades.index.values[0] - np.timedelta64(1,'D'):]
    
    if df_trades.empty:
        raise Exception("No trades found")
    if df_days.empty:
        raise Exception("No days found")
    
    df_days['evolution'] = df_days['wallet'].diff()
    df_days['daily_return'] = df_days['evolution']/df_days['wallet'].shift(1)
    
    df_trades['trade_result'] = df_trades["close_trade_size"] - df_trades["open_trade_size"] - df_trades["open_fee"]
    df_trades['trade_result_pct'] = df_trades['trade_result']/df_trades["open_trade_size"]
    df_trades['trade_result_pct_wallet'] = df_trades['trade_result']/(df_trades["wallet"]+df_trades["trade_result"])
    if indepedant_trade:
        result_to_use = "trade_result_pct"
    else:
        result_to_use = "trade_result_pct_wallet"
    
    df_trades['trades_duration'] = df_trades['close_date'] - df_trades['open_date']
    
    df_trades['wallet_ath'] = df_trades['wallet'].cummax()
    df_trades['drawdown'] = df_trades['wallet_ath'] - df_trades['wallet']
    df_trades['drawdown_pct'] = df_trades['drawdown'] / df_trades['wallet_ath']
    df_days['wallet_ath'] = df_days['wallet'].cummax()
    df_days['drawdown'] = df_days['wallet_ath'] - df_days['wallet']
    df_days['drawdown_pct'] = df_days['drawdown'] / df_days['wallet_ath']
    
    good_trades = df_trades.loc[df_trades['trade_result'] > 0]
    if good_trades.empty:
        print("!!! No good trades found")
    bad_trades = df_trades.loc[df_trades['trade_result'] < 0]
    if bad_trades.empty:
        print("!!! No bad trades found")
    
    initial_wallet = df_days.iloc[0]["wallet"]
    total_trades = len(df_trades)
    total_days = len(df_days)
    if good_trades.empty:
        total_good_trades = 0
    else:
        total_good_trades = len(good_trades)
        
    avg_profit = df_trades[result_to_use].mean()  
     
    # Calculate trade statistics (handle empty dataframes)
    if not good_trades.empty:
        avg_profit_good_trades = good_trades[result_to_use].mean()
        mean_good_trades_duration = good_trades['trades_duration'].mean()
    else:
        avg_profit_good_trades = 0
        mean_good_trades_duration = pd.Timedelta(0)

    if not bad_trades.empty:
        avg_profit_bad_trades = bad_trades[result_to_use].mean()
        total_bad_trades = len(bad_trades)
        mean_bad_trades_duration = bad_trades['trades_duration'].mean()
    else:
        avg_profit_bad_trades = 0
        total_bad_trades = 0
        mean_bad_trades_duration = pd.Timedelta(0)  
    
    global_win_rate = total_good_trades / total_trades
    max_trades_drawdown = df_trades['drawdown_pct'].max()
    max_days_drawdown = df_days['drawdown_pct'].max()
    final_wallet = df_days.iloc[-1]['wallet']
    buy_and_hold_pct = (df_days.iloc[-1]['price'] - df_days.iloc[0]['price']) / df_days.iloc[0]['price']
    buy_and_hold_wallet = initial_wallet + initial_wallet * buy_and_hold_pct
    vs_hold_pct = (final_wallet - buy_and_hold_wallet)/buy_and_hold_wallet
    vs_usd_pct = (final_wallet - initial_wallet)/initial_wallet
    sharpe_ratio = (365**0.5)*(df_days['daily_return'].mean()/df_days['daily_return'].std())
    mean_trades_duration = df_trades['trades_duration'].mean()
    mean_trades_per_days = total_trades/total_days
    total_fees = df_trades['open_fee'].sum() + df_trades['close_fee'].sum()
    
    best_trade = df_trades[result_to_use].max()
    best_trade_date1 =  str(df_trades.loc[df_trades[result_to_use] == best_trade].iloc[0]['open_date'])
    best_trade_date2 =  str(df_trades.loc[df_trades[result_to_use] == best_trade].iloc[0]['close_date'])
    worst_trade = df_trades[result_to_use].min()
    worst_trade_date1 =  str(df_trades.loc[df_trades[result_to_use] == worst_trade].iloc[0]['open_date'])
    worst_trade_date2 =  str(df_trades.loc[df_trades[result_to_use] == worst_trade].iloc[0]['close_date'])

    df_days["win_loose"] = 0
    df_days.loc[df_days['daily_return'] > 0, "win_loose"] = 1
    df_days.loc[df_days['daily_return'] < 0, "win_loose"] = -1
    trade_days = df_days.loc[df_days['win_loose'] != 0]
    grouper = (trade_days["win_loose"] != trade_days["win_loose"].shift()).cumsum()
    df_days['streak'] = trade_days["win_loose"].groupby(grouper).cumsum()
    df_days['streak'] = df_days['streak'].ffill(axis = 0)

    best_day = df_days.loc[df_days['daily_return'] == df_days['daily_return'].max()].iloc[0]
    worst_day = df_days.loc[df_days['daily_return'] == df_days['daily_return'].min()].iloc[0]
    worst_day_return = worst_day['daily_return']
    best_day_return = best_day['daily_return']
    worst_day_date = worst_day['day']
    best_day_date = best_day['day']
    best_streak = df_days.loc[df_days['streak'] == df_days['streak'].max()].iloc[0]
    worst_streak = df_days.loc[df_days['streak'] == df_days['streak'].min()].iloc[0]
    best_streak_date = best_streak['day']
    worst_streak_date = worst_streak['day']
    best_streak_number = best_streak['streak']
    worst_streak_number = worst_streak['streak']
    win_days_number = len(df_days.loc[df_days['win_loose'] == 1])
    loose_days_number = len(df_days.loc[df_days['win_loose'] == -1])
    neutral_days_number = len(df_days.loc[df_days['win_loose'] == 0])
    
    if general_info:
        table = [["Période", "{} -> {}".format(*[d.strftime("%d.%m.%Y") for d in [df_days.iloc[0]["day"], df_days.iloc[-1]["day"]]])],
        ["Portefeuille initial", "{:,.2f} $".format(initial_wallet)],
        [],
        ["Portefeuille final", "{:,.2f} $".format(final_wallet)],
        ["Performance vs US dollar", "{:,.2f} %".format(vs_usd_pct*100)],
        ["Pire Drawdown T|D", "-{}% | -{}%".format(round(max_trades_drawdown*100, 2), round(max_days_drawdown*100, 2))],
        ["Buy and hold performance", "{} %".format(round(buy_and_hold_pct*100,2))],
        ["Performance vs buy and hold", "{:,.2f} %".format(vs_hold_pct*100)],
        ["Nombre total de trades", "{}".format(total_trades)],
        ["Sharpe Ratio", "{}".format(round(sharpe_ratio,2))],
        ["Global Win rate", "{} %".format(round(global_win_rate*100, 2))],
        ["Profit moyen", "{} %".format(round(avg_profit*100, 2))],
        ["Total des frais", "{:,.2f} $".format(total_fees)],
        [],
        ["\033[92mMeilleur trade\033[0m","\033[92m+{:.2f} % le {} -> {}\033[0m".format(best_trade*100, best_trade_date1, best_trade_date2)],
        ["\033[91mPire trade\033[0m", "\033[91m{:.2f} % le {} -> {}\033[0m".format(worst_trade*100, worst_trade_date1, worst_trade_date2)]
        ]

    headers = ["Résultats backtest", pair + '('+ tf + ')']
    print(tabulate(table, headers, tablefmt="fancy_outline"))
    
    if trades_info:
        print("\n--- Trades Information ---")
        print(f"Mean Trades per day: {round(mean_trades_per_days, 2)}")
        # print(f"Mean Trades Duration: {mean_trades_duration.days}d {mean_trades_duration.hour}:{mean_trades_duration.minutes}")
        print(f"Best trades: +{round(best_trade*100, 2)} % the {best_trade_date1} -> {best_trade_date2}")
        print(f"Worst trades: {round(worst_trade*100, 2)} % the {worst_trade_date1} -> {worst_trade_date2}")
        try:
            print(f"Total Good trades on the period: {total_good_trades}")
            print(f"Total Bad trades on the period: {total_bad_trades}")
            print(f"Average Good Trades result: {round(avg_profit_good_trades*100, 2)} %")
            print(f"Average Bad Trades result: {round(avg_profit_bad_trades*100, 2)} %")
            print(f"Mean Good Trades Duration: {mean_good_trades_duration}")
            print(f"Mean Bad Trades Duration: {mean_bad_trades_duration}")
        except Exception as e: 
            pass

    if days_info:
        print("\n--- Days Informations ---")
        print(f"Total: {len(df_days)} days recorded")
        print(f"Winning days: {win_days_number} days ({round(100*win_days_number/len(df_days), 2)}%)")
        print(f"Neutral days: {neutral_days_number} days ({round(100*neutral_days_number/len(df_days), 2)}%)")
        print(f"Loosing days: {loose_days_number} days ({round(100*loose_days_number/len(df_days), 2)}%)")
        print(f"Longest winning streak: {round(best_streak_number)} days ({best_streak_date})")
        print(f"Longest loosing streak: {round(-worst_streak_number)} days ({worst_streak_date})")
        print(f"Best day: {best_day_date} (+{round(best_day_return*100, 2)}%)")
        print(f"Worst day: {worst_day_date} ({round(worst_day_return*100, 2)}%)")
        
    if long_short_info:
        long_trades = df_trades.loc[df_trades['position'] == "LONG"]
        short_trades = df_trades.loc[df_trades['position'] == "SHORT"]
        if long_trades.empty or short_trades.empty:
            print("!!! No long or short trades found")
        else:
            total_long_trades = len(long_trades)
            total_short_trades = len(short_trades)
            good_long_trades = long_trades.loc[long_trades['trade_result'] > 0]
            good_short_trades = short_trades.loc[short_trades['trade_result'] > 0]
            if good_long_trades.empty: 
                total_good_long_trades = 0
            else:
                total_good_long_trades = len(good_long_trades)
            if good_short_trades.empty: 
                total_good_short_trades = 0
            else:
                total_good_short_trades = len(good_short_trades)
            long_win_rate = total_good_long_trades / total_long_trades
            short_win_rate = total_good_short_trades / total_short_trades
            long_average_profit = long_trades[result_to_use].mean()
            short_average_profit = short_trades[result_to_use].mean()
            print("\n--- " + "LONG informations" + " ---")
            print(f"Total LONG trades on the period: {total_long_trades}")
            print(f"LONG Win rate: {round(long_win_rate*100, 2)} %")
            print(f"Average LONG Profit: {round(long_average_profit*100, 2)} %")
            print("\n--- " + "SHORT informations" + " ---")
            print(f"Total SHORT trades on the period: {total_short_trades}")
            print(f"SHORT Win rate: {round(short_win_rate*100, 2)} %")
            print(f"Average SHORT Profit: {round(short_average_profit*100, 2)} %")
    
    if entry_exit_info:
        print("\n" + "-" * 16 + " Entries " + "-" * 16)
        total_entries = len(df_trades)
        open_dict = df_trades.groupby("position")["open_reason"].value_counts().to_dict()
        for entry in open_dict:
            print(
                "{:<25s}{:>15s}".format(
                    entry[0] + " - " + entry[1],
                    str(open_dict[entry])
                    + " ("
                    + str(round(100 * open_dict[entry] / total_entries, 1))
                    + "%)",
                )
            )
        print("-" * 17 + " Exits " + "-" * 17)
        total_exits = len(df_trades)
        close_dict = df_trades.groupby("position")["close_reason"].value_counts().to_dict()
        for entry in close_dict:
            print(
                "{:<25s}{:>15s}".format(
                    entry[0] + " - " + entry[1],
                    str(close_dict[entry])
                    + " ("
                    + str(round(100 * close_dict[entry] / total_entries, 1))
                    + "%)",
                )
            )
        print("-" * 40)

    return df_trades, df_days

def multi_backtest_analysis(
    trades, 
    days,
    leverage=1, 
    general_info=True, 
    trades_info=False,
    days_info=False,
    long_short_info=False,
    entry_exit_info=False,
    pair_info=False,
    exposition_info=False,
    indepedant_trade=True
):
    df_trades = trades.copy()
    df_days = days.copy().loc[df_trades.index.values[0] - np.timedelta64(1,'D'):]
    
    if df_trades.empty:
        raise Exception("No trades found")
    if df_days.empty:
        raise Exception("No days found")
    
    df_days['evolution'] = df_days['wallet'].diff()
    df_days['daily_return'] = df_days['evolution']/df_days['wallet'].shift(1)
    df_days['total_exposition'] = df_days['long_exposition']+df_days['short_exposition']
    
    df_trades['trade_result'] = df_trades["close_trade_size"] - df_trades["open_trade_size"] - df_trades["open_fee"]
    df_trades['trade_result_pct'] = df_trades['trade_result']/df_trades["open_trade_size"]
    df_trades['trade_result_pct_wallet'] = df_trades['trade_result']/(df_trades["wallet"]+df_trades["trade_result"])
    if indepedant_trade:
        result_to_use = "trade_result_pct"
    else:
        result_to_use = "trade_result_pct_wallet"
    
    df_trades['trades_duration'] = df_trades['close_date'] - df_trades['open_date']
    
    df_trades['wallet_ath'] = df_trades['wallet'].cummax()
    df_trades['drawdown'] = df_trades['wallet_ath'] - df_trades['wallet']
    df_trades['drawdown_pct'] = df_trades['drawdown'] / df_trades['wallet_ath']
    df_days['wallet_ath'] = df_days['wallet'].cummax()
    df_days['drawdown'] = df_days['wallet_ath'] - df_days['wallet']
    df_days['drawdown_pct'] = df_days['drawdown'] / df_days['wallet_ath']
    
    good_trades = df_trades.loc[df_trades['trade_result'] > 0]
    if good_trades.empty:
        print("!!! No good trades found")
    bad_trades = df_trades.loc[df_trades['trade_result'] < 0]
    if bad_trades.empty:
        print("!!! No bad trades found")
    
    initial_wallet = df_days.iloc[0]["wallet"]
    total_trades = len(df_trades)
    total_days = len(df_days)
    if good_trades.empty:
        total_good_trades = 0
    else:
        total_good_trades = len(good_trades)
        
    avg_profit = df_trades[result_to_use].mean()  
     
    # Calculate trade statistics (handle empty dataframes)
    if not good_trades.empty:
        avg_profit_good_trades = good_trades[result_to_use].mean()
        mean_good_trades_duration = good_trades['trades_duration'].mean()
    else:
        avg_profit_good_trades = 0
        mean_good_trades_duration = pd.Timedelta(0)

    if not bad_trades.empty:
        avg_profit_bad_trades = bad_trades[result_to_use].mean()
        total_bad_trades = len(bad_trades)
        mean_bad_trades_duration = bad_trades['trades_duration'].mean()
    else:
        avg_profit_bad_trades = 0
        total_bad_trades = 0
        mean_bad_trades_duration = pd.Timedelta(0)  
    
    global_win_rate = total_good_trades / total_trades
    max_trades_drawdown = df_trades['drawdown_pct'].max()
    max_days_drawdown = df_days['drawdown_pct'].max()
    mean_drawdown = df_days['drawdown_pct'].mean()
    final_wallet = df_days.iloc[-1]['wallet']
    buy_and_hold_pct = (df_days.iloc[-1]['price'] - df_days.iloc[0]['price']) / df_days.iloc[0]['price']
    buy_and_hold_wallet = initial_wallet + initial_wallet * buy_and_hold_pct
    vs_hold_pct = (final_wallet - buy_and_hold_wallet)/buy_and_hold_wallet
    vs_usd_pct = (final_wallet - initial_wallet)/initial_wallet
    sharpe_ratio = (365**0.5)*(df_days['daily_return'].mean()/df_days['daily_return'].std())
    sortino_ratio = 365**0.5 * (df_days["daily_return"].mean() / df_days["daily_return"][df_days["daily_return"] < 0].std())
    calmar_ratio = (df_days["daily_return"].mean()*365) / max_days_drawdown
    mean_trades_duration = df_trades['trades_duration'].mean()
    mean_trades_per_days = total_trades/total_days
    total_fees = df_trades['open_fee'].sum() + df_trades['close_fee'].sum()
    
    best_trade = df_trades[result_to_use].max()
    best_trade_date1 =  str(df_trades.loc[df_trades[result_to_use] == best_trade].iloc[0]['open_date'])
    best_trade_date2 =  str(df_trades.loc[df_trades[result_to_use] == best_trade].iloc[0]['close_date'])
    best_trade_pair =  str(df_trades.loc[df_trades[result_to_use] == best_trade].iloc[0]['pair'])
    worst_trade = df_trades[result_to_use].min()
    worst_trade_date1 =  str(df_trades.loc[df_trades[result_to_use] == worst_trade].iloc[0]['open_date'])
    worst_trade_date2 =  str(df_trades.loc[df_trades[result_to_use] == worst_trade].iloc[0]['close_date'])
    worst_trade_pair =  str(df_trades.loc[df_trades[result_to_use] == worst_trade].iloc[0]['pair'])

    df_days["win_loose"] = 0
    df_days.loc[df_days['daily_return'] > 0, "win_loose"] = 1
    df_days.loc[df_days['daily_return'] < 0, "win_loose"] = -1
    trade_days = df_days.loc[df_days['win_loose'] != 0]
    grouper = (trade_days["win_loose"] != trade_days["win_loose"].shift()).cumsum()
    df_days['streak'] = trade_days["win_loose"].groupby(grouper).cumsum()
    df_days['streak'] = df_days['streak'].ffill(axis = 0)

    best_day = df_days.loc[df_days['daily_return'] == df_days['daily_return'].max()].iloc[0]
    worst_day = df_days.loc[df_days['daily_return'] == df_days['daily_return'].min()].iloc[0]
    worst_day_return = worst_day['daily_return']
    best_day_return = best_day['daily_return']
    worst_day_date = worst_day['day']
    best_day_date = best_day['day']
    best_streak = df_days.loc[df_days['streak'] == df_days['streak'].max()].iloc[0]
    worst_streak = df_days.loc[df_days['streak'] == df_days['streak'].min()].iloc[0]
    best_streak_date = best_streak['day']
    worst_streak_date = worst_streak['day']
    best_streak_number = best_streak['streak']
    worst_streak_number = worst_streak['streak']
    win_days_number = len(df_days.loc[df_days['win_loose'] == 1])
    loose_days_number = len(df_days.loc[df_days['win_loose'] == -1])
    neutral_days_number = len(df_days.loc[df_days['win_loose'] == 0])

    mean_exposition = df_days['total_exposition'].mean()
    max_exposition = df_days['total_exposition'].max()
    max_long_exposition = df_days['long_exposition'].max()
    max_short_exposition = df_days['short_exposition'].max()
    
    if general_info:
        table_general = [["Période", "{} -> {}".format(*[d.strftime("%d.%m.%Y") for d in [df_days.iloc[0]["day"], df_days.iloc[-1]["day"]]])],
        ["Portefeuille initial", "{:,.2f} $  (levier x{})".format(initial_wallet, leverage)],
        [],
        ["Portefeuille final", "{:,.2f} $".format(final_wallet)],
        ["Performance vs US dollar", "{:,.2f} %".format(vs_usd_pct*100)],
        ["Pire Drawdown T|D", "-{} % | -{} %".format(round(max_trades_drawdown*100, 2), round(max_days_drawdown*100, 2))],
        ["Moyenne journalière Drawdown", "-{} %".format(round(mean_drawdown*100, 2))],
        ["Buy and hold performance", "{} %".format(round(buy_and_hold_pct*100,2))],
        ["Performance vs buy and hold", "{:,.2f} %".format(vs_hold_pct*100)],
        ["Nombre total de trades", "{}".format(total_trades)],
        ["Sharpe | Sortino | Calmar Ratio", "{} | {} | {}".format(round(sharpe_ratio,2), round(sortino_ratio,2), round(calmar_ratio,2))],
        ["Global Win rate", "{} %".format(round(global_win_rate*100, 2))],
        ["Profit moyen", "{} %".format(round(avg_profit*100, 2))],
        ["Total des frais", "{:,.2f} $".format(total_fees)],
        ]

        headers = ["Informations générales", ""]
        print(tabulate(table_general, headers, tablefmt="fancy_outline"))

    if trades_info:
        table_trades = [["Moyenne trades par jour", "{}".format(round(mean_trades_per_days, 2))],
        ["Moyenne temps trades", "{}".format(mean_trades_duration)],      
        ["\033[92mMeilleur trade\033[0m","\033[92m+{:.2f} % le {} -> {}\033[0m".format(best_trade*100, best_trade_date1, best_trade_date2, best_trade_pair)],
        ["\033[91mPire trade\033[0m", "\033[91m{:.2f} % le {} -> {}\033[0m".format(worst_trade*100, worst_trade_date1, worst_trade_date2, worst_trade_pair)],
        ]
        try:
            table_trades = table_trades + [["Total bons trades sur la période", "{}".format(total_good_trades)],
            ["Total mauvais trades sur la période", "{}".format(total_bad_trades)],
            ["Résultat moyen des bons trades", "{} %".format(round(avg_profit_good_trades*100, 2))],
            ["Résultat moyen des mauvais trades", "{} %".format(round(avg_profit_bad_trades*100, 2))],
            ["Durée moyenne des bons trades", "{}".format(mean_good_trades_duration)],
            ["Durée moyenne des mauvais trades", "{}".format(mean_bad_trades_duration)],
            ]
        except Exception as e:
            pass
        
        headers = ["Trades", ""]
        print(tabulate(table_trades, headers, tablefmt="fancy_outline"))

    if days_info:
        table_days = [
        ["Total", "{} jours enregistrés".format(len(df_days))],
        ["Jours gagnants", "{} jours ({} %)".format(win_days_number, round(100*win_days_number/len(df_days), 2))],
        ["Jours neutres", "{} jours ({} %)".format(neutral_days_number, round(100*neutral_days_number/len(df_days), 2))],
        ["Jours perdants", "{} jours ({} %)".format(loose_days_number, round(100*loose_days_number/len(df_days), 2))],
        ["Plus longue série de victoires", "{} jours ({})".format(round(best_streak_number), best_streak_date)],
        ["Plus longue série de défaites", "{} jours ({})".format(round(-worst_streak_number), worst_streak_date)],
        ["Meilleur jour", "{} (+{} %)".format(best_day_date, round(best_day_return*100, 2))],
        ["Pire jour", "{} ({} %)".format(worst_day_date, round(worst_day_return*100, 2))],
        ]
        
        headers = ["Jours", ""]
        print(tabulate(table_days, headers, tablefmt="fancy_outline"))

    if exposition_info:
        table_exposition = [
        ["Exposition moyenne", "{}".format(round(mean_exposition, 2))],
        ["Exposition max", "{}".format(round(max_exposition, 2))],
        ["Exposition max Long", "{}".format(round(max_long_exposition, 2))],
        ["Exposition max Short", "{}".format(round(max_short_exposition, 2))],
        ]
        # Note: VAR metrics (mean_risk, max_risk, min_risk) are not currently calculated
        # TODO: Implement VAR metrics calculation if needed

        headers = ["Exposition", ""]
        print(tabulate(table_exposition, headers, tablefmt="fancy_outline"))
        
    if long_short_info:
        long_trades = df_trades.loc[df_trades['position'] == "LONG"]
        short_trades = df_trades.loc[df_trades['position'] == "SHORT"]
        if long_trades.empty or short_trades.empty:
            print("!!! No long or short trades found")
        else:
            total_long_trades = len(long_trades)
            total_short_trades = len(short_trades)
            good_long_trades = long_trades.loc[long_trades['trade_result'] > 0]
            good_short_trades = short_trades.loc[short_trades['trade_result'] > 0]
            if good_long_trades.empty: 
                total_good_long_trades = 0
            else:
                total_good_long_trades = len(good_long_trades)
            if good_short_trades.empty: 
                total_good_short_trades = 0
            else:
                total_good_short_trades = len(good_short_trades)
            long_win_rate = total_good_long_trades / total_long_trades
            short_win_rate = total_good_short_trades / total_short_trades
            long_average_profit = long_trades[result_to_use].mean()
            short_average_profit = short_trades[result_to_use].mean()
            print("\n" + "-"*14 + "LONG informations" + "-" *14)
            print(f"Total LONG trades sur la periode: {total_long_trades}")
            print(f"LONG Win rate: {round(long_win_rate*100, 2)} %")
            print(f"Bénéfice moyen LONG: {round(long_average_profit*100, 2)} %")
            print("-" * 45)
            print("\n" + "-" *13 + "SHORT informations" + "-" *14)
            print(f"Total SHORT trades sur la période: {total_short_trades}")
            print(f"SHORT Win rate: {round(short_win_rate*100, 2)} %")
            print(f"Bénéfice moyen SHORT: {round(short_average_profit*100, 2)} %")
            print("-" * 45)
    
    if entry_exit_info:
        print("\n" + "-" * 16 + " Entrées " + "-" * 16)
        total_entries = len(df_trades)
        open_dict = df_trades.groupby("position")["open_reason"].value_counts().to_dict()
        for entry in open_dict:
            print(
                "{:<25s}{:>15s}".format(
                    entry[0] + " - " + entry[1],
                    str(open_dict[entry])
                    + " ("
                    + str(round(100 * open_dict[entry] / total_entries, 1))
                    + "%)",
                )
            )
        print("-" * 16 + " Sorties " + "-" * 16)
        total_exits = len(df_trades)
        close_dict = df_trades.groupby("position")["close_reason"].value_counts().to_dict()
        for entry in close_dict:
            print(
                "{:<25s}{:>15s}".format(
                    entry[0] + " - " + entry[1],
                    str(close_dict[entry])
                    + " ("
                    + str(round(100 * close_dict[entry] / total_entries, 1))
                    + "%)",
                )
            )
        print("-" * 40)

    if pair_info:
        print("\n--- Pair Result ---")
        table_pair = []
        for pair in df_trades["pair"].unique():
            df_pair = df_trades.loc[df_trades["pair"] == pair]
            pair_total_trades = len(df_pair)
            pair_good_trades = len(df_pair.loc[df_pair["trade_result"] > 0])
            pair_worst_trade = str(round(df_pair["trade_result_pct"].min() * 100, 2))+' %'
            pair_best_trade = str(round(df_pair["trade_result_pct"].max() * 100, 2))+' %'
            pair_win_rate = str(round((pair_good_trades / pair_total_trades) * 100, 2))+' %'
            pair_sum_result = str(round(df_pair["trade_result_pct"].sum() * 100, 2))+' %'
            pair_avg_result = str(round(df_pair["trade_result_pct"].mean() * 100, 2))+' %'
            table_pair.append([
                pair_total_trades, pair, pair_sum_result, pair_avg_result, pair_worst_trade, pair_best_trade, pair_win_rate
            ])
            
        # Trier d'abord par Sum-result, puis par Win-rate en cas d'égalité
        table_pair_sorted = sorted(table_pair, key=lambda x: (float(x[2].replace('%', '')), float(x[6].replace('%', ''))), reverse=True)

        headers = ["Trades","Pair","Sum-result","Mean-trade","Worst-trade","Best-trade","Win-rate"]
        print(tabulate(table_pair_sorted, headers, tablefmt="fancy_outline"))

    return df_trades, df_days

def backtest_analysis_gui(self,
    trades, 
    days, 
    general_info=True, 
    trades_info=False,
    days_info=False,
    long_short_info=False,
    entry_exit_info=False,
    pair_info=False,
    exposition_info=False,
    indepedant_trade=True
):
    df_trades = trades.copy()
    df_days = days.copy().loc[df_trades.index.values[0] - np.timedelta64(1,'D'):]
    
    if df_trades.empty:
        raise Exception("No trades found")
    if df_days.empty:
        raise Exception("No days found")
    
    df_days['evolution'] = df_days['wallet'].diff()
    df_days['daily_return'] = df_days['evolution']/df_days['wallet'].shift(1)
    df_days['total_exposition'] = df_days['long_exposition']+df_days['short_exposition']
    
    df_trades['trade_result'] = df_trades["close_trade_size"] - df_trades["open_trade_size"] - df_trades["open_fee"]
    df_trades['trade_result_pct'] = df_trades['trade_result']/df_trades["open_trade_size"]
    df_trades['trade_result_pct_wallet'] = df_trades['trade_result']/(df_trades["wallet"]+df_trades["trade_result"])
    if indepedant_trade:
        result_to_use = "trade_result_pct"
    else:
        result_to_use = "trade_result_pct_wallet"
    
    df_trades['trades_duration'] = df_trades['close_date'] - df_trades['open_date']
    
    df_trades['wallet_ath'] = df_trades['wallet'].cummax()
    df_trades['drawdown'] = df_trades['wallet_ath'] - df_trades['wallet']
    df_trades['drawdown_pct'] = df_trades['drawdown'] / df_trades['wallet_ath']
    df_days['wallet_ath'] = df_days['wallet'].cummax()
    df_days['drawdown'] = df_days['wallet_ath'] - df_days['wallet']
    df_days['drawdown_pct'] = df_days['drawdown'] / df_days['wallet_ath']
    
    good_trades = df_trades.loc[df_trades['trade_result'] > 0]
    if good_trades.empty:
        print("!!! No good trades found")
    bad_trades = df_trades.loc[df_trades['trade_result'] < 0]
    if bad_trades.empty:
        print("!!! No bad trades found")
    
    initial_wallet = df_days.iloc[0]["wallet"]
    total_trades = len(df_trades)
    total_days = len(df_days)
    if good_trades.empty:
        total_good_trades = 0
    else:
        total_good_trades = len(good_trades)
        
    avg_profit = df_trades[result_to_use].mean()  
     
    # Calculate trade statistics (handle empty dataframes)
    if not good_trades.empty:
        avg_profit_good_trades = good_trades[result_to_use].mean()
        mean_good_trades_duration = good_trades['trades_duration'].mean()
    else:
        avg_profit_good_trades = 0
        mean_good_trades_duration = pd.Timedelta(0)

    if not bad_trades.empty:
        avg_profit_bad_trades = bad_trades[result_to_use].mean()
        total_bad_trades = len(bad_trades)
        mean_bad_trades_duration = bad_trades['trades_duration'].mean()
    else:
        avg_profit_bad_trades = 0
        total_bad_trades = 0
        mean_bad_trades_duration = pd.Timedelta(0)  
    
    global_win_rate = total_good_trades / total_trades
    max_trades_drawdown = df_trades['drawdown_pct'].max()
    max_days_drawdown = df_days['drawdown_pct'].max()
    mean_drawdown = df_days['drawdown_pct'].mean()
    final_wallet = df_days.iloc[-1]['wallet']
    buy_and_hold_pct = (df_days.iloc[-1]['price'] - df_days.iloc[0]['price']) / df_days.iloc[0]['price']
    buy_and_hold_wallet = initial_wallet + initial_wallet * buy_and_hold_pct
    vs_hold_pct = (final_wallet - buy_and_hold_wallet)/buy_and_hold_wallet
    vs_usd_pct = (final_wallet - initial_wallet)/initial_wallet
    sharpe_ratio = (365**0.5)*(df_days['daily_return'].mean()/df_days['daily_return'].std())
    sortino_ratio = 365**0.5 * (df_days["daily_return"].mean() / df_days["daily_return"][df_days["daily_return"] < 0].std())
    calmar_ratio = (df_days["daily_return"].mean()*365) / max_days_drawdown
    mean_trades_duration = df_trades['trades_duration'].mean()
    mean_trades_per_days = total_trades/total_days
    total_fees = df_trades['open_fee'].sum() + df_trades['close_fee'].sum()
    
    best_trade = df_trades[result_to_use].max()
    best_trade_date1 =  str(df_trades.loc[df_trades[result_to_use] == best_trade].iloc[0]['open_date'])
    best_trade_date2 =  str(df_trades.loc[df_trades[result_to_use] == best_trade].iloc[0]['close_date'])
    best_trade_pair =  str(df_trades.loc[df_trades[result_to_use] == best_trade].iloc[0]['pair'])
    worst_trade = df_trades[result_to_use].min()
    worst_trade_date1 =  str(df_trades.loc[df_trades[result_to_use] == worst_trade].iloc[0]['open_date'])
    worst_trade_date2 =  str(df_trades.loc[df_trades[result_to_use] == worst_trade].iloc[0]['close_date'])
    worst_trade_pair =  str(df_trades.loc[df_trades[result_to_use] == worst_trade].iloc[0]['pair'])

    df_days["win_loose"] = 0
    df_days.loc[df_days['daily_return'] > 0, "win_loose"] = 1
    df_days.loc[df_days['daily_return'] < 0, "win_loose"] = -1
    trade_days = df_days.loc[df_days['win_loose'] != 0]
    grouper = (trade_days["win_loose"] != trade_days["win_loose"].shift()).cumsum()
    df_days['streak'] = trade_days["win_loose"].groupby(grouper).cumsum()
    df_days['streak'] = df_days['streak'].ffill(axis = 0)

    best_day = df_days.loc[df_days['daily_return'] == df_days['daily_return'].max()].iloc[0]
    worst_day = df_days.loc[df_days['daily_return'] == df_days['daily_return'].min()].iloc[0]
    worst_day_return = worst_day['daily_return']
    best_day_return = best_day['daily_return']
    worst_day_date = worst_day['day']
    best_day_date = best_day['day']
    best_streak = df_days.loc[df_days['streak'] == df_days['streak'].max()].iloc[0]
    worst_streak = df_days.loc[df_days['streak'] == df_days['streak'].min()].iloc[0]
    best_streak_date = best_streak['day']
    worst_streak_date = worst_streak['day']
    best_streak_number = best_streak['streak']
    worst_streak_number = worst_streak['streak']
    win_days_number = len(df_days.loc[df_days['win_loose'] == 1])
    loose_days_number = len(df_days.loc[df_days['win_loose'] == -1])
    neutral_days_number = len(df_days.loc[df_days['win_loose'] == 0])

    mean_exposition = df_days['total_exposition'].mean()
    max_exposition = df_days['total_exposition'].max()
    max_long_exposition = df_days['long_exposition'].max()
    max_short_exposition = df_days['short_exposition'].max()
    
    if general_info:
        table_general = [["Période", "{} -> {}".format(*[d.strftime("%d.%m.%Y") for d in [df_days.iloc[0]["day"], df_days.iloc[-1]["day"]]])],
        ["Portefeuille initial", "{:,.2f} $".format(initial_wallet)],
        [],
        ["Portefeuille final", "{:,.2f} $".format(final_wallet)],
        ["Performance vs US dollar", "{:,.2f} %".format(vs_usd_pct*100)],
        ["Pire Drawdown T|D", "-{} % | -{} %".format(round(max_trades_drawdown*100, 2), round(max_days_drawdown*100, 2))],
        ["Moyenne journalière Drawdown", "-{} %".format(round(mean_drawdown*100, 2))],
        ["Buy and hold performance", "{} %".format(round(buy_and_hold_pct*100,2))],
        ["Performance vs buy and hold", "{:,.2f} %".format(vs_hold_pct*100)],
        ["Nombre total de trades", "{}".format(total_trades)],
        ["Sharpe | Sortino | Calmar Ratio", "{} | {} | {}".format(round(sharpe_ratio,2), round(sortino_ratio,2), round(calmar_ratio,2))],
        ["Global Win rate", "{} %".format(round(global_win_rate*100, 2))],
        ["Profit moyen", "{} %".format(round(avg_profit*100, 2))],
        ["Total des frais", "{:,.2f} $".format(total_fees)],
        ]

        headers = ["Informations générales", ""]
        self.textbox.insert("0.0", tabulate(table_general, headers, tablefmt="fancy_outline"))

    if trades_info:
        table_trades = [["Moyenne trades par jour", "{}".format(round(mean_trades_per_days, 2))],
        ["Moyenne temps trades", "{}".format(mean_trades_duration)],      
        ["Meilleur trade","+{:.2f} % le {} -> {} ({})".format(best_trade*100, best_trade_date1, best_trade_date2, best_trade_pair)],
        ["Pire trade", "{:.2f} % le {} -> {} ({})".format(worst_trade*100, worst_trade_date1, worst_trade_date2, worst_trade_pair)],
        ]
        try:
            table_trades = table_trades + [["Total bons trades sur la période", "{}".format(total_good_trades)],
            ["Total mauvais trades sur la période", "{}".format(total_bad_trades)],
            ["Résultat moyen des bons trades", "{} %".format(round(avg_profit_good_trades*100, 2))],
            ["Résultat moyen des mauvais trades", "{} %".format(round(avg_profit_bad_trades*100, 2))],
            ["Durée moyenne des bons trades", "{}".format(mean_good_trades_duration)],
            ["Durée moyenne des mauvais trades", "{}".format(mean_bad_trades_duration)],
            ]
        except Exception as e:
            pass
        
        headers = ["Trades", ""]
        self.textbox.insert("0.0", tabulate(table_trades, headers, tablefmt="fancy_outline"))

    if days_info:
        table_days = [
        ["Total", "{} jours enregistrés".format(len(df_days))],
        ["Jours gagnants", "{} jours ({} %)".format(win_days_number, round(100*win_days_number/len(df_days), 2))],
        ["Jours neutres", "{} jours ({} %)".format(neutral_days_number, round(100*neutral_days_number/len(df_days), 2))],
        ["Jours perdants", "{} jours ({} %)".format(loose_days_number, round(100*loose_days_number/len(df_days), 2))],
        ["Plus longue série de victoires", "{} jours ({})".format(round(best_streak_number), best_streak_date)],
        ["Plus longue série de défaites", "{} jours ({})".format(round(-worst_streak_number), worst_streak_date)],
        ["Meilleur jour", "{} (+{} %)".format(best_day_date, round(best_day_return*100, 2))],
        ["Pire jour", "{} ({} %)".format(worst_day_date, round(worst_day_return*100, 2))],
        ]
        
        headers = ["Jours", ""]
        self.textbox.insert("0.0", tabulate(table_days, headers, tablefmt="fancy_outline"))

    if exposition_info:
        table_exposition = [
        ["Exposition moyenne", "{}".format(round(mean_exposition, 2))],
        ["Exposition max", "{}".format(round(max_exposition, 2))],
        ["Exposition max Long", "{}".format(round(max_long_exposition, 2))],
        ["Exposition max Short", "{}".format(round(max_short_exposition, 2))],
        ]
        # Note: VAR metrics (mean_risk, max_risk, min_risk) are not currently calculated
        # TODO: Implement VAR metrics calculation if needed

        headers = ["Exposition", ""]
        self.textbox.insert("0.0", tabulate(table_exposition, headers, tablefmt="fancy_outline"))
        
    if long_short_info:
        long_trades = df_trades.loc[df_trades['position'] == "LONG"]
        short_trades = df_trades.loc[df_trades['position'] == "SHORT"]
        if long_trades.empty or short_trades.empty:
            print("!!! No long or short trades found")
        else:
            total_long_trades = len(long_trades)
            total_short_trades = len(short_trades)
            good_long_trades = long_trades.loc[long_trades['trade_result'] > 0]
            good_short_trades = short_trades.loc[short_trades['trade_result'] > 0]
            if good_long_trades.empty: 
                total_good_long_trades = 0
            else:
                total_good_long_trades = len(good_long_trades)
            if good_short_trades.empty: 
                total_good_short_trades = 0
            else:
                total_good_short_trades = len(good_short_trades)
            long_win_rate = total_good_long_trades / total_long_trades
            short_win_rate = total_good_short_trades / total_short_trades
            long_average_profit = long_trades[result_to_use].mean()
            short_average_profit = short_trades[result_to_use].mean()
            print("\n" + "-"*14 + "LONG informations" + "-" *14)
            print(f"Total LONG trades sur la periode: {total_long_trades}")
            print(f"LONG Win rate: {round(long_win_rate*100, 2)} %")
            print(f"Bénéfice moyen LONG: {round(long_average_profit*100, 2)} %")
            print("-" * 45)
            print("\n" + "-" *13 + "SHORT informations" + "-" *14)
            print(f"Total SHORT trades sur la période: {total_short_trades}")
            print(f"SHORT Win rate: {round(short_win_rate*100, 2)} %")
            print(f"Bénéfice moyen SHORT: {round(short_average_profit*100, 2)} %")
            print("-" * 45)
    
    if entry_exit_info:
        print("\n" + "-" * 16 + " Entrées " + "-" * 16)
        total_entries = len(df_trades)
        open_dict = df_trades.groupby("position")["open_reason"].value_counts().to_dict()
        for entry in open_dict:
            print(
                "{:<25s}{:>15s}".format(
                    entry[0] + " - " + entry[1],
                    str(open_dict[entry])
                    + " ("
                    + str(round(100 * open_dict[entry] / total_entries, 1))
                    + "%)",
                )
            )
        print("-" * 16 + " Sorties " + "-" * 16)
        total_exits = len(df_trades)
        close_dict = df_trades.groupby("position")["close_reason"].value_counts().to_dict()
        for entry in close_dict:
            print(
                "{:<25s}{:>15s}".format(
                    entry[0] + " - " + entry[1],
                    str(close_dict[entry])
                    + " ("
                    + str(round(100 * close_dict[entry] / total_entries, 1))
                    + "%)",
                )
            )
        print("-" * 40)

    if pair_info:
        print("\n--- Pair Result ---")
        table_pair = []
        for pair in df_trades["pair"].unique():
            df_pair = df_trades.loc[df_trades["pair"] == pair]
            pair_total_trades = len(df_pair)
            pair_good_trades = len(df_pair.loc[df_pair["trade_result"] > 0])
            pair_worst_trade = str(round(df_pair["trade_result_pct"].min() * 100, 2))+' %'
            pair_best_trade = str(round(df_pair["trade_result_pct"].max() * 100, 2))+' %'
            pair_win_rate = str(round((pair_good_trades / pair_total_trades) * 100, 2))+' %'
            pair_sum_result = str(round(df_pair["trade_result_pct"].sum() * 100, 2))+' %'
            pair_avg_result = str(round(df_pair["trade_result_pct"].mean() * 100, 2))+' %'
            table_pair.append([
                pair_total_trades, pair, pair_sum_result, pair_avg_result, pair_worst_trade, pair_best_trade, pair_win_rate
            ])

        headers = ["Trades","Pair","Sum-result","Mean-trade","Worst-trade","Best-trade","Win-rate"]
        self.textbox.insert("0.0", tabulate(table_pair, headers, tablefmt="fancy_outline"))

    return df_trades, df_days
