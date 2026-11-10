"""English UI strings.

Placeholders use ``str.format`` syntax; values are inserted by ``i18n.t``.
Keep the same keys as locales/ru.py.
"""

STRINGS = {
    # --- rank card (drawn with Pillow) ---
    "card_rank_label": "PROCESSOR RANK",
    "card_gen": "GEN {number:02d}",
    "card_messages": "{messages} MESSAGES",
    "card_progress_label": "EVOLUTION PROGRESS",
    "card_next": "{progress}%  |  NEXT: {next_rank}",
    "card_max": "{progress}%  |  MAXIMUM RANK",
    "card_footer": "100 MESSAGES = 1 EVOLUTION",
    "card_default_name": "Telegram user",

    # --- public commands ---
    "start_text": (
        "Hi! I am CPU Evolution Bot.\n\n"
        "/profile — your processor card\n"
        "/rank — text info about your rank\n"
        "/top — group top 10\n"
        "/help — all commands\n\n"
        "To view another member's profile, reply to their message with /profile."
    ),
    "profile_group_only": "Profiles are available in groups only.",
    "user_not_determined": "Could not determine the user.",
    "group_only": "This command works in groups only.",
    "profile_caption": (
        "🖥 <b>CPU Evolution profile</b>\n"
        "👤 {name}\n"
        "⚙️ Rank: <b>{rank}</b>\n"
        "📨 Messages: <b>{messages}</b>"
    ),
    "rank_up_caption": (
        "🚀 <b>Processor rank up!</b>\n"
        "👤 {name}\n"
        "🖥 New level: <b>{rank}</b>\n"
        "📨 Messages: <b>{messages}</b>"
    ),
    "rank_up_final": "🏆 <b>Threadripper reached!</b>",
    "rank_text": (
        "🖥 <b>{name}</b>\n"
        "⚙️ Rank: <b>{rank}</b>\n"
        "📨 Messages: <b>{count}</b>\n"
    ),
    "rank_next": (
        "🚀 Next: <b>{next_rank}</b>\n"
        "Until rank up: <b>{remaining}</b>"
    ),
    "rank_max": "🏆 Maximum rank reached!",
    "id_text": "Chat ID: <code>{chat_id}</code>\nUser ID: <code>{user_id}</code>",
    "id_unknown": "not determined",
    "top_empty": "No stats yet.",
    "top_header": "🏆 <b>CPU EVOLUTION TOP</b>\n",
    "top_line": "{place}. {name} — <b>{rank}</b> ({messages} messages)",
    "atop_empty": "No stats in this chat yet.",
    "atop_header": "🏆 <b>CPU EVOLUTION TOP</b> (<code>{chat_id}</code>)\n",
    "atop_line": "{place:2}. {name} — <b>{rank}</b> ({messages})",
    "public_help": (
        "🤖 <b>CPU Evolution Bot</b>\n\n"
        "/profile — processor rank card\n"
        "/rank — text info about your rank\n"
        "/top — group top 10\n"
        "/id — Chat ID and User ID\n"
        "/help — this help\n\n"
        "Another member's profile: reply to their message with /profile.\n"
        "Profiles and top work in groups."
    ),

    # --- admin commands ---
    "admin_usage": (
        "In a group, reply to a member's message and pass only the parameters.\n"
        "Without a reply, pass the Telegram user ID as the first parameter.\n"
        "In DM, pass the group chat ID first, then the user ID."
    ),
    "admin_help": (
        "🛠 <b>CPU Evolution admin commands</b>\n\n"
        "{usage}\n\n"
        "/auser — member stats\n"
        "/aadd &lt;N&gt; — add N messages\n"
        "/asetrank &lt;number&gt; — set rank (see /aranks)\n"
        "/areset confirm — reset progress\n"
        "/acard — send a test card\n"
        "/aranks — list ranks\n"
        "/atop — top 20 (in DM pass chat_id)\n"
        "/agroup add|del|list — group whitelist\n"
        "/top — group top 10\n\n"
        "In a group, chat_id may be omitted for /agroup add and /agroup del —\n"
        "the current chat is used.\n\n"
        "Your Telegram ID: <code>{user_id}</code>"
    ),
    "admin_dm_only": "The admin command list is available in DM with the bot only.",
    "admin_usage_error": "⚠️ {error}\n\n{usage}",
    "admin_target_private": "In DM, pass chat_id and user_id.",
    "admin_target_group": "Reply to a member's message or pass a user_id.",
    "admin_group_id_negative": "Group chat_id must be a negative number.",
    "admin_group_id_private": "In DM, pass the group chat_id.",
    "admin_default_name": "User {user_id}",
    "label_chat_id": "chat_id",
    "label_user_id": "user_id",
    "label_amount": "Amount",
    "label_rank_number": "Rank number",
    "parse_int_invalid": "{label}: an integer is required.",
    "parse_int_too_large": "{label}: the number is too large.",
    "auser_not_found": (
        "User <code>{user_id}</code> was not found in the database of chat "
        "<code>{chat_id}</code>."
    ),
    "auser_text": (
        "👤 <b>{name}</b> (<code>{user_id}</code>)\n"
        "⚙️ Rank: <b>{rank}</b>\n"
        "📨 Messages: <b>{count}</b>"
    ),
    "auser_next": (
        "\n🚀 Next: <b>{next_rank}</b>"
        "\nUntil rank up: <b>{remaining}</b>"
    ),
    "auser_max": "\n🏆 Maximum rank reached!",
    "aadd_need_amount": "Specify the number of messages.",
    "aadd_positive": "The number must be greater than zero.",
    "aadd_too_big": "Too many messages (maximum {max_messages}).",
    "aadd_done": (
        "✅ <b>{name}</b>: {old} → <b>{new}</b> messages\n"
        "⚙️ Rank: <b>{rank}</b>"
    ),
    "asetrank_need": "Specify a rank number from 1 to {ranks_count}.",
    "asetrank_range": "The rank must be from 1 to {ranks_count}.",
    "asetrank_done": (
        "✅ <b>{name}</b>: rank <b>{rank}</b> (messages: {messages})"
    ),
    "areset_confirm": (
        "⚠️ Reset will wipe <b>{name}</b>'s progress. "
        "Repeat the command with <code>confirm</code>."
    ),
    "areset_done": "♻️ Progress reset: {old} → <b>0</b>.",
    "acard_sent": "✅ Test card sent.",
    "aranks_header": "🖥 <b>CPU Evolution ranks</b>",
    "aranks_line": "{number:2}. {rank} — {low}-{high} messages",
    "aranks_beyond": "🏆 {beyond_rank} — from {threshold} messages",

    # --- group whitelist ---
    "agroup_help": (
        "🛠 <b>Group whitelist</b>\n\n"
        "/agroup add &lt;chat_id&gt; — add a group\n"
        "/agroup del &lt;chat_id&gt; — remove a group\n"
        "/agroup list — show the list\n\n"
        "In a group, chat_id may be omitted — the current chat is used."
    ),
    "agroup_empty": (
        "📋 The whitelist is empty — the bot serves no groups.\n"
        "Add a group: /agroup add in the group itself "
        "or /agroup add &lt;chat_id&gt; in DM."
    ),
    "agroup_header": "📋 <b>Group whitelist</b>\n",
    "agroup_no_title": "untitled",
    "agroup_line": "• {title} — <code>{chat_id}</code>",
    "agroup_unknown_action": "⚠️ Use /agroup add, /agroup del or /agroup list.",
    "agroup_error": "⚠️ {error}",
    "agroup_added": "✅ Group <code>{chat_id}</code> added to the whitelist.",
    "agroup_removed": "🗑 Group <code>{chat_id}</code> removed from the whitelist.",
    "agroup_not_found": "Group <code>{chat_id}</code> was not found in the whitelist.",
    "blocked_notice": (
        "⚠️ The bot is not enabled for this chat. "
        "The bot administrator can enable it for this group."
    ),

    # --- error reports and logs ---
    "error_report_header": (
        "🚨 <b>Error in CPU Evolution Bot</b>\n"
        "🕒 <code>{stamp}</code>\n"
        "{context}\n\n"
    ),
    "fatal_report_header": (
        "🚨 <b>Critical error in CPU Evolution Bot</b>\n"
        "🕒 <code>{stamp}</code>\n"
        "The bot is restarting polling.\n\n"
    ),
    "log_report_send_failed": (
        "Failed to send the error report to {admin_id}: {error}"
    ),
    "log_unhandled": "Unhandled error",
    "log_report_failed": "Failed to send the error report",
    "log_polling_error": "Polling error",
    "log_fatal_send_failed": "Failed to send the critical error",
    "retry_polling": "Restarting polling in {seconds} seconds...",

    # --- console admin mode ---
    "token_missing": "BOT_TOKEN not found. Fill in .env.",
    "console_title": "          CPU EVOLUTION CONSOLE",
    "console_menu_find": "[1] Find a user",
    "console_menu_add": "[2] Add messages (with rank-up announcement)",
    "console_menu_setrank": "[3] Set rank manually",
    "console_menu_reset": "[4] Reset progress",
    "console_menu_top": "[5] Show group top",
    "console_menu_card": "[6] Send a test card",
    "console_menu_ranks": "[7] Show the rank list",
    "console_menu_exit": "[0] Exit",
    "console_choose": "\nChoose an action: ",
    "console_ask_chat": "Group chat ID: ",
    "console_ask_user": "Telegram user ID: ",
    "console_ask_amount": "How many messages to add: ",
    "console_ask_rank": "Rank number: ",
    "console_ask_card": "Send the new rank card to the group? (y/n): ",
    "console_ask_card_plain": "Send the card to the group? (y/n): ",
    "console_ask_reset": "REALLY reset progress? Type RESET: ",
    "console_user_not_found": "User not found in the database yet.",
    "console_user_name": "\nName: {name}",
    "console_user_messages": "Messages: {count}",
    "console_user_rank": "Rank: {rank}",
    "console_user_next": "Next: {next_rank}",
    "console_user_remaining": "Until rank up: {remaining}",
    "console_add_positive": "The number must be greater than zero.",
    "console_add_done": "Done: {old} -> {new}. Rank: {rank}",
    "console_card_sent": "Card sent.",
    "console_no_rank": "No such rank.",
    "console_rank_set": "Rank set: {rank} (messages: {messages})",
    "console_reset_done": "Progress reset.",
    "console_cancelled": "Cancelled.",
    "console_top_empty": "No stats in this group yet.",
    "console_top_line": "{place:2}. {name} | {messages} | {rank}",
    "console_test_card_sent": "Test card sent.",
    "console_ranks_line": "{number:2}. {rank}: {low}-{high} messages",
    "console_unknown": "Unknown command.",
    "ask_int_invalid": "Please enter an integer.",
    "startup_admin_missing": (
        "Warning: ADMIN_IDS is not set — Telegram admin commands are disabled."
    ),
    "startup_errors_missing": (
        "Warning: ADMIN_IDS/ERROR_REPORT_IDS is not set — "
        "Telegram error reports are disabled."
    ),
    "startup_no_groups": (
        "Warning: the group whitelist is empty — the bot serves no groups. "
        "Add a group with /agroup add."
    ),
    "startup_started": "CPU Evolution Bot started. Press Ctrl+C to stop.",
    "menu_title": "CPU EVOLUTION BOT",
    "menu_start_bot": "[1] Start the Telegram bot",
    "menu_console": "[2] Open the test console",
    "menu_exit": "[0] Exit",
    "menu_choice": "Choice: ",
}
