import os, sys

sys.path.append(os.path.abspath("."))

import matplotlib.pyplot as plt
import pandas as pd
from BOTS.PLOTBOTS.BaseBot import BasePlotBot
from CORE.log_manager import Logger


class MLPlotBot(BasePlotBot):
    def __init__(self, csv_file=None, df=None, fig_path="DATA/FIG", output=None):
        """
        Инициация класс для статичных графиков. 
        output 1 -- сохранить и вывести на экран, 0 -- только вывести, -1 только сохранить
        """
        super().__init__(csv_file=csv_file)
        self.df = df  # можно передать уже загруженный df напрямую
        self.fig_path = fig_path
        self.output = output

    def prepare(self):
        """Загрузка и обработка данных, если нужно"""
        if self.df is None and self.csv_file:
            self.df = self.load_df()
        self.df["time"] = pd.to_datetime(self.df["time"])

    def graph_saver(self, plt, fig_name="plot.png"):
        """
        Управление отображением и сохранением графиков.
        
        self.output:
            1  → показать и сохранить
            0  → только показать
        -1  → только сохранить

        fig_name: имя сохраняемого файла (внутри self.output)
        """
        if self.output != -1:
            plt.show()
        if self.output != 0:
            file_path = os.path.join(self.fig_path, fig_name)

            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            plt.savefig(file_path, bbox_inches="tight")
            self.logger.info(f"График сохранён в {file_path}")


    def plot_phase_split(self):
        """Цветная полоска train/test/val"""
        self.prepare()
        fig, ax = plt.subplots(figsize=(12, 2))

        phase_colors = {
            "train": "green",
            "test": "blue",
            "val": "purple",
            "predict": "orange",
            "unknown": "gray"
        }

        if "phase" not in self.df.columns:
            self.logger.warning("Нет колонки 'phase' — невозможно построить split.")
            return

        for phase, color in phase_colors.items():
            if phase in self.df["phase"].unique():
                mask = self.df["phase"] == phase
                ax.fill_between(self.df["time"], 0, 1, where=mask,
                                transform=ax.get_xaxis_transform(), color=color, alpha=0.3, label=phase)

        ax.set_title(self.title)
        ax.set_yticks([])
        ax.set_ylabel("Фаза", rotation=0, labelpad=30)
        ax.legend(loc="center left", bbox_to_anchor=(1.0, 0.5))
        ax.grid(False)

        self.graph_saver(plt,"phasesplit.png")

    def plot_predictions(self, true_col="y_true", pred_col="y_pred"):
        """Сравнение предсказаний и истинных значений"""
        self.prepare()
        fig, ax = plt.subplots(figsize=(12, 4))
        if true_col in self.df.columns:
            ax.plot(self.df["time"], self.df[true_col], label="True", color="black")
        if pred_col in self.df.columns:
            ax.plot(self.df["time"], self.df[pred_col], label="Predicted", color="orange")

        ax.set_title("Предсказания модели")
        ax.set_ylabel("Значение")
        ax.legend()
        ax.grid(True)

        self.graph_saver(plt,"predict.png")
