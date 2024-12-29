# discord_bot.py

import disnake as discord
import asyncio
import threading
from datetime import datetime

# Глобальные переменные
discord_client = None
bot_thread = None
loop = None

# Настройки интентов
intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.messages = True
intents.message_content = True

def now_str():
    """Возвращает текущее время в понятном формате."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

class MyDiscordClient(discord.Client):
    async def on_ready(self):
        print(f"[{now_str()}] Бот авторизовался как {self.user} (ID: {self.user.id})")

# ================== Утилиты ==================

def get_guilds():
    """Список (id, name) для всех гильдий бота."""
    if not discord_client:
        return []
    return [(g.id, g.name) for g in discord_client.guilds]

def get_guild(guild_id: int):
    """Безопасно найти Guild по ID."""
    if not discord_client:
        return None
    return discord_client.get_guild(guild_id)

def channel_type_str(ch: discord.abc.GuildChannel) -> str:
    t = ch.type
    if t == discord.ChannelType.text:
        return "Text"
    elif t == discord.ChannelType.news:
        return "News"
    elif t == discord.ChannelType.forum:
        return "Forum"
    elif t == discord.ChannelType.voice:
        return "Voice"
    elif t == discord.ChannelType.stage_voice:
        return "Stage"
    elif t == discord.ChannelType.public_thread:
        return "Public Thread"
    elif t == discord.ChannelType.private_thread:
        return "Private Thread"
    elif t == discord.ChannelType.news_thread:
        return "News Thread"
    elif t == discord.ChannelType.category:
        return "Category"
    elif t == discord.ChannelType.store:
        return "Store"
    else:
        print(f"[DEBUG] Неизвестный тип канала: {t} (значение: {t.value})")
        return f"Unknown (val={t.value})"



def get_channel_structure(guild: discord.Guild):
    """
    Структура каналов с учётом категорий:
    [
      {
        "category": "cat.name",
        "category_id": cat.id,
        "channels": [
          {"name": "...", "id": ..., "type": "..."},
          ...
        ]
      },
      ...
      { "category": None, "channels": [ ... ] }  # Orphan channels
    ]
    """
    if not guild:
        return []

    categories = sorted(guild.categories, key=lambda c: c.position)
    result = []

    # Сначала категории
    for cat in categories:
        cat_dict = {
            "category": cat.name,
            "category_id": cat.id,
            "channels": []
        }
        child_channels = sorted(cat.channels, key=lambda c: c.position)
        for ch in child_channels:
            cat_dict["channels"].append({
                "name": ch.name,
                "id": ch.id,
                "type": channel_type_str(ch),
                "position": ch.position
            })
        result.append(cat_dict)

    # Каналы без категории
    orphans = [
        ch for ch in guild.channels
        if ch.category is None and ch.type != discord.ChannelType.category
    ]
    if orphans:
        orphans_sorted = sorted(orphans, key=lambda c: c.position)
        orphans_dict = {
            "category": None,
            "channels": []
        }
        for ch in orphans_sorted:
            orphans_dict["channels"].append({
                "name": ch.name,
                "id": ch.id,
                "type": channel_type_str(ch),
                "position": ch.position
            })
        result.append(orphans_dict)

    return result

# ============ ЛОГИКА ЧТЕНИЯ СООБЩЕНИЙ (TEXT, NEWS, FORUM) ============

async def fetch_channel_messages(guild_id: int, channel_id: int, limit=10):
    """
    Получает последние limit сообщений, если это text/news/thread.
    Если это forum – возвращает список тредов.
    Voice/Stage/Category -> пусто.
    Возвращаем dict:
    {
      "type": "Text"/"News"/"Forum"/"Voice"/...,
      "messages": [discord.Message, ...],  # если text-like
      "threads": [ { "id":..., "name":... }, ... ]  # если forum
    }
    """
    guild = get_guild(guild_id)
    if not guild:
        return {"type": "unknown", "messages": [], "threads": []}

    ch = guild.get_channel(channel_id)
    if not ch:
        return {"type": "unknown", "messages": [], "threads": []}

    t = ch.type

    # Обычные текстовые / новостные
    if t in (discord.ChannelType.text, discord.ChannelType.news):
        messages = []
        try:
            async for msg in ch.history(limit=limit):
                messages.append(msg)
            messages.reverse()  # Переворачиваем, чтобы старые были сверху
        except Exception as e:
            print(f"Ошибка при получении сообщений: {e}")
        return {
            "type": channel_type_str(ch),
            "messages": messages,
            "threads": []
        }

    # Форум — возвращаем список активных тредов
    if t == discord.ChannelType.forum:
        data = {
            "type": "Forum",
            "messages": [],
            "threads": []
        }
        # Получаем список активных тредов
        for thread in ch.threads:
            data["threads"].append({
                "id": thread.id,
                "name": thread.name
            })
        return data

    # Треды (public_thread, private_thread, news_thread)
    if t in (
        discord.ChannelType.public_thread,
        discord.ChannelType.private_thread,
        discord.ChannelType.news_thread
    ):
        messages = []
        try:
            async for msg in ch.history(limit=limit):
                messages.append(msg)
            messages.reverse()  # Переворачиваем, чтобы старые были сверху
        except Exception as e:
            print(f"Ошибка при получении сообщений: {e}")
        return {
            "type": channel_type_str(ch),
            "messages": messages,
            "threads": []
        }

    # Voice / Stage / Category / Unknown -> пустая выдача
    return {
        "type": channel_type_str(ch),
        "messages": [],
        "threads": []
    }



# ============ ОТПРАВКА СООБЩЕНИЙ ============

async def send_message(guild_id, channel_id, content):
    guild = get_guild(guild_id)
    if not guild:
        return False
    channel = guild.get_channel(channel_id)
    if not channel:
        return False

    # Разрешим отправку только в text/news/thread
    allowed_types = (
        discord.ChannelType.text,
        discord.ChannelType.news,
        discord.ChannelType.public_thread,
        discord.ChannelType.private_thread,
        discord.ChannelType.news_thread
    )
    if channel.type not in allowed_types:
        return False

    try:
        await channel.send(content)
        return True
    except:
        return False

# ============ УЧАСТНИКИ, РОЛИ, МОДЕРАЦИЯ ============

def get_members(guild_id):
    guild = get_guild(guild_id)
    if not guild:
        return []
    data = []
    for m in guild.members:
        data.append((m.id, f"{m.display_name} ({m.name}#{m.discriminator})"))
    return data

def get_roles(guild_id):
    guild = get_guild(guild_id)
    if not guild:
        return []
    roles = sorted(guild.roles, key=lambda r: r.position, reverse=True)
    return [(r.id, r.name, r.position) for r in roles]

async def role_edit_permissions(guild_id, role_id, updated_perms: dict):
    guild = get_guild(guild_id)
    if not guild:
        return False
    role = guild.get_role(role_id)
    if not role:
        return False

    current_perms = role.permissions
    new_perms = discord.Permissions()

    # Копируем всё, что было:
    for name, val in current_perms:
        setattr(new_perms, name, val)

    # Применяем изменения
    for flag, boolean in updated_perms.items():
        setattr(new_perms, flag, boolean)

    try:
        await role.edit(permissions=new_perms)
        return True
    except:
        return False

async def give_role_to_members(guild_id, role_id, member_ids):
    guild = get_guild(guild_id)
    if not guild:
        return []
    role = guild.get_role(role_id)
    if not role:
        return []
    results = []
    for mid in member_ids:
        member = guild.get_member(mid)
        if not member:
            results.append((mid, False, "Member not found"))
            continue
        try:
            await member.add_roles(role)
            results.append((mid, True, "Success"))
        except Exception as e:
            results.append((mid, False, str(e)))
    return results

async def kick_member(guild_id, user_id, reason=None):
    guild = get_guild(guild_id)
    if not guild:
        return (False, "Guild not found")
    member = guild.get_member(user_id)
    if not member:
        return (False, "Member not found")
    try:
        await member.kick(reason=reason)
        return (True, "Kicked")
    except Exception as e:
        return (False, str(e))

async def ban_member(guild_id, user_id, reason=None):
    guild = get_guild(guild_id)
    if not guild:
        return (False, "Guild not found")
    member = guild.get_member(user_id)
    if not member:
        return (False, "Member not found")
    try:
        await member.ban(reason=reason)
        return (True, "Banned")
    except Exception as e:
        return (False, str(e))

async def unban_member(guild_id, user_id):
    guild = get_guild(guild_id)
    if not guild:
        return (False, "Guild not found")
    try:
        bans = await guild.bans()
        user_to_unban = None
        for ban_entry in bans:
            if ban_entry.user.id == user_id:
                user_to_unban = ban_entry.user
                break
        if not user_to_unban:
            return (False, "Not in ban list")
        await guild.unban(user_to_unban)
        return (True, "Unbanned")
    except Exception as e:
        return (False, str(e))

async def fetch_audit_log(guild_id, limit=50):
    guild = get_guild(guild_id)
    if not guild:
        return []
    try:
        entries = []
        async for entry in guild.audit_logs(limit=limit):
            entries.append(entry)
        return entries
    except:
        return []

# ============ Запуск бота в отдельном потоке ============

def run_bot(token: str):
    global loop, discord_client
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    discord_client = MyDiscordClient(intents=intents)
    try:
        loop.run_until_complete(discord_client.start(token))
    except KeyboardInterrupt:
        loop.run_until_complete(discord_client.close())
    except Exception as e:
        print("[!] Ошибка при запуске бота:", e)
    finally:
        loop.close()

def start_bot_thread(token: str):
    global bot_thread
    if bot_thread and bot_thread.is_alive():
        print("[i] Бот уже запущен.")
        return
    bot_thread = threading.Thread(target=run_bot, args=(token,), daemon=True)
    bot_thread.start()
    print("[i] Поток бота запущен.")
