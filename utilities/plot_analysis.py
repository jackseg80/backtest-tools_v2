import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import datetime
import numpy as np
import random

def plot_bar_by_month(df_days):
    custom_palette = {}
    
    last_month = int(df_days.iloc[-1]['day'].month)
    last_year = int(df_days.iloc[-1]['day'].year)
    
    current_month = int(df_days.iloc[0]['day'].month)
    current_year = int(df_days.iloc[0]['day'].year)
    current_year_array = []
    while current_year < last_year or current_month-1 != last_month:
        date_string = str(current_year) + "-" + str(current_month)
        
        monthly_perf = (df_days.loc[date_string]['wallet'].iloc[-1] - df_days.loc[date_string]['wallet'].iloc[0]) / df_days.loc[date_string]['wallet'].iloc[0]
        monthly_row = {
            'date': str(datetime.date(1900, current_month, 1).strftime('%B')),
            'result': round(monthly_perf*100)
        }

        current_year_array.append(monthly_row)
        custom_palette = {'green': 'g', 'red': 'r'}
        if ((current_month == 12) or (current_month == last_month and current_year == last_year)):
            current_df = pd.DataFrame(current_year_array)
            current_df['color'] = ['green' if r >= 0 else 'red' for r in current_df['result']]
            fig, ax_left = plt.subplots(figsize=(12, 6))
            g = sns.barplot(ax=ax_left, data=current_df,x='date',y='result', hue='color', legend=False, palette=custom_palette)
            for index, row in current_df.iterrows():
                if row.result >= 0:
                    g.text(row.name,row.result, '+'+str(round(row.result))+'%', color='black', ha="center", va="bottom")
                else:
                    g.text(row.name,row.result, '-'+str(round(row.result))+'%', color='black', ha="center", va="top")
            
            year_result = (df_days.loc[str(current_year)]['wallet'].iloc[-1] - df_days.loc[str(current_year)]['wallet'].iloc[0]) / df_days.loc[str(current_year)]['wallet'].iloc[0]

            g.set_title(str(current_year) + ' performance in % (cumulative: ' + str(round(year_result*100,2)) + '%)')
            g.set(xlabel=current_year, ylabel='performance %')
            ax_left.axhline(y=0, color='black', alpha=0.5)

            print("----- " + str(current_year) +" Cumulative Performances: " + str(round(year_result*100,2)) + "% -----")
            plt.show()

            current_year_array = []
        
        current_month += 1
        if current_month > 12:
            if current_year == last_year:
                break
            current_month = 1
            current_year += 1

def plot_equity_vs_asset(df_days, pair, leverage=1, log=False):
    days = df_days.copy()
    coin = pair.split("/")[0]
    # print("-- Plotting equity vs asset and drawdown --")
    fig, ax_left = plt.subplots(figsize=(15, 20), nrows=4, ncols=1)

    ax_left[0].title.set_text("Courbe de capital stratégique")
    ax_left[0].plot(days['wallet'], color='royalblue', lw=1)
    if log:
        ax_left[0].set_yscale('log')
    ax_left[0].fill_between(days['wallet'].index, days['wallet'], alpha=0.2, color='royalblue')
    ax_left[0].axhline(y=days.iloc[0]['wallet'], color='black', alpha=0.3)
    ax_left[0].legend(['Evolution du portefeuille (capital)'], loc ="upper left")

    ax_left[1].title.set_text("Cours "+ coin)
    ax_left[1].plot(days['price'], color='sandybrown', lw=1)
    if log:
        ax_left[1].set_yscale('log')
    ax_left[1].fill_between(days['price'].index, days['price'], alpha=0.2, color='sandybrown')
    ax_left[1].axhline(y=days.iloc[0]['price'], color='black', alpha=0.3)
    ax_left[1].legend(["Evolution de l'actif"], loc ="upper left")

    liquidation = 1/leverage * 95
    max_drawdown= days['drawdown_pct'].max() * 100
    
    ax_left[2].title.set_text("Courbe du drawdown")
    ax_left[2].plot(-days['drawdown_pct']*100, color='indianred', lw=1, label='Drawdown en %')
    ax_left[2].fill_between(days['drawdown_pct'].index, -days['drawdown_pct']*100, alpha=0.2, color='indianred')
    ax_left[2].axhline(y=0, color='black', alpha=0.3)
    ax_left[2].axhline(y=-liquidation, color='red', linestyle='--', lw=1, label='Liquidation')
    ax_left[2].set_ylim([-max_drawdown * 1.1, 0])
    ax_left[2].legend(loc="lower left")

    ax_right = ax_left[3].twinx()
    if log:
        ax_left[3].set_yscale('log')
        ax_right.set_yscale('log')

    ax_left[3].title.set_text("Portefeuille VS " + coin + " (pas à la même échelle)")
    ax_left[3].set_yticks([])
    ax_right.set_yticks([])
    ax_left[3].plot(days['wallet'], color='royalblue', lw=1)
    ax_right.plot(days['price'], color='sandybrown', lw=1)
    ax_left[3].legend(['Evolution du portefeuille (capital)'], loc ="lower right")
    ax_right.legend(['Asset evolution'], loc ="upper left")

    plt.show()

def plot_trade_analysis(df_trades):
    trades = df_trades.copy()
    trades["trade_result_pct"] = trades["trade_result_pct"] * 100
    trades["Trades duration in days"] = trades["trades_duration"] / np.timedelta64(1, 'D')
    trades["0"] = 0
    trades["Trade result"] = "Bad Trade"
    trades.loc[trades["trade_result_pct"] > 0, "Trade result"] = "Good Trade"
    palette ={"Bad Trade": "red", "Good Trade": "green"}

    # print("-- Plotting equity vs asset --")
    fig, ax_left = plt.subplots(figsize=(15, 14), nrows=2, ncols=1)

    ax_left[0].title.set_text("Trade result over time")
    sns.scatterplot(ax=ax_left[0], data=trades, x="close_date", y="trade_result_pct", hue="Trade result", ci=None, palette=palette)
    ax_left[0].set(xlabel='Trade close date', ylabel='Trade result in %')
    ax_left[0].axhline(y=0, color='black', alpha=0.5)

    ax_left[1].title.set_text("Trade result compared to trade duration")
    sns.scatterplot(ax=ax_left[1], data=trades, x="Trades duration in days", y="trade_result_pct", hue="Trade result", ci=None, palette=palette)
    ax_left[1].set(xlabel='Trade duration in days', ylabel='Trade result in %')
    ax_left[1].axhline(y=0, color='black', alpha=0.5)
    plt.show()

def plot_exposition_over_time(df_days):
    fig, ax_left = plt.subplots(figsize=(15, 15), nrows=3, ncols=1)
    ax_left[0].plot(df_days['total_exposition'], color='black', lw=1)
    ax_left[1].plot(df_days['long_exposition'], color='green', lw=1)
    ax_left[2].plot(df_days['short_exposition'], color='red', lw=1)
    plt.show()
    
# Simulation de divers scénarios futurs - Méthode de Monte Carlo
def plot_futur_simulations(df_trades, trades_multiplier, trades_to_forecast, number_of_simulations, true_trades_to_show, show_all_simulations=False):
    sns.set_style("darkgrid")
    sns.set(rc={'figure.figsize':(17,8)})
    plt.title("Simulation de " + str(number_of_simulations) + " scénarios différents")
    inital_wallet = df_trades.iloc[-1]['wallet']
    number_of_trade_last_year = len(df_trades[df_trades["close_date"]>datetime.datetime.now()-datetime.timedelta(days=365)])
    mean_trades_per_day = number_of_trade_last_year/365
    start_date = df_trades.iloc[-1]["close_date"]
    time_list = [(start_date:=start_date+datetime.timedelta(hours=int(24/mean_trades_per_day))) for x in range(trades_to_forecast)]
    # Utiliser trade_result_pct_wallet pour éviter explosion exponentielle
    # trade_result_pct_wallet = impact du trade sur le wallet total
    trades_pool = list(df_trades["trade_result_pct_wallet"] + 1) * trades_multiplier
    true_trades_date = list(df_trades.iloc[-true_trades_to_show:]["close_date"])
    true_trades_result = list(df_trades.iloc[-true_trades_to_show:]["wallet"])
    simulations = {}
    result_simulation = []

    # Bootstrap pur (sans bruit gaussien) pour préserver la vraie distribution
    for i in range(number_of_simulations):
        # Bootstrap: rééchantillonnage avec remise
        current_trades_pool = random.choices(trades_pool, k=trades_to_forecast)
        # NOTE: Pas de bruit gaussien - la distribution réelle n'est pas normale
        curr=1
        current_trades_result = [(curr:=curr*v) for v in current_trades_pool]
        simulated_wallet = [x*inital_wallet for x in current_trades_result]
        result_simulation.append({"key": i, "result": simulated_wallet[-1]})
        simulations[i] =  simulated_wallet
        if show_all_simulations:
            plt.plot(true_trades_date+time_list, true_trades_result+simulated_wallet, linewidth=0.5, color="grey")
            
    # if show_all_simulations == False:
    sorted_simul_result = sorted(result_simulation, key=lambda d: d['result']) 
    for i in range(10):
        index_to_show = i*int(len(sorted_simul_result)/9)
        if index_to_show>=len(sorted_simul_result):
            index_to_show = len(sorted_simul_result)-1
        if i != 9:
            plt.plot(true_trades_date+time_list, true_trades_result+simulations[sorted_simul_result[index_to_show]["key"]], linewidth=2)

    plt.show()
    
# Comparaison entre les divers scénarios et la réalité pour voir si il y a du surapprentissage
# Séparation des échantillons en train et en test - Méthode de Monte Carlo (Loi normale)
def plot_train_test_simulation(df_trades, train_test_date, trades_multiplier, number_of_simulations):
    sns.set_style("darkgrid")
    sns.set(rc={'figure.figsize':(17,8)})
    plt.title("Courbe de surapprentissage sur " + str(number_of_simulations) + " scénarios différents")

    # Séparation entre ensemble d'entraînement et de test
    df_train = df_trades.loc[df_trades["close_date"]<train_test_date]
    df_test = df_trades.loc[df_trades["close_date"]>=train_test_date]

    # Initialisation des paramètres
    trades_to_forecast = len(df_test)
    inital_wallet = df_train.iloc[-1]['wallet']
    trades_to_show = len(df_test) *2
    time_list = list(df_test["close_date"])
    # Utiliser trade_result_pct_wallet pour éviter explosion exponentielle
    # trade_result_pct_wallet = impact du trade sur le wallet total
    trades_pool = list(df_train["trade_result_pct_wallet"] + 1) * trades_multiplier
    true_trades_date = list(df_train.iloc[-trades_to_show:]["close_date"])
    true_trades_result = list(df_train.iloc[-trades_to_show:]["wallet"])
    simulations = {}
    result_simulation = []

    # Simulation de surapprentissage (Bootstrap pur - préserve la vraie distribution)
    for i in range(number_of_simulations):
        # Bootstrap: rééchantillonnage avec remise (préserve queues épaisses et asymétrie)
        current_trades_pool = random.choices(trades_pool, k=trades_to_forecast)
        # NOTE: On n'ajoute PAS de bruit gaussien car la distribution réelle n'est PAS normale
        # Le bootstrap préserve la vraie distribution (fat tails, skewness, etc.)
        curr=1
        current_trades_result = [(curr:=curr*v) for v in current_trades_pool]
        simulated_wallet = [x*inital_wallet for x in current_trades_result]
        result_simulation.append({"key": i, "result": simulated_wallet[-1]})
        simulations[i] =  simulated_wallet
    
    # Affichage des résultats de simulation
    sorted_simul_result = sorted(result_simulation, key=lambda d: d['result']) 
    for i in range(10):
        index_to_show = i*int(len(sorted_simul_result)/9)
        if index_to_show>=len(sorted_simul_result):
            index_to_show = len(sorted_simul_result)-1
        if i != 9:
            plt.plot(true_trades_date+time_list, true_trades_result+simulations[sorted_simul_result[index_to_show]["key"]])
            
    # Tracer la courbe réelle en vert épais
    plt.plot(true_trades_date+time_list, true_trades_result+list(df_test["wallet"]), linewidth=3.0, color="green", label="Réalité (Test Set)")

    # Validation statistique : percentile de la performance réelle
    real_final_wallet = df_test.iloc[-1]["wallet"]
    simulated_finals = [sim[-1] for sim in simulations.values()]
    percentile = sum(1 for x in simulated_finals if x < real_final_wallet) / len(simulated_finals) * 100

    # Afficher le résultat
    plt.legend()
    print(f"\n{'='*60}")
    print(f"VALIDATION OVERFITTING")
    print(f"{'='*60}")
    print(f"Wallet final réel (test): {real_final_wallet:.2f}")
    print(f"Percentile vs simulations: {percentile:.1f}%")
    if percentile > 95:
        print(f"⚠️  ALERTE OVERFITTING: Performance réelle > 95% des simulations!")
    elif percentile > 75:
        print(f"⚠️  Overfitting possible: Performance > 75% des simulations")
    elif percentile < 25:
        print(f"📉 Performance inférieure: < 25% des simulations")
    else:
        print(f"✅ Performance cohérente avec les simulations")
    print(f"{'='*60}\n")

    plt.show() 

    from datetime import datetime, timedelta


def detect_date_train_test(start_date, pourcent_test=0.2, end_date=None):
    """
    Calcule la date de séparation train/test.

    Args:
        start_date: Date de début au format 'YYYY-MM-DD'
        pourcent_test: Pourcentage de données pour le test (default: 0.2)
        end_date: Date de fin (optionnel, par défaut datetime.now())

    Returns:
        Date de coupure au format string 'YYYY-MM-DD HH:MM:SS'
    """
    from datetime import datetime, timedelta

    start_dt = datetime.strptime(start_date, '%Y-%m-%d')
    end_dt = datetime.strptime(end_date, '%Y-%m-%d') if end_date else datetime.now()

    total_duration = end_dt - start_dt
    training_days = total_duration.days * (1 - pourcent_test)
    cutoff_date = start_dt + timedelta(days=training_days)

    print(f"Train/Test Split:")
    print(f"  Train: {start_date} → {cutoff_date.strftime('%Y-%m-%d')} ({int(training_days)} jours)")
    print(f"  Test:  {cutoff_date.strftime('%Y-%m-%d')} → {end_dt.strftime('%Y-%m-%d')} ({int(total_duration.days * pourcent_test)} jours)")

    return str(cutoff_date)