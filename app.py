# app.py

from flask import Flask, render_template, request, redirect, url_for
import asyncio
import discord_bot  # наш файл с логикой бота

app = Flask(__name__)
app.secret_key = "SOME_RANDOM_SECRET_KEY"

# ---------- Фильтр для отображения даты (Jinja2) ----------
@app.template_filter("datetimeformat")
def datetimeformat(value, fmt="%Y-%m-%d %H:%M:%S UTC"):
    """Фильтр, чтобы красиво форматировать msg.created_at в шаблонах."""
    if not value:
        return ""
    return value.strftime(fmt)

# ---------- Хелпер для вызова корутин в event_loop бота ----------
def run_coroutine(coro):
    """Выполняет корутину в loop бота и возвращает результат."""
    if not discord_bot.loop:
        return None
    future = asyncio.run_coroutine_threadsafe(coro, discord_bot.loop)
    return future.result()

# ---------- Маршруты Flask ----------

@app.route("/", methods=["GET", "POST"])
def index():
    """Главная страница: ввод токена бота."""
    if request.method == "POST":
        token = request.form.get("bot_token", "").strip()
        if token:
            discord_bot.start_bot_thread(token)
            return redirect(url_for("guilds_page"))
    return render_template("index.html")

@app.route("/guilds")
def guilds_page():
    """Список гильдий, где присутствует бот."""
    guild_list = discord_bot.get_guilds()  # [(id, name), ...]
    return render_template("guilds.html", guilds=guild_list)

@app.route("/guild/<int:guild_id>/channels")
def channels_page(guild_id):
    """Иерархический список каналов для выбранного сервера."""
    g = discord_bot.get_guild(guild_id)
    if not g:
        return "Guild not found", 404
    struct = discord_bot.get_channel_structure(g)
    return render_template("channels.html", guild=g, struct=struct)

@app.route("/guild/<int:guild_id>/channel/<int:channel_id>")
def channel_view(guild_id, channel_id):
    """
    Просмотр канала:
    Если Text/News/Thread -> список сообщений (новые внизу).
    Если Forum -> список тредов.
    Если Voice/Stage -> пусто.
    """
    limit = int(request.args.get("limit", 10))
    result = run_coroutine(discord_bot.fetch_channel_messages(guild_id, channel_id, limit))
    # result = {"type": "...", "messages": [...], "threads": [...]}

    return render_template(
        "channel_view.html",
        guild_id=guild_id,
        channel_id=channel_id,
        channel_type=result["type"],
        messages=result["messages"],
        threads=result["threads"],
        limit=limit
    )

@app.route("/guild/<int:guild_id>/channel/<int:channel_id>/send", methods=["POST"])
def channel_send(guild_id, channel_id):
    """Отправка сообщения в канал."""
    content = request.form.get("content", "")
    if content:
        run_coroutine(discord_bot.send_message(guild_id, channel_id, content))
    return redirect(url_for("channel_view", guild_id=guild_id, channel_id=channel_id))

@app.route("/guild/<int:guild_id>/members")
def members_page(guild_id):
    """Список участников."""
    g = discord_bot.get_guild(guild_id)
    if not g:
        return "Guild not found"
    m_list = discord_bot.get_members(guild_id)
    return render_template("members.html", guild=g, members=m_list)

@app.route("/guild/<int:guild_id>/roles")
def roles_page(guild_id):
    """Список ролей (сверху вниз)."""
    g = discord_bot.get_guild(guild_id)
    if not g:
        return "Guild not found"
    r_list = discord_bot.get_roles(guild_id)
    return render_template("roles.html", guild=g, roles=r_list)

PERMISSIONS_DICT = {
    "administrator":           "Администратор",
    "create_instant_invite":  "Создавать пригл.",
    "kick_members":           "Кикать участников",
    "ban_members":            "Банить участников",
    "manage_channels":        "Управлять каналами",
    "manage_guild":           "Управлять сервером",
    "view_audit_log":         "Просматривать аудит",
    "send_messages":          "Отправлять сообщения",
    "manage_messages":        "Управлять сообщениями",
    "embed_links":            "Встраивать ссылки",
    "attach_files":           "Прикреплять файлы",
    "mention_everyone":       "Упоминать everyone",
    "read_message_history":   "Читать историю",
    "manage_roles":           "Управлять ролями",
    # ... при желании можно добавить остальное
}

@app.route("/guild/<int:guild_id>/role/<int:role_id>/edit", methods=["GET", "POST"])
def role_edit_page(guild_id, role_id):
    """Интерактивное редактирование прав роли."""
    g = discord_bot.get_guild(guild_id)
    if not g:
        return "Guild not found"
    role_obj = g.get_role(role_id)
    if not role_obj:
        return "Role not found"

    if request.method == "POST":
        updated_flags = {}
        for flag, label in PERMISSIONS_DICT.items():
            val = request.form.get(flag, "off")
            updated_flags[flag] = (val == "on")
        run_coroutine(discord_bot.role_edit_permissions(guild_id, role_id, updated_flags))
        return redirect(url_for("roles_page", guild_id=guild_id))

    current_perms = role_obj.permissions
    current_flags = {}
    for name, value in current_perms:
        current_flags[name] = value

    return render_template(
        "role_edit.html",
        guild=g, 
        role=role_obj,
        permissions_dict=PERMISSIONS_DICT,
        current_flags=current_flags
    )

@app.route("/guild/<int:guild_id>/kick", methods=["POST"])
def guild_kick(guild_id):
    """Кик участника."""
    user_id = int(request.form.get("user_id", "0"))
    reason = request.form.get("reason", "")
    run_coroutine(discord_bot.kick_member(guild_id, user_id, reason))
    return redirect(url_for("members_page", guild_id=guild_id))

@app.route("/guild/<int:guild_id>/ban", methods=["POST"])
def guild_ban(guild_id):
    """Бан участника."""
    user_id = int(request.form.get("user_id", "0"))
    reason = request.form.get("reason", "")
    run_coroutine(discord_bot.ban_member(guild_id, user_id, reason))
    return redirect(url_for("members_page", guild_id=guild_id))

@app.route("/guild/<int:guild_id>/unban", methods=["POST"])
def guild_unban(guild_id):
    """Разбан участника."""
    user_id = int(request.form.get("user_id", "0"))
    run_coroutine(discord_bot.unban_member(guild_id, user_id))
    return redirect(url_for("members_page", guild_id=guild_id))

@app.route("/guild/<int:guild_id>/audit")
def audit_page(guild_id):
    """Журнал аудита."""
    limit = int(request.args.get("limit", 50))
    entries = run_coroutine(discord_bot.fetch_audit_log(guild_id, limit))
    return render_template("audit.html", guild_id=guild_id, entries=entries)

if __name__ == "__main__":
    # Запуск веб-приложения Flask
    app.run(host="0.0.0.0", port=5000, debug=True)
