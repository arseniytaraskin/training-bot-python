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

async def start(update: Update, context: CallbackContext) -> int:
    await update.message.reply_text('Привет! Я твой помощник по курсу Python. Готов к заданиям? Напиши /next, чтобы получить первое задание.')
    return QUESTION

async def next_task(update: Update, context: CallbackContext) -> int:
    student_id = update.message.from_user.id
    username = update.message.from_user.username

    conn = sqlite3.connect('students_progress.db')
    cursor = conn.cursor()

    cursor.execute('SELECT completed_tasks FROM progress WHERE student_id = ?', (student_id,))
    result = cursor.fetchone()

    if result:
        completed_tasks = result[0]
    else:
        completed_tasks = 0
        cursor.execute('INSERT INTO progress (student_id, username, completed_tasks, rating) VALUES (?, ?, ?, ?)', (student_id, username, 0, 0))
        conn.commit()

    task_row = completed_tasks + 2
    task = sheet.row_values(task_row)

    if task:
        context.user_data['task'] = task
        await update.message.reply_text(f'Задание {completed_tasks + 1}: {task[1]}')
        conn.close()
        return ANSWER
    else:
        await update.message.reply_text('Все задания выполнены!')
        conn.close()
        return ConversationHandler.END

async def check_answer(update: Update, context: CallbackContext) -> int:
    student_id = update.message.from_user.id
    answer = update.message.text
    task = context.user_data['task']
    correct_answer = task[2] if len(task) > 2 else None
    points = int(task[3]) if len(task) > 3 else 0

    conn = sqlite3.connect('students_progress.db')
    cursor = conn.cursor()

    if correct_answer and answer.strip() == correct_answer:
        cursor.execute('UPDATE progress SET completed_tasks = completed_tasks + 1, rating = rating + ? WHERE student_id = ?', (points, student_id))
        await update.message.reply_text('Правильно! Ты получаешь баллы!')
    else:
        cursor.execute('UPDATE progress SET completed_tasks = completed_tasks + 1 WHERE student_id = ?', (student_id,))
        await update.message.reply_text('Ответ получен. Следующее задание доступно с командой /next')

    conn.commit()
    conn.close()
    return ConversationHandler.END

async def cancel(update: Update, context: CallbackContext) -> int:
    await update.message.reply_text('Задание отменено. Напиши /next для нового задания.')
    return ConversationHandler.END

def main() -> None:
    application = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start), CommandHandler('next', next_task)],
        states={
            QUESTION: [CommandHandler('next', next_task)],
            ANSWER: [MessageHandler(filters.TEXT & ~filters.COMMAND, check_answer)]
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    application.add_handler(conv_handler)

    application.run_polling()

if __name__ == '__main__':
    main()



