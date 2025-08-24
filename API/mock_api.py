# API/mock_api.py

import os
import json
import random
import asyncio
import pandas as pd
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta, timezone

from API import BirzaAPI


class MockAPI(BirzaAPI):
    """
    Живой мок-API: генерирует OHLCV по random-walk, дописывает новые свечи,
    слегка двигает текущую свечу между «клоузами», обновляет баланс/позиции.

    ДОБАВЛЕНО:
      • Полноценные сделки на споте с комиссиями и учётом среднего входа
      • Реализованный/нереализованный PnL
      • История ордеров в памяти и трейды в DATA/static/trades.csv
      • Стоимость портфеля в state.json (equity)
    """

    def __init__(self, data_dir: str = "DATA", log_file: Optional[str] = "LOGS/mock_api.log", console: bool = True):
        super().__init__(name="MockAPI", log_tag="[MOCK_API]", log_file=log_file, console=console)

        self.data_dir = data_dir
        os.makedirs(self.data_dir, exist_ok=True)

        # Кэш данных по ключу "SYMBOL_TIMEFRAME"
        self.mock_data: Dict[str, pd.DataFrame] = {}

        # Денежка и активы
        self.mock_balance: Dict[str, float] = {
            "BTC": 0.0,
            "ETH": 0.0,
            "USDT": 10_000.0,
            "USD": 0.0,
        }

        # Позиции: только спот, без шортов
        # { "BTC/USDT": {size, avg_price, realized_pnl, markPrice} }
        self.mock_positions: Dict[str, Dict[str, Any]] = {}

        # История ордеров в памяти
        self.mock_orders: List[Dict[str, Any]] = []

        # Файл для трейдов
        self.trades_path = os.path.join(self.data_dir, "static", "trades.csv")
        os.makedirs(os.path.dirname(self.trades_path), exist_ok=True)
        if not os.path.exists(self.trades_path):
            pd.DataFrame(columns=[
                "datetime", "symbol", "side", "qty", "price", "cost", "fee",
                "realized_pnl", "balance_usdt"
            ]).to_csv(self.trades_path, index=False)

        self.logger.info(f"Initialized MockAPI with data directory: {self.data_dir}")

    # ---------- helpers ----------

    @staticmethod
    def _key(symbol: str, timeframe: str) -> str:
        return f"{symbol}_{timeframe}"

    @staticmethod
    def _tf_delta(timeframe: str) -> timedelta:
        tf = timeframe.lower()
        if tf.endswith("m"):
            return timedelta(minutes=int(tf[:-1]))
        if tf.endswith("h"):
            return timedelta(hours=int(tf[:-1]))
        if tf.endswith("d"):
            return timedelta(days=int(tf[:-1]))
        return timedelta(hours=1)

    @staticmethod
    def _align(dt: datetime, tf_delta: timedelta) -> datetime:
        # Выравнивание к началу «свечной» сетки
        if tf_delta >= timedelta(days=1):
            base = datetime(dt.year, dt.month, dt.day)
            return base
        if tf_delta >= timedelta(hours=1):
            step = tf_delta.seconds // 3600
            return datetime(dt.year, dt.month, dt.day, (dt.hour // step) * step)
        # минуты
        step = tf_delta.seconds // 60
        return datetime(dt.year, dt.month, dt.day, dt.hour, (dt.minute // step) * step)

    def _default_start_price(self, symbol: str) -> Tuple[float, float]:
        if symbol.upper().startswith("BTC"):
            return 30000.0, 0.02
        if symbol.upper().startswith("ETH"):
            return 2000.0, 0.03
        return 100.0, 0.05

    def _csv_path(self, symbol: str, timeframe: str) -> str:
        return os.path.join(self.data_dir, f"{symbol.replace('/', '')}_{timeframe}.csv")

    def _load_or_generate(self, symbol: str, timeframe: str, num_candles: int = 500) -> pd.DataFrame:
        key = self._key(symbol, timeframe)
        if key in self.mock_data:
            return self.mock_data[key]

        path = self._csv_path(symbol, timeframe)
        if os.path.exists(path):
            try:
                df = pd.read_csv(path)
                if "time" in df.columns:
                    df["time"] = pd.to_datetime(df["time"])
                else:
                    # редкий случай: старый формат с timestamp
                    if "timestamp" in df.columns:
                        df["time"] = pd.to_datetime(df["timestamp"])
                # нормализуем набор столбцов
                cols = ["time", "open", "high", "low", "close", "volume"]
                for c in cols:
                    if c not in df.columns:
                        df[c] = pd.NA
                df = df[cols].dropna(subset=["time"]).reset_index(drop=True)
                self.mock_data[key] = df
                return df
            except Exception as e:
                self.logger.warning(f"Failed to load existing CSV '{path}': {e}")

        # Сгенерируем историю
        price0, vol = self._default_start_price(symbol)
        tf_delta = self._tf_delta(timeframe)

        end = self._align(datetime.now(), tf_delta)
        times = [end - tf_delta * i for i in range(num_candles)][::-1]

        prices = [price0]
        for _ in range(1, num_candles):
            change = prices[-1] * random.uniform(-vol, vol)
            prices.append(max(0.01, prices[-1] + change))

        rows = []
        for i, t in enumerate(times):
            p = prices[i]
            h = p * (1 + random.uniform(0, vol * 0.5))
            l = p * (1 - random.uniform(0, vol * 0.5))
            o = p * (1 + random.uniform(-vol * 0.25, vol * 0.25))
            c = p * (1 + random.uniform(-vol * 0.25, vol * 0.25))
            v = p * random.uniform(10, 100)
            rows.append({"time": t, "open": o, "high": h, "low": l, "close": c, "volume": v})

        df = pd.DataFrame(rows)
        self.mock_data[key] = df
        # сразу сохраним на диск
        df.to_csv(self._csv_path(symbol, timeframe), index=False)
        return df

    def _append_next_bar(self, df: pd.DataFrame, tf_delta: timedelta, vol: float) -> None:
        """Синтез следующего бара на основе последнего close."""
        if df.empty:
            return
        last = df.iloc[-1]
        base = float(last["close"])
        t_next = pd.to_datetime(last["time"]) + tf_delta

        # ограничим волатильность разумно
        change = base * random.uniform(-vol, vol)
        p = max(0.01, base + change)
        high = max(p, base) * (1 + random.uniform(0, vol * 0.3))
        low = min(p, base) * (1 - random.uniform(0, vol * 0.3))
        open_price = base * (1 + random.uniform(-vol * 0.2, vol * 0.2))
        close = p * (1 + random.uniform(-vol * 0.15, vol * 0.15))
        volume = p * random.uniform(10, 100)

        df.loc[len(df)] = {
            "time": t_next,
            "open": open_price,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
        }

    def _jitter_current_bar(self, df: pd.DataFrame, vol: float) -> None:
        """Небольшое движение внутри текущего бара."""
        if df.empty:
            return
        i = len(df) - 1
        row = df.iloc[i]
        close = float(row["close"])
        new_close = max(0.01, close * (1 + random.uniform(-vol * 0.02, vol * 0.02)))

        new_high = max(float(row["high"]), new_close)
        new_low = min(float(row["low"]), new_close)
        new_vol = float(row["volume"]) * (1 + random.uniform(-0.02, 0.08))

        df.at[i, "close"] = new_close
        df.at[i, "high"] = new_high
        df.at[i, "low"] = new_low
        df.at[i, "volume"] = new_vol

    def _ensure_fresh(self, symbol: str, timeframe: str) -> pd.DataFrame:
        """Догенерировать данные до «текущего» времени и сохранить CSV."""
        df = self._load_or_generate(symbol, timeframe)
        tf_delta = self._tf_delta(timeframe)
        _price0, vol = self._default_start_price(symbol)

        # текущее целевое время
        now_aligned = self._align(datetime.now(), tf_delta)

        # последняя точка в данных
        last_time = pd.to_datetime(df["time"].iloc[-1])

        # если мы отстаем на несколько интервалов — догоняем барами
        while last_time + tf_delta <= now_aligned:
            self._append_next_bar(df, tf_delta, vol)
            last_time = pd.to_datetime(df["time"].iloc[-1])

        # если новый бар «ещё не настал», шевельнём текущую свечу
        if last_time == now_aligned:
            self._jitter_current_bar(df, vol)

        # сохраняем файл каждый раз, чтобы фронт видел обновления
        path = self._csv_path(symbol, timeframe)
        try:
            df.to_csv(path, index=False)
        except Exception as e:
            self.logger.error(f"Failed to write CSV '{path}': {e}")

        return df

    # ---------- market data ----------

    def _last_price(self, symbol: str) -> float:
        df = self._ensure_fresh(symbol, "1m")
        return float(df["close"].iloc[-1]) if not df.empty else 0.0

    # ---------- public: OHLCV ----------

    def get_ohlcv(self, symbol: str, timeframe: str = "1m", limit: int = 100) -> pd.DataFrame:
        try:
            self.logger.info(f"Fetching mock OHLCV: {symbol} {timeframe} limit={limit}")
            df = self._ensure_fresh(symbol, timeframe)
            out = df.tail(max(1, int(limit))).reset_index(drop=True).copy()
            # убедимся, что time будет сериализуемым
            out["time"] = pd.to_datetime(out["time"])
            return out
        except Exception as e:
            return self._handle_error(f"fetching mock OHLCV for {symbol}", e, pd.DataFrame())

    async def get_ohlcv_async(self, symbol: str, timeframe: str = "1m", limit: int = 100) -> pd.DataFrame:
        await asyncio.sleep(0)  # имитация I/O
        return self.get_ohlcv(symbol, timeframe, limit)

    # ---------- public: orders/balance/positions ----------

    def place_order(self, symbol: str, side: str, qty: float,
                    order_type: str = "market", price: Optional[float] = None) -> Dict[str, Any]:
        """
        Спот‑исполнение по последней цене. Никаких шортов.
        Если пытаемся продать больше, чем есть, продаём сколько есть.
        Комиссия 0.1% в валюте котировки. Средняя цена входа пересчитывается.
        """
        try:
            self.logger.info(f"Creating mock order: {side.upper()} {qty} {symbol} ({order_type})")
            # текущая цена
            current_price = self._last_price(symbol)
            if order_type.lower() == "limit" and price is not None:
                exec_price = float(price)
            else:
                exec_price = current_price

            base, quote = symbol.split("/") if "/" in symbol else (symbol, "USDT")
            qty = float(qty)
            side = side.lower()
            fee_rate = 0.001

            # позиция
            pos = self.mock_positions.get(symbol, {"size": 0.0, "avg_price": 0.0, "realized_pnl": 0.0})
            size = float(pos["size"])
            avg_price = float(pos["avg_price"])
            realized_pnl = float(pos["realized_pnl"])

            # ограничение на продажу
            if side == "sell" and qty > size:
                qty = size  # продаём не больше, чем есть

            if qty <= 0:
                return {"error": "qty<=0", "status": "rejected"}

            cost = exec_price * qty
            fee = cost * fee_rate

            if side == "buy":
                # проверим баланс котировки
                free_quote = self.mock_balance.get(quote, 0.0)
                total_needed = cost + fee
                if total_needed > free_quote:
                    # уменьшаем размер до доступного баланса
                    if exec_price <= 0:
                        return {"error": "bad price", "status": "rejected"}
                    qty = max(0.0, (free_quote / (1 + fee_rate)) / exec_price)
                    cost = exec_price * qty
                    fee = cost * fee_rate
                # списываем
                self.mock_balance[quote] = self.mock_balance.get(quote, 0.0) - (cost + fee)
                self.mock_balance[base] = self.mock_balance.get(base, 0.0) + qty
                # новая ср. цена
                new_size = size + qty
                if new_size > 0:
                    avg_price = (size * avg_price + qty * exec_price) / new_size
                size = new_size

            else:  # sell
                # списываем базовый, начисляем котировку
                self.mock_balance[base] = self.mock_balance.get(base, 0.0) - qty
                self.mock_balance[quote] = self.mock_balance.get(quote, 0.0) + (cost - fee)
                # реализованный PnL по проданной части
                realized_pnl += (exec_price - avg_price) * qty
                size = size - qty
                if size <= 1e-12:
                    size = 0.0
                    avg_price = 0.0  # позиция закрыта

            # комиссия оплачивается из котировки
            # уже учтена выше, но для явности занесём валюту
            self.mock_balance[quote] = self.mock_balance.get(quote, 0.0)

            # пересчёт позы и марк‑цены
            mark_price = self._last_price(symbol)
            self.mock_positions[symbol] = {
                "symbol": symbol,
                "size": size,
                "side": "long" if size > 0 else "none",
                "entryPrice": avg_price if size > 0 else None,
                "avg_price": avg_price,
                "markPrice": mark_price,
                "unrealizedPnl": (mark_price - avg_price) * size if size > 0 else 0.0,
                "realized_pnl": realized_pnl,
                "timestamp": int(datetime.now().timestamp() * 1000),
                "datetime": datetime.now(timezone.utc).isoformat()
            }

            order_id = f"mock_{int(datetime.now().timestamp()*1000)}"
            order = {
                "id": order_id,
                "symbol": symbol,
                "side": side,
                "type": order_type.lower(),
                "price": exec_price,
                "amount": qty,
                "cost": cost,
                "timestamp": int(datetime.now().timestamp() * 1000),
                "datetime": datetime.now(timezone.utc).isoformat(),
                "status": "closed" if order_type.lower() == "market" else "open",
                "filled": qty,
                "remaining": 0.0,
                "fee": {"cost": fee, "currency": quote},
            }
            self.mock_orders.append(order)

            # запись трейда в CSV
            try:
                bal_usdt = float(self.mock_balance.get("USDT", 0.0))
                row = {
                    "datetime": order["datetime"],
                    "symbol": symbol,
                    "side": side,
                    "qty": qty,
                    "price": exec_price,
                    "cost": cost,
                    "fee": fee,
                    "realized_pnl": realized_pnl,
                    "balance_usdt": bal_usdt,
                }
                pd.DataFrame([row]).to_csv(self.trades_path, mode="a", header=False, index=False)
            except Exception as e:
                self.logger.warning(f"Failed to append trade row: {e}")

            return order
        except Exception as e:
            return self._handle_error(f"placing mock {order_type} order for {symbol}", e, {})

    async def place_order_async(self, symbol: str, side: str, qty: float,
                                order_type: str = "market", price: Optional[float] = None) -> Dict[str, Any]:
        await asyncio.sleep(0)
        return self.place_order(symbol, side, qty, order_type, price)

    def get_balance(self) -> Dict[str, Any]:
        try:
            self.logger.info("Fetching mock balance")
            return dict(self.mock_balance)
        except Exception as e:
            return self._handle_error("fetching mock balance", e, {})

    async def get_balance_async(self) -> Dict[str, Any]:
        await asyncio.sleep(0)
        return self.get_balance()

    def get_positions(self, symbol: str) -> Dict[str, Any]:
        try:
            self.logger.info(f"Fetching mock positions for {symbol}")
            return self.mock_positions.get(symbol, {})
        except Exception as e:
            return self._handle_error(f"fetching mock positions for {symbol}", e, {})

    async def get_positions_async(self, symbol: str) -> Dict[str, Any]:
        await asyncio.sleep(0)
        return self.get_positions(symbol)

    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        try:
            # Минимальная заглушка: в реале хранили бы заказы
            for o in reversed(self.mock_orders):
                if o["id"] == order_id:
                    return {"id": order_id, "status": o["status"]}
            return {"id": order_id, "status": "unknown"}
        except Exception as e:
            return self._handle_error(f"checking status of mock order {order_id}", e, {})

    async def get_order_status_async(self, order_id: str) -> Dict[str, Any]:
        await asyncio.sleep(0)
        return self.get_order_status(order_id)

    # ---------- state.json ----------

    async def update_state(self, symbol: str = "BTC/USDT", STATE_PATH: str = "DATA/static/state.json"):
        """
        Пишет state.json для дашборда:
          • balance: остатки по валютам
          • positions: список поз
          • equity: USDT + Σ(size*markPrice по символам с котировкой USDT)
        """
        try:
            bal = await self.get_balance_async()
            quote = symbol.split("/")[1] if "/" in symbol else "USDT"

            # оценка портфеля
            equity = float(bal.get("USDT", 0.0))
            positions = []
            for sym, pos in self.mock_positions.items():
                mark = float(pos.get("markPrice") or self._last_price(sym))
                qty = float(pos.get("size", 0.0))
                entry = float(pos.get("avg_price", 0.0))
                unreal = (mark - entry) * qty if qty > 0 else 0.0
                positions.append({
                    "symbol": sym,
                    "qty": qty,
                    "entry": entry,
                    "price": mark,
                    "unrealized_pnl": unreal,
                })
                # учитываем только пары с котировкой USDT
                if "/" in sym and sym.split("/")[1] == "USDT":
                    equity += qty * mark

            state = {
                "balance": bal,
                "equity": {"total": equity, "currency": "USDT"},
                "positions": positions,
                "updated": datetime.now(timezone.utc).isoformat(),
            }

            os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
            with open(STATE_PATH, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2, ensure_ascii=False)

            self.logger.info(f"state.json updated: {STATE_PATH}")
        except Exception as e:
            self.logger.error(f"Failed to update state.json: {e}")

    # ---------- missing abstract methods ----------

    def download_candels_to_csv(self, symbol: str, start_date: str = "2023-01-01T00:00:00Z",
                               timeframe: str = "1h", save_folder: str = "DATA") -> pd.DataFrame:
        """
        Download historical candle data and save to CSV (mock implementation).
        """
        try:
            self.logger.info(f"Downloading mock historical data for {symbol} from {start_date}, timeframe={timeframe}")
            
            # Генерируем исторические данные
            df = self._load_or_generate(symbol, timeframe, num_candles=500)
            
            if save_folder is not None:
                file_name = f'{symbol.replace("/", "")}_{timeframe}.csv'
                save_path = f'{save_folder}/{file_name}'
                
                try:    
                    os.makedirs(save_folder, exist_ok=True)
                    df.to_csv(save_path, index=False)
                    self.logger.info(f"Mock data saved to: {save_path}")
                except Exception as e:
                    return self._handle_error(f"saving mock data to {save_path}", e, df)
            
            return df
        except Exception as e:
            return self._handle_error(f"downloading mock data for {symbol}", e, pd.DataFrame())

    async def download_candels_to_csv_async(self, symbol: str, start_date: str = "2023-01-01T00:00:00Z",
                               timeframe: str = "1h", save_folder: str = "DATA") -> pd.DataFrame:
        """
        Asynchronously download historical candle data and save to CSV (mock implementation).
        """
        await asyncio.sleep(0)  # имитация I/O
        return self.download_candels_to_csv(symbol, start_date, timeframe, save_folder)

    async def close_async(self):
        """
        Close async connections (mock implementation - no actual connections to close).
        """
        self.logger.info("MockAPI async connections closed (no actual connections)")
        pass
