from flask import Flask, request, jsonify
import json, os, requests
from datetime import datetime, timedelta
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

app = Flask(__name__)

# 從環境變數取得LINE的Token與Secret
LINE_CHANNEL_SECRET = os.environ.get('LINE_CHANNEL_SECRET', 'YOUR_CHANNEL_SECRET')
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN', 'YOUR_CHANNEL_ACCESS_TOKEN')

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

STATE_FILE = 'state.json'

TARGET_NAME = "曾慶豪 Howard 🦊"  # 目標使用者顯示名稱

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE,'r') as f:
            return json.load(f)
    else:
        s = {"userId": None, "next_available_time": None}
        save_state(s)
        return s

def save_state(state):
    with open(STATE_FILE,'w') as f:
        json.dump(state, f, indent=2, ensure_ascii=False)

def line_profile(user_id):
    """透過LINE API取得用戶檔案"""
    url = f"https://api.line.me/v2/bot/profile/{user_id}"
    headers = {
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"
    }
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        return r.json()  # { "displayName": "...", "userId": "...", ...}
    return None

def push_message(user_id, text):
    line_bot_api.push_message(user_id, TextSendMessage(text=text))

@app.route("/linewebhook", methods=["POST"])
def line_webhook():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        return 'Invalid signature', 400
    return 'OK', 200

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    # 當使用者發訊息給Bot時觸發此函式
    user_id = event.source.user_id
    state = load_state()

    # 如果還沒有記錄目標userId，就嘗試取得用戶資訊
    if state["userId"] is None:
        prof = line_profile(user_id)
        if prof and prof.get("displayName") == TARGET_NAME:
            # 確認是目標用戶
            state["userId"] = user_id
            save_state(state)
            push_message(user_id, "已記錄您的UserID，以後冷卻時間到會通知您。")

    # 若非目標用戶或已經有userId，不特別處理
    # 可回覆一則簡訊告知收到
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text="收到您的訊息！")
    )

@app.route("/update_usage", methods=["POST"])
def update_usage():
    # 用來更新下一次可用時間
    # 假設計算邏輯：現在時間 + 1小時
    # 可依你需求更換計算方式，例如根據當前已用次數與平均速率計算
    state = load_state()

    now = datetime.utcnow()
    next_available = now + timedelta(hours=1)  # 理想下一次使用時間：現+1小時
    state["next_available_time"] = next_available.isoformat()
    save_state(state)

    return jsonify({"status":"ok", "next_available_time": next_available.isoformat()}),200

@app.route("/check_time", methods=["GET"])
def check_time():
    # 檢查是否已達下一次可用時間，如是且有userId則推播提醒
    state = load_state()
    user_id = state.get("userId")
    next_avail_str = state.get("next_available_time")

    if user_id and next_avail_str:
        next_avail = datetime.fromisoformat(next_avail_str)
        now = datetime.utcnow()
        if now >= next_avail:
            # 時間已到，可推播提醒
            push_message(user_id, "冷卻已結束，您現在可以使用下一次O1回應了！")
            # 使用後可將 next_available_time 清除或保留給下次更新
            state["next_available_time"] = None
            save_state(state)
            return jsonify({"status":"notified"}),200
        else:
            return jsonify({"status":"waiting", "remaining_seconds": (next_avail - now).total_seconds()}),200
    else:
        return jsonify({"status":"no_data"}),200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
