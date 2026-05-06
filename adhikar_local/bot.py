"""
Adhikar-Aina | bot.py

Replaces: telegram_bot/nb6.py
# DATABRICKS REMOVED: SparkSession, spark.table(), Databricks catalog replaced with local pipeline
# DATABRICKS REMOVED: MERGE INTO eligibility_results → in-memory match.match_citizen()

Telegram bot:
- Accepts 12-digit Aadhaar → validates → matches schemes → sends PDF certificate
- Multi-language support via Sarvam AI (Hindi, Bengali, Tamil, Telugu, Marathi, …)
- /language  — pick preferred language
- /start     — welcome + language prompt
- /help      — usage guide
"""

from __future__ import annotations

import asyncio
import logging
import sys
import tempfile
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent))

from telegram import (
    InlineKeyboardButton, InlineKeyboardMarkup,
    Update,
)
from telegram.ext import (
    Application, CallbackQueryHandler, CommandHandler,
    ContextTypes, MessageHandler, filters,
)
from telegram.constants import ParseMode

from config import TELEGRAM_TOKEN

logging.basicConfig(
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ── Language config ───────────────────────────────────────────────────────────

SUPPORTED_LANGS = {
    "en": "English",
    "hi": "हिंदी (Hindi)",
    "bn": "বাংলা (Bengali)",
    "mr": "मराठी (Marathi)",
    "ta": "தமிழ் (Tamil)",
    "te": "తెలుగు (Telugu)",
    "gu": "ગુજરાતી (Gujarati)",
    "kn": "ಕನ್ನಡ (Kannada)",
    "ml": "മലയാളം (Malayalam)",
    "pa": "ਪੰਜਾਬੀ (Punjabi)",
}

# In-memory per-chat language preference (resets on bot restart)
_USER_LANG: dict[int, str] = {}   # chat_id → lang code


def _get_lang(chat_id: int) -> str:
    return _USER_LANG.get(chat_id, "en")


def _translate(text: str, chat_id: int) -> str:
    lang = _get_lang(chat_id)
    if lang == "en":
        return text
    try:
        from sarvam import translate
        return translate(text, target_lang=lang, source_lang="en")
    except Exception:
        return text


def _lang_keyboard() -> InlineKeyboardMarkup:
    buttons = []
    row = []
    for code, label in SUPPORTED_LANGS.items():
        row.append(InlineKeyboardButton(label, callback_data=f"lang:{code}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    return InlineKeyboardMarkup(buttons)


# ── Message templates (English — translated before sending) ───────────────────

_WELCOME_EN = (
    "Namaste! Welcome to ADHIKAR\n"
    "Aapka Adhikar, Aapki Pehchaan\n\n"
    "I help you discover government welfare schemes you are legally entitled to, "
    "and generate an Adhikar Certificate you can show to any official.\n\n"
    "How to use:\n"
    "1. Send your 12-digit Aadhaar number\n"
    "2. Receive your certificate as a PDF\n\n"
    "Send /language to choose your preferred language first."
)

_HELP_EN = (
    "ADHIKAR Bot — Help\n\n"
    "Commands:\n"
    "/start — Start the bot\n"
    "/language — Choose your language\n"
    "/demo — Show sample Aadhaar numbers to try\n"
    "/myid — Show your Telegram chat ID\n"
    "/link <citizen_id> — Link your account to a citizen profile\n"
    "/help — Show this message\n\n"
    "Usage:\n"
    "Send your 12-digit Aadhaar number (digits only, no spaces).\n"
    "The PDF certificate lists schemes you qualify for, your legal rights, "
    "and the exact words to use when claiming benefits.\n\n"
    "Emergency Helplines:\n"
    "National: 1800-11-0001 (Free)\n"
    "Legal Aid: 1800-233-4415 (Free)"
)

_LANG_PROMPT_EN = "Please choose your preferred language / अपनी भाषा चुनें:"

_INVALID_AADHAAR_EN = (
    "Please send a valid 12-digit Aadhaar number (digits only).\n"
    "Example: 999999999999"
)

_NOT_FOUND_EN = (
    "Aadhaar not found in our database.\n\n"
    "Please register at your nearest Jan Seva Kendra (CSC).\n"
    "Apne najdiki Jan Seva Kendra par panjikaran karein."
)

_NO_SCHEMES_EN = (
    "Namaste {name}!\n\n"
    "No government schemes matched your current profile.\n\n"
    "This may change if your income or circumstances change. "
    "Visit your local District Welfare Office for more assistance."
)

_PROCESSING_EN = "Processing Aadhaar {masked}... please wait."

_DEMO_EN = (
    "Demo Aadhaar numbers you can test with:\n\n"
    "{entries}\n\n"
    "Send any of these 12-digit numbers to see their eligible schemes."
)

_MYID_EN = "Your Telegram Chat ID is: {chat_id}\n\nShare this with the admin to link your account to a citizen profile."

_LINK_USAGE_EN = (
    "Usage: /link <citizen_id>\n"
    "Example: /link CIT-00002\n\n"
    "This links your Telegram account to that citizen's profile so you receive policy notifications."
)

_LINK_NOT_FOUND_EN = "Citizen ID '{citizen_id}' not found in the database."
_LINK_SUCCESS_EN   = "Linked! Your Telegram is now connected to:\n\nName: {name}\nDistrict: {district}, {state}\nOccupation: {occupation}\n\nYou will receive notifications when new schemes match your profile."


# ── Handlers ──────────────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    msg = _translate(_WELCOME_EN, chat_id)
    await update.message.reply_text(msg)
    await update.message.reply_text(
        _LANG_PROMPT_EN, reply_markup=_lang_keyboard()
    )


async def cmd_language(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        _LANG_PROMPT_EN, reply_markup=_lang_keyboard()
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    await update.message.reply_text(_translate(_HELP_EN, chat_id))


async def callback_lang(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    code = query.data.split(":", 1)[1]
    chat_id = update.effective_chat.id
    _USER_LANG[chat_id] = code
    lang_name = SUPPORTED_LANGS.get(code, code)
    confirm_en = f"Language set to {lang_name}. Now send your 12-digit Aadhaar number."
    msg = _translate(confirm_en, chat_id)
    await query.edit_message_text(msg)


async def cmd_myid(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    msg = _translate(_MYID_EN.format(chat_id=chat_id), chat_id)
    await update.message.reply_text(msg)


async def cmd_link(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id  = update.effective_chat.id
    username = update.effective_user.username if update.effective_user else None

    if not context.args:
        await update.message.reply_text(_translate(_LINK_USAGE_EN, chat_id))
        return

    citizen_id = context.args[0].strip().upper()

    try:
        import sqlite3
        from config import DB_PATH

        with sqlite3.connect(str(DB_PATH)) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM citizens WHERE citizen_id=? OR aadhar=? LIMIT 1",
                (citizen_id, citizen_id)
            ).fetchone()

        if not row:
            await update.message.reply_text(
                _translate(_LINK_NOT_FOUND_EN.format(citizen_id=citizen_id), chat_id)
            )
            return

        citizen = dict(row)
        with sqlite3.connect(str(DB_PATH)) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO telegram_user_mapping
                (citizen_id, telegram_chat_id, telegram_username, updated_at)
                VALUES (?,?,?,datetime('now'))
            """, (citizen["citizen_id"], str(chat_id), username or ""))
            conn.commit()

        msg = _translate(
            _LINK_SUCCESS_EN.format(
                name=citizen["name"],
                district=citizen["district"],
                state=citizen["state"],
                occupation=citizen["occupation"],
            ),
            chat_id,
        )
        await update.message.reply_text(msg)
        logger.info("Linked chat_id=%s to citizen_id=%s (%s)",
                    chat_id, citizen["citizen_id"], citizen["name"])

    except Exception as exc:
        logger.error("Link error: %s", exc, exc_info=True)
        await update.message.reply_text(
            _translate(f"Error linking account: {exc}", chat_id)
        )


async def cmd_demo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    try:
        from match import get_citizen
        import sqlite3
        from config import DB_PATH

        with sqlite3.connect(str(DB_PATH)) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT aadhar, name, district, state, occupation, annual_income, caste_category
                FROM citizens
                WHERE citizen_id IN ('CIT-00001','CIT-00002','CIT-00003','CIT-00004','CIT-00005')
                   OR aadhar = '999999999999'
                LIMIT 6
            """).fetchall()

        if not rows:
            await update.message.reply_text(_translate(
                "No demo citizens found. Ask the admin to run setup.", chat_id))
            return

        lines = []
        for r in rows:
            lines.append(
                f"  {r['aadhar']}  —  {r['name']}, {r['district']}\n"
                f"     {r['occupation'].title()}, Income: Rs {int(r['annual_income']):,}, {r['caste_category']}"
            )
        entries = "\n\n".join(lines)
        msg = _translate(_DEMO_EN.format(entries=entries), chat_id)
        await update.message.reply_text(msg)
    except Exception as exc:
        logger.error("Demo command error: %s", exc, exc_info=True)
        await update.message.reply_text(
            _translate("Could not load demo citizens. Try sending any 12-digit Aadhaar.", chat_id)
        )


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    raw  = (update.message.text or "").strip()
    text = raw.replace(" ", "").replace("-", "")

    if not text.isdigit() or len(text) != 12:
        await update.message.reply_text(_translate(_INVALID_AADHAAR_EN, chat_id))
        return

    masked = text[:4] + "XXXX" + text[-4:]
    await update.message.reply_text(
        _translate(_PROCESSING_EN.format(masked=masked), chat_id)
    )

    try:
        from match import match_citizen, get_citizen
        from certificate import generate_pdf

        citizen = get_citizen(text)
        if citizen is None:
            await update.message.reply_text(_translate(_NOT_FOUND_EN, chat_id))
            return

        schemes = match_citizen(text)
        if not schemes:
            msg = _translate(_NO_SCHEMES_EN.format(name=citizen["name"]), chat_id)
            await update.message.reply_text(msg)
            return

        scheme_lines = "\n".join(
            f"  {i}. {s['scheme_name']}" for i, s in enumerate(schemes, 1)
        )
        summary_en = (
            f"Namaste {citizen['name']}!\n\n"
            f"You are eligible for {len(schemes)} government scheme(s):\n"
            f"{scheme_lines}\n\n"
            "Your certificate (with legal rights and claim script) is below.\n"
            "Agar koi inkaar kare — yeh certificate legal proof hai."
        )
        summary = _translate(summary_en, chat_id)

        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = generate_pdf(
                citizen, schemes,
                output_path=Path(tmpdir) / "adhikar_certificate.pdf"
            )
            await update.message.reply_text(summary)
            with open(pdf_path, "rb") as pdf:
                await update.message.reply_document(
                    document=pdf,
                    filename=f"Adhikar_Certificate_{text[-4:]}.pdf",
                    caption="ADHIKAR Certificate — Your Rights Document",
                )

    except Exception as exc:
        logger.error("Error for Aadhaar %s: %s", text, exc, exc_info=True)
        err_msg = _translate(
            f"An error occurred. Please try again or contact support.\nError: {exc}",
            chat_id,
        )
        await update.message.reply_text(err_msg)


# ── Entry point ───────────────────────────────────────────────────────────────

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Exception while handling update %s", update, exc_info=context.error)
    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(
                f"An internal error occurred: {context.error}"
            )
        except Exception:
            pass


def main() -> None:
    token = TELEGRAM_TOKEN
    if not token:
        raise ValueError(
            "TELEGRAM_TOKEN is not set.\n"
            "Set it as an environment variable:  export TELEGRAM_TOKEN='your-token'\n"
            "Or edit config.py and set TELEGRAM_TOKEN = 'your-token'"
        )

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start",    cmd_start))
    app.add_handler(CommandHandler("language", cmd_language))
    app.add_handler(CommandHandler("help",     cmd_help))
    app.add_handler(CommandHandler("demo",     cmd_demo))
    app.add_handler(CommandHandler("myid",     cmd_myid))
    app.add_handler(CommandHandler("link",     cmd_link))
    app.add_handler(CallbackQueryHandler(callback_lang, pattern=r"^lang:"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_error_handler(error_handler)

    logger.info("ADHIKAR Bot started. Ctrl+C to stop.")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()
