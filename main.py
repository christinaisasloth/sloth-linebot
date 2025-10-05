import os
import json
import tempfile
from datetime import datetime
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.models import MessageEvent, TextMessage, TextSendMessage, ImageMessage

import firebase_admin
from firebase_admin import credentials, storage

# 🔐 初始化 Firebase Admin（從環境變數抓 JSON 金鑰）
firebase_key_str = os.getenv("FIREBASE_KEY_JSON")
firebase_key_dict = json.loads(firebase_key_str)
cred = credentials.Certificate(firebase_key_dict)
firebase_admin.initialize_app(cred, {
    'storageBucket': 'sloth-bot-8d917.appspot.com'
})

# 🔧 建立 Flask 應用
app = Flask(__name__)
line_bot_api = LineBotApi(os.getenv("CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.getenv("CHANNEL_SECRET"))

# 📩 LINE Webhook 接收點
@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except:
        abort(400)
    return 'OK'

# 💬 回覆文字訊息
@handler.add(MessageEvent, message=TextMessage)
def handle_text(event):
    msg = event.message.text
    reply = f"你說的是：{msg} 🦥"
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply)
    )

# 📷 回覆圖片訊息：下載 → 暫存 → 上傳 Firebase
@handler.add(MessageEvent, message=ImageMessage)
def handle_image(event):
    message_content = line_bot_api.get_message_content(event.message.id)

    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        for chunk in message_content.iter_content():
            temp_file.write(chunk)
        temp_path = temp_file.name

    bucket = storage.bucket()
    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    blob = bucket.blob(f"line_images/{event.message.id}_{now}.jpg")
    blob.upload_from_filename(temp_path)

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text="圖片已成功上傳 Firebase 🦥")
    )

# 🚀 啟動伺服器
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
