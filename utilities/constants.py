"""
Constants and standardized naming conventions for the backtesting framework.
"""
from typing import List

# ============================================================================
# COLUMN NAMES - Standardized DataFrame column names
# ============================================================================
class ColumnNames:
    """Standard column names for OHLCV data."""
    OPEN = "open"
    HIGH = "high"
    LOW = "low"
    CLOSE = "close"
    VOLUME = "volume"
    DATE = "date"

    # Calculated columns
    WALLET = "wallet"
    PRICE = "price"
    DRAWDOWN = "drawdown"
    DRAWDOWN_PCT = "drawdown_pct"
    POSITION = "position"
    PAIR = "pair"

    # Trade columns
    OPEN_DATE = "open_date"
    CLOSE_DATE = "close_date"
    OPEN_PRICE = "open_price"
    CLOSE_PRICE = "close_price"
    OPEN_FEE = "open_fee"
    CLOSE_FEE = "close_fee"
    TRADE_RESULT = "trade_result"
    TRADE_RESULT_PCT = "trade_result_pct"

    @classmethod
    def get_required_ohlcv(cls) -> List[str]:
        """Get list of required OHLCV columns."""
        return [cls.OPEN, cls.HIGH, cls.LOW, cls.CLOSE, cls.VOLUME]


# ============================================================================
# PARAMETER NAMES - Standardized parameter names
# ============================================================================
class ParamNames:
    """Standard parameter names for strategies."""
    # Exposure (use consistent naming)
    WALLET_EXPOSURE = "wallet_exposure"  # Standard name (not wallet_exposition)

    # Envelope strategy
    MA_BASE_WINDOW = "ma_base_window"
    ENVELOPES = "envelopes"
    SIZE = "size"
    SRC = "src"

    # Bollinger strategy
    BB_WINDOW = "bb_window"
    BB_STD = "bb_std"
    LONG_MA_WINDOW = "long_ma_window"

    # TRIX strategy
    TRIX_LENGTH = "trix_length"
    TRIX_SIGNAL_LENGTH = "trix_signal_length"
    TRIX_SIGNAL_TYPE = "trix_signal_type"


# ============================================================================
# TRADE TYPES
# ============================================================================
class TradeTypes:
    """Trade position types."""
    LONG = "LONG"
    SHORT = "SHORT"


class OrderTypes:
    """Order execution types."""
    MARKET = "Market"
    LIMIT = "Limit"
    STOP_LOSS = "Stop Loss"
    LIQUIDATION = "Liquidation"


# ============================================================================
# FEES - Default fee structures
# ============================================================================
class Fees:
    """Default fee structures for exchanges."""

    # Binance
    BINANCE_MAKER = 0.0002
    BINANCE_TAKER = 0.0004

    # Bitget
    BITGET_MAKER = 0.0002
    BITGET_TAKER = 0.0006

    # Bybit
    BYBIT_MAKER = 0.0001
    BYBIT_TAKER = 0.0006

    @classmethod
    def get_exchange_fees(cls, exchange: str) -> dict:
        """Get maker/taker fees for an exchange."""
        fees = {
            "binance": {"maker": cls.BINANCE_MAKER, "taker": cls.BINANCE_TAKER},
            "bitget": {"maker": cls.BITGET_MAKER, "taker": cls.BITGET_TAKER},
            "bybit": {"maker": cls.BYBIT_MAKER, "taker": cls.BYBIT_TAKER},
        }
        return fees.get(exchange.lower(), {"maker": 0.0002, "taker": 0.0007})


# ============================================================================
# VAR SETTINGS
# ============================================================================
class VaRSettings:
    """Value at Risk calculation settings."""
    DEFAULT_CONFIDENCE_LEVEL = 0.05  # 95% confidence
    DEFAULT_LOOKBACK_DAYS = 1000
    MIN_LOOKBACK_DAYS = 100


# ============================================================================
# TIME INTERVALS
# ============================================================================
class TimeIntervals:
    """Standard time interval identifiers."""
    MIN_1 = "1m"
    MIN_5 = "5m"
    MIN_15 = "15m"
    MIN_30 = "30m"
    HOUR_1 = "1h"
    HOUR_4 = "4h"
    HOUR_12 = "12h"
    DAY_1 = "1d"
    WEEK_1 = "1w"
    MONTH_1 = "1M"

    @classmethod
    def get_all_intervals(cls) -> List[str]:
        """Get list of all supported intervals."""
        return [
            cls.MIN_1, cls.MIN_5, cls.MIN_15, cls.MIN_30,
            cls.HOUR_1, cls.HOUR_4, cls.HOUR_12,
            cls.DAY_1, cls.WEEK_1, cls.MONTH_1
        ]


# ============================================================================
# FILE PATHS
# ============================================================================
class Paths:
    """Standard file paths."""
    DATABASE = "./database"
    DATABASE_EXCHANGES = "./database/exchanges"
    LOGS = "./logs"
    SCRIPTS = "./scripts"
    STRATEGIES = "./strategies"
    UTILITIES = "./utilities"
