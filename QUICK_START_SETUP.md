# 🚀 QUICK START (5 minutes)

Готовий до продажу Telegram бот. Полна конфігурація через один файл.

## 📝 Step 1: Setup Configuration

```bash
# Скопіюйте конфігурацію
cp scripts/settings.json.example scripts/settings.json
```

## 🔑 Step 2: Get Credentials

### Telegram Bot Token
1. Напишіть [@BotFather](https://t.me/botfather)
2. Скомандуйте `/newbot`
3. Виберіть ім'я та username
4. Скопіюйте токен → вставте в `bot_token`

### Telegram API Credentials
1. Перейдіть на https://my.telegram.org
2. Залогіньтесь
3. Перейдіть в "API development tools"
4. Створіть Application
5. Копіюйте `api_id` і `api_hash`

### Your Telegram ID
- Напишіть [@userinfobot](https://t.me/userinfobot)
- Отримаєте ID → вставте в `admin_ids`

## ⚙️ Step 3: Fill Configuration

Відредагуйте `scripts/settings.json`:

```json
{
  "bot_token": "7451234567:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefgh",
  "api_id": 27696098,
  "api_hash": "abcdef123456789abc",
  "webapp_url": "https://your-domain.com",
  "admin_ids": [123456789],
  "workers": [123456789],
  "target_user": "@your_username",
  "about_link": "https://t.me/your_channel",
  "profit_channel_id": -1001234567890,
  "logs_channel_id": -1001234567891
}
```

## 🚀 Step 4: Run Bot

### Windows
```bash
scripts/start.bat
```

### Linux/Mac
```bash
bash scripts/run_bot.sh
```

### Manual
```bash
python scripts/main3.py
```

## ✅ Перевіримо

1. Бот має запуститися в консолі
2. Відкрийте бота в Telegram
3. Натисніть `/start`
4. Повинны побачити кнопки

## 📚 Далі

- **Документація**: [BUYER_GUIDE.md](BUYER_GUIDE.md)
- **Налаштування**: [scripts/CONFIGURATION.md](scripts/CONFIGURATION.md)
- **Розгортання**: [SETUP_GUIDE.md](SETUP_GUIDE.md)

---

**Готово! Бот запущено.** 🎉
