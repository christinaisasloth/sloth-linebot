import os
import json
import tempfile
from datetime import datetime

import firebase_admin
from firebase_admin import credentials, storage

from flask import Flask, request, abort

from linebot import LineBotApi, WebhookHandler
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
    ImageMessage, ImageSendMessage
)

# ✅ 新增 v3 的 MessagingApiBlob & Configuration
from linebot.v3.messaging import MessagingApiBlob
from linebot.v3.configuration import Configuration

# === 🔐 初始化 Firebase Admin ===
firebase_key_str = os.getenv("FIREBASE_KEY_JSON")
firebase_key_dict = json.loads(firebase_key_str)
cred = credentials.Certificate(firebase_key_dict)
firebase_admin.initialize_app(cred, {
    'storageBucket': 'sloth-bot-8d917.appspot.com'
})

# === 🚀 初始化 Flask 與 LINE Bot ===
app = Flask(__name__)
line_bot_api = LineBotApi(os.getenv("CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.getenv("CHANNEL_SECRET"))

# ✅ 用新版 v3 初始化 blob_client
configuration = Configuration(access_token=os.getenv("CHANNEL_ACCESS_TOKEN"))
blob_client = MessagingApiBlob(configuration)

# === 🛠️ 保活用首頁 ===
@app.route("/", methods=["GET"])
def home():
    return "LINE Bot is running."

# === 📡 Webhook 路由 ===
@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers.get('X-Line-Signature')
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except Exception as e:
        print(f"❌ Webhook error: {e}")
        abort(400)

    return "OK"

# === 💬 回覆文字訊息 ===
@handler.add(MessageEvent, message=TextMessage)
def handle_text(event):
    user_text = event.message.text
    reply_text = f"你說的是：{user_text} 🦥"
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_text)
    )

# === 🖼️ 回覆圖片並上傳 Firebase ===
@handler.add(MessageEvent, message=ImageMessage)
def handle_image(event):
    try:
        # 取得圖片內容（v3 blob client）
        message_content = blob_client.get_message_content(event.message.id)

        # 存成暫存檔案
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            for chunk in message_content.iter_content():
                temp_file.write(chunk)
            temp_path = temp_file.name

        # 上傳至 Firebase
        bucket = storage.bucket()
        now = datetime.now().strftime("%Y%m%d_%H%M%S")
        blob_path = f"line_images/{event.message.id}_{now}.jpg"
        blob = bucket.blob(blob_path)
        blob.upload_from_filename(temp_path)
        blob.make_public()
        public_url = blob.public_url

        # 回傳圖片訊息
        line_bot_api.reply_message(
            event.reply_token,
            ImageSendMessage(
                original_content_url=public_url,
                preview_image_url=public_url
            )
        )

    except Exception as e:
        print(f"❌ 圖片處理錯誤：{e}")
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="圖片處理失敗了，請稍後再試 🥺")
        )

# === 🔁 啟動應用（Render 自動執行） ===
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)





