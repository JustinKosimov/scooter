from aiogram import Router, Bot, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.exceptions import TelegramBadRequest
from config import OWNER_IDS
from database import (
    add_promoted_admin,
    remove_promoted_admin,
    get_chat_settings,
    set_chat_ban_limit,
    get_all_admins_ban_stats,
    reset_admin_bans
)

router = Router()


async def is_authorized(message: Message, bot: Bot) -> bool:
    """Foydalanuvchi guruh egasi yoki bot super-admini ekanligini tekshirish"""
    if message.from_user.id in OWNER_IDS:
        return True

    if message.chat.type in ["group", "supergroup"]:
        try:
            member = await bot.get_chat_member(message.chat.id, message.from_user.id)
            if member.status == "creator":
                return True
        except Exception:
            pass

    return False


@router.message(Command("start", "help"))
async def cmd_help(message: Message):
    text = (
        "🛡 <b>Mafia Guruhi Xavfsizlik Boti</b>\n\n"
        f"🆔 <b>Sizning Telegram ID:</b> <code>{message.from_user.id}</code>\n\n"
        "Ushbu bot adminlarning o'zboshimchalik bilan odamlarni BAN qilishini oldini oladi.\n"
        "Admin belgilangan limitdan (standart: 25 ta) ko'p odamga BAN bersa, "
        "bot avtomatik tarzda uning <b>BAN huquqini va adminligini olib tashlaydi!</b>\n\n"
        "<b>⚠️ Muhim qoida:</b>\n"
        "Telegram qoidalariga ko'ra, bot faqat <b>o'zi tayinlagan adminlarni</b> tushira oladi. "
        "Shuning uchun adminlarni Telegram'dan emas, ushbu bot orqali tayinlang!\n\n"
        "<b>Buyruqlar (Faqat guruh egasi uchun):</b>\n"
        "• <code>/promote [unvon]</code> — Xabarga javob (reply) berib yozilsa, odamni admin qiladi.\n"
        "• <code>/demote</code> — Xabarga javob berib yozilsa, adminlikdan tushiradi.\n"
        "• <code>/stats</code> — Adminlarning so'nggi 24 soatdagi banlar statistikasini ko'rsatadi.\n"
        "• <code>/setlimit [son]</code> — Ban limitini o'zgartirish (masalan: <code>/setlimit 25</code>)\n"
        "• <code>/reset [user_id]</code> — Adminning banlar hisobini 0 ga tushirish."
    )
    await message.reply(text, parse_mode="HTML")


@router.message(Command("promote", "addadmin"))
async def cmd_promote(message: Message, bot: Bot):
    """Admin tayinlash"""
    if message.chat.type not in ["group", "supergroup"]:
        return await message.reply("Bu buyruq faqat guruhlarda ishlaydi!")

    if not await is_authorized(message, bot):
        return await message.reply("❌ Bu buyruqni faqat guruh egasi ishlata oladi!")

    target_user = None
    custom_title = "Mafia Admin"

    # Argumentlarni tekshirish
    args = message.text.split(maxsplit=2)
    if len(args) > 1:
        custom_title = args[1][:16]  # Max 16 ta belgi

    if message.reply_to_message:
        target_user = message.reply_to_message.from_user
    else:
        return await message.reply(
            "⚠️ Admin qilmoqchi bo'lgan foydalanuvchining xabariga javob (reply) qilib "
            "<code>/promote [Unvon]</code> deb yozing!",
            parse_mode="HTML"
        )

    if target_user.is_bot:
        return await message.reply("❌ Botlarni admin qilib bo'lmaydi.")

    try:
        # Bot orqali adminlik huquqlarini berish
        await bot.promote_chat_member(
            chat_id=message.chat.id,
            user_id=target_user.id,
            can_manage_chat=True,
            can_delete_messages=True,
            can_manage_video_chats=True,
            can_restrict_members=True,  # BAN va MUTE bera oladi
            can_promote_members=False,  # O'zi boshqa admin qo'sha OLMAYDI
            can_change_info=False,
            can_invite_users=True,
            can_pin_messages=True
        )

        try:
            await bot.set_chat_administrator_custom_title(
                chat_id=message.chat.id,
                user_id=target_user.id,
                custom_title=custom_title
            )
        except Exception:
            pass  # Ba'zi guruhlarda maxsus unvon qo'yish cheklangan bo'lishi mumkin

        # Bazaga saqlab qo'yish
        await add_promoted_admin(
            chat_id=message.chat.id,
            user_id=target_user.id,
            username=target_user.username or "",
            first_name=target_user.first_name,
            promoted_by=message.from_user.id
        )

        settings = await get_chat_settings(message.chat.id)
        limit = settings["ban_limit"]

        await message.reply(
            f"✅ {target_user.mention_html()} muvaffaqiyatli admin etib tayinlandi!\n\n"
            f"🏷 <b>Unvoni:</b> {custom_title}\n"
            f"🛡 <b>BAN limiti:</b> 24 soatda {limit} ta.\n"
            f"<i>Eslatma: Agar admin 24 soat ichida {limit} tadan ortiq odamga BAN bersa, "
            f"bot uni avtomatik adminlikdan tushiradi!</i>",
            parse_mode="HTML"
        )

    except TelegramBadRequest as e:
        error_msg = str(e).lower()
        if "rights_not_enough" in error_msg or "not enough rights" in error_msg:
            await message.reply(
                "❌ <b>Botda ruxsat yetarli emas!</b>\n\n"
                "Iltimos, guruh sozlamalariga kirib botga <b>'Yangi adminlar qo'shish' (Add new admins)</b> "
                "huquqini bering.",
                parse_mode="HTML"
            )
        else:
            await message.reply(f"❌ Xatolik yuz berdi: {e}")


@router.message(Command("demote", "deladmin"))
async def cmd_demote(message: Message, bot: Bot):
    """Adminlikdan tushirish"""
    if message.chat.type not in ["group", "supergroup"]:
        return await message.reply("Bu buyruq faqat guruhlarda ishlaydi!")

    if not await is_authorized(message, bot):
        return await message.reply("❌ Bu buyruqni faqat guruh egasi ishlata oladi!")

    target_user = None
    if message.reply_to_message:
        target_user = message.reply_to_message.from_user
    else:
        return await message.reply(
            "⚠️ Adminlikdan olmoqchi bo'lgan odamning xabariga reply qilib <code>/demote</code> deb yozing!",
            parse_mode="HTML"
        )

    try:
        # Barcha admin huquqlarini o'chirish
        await bot.promote_chat_member(
            chat_id=message.chat.id,
            user_id=target_user.id,
            can_manage_chat=False,
            can_delete_messages=False,
            can_manage_video_chats=False,
            can_restrict_members=False,
            can_promote_members=False,
            can_change_info=False,
            can_invite_users=False,
            can_pin_messages=False
        )

        await remove_promoted_admin(message.chat.id, target_user.id)

        await message.reply(
            f"✅ {target_user.mention_html()} adminlikdan muvaffaqiyatli tushirildi.",
            parse_mode="HTML"
        )
    except TelegramBadRequest as e:
        await message.reply(
            f"❌ Adminlikdan tushirib bo'lmadi.\n"
            f"<i>Ehtimol, bu foydalanuvchi bot orqali emas, Telegram'dan to'g'ridan-to'g'ri admin qilingan bo'lishi mumkin.</i>\n\n"
            f"Batafsil xato: {e}",
            parse_mode="HTML"
        )


@router.message(Command("stats"))
async def cmd_stats(message: Message, bot: Bot):
    """Adminlarning banlar statistikasini ko'rish"""
    if message.chat.type not in ["group", "supergroup"]:
        return await message.reply("Bu buyruq faqat guruhlarda ishlaydi!")

    settings = await get_chat_settings(message.chat.id)
    limit = settings["ban_limit"]
    hours = settings["time_window_hours"]

    stats = await get_all_admins_ban_stats(message.chat.id, hours)

    if not stats:
        return await message.reply("📊 Hozircha bot orqali tayinlangan adminlar yo'q.")

    text = f"📊 <b>Adminlarning so'nggi {hours} soatdagi BAN statistikasi:</b>\n"
    text += f"<i>(Ruxsat etilgan limit: {limit} ta)</i>\n\n"

    for idx, admin in enumerate(stats, 1):
        name = admin["first_name"]
        uname = f"(@{admin['username']})" if admin["username"] else ""
        count = admin["ban_count"]

        # Limitga yaqinlashganda ogohlantiruvchi belgi
        status_icon = "🟢"
        if count >= limit:
            status_icon = "🔴 (Limit buzilgan)"
        elif count >= limit - 5:
            status_icon = "🟡 (Xavfli zona)"

        text += f"{idx}. {name} {uname}: <b>{count}/{limit}</b> ta ban {status_icon}\n"

    await message.reply(text, parse_mode="HTML")


@router.message(Command("setlimit"))
async def cmd_setlimit(message: Message, bot: Bot):
    """BAN limitini o'zgartirish (masalan: /setlimit 25)"""
    if not await is_authorized(message, bot):
        return await message.reply("❌ Bu buyruqni faqat guruh egasi ishlata oladi!")

    args = message.text.split()
    if len(args) < 2 or not args[1].isdigit():
        return await message.reply(
            "⚠️ Noto'g'ri format! Masalan: <code>/setlimit 25</code>",
            parse_mode="HTML"
        )

    new_limit = int(args[1])
    if new_limit < 1 or new_limit > 500:
        return await message.reply("❌ Limit 1 dan 500 gacha bo'lishi kerak!")

    await set_chat_ban_limit(message.chat.id, new_limit)
    await message.reply(
        f"✅ Guruh uchun maksimal BAN limiti <b>{new_limit}</b> taga o'zgartirildi!",
        parse_mode="HTML"
    )


@router.message(Command("reset"))
async def cmd_reset(message: Message, bot: Bot):
    """Adminning banlar hisobini qayta nollash"""
    if not await is_authorized(message, bot):
        return await message.reply("❌ Bu buyruqni faqat guruh egasi ishlata oladi!")

    user_id = None
    if message.reply_to_message:
        user_id = message.reply_to_message.from_user.id
    else:
        args = message.text.split()
        if len(args) > 1 and args[1].isdigit():
            user_id = int(args[1])

    if not user_id:
        return await message.reply(
            "⚠️ Xabarga reply qiling yoki ID kiriting: <code>/reset 123456789</code>",
            parse_mode="HTML"
        )

    await reset_admin_bans(message.chat.id, user_id)
    await message.reply(f"✅ Foydalanuvchi ({user_id}) ning BAN hisobi nolga tushirildi.")
