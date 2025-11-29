import json
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, CommandStart
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.methods import SendChatAction
from aiogram.enums import ChatAction
import asyncio
import aiohttp
import tempfile
from aiogram.types import FSInputFile
import json
from openai import OpenAI
import asyncio
import random

# ================== БОТ С ГОЛОСОВЫМИ ==================
max = "475b38e759cc49988dd107f97fa840a5" #"e4adddc02d38434784347c9f4b279e53"
artem = "bc711204367e40c585ea71cabfcff874"
COOKIES = {
    "PHPSESSID": "rn8k1bl2md5bpnque3aolir2fl"
}


HEADERS = {
    "Accept": "*/*",
    "Origin": "https://vocloner.com",
    "Referer": "https://vocloner.com/tts.php",
    "Content-Type": "application/json",
}

async def voice_message(text: str, VOICE_ID) -> str:
    import aiohttp
    import tempfile
    import json
    import os

    payload = {
        "voice": VOICE_ID,
        "text": text,
        "format": "mp3"
    }

    async with aiohttp.ClientSession(cookies=COOKIES, headers=HEADERS) as session:
        async with session.post("https://vocloner.com/tts_processprova.php", json=payload) as resp:
            raw = await resp.text()

    start = raw.find("{")
    end = raw.rfind("}")

    if start == -1 or end == -1:
        raise RuntimeError("JSON не найден")

    clean_json = raw[start:end+1]
    data = json.loads(clean_json)

    if not data.get("success"):
        return data
        raise RuntimeError("Ошибка API vocloner")


    file_url = "https://vocloner.com/" + data["file_path"]

    async with aiohttp.ClientSession() as session:
        async with session.get(file_url) as f:
            file_bytes = await f.read()

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    tmp.write(file_bytes)
    tmp.flush()
    tmp.close()

    return tmp.name





# ================== OPENROUTER ==================
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key="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"
)

# ================== TELEGRAM BOT ==================
TG_TOKEN = "8500720899:AAF7qu-NvjjHu_xfvBVeQOmpG6SMiZemzW4"

bot = Bot(
    token=TG_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

dp = Dispatcher()

user_profiles = {}


# ================== ЗАГРУЗКА ПРОФИЛЯ ==================

def load_profile(file_name):
    with open(file_name, "r", encoding="utf-8") as f:
        data = json.load(f)

    target_name = data.get("name")
    messages_list = []

    for msg in data.get("messages", []):
        if msg.get("from") == target_name:
            text = msg.get("text")

            if isinstance(text, list):
                parts = []
                for t in text:
                    if isinstance(t, dict):
                        parts.append(t.get("text", ""))
                    else:
                        parts.append(str(t))
                text = "".join(parts)

            messages_list.append(text)

    history_text = ", ".join(messages_list)

    chat_history = [{
        "role": "user",
        "content": (
            f"Ты — цифровой двойник {target_name}, который писал так: {history_text}. "
            f"Используй тот же стиль общения. Отвечай одним коротким сообщением, не соединяй много в одно. НЕ используй мат Отвечай на то что спрашивает собеседник, не придумывай, если не было в диалоге"
        )
    }]

    return target_name, chat_history


# ================== СТАРТ ==================

@dp.message(CommandStart())
async def start(message: types.Message):
    await message.answer(
        "Привет! Выбери чьим голосом отвечать:\n\n"
        #"/dima — Дима\n"
        "/maks — Макс\n"
        "/tema — Тема\n"
        "/atabek — Атабек"
    )

# ================== ВЫБОР ПЕРСОНЫ ==================

@dp.message(Command(commands=["dima", "maks", "tema", "atabek"]))
async def select_person(message: types.Message):

    chat_id = message.chat.id
    command = message.text[1:]

    filename = f"{command}.json"

    try:
        target_name, chat_history = load_profile(filename)
    except Exception as e:
        return await message.answer("Файл профиля не найден.")

    user_profiles[chat_id] = {
        "name": target_name,
        "history": chat_history
    }

    await message.answer(f"Теперь я пишу как {target_name}. Пиши сообщение.")


# ================== ОСНОВНОЙ ДИАЛОГ ==================

@dp.message()
async def dialog(message: types.Message):

    chat_id = message.chat.id

    if chat_id not in user_profiles:
        return await message.answer("Сначала выбери профиль: /tema /maks /atabek")

    profile = user_profiles[chat_id]
    target_name = profile["name"]
    chat_history = profile["history"]
    rnd = random.randint(0,1)
    user_input = message.text
    chat_history.append({"role": "user", "content": user_input})
    if rnd == 0:
      await bot.send_chat_action(chat_id, "typing")
    else:
      await bot.send_chat_action(chat_id, "record_audio")
    completion = client.chat.completions.create(
        model="kwaipilot/kat-coder-pro:free",
        #model="openai/gpt-oss-20b:free",
        messages=chat_history
    )

    bot_reply = completion.choices[0].message.content
    chat_history.append({"role": "assistant", "content": bot_reply})
    try:
      if target_name in ("макс", "Артём (())"):

        voice_name = max if target_name == "макс" else artem

        if rnd == 0:
            await message.answer(f"<b>{target_name}:</b> {bot_reply}")
        else:
            tmp_path = await voice_message(bot_reply, voice_name)

            if tmp_path:
                await message.answer_voice(FSInputFile(tmp_path))
            else:
                await message.answer(f"<b>{target_name}:</b> {bot_reply}")
      else:
        await message.answer(f"<b>{target_name}:</b> {bot_reply}")
    except Exception as e:
        return await message.answer(f"Что-то пошло не так :(\n Информация для технического специалиста: <tg-spoiler>{e}</tg-spoiler>", parse_mode='html')


# ================== ЗАПУСК ==================

async def main(): await dp.start_polling(bot)
await main()





