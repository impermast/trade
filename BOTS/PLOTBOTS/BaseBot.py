# base_plotbot.py
import sys, os
sys.path.append(os.path.abspath("."))

import pandas as pd
import tkinter as tk
from datetime import datetime
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt

from BOTS.loggerbot import Logger


class BasePlotBot:
    def __init__(self, csv_file=None, refresh_interval=10):
        self.csv_file = csv_file
        self.refresh_interval = refresh_interval
        self.root = None
        self.figure = None
        self.canvas = None
        self.logger = Logger(name=self.__class__.__name__, tag="[PLOT]", logfile="logs/plotbot.log", console=True).get_logger()

    def load_df(self, tail:int = 100):
        df = pd.read_csv(self.csv_file)
        if "timestamp" in df.columns:
            df.rename(columns={"timestamp": "time"}, inplace=True)
        df["time"] = pd.to_datetime(df["time"])
        return df.tail(tail)

    def setup_root(self, title="PlotBot"):
        self.root = tk.Tk()
        self.root.title(title)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def setup_canvas_tk(self, n_axes=2, height_ratios=None):
        frame = tk.Frame(self.root)
        frame.pack(fill=tk.BOTH, expand=True)
        self.figure, axes = plt.subplots(n_axes, 1, figsize=(10, 6 + n_axes), sharex=True,
                                         gridspec_kw={'height_ratios': height_ratios or [3, 1]})
        self.canvas = FigureCanvasTkAgg(self.figure, master=frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        return axes
    def setup_canvas_local(self, n_axes=2, height_ratios=None):
        self.figure, axes = plt.subplots(n_axes, 1, figsize=(10, 6 + n_axes), sharex=True,
                                         gridspec_kw={'height_ratios': height_ratios or [3, 1]})
        return axes

    def render_to_file(self, out_path: str = "DATA/static/plot.png", tail: int = 100):
        """Сохраняет график в PNG — свечи, линия закрытия, RSI."""
        import matplotlib.dates as mdates
        from matplotlib.patches import Rectangle
        from matplotlib import pyplot as plt

        try:
            df = self.load_df(tail)
            df["time"] = pd.to_datetime(df["time"])
            df = df.tail(tail)

            (ax1, ax2) = self.setup_canvas_local(n_axes=2, height_ratios=[3, 1])

            file_name = os.path.basename(self.csv_file)
            title = os.path.splitext(file_name)[0]

            has_ohlc = {"open", "high", "low", "close"}.issubset(df.columns)

            # --- Свечной график ---
            if has_ohlc:
                for _, row in df.iterrows():
                    color = '#00cc00' if row['close'] >= row['open'] else '#ff3333'
                    # Тени
                    ax1.plot([row["time"], row["time"]], [row["low"], row["high"]], color=color, linewidth=0.8)
                    # Тело
                    rect = Rectangle(
                        (row["time"] - pd.Timedelta(minutes=0.5), min(row["open"], row["close"])),
                        pd.Timedelta(minutes=1),
                        abs(row["close"] - row["open"]),
                        color=color, alpha=0.8
                    )
                    ax1.add_patch(rect)
                # Основная линия закрытия
                ax1.plot(df["time"], df["close"], color="black", linewidth=1.2, linestyle="--", label="Close price")
            else:
                ax1.plot(df["time"], df["close"], label="Close", color="blue", linewidth=1.5)

            ax1.set_title(f"График: {title}", fontsize=14, weight="bold")
            ax1.set_ylabel("Цена")
            ax1.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
            ax1.legend(loc="upper left", fontsize=8)
            ax1.tick_params(axis='x', labelrotation=45)

            # --- RSI ---
            if "rsi" in df.columns:
                ax2.plot(df["time"], df["rsi"], label="RSI", color="#800080", linewidth=1.5)
                ax2.axhline(70, color="red", linestyle="--", linewidth=1, alpha=0.5)
                ax2.axhline(30, color="green", linestyle="--", linewidth=1, alpha=0.5)
                ax2.set_ylabel("RSI")
                ax2.set_xlabel("Время")
                ax2.set_ylim(0, 100)
                ax2.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
                ax2.tick_params(axis='x', labelrotation=45)
                ax2.legend(fontsize=8)

            # Убираем гриды
            ax1.grid(False)
            ax2.grid(False)

            plt.tight_layout()
            plt.savefig(out_path)
            self.logger.info(f"График сохранён в {out_path}")
        except Exception as e:
            self.logger.error(f"Ошибка сохранения графика: {e}")

 

    def _on_close(self):
        self.logger.info("Окно PlotBot закрыто пользователем.")
        if self.root:
            self.root.destroy()
        self.logger.info("Завершаем процесс.")
        sys.exit(0)