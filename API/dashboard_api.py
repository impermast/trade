from flask import Flask, request, send_from_directory, jsonify, send_file
import json
import os, sys


sys.path.append(os.path.abspath("."))
from BOTS.PLOTBOTS.plotbot import PlotBot

app = Flask(__name__)

@app.route("/")
def index():
    return send_file("index.html")

@app.route("/candles")
def candles():
    return send_from_directory("../DATA", "BTCUSDT_1h_anal.csv")

# 3. Получение списка всех лог-файлов
@app.route("/logs")
def list_logs():
    log_dir = "LOGS"
    files = [f for f in os.listdir(log_dir) if f.endswith(".log")]
    return jsonify(files)

# 4. Получение содержимого выбранного лог-файла
@app.route("/log/<filename>")
def get_log_file(filename):
    filepath = os.path.join("LOGS", filename)
    if not os.path.exists(filepath):
        return "Файл не найден", 404
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()

# @app.route("/state")
# def state():
#     with open("state.json", "r", encoding="utf-8") as f:
#         return jsonify(json.load(f))

@app.route("/csv_list")
def list_csv_files():
    data_dir = "DATA"
    files = [f for f in os.listdir(data_dir) if f.endswith(".csv")]
    return jsonify(files)

@app.route("/plot")
def plot_image():
    csv_file = request.args.get("file", "BTCUSDT_1m_anal.csv")
    csv_path = os.path.join("DATA", csv_file)
    bot = PlotBot(csv_file=csv_path)
    bot.render_to_file(out_path="DATA/static/plot.png", tail=100)
    return send_from_directory("../DATA/static","plot.png", mimetype="image/png")

app.run(debug=True, port=5000)
