import firebase_admin
from firebase_admin import credentials, storage
import json
import os

# 🔑 讀取金鑰 JSON 內容（從環境變數中）
firebase_key_str = os.getenv("FIREBASE_KEY_JSON")  # 環境變數裡是一段字串
firebase_key_dict = json.loads(firebase_key_str)   # 轉成字典

# 🔐 初始化 Firebase Admin
cred = credentials.Certificate(firebase_key_dict)
firebase_admin.initialize_app(cred, {
    'storageBucket': 'sloth-bot-8d917.appspot.com'
})



from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.models import MessageEvent, TextMessage, TextSendMessage

import os

app = Flask(__name__)

line_bot_api = LineBotApi(os.getenv("CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.getenv("CHANNEL_SECRET"))

@app.route("/callback", methods=['POST'])
def callback():

    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except:
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    msg = event.message.text
    reply = f"你說的是：{msg} 🦥"
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply)
    )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # 從環境變數抓 port
    app.run(host="0.0.0.0", port=port)

