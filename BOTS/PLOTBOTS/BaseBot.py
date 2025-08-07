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

    def render_to_file(self,out_path: str = "DATA/static/plot.png", tail: int = 100):
        """Сохраняет график в PNG без GUI."""
        try:
            df = self.load_df(tail)
            (ax1, ax2) = self.setup_canvas_local(n_axes=2, height_ratios=None)
            ax1.plot(df["time"], df['close'])
            if 'rsi' in df.columns: ax2.plot(df["time"], df['rsi'])

            file_name = os.path.basename(self.csv_file)  
            self.logger.info(file_name)        
            title = os.path.splitext(file_name)[0]               # e.g. BTCUSDT_1m_anal
            
            ax1.set_title(f"График: {title}", fontsize=14, weight="bold")
            
            
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