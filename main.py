import firebase_admin
from firebase_admin import credentials, storage
import json, os

firebase_key = os.environ.get("FIREBASE_KEY_JSON")
cred = credentials.Certificate(json.loads(firebase_key))

firebase_admin.initialize_app(cred, {
    'storageBucket': '你的-bucket名稱.appspot.com'  # ✅ 請改成你自己的
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

