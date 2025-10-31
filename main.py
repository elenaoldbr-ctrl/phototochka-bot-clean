import os
import sys
import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from flask import Flask
from threading import Thread
import replicate
import requests

VK_TOKEN = os.getenv("VK_TOKEN")
GROUP_ID_STR = os.getenv("GROUP_ID")
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")

if not VK_TOKEN or not GROUP_ID_STR or not REPLICATE_API_TOKEN:
    print("❌ ОШИБКА: Не заданы переменные окружения", file=sys.stderr)
    sys.exit(1)

try:
    GROUP_ID = int(GROUP_ID_STR)
except:
    print("❌ ОШИБКА: GROUP_ID должен быть числом", file=sys.stderr)
    sys.exit(1)

os.environ["REPLICATE_API_TOKEN"] = REPLICATE_API_TOKEN

vk_session = vk_api.VkApi(token=VK_TOKEN)
vk = vk_session.get_api()
vk.groups.getById(group_id=GROUP_ID)
print(f"✅ Подключено к группе {GROUP_ID}")

app = Flask(__name__)

@app.route('/health')
def health():
    return "OK", 200

def generate_image(prompt):
    try:
        output = replicate.run(
            "stability-ai/sdxl:da77bc59ee60423279fd632efb4795ab731d9e3ca9705ef3341091fb989b7eaf",
            input={"prompt": prompt, "width": 1024, "height": 1024}
        )
        return output[0]
    except Exception as e:
        print(f"❌ Генерация: {e}")
        return None

def send_photo_to_vk(user_id, url):
    try:
        img = requests.get(url).content
        upload_url = vk.photos.getMessagesUploadServer()['upload_url']
        resp = requests.post(upload_url, files={'photo': ('img.png', img, 'image/png')}).json()
        photo = vk.photos.saveMessagesPhoto(**resp)[0]
        vk.messages.send(user_id=user_id, message="✅ Готово!", attachment=f"photo{photo['owner_id']}_{photo['id']}", random_id=0)
    except Exception as e:
        print(f"❌ Отправка: {e}")
        vk.messages.send(user_id=user_id, message="Ошибка.", random_id=0)

def run_bot():
    longpoll = VkBotLongPoll(vk_session, GROUP_ID)
    print("✅ Бот запущен")
    for event in longpoll.listen():
        if event.type == VkBotEventType.MESSAGE_NEW:
            uid = event.obj.message['from_id']
            text = event.obj.message.get('text', '').strip()
            if text:
                vk.messages.send(user_id=uid, message="⏳ Жду...", random_id=0)
                img_url = generate_image(text)
                if img_url:
                    send_photo_to_vk(uid, img_url)
                else:
                    vk.messages.send(user_id=uid, message="❌ Не вышло.", random_id=0)

if __name__ == '__main__':
    Thread(target=run_bot, daemon=True).start()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8000)))