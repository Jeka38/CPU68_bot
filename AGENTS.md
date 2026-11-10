# AGENTS.md

## Project

Telegram bot (Python 3.10+, aiogram 3, SQLite, Pillow). `bot.py` holds config, DB access,
handlers, console admin, and card rendering; `ranks.py` defines `RANKS`; `i18n.py` loads
`locales/ru.py` or `locales/en.py` selected by `LANGUAGE`. No tests, CI, lint, formatter,
or typecheck config. Russian docs in `README.txt`.

## Run

```cmd
py -m pip install -r requirements.txt
copy .env.example .env   REM set BOT_TOKEN, ADMIN_IDS (optional: ERROR_REPORT_IDS, ALLOWED_CHAT_IDS, DB_PATH)
py bot.py                REM interactive menu
py bot.py bot            REM Telegram polling
py bot.py console        REM local admin console (still needs a valid token)
py -m py_compile bot.py  REM syntax-only check
```

Docker:

```bash
cp .env.example .env
docker compose up -d --build
docker compose logs -f
```

- No automated tests. Verify with `py bot.py console`, a throwaway Telegram group, or
  `/help` (group: public list only; admin DM: public + admin list).
- Docker uses `restart: unless-stopped`, bind mount `./data:/data`, and `DB_PATH=/data/users.db`.
  `.env` is not baked into the image; change requires `docker compose up -d`.

## Gotchas

- **Import side effects:** importing `bot.py` sets `os.umask(0o077)`, loads `.env` next to
  `bot.py` (not CWD), opens/creates the SQLite DB (WAL), and runs schema/migration DDL.
  Keep `.env` load before `i18n` import and `umask` before DB open.
- **DB:** path from `DB_PATH` env, default `users.db` next to `bot.py`; relative paths resolve
  against script dir, parent dir auto-created. Runtime data — never commit/delete. All SQL must
  use `?` placeholders (no interpolation). Run one instance per token/DB.
- **Whitelist:** groups are served only if in `allowed_chats` (`/agroup add|del|list`).
  `ALLOWED_CHAT_IDS` seeds once on first start (`settings.whitelist_seeded`); then DB is
  authoritative. Public group handlers and the catch-all counter must carry `ChatAllowed()`;
  admin handlers and `/id` must not. `is_chat_allowed` reads in-memory `ALLOWED_CHATS` kept in
  sync by `add_allowed_chat`/`remove_allowed_chat`.
- **Handler order (aiogram 3):** register all `Command(...)`/admin handlers before the catch-all
  group counter `@dp.message(F.chat.type.in_({"group", "supergroup"}), ChatAllowed())` or commands
  get counted as messages. `blocked_group_command` fallback must stay after the counter and reply
  only to commands.
- **Auth/targets:** admin access = `IsAdmin()` against `ADMIN_IDS` (parsed at import; empty disables).
  In group, reply targets replied user in current chat else first arg is user ID; in private chat
  admin commands take `<chat_id> <user_id>`. `/areset` requires literal `confirm`. `/help` appends
  admin list only in private chat to an admin.
- **Counting/ranks:** skip bots and messages whose text/caption starts with `/`. Write counts only
  via `count_user_message` (respects `MESSAGE_COOLDOWN_SECONDS`/`last_counted_at`); the first seen
  message registers the user (messages 0, nickname updated) and is not counted. Nickname is updated
  on counted messages. Public commands use `COMMAND_THROTTLE` (`COMMAND_COOLDOWN_SECONDS`) — do not
  add unthrottled public handlers. Use `announce_rank_up` for any count-changing path. Constants:
  `MESSAGES_PER_RANK` from env (default 100, min 1), `MAX_MESSAGES=10_000_000`, `RANKS` in `ranks.py`
  (currently 55), messages `>= len(RANKS) * MESSAGES_PER_RANK` are `BEYOND_RANK`, progress `messages % MESSAGES_PER_RANK`. `parse_int`
  rejects outside signed 64-bit; `MAX_MESSAGES` caps counters.
- **Commands:** public group commands include `/profile`, `/user`, `/ranks`, `/top`, `/id` (plus
  `/help`, `/start`); admin Telegram commands are `/admin`, `/asetrank`, `/areset`, `/agroup`. No
  duplicate admin/user command names. Keep handler registration before the catch-all counter.
- **Ranks/cards:** `RANK_STYLES` in `bot.py` must stay parallel to `RANKS` in `ranks.py` (same
  order/length). `draw_cpu` renders an index-based unique illustration per rank using `RANK_STYLES`
  label/colors. Rank-up cards fire on rank-boundary crossings (`/asetrank`, live counter); the final
  boundary (`len(RANKS)*MESSAGES_PER_RANK`) is text-only. `make_rank_card` is `@lru_cache(maxsize=32)`
  and must run via `asyncio.to_thread` (`send_rank_card`). Keep text/layout within card bounds.
- **i18n/runtime files:** UI strings must not be hardcoded in `bot.py` — add keys to both
  `locales/ru.py` and `locales/en.py` and call `t(...)` (keys must match; fallback to ru, unknown
  raises). Catalogs load once at startup. `Dockerfile` copies `bot.py`, `ranks.py`, `i18n.py`,
  `locales/`; add new runtime modules to `COPY`. Linux cards use `fonts-dejavu-core`.
- **Safety/output:** `redact_secrets` + `_RedactingFormatter` must redact bot/token-shaped strings in
  logs and error/admin reports. Captions/error reports use `parse_mode="HTML"`: use `esc_name` for
  names and `join_lines_fit`/`tg_len` for unbounded lists (`/top`, `/ranks`, `/agroup list`, etc.);
  escape/truncate tracebacks in `<pre>` below 4096 chars. Unhandled errors go to `ERROR_REPORT_IDS`
  (fallback `ADMIN_IDS`) via `notify_admins` with `ERROR_NOTIFY_COOLDOWN_SECONDS` throttle;
  `@dp.errors()` must stay registered. `run_bot()` retries polling with backoff (5s→300s). Docker is
  hardened (`read_only`, `/tmp` tmpfs, `cap_drop: ALL`, `no-new-privileges`, limits); write only to
  `/data` or `/tmp`.
- **Telegram behavior:** user-facing text is Russian; keep new messages consistent. Privacy Mode must
  be disabled in @BotFather to receive all group messages (not retroactive).
