# create_db.py
from app import db, app

with app.app_context():
    db.drop_all()  # Удаляем старую базу
    db.create_all()  # Создаем новую с полем date
    print("✅ База данных обновлена!")