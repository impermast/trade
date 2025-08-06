from flask import Flask, send_from_directory, jsonify
import json

app = Flask(__name__)

@app.route("/")
def index():
    return send_from_directory("API", "index.html")

@app.route("/candles")
def candles():
    return send_from_directory("DATA", "BTCUSDT_1h_anal.csv")

@app.route("/log")
def log():
    with open("LOGS/bot.log", "r", encoding="utf-8") as f:
        return f.read()

@app.route("/state")
def state():
    with open("state.json", "r", encoding="utf-8") as f:
        return jsonify(json.load(f))

app.run(debug=True, port=5000)
