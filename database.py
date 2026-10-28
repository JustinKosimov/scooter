import time
import aiosqlite
from config import DB_PATH, BAN_LIMIT, TIME_WINDOW_HOURS


async def init_db():
    """Baza jadvallarini yaratish"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS promoted_admins (
                chat_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                username TEXT,
                first_name TEXT,
                promoted_by INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (chat_id, user_id)
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS ban_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                admin_id INTEGER NOT NULL,
                banned_user_id INTEGER NOT NULL,
                timestamp REAL NOT NULL
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS chat_settings (
                chat_id INTEGER PRIMARY KEY,
                ban_limit INTEGER NOT NULL DEFAULT 25,
                time_window_hours INTEGER NOT NULL DEFAULT 24
            )
        """)

        # Tezkor qidiruv uchun indeks
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_ban_events_time 
            ON ban_events(chat_id, admin_id, timestamp)
        """)

        await db.commit()


async def get_chat_settings(chat_id: int):
    """Guruh uchun sozlamalarni olish"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT ban_limit, time_window_hours FROM chat_settings WHERE chat_id = ?",
            (chat_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return {"ban_limit": row[0], "time_window_hours": row[1]}
            return {"ban_limit": BAN_LIMIT, "time_window_hours": TIME_WINDOW_HOURS}


async def set_chat_ban_limit(chat_id: int, limit: int):
    """Guruh uchun ban limitini o'zgartirish"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO chat_settings (chat_id, ban_limit)
            VALUES (?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET ban_limit = excluded.ban_limit
        """, (chat_id, limit))
        await db.commit()


async def add_promoted_admin(chat_id: int, user_id: int, username: str, first_name: str, promoted_by: int):
    """Bot orqali tayinlangan adminni bazaga yozish"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO promoted_admins (chat_id, user_id, username, first_name, promoted_by)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(chat_id, user_id) DO UPDATE SET
                username = excluded.username,
                first_name = excluded.first_name,
                promoted_by = excluded.promoted_by
        """, (chat_id, user_id, username, first_name, promoted_by))
        await db.commit()


async def remove_promoted_admin(chat_id: int, user_id: int):
    """Adminlikdan olinganda bazadan o'chirish"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM promoted_admins WHERE chat_id = ? AND user_id = ?",
            (chat_id, user_id)
        )
        await db.commit()


async def is_promoted_by_bot(chat_id: int, user_id: int) -> bool:
    """Foydalanuvchi bot orqali admin qilinganligini tekshirish"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT 1 FROM promoted_admins WHERE chat_id = ? AND user_id = ?",
            (chat_id, user_id)
        ) as cursor:
            row = await cursor.fetchone()
            return row is not None


async def get_promoted_admins(chat_id: int):
    """Guruhdagi bot tayinlagan barcha adminlar ro'yxati"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM promoted_admins WHERE chat_id = ? ORDER BY created_at DESC",
            (chat_id,)
        ) as cursor:
            return await cursor.fetchall()


async def record_ban(chat_id: int, admin_id: int, banned_user_id: int, window_hours: int) -> int:
    """Ban qayd etish va berilgan soat ichidagi banlar sonini qaytarish"""
    now = time.time()
    cutoff_time = now - (window_hours * 3600)

    async with aiosqlite.connect(DB_PATH) as db:
        # Yangi banni yozish
        await db.execute(
            "INSERT INTO ban_events (chat_id, admin_id, banned_user_id, timestamp) VALUES (?, ?, ?, ?)",
            (chat_id, admin_id, banned_user_id, now)
        )
        await db.commit()

        # So'nggi window_hours ichidagi umumiy banlar sonini hisoblash
        async with db.execute(
            "SELECT COUNT(*) FROM ban_events WHERE chat_id = ? AND admin_id = ? AND timestamp >= ?",
            (chat_id, admin_id, cutoff_time)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 1


async def get_ban_count(chat_id: int, admin_id: int, window_hours: int) -> int:
    """Adminning so'nggi N soat ichida bergan banlari sonini olish"""
    cutoff_time = time.time() - (window_hours * 3600)
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM ban_events WHERE chat_id = ? AND admin_id = ? AND timestamp >= ?",
            (chat_id, admin_id, cutoff_time)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0


async def get_all_admins_ban_stats(chat_id: int, window_hours: int):
    """Barcha adminlarning so'nggi N soatdagi banlar statistikasi"""
    cutoff_time = time.time() - (window_hours * 3600)
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT 
                p.user_id,
                p.username,
                p.first_name,
                COUNT(b.id) as ban_count
            FROM promoted_admins p
            LEFT JOIN ban_events b 
                ON p.chat_id = b.chat_id 
                AND p.user_id = b.admin_id 
                AND b.timestamp >= ?
            WHERE p.chat_id = ?
            GROUP BY p.user_id
            ORDER BY ban_count DESC
        """, (cutoff_time, chat_id)) as cursor:
            return await cursor.fetchall()


async def reset_admin_bans(chat_id: int, admin_id: int):
    """Adminning banlar hisobini tozalash (masalan, noto'g'ri bo'lsa)"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM ban_events WHERE chat_id = ? AND admin_id = ?",
            (chat_id, admin_id)
        )
        await db.commit()
