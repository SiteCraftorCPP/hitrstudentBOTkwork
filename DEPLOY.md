# 🚀 Инструкция по деплою

## Подготовка к деплою

### 1. Локальная подготовка

1. **Проверьте, что все файлы на месте:**
   - `env.example` - пример переменных окружения
   - `.env` - ваши реальные настройки (не коммитится в Git)
   - `requirements.txt` - зависимости
   - `README.md` - документация

2. **Обновите `.env` файл:**
   - Укажите реальный `BOT_TOKEN`
   - Проверьте `ADMINS` (ID администраторов)
   - Остальные настройки можно оставить по умолчанию

3. **Проверьте `.gitignore`:**
   - Убедитесь, что `.env`, `*.db`, `logs/` в игноре

### 2. Коммит в Git

```bash
git add .
git commit -m "Подготовка к деплою"
git push origin main
```

## Деплой на VPS

### Шаг 1: Подключение к серверу

```bash
ssh user@your-server-ip
```

### Шаг 2: Установка зависимостей

```bash
# Обновляем систему
sudo apt update && sudo apt upgrade -y

# Устанавливаем Python и pip
sudo apt install python3 python3-pip python3-venv -y

# Устанавливаем git (если нет)
sudo apt install git -y
```

### Шаг 3: Клонирование проекта

```bash
# Создаем директорию для проекта
sudo mkdir -p /opt/telegram-bot
sudo chown $USER:$USER /opt/telegram-bot

# Клонируем репозиторий
cd /opt/telegram-bot
git clone <your-repo-url> .

# Или если уже есть репозиторий, просто:
git pull
```

### Шаг 4: Настройка окружения

```bash
# Создаем виртуальное окружение
python3 -m venv venv
source venv/bin/activate

# Устанавливаем зависимости
pip install -r requirements.txt

# Создаем .env файл
cp env.example .env
nano .env  # Отредактируйте настройки
```

**Важно:** В `.env` укажите:
- `BOT_TOKEN` - ваш токен бота
- `ADMINS` - ваш ID администратора

### Шаг 5: Настройка systemd сервиса

```bash
# Копируем файл сервиса
sudo cp telegram-bot.service /etc/systemd/system/

# Редактируем пути в сервисе (если нужно)
sudo nano /etc/systemd/system/telegram-bot.service
```

**Измените в файле:**
- `User=your-user` → `User=ваш-пользователь`
- `/opt/telegram-bot` → ваш путь к проекту (если другой)

### Шаг 6: Запуск сервиса

```bash
# Перезагружаем systemd
sudo systemctl daemon-reload

# Включаем автозапуск
sudo systemctl enable telegram-bot

# Запускаем бота
sudo systemctl start telegram-bot

# Проверяем статус
sudo systemctl status telegram-bot
```

### Шаг 7: Просмотр логов

```bash
# Логи systemd
sudo journalctl -u telegram-bot -f

# Логи бота
tail -f /opt/telegram-bot/logs/bot.log
```

## Управление ботом

### Остановка
```bash
sudo systemctl stop telegram-bot
```

### Запуск
```bash
sudo systemctl start telegram-bot
```

### Перезапуск
```bash
sudo systemctl restart telegram-bot
```

### Статус
```bash
sudo systemctl status telegram-bot
```

## Обновление бота

```bash
# 1. Останавливаем бота
sudo systemctl stop telegram-bot

# 2. Делаем бэкап БД
cd /opt/telegram-bot
cp bot_database.db bot_database.db.backup

# 3. Обновляем код
git pull

# 4. Обновляем зависимости (если нужно)
source venv/bin/activate
pip install -r requirements.txt

# 5. Запускаем бота
sudo systemctl start telegram-bot

# 6. Проверяем логи
tail -f logs/bot.log
```

## Бэкапы

### Автоматический бэкап (cron)

Создайте скрипт бэкапа:

```bash
nano /opt/telegram-bot/backup.sh
```

```bash
#!/bin/bash
BACKUP_DIR="/opt/backups/telegram-bot"
mkdir -p $BACKUP_DIR
cp /opt/telegram-bot/bot_database.db $BACKUP_DIR/bot_database_$(date +%Y%m%d_%H%M%S).db
# Удаляем старые бэкапы (старше 7 дней)
find $BACKUP_DIR -name "bot_database_*.db" -mtime +7 -delete
```

```bash
chmod +x /opt/telegram-bot/backup.sh
```

Добавьте в crontab:

```bash
crontab -e
```

Добавьте строку (бэкап каждый день в 3:00):

```
0 3 * * * /opt/telegram-bot/backup.sh
```

## Решение проблем

### Бот не запускается

1. Проверьте логи:
```bash
sudo journalctl -u telegram-bot -n 50
```

2. Проверьте .env файл:
```bash
cat /opt/telegram-bot/.env
```

3. Проверьте права доступа:
```bash
ls -la /opt/telegram-bot
```

### Бот падает с ошибкой

1. Проверьте логи бота:
```bash
tail -100 /opt/telegram-bot/logs/bot.log
```

2. Проверьте, что все зависимости установлены:
```bash
source venv/bin/activate
pip list
```

### База данных заблокирована

```bash
# Остановите бота
sudo systemctl stop telegram-bot

# Проверьте процессы
ps aux | grep python

# Если нужно, убейте процесс
kill -9 <PID>
```

## Безопасность

1. **Firewall:**
```bash
sudo ufw allow 22/tcp  # SSH
sudo ufw enable
```

2. **Регулярные обновления:**
```bash
sudo apt update && sudo apt upgrade -y
```

3. **Бэкапы БД:**
- Настройте автоматические бэкапы (см. выше)
- Регулярно проверяйте наличие бэкапов

## Полезные команды

```bash
# Просмотр использования ресурсов
htop

# Просмотр места на диске
df -h

# Просмотр процессов Python
ps aux | grep python

# Перезагрузка сервера
sudo reboot
```

