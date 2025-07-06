import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.preprocessing import PolynomialFeatures
from sklearn.linear_model import LinearRegression

# Загрузка данных из CSV
ticket = "CHMF"
file_name = ticket + "_price.csv"  # Имя файла
df = pd.read_csv(file_name)

# Преобразуем столбец даты в datetime формат
df['Дата'] = pd.to_datetime(df['Дата'], format='%d.%m.%Y')

# Заменяем точку для тысяч и запятую на точку для десятичных чисел
df['Цена'] = df['Цена'].str.replace('.', '', regex=False)
df['Цена'] = df['Цена'].str.replace(',', '.', regex=False).astype(float)

# Сортировка данных по дате в порядке возрастания
df = df.sort_values('Дата')

# Преобразуем даты в числовой формат (например, дни с начала наблюдений)
df['Дата_num'] = (df['Дата'] - df['Дата'].min()).dt.days

# Настроим фигуру для 2x2 подграфиков
fig, axs = plt.subplots(2, 2, figsize=(20, 12))

# Функция для построения графика с увеличенной степенью полинома
def plot_graph(ax, train_size, degree, title, extrapolate=False):
    # Разделим данные на обучающую и тестовую выборки
    train_data = df[:train_size]
    test_data = df[train_size:]

    # Подготовим данные для полиномиальной регрессии 
    X_train = train_data['Дата_num'].values.reshape(-1, 1)
    y_train = train_data['Цена'].values

    # Применяем полиномиальную регрессию с заданной степенью
    poly = PolynomialFeatures(degree=degree)
    X_train_poly = poly.fit_transform(X_train)

    # Обучаем модель на обучающих данных
    model = LinearRegression()
    model.fit(X_train_poly, y_train)

    # Если нужно делать экстраполяцию (на 25% вперед)
    if extrapolate:
        # Расширим X_train на дополнительные 25% (добавляем новые дни в X_test)
        last_day = train_data['Дата_num'].max()
        future_days = np.arange(last_day + 1, last_day + int(len(df) * 0.25) + 1).reshape(-1, 1)
        X_future_poly = poly.transform(future_days)
        future_predictions = model.predict(X_future_poly)
        
        # Построение графика
        ax.plot(train_data['Дата'], train_data['Цена'], marker='o', linestyle='-', color='b', label='Обучающие данные')
        ax.plot(test_data['Дата'], test_data['Цена'], marker='x', linestyle='-', color='g', label='Тестовые данные')
        ax.plot(pd.date_range(train_data['Дата'].max(), periods=len(future_predictions)+1, freq='D')[1:], future_predictions, linestyle='--', color='r', label='Экстраполяция вперед')
    else:
        # Построение графика без экстраполяции
        ax.plot(train_data['Дата'], train_data['Цена'], marker='o', linestyle='-', color='b', label='Обучающие данные')
        ax.plot(test_data['Дата'], test_data['Цена'], marker='x', linestyle='-', color='g', label='Тестовые данные')
        ax.plot(test_data['Дата'], model.predict(poly.transform(test_data['Дата_num'].values.reshape(-1, 1))), linestyle='--', color='r', label='Предсказания')

    ax.set_title(title, fontsize=14)
    ax.set_xlabel("Дата", fontsize=12)
    ax.set_ylabel("Цена (в рублях)", fontsize=12)
    ax.grid(True, which='both', linestyle='--', linewidth=0.5)
    ax.legend()
    ax.tick_params(axis='x', rotation=45)

# Первый график: 25% обучающих данных и 75% тестовых, степень полинома 2
train_size_1 = len(df) // 4
plot_graph(axs[0, 0], train_size_1, degree=2, title="25% обучающих и 75% тестовых")

# Второй график: 50% обучающих и 50% тестовых, степень полинома 2
train_size_2 = len(df) // 2
plot_graph(axs[0, 1], train_size_2, degree=2, title="50% обучающих и 50% тестовых")

# Третий график: 75% обучающих и 25% тестовых, степень полинома 3
train_size_3 = int(len(df) * 0.75)
plot_graph(axs[1, 0], train_size_3, degree=3, title="75% обучающих и 25% тестовых (степень 3)")

# Четвертый график: экстраполяция на 25% данных вперед, используя все данные для обучения
plot_graph(axs[1, 1], len(df), degree=3, title="Экстраполяция на 25% вперед (все данные)", extrapolate=True)

# Показываем графики
plt.tight_layout()
plt.show()
