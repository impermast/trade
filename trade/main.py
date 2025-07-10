"""
Main entry point for the trade application.
"""

import os
import pandas as pd
from typing import Dict, Any

from trade.bots.analbot import Analytic
from trade.strategy.rsi import RSIonly_Strategy


def main() -> Dict[str, Any]:
    """
    Main entry point for the trade analysis application.
    
    Returns:
        Dict[str, Any]: The results of the strategy analysis.
    """
    # Get the path to the current file
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Path to the DATA folder
    csv_path = os.path.join(os.path.dirname(current_dir), "DATA", "BTCUSDT_1h.csv")
    csv_path = os.path.abspath(csv_path)  # absolute path (just in case)
    
    # Load and preprocess data
    df = pd.read_csv(csv_path)
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Initialize analytic and run strategy
    anal = Analytic(df, "BTCUSDT_1h")
    result = anal.make_strategy(RSIonly_Strategy, rsi={"period": 20, "lower": 20})
    
    print(result)
    return result


if __name__ == "__main__":
    main()