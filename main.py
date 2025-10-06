import os
import uuid
import hashlib
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, ImageMessage, TextSendMessage

import firebase_admin
from firebase_admin import credentials, storage, firestore

# === Firebase 初始化 ===
firebase_key_path = "/etc/secrets/FIREBASE_KEY"
if not os.path.exists(firebase_key_path):
    raise RuntimeError("❌ 找不到 FIREBASE_KEY，請確認 Secret Files 已設定")
cred = credentials.Certificate(firebase_key_path)
firebase_admin.initialize_app(cred, {
    'storageBucket': '你的專案-id.appspot.com'  # ✅ 替換為你的 bucket
})

db = firestore.client()
bucket = storage.bucket()

# === LINE Bot 初始化 ===
app = Flask(__name__)
line_bot_api = LineBotApi(os.environ.get("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.environ.get("LINE_CHANNEL_SECRET"))

# === Utils ===
def get_image_hash(filepath):
    with open(filepath, 'rb') as f:
        return hashlib.md5(f.read()).hexdigest()

def save_image_to_storage(local_path, dest_path):
    blob = bucket.blob(dest_path)
    blob.upload_from_filename(local_path)
    blob.make_public()
    return blob.public_url

def check_duplicate_by_hash(img_hash):
    results = db.collection("images").where("hash", "==", img_hash).get()
    return len(results) > 0

# === Webhook ===
@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

# === 處理圖片訊息 ===
@handler.add(MessageEvent, message=ImageMessage)
def handle_image(event):
    try:
        msg_id = event.message.id
        content = line_bot_api.get_message_content(msg_id)

        filename = f"{uuid.uuid4().hex}.jpg"
        tmp_path = f"/tmp/{filename}"

        with open(tmp_path, 'wb') as f:
            for chunk in content.iter_content():
                f.write(chunk)

        img_hash = get_image_hash(tmp_path)

        if check_duplicate_by_hash(img_hash):
            line_bot_api.reply_message(event.reply_token, TextSendMessage("這張圖片已經收藏過囉 🧸"))
            return

        firebase_path = f"pending/{filename}"
        public_url = save_image_to_storage(tmp_path, firebase_path)

        doc_ref = db.collection("images").document()
        doc_ref.set({
            "imagePath": firebase_path,
            "imageUrl": public_url,
            "hash": img_hash,
            "status": "pending",
            "category": "unknown",
            "confirmed": False,
            "name": "",
            "description": ""
        })

        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=f"圖片已上傳成功 ✅\n👉 {public_url}")
        )
    except Exception as e:
        print(f"❌ 圖片處理錯誤：{e}")
        line_bot_api.reply_message(event.reply_token, TextSendMessage("圖片處理失敗，請稍後再試 😢"))

# === 處理文字訊息 ===
@handler.add(MessageEvent, message=TextMessage)
def handle_text(event):
    text = event.message.text.strip()

    if text == "玩偶列表":
        dolls = db.collection("images").where("category", "==", "doll").where("name", "!=", "").stream()
        names = [doc.to_dict().get("name") for doc in dolls]
        if names:
            line_bot_api.reply_message(event.reply_token, TextSendMessage("🧸 玩偶清單：\n" + "\n".join(names)))
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage("目前尚未命名玩偶～"))

    elif text.startswith("搜尋"):
        keyword = text.replace("搜尋", "").strip()
        query = db.collection("images").where("status", "!=", "pending").stream()
        results = []
        for doc in query:
            data = doc.to_dict()
            if keyword in data.get("name", "") or keyword in data.get("description", ""):
                results.append(f"📌 {data.get('name')}\n{data.get('description')}\n👉 {data.get('imageUrl')}")
        if results:
            line_bot_api.reply_message(event.reply_token, TextSendMessage("\n\n".join(results[:5])))
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage("找不到相關結果 😢"))

    elif text.startswith("分類為"):
        category = "doll" if "玩偶" in text else "other"
        pending = db.collection("images").where("status", "==", "pending").where("category", "==", "unknown").limit(1).stream()
        for doc in pending:
            data = doc.to_dict()
            old_path = data["imagePath"]
            filename = old_path.split("/")[-1]
            new_path = f"{category}s/{filename}"

            # 移動檔案
            bucket.copy_blob(bucket.blob(old_path), bucket, new_path)
            bucket.delete_blob(old_path)

            doc.reference.update({
                "category": category,
                "status": "classified",
                "imagePath": new_path
            })

            line_bot_api.reply_message(event.reply_token, TextSendMessage(f"已分類為 {category} ✅"))
            return
        line_bot_api.reply_message(event.reply_token, TextSendMessage("沒有待分類的圖片囉 🎉"))

    elif text.startswith("命名：") or text.startswith("命名為"):
        name = text.split("：")[-1].replace("命名為", "").strip()
        pending = db.collection("images").where("status", "!=", "done").where("name", "==", "").limit(1).stream()
        for doc in pending:
            doc.reference.update({"name": name})
            line_bot_api.reply_message(event.reply_token, TextSendMessage(f"已命名為：{name} ✅"))
            return
        line_bot_api.reply_message(event.reply_token, TextSendMessage("沒有可以命名的圖片囉"))

    elif text.startswith("描述："):
        desc = text.split("：")[-1].strip()
        pending = db.collection("images").where("status", "!=", "done").where("description", "==", "").limit(1).stream()
        for doc in pending:
            doc.reference.update({"description": desc})
            line_bot_api.reply_message(event.reply_token, TextSendMessage("描述已更新 ✅"))
            return
        line_bot_api.reply_message(event.reply_token, TextSendMessage("沒有圖片可加入描述囉"))

    elif text.startswith("更新圖片"):
        line_bot_api.reply_message(event.reply_token, TextSendMessage("請傳送新的圖片，我會更新到最近一張已命名的收藏中。"))

# === 主程式 ===
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
