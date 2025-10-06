import os
import json
import tempfile
from datetime import datetime

import firebase_admin
from firebase_admin import credentials, storage

from flask import Flask, request, abort

from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, ImageMessage,
    TextSendMessage, ImageSendMessage
)

# === 🔐 初始化 Firebase Admin ===
try:
    firebase_key_str = os.getenv("FIREBASE_KEY_JSON")
    firebase_key_dict = json.loads(firebase_key_str)
    cred = credentials.Certificate(firebase_key_dict)
    firebase_admin.initialize_app(cred, {
        'storageBucket': 'sloth-bot-8d917.appspot.com'
    })
    print("✅ Firebase 初始化成功")
except Exception as e:
    print(f"❌ Firebase 初始化失敗：{e}")

# === 🚀 初始化 Flask 與 LINE Bot ===
app = Flask(__name__)
line_bot_api = LineBotApi(os.getenv("CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.getenv("CHANNEL_SECRET"))

@app.route("/", methods=["GET"])
def home():
    return "LINE Bot is running."

@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature")
    body = request.get_data(as_text=True)
    print("🔔 收到 LINE webhook")

    try:
        handler.handle(body, signature)
    except InvalidSignatureError as e:
        print(f"❌ Signature error: {e}")
        abort(400)
    except Exception as e:
        print(f"❌ General error: {e}")
        abort(400)
    return "OK"

@handler.add(MessageEvent, message=TextMessage)
def handle_text(event):
    user_text = event.message.text
    print(f"💬 收到文字訊息：{user_text}")
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=f"你說的是：{user_text} 🦥")
    )

@handler.add(MessageEvent, message=ImageMessage)
def handle_image(event):
    print("🖼️ 收到圖片訊息")
    try:
        message_content = line_bot_api.get_message_content(event.message.id)
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            for chunk in message_content.iter_content():
                temp_file.write(chunk)
            temp_path = temp_file.name

        bucket = storage.bucket()
        now = datetime.now().strftime("%Y%m%d_%H%M%S")
        blob_path = f"line_images/{event.message.id}_{now}.jpg"
        blob = bucket.blob(blob_path)
        blob.upload_from_filename(temp_path, content_type="image/jpeg")
        blob.make_public()
        public_url = blob.public_url

        print(f"✅ 圖片上傳成功：{public_url}")

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

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)






