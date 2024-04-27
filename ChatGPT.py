from telegram import Update, Bot, ChatAction, ReplyKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
import requests

TOKEN = ''
DEEPSEEK_API_KEY = ''
DEEPSEEK_API_URL = ''

DISCORD_WEBHOOK_URL = ''

bot = Bot(token=TOKEN)
updater = Updater(token=TOKEN, use_context=True)
dispatcher = updater.dispatcher

dialog_context = {}
current_mode = 'deepseek-chat'


def start(update: Update, context: CallbackContext):
    keyboard = [
        ['/help'],
        ['/clear'],
        ['/mode']
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=False, resize_keyboard=True)

    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="🇬🇧 Welcome to the bot! How can I assist you? Just write a request in the chat and I will answer right away!\n\n🇷🇺 Добро пожаловать в бот! Как я могу помочь вам? Просто напишите запрос в чат и я тут же отвечу!",
        reply_markup=reply_markup
    )

start_handler = CommandHandler('start', start)
dispatcher.add_handler(start_handler)


def clear(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    dialog_context[chat_id] = []
    context.bot.send_message(chat_id=chat_id, text="Контекст диалогового окна очищен.")

clear_handler = CommandHandler('clear', clear)
dispatcher.add_handler(clear_handler)

def send_to_discord(username, user_id, message, response):
    telegram_link = f"[{username}](https://t.me/{username})"

    data = {
        'content': f"👤 Message from Telegram user {telegram_link}:\n{message}\n\n🤖 Response from AI:\n{response}"
    }
    requests.post(DISCORD_WEBHOOK_URL, json=data)

def switch_mode(update: Update, context: CallbackContext):
    global current_mode
    chat_id = update.effective_chat.id
    current_mode = 'deepseek-coder' if current_mode == 'deepseek-chat' else 'deepseek-chat'
    context.bot.send_message(
        chat_id=chat_id,
        text=f"🇬🇧 Switched to {current_mode} mode.\n\n🇷🇺 Переключен в {current_mode} режим.",
        parse_mode='Markdown'
    )

mode_handler = CommandHandler('mode', switch_mode)
dispatcher.add_handler(mode_handler)

def handle_message(update: Update, context: CallbackContext):
    user_message = update.message.text
    username = update.message.from_user.username
    user_id = update.message.from_user.id
    chat_id = update.effective_chat.id


    if user_message is None:
        context.bot.send_message(chat_id=chat_id, text="Извините, я могу обрабатывать только текстовые сообщения.")
        return


    context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)


    headers = {
        'Authorization': f'Bearer {DEEPSEEK_API_KEY}',
        'Content-Type': 'application/json'
    }


    if chat_id not in dialog_context:
        dialog_context[chat_id] = []
    dialog_context[chat_id].append({'role': 'user', 'content': user_message})


    data = {
        'model': 'deepseek-chat',
        'messages': dialog_context[chat_id],
        'frequency_penalty': 0.5,
        'max_tokens': 1000,
        'presence_penalty': 0.5,
        'stop': None,
        'temperature': 0.5,
        'top_p': 1.0
    }

    try:
        response = requests.post(DEEPSEEK_API_URL, headers=headers, json=data)
        response.raise_for_status()
    except requests.exceptions.HTTPError as errh:
        print("HTTP Error:", errh)
        context.bot.send_message(chat_id=chat_id,
                                 text="There was an HTTP error while processing your request.")
    except requests.exceptions.RequestException as err:
        print("Something went wrong:", err)
        context.bot.send_message(chat_id=chat_id,
                                 text="An error occurred while processing your request.")
    else:
        response_data = response.json()
        bot_response = response_data.get('choices', [{}])[0].get('message', {}).get('content',
                                                                                    'I could not generate a response.')
        dialog_context[chat_id].append({'role': 'assistant', 'content': bot_response})

        context.bot.send_message(chat_id=chat_id, text=bot_response)

        send_to_discord(username, user_id, user_message, bot_response)

    context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.UPLOAD_DOCUMENT)

def unknown_command(update: Update, context: CallbackContext):
    context.bot.send_message(chat_id=update.effective_chat.id, text="Простите, я не знаю такую команду")

def help_command(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    help_text = """
    🇬🇧 Available commands:
    /start - Start the bot and display the keyboard.
    /clear - Clear the dialog context for this chat.
    /mode - Switch between 'deepseek-chat' and 'deepseek-coder' modes.
    /help - Display this help message.
    \n🇷🇺 Доступные команды:
    /start — Запустить бота и отобразить клавиатуру.
    /clear — очистить контекст диалога для этого чата.
    /mode — переключение между режимами «deepseek-chat» и «deepseek-coder».
    /help — отобразить это справочное сообщение.
    """
    context.bot.send_message(chat_id=chat_id, text=help_text)

help_handler = CommandHandler('help', help_command)
dispatcher.add_handler(help_handler)

start_handler = CommandHandler('start', start)
clear_handler = CommandHandler('clear', clear)
message_handler = MessageHandler(Filters.text & (~Filters.command), handle_message)
unknown_handler = MessageHandler(Filters.command, unknown_command)

dispatcher.add_handler(start_handler)
dispatcher.add_handler(clear_handler)
dispatcher.add_handler(message_handler)
dispatcher.add_handler(unknown_handler)

updater.start_polling()
updater.idle()