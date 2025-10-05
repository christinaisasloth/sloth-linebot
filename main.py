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
from linebot.v3.messaging import MessagingApiBlob  # 用於新版 get_message_content

# === 🔐 初始化 Firebase Admin ===
firebase_key_str = os.getenv("FIREBASE_KEY_JSON")
firebase_key_dict = json.loads(firebase_key_str)
cred = credentials.Certificate(firebase_key_dict)
firebase_admin.initialize_app(cred, {
    'storageBucket': 'sloth-bot-8d917.appspot.com'
})

# === 🚀 初始化 Flask 與 LINE ===
app = Flask(__name__)
line_bot_api = LineBotApi(os.getenv("CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.getenv("CHANNEL_SECRET"))
blob_client = MessagingApiBlob(os.getenv("CHANNEL_ACCESS_TOKEN"))  # 新增 blob 客戶端

# === 🛠️ Home route，Render 保活用 ===
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

# === 💬 處理文字訊息 ===
@handler.add(MessageEvent, message=TextMessage)
def handle_text(event):
    user_text = event.message.text
    reply_text = f"你說的是：{user_text} 🦥"
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_text)
    )

# === 🖼️ 處理圖片訊息並上傳 Firebase Storage ===
@handler.add(MessageEvent, message=ImageMessage)
def handle_image(event):
    try:
        # 1. 從 LINE 拿圖片內容（新版方法）
        message_content = blob_client.get_message_content(event.message.id)

        # 2. 存成暫存檔案
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            for chunk in message_content.iter_content():
                temp_file.write(chunk)
            temp_path = temp_file.name

        # 3. 上傳至 Firebase
        bucket = storage.bucket()
        now = datetime.now().strftime("%Y%m%d_%H%M%S")
        blob_path = f"line_images/{event.message.id}_{now}.jpg"
        blob = bucket.blob(blob_path)
        blob.upload_from_filename(temp_path)
        blob.make_public()
        public_url = blob.public_url

        # 4. 回傳圖片訊息
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

# === 🔁 啟動 Flask App（Render 會自動啟動） ===
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)



