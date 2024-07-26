import logging
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, ConversationHandler
import sqlite3
import config

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name(config.GOOGLE_SHEETS_CREDENTIALS, scope)
client = gspread.authorize(creds)

sheet = client.open_by_key(config.SHEET_ID).sheet1

QUESTION, ANSWER = range(2)

def create_user_table():
    conn = sqlite3.connect('students_progress.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

create_user_table()

async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text(
        'Привет! Выберите действие:\n'
        '1. /register - Регистрация\n'
        '2. /login - Вход'
    )

async def register(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text('Введите имя пользователя:')
    return 'USERNAME'

async def get_username(update: Update, context: CallbackContext) -> None:
    context.user_data['username'] = update.message.text
    await update.message.reply_text('Введите пароль:')
    return 'PASSWORD'

async def get_password(update: Update, context: CallbackContext) -> None:
    username = context.user_data['username']
    password = update.message.text

    conn = sqlite3.connect('students_progress.db')
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
    if cursor.fetchone() is not None:
        await update.message.reply_text('Этот пользователь уже существует. Попробуйте другое имя пользователя или войдите в свою учетную запись.')
        conn.close()
        return ConversationHandler.END

    cursor.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password))
    conn.commit()
    conn.close()
    await update.message.reply_text('Вы успешно зарегистрированы! Вы можете войти, используя ваше имя пользователя и пароль.')
    return ConversationHandler.END

async def login(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text('Введите имя пользователя для входа:')
    return 'LOGIN_USERNAME'

async def get_login_username(update: Update, context: CallbackContext) -> None:
    context.user_data['login_username'] = update.message.text
    await update.message.reply_text('Введите пароль:')
    return 'LOGIN_PASSWORD'

async def get_login_password(update: Update, context: CallbackContext) -> None:
    username = context.user_data['login_username']
    password = update.message.text

    conn = sqlite3.connect('students_progress.db')
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password))
    if cursor.fetchone() is None:
        await update.message.reply_text('Неверное имя пользователя или пароль. Попробуйте еще раз.')
        conn.close()
        return ConversationHandler.END

    await update.message.reply_text('Вы успешно вошли в свою учетную запись!')
    conn.close()
    return ConversationHandler.END

async def cancel(update: Update, context: CallbackContext) -> int:
    await update.message.reply_text('Операция отменена.')
    return ConversationHandler.END

def main() -> None:
    application = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()

    conv_handler_registration = ConversationHandler(
        entry_points=[CommandHandler('register', register)],
        states={
            'USERNAME': [MessageHandler(filters.TEXT & ~filters.COMMAND, get_username)],
            'PASSWORD': [MessageHandler(filters.TEXT & ~filters.COMMAND, get_password)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    conv_handler_login = ConversationHandler(
        entry_points=[CommandHandler('login', login)],
        states={
            'LOGIN_USERNAME': [MessageHandler(filters.TEXT & ~filters.COMMAND, get_login_username)],
            'LOGIN_PASSWORD': [MessageHandler(filters.TEXT & ~filters.COMMAND, get_login_password)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    application.add_handler(CommandHandler('start', start))
    application.add_handler(conv_handler_registration)
    application.add_handler(conv_handler_login)

    application.run_polling()

if __name__ == '__main__':
    main()
