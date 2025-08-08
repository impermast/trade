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
    csv_file = request.args.get("file", "BTCUSDT_1h_anal.csv")
    try:
        safe_path(DATA_DIR, csv_file)
    except Exception:
        return "Некорректное имя файла", 400
    return send_from_directory(DATA_DIR, csv_file)

# JSON-свечи для интерактивного графика Plotly
@app.route("/api/candles")
def api_candles():
    """
    Параметры:
      - file: имя CSV в DATA (по умолчанию BTCUSDT_1h_anal.csv)
      - tail: сколько последних строк вернуть (по умолчанию 500)
    Формат ответа: [{ts, open, high, low, close, volume}, ...]
    """
    csv_file = request.args.get("file", "BTCUSDT_1h_anal.csv")
    tail_rows = int(request.args.get("tail", "500"))
    try:
        csv_path = safe_path(DATA_DIR, csv_file)
    except Exception:
        return jsonify({"error": "Некорректное имя файла"}), 400

    if not os.path.exists(csv_path):
        return jsonify({"error": "Файл не найден"}), 404

    try:
        # Читаем только нужный хвост быстро
        df = pd.read_csv(csv_path)
        # Пытаемся найти колонки времени и OHLCV
        time_cols = [c for c in df.columns if c.lower() in ("time", "timestamp", "date", "datetime")]
        o = next((c for c in df.columns if c.lower() == "open"), None)
        h = next((c for c in df.columns if c.lower() == "high"), None)
        l = next((c for c in df.columns if c.lower() == "low"), None)
        c = next((c for c in df.columns if c.lower() == "close"), None)
        v = next((c for c in df.columns if c.lower() in ("volume", "vol")), None)

        if not time_cols or not all([o, h, l, c]):
            return jsonify({"error": "Не найдены необходимые колонки для OHLC"}), 400

        t = time_cols[0]
        # Приводим время к ISO-строке, если это числовой timestamp — оставим как есть
        # Попробуем конвертировать в datetime
        try:
            ts_series = pd.to_datetime(df[t], errors="coerce")
            # Где удалось — форматируем, иначе берем исходное значение
            ts_values = [
                (ts.isoformat() if pd.notna(ts) else str(orig))
                for ts, orig in zip(ts_series, df[t])
            ]
        except Exception:
            ts_values = df[t].astype(str).tolist()

        # Обрезаем хвост
        if tail_rows > 0:
            df = df.tail(tail_rows)
            ts_values = ts_values[-len(df):]

        result = []
        for i, row in df.reset_index(drop=True).iterrows():
            item = {
                "ts": ts_values[i],
                "open": float(row[o]),
                "high": float(row[h]),
                "low": float(row[l]),
                "close": float(row[c]),
            }
            if v in df.columns:
                try:
                    item["volume"] = float(row[v])
                except Exception:
                    item["volume"] = None
            else:
                item["volume"] = None
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
    files = [f for f in os.listdir(DATA_DIR) if f.endswith(".csv")]
    files.sort()
    return jsonify(files)

# Простое состояние (если есть state.json в корне проекта)
@app.route("/api/state")
def state():
    state_path = os.path.join(PROJECT_ROOT, "state.json")
    if os.path.exists(state_path):
        try:
            with open(state_path, "r", encoding="utf-8") as f:
                return jsonify(json.load(f))
        except Exception:
            pass
    # Значения по умолчанию
    return jsonify({
        "balance": {"total": None, "currency": "USDT"},
        "positions": [],
        "updated": None
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