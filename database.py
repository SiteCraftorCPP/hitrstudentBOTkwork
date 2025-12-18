import sqlite3
import datetime
from typing import Optional, List, Dict, Tuple
from config import DB_NAME


class Database:
    def __init__(self):
        try:
            self.conn = sqlite3.connect(DB_NAME, check_same_thread=False, timeout=10.0)
            self.conn.row_factory = sqlite3.Row
            self.create_tables()
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Ошибка при инициализации базы данных: {e}", exc_info=True)
            raise

    def create_tables(self):
        try:
            cursor = self.conn.cursor()
            
            # Таблица пользователей
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    balance REAL DEFAULT 0.0,
                    withdrawn REAL DEFAULT 0.0,
                    referrer_id INTEGER,
                    invited_count INTEGER DEFAULT 0,
                    last_daily_bonus DATE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Таблица заданий
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    channel_username TEXT,
                    channel_link TEXT,
                    reward REAL DEFAULT 0.0,
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Добавляем поле channel_link, если его нет (для существующих баз данных)
            try:
                cursor.execute("ALTER TABLE tasks ADD COLUMN channel_link TEXT")
            except sqlite3.OperationalError:
                pass  # Поле уже существует
            
            # Таблица выполненных заданий
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS completed_tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    task_id INTEGER,
                    completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id),
                    FOREIGN KEY (task_id) REFERENCES tasks(task_id),
                    UNIQUE(user_id, task_id)
                )
            """)
            
            # Таблица подписок
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS subscriptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    channel_username TEXT,
                    subscribed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id),
                    UNIQUE(user_id, channel_username)
                )
            """)
            
            # Таблица выводов
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS withdrawals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    amount REAL,
                    method TEXT,
                    wallet TEXT,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """)
            
            # Таблица настроек
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)
            
            # Таблица каналов для подписки
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS subscribe_channels (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    channel_username TEXT,
                    channel_link TEXT,
                    channel_chat_id TEXT,
                    display_name TEXT,
                    order_index INTEGER DEFAULT 0,
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Добавляем поле channel_chat_id, если его нет
            try:
                cursor.execute("ALTER TABLE subscribe_channels ADD COLUMN channel_chat_id TEXT")
            except sqlite3.OperationalError:
                pass  # Поле уже существует
            
            # Таблица для отслеживания награды за набор каналов
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS channel_rewards (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    channels_hash TEXT,
                    rewarded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id),
                    UNIQUE(user_id, channels_hash)
                )
            """)
            
            # Инициализация настроек
            cursor.execute("""
                INSERT OR IGNORE INTO settings (key, value) 
                VALUES ('bot_created_date', '12.06.2024'),
                       ('total_users', '0'),
                       ('total_withdrawn', '0'),
                       ('withdraw_site_confirmation_text', '💸 Подтвердите вывод\n\nСумма: {amount:.0f} Rcoin\n\n📌 Пример: 5000 Rcoin = 1000 рублей на балансе\n\nПодтверждаете вывод?'),
                       ('withdraw_site_success_text', '✅ Заявка на вывод создана!\n\n⏳ Ожидайте исполнения заявки.'),
                       ('withdraw_site_link', 'https://example.com'),
                       ('daily_bonus_min', '1'),
                       ('daily_bonus_max', '50'),
                       ('subscribe_button_text', '📢 Подписаться на каналы'),
                       ('subscribe_message_text', '📢 Подпишитесь на каналы для получения награды!')
            """)
            
            self.conn.commit()
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Ошибка при создании таблиц: {e}", exc_info=True)
            self.conn.rollback()
            raise

    def get_user(self, user_id: int) -> Optional[Dict]:
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            if row:
                return {key: row[key] for key in row.keys()}
            return None
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Ошибка в get_user: {e}", exc_info=True)
            return None

    def create_user(self, user_id: int, username: str, first_name: str, referrer_id: Optional[int] = None):
        cursor = self.conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO users (user_id, username, first_name, referrer_id)
                VALUES (?, ?, ?, ?)
            """, (user_id, username, first_name, referrer_id))
            self.conn.commit()
            
            # Обновляем статистику
            if referrer_id:
                cursor.execute("""
                    UPDATE users SET invited_count = invited_count + 1 
                    WHERE user_id = ?
                """, (referrer_id,))
                self.conn.commit()
            
            # Обновляем общее количество пользователей
            cursor.execute("UPDATE settings SET value = CAST(value AS INTEGER) + 1 WHERE key = 'total_users'")
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def update_user_balance(self, user_id: int, amount: float) -> bool:
        """Обновляет баланс пользователя. Если пользователя нет - создает его."""
        try:
            cursor = self.conn.cursor()
            
            # Создаем пользователя, если его нет
            cursor.execute("""
                INSERT OR IGNORE INTO users (user_id, username, first_name, balance)
                VALUES (?, ?, ?, 0.0)
            """, (user_id, "", ""))
            
            # Обновляем баланс
            cursor.execute("""
                UPDATE users SET balance = balance + ? WHERE user_id = ?
            """, (amount, user_id))
            
            self.conn.commit()
            
            # Проверяем, что обновление прошло успешно
            if cursor.rowcount > 0:
                return True
            else:
                # Если UPDATE не затронул строки, пробуем еще раз
                cursor.execute("""
                    INSERT OR IGNORE INTO users (user_id, username, first_name, balance)
                    VALUES (?, ?, ?, ?)
                """, (user_id, "", "", amount))
                cursor.execute("""
                    UPDATE users SET balance = balance + ? WHERE user_id = ?
                """, (amount, user_id))
                self.conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Ошибка при обновлении баланса: {e}", exc_info=True)
            self.conn.rollback()
            return False

    def get_referrer(self, user_id: int) -> Optional[int]:
        user = self.get_user(user_id)
        return user['referrer_id'] if user else None

    def get_invited_count(self, user_id: int) -> int:
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM users WHERE referrer_id = ?", (user_id,))
        row = cursor.fetchone()
        return row['count'] if row else 0

    def get_friends_referrals_count(self, user_id: int) -> int:
        """Подсчет рефералов друзей (рефералы рефералов)"""
        cursor = self.conn.cursor()
        # Получаем всех прямых рефералов
        cursor.execute("SELECT user_id FROM users WHERE referrer_id = ?", (user_id,))
        direct_referrals = cursor.fetchall()
        
        total = 0
        for ref in direct_referrals:
            cursor.execute("SELECT COUNT(*) as count FROM users WHERE referrer_id = ?", (ref['user_id'],))
            row = cursor.fetchone()
            total += row['count'] if row else 0
        
        return total

    def can_get_daily_bonus(self, user_id: int):
        """
        Проверяет, может ли пользователь получить ежедневный бонус.
        Возвращает (can_get: bool, next_date: date или None)
        Бонус обновляется каждый день (не через 24 часа, а в новую дату)
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT last_daily_bonus FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        if not row or not row['last_daily_bonus']:
            return True, None
        
        try:
            last_date = datetime.datetime.strptime(row['last_daily_bonus'], '%Y-%m-%d').date()
            today = datetime.date.today()
            
            if last_date < today:
                # Можно получить бонус (прошлый раз был вчера или раньше)
                return True, None
            else:
                # Бонус уже получен сегодня, следующий доступен завтра
                next_date = today + datetime.timedelta(days=1)
                return False, next_date
        except (ValueError, TypeError):
            # Если ошибка парсинга даты, разрешаем получить бонус
            return True, None

    def set_daily_bonus(self, user_id: int, amount: float):
        cursor = self.conn.cursor()
        today = datetime.date.today().isoformat()
        cursor.execute("""
            UPDATE users SET last_daily_bonus = ?, balance = balance + ?
            WHERE user_id = ?
        """, (today, amount, user_id))
        self.conn.commit()

    def add_task(self, task_type: str, title: str, description: str = None, 
                 channel_username: str = None, channel_link: str = None, reward: float = 0.0) -> int:
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO tasks (task_type, title, description, channel_username, channel_link, reward)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (task_type, title, description, channel_username, channel_link, reward))
        self.conn.commit()
        return cursor.lastrowid

    def get_tasks(self, task_type: str = None, active_only: bool = True) -> List[Dict]:
        cursor = self.conn.cursor()
        if task_type:
            cursor.execute("""
                SELECT * FROM tasks 
                WHERE task_type = ? AND is_active = ?
                ORDER BY created_at DESC
            """, (task_type, 1 if active_only else 0))
        else:
            cursor.execute("""
                SELECT * FROM tasks 
                WHERE is_active = ?
                ORDER BY created_at DESC
            """, (1 if active_only else 0,))
        return [dict(row) for row in cursor.fetchall()]

    def complete_task(self, user_id: int, task_id: int) -> bool:
        cursor = self.conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO completed_tasks (user_id, task_id)
                VALUES (?, ?)
            """, (user_id, task_id))
            
            # Начисляем награду
            cursor.execute("SELECT reward FROM tasks WHERE task_id = ?", (task_id,))
            task = cursor.fetchone()
            if task:
                self.update_user_balance(user_id, task['reward'])
            
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def is_task_completed(self, user_id: int, task_id: int) -> bool:
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) as count FROM completed_tasks 
            WHERE user_id = ? AND task_id = ?
        """, (user_id, task_id))
        row = cursor.fetchone()
        return row['count'] > 0 if row else False

    def add_subscription(self, user_id: int, channel_username: str):
        cursor = self.conn.cursor()
        try:
            cursor.execute("""
                INSERT OR IGNORE INTO subscriptions (user_id, channel_username)
                VALUES (?, ?)
            """, (user_id, channel_username))
            self.conn.commit()
            return True
        except Exception:
            return False

    def is_subscribed(self, user_id: int, channel_username: str) -> bool:
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) as count FROM subscriptions 
            WHERE user_id = ? AND channel_username = ?
        """, (user_id, channel_username))
        row = cursor.fetchone()
        return row['count'] > 0 if row else False

    def create_withdrawal(self, user_id: int, amount: float, method: str, wallet: str = None) -> int:
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO withdrawals (user_id, amount, method, wallet, status)
            VALUES (?, ?, ?, ?, 'pending')
        """, (user_id, amount, method, wallet))
        
        # Только списываем баланс, НЕ обновляем withdrawn
        # withdrawn будет обновлен только при подтверждении вывода админом
        cursor.execute("""
            UPDATE users SET balance = balance - ?
            WHERE user_id = ?
        """, (amount, user_id))
        
        # НЕ обновляем статистику total_withdrawn здесь
        # Она будет обновлена только при подтверждении вывода
        
        self.conn.commit()
        return cursor.lastrowid
    
    def confirm_withdrawal(self, withdrawal_id: int) -> bool:
        """Подтверждает вывод - обновляет withdrawn и статистику"""
        cursor = self.conn.cursor()
        
        # Получаем информацию о выводе
        cursor.execute("""
            SELECT user_id, amount, status FROM withdrawals WHERE id = ?
        """, (withdrawal_id,))
        withdrawal = cursor.fetchone()
        
        if not withdrawal or withdrawal['status'] != 'pending':
            return False
        
        user_id = withdrawal['user_id']
        amount = withdrawal['amount']
        
        # Обновляем withdrawn только при подтверждении
        cursor.execute("""
            UPDATE users SET withdrawn = withdrawn + ?
            WHERE user_id = ?
        """, (amount, user_id))
        
        # Обновляем статистику
        from config import COIN_TO_RUB
        rub_amount = amount / COIN_TO_RUB
        cursor.execute("""
            UPDATE settings SET value = CAST(value AS REAL) + ?
            WHERE key = 'total_withdrawn'
        """, (rub_amount,))
        
        # Меняем статус заявки
        cursor.execute("""
            UPDATE withdrawals SET status = 'completed'
            WHERE id = ?
        """, (withdrawal_id,))
        
        self.conn.commit()
        return True

    def get_statistics(self) -> Dict:
        cursor = self.conn.cursor()
        stats = {}
        
        cursor.execute("SELECT value FROM settings WHERE key = 'total_users'")
        row = cursor.fetchone()
        stats['total_users'] = int(row['value']) if row else 0
        
        cursor.execute("SELECT value FROM settings WHERE key = 'total_withdrawn'")
        row = cursor.fetchone()
        stats['total_withdrawn'] = float(row['value']) if row else 0.0
        
        cursor.execute("SELECT value FROM settings WHERE key = 'bot_created_date'")
        row = cursor.fetchone()
        stats['bot_created_date'] = row['value'] if row else '12.06.2024'
        
        return stats

    def update_task(self, task_id: int, **kwargs):
        cursor = self.conn.cursor()
        updates = []
        values = []
        
        for key, value in kwargs.items():
            if key in ['title', 'description', 'channel_username', 'reward', 'is_active']:
                updates.append(f"{key} = ?")
                values.append(value)
        
        if updates:
            values.append(task_id)
            cursor.execute(f"""
                UPDATE tasks SET {', '.join(updates)}
                WHERE task_id = ?
            """, values)
            self.conn.commit()

    def delete_task(self, task_id: int):
        cursor = self.conn.cursor()
        cursor.execute("UPDATE tasks SET is_active = 0 WHERE task_id = ?", (task_id,))
        self.conn.commit()

    def get_setting(self, key: str, default: str = "") -> str:
        """Получить настройку по ключу"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = cursor.fetchone()
        return row['value'] if row else default

    def set_setting(self, key: str, value: str):
        """Установить настройку"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO settings (key, value)
            VALUES (?, ?)
        """, (key, value))
        self.conn.commit()

    def get_all_users(self) -> List[int]:
        """Получить список всех user_id пользователей"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT user_id FROM users")
        rows = cursor.fetchall()
        return [row['user_id'] for row in rows]

    def get_subscribe_channels(self, active_only: bool = True) -> List[Dict]:
        """Получить список активных каналов для подписки"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM subscribe_channels 
            WHERE is_active = 1 
            ORDER BY order_index, id
        """)
        rows = cursor.fetchall()
        return [{key: row[key] for key in row.keys()} for row in rows]

    def add_subscribe_channel(self, channel_username: str, channel_link: str, display_name: str, channel_chat_id: str = None) -> int:
        """Добавить канал для подписки"""
        cursor = self.conn.cursor()
        # Проверяем, нет ли уже такого канала (по username или link)
        cursor.execute("""
            SELECT id FROM subscribe_channels 
            WHERE (channel_username = ? OR channel_link = ?) AND is_active = 1
        """, (channel_username, channel_link))
        existing = cursor.fetchone()
        if existing:
            # Канал уже существует - возвращаем его ID
            return existing['id']
        
        cursor.execute("""
            INSERT INTO subscribe_channels (channel_username, channel_link, display_name, channel_chat_id)
            VALUES (?, ?, ?, ?)
        """, (channel_username, channel_link, display_name, channel_chat_id))
        self.conn.commit()
        return cursor.lastrowid

    def delete_subscribe_channel(self, channel_id: int):
        """Удалить канал для подписки"""
        cursor = self.conn.cursor()
        # Физически удаляем канал из БД
        cursor.execute("DELETE FROM subscribe_channels WHERE id = ?", (channel_id,))
        self.conn.commit()

    def update_subscribe_channel(self, channel_id: int, **kwargs):
        """Обновить канал для подписки"""
        cursor = self.conn.cursor()
        updates = []
        values = []
        
        for key, value in kwargs.items():
            if key in ['channel_username', 'channel_link', 'channel_chat_id', 'display_name', 'order_index', 'is_active']:
                updates.append(f"{key} = ?")
                values.append(value)
        
        if updates:
            values.append(channel_id)
            cursor.execute(f"""
                UPDATE subscribe_channels SET {', '.join(updates)}
                WHERE id = ?
            """, values)
            self.conn.commit()

    def get_subscribe_channel(self, channel_id: int) -> Optional[Dict]:
        """Получить канал по ID"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM subscribe_channels WHERE id = ?", (channel_id,))
        row = cursor.fetchone()
        if row:
            return {key: row[key] for key in row.keys()}
        return None
    
    def get_channels_hash(self) -> str:
        """Получить хеш текущего списка активных каналов для подписки"""
        import hashlib
        channels = self.get_subscribe_channels()
        # Создаем строку из ID каналов, отсортированных по ID
        channel_ids = sorted([str(ch['id']) for ch in channels])
        channels_str = ','.join(channel_ids)
        return hashlib.md5(channels_str.encode()).hexdigest()
    
    def has_received_reward_for_channels(self, user_id: int, channels_hash: str) -> bool:
        """Проверить, получал ли пользователь награду за этот набор каналов"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) as count FROM channel_rewards 
            WHERE user_id = ? AND channels_hash = ?
        """, (user_id, channels_hash))
        row = cursor.fetchone()
        return row['count'] > 0 if row else False
    
    def mark_reward_received(self, user_id: int, channels_hash: str):
        """Отметить, что пользователь получил награду за этот набор каналов"""
        cursor = self.conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO channel_rewards (user_id, channels_hash)
                VALUES (?, ?)
            """, (user_id, channels_hash))
            self.conn.commit()
        except sqlite3.IntegrityError:
            # Уже существует
            pass

