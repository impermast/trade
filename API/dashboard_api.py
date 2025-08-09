# dashboard_api.py
from flask import Flask, request, send_from_directory, jsonify, send_file
import os, re, json, subprocess, sys, signal
from collections import deque
from datetime import datetime
from typing import Optional
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, ".."))
DATA_DIR = os.path.join(PROJECT_ROOT, "DATA")
LOGS_DIR = os.path.join(PROJECT_ROOT, "LOGS")
STATIC_DATA_DIR = os.path.join(DATA_DIR, "static")
os.makedirs(STATIC_DATA_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)

app = Flask(__name__)

# ---------- Веб ----------
def get_csv_list() -> list[str]:
    files = [f for f in os.listdir(DATA_DIR) if f.endswith(".csv")]
    files.sort()
    return files

def get_anal_list() -> list[str]:
    return [f for f in get_csv_list() if f.endswith("_anal.csv")]

def safe_path(base_dir: str, filename: str) -> str:
    filename = os.path.basename(filename)
    full_path = os.path.join(base_dir, filename)
    if not os.path.abspath(full_path).startswith(os.path.abspath(base_dir)):
        raise ValueError("Недопустимый путь")
    return full_path

@app.after_request
def add_cache_headers(resp):
    if request.path.startswith("/api/"):
        resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return resp

@app.route("/")
def index():
    return send_file(os.path.join(BASE_DIR, "index.html"))

@app.route("/candles")
def candles():
    anal = get_anal_list()
    if not anal:
        return "", 204
    chosen = request.args.get("file")
    if chosen not in anal:
        chosen = anal[0]
    return send_from_directory(DATA_DIR, chosen)

@app.route("/api/candles")
def api_candles():
    anal = get_anal_list()
    all_csv = get_csv_list()

    # пул допустимых файлов
    allowed = anal if anal else all_csv
    if not allowed:
        return jsonify([])

    requested = request.args.get("file")
    if requested in allowed:
        csv_file = requested
    elif requested in all_csv:
        csv_file = requested
    else:
        csv_file = allowed[0]

    try:
        csv_path = safe_path(DATA_DIR, csv_file)
    except ValueError:
        return jsonify({"error": "Некорректное имя файла"}), 400
    if not os.path.exists(csv_path):
        return jsonify({"error": "Файл не найден"}), 404

    tail_rows = max(0, int(request.args.get("tail", "500")))

    try:
        df = pd.read_csv(csv_path)

        # маппинг колонок без учёта регистра
        lower_map = {c.lower(): c for c in df.columns}

        time_col = next((lower_map[k] for k in ("time","timestamp","date","datetime") if k in lower_map), None)
        o = lower_map.get("open")
        h = lower_map.get("high")
        l = lower_map.get("low")
        c = lower_map.get("close")
        v = next((lower_map[k] for k in ("volume","vol") if k in lower_map), None)

        # варианты колонок ордеров
        orders_col      = lower_map.get("orders")
        orders_rsi_col  = lower_map.get("orders_rsi")
        # поддержим старые/кривые названия модели
        orders_xgb_col  = lower_map.get("orders_xgb") or lower_map.get("xgb_signal")

        if not time_col or not all([o, h, l, c]):
            return jsonify({"error": "Не найдены необходимые колонки для OHLC"}), 400

        # время
        df["_ts"] = pd.to_datetime(df[time_col], errors="coerce", utc=False)
        if tail_rows > 0:
            df = df.tail(tail_rows).copy()

        # числовые поля
        for col in [o, h, l, c, v, orders_col, orders_rsi_col, orders_xgb_col]:
            if col and col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        # ордера делаем явными нулями, чтобы фронту не присылать пустоты
        for col in [orders_col, orders_rsi_col, orders_xgb_col]:
            if col and col in df.columns:
                df[col] = df[col].fillna(0).astype(float)

        out = []
        for _, row in df.iterrows():
            ts = row["_ts"]
            item = {
                "ts": ts.isoformat() if pd.notna(ts) else str(row[time_col]),
                "open":  float(row[o]) if pd.notna(row[o]) else None,
                "high":  float(row[h]) if pd.notna(row[h]) else None,
                "low":   float(row[l]) if pd.notna(row[l]) else None,
                "close": float(row[c]) if pd.notna(row[c]) else None,
                "volume": float(row[v]) if (v and pd.notna(row[v])) else None,
            }
            # добавим все варианты колонок ордеров, если есть
            if orders_col:
                val = row[orders_col]
                item["orders"] = float(val) if pd.notna(val) else 0.0
            if orders_rsi_col:
                val = row[orders_rsi_col]
                item["orders_rsi"] = float(val) if pd.notna(val) else 0.0
            if orders_xgb_col:
                val = row[orders_xgb_col]
                item["orders_xgb"] = float(val) if pd.notna(val) else 0.0

            out.append(item)

        resp = jsonify(out)
        resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        return resp
    except Exception as e:
        return jsonify({"error": f"Ошибка обработки CSV: {e}"}), 500

@app.route("/logs")
def list_logs():
    files = [f for f in os.listdir(LOGS_DIR) if f.endswith(".log")]
    files.sort()
    return jsonify(files)

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

    dq = deque(maxlen=max(n,1))
    with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            dq.append(line.rstrip("\n"))
    return jsonify({"lines": list(dq)})

_TS_RE = re.compile(r"\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:[.,]\d{3,6})?")
_LEVELS = ("INFO","WARN","WARNING","ERROR","DEBUG","CRITICAL")

def _parse_line(filename: str, line: str):
    src = os.path.basename(filename)
    m = _TS_RE.search(line)
    ts_val = None
    if m:
        ts_str = m.group(0).replace(",", ".")
        ts_val = pd.to_datetime(ts_str, errors="coerce")
        msg = _TS_RE.sub("", line).strip()
    else:
        msg = line.strip()

    level = None
    up = line.upper()
    for lv in _LEVELS:
        if f"[{lv}]" in up or f" {lv}:" in up or up.startswith(f"{lv} ") or up.endswith(f" {lv}"):
            level = "WARN" if lv == "WARNING" else lv
            break

    msg = re.sub(r"\s{2,}", " ", msg)
    return ts_val, level, src, msg

@app.route("/api/logs_all")
def logs_all():
    n = int(request.args.get("n", "1000"))
    level = (request.args.get("level") or "ALL").upper()
    q = (request.args.get("q") or "").strip().lower()

    entries = []
    for fname in [f for f in os.listdir(LOGS_DIR) if f.endswith(".log")]:
        path = os.path.join(LOGS_DIR, fname)
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    ts, lv, src, msg = _parse_line(fname, line)
                    if level != "ALL" and (lv or "") != level:
                        continue
                    if q and q not in msg.lower():
                        continue
                    entries.append({
                        "ts": ts.to_pydatetime() if isinstance(ts, pd.Timestamp) else None,
                        "level": lv or "",
                        "src": src,
                        "msg": msg
                    })
        except Exception:
            continue

    entries.sort(key=lambda x: (x["ts"] or datetime.min, x["src"]))
    if n > 0 and len(entries) > n:
        entries = entries[-n:]

    out = []
    for e in entries:
        ts_str = e["ts"].strftime("%Y-%m-%d %H:%M:%S.%f")[:-3] if e["ts"] else ""
        out.append({"ts": ts_str, "level": e["level"], "src": e["src"], "msg": e["msg"]})
    return jsonify(out)

@app.route("/csv_list")
def list_csv_files():
    return jsonify(get_csv_list())

@app.route("/api/state")
def state():
    state_path = os.path.join(STATIC_DATA_DIR, "state.json")
    if os.path.exists(state_path):
        try:
          with open(state_path, "r", encoding="utf-8") as f:
              data = json.load(f)
          ts = data.get("updated")
          if ts:
              ts_norm = ts.replace(",", ".")
              dt = pd.to_datetime(ts_norm, errors="coerce")
              if pd.notna(dt):
                  data["updated"] = dt.tz_localize(None).strftime("%d.%m.%Y %H:%M:%S")
          resp = jsonify(data)
          resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
          return resp
        except Exception as e:
          app.logger.error(f"Error reading state.json: {e}")
    return jsonify({"balance":{"total":None,"currency":"USDT"},"positions":[],"updated":None})

@app.route("/api/health")
def health():
    return jsonify({"status":"ok"})


# ---------- Локальный запуск ----------
def run():
    port = int(os.getenv("DASHBOARD_PORT", "5000"))
    host = os.getenv("DASHBOARD_HOST", "127.0.0.1")
    app.run(debug=True, port=port, host=host, use_reloader=False)

# ---------- Утилиты запуска/остановки из main.py ----------
def run_flask_in_new_terminal(host: str = "127.0.0.1", port: int = 5000, log_path: Optional[str] = None) -> subprocess.Popen:
    env = os.environ.copy()
    env["DASHBOARD_HOST"] = str(host)
    env["DASHBOARD_PORT"] = str(port)

    py = sys.executable
    if log_path is None:
        log_path = os.path.join(LOGS_DIR, "dashboard.out.log")
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    log_file = open(log_path, "a", buffering=1, encoding="utf-8")

    kwargs = dict(env=env, stdin=subprocess.DEVNULL, stdout=log_file, stderr=log_file)

    if os.name == "nt":
        CREATE_NEW_CONSOLE = 0x00000010
        proc = subprocess.Popen([py, "-m", "API.dashboard_api"], creationflags=CREATE_NEW_CONSOLE, close_fds=False, **kwargs)
    else:
        proc = subprocess.Popen([py, "-m", "API.dashboard_api"], preexec_fn=os.setsid, close_fds=True, **kwargs)

    return proc

def stop_flask(proc: Optional[subprocess.Popen]) -> None:
    if not proc:
        return
    try:
        if proc.poll() is None:
            if os.name == "nt":
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except Exception:
                    proc.kill()
            else:
                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                try:
                    proc.wait(timeout=5)
                except Exception:
                    os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
    except Exception:
        pass

if __name__ == "__main__":
    run()
