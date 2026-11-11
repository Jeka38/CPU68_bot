"""Russian UI strings (default language).

Placeholders use ``str.format`` syntax; values are inserted by ``i18n.t``.
Keep the same keys in every locale file (see locales/en.py).
"""

STRINGS = {
    # --- rank card (drawn with Pillow) ---
    "card_rank_label": "ПРОЦЕССОРНЫЙ РАНГ",
    "card_gen": "GEN {number:02d}",
    "card_messages": "{messages} СООБЩЕНИЙ",
    "card_progress_label": "ПРОГРЕСС ЭВОЛЮЦИИ",
    "card_next": "{progress}%  |  ДАЛЕЕ: {next_rank}",
    "card_max": "{progress}%  |  МАКСИМАЛЬНЫЙ РАНГ",
    "card_footer": "{step} СООБЩЕНИЙ = 1 ЭВОЛЮЦИЯ",
    "card_vault_label": "VAULT68-TEC CPU DEVISION",
    "card_default_name": "Пользователь Telegram",

    # --- public commands ---
    "start_text": (
        "Привет! Я CPU Evolution Bot.\n\n"
        "/profile — карточка твоего процессора\n"
        "/user — статистика участника\n"
        "/ranks — список рангов\n"
        "/top — рейтинг группы\n"
        "/help — все команды\n\n"
        "Чтобы посмотреть профиль другого участника, ответь на его "
        "сообщение командой /profile или /user."
    ),
    "profile_group_only": "Профили пока доступны внутри группы.",
    "user_not_determined": "Не удалось определить пользователя.",
    "group_only": "Команда работает внутри группы.",
    "profile_caption": (
        "🖥 <b>Профиль CPU Evolution</b>\n"
        "👤 {name}\n"
        "⚙️ Ранг: <b>{rank}</b>\n"
        "📨 Сообщений: <b>{messages}</b>"
    ),
    "rank_up_caption": (
        "🚀 <b>Повышение процессорного ранга!</b>\n"
        "👤 {name}\n"
        "🖥 Новый уровень: <b>{rank}</b>\n"
        "📨 Сообщений: <b>{messages}</b>"
    ),
    "rank_up_final": "🏆 <b>Threadripper достигнут!</b>",
    "rank_next": (
        "🚀 Следующий: <b>{next_rank}</b>\n"
        "До повышения: <b>{remaining}</b>"
    ),
    "rank_max": "🏆 Максимальный ранг достигнут!",
    "id_text": "Chat ID: <code>{chat_id}</code>\nUser ID: <code>{user_id}</code>",
    "id_unknown": "не определён",
    "top_empty": "Пока статистики нет.",
    "top_header": "🏆 <b>ТОП CPU EVOLUTION</b>\n",
    "top_line": "{place}. {name} — <b>{rank}</b> ({messages} сообщений)",
    "public_help": (
        "🤖 <b>CPU Evolution Bot</b>\n\n"
        "/profile — карточка процессорного ранга\n"
        "/user — статистика участника\n"
        "/ranks — список рангов\n"
        "/top — топ-10 группы\n"
        "/id — Chat ID и User ID\n"
        "/help — эта справка\n\n"
        "Профиль/статистика другого участника: ответьте на его сообщение командой /profile или /user.\n"
        "Команды работают в группе."
    ),

    # --- admin commands ---
    "admin_usage": (
        "В группе ответьте на сообщение участника и передайте только параметры.\n"
        "Без ответа первым параметром укажите Telegram user ID.\n"
        "В личке сначала chat ID группы, затем user ID."
    ),
    "admin_help": (
        "🛠 <b>Админ-команды CPU Evolution</b>\n\n"
        "{usage}\n\n"
        "/asetrank &lt;номер&gt; — выставить ранг (см. /ranks)\n"
        "/areset confirm — сбросить прогресс\n"
        "/agroup add|del|list — белый список групп\n"
        "/abackup — бэкап бота и БД (status|now|on|off|interval &lt;часы&gt;)\n\n"
        "В группе для /agroup add и /agroup del chat_id можно не указывать —\n"
        "будет использован текущий чат.\n\n"
        "Ваш Telegram ID: <code>{user_id}</code>"
    ),
    "admin_dm_only": "Список админ-команд доступен только в личном чате с ботом.",
    "admin_usage_error": "⚠️ {error}\n\n{usage}",
    "admin_target_private": "В личке укажите chat_id и user_id.",
    "admin_target_group": "Ответьте на сообщение участника или укажите user_id.",
    "admin_group_id_negative": "chat_id группы должен быть отрицательным числом.",
    "admin_group_id_private": "В личке укажите chat_id группы.",
    "admin_default_name": "User {user_id}",
    "label_chat_id": "chat_id",
    "label_user_id": "user_id",
    "label_amount": "Количество",
    "label_rank_number": "Номер ранга",
    "parse_int_invalid": "{label}: нужно целое число.",
    "parse_int_too_large": "{label}: число слишком большое.",
    "user_not_found": "Пользователь <code>{user_id}</code> пока не найден в базе этого чата.",
    "user_text": (
        "👤 <b>{name}</b> (<code>{user_id}</code>)\n"
        "⚙️ Ранг: <b>{rank}</b>\n"
        "📨 Сообщений: <b>{count}</b>"
    ),
    "user_next": (
        "\n🚀 Следующий: <b>{next_rank}</b>"
        "\nДо повышения: <b>{remaining}</b>"
    ),
    "user_max": "\n🏆 Максимальный ранг достигнут!",
    "asetrank_need": "Укажите номер ранга от 1 до {ranks_count}.",
    "asetrank_range": "Ранг должен быть от 1 до {ranks_count}.",
    "asetrank_done": (
        "✅ <b>{name}</b>: ранг <b>{rank}</b> (сообщений: {messages})"
    ),
    "areset_confirm": (
        "⚠️ Сброс обнулит прогресс <b>{name}</b>. "
        "Повторите команду с <code>confirm</code>."
    ),
    "areset_done": "♻️ Прогресс сброшен: {old} → <b>0</b>.",
    "ranks_header": "🖥 <b>Ранги CPU Evolution</b>",
    "ranks_line": "{number:2}. {rank} — {low}-{high} сообщений",
    "ranks_beyond": "🏆 {beyond_rank} — от {threshold} сообщений",

    # --- group whitelist ---
    "agroup_help": (
        "🛠 <b>Белый список групп</b>\n\n"
        "/agroup add &lt;chat_id&gt; — добавить группу\n"
        "/agroup del &lt;chat_id&gt; — удалить группу\n"
        "/agroup list — показать список\n\n"
        "В группе chat_id можно не указывать — будет использован текущий чат."
    ),
    "agroup_empty": (
        "📋 Белый список пуст — бот не обслуживает группы.\n"
        "Добавьте группу: /agroup add в самой группе "
        "или /agroup add &lt;chat_id&gt; в личке."
    ),
    "agroup_header": "📋 <b>Белый список групп</b>\n",
    "agroup_no_title": "без названия",
    "agroup_line": "• {title} — <code>{chat_id}</code>",
    "agroup_unknown_action": (
        "⚠️ Используйте /agroup add, /agroup del или /agroup list."
    ),
    "agroup_error": "⚠️ {error}",
    "agroup_added": "✅ Группа <code>{chat_id}</code> добавлена в белый список.",
    "agroup_removed": "🗑 Группа <code>{chat_id}</code> удалена из белого списка.",
    "agroup_not_found": "Группа <code>{chat_id}</code> не найдена в белом списке.",
    "blocked_notice": (
        "⚠️ Бот не активирован для этого чата. "
        "Администратор бота может включить его для этой группы."
    ),
    "welcome_new_member": "{name} Привет, скинь ножки",

    # --- backup ---
    "backup_no_recipients": "Не задан ERROR_REPORT_IDS/ADMIN_IDS — некому отправить бэкап.",
    "backup_caption_auto": "💾 Автобэкап CPU68 ({time}, БД: {db})",
    "backup_caption_manual": "💾 Бэкап CPU68 ({time}, БД: {db})",
    "backup_send_failed": "Не удалось отправить бэкап ни одному получателю.",
    "backup_creating": "⏳ Создаю бэкап и отправляю...",
    "backup_sent": "✅ Бэкап отправлен.\n{detail}",
    "backup_failed": "⚠️ Не удалось выполнить бэкап: {detail}",
    "backup_enabled_on": "✅ Автобэкап включён.",
    "backup_enabled_off": "✅ Автобэкап выключен.",
    "backup_interval_usage": "Использование: /abackup interval &lt;часы&gt; (минимум 1).",
    "backup_interval_set": "✅ Интервал автобэкапа: {hours} ч.",
    "backup_never": "ещё не выполнялся",
    "backup_state_on": "включён",
    "backup_state_off": "выключен",
    "backup_status": (
        "💾 <b>Бэкап</b>\n"
        "Статус: <b>{state}</b>\n"
        "Интервал: <b>{hours}</b> ч.\n"
        "Последний: <code>{last}</code>"
    ),
    "backup_help": (
        "💾 <b>/abackup</b>\n\n"
        "/abackup status — состояние\n"
        "/abackup now — сделать и отправить сейчас\n"
        "/abackup on|off — включить/выключить автобэкап\n"
        "/abackup interval &lt;часы&gt; — интервал (минимум 1)"
    ),

    # --- error reports and logs ---
    "error_report_header": (
        "🚨 <b>Ошибка в CPU Evolution Bot</b>\n"
        "🕒 <code>{stamp}</code>\n"
        "{context}\n\n"
    ),
    "fatal_report_header": (
        "🚨 <b>Критическая ошибка CPU Evolution Bot</b>\n"
        "🕒 <code>{stamp}</code>\n"
        "Бот перезапускает polling.\n\n"
    ),
    "log_report_send_failed": (
        "Не удалось отправить отчёт об ошибке {admin_id}: {error}"
    ),
    "log_unhandled": "Необработанная ошибка",
    "log_report_failed": "Не удалось отправить отчёт об ошибке",
    "log_polling_error": "Ошибка polling",
    "log_fatal_send_failed": "Не удалось отправить критическую ошибку",
    "retry_polling": "Перезапуск polling через {seconds} секунд...",

    # --- console admin mode ---
    "token_missing": "Не найден BOT_TOKEN. Заполни .env.",
    "console_title": "          CPU EVOLUTION CONSOLE",
    "console_menu_find": "[1] Найти пользователя",
    "console_menu_add": "[2] Добавить сообщения (с объявлением повышения)",
    "console_menu_setrank": "[3] Установить ранг вручную",
    "console_menu_reset": "[4] Сбросить прогресс",
    "console_menu_top": "[5] Показать ТОП группы",
    "console_menu_card": "[6] Отправить тестовую карточку",
    "console_menu_ranks": "[7] Показать список рангов",
    "console_menu_exit": "[0] Выход",
    "console_choose": "\nВыберите действие: ",
    "console_ask_chat": "Chat ID группы: ",
    "console_ask_user": "Telegram user ID: ",
    "console_ask_amount": "Сколько сообщений добавить: ",
    "console_ask_rank": "Номер ранга: ",
    "console_ask_card": "Отправить карточку нового ранга в группу? (y/n): ",
    "console_ask_card_plain": "Отправить карточку в группу? (y/n): ",
    "console_ask_reset": "ТОЧНО сбросить прогресс? Напиши RESET: ",
    "console_user_not_found": "Пользователь пока не найден в базе.",
    "console_user_name": "\nИмя: {name}",
    "console_user_messages": "Сообщений: {count}",
    "console_user_rank": "Ранг: {rank}",
    "console_user_next": "Следующий: {next_rank}",
    "console_user_remaining": "До повышения: {remaining}",
    "console_add_positive": "Количество должно быть больше нуля.",
    "console_add_done": "Готово: {old} -> {new}. Ранг: {rank}",
    "console_card_sent": "Карточка отправлена.",
    "console_no_rank": "Такого ранга нет.",
    "console_rank_set": "Ранг установлен: {rank} (сообщений: {messages})",
    "console_reset_done": "Прогресс сброшен.",
    "console_cancelled": "Отменено.",
    "console_top_empty": "В этой группе пока нет статистики.",
    "console_top_line": "{place:2}. {name} | {messages} | {rank}",
    "console_test_card_sent": "Тестовая карточка отправлена.",
    "console_ranks_line": "{number:2}. {rank}: {low}-{high} сообщений",
    "console_unknown": "Неизвестная команда.",
    "ask_int_invalid": "Нужно ввести целое число.",
    "startup_admin_missing": (
        "Внимание: ADMIN_IDS не задан — Telegram-админка отключена."
    ),
    "startup_errors_missing": (
        "Внимание: ADMIN_IDS/ERROR_REPORT_IDS не задан — "
        "отчёты об ошибках в Telegram отключены."
    ),
    "startup_no_groups": (
        "Внимание: белый список групп пуст — бот не обслуживает группы. "
        "Добавьте группу командой /agroup add."
    ),
    "startup_started": "CPU Evolution Bot запущен. Для остановки нажми Ctrl+C.",
    "menu_title": "CPU EVOLUTION BOT",
    "menu_start_bot": "[1] Запустить Telegram-бота",
    "menu_console": "[2] Открыть консоль тестирования",
    "menu_exit": "[0] Выход",
    "menu_choice": "Выбор: ",
}
