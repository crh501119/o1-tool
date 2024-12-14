from flask import Flask, request, jsonify
import json, os, requests
from datetime import datetime, timedelta
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

app = Flask(__name__)

# 請將下列環境變數於Render設定
LINE_CHANNEL_SECRET = os.environ.get('LINE_CHANNEL_SECRET', 'YOUR_CHANNEL_SECRET')
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN', 'YOUR_CHANNEL_ACCESS_TOKEN')

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

STATE_FILE = 'state.json'
TARGET_NAME = "曾慶豪 Howard 🦊"  # 目標使用者名稱

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
        return r.json()  # { "displayName": "...", "userId": "..."}
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
    user_id = event.source.user_id
    user_text = event.message.text.strip()
    state = load_state()

    # 若尚未記錄userId，嘗試取得用戶資訊
    if state["userId"] is None:
        prof = line_profile(user_id)
        if prof and prof.get("displayName") == TARGET_NAME:
            state["userId"] = user_id
            save_state(state)
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="已記錄您的UserID，以後將針對您進行推播通知。")
            )
            return
        else:
            # 若不是目標用戶，可回應一則訊息表示無法提供服務
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="您不是目標使用者，無法進行冷卻通知服務。")
            )
            return

    # 此時已經有userId且為目標用戶
    # 處理指令: 狀態 / 使用 / 檢查 / help
    if user_text.lower() in ["help", "指令"]:
        reply = ("可用指令：\n"
                 "『狀態』：顯示下一次可用時間\n"
                 "『使用』：模擬使用一次O1，設定下一次可用時間=現+1小時\n"
                 "『檢查』：檢查是否達到可用時間，如已達則通知冷卻結束\n"
                 "『help』或『指令』：顯示此幫助訊息")
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=reply)
        )
        return

    elif user_text == "狀態":
        next_avail_str = state.get("next_available_time")
        if next_avail_str is None:
            reply = "目前尚未設定下一次可用時間。"
        else:
            next_avail = datetime.fromisoformat(next_avail_str)
            reply = f"下一次可用時間：{next_avail.isoformat()} (UTC)，台灣時間：{next_avail.astimezone().isoformat()}"
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=reply)
        )
        return

    elif user_text == "使用":
        # 設定下一次可用時間=現在+1小時(UTC)
        now = datetime.utcnow()
        next_avail = now + timedelta(hours=1)
        state["next_available_time"] = next_avail.isoformat()
        save_state(state)
        reply = f"已設定下一次可用時間為：{next_avail.isoformat()} (UTC)"
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=reply)
        )
        return

    elif user_text == "檢查":
        next_avail_str = state.get("next_available_time")
        if next_avail_str is None:
            reply = "尚未設定下一次可用時間，無法檢查。"
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=reply)
            )
            return
        next_avail = datetime.fromisoformat(next_avail_str)
        now = datetime.utcnow()
        if now >= next_avail:
            # 時間已到
            push_message(state["userId"], "冷卻已結束，您現在可以使用下一次O1回應了！")
            state["next_available_time"] = None
            save_state(state)
            reply = "已達可用時間並推播通知。"
        else:
            remain = (next_avail - now).total_seconds()
            reply = f"尚未到達可用時間，還需等待約 {remain:.0f} 秒。"
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=reply)
        )
        return
    else:
        # 非已知指令
        reply = "無法識別的指令。輸入 'help' 或 '指令' 查看可用命令。"
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=reply)
        )
@app.route('/')
def home():
    return "OK", 200

if __name__ == '__main__':
    # 本地開發時使用
    app.run(host='0.0.0.0', port=5000)
