from flask import Flask, request, send_from_directory, jsonify, send_file
import os,sys
import json
from collections import deque
import pandas as pd

# ---------------------------
# Папки проекта
# ---------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))              # .../API
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, ".."))       # корень проекта
DATA_DIR = os.path.join(PROJECT_ROOT, "DATA")
LOGS_DIR = os.path.join(PROJECT_ROOT, "LOGS")
STATIC_DATA_DIR = os.path.join(DATA_DIR, "static")
os.makedirs(STATIC_DATA_DIR, exist_ok=True)

app = Flask(__name__)

def run_flask_in_new_terminal():
    import webbrowser
    import time, platform
    import subprocess
    """
    Запускает Flask-приложение в новом терминале (Windows).
    """
    script_path = os.path.abspath(__file__)
    if platform.system() == "Windows":
       flask_process = subprocess.Popen(f'start cmd /k "{sys.executable} {script_path}"', shell=True)
    elif platform.system() == "Linux":
        for term in ["gnome-terminal", "x-terminal-emulator", "xterm", "konsole"]:
            try:
                flask_process = subprocess.Popen([term, "-e", f"{sys.executable} {script_path}"])
                return
            except FileNotFoundError:
                continue
    else:
        raise ValueError("Платформа компьютера не определена")
    time.sleep(3)
    # Открыть браузер
    webbrowser.open("http://127.0.0.1:5000")
    return flask_process

def stop_flask(flask_process):
    if flask_process and flask_process.poll() is None:
        flask_process.terminate()
        flask_process.wait(timeout=5)

def get_csv_list() -> list[str]:
    """Все CSV в папке DATA."""
    files = [f for f in os.listdir(DATA_DIR) if f.endswith(".csv")]
    files.sort()
    return files

def get_anal_list() -> list[str]:
    """Все CSV с суффиксом _anal.csv."""
    return [f for f in get_csv_list() if f.endswith("_anal.csv")]

def safe_path(base_dir: str, filename: str) -> str:
    # Защита от traversal и только внутри base_dir
    filename = os.path.basename(filename)
    full_path = os.path.join(base_dir, filename)
    if not os.path.abspath(full_path).startswith(os.path.abspath(base_dir)):
        raise ValueError("Недопустимый путь")
    return full_path

@app.route("/")
def index():
    return send_file(os.path.join(BASE_DIR, "index.html"))

# ОТДАЧА CSV-файла (как есть) — на случай, если нужно
@app.route("/candles")
def candles():
    anal = get_anal_list()
    if not anal:
        return "", 204
    chosen = request.args.get("file")
    if chosen not in anal:
        chosen = anal[0]
    return send_from_directory(DATA_DIR, chosen)

# JSON-свечи для интерактивного графика Plotly

    
@app.route("/api/candles")
def api_candles():
    """
    Параметры:
      - file: имя CSV из списка *_anal.csv (автоматически берётся первый, если параметр не задан или не найден)
      - tail: сколько последних строк вернуть (по умолчанию 500)
    Формат ответа: [{ts, open, high, low, close, volume}, ...]
    """
    # 1. Собираем все анал-файлы
    anal = get_anal_list()
    if not anal:
        # нет ни одного *_anal.csv — возвращаем пустой массив
        return jsonify([])

    # 2. Выбираем файл: если пришёл параметр и он валиден — берём его, иначе первый из списка
    requested = request.args.get("file")
    csv_file = requested if requested in anal else anal[0]

    # 3. Проверяем путь
    try:
        csv_path = safe_path(DATA_DIR, csv_file)
    except ValueError:
        return jsonify({"error": "Некорректное имя файла"}), 400

    if not os.path.exists(csv_path):
        return jsonify({"error": "Файл не найден"}), 404

    # 4. Читаем параметр tail
    tail_rows = int(request.args.get("tail", "500"))

    # 5. Загружаем CSV и формируем JSON
    try:
        df = pd.read_csv(csv_path)

        # находим колонки времени и OHLCV
        time_cols = [c for c in df.columns if c.lower() in ("time", "timestamp", "date", "datetime")]
        o = next((c for c in df.columns if c.lower()=="open"), None)
        h = next((c for c in df.columns if c.lower()=="high"), None)
        l = next((c for c in df.columns if c.lower()=="low"), None)
        c = next((c for c in df.columns if c.lower()=="close"), None)
        v = next((c for c in df.columns if c.lower() in ("volume", "vol")), None)

        if not time_cols or not all([o, h, l, c]):
            return jsonify({"error": "Не найдены необходимые колонки для OHLC"}), 400

        # приводим время к строкам ISO, где возможно
        tcol = time_cols[0]
        ts_series = pd.to_datetime(df[tcol], errors="coerce")
        ts_values = [
            (ts.isoformat() if pd.notna(ts) else str(orig))
            for ts, orig in zip(ts_series, df[tcol])
        ]

        # обрезаем хвост
        if tail_rows > 0:
            df = df.tail(tail_rows)
            ts_values = ts_values[-len(df):]

        # строим итоговый список
        result = []
        for i, row in df.reset_index(drop=True).iterrows():
            item = {
                "ts":    ts_values[i],
                "open":  float(row[o]),
                "high":  float(row[h]),
                "low":   float(row[l]),
                "close": float(row[c]),
                "volume": float(row[v]) if v in df.columns else None
            }
            result.append(item)

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": f"Ошибка обработки CSV: {e}"}), 500


# Список лог-файлов
@app.route("/logs")
def list_logs():
    files = [f for f in os.listdir(LOGS_DIR) if f.endswith(".log")]
    files.sort()
    return jsonify(files)

# Возврат целого лог-файла (осталось для совместимости)
@app.route("/log/<filename>")
def get_log_file(filename):
    try:
        log_path = safe_path(LOGS_DIR, filename)
    except Exception:
        return "Некорректное имя файла", 400
    if not os.path.exists(log_path):
        return "Файл не найден", 404
    with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()

# Хвост лог-файла (эффективный tail)
@app.route("/api/log_tail")
def log_tail():
    filename = request.args.get("filename")
    n = int(request.args.get("n", "500"))
    if not filename:
        return jsonify({"error": "Не передано имя файла"}), 400
    try:
        log_path = safe_path(LOGS_DIR, filename)
    except Exception:
        return jsonify({"error": "Некорректное имя файла"}), 400
    if not os.path.exists(log_path):
        return jsonify({"error": "Файл не найден"}), 404

    dq = deque(maxlen=max(n, 1))
    with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            dq.append(line.rstrip("\n"))
    return jsonify({"lines": list(dq)})

# Список CSV в DATA
@app.route("/csv_list")
def list_csv_files():
    return jsonify(get_csv_list())


# Простое состояние (если есть state.json в корне проекта)
@app.route("/api/state")
def state():
    from datetime import datetime, timezone
    state_path = os.path.join(STATIC_DATA_DIR, "state.json")
    if os.path.exists(state_path):
        try:
            with open(state_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            # если есть поле updated — форматируем его
            ts = data.get("updated")
            if ts:
                try:
                    # Парсим ISO-строку (с учётом часового пояса)
                    dt = datetime.fromisoformat(ts)
                    # Переводим в локальную зону (если нужно)
                    dt_local = dt.astimezone()  
                    # Форматируем без микросекунд
                    data["updated"] = dt_local.strftime("%d.%m.%Y %H:%M:%S")
                except Exception as e:
                    app.logger.error(f"Не удалось распарсить updated: {e}")
            # Запрещаем кэширование этого ответа
            resp = jsonify(data)
            resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            return resp
        except Exception as e:
            app.logger.error(f"Error reading state.json: {e}")
    # fallback
    return jsonify({
        "balance":  {"total": None, "currency": "USDT"},
        "positions": [],
        "updated":   None
    })

# Статика: изображение графика, если нужно отрисовать через PlotBot
@app.route("/plot")
def plot_image():
    # Оставлено для совместимости. При желании используйте /api/candles для Plotly.
    from BOTS.PLOTBOTS.plotbot import PlotBot  # локальный импорт, чтобы не тянуть зависимость, если не нужно
    csv_file = request.args.get("file", "BTCUSDT_1h_anal.csv")
    try:
        csv_path = safe_path(DATA_DIR, csv_file)
    except Exception:
        return "Некорректное имя файла", 400
    bot = PlotBot(csv_file=csv_path)
    out_path = os.path.join(STATIC_DATA_DIR, "plot.png")
    bot.render_to_file(out_path=out_path, tail=100)
    return send_from_directory(STATIC_DATA_DIR, "plot.png", mimetype="image/png")

@app.route("/api/health")
def health():
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    app.run(debug=True, port=5000, use_reloader=False)