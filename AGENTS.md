# AGENTS.md

## Project

Telegram bot split into a few modules: `bot.py` holds config, SQLite access, Pillow
rank-card rendering, aiogram handlers, and the console admin tool; `ranks.py` holds the
CPU rank names; `i18n.py` loads one catalog per language from `locales/` (`ru.py`
default, `en.py`). No tests, CI, lint, formatter, or typecheck config exists. Docs are
in `README.txt` (Russian).

Stack: Python 3.10+, `aiogram>=3.31,<4.0`, `aiohttp>=3.14.5,<4.0`,
`python-dotenv>=1.2,<2.0`, `Pillow>=13.0,<14.0` (`requirements.txt`).

## Run

```cmd
py -m pip install -r requirements.txt
copy .env.example .env   REM then set BOT_TOKEN + ADMIN_IDS
py bot.py                REM interactive menu
py bot.py bot            REM start Telegram polling
py bot.py console        REM local admin console (still needs a valid token)
```

Docker (server deployment):

```bash
cp .env.example .env     # BOT_TOKEN, ADMIN_IDS, optional ERROR_REPORT_IDS
docker compose up -d --build
docker compose logs -f
```

- `docker-compose.yml` uses `restart: unless-stopped`, so the bot returns after a
  server reboot once the Docker daemon starts. On Linux the daemon itself must be
  enabled: `systemctl enable --now docker`.
- SQLite lives on a host bind mount `./data:/data`; the container uses
  `DB_PATH=/data/users.db`. The image never contains the database.
- `.env` is in `.dockerignore` and is not baked into the image; Compose reads it at
  container start. Re-run `docker compose up -d` after changing it.
- No test suite. To verify, use `py bot.py console` (menu options 1-7: add messages,
  set rank, send test card) or a throwaway Telegram group. Check `/help` in a group
  (public list only) and in DM as an admin (admin list appended).
- Syntax-only check: `py -m py_compile bot.py`.

## Gotchas

- Importing `bot.py` has side effects: it opens/creates the SQLite database (WAL mode)
  and runs schema DDL + a `last_counted_at` column migration at module level.
  Do not import it from scripts/tests without expecting a DB to be created.
- DB path comes from `DB_PATH` (env) and defaults to `users.db` next to `bot.py`;
  a relative `DB_PATH` is resolved against the script directory, not the CWD. The
  parent directory is created automatically. In Docker it is `/data/users.db`.
  The database is runtime data; do not commit or delete it (it holds all stats).
- All SQL must stay parameterized with `?` placeholders. Never interpolate user input,
  even for integers or limits.
- Anti-spam is two-layered: the group counter checks `MESSAGE_COOLDOWN_SECONDS` via
  `last_counted_at` and must write counts only through `count_user_message`; public
  commands carry `COMMAND_THROTTLE` (`COMMAND_COOLDOWN_SECONDS`). Do not add unthrottled
  public command handlers.
- Group whitelist lives in the `allowed_chats` table and is managed by `/agroup
  add|del|list`. Strict mode: only groups in the whitelist are served; an empty
  whitelist means no groups are served at all. Seed `ALLOWED_CHAT_IDS` is used once on
  the first start (`settings.whitelist_seeded`); after that the DB is authoritative, so
  deleting all groups does not resurrect the seed.
- Public group handlers and the catch-all counter must carry `ChatAllowed()`; admin
  handlers and `/id` intentionally do not, so an admin can add a group from inside it.
  The fallback `blocked_group_command` handler must stay registered after the counter and
  only replies to commands. `is_chat_allowed` reads the in-memory `ALLOWED_CHATS` set,
  which `add_allowed_chat`/`remove_allowed_chat` must keep in sync with the DB.
- aiogram 3 handler order matters: the catch-all group counter
  `@dp.message(F.chat.type.in_({"group", "supergroup"}), ChatAllowed())` must stay
  registered after all `Command(...)` handlers, otherwise commands are counted as
  messages. Register any new command/admin handler before it. The
  `blocked_group_command` fallback is registered after the counter.
- Telegram admin access is enforced by the `IsAdmin()` filter against `ADMIN_IDS`
  (comma/space-separated env var, parsed at import; empty = admin commands disabled).
  Never trust a username or chat ID for authorization.
- Admin target resolution: in a group, a reply targets the replied user in the current
  chat; otherwise the first argument is the user ID. In private chat, admin commands
  require `<chat_id> <user_id>` before the command's own arguments (`/atop` needs only
  `<chat_id>`). `/areset` requires the literal word `confirm`.
- `/help` is public and always shows the public list; the admin list is appended only
  when the caller is in `ADMIN_IDS` AND the chat is private. `/admin` in a group must
  not print the admin list either.
- The counter explicitly skips bot users and messages whose text/caption starts with `/`.
- Rank-up notifications are centralized in `announce_rank_up`; use it for any new
  count-changing path instead of duplicating boundary logic or hardcoding `100`.
- Ranking constants live in `bot.py` (`MESSAGES_PER_RANK = 100`,
  `MAX_MESSAGES = 10_000_000`) and the 17-entry `RANKS` list in `ranks.py`
  (Intel 286 → Threadripper); ≥1700 messages is `BEYOND_RANK` ("Beyond Threadripper").
  Progress shown on cards is `messages % 100`.
- `MAX_MESSAGES = 10_000_000` caps counters and admin additions (`save_user`,
  `count_user_message`, `/aadd`); `parse_int` rejects values outside signed 64-bit
  before they reach SQLite.
- Rank-up cards fire only when the count crosses a rank boundary (live message counter,
  `/aadd`, `/asetrank`); the final 1700 boundary has a separate text-only branch.
- `RANK_STYLES` is parallel to `RANKS` in `ranks.py` (same order): each entry defines
  the accent colour, chip colour, chip label and `draw_cpu()` family. Adding a rank
  requires editing both files and keeping the order aligned; a missing style falls
  back to the Threadripper theme.
- UI strings must not be hardcoded in `bot.py`: add a key to `locales/ru.py` **and**
  `locales/en.py`, then call `t("key", **values)`. Keys must match across catalogs;
  missing keys fall back to Russian and unknown keys raise `KeyError`. `LANGUAGE`
  comes from `.env`, so `.env` is loaded before `i18n` is imported — keep that import
  order. Catalogs are loaded once at startup; changing the language needs a restart.
- `Dockerfile` copies `bot.py`, `ranks.py`, `i18n.py` and `locales/`. Add new runtime
  modules to that `COPY` list or the container will fail with `ModuleNotFoundError`
  (the image has a read-only rootfs, so nothing is generated at runtime).
- Cards are generated locally with Pillow (1200x675, PNG). Font lookup tries Windows
  Arial/Segoe UI, then DejaVu/Liberation, then Pillow's bitmap default — output can
  differ between machines, that is expected. The Dockerfile installs
  `fonts-dejavu-core`; keep that if you add Linux font paths.
- `make_rank_card` is `@lru_cache(maxsize=32)` and must only be called through
  `asyncio.to_thread` (see `send_rank_card`): rendering is CPU-bound and blocks the
  event loop. The gradient is drawn at low resolution and upscaled; do not reintroduce
  a per-pixel loop over 1200x675.
- Card names are laid out by `layout_card_name`: one line at 27 px, otherwise wrapped
  to 2-3 lines at 25/22 px. Keep the name block above the message counter
  (bottom ≈ y=352) so long names never overlap it; three lines start at y≈266 and must
  stay below the rank title. Do not hard-truncate names with a 28-character slice.
- Unhandled update errors go to `ERROR_REPORT_IDS` (fallback `ADMIN_IDS`) via
  `notify_admins`; the `@dp.errors()` handler must stay registered. Identical errors
  are throttled by `ERROR_NOTIFY_COOLDOWN_SECONDS` (default 300).
- `run_bot()` retries `start_polling` with exponential backoff (5 s → 300 s) and
  reports fatal errors to admins instead of letting the container exit. Admins must
  press `/start` in DM or Telegram cannot deliver reports (failure is only logged).
- Secrets: `load_dotenv(Path(__file__).with_name(".env"))` loads only the file next to
  `bot.py` (never CWD/parents). `redact_secrets` + `_RedactingFormatter` replace the
  bot token and token-shaped strings with `<bot-token>` in logs, error reports and
  admin notifications — keep both when adding new logging/report paths.
  `.env` and the DB are covered by `.gitignore`/`.dockerignore`; never commit them.
- `os.umask(0o077)` is set at import so SQLite/WAL files are owner-only. Do not move
  it after the DB connection is opened.
- Docker hardening in `docker-compose.yml`: `read_only`, `/tmp` tmpfs, `cap_drop: ALL`,
  `no-new-privileges`, `mem_limit`/`pids_limit`. Any new write path must go to
  `/data` (bind mount) or `/tmp`, otherwise the container fails. Non-root `user:` is
  opt-in and requires `chown` of `./data`. Run exactly one instance per token/DB.
- Captions use `parse_mode="HTML"`; never pass a raw user-controlled name through
  `html.escape` alone. Use `esc_name` (whitespace/control-char cleanup, 48-char cap,
  HTML escape) for names and `join_lines_fit`/`tg_len` for unbounded lists
  (`/top`, `/atop`, `/agroup list`). Error reports also embed tracebacks in `<pre>`
  and must be HTML-escaped and truncated below Telegram's 4096-char limit.
- User-facing bot text is Russian — keep new messages Russian for consistency.
- Telegram setup requirement: Privacy Mode must be disabled in @BotFather for the bot
  to receive all group messages (no admin rights needed); earlier messages are never
  counted retroactively.
