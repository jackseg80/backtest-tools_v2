# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Backtest-Tools-V2 is a cryptocurrency trading strategy backtesting framework written in Python. It supports multiple trading strategies (Bollinger Bands, TRIX, Envelope) across multiple coins/timeframes with risk management tools like Value at Risk (VaR).

## Setup and Environment

**Prerequisites**: Python >= 3.10

**Initial Setup**:
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

The project uses a virtual environment (`.venv` or `venv`) - ensure you activate it before running commands.

## Project Architecture

### Core Components

**Data Management (`utilities/data_manager.py`)**:
- `ExchangeDataManager` class handles downloading and loading historical data from multiple exchanges
- Supports exchanges: binance, binanceusdm, kucoin, kucoinfutures, okx, bitget, bybit
- Downloads data via CCXT async and saves to CSV in `database/exchanges/`
- Timeframes: 1m, 2m, 5m, 15m, 30m, 1h, 2h, 4h, 12h, 1d, 1w, 1M

**Backtesting Analysis (`utilities/bt_analysis.py`)**:
- `simple_backtest_analysis()` - Single pair backtests
- `multi_backtest_analysis()` - Multi-coin portfolio backtests
- Calculates metrics: Sharpe ratio, win rate, drawdown, profit stats
- Generates detailed trade and daily performance reports

**Custom Indicators (`utilities/custom_indicators.py`)**:
- `Trix` class - Triple EMA oscillator with signal line
- `chop()` - Choppiness indicator
- `fear_and_greed()` - Fetches Fear & Greed Index from API
- Helper: `get_n_columns()` shifts dataframe columns by n periods

**Visualization (`utilities/plot_analysis.py`)**:
- `plot_equity_vs_asset()` - Compare strategy vs buy & hold
- `plot_bar_by_month()` - Monthly/yearly performance breakdown
- `plot_futur_simulations()` - Monte Carlo forward testing
- `plot_train_test_simulation()` - Overfitting detection via train/test split

**Risk Management (`utilities/VaR.py`)**:
- `ValueAtRisk` class calculates position sizing based on VaR
- Used in multi-coin strategies to limit portfolio risk exposure

### Strategy Implementations

All strategies follow a consistent pattern with three methods:
1. `populate_indicators()` - Calculate technical indicators
2. `populate_buy_sell()` - Generate entry/exit signals
3. `run_backtest()` - Execute backtest with trade/position management

**Strategy Classes** (in `utilities/strategies/`):
- `BollingerTrendMulti` (`boltrend_multi.py`) - Bollinger Bands + MA trend filter
- `TrixMulti` (`trixMulti.py`) - TRIX oscillator strategy
- `EnvelopeMulti_v2` (`envelopeMulti_v2.py`) - **[PRODUCTION]** Moving average envelope strategy with improved margin/liquidation management
- `EnvelopeMulti` (`envelopeMulti.py`) - **[LEGACY]** Original envelope implementation (bug with leverage)
- `Envelope` (`envelope.py`) - Single-pair envelope implementation

**Important**: Always use V2 engines for production/live trading. V1 engines have known bugs with leverage calculation and are kept only for legacy comparison.

**V2 Engine Improvements** (as of 2025-10-05):
- ✅ **Margin calculation bugfix**: `used_margin` is now recalculated at each iteration based on actual open positions, preventing false "margin cap reached" rejections that stopped trading prematurely
- ✅ Accurate intra-candle liquidation detection
- ✅ Independent stop-loss and liquidation checks
- ✅ Exposure caps (gross, per-side, per-pair, margin)
- ✅ Kill-switch for automatic trading pause after drawdown

**Multi-coin Strategy Pattern**:
- Takes `df_list` dict mapping pair names to dataframes
- Takes `parameters_obj` dict mapping pairs to strategy parameters
- Supports independent parameters per coin (bb_window, wallet_exposure, etc.)
- Uses VaR for dynamic position sizing when `max_var` is specified

### Strategy Notebooks

Located in `strategies/` with subfolders per strategy type:
- `strategies/bol_trend/` - Bollinger trend variations
- `strategies/envelopes/` - Envelope strategies
- `strategies/trix/` - TRIX strategies
- `strategies/mrat/` - Mean reversion strategies

Key notebook pattern (`bollinger_trend_multi.ipynb`):
1. Define coin list with individual parameters in `params_coin` dict
2. Load historical data via `ExchangeDataManager`
3. Initialize strategy class with df_list and parameters
4. Run backtest with fees, leverage, VaR limits
5. Analyze results and plot performance

### Data Workflow

**Main Jupyter Notebook** (`data_engine.ipynb`):
- Downloads historical OHLCV data from exchanges
- Stores in `database/exchanges/{exchange}/{pair}_{timeframe}.csv`
- Explores available data with `exchange.explore_data()`

**Loading Data**:
```python
exchange = ExchangeDataManager(exchange_name="binance", path_download="./database/exchanges")
df = exchange.load_data(coin="BTC/USDT:USDT", interval="1h")
```

### Common Development Patterns

**Backtest Parameters**:
- Coins are defined with pair-specific parameters (wallet_exposure, indicator windows)
- Leverage is applied globally across portfolio
- Fees: maker_fee, taker_fee (exchange-specific)
- Risk: max_var limits max loss percentage per timeframe

**Signal Generation**:
- Long/Short signals stored as boolean columns (e.g., `open_long_market`, `close_short_market`)
- Multi-coin strategies aggregate signals by date, returning dict of {date: [pairs_with_signal]}
- Uses shifted indicators (`get_n_columns`) to avoid lookahead bias

**Result Analysis**:
- Returns `df_trades` (individual trades) and `df_days` (daily wallet snapshots)
- Both dataframes have calculated columns for P&L, drawdown, exposure
- Analysis functions accept flags to show/hide specific sections (trades_info, days_info, etc.)

## External APIs and Integration

- `python-ctapi/` subfolder contains a custom exchange API wrapper (separate package)
- Fear & Greed API: `https://api.alternative.me/fng/` used in custom_indicators.py
- CCXT library handles all exchange interactions with rate limiting enabled

## File Organization Notes

- Main utilities are in `utilities/` (reusable across strategies)
- Individual strategy implementations in `utilities/strategies/`
- Strategy notebooks/research in `strategies/{strategy_name}/`
- Historical data stored in `database/exchanges/`
- Test/experimental files in `test/`
- **Scripts** in `scripts/` with results saved to `scripts/resultats/`

## Scripts and Automation

**Testing Scripts** (in `scripts/`):
- `test_cycles.py` - Tests strategy performance across different market cycles (Bull 2020-2021, Bear 2022, Recovery 2023, Bull 2024)
  - Generates CSV summary: `scripts/resultats/backtest_cycles_results.csv`
  - Generates detailed CSV per cycle: `scripts/resultats/trades_{cycle}.csv` and `scripts/resultats/days_{cycle}.csv`
- `test_cycles_detailed.py` - Extended version with LONG ONLY vs LONG+SHORT comparison
  - Tests all 28 pairs across all cycles
  - Generates comprehensive text report: `scripts/resultats/backtest_cycles_detailed.txt`
  - Shows excluded pairs and reasons (insufficient data)

**Running Scripts**:
```bash
cd d:\Python\Cryptobots\Backtest-Tools-V2
python scripts/test_cycles.py              # Quick summary
python scripts/test_cycles_detailed.py     # Full analysis
```

## Envelope Strategy Configuration (Production)

**Notebook**: `strategies/envelopes/multi_envelope.ipynb`
**Live Bot**: `strategies/envelopes/live/live_multi_envelope.py`

### Key Configuration
The notebook is configured to match the live trading bot exactly:

```python
# Centralized configuration
BACKTEST_LEVERAGE = 10  # Must match live bot leverage

# Size values from live bot (automatically adjusted for backtest)
params_live = {
    "BTC/USDT:USDT": {"size": 0.1, "ma_base_window": 7, "envelopes": [0.07, 0.1, 0.15]},
    # ... other pairs
}

# Automatic adjustment for V2 engine
params[pair]["size"] = params_live[pair]["size"] / BACKTEST_LEVERAGE
```

### Backtest Parameters (Aligned with Live)
- `reinvest = True` - Recalculates sizing at each trade (matches live behavior)
- `leverage = 10` - Cross 10x leverage
- `stop_loss = 0.25` - 25% stop loss
- `risk_mode = "scaling"` - Notional scales with leverage
- `maker_fee = 0.0002, taker_fee = 0.0006` - Bitget fees

### Important Notes
1. **MATIC/USDT:USDT is commented out** in the notebook (disabled in live production)
2. **Size adjustment is automatic** - no need to manually calculate
3. **V2 engine messages are silenced** - clean backtest output without debug logs
4. To change leverage, only modify `BACKTEST_LEVERAGE` in one place

### Known Issues and Fixes

**Margin Cap Bug (FIXED 2025-10-05)**:
- **Symptom**: Backtest stops opening new positions after several months despite having available wallet balance
- **Cause**: `used_margin` accumulated from closed positions instead of reflecting only current open positions
- **Impact**: With tight stop-loss (e.g., 5%) and high leverage (10x), `rejected_by_margin_cap` could reach thousands, blocking all new trades
- **Fix**: `used_margin` is now recalculated at each iteration: `sum(pos.get('init_margin', 0) for pos in current_positions.values())`
- **Result**: `rejected_by_margin_cap` reduced from 6116 → 0, allowing backtest to continue normally throughout entire data range
