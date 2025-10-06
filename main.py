import os
import uuid
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, ImageMessage, TextSendMessage
import firebase_admin
from firebase_admin import credentials, storage

# ====== 初始化 Firebase ======
cred = credentials.Certificate("firebase-key.json")  # 路徑請放在根目錄
firebase_admin.initialize_app(cred, {
    'storageBucket': '你的 Firebase bucket 名稱，例如 your-project-id.appspot.com'
})
bucket = storage.bucket()

# ====== 初始化 Flask 與 LINE Bot ======
app = Flask(__name__)

line_bot_api = LineBotApi('你的 LINE Channel Access Token')
handler = WebhookHandler('你的 LINE Channel Secret')

# ====== 接收 LINE Webhook ======
@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

# ====== 處理圖片訊息 ======
@handler.add(MessageEvent, message=ImageMessage)
def handle_image_message(event):
    try:
        message_id = event.message.id
        image_content = line_bot_api.get_message_content(message_id)
        filename = f"{uuid.uuid4().hex}.jpg"
        file_path = f"/tmp/{filename}"

        # 儲存圖片至 /tmp
        with open(file_path, 'wb') as f:
            for chunk in image_content.iter_content():
                f.write(chunk)
        print(f"✅ 圖片儲存成功：{file_path}")

        # 上傳至 Firebase Storage
        blob = bucket.blob(f"images/{filename}")
        blob.upload_from_filename(file_path)
        blob.make_public()
        print(f"✅ 上傳 Firebase 成功：{blob.public_url}")

        # 回覆訊息
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="圖片已成功儲存至 Firebase Storage ✅")
        )

    except Exception as e:
        print(f"❌ 圖片處理錯誤：{str(e)}")
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="圖片處理失敗，請稍後再試 😢")
        )



