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

from linebot.models import ImageMessage
import tempfile
from google.cloud import storage as gcs_storage
from datetime import datetime

@handler.add(MessageEvent, message=ImageMessage)
def handle_image(event):
    # 1. 從 LINE 拿圖片內容
    message_content = line_bot_api.get_message_content(event.message.id)

    # 2. 存成暫存檔
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        for chunk in message_content.iter_content():
            temp_file.write(chunk)
        temp_path = temp_file.name

    # 3. 上傳到 Firebase Storage
    bucket = storage.bucket()
    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    blob = bucket.blob(f"line_images/{event.message.id}_{now}.jpg")
    blob.upload_from_filename(temp_path)

    # 4. 回覆用戶
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text="已收到圖片，已上傳 Firebase 🦥")
    )

from linebot.models import ImageMessage
import tempfile
from datetime import datetime

@handler.add(MessageEvent, message=ImageMessage)
def handle_image(event):
    # 從 LINE 下載圖片內容
    message_content = line_bot_api.get_message_content(event.message.id)

    # 暫存圖片
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        for chunk in message_content.iter_content():
            temp_file.write(chunk)
        temp_path = temp_file.name

    # 上傳到 Firebase Storage
    bucket = storage.bucket()
    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    blob = bucket.blob(f"line_images/{event.message.id}_{now}.jpg")
    blob.upload_from_filename(temp_path)

    # 回覆用戶
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text="圖片已成功上傳 Firebase 🦥")
    )

from linebot.models import ImageMessage
import tempfile
from datetime import datetime

@handler.add(MessageEvent, message=ImageMessage)
def handle_image(event):
    # 從 LINE 下載圖片內容
    message_content = line_bot_api.get_message_content(event.message.id)

    # 暫存圖片
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        for chunk in message_content.iter_content():
            temp_file.write(chunk)
        temp_path = temp_file.name

    # 上傳到 Firebase Storage
    bucket = storage.bucket()
    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    blob = bucket.blob(f"line_images/{event.message.id}_{now}.jpg")
    blob.upload_from_filename(temp_path)

    # 回覆用戶
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text="圖片已成功上傳 Firebase 🦥")
    )



if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # 從環境變數抓 port
    app.run(host="0.0.0.0", port=port)

