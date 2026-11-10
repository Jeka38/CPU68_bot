import asyncio
import html
import io
import logging
import os
import re
import sqlite3
import sys
import time
import traceback
from functools import lru_cache
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.filters import BaseFilter, Command
from aiogram.types import BufferedInputFile, ErrorEvent, Message
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont


# -------------------- CONFIG --------------------

# Load only the .env next to bot.py; do not search parent directories or CWD.
# This must happen before i18n is imported so LANGUAGE from .env is honoured.
load_dotenv(Path(__file__).with_name(".env"))

from i18n import t  # noqa: E402
from ranks import BEYOND_RANK, RANKS  # noqa: E402

TOKEN = os.getenv("BOT_TOKEN", "").strip()

# SQLite DB and WAL files contain user data: keep them owner-only where supported.
os.umask(0o077)


def env_seconds(name: str, default: float) -> float:
    try:
        return max(0.0, float(os.getenv(name, str(default))))
    except ValueError:
        return default


def parse_ids(value: str) -> set[int]:
    return {
        int(part)
        for part in re.split(r"[,\s]+", value.strip())
        if part.isdigit()
    }


def parse_chat_ids(value: str) -> set[int]:
    """Parse negative Telegram chat IDs (groups/supergroups)."""
    result = set()
    for part in re.split(r"[,\s]+", value.strip()):
        try:
            chat_id = int(part)
        except ValueError:
            continue
        if chat_id < 0:
            result.add(chat_id)
    return result


# Telegram tokens look like "123456789:AA...". Also redact any token-shaped
# string so proxy/HTML error pages that echo the request URL cannot leak it.
_BOT_TOKEN_RE = re.compile(r"\d{6,12}:[A-Za-z0-9_-]{30,}")


def redact_secrets(text: str) -> str:
    if TOKEN:
        text = text.replace(TOKEN, "<bot-token>")
    return _BOT_TOKEN_RE.sub("<bot-token>", text)


class _RedactingFormatter(logging.Formatter):
    """Strip bot tokens from log messages and tracebacks."""

    def format(self, record: logging.LogRecord) -> str:
        return redact_secrets(super().format(record))


# DB_PATH defaults to users.db next to bot.py. In Docker it is set to
# /data/users.db, which is a bind mount so the database lives outside the image.
_db_env = os.getenv("DB_PATH", "").strip()
DB_PATH = Path(_db_env) if _db_env else Path(__file__).with_name("users.db")
if not DB_PATH.is_absolute():
    DB_PATH = Path(__file__).resolve().parent / DB_PATH
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

MESSAGES_PER_RANK = 100
# Hard cap for message counters. Prevents int overflow in SQLite and absurd values.
MAX_MESSAGES = 10_000_000
# Anti-spam: minimum seconds between counted messages / public commands per user.
MESSAGE_COOLDOWN_SECONDS = env_seconds("MESSAGE_COOLDOWN_SECONDS", 2.0)
COMMAND_COOLDOWN_SECONDS = env_seconds("COMMAND_COOLDOWN_SECONDS", 3.0)

# Telegram user IDs allowed to use the /a* admin commands.
ADMIN_IDS = parse_ids(os.getenv("ADMIN_IDS", ""))
# Optional bootstrap for the group whitelist (only used when the table is empty).
ALLOWED_CHAT_IDS_ENV = parse_chat_ids(os.getenv("ALLOWED_CHAT_IDS", ""))
# Where unhandled errors are sent in private messages (falls back to ADMIN_IDS).
ERROR_REPORT_IDS = parse_ids(os.getenv("ERROR_REPORT_IDS", "")) or ADMIN_IDS
ERROR_NOTIFY_COOLDOWN_SECONDS = env_seconds(
    "ERROR_NOTIFY_COOLDOWN_SECONDS", 300.0
)

logging.basicConfig(
    level=logging.INFO,
    handlers=[logging.StreamHandler()],
)
for _root_handler in logging.getLogger().handlers:
    _root_handler.setFormatter(
        _RedactingFormatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    )
logger = logging.getLogger("cpu_evolution")

# Rank 1 is Intel 286 (0-99 messages), rank 2 is Intel 386 (100-199), etc.
# The CPU names live in ranks.py; RANK_STYLES below must stay in sync with it.

# One visual theme per rank, in the same order as RANKS:
# (accent RGB, chip RGB, chip label, CPU family used by draw_cpu()).
RANK_STYLES = [
    ((196, 154, 82), (86, 70, 43), "286", "legacy"),
    ((184, 140, 92), (78, 62, 52), "386", "legacy"),
    ((210, 120, 70), (90, 58, 45), "486", "legacy"),
    ((90, 190, 220), (38, 84, 102), "PENTIUM", "classic"),
    ((80, 170, 235), (34, 78, 118), "PII", "classic"),
    ((95, 150, 245), (38, 66, 124), "PIII", "classic"),
    ((120, 125, 250), (53, 52, 130), "P4", "classic"),
    ((80, 200, 190), (33, 92, 92), "C2D", "core"),
    ((70, 210, 160), (30, 97, 74), "i3", "core"),
    ((90, 205, 120), (36, 95, 58), "i5", "core"),
    ((120, 200, 90), (48, 92, 42), "i7", "core"),
    ((170, 200, 70), (69, 86, 33), "i9", "core"),
    ((240, 130, 90), (112, 58, 43), "R3", "ryzen"),
    ((240, 105, 80), (112, 48, 39), "R5", "ryzen"),
    ((245, 85, 80), (116, 41, 42), "R7", "ryzen"),
    ((235, 70, 105), (108, 35, 55), "R9", "ryzen"),
    ((220, 80, 140), (100, 36, 68), "TR", "hedt"),
]

# SECURITY: every SQL query in this file uses ? placeholders.
# Never build SQL with f-strings, .format() or string concatenation.
db = sqlite3.connect(DB_PATH)
db.row_factory = sqlite3.Row
db.execute("PRAGMA journal_mode=WAL")
db.execute("""
CREATE TABLE IF NOT EXISTS users (
    chat_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    display_name TEXT NOT NULL,
    messages INTEGER NOT NULL DEFAULT 0,
    last_counted_at REAL NOT NULL DEFAULT 0,
    PRIMARY KEY (chat_id, user_id)
)
""")
db.execute("""
CREATE TABLE IF NOT EXISTS allowed_chats (
    chat_id INTEGER PRIMARY KEY,
    title TEXT NOT NULL DEFAULT '',
    added_at REAL NOT NULL DEFAULT 0
)
""")
db.execute("""
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
)
""")
user_columns = {row["name"] for row in db.execute("PRAGMA table_info(users)")}
if "last_counted_at" not in user_columns:
    db.execute(
        "ALTER TABLE users ADD COLUMN last_counted_at REAL NOT NULL DEFAULT 0"
    )
# Seed the whitelist from env once, on the first start with an empty table.
# After that the DB is authoritative: deleting all groups must not resurrect them.
seeded = db.execute(
    "SELECT value FROM settings WHERE key='whitelist_seeded'"
).fetchone()
if not seeded:
    if ALLOWED_CHAT_IDS_ENV and not db.execute(
        "SELECT 1 FROM allowed_chats LIMIT 1"
    ).fetchone():
        for allowed_chat_id in sorted(ALLOWED_CHAT_IDS_ENV):
            db.execute(
                """
                INSERT OR IGNORE INTO allowed_chats(chat_id, title, added_at)
                VALUES (?, '', ?)
                """,
                (allowed_chat_id, time.time()),
            )
    db.execute(
        "INSERT INTO settings(key, value) VALUES ('whitelist_seeded', '1')"
    )
db.commit()

dp = Dispatcher()

ALLOWED_CHATS = {
    int(row["chat_id"])
    for row in db.execute("SELECT chat_id FROM allowed_chats")
}


def is_chat_allowed(chat_id: int) -> bool:
    """Only groups explicitly added to the whitelist are served."""
    return chat_id in ALLOWED_CHATS


# -------------------- RANKS / DATABASE --------------------

def rank_index(messages: int) -> int:
    return min(max(messages, 0) // MESSAGES_PER_RANK, len(RANKS) - 1)


def rank_name(messages: int) -> str:
    if messages >= len(RANKS) * MESSAGES_PER_RANK:
        return BEYOND_RANK
    return RANKS[rank_index(messages)]


def next_rank_name(messages: int):
    idx = messages // MESSAGES_PER_RANK
    if idx + 1 >= len(RANKS):
        return None
    return RANKS[idx + 1]


def progress_percent(messages: int) -> int:
    if messages >= len(RANKS) * MESSAGES_PER_RANK:
        return 100
    return (messages % MESSAGES_PER_RANK)


def get_messages(chat_id: int, user_id: int) -> int:
    row = db.execute(
        "SELECT messages FROM users WHERE chat_id=? AND user_id=?",
        (chat_id, user_id),
    ).fetchone()
    return int(row["messages"]) if row else 0


def get_last_counted_at(chat_id: int, user_id: int) -> float:
    row = db.execute(
        "SELECT last_counted_at FROM users WHERE chat_id=? AND user_id=?",
        (chat_id, user_id),
    ).fetchone()
    return float(row["last_counted_at"]) if row else 0.0


def count_user_message(chat_id: int, user_id: int, display_name: str, now: float):
    row = db.execute(
        "SELECT messages FROM users WHERE chat_id=? AND user_id=?",
        (chat_id, user_id),
    ).fetchone()
    if not row:
        # First seen message: register/update nickname, but do not count it.
        db.execute(
            """
            INSERT INTO users(chat_id, user_id, display_name, messages, last_counted_at)
            VALUES (?, ?, ?, 0, ?)
            """,
            (chat_id, user_id, display_name, now),
        )
        db.commit()
        return 0, 0
    old_count = min(int(row["messages"]), MAX_MESSAGES)
    new_count = min(old_count + 1, MAX_MESSAGES)
    db.execute(
        """
        UPDATE users
        SET display_name=?, messages=?, last_counted_at=?
        WHERE chat_id=? AND user_id=?
        """,
        (display_name, new_count, now, chat_id, user_id),
    )
    db.commit()
    return old_count, new_count


def get_user(chat_id: int, user_id: int):
    return db.execute(
        "SELECT * FROM users WHERE chat_id=? AND user_id=?",
        (chat_id, user_id),
    ).fetchone()


def save_user(chat_id: int, user_id: int, display_name: str, messages: int):
    # Defense in depth: values land in a SQLite INTEGER column.
    messages = max(0, min(int(messages), MAX_MESSAGES))
    db.execute(
        """
        INSERT INTO users(chat_id, user_id, display_name, messages)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(chat_id, user_id) DO UPDATE SET
            display_name=excluded.display_name,
            messages=excluded.messages
        """,
        (chat_id, user_id, display_name, messages),
    )
    db.commit()


def get_top(chat_id: int, limit: int = 10):
    return db.execute(
        """
        SELECT user_id, display_name, messages
        FROM users
        WHERE chat_id=?
        ORDER BY messages DESC, display_name COLLATE NOCASE ASC
        LIMIT ?
        """,
        (chat_id, limit),
    ).fetchall()


def get_allowed_chats():
    return db.execute(
        """
        SELECT chat_id, title
        FROM allowed_chats
        ORDER BY added_at ASC, chat_id ASC
        """
    ).fetchall()


def add_allowed_chat(chat_id: int, title: str):
    db.execute(
        """
        INSERT INTO allowed_chats(chat_id, title, added_at)
        VALUES (?, ?, ?)
        ON CONFLICT(chat_id) DO UPDATE SET
            title=CASE
                WHEN excluded.title = '' THEN allowed_chats.title
                ELSE excluded.title
            END
        """,
        (chat_id, title, time.time()),
    )
    db.commit()
    ALLOWED_CHATS.add(chat_id)


def remove_allowed_chat(chat_id: int) -> bool:
    cursor = db.execute(
        "DELETE FROM allowed_chats WHERE chat_id=?", (chat_id,)
    )
    db.commit()
    ALLOWED_CHATS.discard(chat_id)
    return cursor.rowcount > 0


# -------------------- HELP / ANTI-SPAM --------------------

class FloodControl(BaseFilter):
    """Drop repeated public commands from the same user in the same chat."""

    def __init__(self, seconds: float):
        self.seconds = seconds
        self.last_seen: dict[tuple[int, int], float] = {}

    async def __call__(self, message: Message) -> bool:
        user = message.from_user
        if not user:
            return False
        key = (message.chat.id, user.id)
        now = time.monotonic()
        if now - self.last_seen.get(key, 0.0) < self.seconds:
            return False
        self.last_seen[key] = now
        if len(self.last_seen) > 10_000:
            cutoff = now - max(self.seconds, 60.0)
            self.last_seen = {
                k: v for k, v in self.last_seen.items() if v >= cutoff
            }
        return True


COMMAND_THROTTLE = FloodControl(COMMAND_COOLDOWN_SECONDS)
BLOCKED_NOTICE_THROTTLE = FloodControl(COMMAND_COOLDOWN_SECONDS)


class ChatAllowed(BaseFilter):
    """Allow group commands only in whitelisted chats (private chats pass)."""

    async def __call__(self, message: Message) -> bool:
        if message.chat.type not in ("group", "supergroup"):
            return True
        return is_chat_allowed(message.chat.id)


def is_admin(user) -> bool:
    return bool(user) and user.id in ADMIN_IDS


# -------------------- SAFE USER TEXT --------------------

# C0/C1 controls plus zero-width and bidi format characters: they break card
# rendering and can be used to spoof names (RTL override, invisible joiners).
_UNSAFE_CHARS_RE = re.compile(
    "[\x00-\x1f\x7f-\x9f\u200b-\u200f\u202a-\u202e\u2066-\u2069\ufeff]"
)


def clean_text(value: str) -> str:
    """Collapse whitespace and drop control/format characters in user text."""
    text = _UNSAFE_CHARS_RE.sub(" ", value or "")
    return " ".join(text.split())


def esc_name(value: str, limit: int = 48) -> str:
    """Sanitize, truncate and HTML-escape a user/group name."""
    text = clean_text(value) or "—"
    if len(text) > limit:
        text = text[: limit - 1] + "…"
    return html.escape(text)


def tg_len(text: str) -> int:
    """Telegram counts message length in UTF-16 code units."""
    return len(text.encode("utf-16-le")) // 2


def join_lines_fit(lines: list[str], limit: int = 3800) -> str:
    """Join lines and drop the tail instead of exceeding Telegram's 4096 limit."""
    kept: list[str] = []
    total = 0
    for line in lines:
        line_len = tg_len(line) + 1
        if total + line_len > limit:
            kept.append("…")
            break
        kept.append(line)
        total += line_len
    return "\n".join(kept)


# -------------------- ERROR REPORTING --------------------

_error_last_sent: dict[str, float] = {}


def _traceback_text(exc: BaseException) -> str:
    text = "".join(
        traceback.format_exception(type(exc), exc, exc.__traceback__)
    )
    # Root cause is at the end; keep the tail of very long tracebacks.
    if len(text) > 3200:
        text = "..." + text[-3200:]
    return text


def _truncate_html(text: str, limit: int) -> str:
    """Cut escaped text without breaking an HTML entity at the end."""
    if len(text) <= limit:
        return text
    cut = text[: max(0, limit - 3)]
    amp = cut.rfind("&")
    if amp != -1 and ";" not in cut[amp:]:
        cut = cut[:amp]
    return cut + "..."


def _error_message(header: str, exc: BaseException) -> str:
    """Build a Telegram-safe (<4096 chars) HTML message with a traceback."""
    tag_len = len("<pre></pre>")
    budget = max(400, 4000 - len(header) - tag_len - 8)
    body = _truncate_html(html.escape(_traceback_text(exc)), budget)
    return redact_secrets(f"{header}<pre>{body}</pre>")


def _update_context(event: ErrorEvent) -> str:
    update = event.update
    message = getattr(update, "message", None)
    if message is None:
        message = getattr(update, "edited_message", None)

    lines = [f"update: <code>{type(update).__name__}</code>"]
    chat_id = getattr(getattr(message, "chat", None), "id", None)
    user = getattr(message, "from_user", None)
    user_id = getattr(user, "id", None)
    name = getattr(user, "full_name", None)
    text_value = getattr(message, "text", None) or getattr(
        message, "caption", None
    )

    if chat_id is not None:
        lines.append(f"chat_id: <code>{chat_id}</code>")
    if user_id is not None:
        lines.append(f"user_id: <code>{user_id}</code>")
    if name:
        lines.append(f"user: {esc_name(name, 64)}")
    # Only commands are included: regular group messages stay private.
    if text_value and text_value.startswith("/"):
        lines.append(f"command: <code>{html.escape(text_value[:160])}</code>")
    return "\n".join(lines)


def format_error_report(event: ErrorEvent) -> str:
    stamp = time.strftime("%Y-%m-%d %H:%M:%S")
    header = t(
        "error_report_header",
        stamp=stamp,
        context=_update_context(event),
    )
    return _error_message(header, event.exception)


def format_fatal_error(exc: BaseException) -> str:
    stamp = time.strftime("%Y-%m-%d %H:%M:%S")
    header = t("fatal_report_header", stamp=stamp)
    return _error_message(header, exc)


async def notify_admins(bot: Bot, text: str, signature: str | None = None) -> None:
    """Send an error report to every configured admin in private messages."""
    if not ERROR_REPORT_IDS:
        return

    text = redact_secrets(text)

    if signature:
        now = time.monotonic()
        last = _error_last_sent.get(signature)
        if last is not None and now - last < ERROR_NOTIFY_COOLDOWN_SECONDS:
            return
        _error_last_sent[signature] = now
        if len(_error_last_sent) > 500:
            # Hard cap: keep the newest signatures, never grow without bound.
            for key in list(_error_last_sent)[:200]:
                _error_last_sent.pop(key, None)
        elif len(_error_last_sent) > 200:
            cutoff = now - max(ERROR_NOTIFY_COOLDOWN_SECONDS, 60.0)
            for key in [
                k for k, sent_at in _error_last_sent.items() if sent_at < cutoff
            ]:
                _error_last_sent.pop(key, None)

    for admin_id in ERROR_REPORT_IDS:
        try:
            await bot.send_message(admin_id, text, parse_mode="HTML")
        except Exception as exc:
            # An admin may not have started the bot yet; never fail because of it.
            logger.warning(
                t("log_report_send_failed", admin_id=admin_id, error=exc)
            )


PUBLIC_HELP = t("public_help")
ADMIN_USAGE = t("admin_usage")


def admin_help_text(user_id: int) -> str:
    return t("admin_help", usage=ADMIN_USAGE, user_id=user_id)


# -------------------- IMAGE CARD --------------------

def load_font(size: int, bold: bool = False):
    candidates = []
    if os.name == "nt":
        candidates += [
            r"C:\Windows\Fonts\arialbd.ttf" if bold else r"C:\Windows\Fonts\arial.ttf",
            r"C:\Windows\Fonts\segoeuib.ttf" if bold else r"C:\Windows\Fonts\segoeui.ttf",
        ]
    candidates += [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold
        else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            pass
    return ImageFont.load_default()


def _lighten(color, amount: float):
    return tuple(min(255, int(c + (255 - c) * amount)) for c in color)


def _darken(color, amount: float):
    return tuple(max(0, int(c * (1 - amount))) for c in color)


def _wrap_lines(draw, text: str, font, max_width: int) -> list[str]:
    """Greedy word wrap; words wider than the line are split by characters."""
    words: list[str] = []
    for word in text.split():
        while draw.textlength(word, font=font) > max_width and len(word) > 1:
            cut = len(word) - 1
            while cut > 1 and draw.textlength(word[:cut], font=font) > max_width:
                cut -= 1
            words.append(word[:cut])
            word = word[cut:]
        words.append(word)

    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}" if current else word
        if current and draw.textlength(candidate, font=font) > max_width:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


def _ellipsize(draw, line: str, font, max_width: int) -> str:
    """Trim a line to max_width, appending '...' when text was dropped."""
    if draw.textlength(line, font=font) <= max_width:
        return line
    while line and draw.textlength(line + "...", font=font) > max_width:
        line = line[:-1]
    line = line.rstrip()
    return f"{line}..." if line else "..."


def layout_card_name(draw, text: str, max_width: int):
    """Fit a display name into 1-3 lines, shrinking the font only if needed.

    Returns ``(font, lines)``. Names that still overflow at the smallest size
    are capped at three lines and the remainder is replaced with an ellipsis.
    """
    overflow = None
    for size, max_lines in ((27, 1), (25, 2), (22, 3)):
        font = load_font(size, True)
        lines = _wrap_lines(draw, text, font, max_width)
        if len(lines) <= max_lines:
            return font, lines
        overflow = (font, lines)
    font, lines = overflow
    if len(lines) > 3:
        lines = lines[:2] + [" ".join(lines[2:])]
    return font, [_ellipsize(draw, line, font, max_width) for line in lines]


def draw_legacy_cpu(draw, cx, cy, idx, accent, chip, label):
    """Ceramic package with gold pins (286 / 386 / 486)."""
    half = 76 + idx * 5
    pin = _lighten(accent, 0.25)
    for i in range(-3, 4):
        p = i * 26
        draw.line((cx + p, cy - half - 24, cx + p, cy - half), fill=pin, width=6)
        draw.line((cx + p, cy + half, cx + p, cy + half + 24), fill=pin, width=6)
        draw.line((cx - half - 24, cy + p, cx - half, cy + p), fill=pin, width=6)
        draw.line((cx + half, cy + p, cx + half + 24, cy + p), fill=pin, width=6)
    draw.rounded_rectangle(
        (cx - half, cy - half, cx + half, cy + half),
        radius=12, fill=chip, outline=accent, width=3,
    )
    draw.polygon(
        [(cx - half + 10, cy - half), (cx - half + 34, cy - half),
         (cx - half + 10, cy - half + 24)],
        fill=(9, 15, 29, 255),
    )
    inner = half - 24
    draw.rounded_rectangle(
        (cx - inner, cy - inner, cx + inner, cy + inner),
        radius=6, fill=(10, 18, 30, 255),
        outline=_darken(accent, 0.25), width=2,
    )
    draw.text(
        (cx, cy - 8), label,
        font=load_font(30 if len(label) <= 4 else 20, True),
        fill=_lighten(accent, 0.65), anchor="mm",
    )
    draw.text(
        (cx, cy + 34), "CPU", font=load_font(18, True),
        fill=_lighten(accent, 0.35), anchor="mm",
    )


def draw_classic_cpu(draw, cx, cy, idx, accent, chip, label):
    """Pentium-era heat spreader with bevel and notch."""
    w, h = 250, 205
    draw.rounded_rectangle(
        (cx - w // 2 - 14, cy - h // 2 - 14, cx + w // 2 + 14, cy + h // 2 + 14),
        radius=16, fill=_darken(chip, 0.35), outline=_darken(accent, 0.15),
        width=3,
    )
    draw.rounded_rectangle(
        (cx - w // 2, cy - h // 2, cx + w // 2, cy + h // 2),
        radius=12, fill=chip, outline=accent, width=4,
    )
    draw.line(
        (cx - w // 2 + 20, cy - h // 2 + 8, cx + w // 2 - 20, cy - h // 2 + 8),
        fill=_lighten(accent, 0.6), width=2,
    )
    draw.polygon(
        [(cx - w // 2, cy + h // 2 - 30), (cx - w // 2, cy + h // 2),
         (cx - w // 2 + 30, cy + h // 2)],
        fill=(9, 15, 29, 255),
    )
    draw.polygon(
        [(cx - w // 2 + 20, cy - h // 2 + 20),
         (cx - w // 2 + 52, cy - h // 2 + 20),
         (cx - w // 2 + 20, cy - h // 2 + 52)],
        fill=(*accent, 190),
    )
    draw.text(
        (cx, cy - 8), label,
        font=load_font(32 if len(label) <= 4 else 24, True),
        fill=_lighten(accent, 0.65), anchor="mm",
    )
    draw.text(
        (cx, cy + 42), "CPU", font=load_font(18, True),
        fill=_lighten(accent, 0.35), anchor="mm",
    )


def draw_core_cpu(draw, cx, cy, idx, accent, chip, label):
    """Modern square IHS with a core-count bar row."""
    half = 112
    notch = 24
    points = [
        (cx - half + notch, cy - half), (cx + half - notch, cy - half),
        (cx + half, cy - half + notch), (cx + half, cy + half - notch),
        (cx + half - notch, cy + half), (cx - half + notch, cy + half),
        (cx - half, cy + half - notch), (cx - half, cy - half + notch),
    ]
    draw.polygon(points, fill=_darken(chip, 0.15), outline=accent, width=4)
    inner = half - 28
    inner_points = [
        (cx - inner + 16, cy - inner), (cx + inner - 16, cy - inner),
        (cx + inner, cy - inner + 16), (cx + inner, cy + inner - 16),
        (cx + inner - 16, cy + inner), (cx - inner + 16, cy + inner),
        (cx - inner, cy + inner - 16), (cx - inner, cy - inner + 16),
    ]
    draw.polygon(
        inner_points, fill=(10, 18, 30, 255),
        outline=_lighten(accent, 0.25), width=2,
    )
    bars = 2 if idx == 7 else (idx - 6) * 2
    bar_w, gap = 14, 6
    total = bars * bar_w + (bars - 1) * gap
    start = cx - total // 2
    for i in range(bars):
        x = start + i * (bar_w + gap)
        draw.rounded_rectangle(
            (x, cy + 40, x + bar_w, cy + 54), radius=3,
            fill=(*accent, 170),
        )
    draw.text(
        (cx, cy - 18), label, font=load_font(34, True),
        fill=_lighten(accent, 0.65), anchor="mm",
    )
    draw.text(
        (cx, cy + 12), "CPU", font=load_font(17, True),
        fill=_lighten(accent, 0.35), anchor="mm",
    )


def draw_ryzen_cpu(draw, cx, cy, idx, accent, chip, label):
    """Two CCDs and a central I/O die."""
    w, h = 300, 245
    draw.rounded_rectangle(
        (cx - w // 2, cy - h // 2, cx + w // 2, cy + h // 2),
        radius=14, fill=_darken(chip, 0.3), outline=accent, width=4,
    )
    for oy in (-96, 12):
        draw.rounded_rectangle(
            (cx - 132, cy + oy, cx - 28, cy + oy + 84),
            radius=8, fill=chip, outline=_lighten(accent, 0.25), width=2,
        )
    draw.rounded_rectangle(
        (cx - 10, cy - 96, cx + 126, cy + 96),
        radius=10, fill=_darken(chip, 0.12),
        outline=_lighten(accent, 0.4), width=2,
    )
    for oy in range(-80, 81, 20):
        draw.line(
            (cx + 6, cy + oy, cx + 110, cy + oy),
            fill=(*accent, 110), width=1,
        )
    draw.text(
        (cx + 58, cy - 8), label, font=load_font(30, True),
        fill=_lighten(accent, 0.65), anchor="mm",
    )
    draw.text(
        (cx + 58, cy + 30), "CPU", font=load_font(17, True),
        fill=_lighten(accent, 0.35), anchor="mm",
    )


def draw_hedt_cpu(draw, cx, cy, idx, accent, chip, label):
    """Large four-die Threadripper package."""
    w, h = 336, 276
    draw.rounded_rectangle(
        (cx - w // 2, cy - h // 2, cx + w // 2, cy + h // 2),
        radius=16, fill=_darken(chip, 0.32), outline=accent, width=5,
    )
    for dx, dy in ((-150, -120), (-30, -120), (-150, -10), (-30, -10)):
        draw.rounded_rectangle(
            (cx + dx, cy + dy, cx + dx + 105, cy + dy + 90),
            radius=8, fill=chip, outline=_lighten(accent, 0.25), width=2,
        )
    draw.rounded_rectangle(
        (cx + 88, cy - 120, cx + 155, cy + 80),
        radius=10, fill=_darken(chip, 0.1),
        outline=_lighten(accent, 0.4), width=2,
    )
    for oy in range(-100, 61, 20):
        draw.line(
            (cx + 34, cy + oy, cx + 84, cy + oy),
            fill=(*accent, 100), width=1,
        )
    draw.text(
        (cx + 121, cy - 24), label, font=load_font(32, True),
        fill=_lighten(accent, 0.65), anchor="mm",
    )
    draw.text(
        (cx + 121, cy + 18), "CPU", font=load_font(16, True),
        fill=_lighten(accent, 0.35), anchor="mm",
    )


def draw_cpu(draw, cx, cy, idx, accent, chip, label, family):
    if family == "legacy":
        draw_legacy_cpu(draw, cx, cy, idx, accent, chip, label)
    elif family == "classic":
        draw_classic_cpu(draw, cx, cy, idx, accent, chip, label)
    elif family == "core":
        draw_core_cpu(draw, cx, cy, idx, accent, chip, label)
    elif family == "ryzen":
        draw_ryzen_cpu(draw, cx, cy, idx, accent, chip, label)
    else:
        draw_hedt_cpu(draw, cx, cy, idx, accent, chip, label)


@lru_cache(maxsize=32)
def make_rank_card(display_name: str, messages: int) -> bytes:
    """Create a shareable 1200x675 CPU-themed profile/rank card.

    Cached: repeated /profile calls for the same user are free. The gradient is
    rendered at low resolution and scaled up to keep generation cheap.
    """
    W, H = 1200, 675

    idx = rank_index(messages)
    accent, chip_color, chip_label, family = RANK_STYLES[
        min(idx, len(RANK_STYLES) - 1)
    ]
    current_rank = rank_name(messages)
    next_rank = next_rank_name(messages)
    progress = progress_percent(messages)

    # Per-rank tinted gradient background (low-res loop, then smooth upscale).
    scale = 8
    grad_w, grad_h = W // scale, H // scale
    small = Image.new("RGB", (grad_w, grad_h), (9, 15, 29))
    small_px = small.load()
    for gy in range(grad_h):
        y = gy * scale
        for gx in range(grad_w):
            x = gx * scale
            glow = max(0, 1 - (((x - 920) / 750) ** 2 + ((y - 300) / 650) ** 2))
            small_px[gx, gy] = (
                9 + int(accent[0] * 0.16 * glow),
                15 + int(accent[1] * 0.16 * glow),
                29 + int(accent[2] * 0.16 * glow),
            )
    img = small.resize((W, H), Image.Resampling.BILINEAR)

    draw = ImageDraw.Draw(img, "RGBA")

    # Subtle circuit-board grid in the rank colour.
    for x in range(40, W, 48):
        draw.line((x, 0, x, H), fill=(*accent, 20), width=1)
    for y in range(30, H, 48):
        draw.line((0, y, W, y), fill=(*accent, 20), width=1)

    # Accent stripe and panel.
    draw.rounded_rectangle(
        (54, 48, 1146, 627), radius=32,
        fill=(12, 24, 43, 238), outline=(*accent, 150), width=2,
    )
    draw.rounded_rectangle((54, 48, 68, 627), radius=7, fill=(*accent, 255))

    # Rank-specific CPU illustration.
    cx, cy = 865, 315
    draw_cpu(draw, cx, cy, idx, accent, chip_color, chip_label, family)
    draw.text(
        (cx, cy + 196), t("card_gen", number=idx + 1), font=load_font(22, True),
        fill=_lighten(accent, 0.55), anchor="mm",
    )

    # Large rank number watermark.
    draw.text(
        (1128, 610), f"{idx + 1:02d}", font=load_font(76, True),
        fill=(*accent, 30), anchor="rs",
    )

    # Text content.
    draw.text(
        (105, 92), "CPU EVOLUTION", font=load_font(27, True),
        fill=(*_lighten(accent, 0.45), 255),
    )
    draw.text((105, 157), t("card_rank_label"), font=load_font(20, True),
              fill=(145, 165, 190, 255))
    rank_text = current_rank.upper()
    max_rank_width = 540
    rank_lines = [rank_text]
    rank_font = load_font(47, True)
    for size, max_lines in ((47, 1), (42, 2), (36, 2), (32, 2), (28, 2)):
        rank_font = load_font(size, True)
        lines = _wrap_lines(draw, rank_text, rank_font, max_rank_width)
        if len(lines) <= max_lines:
            rank_lines = lines
            break
        rank_lines = lines
    else:
        if len(rank_lines) > 2:
            rank_lines = rank_lines[:1] + [" ".join(rank_lines[1:])]
        rank_lines = [_ellipsize(draw, line, rank_font, max_rank_width) for line in rank_lines]
    try:
        r_ascent, r_descent = rank_font.getmetrics()
        rank_line_height = r_ascent + r_descent
    except (AttributeError, OSError):
        rank_line_height = int(getattr(rank_font, "size", 47)) + 6
    rank_spacing = rank_line_height + 2
    for i, line in enumerate(rank_lines):
        draw.text((105, 205 + i * rank_spacing), line, font=rank_font,
                  fill=(245, 249, 255, 255))
    rank_bottom = 205 + rank_line_height + rank_spacing * (len(rank_lines) - 1)

    safe_name = clean_text(display_name) or t("card_default_name")
    name_font, name_lines = layout_card_name(draw, safe_name, 540)
    try:
        ascent, descent = name_font.getmetrics()
        line_height = ascent + descent
    except (AttributeError, OSError):
        line_height = int(getattr(name_font, "size", 27)) + 6
    spacing = line_height + 4
    block_height = line_height + spacing * (len(name_lines) - 1)
    # Single-line names keep their usual place; longer names grow upwards so
    # they never collide with the message counter underneath. Keep clear of rank.
    name_top = 300 if len(name_lines) == 1 else 352 - block_height
    min_top = rank_bottom + 6
    if name_top < min_top:
        name_top = min(min_top, 352 - block_height)
    for i, line in enumerate(name_lines):
        draw.text((108, name_top + i * spacing), line, font=name_font,
                  fill=(196, 216, 236, 255))
    draw.text(
        (108, 365),
        t("card_messages", messages=f"{messages:,}".replace(",", " ")),
        font=load_font(25, True),
        fill=(*_lighten(accent, 0.35), 255),
    )

    # Progress bar.
    draw.text((108, 440), t("card_progress_label"), font=load_font(17, True),
              fill=(145, 165, 190, 255))
    bar_x1, bar_y1, bar_x2, bar_y2 = 108, 476, 650, 497
    draw.rounded_rectangle((bar_x1, bar_y1, bar_x2, bar_y2),
                           radius=10, fill=(35, 51, 72, 255))
    fill_x = bar_x1 + int((bar_x2 - bar_x1) * progress / 100)
    if fill_x > bar_x1:
        draw.rounded_rectangle((bar_x1, bar_y1, fill_x, bar_y2),
                               radius=10, fill=(*accent, 255))
    progress_line = (
        t("card_next", progress=progress, next_rank=next_rank)
        if next_rank
        else t("card_max", progress=progress)
    )
    draw.text((108, 523), progress_line,
              font=load_font(18, True), fill=(205, 220, 235, 255))
    draw.text((108, 582), t("card_footer"),
              font=load_font(16, True), fill=(100, 130, 160, 255))

    output = io.BytesIO()
    img.save(output, format="PNG", optimize=True)
    return output.getvalue()


async def send_rank_card(bot: Bot, chat_id: int, user_id: int,
                         display_name: str, messages: int, announce: bool = False):
    # Card rendering is CPU-bound: run it in a worker thread so polling and
    # other handlers stay responsive.
    card = await asyncio.to_thread(make_rank_card, display_name, messages)
    safe_name = esc_name(display_name, 64)
    caption = t(
        "rank_up_caption" if announce else "profile_caption",
        name=safe_name,
        rank=html.escape(rank_name(messages)),
        messages=messages,
    )
    await bot.send_photo(
        chat_id=chat_id,
        photo=BufferedInputFile(card, filename="cpu_rank.png"),
        caption=caption,
        parse_mode="HTML",
    )


async def announce_rank_up(
    bot: Bot,
    chat_id: int,
    user_id: int,
    display_name: str,
    old_count: int,
    new_count: int,
):
    """Send a rank-up card/text only if a rank boundary was crossed."""
    old_idx = old_count // MESSAGES_PER_RANK
    new_idx = new_count // MESSAGES_PER_RANK
    if new_idx > old_idx and new_idx < len(RANKS):
        await send_rank_card(
            bot, chat_id, user_id, display_name, new_count, announce=True
        )
    elif new_count == len(RANKS) * MESSAGES_PER_RANK:
        await bot.send_message(chat_id, t("rank_up_final"), parse_mode="HTML")


# -------------------- TELEGRAM COMMANDS --------------------

@dp.message(Command("start"), ChatAllowed(), COMMAND_THROTTLE)
async def start_command(message: Message):
    await message.answer(t("start_text"))


@dp.message(Command("profile"), ChatAllowed(), COMMAND_THROTTLE)
async def profile_command(message: Message, bot: Bot):
    if message.chat.type not in ("group", "supergroup"):
        await message.answer(t("profile_group_only"))
        return

    target = message.reply_to_message.from_user if message.reply_to_message else message.from_user
    if not target or target.is_bot:
        await message.answer(t("user_not_determined"))
        return

    count = get_messages(message.chat.id, target.id)
    await send_rank_card(bot, message.chat.id, target.id, target.full_name, count)


@dp.message(Command("rank"), ChatAllowed(), COMMAND_THROTTLE)
async def rank_command(message: Message):
    if message.chat.type not in ("group", "supergroup"):
        await message.answer(t("group_only"))
        return

    target = message.reply_to_message.from_user if message.reply_to_message else message.from_user
    if not target or target.is_bot:
        await message.answer(t("user_not_determined"))
        return

    count = get_messages(message.chat.id, target.id)
    nxt = next_rank_name(count)
    remaining = MESSAGES_PER_RANK - (count % MESSAGES_PER_RANK)
    result = t(
        "rank_text",
        name=esc_name(target.full_name),
        rank=html.escape(rank_name(count)),
        count=count,
    )
    if nxt:
        result += t(
            "rank_next",
            next_rank=html.escape(nxt),
            remaining=remaining,
        )
    else:
        result += t("rank_max")
    await message.answer(result, parse_mode="HTML")


@dp.message(Command("id"), COMMAND_THROTTLE)
async def id_command(message: Message):
    target = message.reply_to_message.from_user if message.reply_to_message else message.from_user
    user_id = target.id if target else t("id_unknown")
    await message.answer(
        t("id_text", chat_id=message.chat.id, user_id=user_id),
        parse_mode="HTML",
    )


@dp.message(Command("top"), ChatAllowed(), COMMAND_THROTTLE)
async def top_command(message: Message):
    if message.chat.type not in ("group", "supergroup"):
        await message.answer(t("group_only"))
        return

    rows = get_top(message.chat.id, 10)
    if not rows:
        await message.answer(t("top_empty"))
        return

    lines = [t("top_header")]
    for place, row in enumerate(rows, start=1):
        name = esc_name(row["display_name"])
        lines.append(
            t(
                "top_line",
                place=place,
                name=name,
                rank=html.escape(rank_name(row["messages"])),
                messages=row["messages"],
            )
        )
    await message.answer(join_lines_fit(lines), parse_mode="HTML")


@dp.message(Command("help"), ChatAllowed(), COMMAND_THROTTLE)
async def help_command(message: Message):
    text = PUBLIC_HELP
    # Admin commands are listed only in a private chat with an admin.
    if is_admin(message.from_user) and message.chat.type == "private":
        text += "\n\n" + admin_help_text(message.from_user.id)
    await message.answer(text, parse_mode="HTML")


# -------------------- TELEGRAM ADMIN --------------------

class IsAdmin(BaseFilter):
    async def __call__(self, message: Message) -> bool:
        return is_admin(message.from_user)


class AdminUsage(Exception):
    pass


def admin_args(message: Message) -> list[str]:
    return (message.text or "").split()[1:]


def parse_int(value: str, label: str) -> int:
    try:
        number = int(value)
    except ValueError:
        raise AdminUsage(t("parse_int_invalid", label=label)) from None
    # Keep values inside the signed 64-bit range accepted by SQLite.
    if not -(2 ** 63) <= number < 2 ** 63:
        raise AdminUsage(t("parse_int_too_large", label=label))
    return number


def resolve_admin_target(message: Message, args: list[str]):
    """Resolve (chat_id, user_id, display_name, remaining_args) for admin commands."""
    reply = message.reply_to_message
    if (
        reply
        and reply.from_user
        and not reply.from_user.is_bot
        and message.chat.type in ("group", "supergroup")
    ):
        user = reply.from_user
        row = get_user(message.chat.id, user.id)
        name = row["display_name"] if row else user.full_name
        return message.chat.id, user.id, name, args

    if message.chat.type == "private":
        if len(args) < 2:
            raise AdminUsage(t("admin_target_private"))
        chat_id = parse_int(args[0], t("label_chat_id"))
        user_id = parse_int(args[1], t("label_user_id"))
        rest = args[2:]
    else:
        if not args:
            raise AdminUsage(t("admin_target_group"))
        chat_id = message.chat.id
        user_id = parse_int(args[0], t("label_user_id"))
        rest = args[1:]

    row = get_user(chat_id, user_id)
    name = row["display_name"] if row else t(
        "admin_default_name", user_id=user_id
    )
    return chat_id, user_id, name, rest


def resolve_group_target(message: Message, args: list[str]):
    """Resolve (chat_id, title) for /agroup add|del."""
    if args:
        chat_id = parse_int(args[0], t("label_chat_id"))
        if chat_id >= 0:
            raise AdminUsage(t("admin_group_id_negative"))
        return chat_id, ""
    if message.chat.type in ("group", "supergroup"):
        return message.chat.id, message.chat.title or ""
    raise AdminUsage(t("admin_group_id_private"))


async def admin_usage_error(message: Message, exc: AdminUsage):
    await message.answer(
        t(
            "admin_usage_error",
            error=html.escape(str(exc)),
            usage=ADMIN_USAGE,
        ),
        parse_mode="HTML",
    )


@dp.message(Command("admin"), IsAdmin())
async def admin_command(message: Message):
    if message.chat.type != "private":
        await message.answer(t("admin_dm_only"))
        return
    await message.answer(
        admin_help_text(message.from_user.id),
        parse_mode="HTML",
    )


@dp.message(Command("user"), ChatAllowed(), COMMAND_THROTTLE)
async def user_command(message: Message):
    if message.chat.type not in ("group", "supergroup"):
        await message.answer(t("group_only"))
        return

    target = message.reply_to_message.from_user if message.reply_to_message else message.from_user
    if not target or target.is_bot:
        await message.answer(t("user_not_determined"))
        return

    row = get_user(message.chat.id, target.id)
    if not row:
        await message.answer(
            t("user_not_found", user_id=target.id),
            parse_mode="HTML",
        )
        return

    count = int(row["messages"])
    text = t(
        "user_text",
        name=esc_name(row["display_name"]),
        user_id=target.id,
        rank=html.escape(rank_name(count)),
        count=count,
    )
    nxt = next_rank_name(count)
    if nxt:
        text += t(
            "user_next",
            next_rank=html.escape(nxt),
            remaining=MESSAGES_PER_RANK - count % MESSAGES_PER_RANK,
        )
    else:
        text += t("user_max")
    await message.answer(text, parse_mode="HTML")


@dp.message(Command("aadd"), IsAdmin())
async def aadd_command(message: Message, bot: Bot):
    try:
        chat_id, user_id, name, rest = resolve_admin_target(
            message, admin_args(message)
        )
        if not rest:
            raise AdminUsage(t("aadd_need_amount"))
        amount = parse_int(rest[0], t("label_amount"))
        if amount <= 0:
            raise AdminUsage(t("aadd_positive"))
    except AdminUsage as exc:
        await admin_usage_error(message, exc)
        return

    old_count = get_messages(chat_id, user_id)
    new_count = old_count + amount
    if new_count > MAX_MESSAGES:
        await admin_usage_error(
            message,
            AdminUsage(t("aadd_too_big", max_messages=MAX_MESSAGES)),
        )
        return
    save_user(chat_id, user_id, name, new_count)
    await message.answer(
        t(
            "aadd_done",
            name=esc_name(name),
            old=old_count,
            new=new_count,
            rank=html.escape(rank_name(new_count)),
        ),
        parse_mode="HTML",
    )
    await announce_rank_up(bot, chat_id, user_id, name, old_count, new_count)


@dp.message(Command("asetrank"), IsAdmin())
async def asetrank_command(message: Message, bot: Bot):
    try:
        chat_id, user_id, name, rest = resolve_admin_target(
            message, admin_args(message)
        )
        if not rest:
            raise AdminUsage(t("asetrank_need", ranks_count=len(RANKS)))
        selected = parse_int(rest[0], t("label_rank_number"))
        if not 1 <= selected <= len(RANKS):
            raise AdminUsage(t("asetrank_range", ranks_count=len(RANKS)))
    except AdminUsage as exc:
        await admin_usage_error(message, exc)
        return

    old_count = get_messages(chat_id, user_id)
    new_count = (selected - 1) * MESSAGES_PER_RANK
    save_user(chat_id, user_id, name, new_count)
    await message.answer(
        t(
            "asetrank_done",
            name=esc_name(name),
            rank=html.escape(RANKS[selected - 1]),
            messages=new_count,
        ),
        parse_mode="HTML",
    )
    if new_count // MESSAGES_PER_RANK > old_count // MESSAGES_PER_RANK:
        await send_rank_card(bot, chat_id, user_id, name, new_count, announce=True)


@dp.message(Command("areset"), IsAdmin())
async def areset_command(message: Message):
    try:
        chat_id, user_id, name, rest = resolve_admin_target(
            message, admin_args(message)
        )
    except AdminUsage as exc:
        await admin_usage_error(message, exc)
        return

    if not rest or rest[0].lower() != "confirm":
        await message.answer(
            t("areset_confirm", name=esc_name(name)),
            parse_mode="HTML",
        )
        return

    old_count = get_messages(chat_id, user_id)
    save_user(chat_id, user_id, name, 0)
    await message.answer(
        t("areset_done", old=old_count),
        parse_mode="HTML",
    )


@dp.message(Command("ranks"), ChatAllowed(), COMMAND_THROTTLE)
async def ranks_command(message: Message):
    lines = [t("ranks_header")]
    for i, rank in enumerate(RANKS, 1):
        low = (i - 1) * MESSAGES_PER_RANK
        high = low + MESSAGES_PER_RANK - 1
        lines.append(
            t(
                "ranks_line",
                number=i,
                rank=html.escape(rank),
                low=low,
                high=high,
            )
        )
    lines.append(
        t(
            "ranks_beyond",
            beyond_rank=BEYOND_RANK,
            threshold=len(RANKS) * MESSAGES_PER_RANK,
        )
    )
    await message.answer("\n".join(lines), parse_mode="HTML")


@dp.message(Command("agroup"), IsAdmin())
async def agroup_command(message: Message, bot: Bot):
    args = admin_args(message)
    if not args:
        await message.answer(t("agroup_help"), parse_mode="HTML")
        return

    action = args[0].lower()
    rest = args[1:]

    if action == "list":
        rows = get_allowed_chats()
        if not rows:
            await message.answer(t("agroup_empty"), parse_mode="HTML")
            return
        lines = [t("agroup_header")]
        for row in rows:
            title = row["title"] or t("agroup_no_title")
            lines.append(
                t(
                    "agroup_line",
                    title=esc_name(title),
                    chat_id=row["chat_id"],
                )
            )
        await message.answer(join_lines_fit(lines), parse_mode="HTML")
        return

    if action not in ("add", "del"):
        await message.answer(t("agroup_unknown_action"), parse_mode="HTML")
        return

    try:
        chat_id, title = resolve_group_target(message, rest)
    except AdminUsage as exc:
        await message.answer(
            t("agroup_error", error=html.escape(str(exc))),
            parse_mode="HTML",
        )
        return

    if action == "add":
        if not title:
            try:
                chat = await bot.get_chat(chat_id)
                title = chat.title or chat.full_name or ""
            except Exception:
                title = ""
        add_allowed_chat(chat_id, title)
        await message.answer(
            t("agroup_added", chat_id=chat_id),
            parse_mode="HTML",
        )
        return

    if remove_allowed_chat(chat_id):
        await message.answer(
            t("agroup_removed", chat_id=chat_id),
            parse_mode="HTML",
        )
    else:
        await message.answer(
            t("agroup_not_found", chat_id=chat_id),
            parse_mode="HTML",
        )


# Register this catch-all handler AFTER command handlers.
@dp.message(F.chat.type.in_({"group", "supergroup"}), ChatAllowed())
async def count_group_messages(message: Message, bot: Bot):
    user = message.from_user
    if not user or user.is_bot:
        return

    # Do not count bot commands (including commands with captions).
    text_value = message.text or message.caption or ""
    if text_value.startswith("/"):
        return

    chat_id = message.chat.id
    now = time.time()
    if now - get_last_counted_at(chat_id, user.id) < MESSAGE_COOLDOWN_SECONDS:
        return
    old_count, new_count = count_user_message(
        chat_id, user.id, user.full_name, now
    )
    await announce_rank_up(bot, chat_id, user.id, user.full_name, old_count, new_count)


@dp.message(F.chat.type.in_({"group", "supergroup"}))
async def blocked_group_command(message: Message):
    """Explain why public commands are ignored in a non-whitelisted group."""
    if is_chat_allowed(message.chat.id):
        return
    text_value = message.text or ""
    if not text_value.startswith("/"):
        return
    if not await BLOCKED_NOTICE_THROTTLE(message):
        return
    await message.answer(t("blocked_notice"))


@dp.errors()
async def on_error(event: ErrorEvent, bot: Bot):
    """Report unhandled handler errors to admins (not to the group)."""
    logger.error(t("log_unhandled"), exc_info=event.exception)
    try:
        await notify_admins(
            bot,
            format_error_report(event),
            signature=f"{type(event.exception).__name__}:"
            f"{str(event.exception)[:200]}",
        )
    except Exception:
        logger.exception(t("log_report_failed"))


# -------------------- CONSOLE ADMIN MODE --------------------

def ask_int(prompt: str) -> int:
    while True:
        try:
            return int(input(prompt).strip())
        except ValueError:
            print(t("ask_int_invalid"))


def console_user_summary(chat_id: int, user_id: int):
    row = get_user(chat_id, user_id)
    if not row:
        print(t("console_user_not_found"))
        return
    count = row["messages"]
    print(t("console_user_name", name=row["display_name"]))
    print(t("console_user_messages", count=count))
    print(t("console_user_rank", rank=rank_name(count)))
    nxt = next_rank_name(count)
    if nxt:
        print(t("console_user_next", next_rank=nxt))
        print(
            t(
                "console_user_remaining",
                remaining=MESSAGES_PER_RANK - count % MESSAGES_PER_RANK,
            )
        )
    print()


async def console_menu():
    if not TOKEN:
        print(t("token_missing"))
        return

    async with Bot(TOKEN) as bot:
        while True:
            print("\n" + "=" * 42)
            print(t("console_title"))
            print("=" * 42)
            print(t("console_menu_find"))
            print(t("console_menu_add"))
            print(t("console_menu_setrank"))
            print(t("console_menu_reset"))
            print(t("console_menu_top"))
            print(t("console_menu_card"))
            print(t("console_menu_ranks"))
            print(t("console_menu_exit"))

            choice = input(t("console_choose")).strip()

            if choice == "0":
                break

            elif choice == "1":
                chat_id = ask_int(t("console_ask_chat"))
                user_id = ask_int(t("console_ask_user"))
                console_user_summary(chat_id, user_id)

            elif choice == "2":
                chat_id = ask_int(t("console_ask_chat"))
                user_id = ask_int(t("console_ask_user"))
                amount = ask_int(t("console_ask_amount"))
                if amount <= 0:
                    print(t("console_add_positive"))
                    continue
                row = get_user(chat_id, user_id)
                name = row["display_name"] if row else t(
                    "admin_default_name", user_id=user_id
                )
                old = get_messages(chat_id, user_id)
                new = old + amount
                save_user(chat_id, user_id, name, new)
                print(t("console_add_done", old=old, new=new, rank=rank_name(new)))
                if old // MESSAGES_PER_RANK != new // MESSAGES_PER_RANK:
                    confirm = input(t("console_ask_card")).lower()
                    if confirm == "y":
                        await send_rank_card(bot, chat_id, user_id, name, new, announce=True)
                        print(t("console_card_sent"))

            elif choice == "3":
                chat_id = ask_int(t("console_ask_chat"))
                user_id = ask_int(t("console_ask_user"))
                print("\n".join(f"{i + 1}. {name}" for i, name in enumerate(RANKS)))
                selected = ask_int(t("console_ask_rank"))
                if not 1 <= selected <= len(RANKS):
                    print(t("console_no_rank"))
                    continue
                row = get_user(chat_id, user_id)
                name = row["display_name"] if row else t(
                    "admin_default_name", user_id=user_id
                )
                old = get_messages(chat_id, user_id)
                new = (selected - 1) * MESSAGES_PER_RANK
                save_user(chat_id, user_id, name, new)
                print(
                    t(
                        "console_rank_set",
                        rank=RANKS[selected - 1],
                        messages=new,
                    )
                )
                if new // MESSAGES_PER_RANK > old // MESSAGES_PER_RANK:
                    confirm = input(t("console_ask_card_plain")).lower()
                    if confirm == "y":
                        await send_rank_card(bot, chat_id, user_id, name, new, announce=True)
                        print(t("console_card_sent"))

            elif choice == "4":
                chat_id = ask_int(t("console_ask_chat"))
                user_id = ask_int(t("console_ask_user"))
                confirm = input(t("console_ask_reset"))
                if confirm == "RESET":
                    row = get_user(chat_id, user_id)
                    name = row["display_name"] if row else t(
                        "admin_default_name", user_id=user_id
                    )
                    save_user(chat_id, user_id, name, 0)
                    print(t("console_reset_done"))
                else:
                    print(t("console_cancelled"))

            elif choice == "5":
                chat_id = ask_int(t("console_ask_chat"))
                rows = get_top(chat_id, 20)
                if not rows:
                    print(t("console_top_empty"))
                for i, row in enumerate(rows, 1):
                    print(
                        t(
                            "console_top_line",
                            place=i,
                            name=row["display_name"],
                            messages=row["messages"],
                            rank=rank_name(row["messages"]),
                        )
                    )

            elif choice == "6":
                chat_id = ask_int(t("console_ask_chat"))
                user_id = ask_int(t("console_ask_user"))
                row = get_user(chat_id, user_id)
                name = row["display_name"] if row else t(
                    "admin_default_name", user_id=user_id
                )
                count = get_messages(chat_id, user_id)
                await send_rank_card(bot, chat_id, user_id, name, count, announce=False)
                print(t("console_test_card_sent"))

            elif choice == "7":
                for i, name in enumerate(RANKS, 1):
                    low = (i - 1) * MESSAGES_PER_RANK
                    high = low + MESSAGES_PER_RANK - 1
                    print(
                        t(
                            "console_ranks_line",
                            number=i,
                            rank=name,
                            low=low,
                            high=high,
                        )
                    )

            else:
                print(t("console_unknown"))


# -------------------- STARTUP --------------------

async def run_bot():
    if not TOKEN:
        raise RuntimeError(t("token_missing"))
    if not ADMIN_IDS:
        print(t("startup_admin_missing"))
    if not ERROR_REPORT_IDS:
        print(t("startup_errors_missing"))
    if not ALLOWED_CHATS:
        print(t("startup_no_groups"))

    bot = Bot(TOKEN)
    print(t("startup_started"))
    delay = 5
    try:
        while True:
            try:
                await dp.start_polling(bot)
                break
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                # Keep the container alive: report and retry with backoff.
                logger.error(t("log_polling_error"), exc_info=exc)
                try:
                    await notify_admins(
                        bot,
                        format_fatal_error(exc),
                        signature=f"fatal:{type(exc).__name__}:{str(exc)[:200]}",
                    )
                except Exception:
                    logger.exception(t("log_fatal_send_failed"))
                print(t("retry_polling", seconds=delay))
                await asyncio.sleep(delay)
                delay = min(delay * 2, 300)
            else:
                delay = 5
    finally:
        await bot.session.close()


def main():
    mode = sys.argv[1].lower() if len(sys.argv) > 1 else "menu"
    if mode == "bot":
        asyncio.run(run_bot())
    elif mode == "console":
        asyncio.run(console_menu())
    else:
        print(t("menu_title"))
        print(t("menu_start_bot"))
        print(t("menu_console"))
        print(t("menu_exit"))
        choice = input(t("menu_choice")).strip()
        if choice == "1":
            asyncio.run(run_bot())
        elif choice == "2":
            asyncio.run(console_menu())


if __name__ == "__main__":
    main()
