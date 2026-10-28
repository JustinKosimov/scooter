# 🛡 Telegram Mafia Guruhi Admin Guard Bot

Ushbu bot Telegram guruhlarda (ayniqsa Mafia o'yin guruhlarida) adminlarning guruh a'zolarini ommaviy BAN qilishini (reyd/nuke) oldini oladi.

Agar biror admin 24 soat ichida belgilangan limitdan (standart: **25 ta**) ko'p foydalanuvchiga BAN bersa:
1. Bot avtomatik ravishda uning **BAN berish huquqini va barcha adminlik vakolatlarini bekor qiladi**.
2. Guruhga shoshilinch ogohlantirish xabari yuboradi.

---

## ⚙️ O'rnatish va Ishga tushirish

### 1. Bot tokenini olish
1. Telegram'da [@BotFather](https://t.me/BotFather) ga kiring.
2. `/newbot` buyrug'ini yuboring va botingizga nom va username tanlang.
3. BotFather bergan **HTTP API Token** ni nusxalab oling.

### 2. O'zingizning Telegram ID raqamingizni bilish
1. Telegram'da [@userinfobot](https://t.me/userinfobot) ga kiring va `/start` bosing.
2. Sizga ID raqamingizni (masalan: `123456789`) beradi.

### 3. `.env` faylini sozlash
`mafia_guard_bot/.env` faylini oching va ma'lumotlarni kiriting:
```env
BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrSTUvwxYZ
OWNER_IDS=123456789
BAN_LIMIT=25
TIME_WINDOW_HOURS=24
```

### 4. Kutubxonalarni o'rnatish
```bash
pip install -r requirements.txt
```

### 5. Botni ishga tushirish
```bash
python main.py
```

---

## 👥 Guruhda Sozlash (Juda muhim qadamlar!)

1. **Botni guruhga qo'shing.**
2. **Botga guruhda to'liq Admin huquqini bering:**
   - Ayniqsa **"Foydalanuvchilarni cheklash / Ban qilish" (Ban users)**
   - Va **"Yangi adminlar qo'shish" (Add new admins)** huquqi yoqilgan bo'lishi shart!
3. **Adminlarni bot orqali tayinlang:**
   - *Telegram qoidasi:* Bot faqat **o'zi tayinlagan** adminlarni lavozimidan tushira oladi.
   - Guruh egasi guruhda admin qilmoqchi bo'lgan foydalanuvchining xabariga reply qilib:
     ```text
     /promote Moderator
     ```
     deb yozadi. Bot uni avtomatik admin qiladi.

---

## 📜 Buyruqlar ro'yxati (Faqat guruh egasi uchun)

* `/promote [Unvon]` — Xabarga reply qilib yozilsa, foydalanuvchini admin qiladi (BAN berish huquqi bilan).
* `/demote` — Xabarga reply qilib yozilsa, adminlik huquqini to'liq bekor qiladi.
* `/stats` — Barcha bot-adminlarning so'nggi 24 soatdagi banlar statistikasini ko'rsatadi.
* `/setlimit 25` — Ban limitini o'zgartirish (masalan: 10, 25, 50).
* `/reset [user_id]` — Adminning ban hisobini 0 ga tushirish.
