import os
import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from flask import Flask
from threading import Thread
import replicate
import requests

# Настройки
VK_TOKEN = os.getenv("VK_TOKEN")
GROUP_ID = int(os.getenv("GROUP_ID"))
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")

os.environ["REPLICATE_API_TOKEN"] = REPLICATE_API_TOKEN

vk_session = vk_api.VkApi(token=VK_TOKEN)
vk = vk_session.get_api()
app = Flask(__name__)

def generate_image(prompt):
    try:
        output = replicate.run(
            "stability-ai/sdxl:da77bc59ee60423279fd632efb4795ab731d9e3ca9705ef3341091fb989b7eaf",
            input={
                "prompt": prompt,
                "negative_prompt": "blurry, low quality, text",
                "width": 1024,
                "height": 1024
            }
        )
        return output[0]
    except Exception as e:
        print("Ошибка генерации:", e)
        return None

def send_photo_to_vk(user_id, image_url):
    try:
        img_data = requests.get(image_url).content
        upload_url = vk.photos.getMessagesUploadServer()['upload_url']
        files = {'photo': ('image.png', img_data, 'image/png')}
        upload_response = requests.post(upload_url, files=files).json()
        saved = vk.photos.saveMessagesPhoto(**upload_response)[0]
        attachment = f"photo{saved['owner_id']}_{saved['id']}"
        vk.messages.send(user_id=user_id, message="Ваше изображение готово!", attachment=attachment, random_id=0)
    except Exception as e:
        print("Ошибка отправки:", e)
        vk.messages.send(user_id=user_id, message="Не удалось отправить изображение.", random_id=0)

def run_vk_bot():
    longpoll = VkBotLongPoll(vk_session, GROUP_ID)
    print("✅ Бот запущен!")
    for event in longpoll.listen():
        if event.type == VkBotEventType.MESSAGE_NEW:
            user_id = event.obj.message['from_id']
            text = event.obj.message['text'].strip()
            if text:
                vk.messages.send(user_id=user_id, message="Генерирую... ⏳", random_id=0)
                img_url = generate_image(text)
                if img_url:
                    send_photo_to_vk(user_id, img_url)
                else:
                    vk.messages.send(user_id=user_id, message="Ошибка генерации.", random_id=0)

@app.route('/')
def home():
    return "ФотоТочка бот работает!"

@app.route('/health')
def health():
    return "OK", 200

if __name__ == '__main__':
    Thread(target=run_vk_bot).start()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8000)))