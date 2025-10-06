import os
import json
import uuid
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, ImageMessage, TextSendMessage

import firebase_admin
from firebase_admin import credentials, storage

# ====== 初始化 Firebase ======
firebase_key = os.environ.get("FIREBASE_KEY")
if not firebase_key:
    raise RuntimeError("❌ 無法找到 FIREBASE_KEY，請確認 Render 的 Secret 已設定")

cred_dict = json.loads(firebase_key)
cred = credentials.Certificate(cred_dict)

firebase_admin.initialize_app(cred, {
    'storageBucket': '你的專案-id.appspot.com'  # ← 請替換為你的 Firebase bucket 名稱（例如 sloth-bot-xxxx.appspot.com）
})
bucket = storage.bucket()

# ====== 初始化 Flask 與 LINE Bot ======
app = Flask(__name__)

line_bot_api = LineBotApi(os.environ.get("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.environ.get("LINE_CHANNEL_SECRET"))

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

        # 儲存圖片到本地 /tmp/
        with open(file_path, 'wb') as f:
            for chunk in image_content.iter_content():
                f.write(chunk)

        print(f"✅ 圖片儲存成功：{file_path}")

        # 上傳圖片到 Firebase Storage
        blob = bucket.blob(f"images/{filename}")
        blob.upload_from_filename(file_path)
        blob.make_public()  # 如果你希望圖片 URL 可直接公開訪問

        print(f"✅ 上傳 Firebase 成功：{blob.public_url}")

        # 回覆使用者圖片連結（或固定文字）
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=f"圖片已上傳成功 ✅\n👉 {blob.public_url}")
        )

    except Exception as e:
        print(f"❌ 圖片處理錯誤：{str(e)}")
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="圖片處理失敗，請稍後再試 😢")
        )

# ====== 入口點 ======
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)




