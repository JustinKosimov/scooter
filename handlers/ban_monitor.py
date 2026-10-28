import logging
from aiogram import Router, Bot
from aiogram.types import ChatMemberUpdated
from aiogram.filters import ChatMemberUpdatedFilter, KICKED
from aiogram.enums import ChatMemberStatus
from aiogram.exceptions import TelegramBadRequest

from config import OWNER_IDS
from database import (
    record_ban,
    get_chat_settings,
    remove_promoted_admin,
    is_promoted_by_bot
)

router = Router()
logger = logging.getLogger(__name__)


@router.chat_member(ChatMemberUpdatedFilter(member_status_changed=KICKED))
async def on_user_banned(event: ChatMemberUpdated, bot: Bot):
    """
    Foydalanuvchi guruhdan ban qilinganda (KICKED holatiga o'tganda) ishlaydi.
    """
    # Faqat guruh va superguruhlarda ishlaydi
    if event.chat.type not in ["group", "supergroup"]:
        return

    admin_user = event.from_user
    banned_user = event.new_chat_member.user

    # Agar o'zini o'zi tark etgan bo'lsa (bunday holatda ham kicked bo'lmaydi, lekin xavfsizlik uchun tekshirish)
    if not admin_user or admin_user.id == banned_user.id:
        return

    # Agar botning o'zi ban bergan bo'lsa, e'tibor bermaymiz
    bot_info = await bot.get_me()
    if admin_user.id == bot_info.id:
        return

    # Guruh egasi (Creator) yoki bot superadminlari uchun cheklov yo'q
    if admin_user.id in OWNER_IDS:
        return

    try:
        member = await bot.get_chat_member(event.chat.id, admin_user.id)
        if member.status == ChatMemberStatus.CREATOR:
            return  # Guruh egasiga tegmaymiz
    except Exception:
        pass

    # Sozlamalarni olish (limit va vaqt oynasi)
    settings = await get_chat_settings(event.chat.id)
    ban_limit = settings["ban_limit"]
    window_hours = settings["time_window_hours"]

    # Banlar sonini hisoblash va bazaga saqlash
    current_bans = await record_ban(
        chat_id=event.chat.id,
        admin_id=admin_user.id,
        banned_user_id=banned_user.id,
        window_hours=window_hours
    )

    logger.info(
        f"Admin {admin_user.id} ({admin_user.full_name}) chat {event.chat.id} da ban berdi. "
        f"So'nggi {window_hours} soatdagi soni: {current_bans}/{ban_limit}"
    )

    # 1. LIMITDAN OSHIB KETGANDA (25 tadan ko'p bo'lsa)
    if current_bans > ban_limit:
        try:
            # Barcha adminlik huquqlarini (shu jumladan BAN berish huquqini) butunlay olib tashlaymiz
            await bot.promote_chat_member(
                chat_id=event.chat.id,
                user_id=admin_user.id,
                can_manage_chat=False,
                can_delete_messages=False,
                can_manage_video_chats=False,
                can_restrict_members=False,
                can_promote_members=False,
                can_change_info=False,
                can_invite_users=False,
                can_pin_messages=False
            )

            # Bazadan o'chiramiz
            await remove_promoted_admin(event.chat.id, admin_user.id)

            # Guruhga shoshilinch ogohlantirish yuborish
            alert_text = (
                f"🚨 <b>XAVFSIZLIK TIZIMI ISHLADI!</b> 🚨\n\n"
                f"👤 <b>Admin:</b> {admin_user.mention_html()} (ID: <code>{admin_user.id}</code>)\n"
                f"⚠️ <b>Sabab:</b> Belgilangan <b>{ban_limit} ta</b> BAN limitidan oshib ketdi "
                f"(so'nggi {window_hours} soat ichida <b>{current_bans} ta</b> odamga BAN berdi)!\n\n"
                f"🛡 <b>Chora:</b> Foydalanuvchining <b>BAN berish huquqi va barcha adminlik vakolatlari bekor qilindi</b>!"
            )
            await bot.send_message(
                chat_id=event.chat.id,
                text=alert_text,
                parse_mode="HTML"
            )

        except TelegramBadRequest as e:
            # Agar bot bu adminni tushira olmasa (masalan, botdan emas, guruh egasi tomonidan qo'lda admin qilingan bo'lsa)
            logger.error(f"Adminni tushirib bo'lmadi: {e}")
            warning_text = (
                f"⚠️ <b>DIQQAT! XAVFLI HARAKAT!</b> ⚠️\n\n"
                f"Admin {admin_user.mention_html()} <b>{ban_limit} tadan ko'p</b> odamni ban qildi ({current_bans} ta)!\n\n"
                f"❗ <b>Bot ushbu adminni avtomatik tushira olmadi</b>, chunki bu admin bot orqali emas, "
                f"guruh egasi tomonidan qo'lda tayinlangan.\n"
                f"<i>Guruh egasi zudlik bilan ushbu adminni adminlikdan olishi tavsiya etiladi!</i>"
            )
            await bot.send_message(
                chat_id=event.chat.id,
                text=warning_text,
                parse_mode="HTML"
            )

    # 2. LIMITGA YAQINLASHGANDA OGOHLANTIRISH (Masalan, 25 bo'lsa, 20-banda ogohlantirish)
    elif current_bans == ban_limit - 5 and ban_limit > 5:
        warn_text = (
            f"⚠️ <b>Ogohlantirish!</b>\n\n"
            f"Admin {admin_user.mention_html()} so'nggi {window_hours} soat ichida <b>{current_bans} ta</b> foydalanuvchiga BAN berdi.\n"
            f"Maksimal limit: <b>{ban_limit} ta</b>.\n"
            f"<i>Yana {ban_limit - current_bans} ta bandan so'ng adminlik huquqi avtomatik bekor qilinadi!</i>"
        )
        await bot.send_message(
            chat_id=event.chat.id,
            text=warn_text,
            parse_mode="HTML"
        )
