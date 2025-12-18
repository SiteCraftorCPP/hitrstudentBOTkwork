"""Тестовый скрипт для проверки базы данных"""
from database import Database
import traceback

try:
    db = Database()
    print("OK: База данных подключена")
    
    # Проверяем таблицы
    cursor = db.conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    print(f"OK: Таблицы: {[t[0] for t in tables]}")
    
    # Тестируем создание пользователя
    test_user_id = 123456789
    print(f"\nТестируем создание пользователя {test_user_id}...")
    db.create_user(test_user_id, "test_user", "Test User", None)
    print("OK: Пользователь создан")
    
    # Тестируем получение пользователя
    user = db.get_user(test_user_id)
    if user:
        print(f"OK: Пользователь получен: {user}")
        print(f"  - Тип: {type(user)}")
        print(f"  - Ключи: {list(user.keys()) if isinstance(user, dict) else 'не словарь'}")
    else:
        print("ERROR: Пользователь не найден")
    
    # Удаляем тестового пользователя
    cursor.execute("DELETE FROM users WHERE user_id = ?", (test_user_id,))
    db.conn.commit()
    print("OK: Тестовый пользователь удален")
    
except Exception as e:
    print(f"ERROR: {e}")
    traceback.print_exc()

