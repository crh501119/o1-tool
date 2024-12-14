from flask import Flask, request, jsonify
import json
import os

app = Flask(__name__)

STATE_FILE = 'state.json'

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE,'r') as f:
            return json.load(f)
    else:
        # 初始狀態
        return {"A":{"start":None,"next":None,"used":0},"B":{"start":None,"next":None,"used":0},"history":[]}

def save_state(state):
    with open(STATE_FILE,'w') as f:
        json.dump(state,f,indent=2, ensure_ascii=False)

@app.route('/state', methods=['GET'])
def get_state():
    state = load_state()
    return jsonify(state)

@app.route('/state', methods=['POST'])
def update_state():
    state = request.json
    save_state(state)
    return jsonify({"status":"ok"}),200

if __name__ == '__main__':
    # 本地測試用
    app.run(host='0.0.0.0', port=5000)
