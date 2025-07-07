# TradingBot for Tinkoff Sandbox

Бот, который торгует акциями на основе RSI и MACD, используя Tinkoff API.

## Возможности
- Получение свечей и индикаторов
- Генерация сигналов
- Выставление заявок в песочнице
- Визуализация графиков
- Логирование и симуляция торговли

```bash
project_root/
├── main.py                        # Главный async-бот
├── .env                           # API-ключи и секреты
├── config.yaml                    # Конфигурация стратегий, таймфреймов и т.п.
│
├── core/                          # Базовые классы и интерфейсы
│   ├── __init__.py
│   └── birza_api.py               # Абстрактный API-класс
│
├── api/                           # Реализации API для разных бирж
│   ├── __init__.py
│   └── bybit_api.py               # Реализация API через pybit
│
├── bots/                          # Подсистемы бота
│   ├── __init__.py
│   ├── databot.py                # API, данные, ордера
│   ├── strategybot.py            # Анализ и генерация сигналов
│   ├── loggerbot.py              # Логгер и обработка ошибок
│   └── plotbot.py                # Графики, визуализация, GUI
│
├── strategies/                    # Плагины стратегий
│   ├── __init__.py
│   ├── base.py                   # BaseStrategy
│   ├── rsi_macd.py               # RSI + MACD
│   └── breakout.py               # Пример альтернативной
│
├── ui/                            # Интерфейс (опционально)
│   └── streamlit_ui.py
│
├── logs/                          # Все логи
│   └── bot.log
└── data/                          # История свечей и сделок
    └── BTCUSDT_1m.csv
```
