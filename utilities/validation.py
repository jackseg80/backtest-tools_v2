"""
Data validation utilities for backtesting framework.
Ensures data integrity before running backtests.
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple


class DataValidator:
    """Validates DataFrame structure and content for backtesting."""

    REQUIRED_COLUMNS = ['open', 'high', 'low', 'close', 'volume']

    @staticmethod
    def validate_ohlcv_dataframe(df: pd.DataFrame, pair_name: str = "Unknown") -> Tuple[bool, List[str]]:
        """
        Validate OHLCV DataFrame structure and content.

        Args:
            df: DataFrame to validate
            pair_name: Name of the trading pair (for error messages)

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        # Check if DataFrame is empty
        if df.empty:
            errors.append(f"{pair_name}: DataFrame is empty")
            return False, errors

        # Check required columns
        missing_cols = set(DataValidator.REQUIRED_COLUMNS) - set(df.columns)
        if missing_cols:
            errors.append(f"{pair_name}: Missing columns: {missing_cols}")

        # Check for NaN values
        nan_cols = df[DataValidator.REQUIRED_COLUMNS].columns[df[DataValidator.REQUIRED_COLUMNS].isna().any()].tolist()
        if nan_cols:
            nan_counts = df[nan_cols].isna().sum().to_dict()
            errors.append(f"{pair_name}: NaN values found in columns: {nan_counts}")

        # Check for infinite values
        inf_cols = df[DataValidator.REQUIRED_COLUMNS].columns[np.isinf(df[DataValidator.REQUIRED_COLUMNS]).any()].tolist()
        if inf_cols:
            errors.append(f"{pair_name}: Infinite values found in columns: {inf_cols}")

        # Check index is datetime
        if not isinstance(df.index, pd.DatetimeIndex):
            errors.append(f"{pair_name}: Index is not DatetimeIndex (type: {type(df.index)})")

        # Check for duplicate dates
        duplicates = df.index.duplicated()
        if duplicates.any():
            dup_count = duplicates.sum()
            errors.append(f"{pair_name}: {dup_count} duplicate dates found")

        # Check for missing dates (gaps)
        if isinstance(df.index, pd.DatetimeIndex) and len(df) > 1:
            time_diffs = df.index.to_series().diff()
            expected_freq = time_diffs.mode()[0] if len(time_diffs.mode()) > 0 else None
            if expected_freq:
                gaps = time_diffs[time_diffs > expected_freq * 1.5]
                if len(gaps) > 0:
                    errors.append(f"{pair_name}: {len(gaps)} gaps detected in time series")

        # Check OHLC logic (high >= low, close between high/low)
        invalid_hl = df[df['high'] < df['low']]
        if len(invalid_hl) > 0:
            errors.append(f"{pair_name}: {len(invalid_hl)} rows where high < low")

        invalid_close = df[(df['close'] > df['high']) | (df['close'] < df['low'])]
        if len(invalid_close) > 0:
            errors.append(f"{pair_name}: {len(invalid_close)} rows where close outside high/low range")

        # Check for negative prices
        for col in ['open', 'high', 'low', 'close']:
            if (df[col] <= 0).any():
                neg_count = (df[col] <= 0).sum()
                errors.append(f"{pair_name}: {neg_count} non-positive values in {col}")

        # Check for negative volume
        if (df['volume'] < 0).any():
            neg_vol = (df['volume'] < 0).sum()
            errors.append(f"{pair_name}: {neg_vol} negative volume values")

        return len(errors) == 0, errors

    @staticmethod
    def validate_multi_pair_data(df_list: Dict[str, pd.DataFrame]) -> Tuple[bool, Dict[str, List[str]]]:
        """
        Validate multiple trading pairs.

        Args:
            df_list: Dictionary mapping pair names to DataFrames

        Returns:
            Tuple of (all_valid, dict_of_errors_per_pair)
        """
        all_errors = {}
        all_valid = True

        for pair, df in df_list.items():
            is_valid, errors = DataValidator.validate_ohlcv_dataframe(df, pair)
            if not is_valid:
                all_errors[pair] = errors
                all_valid = False

        return all_valid, all_errors

    @staticmethod
    def validate_strategy_parameters(params: dict, required_keys: List[str]) -> Tuple[bool, List[str]]:
        """
        Validate strategy parameters.

        Args:
            params: Dictionary of parameters
            required_keys: List of required parameter keys

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        # Check required keys
        missing_keys = set(required_keys) - set(params.keys())
        if missing_keys:
            errors.append(f"Missing required parameters: {missing_keys}")

        # Check for None values
        none_keys = [k for k, v in params.items() if v is None]
        if none_keys:
            errors.append(f"Parameters with None value: {none_keys}")

        return len(errors) == 0, errors

    @staticmethod
    def print_validation_report(all_valid: bool, errors: Dict[str, List[str]]):
        """Print a formatted validation report."""
        if all_valid:
            print("✓ All data validation checks passed")
        else:
            print("✗ Data validation failed:")
            for pair, pair_errors in errors.items():
                print(f"\n  {pair}:")
                for error in pair_errors:
                    print(f"    - {error}")
