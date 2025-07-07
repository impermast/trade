import os, sys
import pandas as pd
import tkinter as tk
from datetime import datetime
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt

sys.path.append(os.path.abspath("."))
from BOTS.loggerbot import Logger


class PlotBot:
    def __init__(self, csv_file=None, refresh_interval=10):
        self.csv_file = csv_file
        self.refresh_interval = refresh_interval  # seconds
        self.root = None
        self.figure = None
        self.ax = None
        self.canvas = None
        self.logger = Logger(name="Plotbot", tag="[PLOT]", logfile="logs/plotbot.log", console=True).get_logger()

    def set_file(self, csv_file):
        self.logger.info(f"Загружен файл {csv_file}")
        self.csv_file = csv_file

    def _update_graph(self):
        try:
            df = pd.read_csv(self.csv_file)
            if 'timestamp' in df.columns:
                df.rename(columns={'timestamp': 'time'}, inplace=True)
            df["time"] = pd.to_datetime(df["time"])
            df = df.tail(50)
            now = datetime.now().strftime("%H:%M:%S")

            self.ax.clear()
            self.ax.plot(df["time"], df["close"], label="Цена закрытия", color="black")

            if "orders" in df.columns:
                for i, row in df.iterrows():
                    if row["orders"] > 0:
                        self.ax.scatter(row["time"], row["close"], color="green", marker="^", s=100, label="Buy" if i == 0 else "")
                    elif row["orders"] < 0:
                        self.ax.scatter(row["time"], row["close"], color="red", marker="v", s=100, label="Sell" if i == 0 else "")

            self.ax.set_title(f"График цен | Обновлено: {now}")
            self.ax.set_xlabel("Время")
            self.ax.set_ylabel("Цена")
            self.ax.legend()
            self.ax.grid()
            self.canvas.draw()

        except Exception as e:
            self.logger.error(f"Ошибка обновления графика: {e}")

        # безопасное повторение
        if self.root and self.root.winfo_exists():
            self.root.after(self.refresh_interval * 1000, self._update_graph)
    
    def _on_close(self):
        self.logger.info("Окно PlotBot закрыто пользователем.")
        if self.root:
            self.root.destroy()
        self.logger.info("Завершаем процесс.")
        sys.exit(0)

    def start(self):
        if not self.csv_file or not os.path.exists(self.csv_file):
            self.logger.error("CSV-файл не найден.")
            return
        df = pd.read_csv(self.csv_file)
        if 'timestamp' in df.columns:
                df.rename(columns={'timestamp': 'time'}, inplace=True)
        print("[DEBUG] Колонки CSV:", df.columns)

        self.root = tk.Tk()
        self.root.title("PlotBot — График торгов")
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        frame = tk.Frame(self.root)
        frame.pack(fill=tk.BOTH, expand=True)

        self.figure, self.ax = plt.subplots(figsize=(10, 6))
        self.canvas = FigureCanvasTkAgg(self.figure, master=frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        self._update_graph()

        try:
            self.root.mainloop()
            
        except KeyboardInterrupt:
            self.logger.info("Пользователь остановил PlotBot.")


if __name__ == "__main__":
    plotbot = PlotBot(csv_file="DATA/BTCUSDT_1h.csv", refresh_interval=15)
    plotbot.start()
    