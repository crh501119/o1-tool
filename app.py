from flask import Flask, request, jsonify
import json
import os
import requests

app = Flask(__name__)

STATE_FILE = 'state.json'
LINE_CHANNEL_ACCESS_TOKEN = 'Da1H++UXNfEgOOmVUkbJ6uvaMKDgLAZBFZninNBmhyr5bx/16YEBMURgCB0xuaeZ2Gcp2lDnC4WM3rlX+fWfYZChnh9pUcymiutrtp7d9Zug/165T5mJ2ExgTCourDookWfZUjY9b9xWWHlVdyjJjgdB04t89/1O/w1cDnyilFU='  # 請自行填入
LINE_USER_ID = 'YOUR_LINE_USER_ID'  # 要通知的使用者ID


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    else:
        return {"A": {"start": None, "next": None, "used": 0}, "B": {"start": None, "next": None, "used": 0},
                "history": [], "futureUsage": 10}


def save_state(state):
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


@app.route('/state', methods=['GET'])
def get_state():
    state = load_state()
    return jsonify(state)


@app.route('/state', methods=['POST'])
def update_state():
    state = request.json
    save_state(state)

    # 檢查事件是否有refresh_shown事件
    # 當refresh_shown發生，通知LINE
    # 簡化邏輯：若history中最後一條是refresh_shown就通知
    if state.get('history'):
        last_evt = state['history'][-1]
        if last_evt['eventType'] == 'refresh_shown':
            account = last_evt['account']
            send_line_message(f"帳號{account}已刷新，現在有50次可用！")

    return jsonify({"status": "ok"}), 200


def send_line_message(msg):
    # 使用LINE Messaging API 推送訊息
    url = 'https://api.line.me/v2/bot/message/push'
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {LINE_CHANNEL_ACCESS_TOKEN}'
    }
    payload = {
        "to": LINE_USER_ID,
        "messages": [{"type": "text", "text": msg}]
    }
    requests.post(url, headers=headers, json=payload)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
