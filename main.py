import firebase_admin
from firebase_admin import credentials, storage
import json
import os

# 🔑 讀取 Firebase 金鑰 JSON 內容（從環境變數）
firebase_key_str = os.getenv("FIREBASE_KEY_JSON")
firebase_key_dict = json.loads(firebase_key_str)

# 🔐 初始化 Firebase Admin SDK
cred = credentials.Certificate(firebase_key_dict)
firebase_admin.initialize_app(cred, {
    'storageBucket': 'sloth-bot-8d917.appspot.com'
})

from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.models import MessageEvent, TextMessage, TextSendMessage, ImageMessage, ImageSendMessage
import tempfile
from datetime import datetime

app = Flask(__name__)

# ✅ 讀取 LINE Channel 的金鑰
line_bot_api = LineBotApi(os.getenv("CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.getenv("CHANNEL_SECRET"))

# 🔁 LINE Webhook 接收區
@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except:
        abort(400)

    return 'OK'

# 📩 處理文字訊息
@handler.add(MessageEvent, message=TextMessage)
def handle_text(event):
    msg = event.message.text
    reply = f"你說的是：{msg} 🦥"
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply)
    )

# 🖼️ 處理圖片訊息 → 上傳 Firebase → 回傳圖
@handler.add(MessageEvent, message=ImageMessage)
def handle_image(event):
    # 1. 從 LINE 拿圖片內容
    message_content = line_bot_api.get_message_content(event.message.id)

    # 2. 暫存圖片
    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp_file:
        for chunk in message_content.iter_content():
            temp_file.write(chunk)
        temp_path = temp_file.name

    # 3. 上傳到 Firebase Storage
    bucket = storage.bucket()
    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"line_images/{event.message.id}_{now}.jpg"
    blob = bucket.blob(filename)
    blob.upload_from_filename(temp_path)

    # 4. 設為公開並取得圖片網址
    blob.make_public()
    image_url = blob.public_url

    # 5. 回傳圖片訊息給使用者
    image_message = ImageSendMessage(
        original_content_url=image_url,
        preview_image_url=image_url
    )
    line_bot_api.reply_message(event.reply_token, image_message)

# 🚀 主程式啟動（for 本地或 Render）
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
