import sqlite3


conn = sqlite3.connect('students_progress.db')
cursor = conn.cursor()


cursor.execute('''
CREATE TABLE IF NOT EXISTS progress (
    student_id INTEGER PRIMARY KEY,
    username TEXT,
    completed_tasks INTEGER,
    rating INTEGER
)
''')

conn.commit()
conn.close()
