import os
import json
import tempfile
from datetime import datetime

import firebase_admin
from firebase_admin import credentials, storage

from flask import Flask, request, abort

from linebot.v3.messaging import MessagingApi, MessagingApiBlob
from linebot.v3.webhooks import WebhookHandler
from linebot.v3.messaging.models import (
    TextMessage, ImageMessage, ImageSendMessage
)
from linebot.v3.webhooks.models import MessageEvent

from linebot.v3.http_client import RequestsHttpClient

# === 🔐 Firebase Admin 初始化 ===
firebase_key_str = os.getenv("FIREBASE_KEY_JSON")
firebase_key_dict = json.loads(firebase_key_str)
cred = credentials.Certificate(firebase_key_dict)
firebase_admin.initialize_app(cred, {
    'storageBucket': 'sloth-bot-8d917.appspot.com'
})

# === 🚀 初始化 Flask 與 LINE Messaging API v3 ===
app = Flask(__name__)
channel_token = os.getenv("CHANNEL_ACCESS_TOKEN")
channel_secret = os.getenv("CHANNEL_SECRET")

handler = WebhookHandler(channel_secret)
http_client = RequestsHttpClient()
messaging_api = MessagingApi(http_client)
blob_client = MessagingApiBlob(http_client)

# === 🛠️ Home route ===
@app.route("/", methods=["GET"])
def home():
    return "LINE Bot v3 is running."

# === 📡 Webhook 路由 ===
@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature")
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
    messaging_api.reply_message_with_http_info(
        reply_token=event.reply_token,
        messages=[TextMessage(text=reply_text)]
    )

# === 🖼️ 處理圖片訊息 + 上傳 Firebase + 回傳圖片 ===
@handler.add(MessageEvent, message=ImageMessage)
def handle_image(event):
    try:
        # 1. 取得圖片內容（v3 blob client）
        content_response = blob_client.get_message_content(event.message.id)
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            for chunk in content_response.iter_content():
                temp_file.write(chunk)
            temp_path = temp_file.name

        # 2. 上傳到 Firebase Storage
        bucket = storage.bucket()
        now = datetime.now().strftime("%Y%m%d_%H%M%S")
        blob_path = f"line_images/{event.message.id}_{now}.jpg"
        blob = bucket.blob(blob_path)
        blob.upload_from_filename(temp_path)
        blob.make_public()
        public_url = blob.public_url

        # 3. 回傳圖片
        messaging_api.reply_message_with_http_info(
            reply_token=event.reply_token,
            messages=[
                ImageMessage(
                    original_content_url=public_url,
                    preview_image_url=public_url
                )
            ]
        )

    except Exception as e:
        print(f"❌ 圖片處理錯誤：{e}")
        messaging_api.reply_message_with_http_info(
            reply_token=event.reply_token,
            messages=[TextMessage(text="圖片處理失敗了，請稍後再試 🥺")]
        )

# === 🔁 Flask 啟動 ===
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)




