import logging
import os
from dotenv import load_dotenv
from datetime import timedelta
import time

import csv
import pandas as pd

from tinkoff.invest import CandleInterval, Client
from tinkoff.invest.schemas import CandleSource, OrderDirection, OrderType, Quotation
from tinkoff.invest.utils import now
from tinkoff.invest.sandbox.client import SandboxClient

logging.basicConfig(format="%(asctime)s %(levelname)s:%(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)


import itertools
import sys
import time

def setup_global_logging(log_file="logs/general.log"):
    logs_dir = os.path.dirname(log_file)
    os.makedirs(logs_dir, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger("global_logger")

def loading_spinner(duration=60, message="Загрузка", portfolio=None):
    """
    Отображает вращающийся индикатор загрузки в командной строке.
    :param duration: Длительность загрузки в секундах.
    :param message: Сообщение, отображаемое рядом с индикатором.
    :param portfolio: Данные портфеля для отображения.
    """
    spinner = itertools.cycle(["⠋", "⠙", "⠸", "⠼", "⠴", "⠦"])  # Вращающийся индикатор
    start_time = time.time()

    while time.time() - start_time < duration:
        # Очищаем экран
        os.system("cls" if os.name == "nt" else "clear")

        # Формируем текст для отображения портфеля
        res = ""
        tot = 0
        if portfolio:
            for p in portfolio:
                res += f"FIGI: {p[0]}, Количество: {p[1]}, Цена: {p[2]}\n"
                if p[2] == 0:
                    tot += p[1]
                else:
                    tot += p[1] * p[2]
            res += f"Баланс: {tot}\n"

        # Выводим сообщение и данные
        sys.stdout.write(f"{message} {next(spinner)}\n{res}")
        sys.stdout.flush()
        time.sleep(0.1)  # Интервал обновления


class Analytic:
    def __init__(self,df, logger):
        self.df = df
        self.logger = logger
        self.indicators = self.Indicators(self)
    
    class Indicators:
        def __init__(self, parent):
            """
            Подкласс для расчёта индикаторов.
            :param parent: Ссылка на родительский объект Analytica.
            """
            self.parent = parent
        def sma(self, period=20, inplace=True):
            """
            Рассчёт SMA.
            """
            df = self.parent.df
            df["sma"] = df["close"].rolling(window=period).mean()
            if inplace:
                self.parent.df["sma"] = df["sma"]
            else:
                return df.copy()
        def rsi(self, period=14, inplace=True):
            """
            Рассчёт RSI (Relative Strength Index).
            """
            df = self.parent.df
            delta = df["close"].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            rs = gain / loss
            self.parent.logger.info(f"RSI расчитаны")
            if inplace:
                self.parent.df["rsi"] = 100 - (100 / (1 + rs))
            else:
                df_copy = df.copy()
                df_copy["rsi"] = 100 - (100 / (1 + rs))
                return df_copy
        def macd(self, short_window=12, long_window=26, signal_window=9, inplace=True):
            """
            Рассчёт индикатора MACD.
            """
            self.parent.logger.info("Вычисление MACD.")
            df = self.parent.df
            df["ema_short"] = df["close"].ewm(span=short_window, adjust=False).mean()
            df["ema_long"] = df["close"].ewm(span=long_window, adjust=False).mean()
            df["macd"] = df["ema_short"] - df["ema_long"]
            df["macd_signal"] = df["macd"].ewm(span=signal_window, adjust=False).mean()
            if inplace:
                self.parent.df[["ema_short", "ema_long", "macd", "macd_signal"]] = df[["ema_short", "ema_long", "macd", "macd_signal"]]
            else:
                return df[["ema_short", "ema_long", "macd", "macd_signal"]]
    
    def analyze_current(self, window=5):
        """
        Анализирует текущую ситуацию на основе последних `window` данных.
        Возвращает -1 (продажа), 0 (ничего не делать), 1 (покупка).
        """
        try:
            if len(self.df) < window:
                self.logger.warning("Недостаточно данных для анализа.")
                return 0  # Нейтральный сигнал при недостатке данных
            
            # Выбираем последние `window` строк
            recent_data = self.df.iloc[-window:]
            current = recent_data.iloc[-1]
            
            # Проверяем тренд цены
            sma_recent = recent_data["close"].mean()
            price_trend = current["close"] > sma_recent
            
            # MACD тренд
            macd_trend = recent_data["macd"].iloc[-1] > recent_data["macd_signal"].iloc[-1]
            
            # RSI перепроданность/перекупленность
            rsi_current = current["rsi"]

            # Сигнал на покупку
            if rsi_current < 30 and price_trend and macd_trend:
                self.logger.info("Сигнал на покупку: восходящий тренд, перепроданность.")
                return 1

            # Сигнал на продажу
            if rsi_current > 70 and not price_trend and not macd_trend:
                self.logger.info("Сигнал на продажу: нисходящий тренд, перекупленность.")
                return -1

            # Нейтральный сигнал
            self.logger.info("Сигнал отсутствует.")
            return 0
        except Exception as e:
            self.logger.error(f"Ошибка при анализе текущей ситуации: {e}")
            return 0

    def analyze_all(self):
        self.df["guess"] = 0
        for i in range(1, len(self.df)):
            if self.df["rsi"].iloc[i] < 30 and self.df["macd"].iloc[i] > self.df["macd_signal"].iloc[i]:
                self.df["guess"].iloc[i] = 1  # Покупка
            elif self.df["rsi"].iloc[i] > 70 and self.df["macd"].iloc[i] < self.df["macd_signal"].iloc[i]:
                self.df["guess"].iloc[i] = -1  # Продажа

    def plot_candles_with_indicators(self, title="График цен с индикаторами", sma_period=20, indicators=None, save=False):
        """
        Построение графика цен и индикаторов на отдельных сабплотах.
        :param title: Заголовок графика.
        :param sma_period: Период для скользящей средней.
        :param indicators: Список индикаторов для отображения.
        :param save: Если True, сохраняет график в папку 'pics'.
        """
        import seaborn as sns
        import os
        import matplotlib.pyplot as plt
        from matplotlib.gridspec import GridSpec
        from matplotlib.ticker import MaxNLocator

        try:
            self.df["time"] = pd.to_datetime(self.df["time"])
            if sma_period:
                self.df["sma"] = self.df["close"].rolling(window=sma_period).mean()

            plt.style.use('seaborn-darkgrid')
            sns.set_palette("muted")

            fig = plt.figure(figsize=(14, 10))
            gs = GridSpec(4, 1, figure=fig)  # 4 строки: 3 для цены, 1 для индикаторов
            
            ax1 = fig.add_subplot(gs[:3, 0]) 
            ax1.plot(self.df["time"], self.df["close"], label="Цена закрытия", linewidth=2, color="red")
            if sma_period:
                ax1.plot(self.df["time"], self.df["sma"], label=f"Скользящая средняя ({sma_period})", linewidth=2, color="purple")
            ax1.set_title(title, fontsize=16, weight="bold")
            ax1.set_xlabel("")
            ax1.set_ylabel("Цена (RUB)", fontsize=12, weight="bold")
            ax1.legend(fontsize=10)
            ax1.grid(alpha=0.1)
            ax1.xaxis.set_major_locator(MaxNLocator(10))
            if indicators:
                ax2 = fig.add_subplot(gs[3, 0])
                for ind in indicators:
                    if ind in self.df.columns:
                        ax2.plot(self.df["time"], self.df[ind], label=ind.capitalize(), linewidth=2)
                    else:
                        self.logger.warning(f"Индикатор '{ind}' отсутствует в данных.")
                ax2.set_xlabel("Дата", fontsize=12, weight="bold")
                ax2.set_ylabel("Индикаторы", fontsize=12, weight="bold")
                ax2.legend(fontsize=10)
                ax2.grid(alpha=0.1)
                ax2.xaxis.set_major_locator(MaxNLocator(10))
            plt.tight_layout()
            
            if save:
                os.makedirs("pics", exist_ok=True)
                plt.savefig(os.path.join("pics", "candle_with_indicators.png"), dpi=300)
                self.logger.info(f"График сохранён в 'pics/candle_with_indicators.png'.")
            else:
                self.logger.info("График успешно построен.")
            plt.show()
        except Exception as e:
            self.logger.error(f"Ошибка при построении графика: {e}")

    def plot_candles(self, title="График цен", sma_period=20, save=False):
        """
        Построение улучшенного графика цен из DataFrame с индикаторами.
        :param title: Заголовок графика.
        :param sma_period: Период для скользящей средней.
        :param save: Если True, сохраняет график в папку 'pics'.
        """
        import seaborn as sns
        import os
        import matplotlib.pyplot as plt
        from matplotlib.ticker import MaxNLocator
        try:
            self.df["time"] = pd.to_datetime(self.df["time"])
            if sma_period:
                self.df["sma"] = self.df["close"].rolling(window=sma_period).mean()
            
            plt.style.use('seaborn-darkgrid')
            sns.set_palette("muted")

            plt.figure(figsize=(14, 8))
            plt.plot(self.df["time"], self.df["close"], label="Цена закрытия", linewidth=2, color="red")
            
            if sma_period:
                plt.plot(self.df["time"], self.df["sma"], label=f"Скользящая средняя ({sma_period})", linewidth=2, color="purple")
            
            plt.gca().xaxis.set_major_locator(MaxNLocator(10))  # Ограничить количество дат на оси X
            plt.title(title, fontsize=16, weight="bold")
            plt.xlabel("Дата", fontsize=12, weight="bold")
            plt.ylabel("Цена (RUB)", fontsize=12, weight="bold")
            plt.grid(alpha=0.1)
            plt.legend(fontsize=12, loc="upper left")
            plt.tick_params(axis='both', which='major', labelsize=10)
            plt.tight_layout()

            if save:
                os.makedirs("pics", exist_ok=True)
                plt.savefig(os.path.join("pics", "candle_graph.png"), dpi=300)
                self.logger.info(f"График сохранён в 'pics/candle_graph.png'.")
            else:
                self.logger.info("График успешно построен.")
            plt.show()
            
        except Exception as e:
            self.logger.error(f"Ошибка при построении графика: {e}")


class Bot:
    def __init__(self, logger, initial_balance=100000,commission=0.003):
        self.balance = initial_balance
        self.initial_balance = initial_balance
        self.position = 0
        self.commission = commission
        self.trade_history = []
        self.logger = logger

    def setup_logging(self):
        """
        Настройка логирования.
        """
        logs_dir = os.path.join(os.getcwd(), "logs")
        os.makedirs(logs_dir, exist_ok=True)
        log_file = os.path.join(logs_dir, "test_logs.log")

        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(message)s",
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()  # Для вывода в консоль
            ]
        )
        self.logger = logging.getLogger(__name__)
        self.logger.info("Тестовый бот успешно инициализирован.")

    def process_signals(self, df):
        """
        Обработка сигналов из DataFrame.
        """
        for i, row in df.iterrows():
            if row["guess"] == 1 and self.position == 0:  # Сигнал на покупку
                self.position = self.balance // (row["close"]*(1+self.commission))
                self.balance -= self.position * row["close"]*(1+self.commission)
                trade = {"action": "buy", "price": row["close"], "date": row["time"]}
                self.trade_history.append(trade)
                self.logger.info(f"Покупка: {trade}")
            elif row["guess"] == -1 and self.position > 0:  # Сигнал на продажу
                self.balance += self.position * row["close"]*(1-self.commission)
                trade = {"action": "sell", "price": row["close"], "date": row["time"]}
                self.trade_history.append(trade)
                self.logger.info(f"Продажа: {trade}")
                self.position = 0

    def report(self):
        """
        Отчёт о результатах торговли.
        """
        final_balance = self.balance + (self.position * self.trade_history[-1]["price"] if self.position > 0 else 0)
        self.logger.info(f" Итоговый баланс: {final_balance}, профит: {final_balance - self.initial_balance}")
        for trade in self.trade_history:
            print(trade)



class TradeBot:
    def __init__(self,ticker, logger):
        from tinkoff.invest import Client
        load_dotenv()
        self.logger = logger
        self.TOKEN = os.environ["INVEST_TOKEN"]
        self.SANDTOKEN = os.environ["SANDBOX_TOKEN"]
        self.client = Client(self.TOKEN,sandbox_token=self.SANDTOKEN).__enter__()
        self.ticker = ticker
        self.figi = self.get_figi()
        self.sandbox = self.Sandbox(self)
    def __exit__(self, exc_type=None, exc_value=None, traceback=None):
        """
        Закрытие клиента и логирование.
        """
        try:
            if self.client:
                self.client.__exit__(exc_type, exc_value, traceback)
                self.client = None
                self.logger.info("Клиент успешно закрыт.")
        except Exception as e:
            self.logger.error(f"Ошибка при закрытии клиента: {e}")
    def __str__(self):
        """
        Формирование строкового представления аккаунтов.
        """
        try:
            print(self.client)
            accounts = self.client.users.get_accounts().accounts
            ret = []
            for account in accounts:
                ret.append(f"Account ID: {account.id}, Тип: {account.type}, Статус: {account.status}")
            return "\n".join(ret)
        except Exception as e:
            return f"Ошибка при проверке аккаунтов: {e}"
    def setup_logging(self):
        """
        Настройка логирования и создание папки logs.
        """
        logs_dir = os.path.join(os.getcwd(), "logs")
        os.makedirs(logs_dir, exist_ok=True)
        log_file = os.path.join(logs_dir, "bot.log")

        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(message)s",
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()  # Для вывода в консоль
            ]
        )
        self.logger = logging.getLogger(__name__)
        self.logger.info("Логирование бота настроено.")
    def get_figi(self):
        try:
            r = self.client.instruments.find_instrument(query=self.ticker,instrument_kind=2)
            if r.instruments:
                for i in r.instruments:
                    print(f"{i.name}:  {i.figi}, {i.instrument_type}, API={i.api_trade_available_flag}")
                    if i.api_trade_available_flag and i.instrument_type == "share":
                        figi = i.figi
                        self.logger.info(f"Найден FIGI для тикера {self.ticker}: {figi}")
                        return figi
                self.logger.warning(f"Тикер {self.ticker} нет торгуемых через API.")
                return False
            else:
                self.logger.warning(f"Тикер {self.ticker} не найден.")
                return False
        except Exception as e:
            self.logger.error(f"Ошибка при получении FIGI для тикера {self.ticker}: {e}")
            return None   


    
 
    def get_candles(self, days= 100, interval=CandleInterval.CANDLE_INTERVAL_HOUR):
        """
        Сохраняет свечи актива в CSV файл.

        :param days: период данных в днях (по умолчанию 365)
        :param interval: интервал свечей (по умолчанию почасовые)
        """
        try:
            filename = f"candles_{self.ticker}.csv"
            file_path = os.path.join("data", filename)
            os.makedirs("data", exist_ok=True)
            
            with open(file_path, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["time", "open", "high", "low", "close", "volume", "orders"])
                orders = self.sandbox.get_orders_history(days)
                # Получение данных
                r = self.client.market_data.get_trading_status(figi=self.figi)
                response = self.client.market_data.get_candles(
                    instrument_id=self.figi,
                    from_=now() - timedelta(days=days),
                    to=now(),
                    interval=interval
                )
                if response.candles:
                    for candle in response.candles:
                        order_quantity = orders.get(candle.time, 0)
                        writer.writerow([
                            candle.time,
                            candle.open.units + candle.open.nano * 1e-9,
                            candle.high.units + candle.high.nano * 1e-9,
                            candle.low.units + candle.low.nano * 1e-9,
                            candle.close.units + candle.close.nano * 1e-9,
                            candle.volume,
                            order_quantity
                        ])
                else:
                    self.logger.warning(f"Нет данных для {self.ticker}.")
            self.logger.info(f"Данные успешно сохранены в {file_path}")
        except Exception as e:
            self.logger.error(f"Ошибка при сохранении свечей: {e}")

    class Sandbox:
        def __init__(self, parent):
            """
            Инициализация песочницы.
            :param parent: Ссылка на родительский объект Bot.
            """
            self.parent = parent
            self.logger = self.parent.logger
            self.account_id = None
            self.sandcli = SandboxClient(parent.TOKEN, sandbox_token = parent.SANDTOKEN).__enter__()
            self.initialize_sandbox()    
        def __exit__(self, exc_type=None, exc_value=None, traceback=None):
            try:
                self.sandcli.__exit__(exc_type, exc_value, traceback)
                self.parent.logger.info("Клиент песочницы успешно закрыт.")
            except Exception as e:
                self.parent.logger.error(f"Ошибка при закрытии клиента песочницы: {e}")
        def __str__(self):
            """
            Получение состояния песочничного портфеля.
            """
            try:
                ret = ""
                portfolio = self.sandcli.operations.get_portfolio(account_id=self.account_id)
                ret+=("\n--"*20+"\n")
                ret+=(f"В акциях: {portfolio.total_amount_shares.units} {portfolio.total_amount_shares.currency}\n")
                for position in portfolio.positions:
                        ret+=(f"FIGI: {position.figi}, Количество: {position.quantity.units}, Цена: {position.current_price.units}\n")
                ret+=("--"*20+"\n")
                self.logger.info(ret)
                return ret
            except Exception as e:
                self.logger.error(f"Ошибка при получении портфеля: {e}")        
        
        def initialize_sandbox(self):
            """
            Создание аккаунта в песочнице.
            """
            try:
                response = self.sandcli.users.get_accounts().accounts
                self.account_id = response[0].id
                self.parent.logger.info(f"Создан песочничный аккаунт: {self.account_id}")
            except Exception as e:
                self.parent.logger.error(f"Ошибка при создании песочничного аккаунта: {e}")
        def clean_sandbox_accounts(self, keep_account_id=None):
            """
            Удаляет все песочничные аккаунты, кроме одного.
            :param keep_account_id: ID аккаунта, который нужно сохранить (None для сохранения первого).
            """
            try:
                accounts = self.sandcli.users.get_accounts().accounts
                self.logger.info(f"Найдено {len(accounts)} аккаунтов песочницы.")
                
                for account in accounts:
                    if account.id != keep_account_id:
                        self.sandcli.sandbox.close_sandbox_account(account_id=account.id)
                        self.logger.info(f"Аккаунт {account.id} закрыт.")
                    else:
                        self.logger.info(f"Аккаунт {account.id} сохранён.")
            except Exception as e:
                self.logger.error(f"Ошибка при очистке песочничных аккаунтов: {e}")


        def deposit(self, amount=100000):
            """
            Пополнение песочничного аккаунта.
            """
            try:
                self.sandcli.sandbox.sandbox_pay_in(
                    account_id=self.account_id,
                    amount=Quotation(units=amount, nano=0)
                )
                self.logger.info(f"Пополнен песочничный аккаунт на {amount} рублей.")
            except Exception as e:
                self.logger.error(f"Ошибка при пополнении песочничного аккаунта: {e}")

        
        def get_portfolio(self):
            """
            Возвращает данные о открытых позициях
            """
            try:
                portfolio = self.sandcli.operations.get_portfolio(account_id=self.account_id)
                response = []
                for position in portfolio.positions:
                    response.append([position.figi,position.quantity.units,position.current_price.units])
                return response
            except Exception as e:
                self.logger.error(f"Ошибка при получении портфеля: {e}")


        def signal_trade(self, signal, price):
            if signal == 1:
                self.order(2, price)
            if signal == -1:
                self.order(2,price, direction=OrderDirection.ORDER_DIRECTION_SELL)

        def order(self, quantity, price, direction=OrderDirection.ORDER_DIRECTION_BUY):
            try:
                response = self.sandcli.orders.post_order(
                    figi=self.parent.figi,
                    quantity=quantity,
                    price=Quotation(units=price, nano=0),
                    account_id=self.account_id,
                    order_type=OrderType.ORDER_TYPE_LIMIT,
                    direction=direction
                )
                self.logger.info(
                    f"Ордер {quantity} акций {self.parent.ticker} по цене {price}. "
                    f"Направление: {'Покупка' if direction == OrderDirection.ORDER_DIRECTION_BUY else 'Продажа'}. "
                    f"Ордер ID: {response.order_id}"
                )
            except Exception as e:
                self.logger.error(f"Ошибка при отправке ордера: {e}")
        def get_orders_history(self, days):
            """
            Получает историю сделок для аккаунта за указанный период.
            :param days: Период в днях.
            :return: Словарь с временем сделки и количеством.
            """
            try:
                operations = self.sandcli.operations.get_operations(
                    account_id=self.account_id,
                    from_=now() - timedelta(days=days),
                    to=now(),
                    figi=self.figi
                )

                orders = {}
                for operation in operations.operations:
                    operation_time = operation.date.replace(second=0, microsecond=0)  # Округляем до минуты
                    quantity = operation.quantity
                    if operation.operation_type == "Buy":
                        orders[operation_time] = orders.get(operation_time, 0) + quantity
                    elif operation.operation_type == "Sell":
                        orders[operation_time] = orders.get(operation_time, 0) - quantity

                return orders
            except Exception as e:
                self.logger.error(f"Ошибка при получении истории сделок: {e}")
                return {}






def main():    
    load_dotenv()
    ticker = "LKOH"
    logger = setup_global_logging()
    bot = TradeBot(ticker, logger)
    print(bot.sandbox)

    
    # analitic.plot_candles_with_indicators(
    # title=f"График цен {ticker}",
    # sma_period=20,
    # indicators=["rsi", "macd", "macd_signal"],
    # save=True
    # )

    # Анализ текущей ситуации
    N=120
    for i in range(N):
        bot.get_candles(days=1,interval=CandleInterval.CANDLE_INTERVAL_1_MIN)
        df = pd.read_csv(f"data/candles_{ticker}.csv")
        analitic = Analytic(df,logger)
        analitic.indicators.sma()
        analitic.indicators.macd()
        analitic.indicators.rsi()

        current_price = df["close"].iloc[-1]
        if i//5 == 0:
            bot.sandbox.order(2,current_price)
        elif i//5 == 3:
            bot.sandbox.order(2,current_price,direction=OrderDirection.ORDER_DIRECTION_SELL)
        signal = analitic.analyze_current(window=10)

        bot.sandbox.signal_trade(signal,current_price)

        portfolio = bot.sandbox.get_portfolio()
        loading_spinner(duration=60, message=f"Ожидание следующего цикла ({i + 1}/{N})", portfolio = portfolio)

    bot.sandbox.get_portfolio()
    # analitic.analyze_all()
    # # Торговля
    # bot1 = Bot(loggerinitial_balance=100000,commission=0.003)
    # bot1.process_signals(analitic.df)
    # bot1.report()

if __name__ == "__main__":
    main()
