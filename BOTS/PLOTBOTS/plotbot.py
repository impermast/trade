import os, sys
import pandas as pd
import tkinter as tk
from datetime import datetime
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt

sys.path.append(os.path.abspath("."))
from BOTS.PLOTBOTS.BaseBot import BasePlotBot


class PlotBot(BasePlotBot):
    def split_indicators(self, df: pd.DataFrame, indicators_overlay = {"sma", "ema", "bb_h", "bb_m", "bb_l"}) -> tuple[list[str], list[str]]:
        # Индикаторы, которые лучше рисовать прямо на графике цены
        
        base_columns = {"time", "timestamp", "open", "high", "low", "close", "volume", "orders", "position", "pnl"}

        overlay_inds = []
        subplot_inds = []

        for col in df.columns:
            if col.lower() in base_columns:
                continue
            if any(col.startswith(prefix) for prefix in indicators_overlay):
                overlay_inds.append(col)
            else:
                subplot_inds.append(col)

        return overlay_inds, subplot_inds
    
    
    def update_axes(self, df: pd.DataFrame):
        self.ax_price.clear()
        self.ax_pnl.clear()
        
        self.ax_price.plot(df["time"], df["close"], label="Цена закрытия", color="black")

        #Строю оверлей индикаторы
        overlay_inds, subplot_inds = self.split_indicators(df)
        self.logger.info(f'Строю дополнительные графики для индикаторов {overlay_inds}')
        for ind in overlay_inds:
            self.ax_price.plot(df["time"], df[ind], label=ind)
        for ind in subplot_inds:
            self.ax_indicators.plot(df["time"], df[ind], label=ind)
        #выставляю ордера на графике
        entry_price = None
        equity = [0]
        pos = 0
        if "orders" in df.columns:
            for i, row in df.iterrows():
                if row["orders"] > 0:
                    self.ax_price.scatter(row["time"], row["close"], color="green", marker="^", s=100)
                    if entry_price is None:
                        entry_price = row["close"]
                        pos = 1
                elif row["orders"] < 0 and entry_price is not None:
                    self.ax_price.scatter(row["time"], row["close"], color="red", marker="v", s=100)
                    pnl = (row["close"] - entry_price) * pos
                    equity.append(equity[-1] + pnl)
                    entry_price = None
                    pos = 0
                else:
                    equity.append(equity[-1])
        else:
            equity = [0] * len(df)

        #График PNL
        self.ax_pnl.plot(df["time"].iloc[:len(equity)], equity, color="blue", label="PNL")
        self.ax_pnl.set_ylabel("PNL")
        self.ax_pnl.grid()

        # Текущий момент времени
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Заголовок графика
        self.ax_price.set_title(f"График цен — Обновлено: {now}", fontsize=10, fontweight='bold')

        # Подписи и сетка
        self.ax_price.set_ylabel("Цена", fontsize=12)
        self.ax_price.set_xlabel("Время", fontsize=12)
        self.ax_price.tick_params(axis='x', rotation=45)
        self.ax_price.grid(visible=True, linestyle="--", linewidth=0.5, alpha=0.4)

        # Легенда — сверху справа, без дублирования
        handles, labels = self.ax_price.get_legend_handles_labels()
        by_label = dict(zip(labels, handles))  # убираем дубликаты
        self.ax_price.legend(by_label.values(), by_label.keys(), loc="upper right", fontsize=10)

        self.ax_indicators.legend(loc="lower right", fontsize=10)

        
    def _update_graph(self):
        try:
            df = pd.read_csv(self.csv_file)
            if 'timestamp' in df.columns:
                df.rename(columns={'timestamp': 'time'}, inplace=True)
            df["time"] = pd.to_datetime(df["time"])
            df = df.tail(100)

            self.update_axes(df)
            self.canvas.draw()

        except Exception as e:
            self.logger.error(f"Ошибка обновления графика: {e}")

        if self.root and self.root.winfo_exists():
            self.root.after(self.refresh_interval * 1000, self._update_graph)

    def start(self):
        self.setup_root("PlotBot — График торгов")
        self.ax_price, self.ax_pnl, self.ax_indicators = self.setup_canvas_tk(n_axes=3, height_ratios=[3, 1,1])
        self._update_graph()
        self.root.mainloop()

if __name__ == "__main__":
    plotbot = PlotBot(csv_file="DATA/BTCUSDT_1m_anal.csv", refresh_interval=15)
    plotbot.start()
    