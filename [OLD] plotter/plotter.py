import tkinter as tk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime

class GraphApp:
    def __init__(self, root, csv_file, refresh_interval=10):
        self.root = root
        self.csv_file = csv_file
        self.refresh_interval = refresh_interval  # Интервал обновления в секундах

        # Настройка окна
        self.root.title("График цен")
        self.frame = tk.Frame(self.root)
        self.frame.pack(fill=tk.BOTH, expand=True)

        # Создание холста для графика
        self.figure, self.ax = plt.subplots(figsize=(8, 5))
        self.canvas = FigureCanvasTkAgg(self.figure, master=self.frame)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.pack(fill=tk.BOTH, expand=True)

        # Запуск обновления графика
        self.update_graph()

    def update_graph(self):
        try:
            # Чтение данных из CSV
            df = pd.read_csv(self.csv_file)
            df["time"] = pd.to_datetime(df["time"])
            current_time = datetime.now().strftime("%H:%M")
            df = df.tail(50)

            self.ax.clear()
            
            self.ax.plot(df["time"], df["close"], label="Цена закрытия", color="blue")
            for i, row in df.iterrows():
                if row["orders"] > 0:  # Покупка
                    self.ax.scatter(row["time"], row["close"], color="green", marker="o", label=f"Куплено")
                elif row["orders"] < 0:  # Продажа
                    self.ax.scatter(row["time"], row["close"], color="red", marker="o", label=f"Продано")

            self.ax.set_title(f"График цен | Обновлено: {current_time}", fontsize=16)
            self.ax.set_xlabel("Дата")
            self.ax.set_ylabel("Цена")
            self.ax.legend()
            self.ax.grid()

            self.canvas.draw()

        except Exception as e:
            print(f"Ошибка обновления графика: {e}")

        # Запланировать следующее обновление
        self.root.after(self.refresh_interval * 1000, self.update_graph)


# Запуск интерфейса
def run_interface(csv_file):
    root = tk.Tk()
    app = GraphApp(root, csv_file)
    root.mainloop()


if __name__ == "__main__":
    run_interface("data/candles_LKOH.csv")