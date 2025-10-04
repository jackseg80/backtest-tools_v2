"""
Logging configuration for the backtesting framework.
Provides consistent logging across all modules.
"""
import logging
import sys
from pathlib import Path
from datetime import datetime


def setup_logger(
    name: str = "backtest",
    level: int = logging.INFO,
    log_to_file: bool = True,
    log_dir: str = "./logs"
) -> logging.Logger:
    """
    Configure and return a logger instance.

    Args:
        name: Logger name
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_to_file: Whether to save logs to file
        log_dir: Directory for log files

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    # Avoid adding handlers multiple times
    if logger.handlers:
        return logger

    logger.setLevel(level)

    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    simple_formatter = logging.Formatter(
        '%(levelname)s - %(message)s'
    )

    # Console handler (simple format)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(simple_formatter)
    logger.addHandler(console_handler)

    # File handler (detailed format)
    if log_to_file:
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file = log_path / f"{name}_{timestamp}.log"

        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)  # Log everything to file
        file_handler.setFormatter(detailed_formatter)
        logger.addHandler(file_handler)

    return logger


# Pre-configured loggers for common modules
def get_backtest_logger(level: int = logging.INFO) -> logging.Logger:
    """Get logger for backtest operations."""
    return setup_logger("backtest", level=level)


def get_data_logger(level: int = logging.INFO) -> logging.Logger:
    """Get logger for data operations."""
    return setup_logger("data", level=level)


def get_strategy_logger(level: int = logging.INFO) -> logging.Logger:
    """Get logger for strategy operations."""
    return setup_logger("strategy", level=level)


# Example usage in modules:
# from utilities.logger import get_backtest_logger
# logger = get_backtest_logger()
# logger.info("Starting backtest...")
# logger.warning("High drawdown detected")
# logger.error("Invalid data format")
