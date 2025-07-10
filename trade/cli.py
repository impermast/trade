"""
Command-line interface for the Trade Project.

This module provides a unified entry point for running different components
of the Trade Project from the command line.
"""

import argparse
import os
import sys
import pandas as pd
from typing import Dict, Any, List, Optional

from trade.bots.analbot import Analytic
from trade.strategy.rsi import RSIonly_Strategy
from trade.core.di import container, register, get


# Register components with the container
@register("analytic")
def create_analytic(df: pd.DataFrame, data_name: str, output_file: str = "anal.csv") -> Analytic:
    """
    Factory function for creating an Analytic instance.

    Args:
        df: DataFrame containing price data
        data_name: Name of the data
        output_file: Output file name

    Returns:
        An Analytic instance
    """
    return Analytic(df, data_name, output_file)


@register("rsi_strategy")
def create_rsi_strategy(**params: Any) -> RSIonly_Strategy:
    """
    Factory function for creating an RSIonly_Strategy instance.

    Args:
        **params: Strategy parameters

    Returns:
        An RSIonly_Strategy instance
    """
    return RSIonly_Strategy(**params)


def analyze_data(args: argparse.Namespace) -> int:
    """
    Analyze data using the specified strategy.

    Args:
        args: Command-line arguments

    Returns:
        0 for success, non-zero for failure
    """
    try:
        # Load data
        df = pd.read_csv(args.data_file)
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])

        # Extract data name from file path
        data_name = os.path.splitext(os.path.basename(args.data_file))[0]

        # Parse strategy parameters
        strategy_params = {}
        if args.rsi_period:
            if 'rsi' not in strategy_params:
                strategy_params['rsi'] = {}
            strategy_params['rsi']['period'] = args.rsi_period

        if args.rsi_lower:
            if 'rsi' not in strategy_params:
                strategy_params['rsi'] = {}
            strategy_params['rsi']['lower'] = args.rsi_lower

        if args.rsi_upper:
            if 'rsi' not in strategy_params:
                strategy_params['rsi'] = {}
            strategy_params['rsi']['upper'] = args.rsi_upper

        # Get components from the container
        anal = get("analytic", df=df, data_name=data_name)
        strategy = get("rsi_strategy", **strategy_params)

        # Run strategy
        result = anal.make_strategy(strategy.__class__, **strategy_params)

        # Print result
        print(f"Strategy result: {result}")
        print(f"Signal interpretation: {signal_to_text(result)}")

        return 0
    except Exception as e:
        print(f"Error analyzing data: {e}", file=sys.stderr)
        return 1


def signal_to_text(signal: int) -> str:
    """
    Convert a signal value to a human-readable text.

    Args:
        signal: Signal value (1, -1, or 0)

    Returns:
        Human-readable text describing the signal
    """
    if signal == 1:
        return "BUY"
    elif signal == -1:
        return "SELL"
    else:
        return "HOLD/NO ACTION"


def main() -> int:
    """
    Main entry point for the command-line interface.

    Returns:
        0 for success, non-zero for failure
    """
    parser = argparse.ArgumentParser(description="Trade Project CLI")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Analyze command
    analyze_parser = subparsers.add_parser("analyze", help="Analyze data using a strategy")
    analyze_parser.add_argument("data_file", help="Path to the data file (CSV)")
    analyze_parser.add_argument("--rsi-period", type=int, help="RSI period")
    analyze_parser.add_argument("--rsi-lower", type=float, help="RSI lower threshold")
    analyze_parser.add_argument("--rsi-upper", type=float, help="RSI upper threshold")

    # Parse arguments
    args = parser.parse_args()

    # Run the appropriate command
    if args.command == "analyze":
        return analyze_data(args)
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
