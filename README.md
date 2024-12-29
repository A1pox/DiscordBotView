# Discord Bot View

## Описание

**Discord Bot View**— это консольное и веб-приложение для управления сервером Discord через API бота. Приложение поддерживает просмотр каналов, сообщений, участников, ролей, управление тредами и правами, а также отправку сообщений.

Проект разработан на основе библиотеки `discord.py` и фреймворка `Flask`.

---

## Возможности

- **Просмотр структуры серверов:**
  - Иерархический вывод категорий и каналов.
  - Поддержка всех основных типов каналов (текстовые, голосовые, и др.).
- **Работа с сообщениями:**
  - Просмотр сообщений.
  - Отправка сообщений в текстовые каналы.
- **Управление пользователями:**
  - Просмотр участников.
  - Кик и бан участников.
- **Управление ролями:**
  - Просмотр списка ролей.
  - Изменение прав ролей.
- **Просмотр журнала аудита:**.

---

## Установка

### 1 Клонирование репозитория
```bash
# Клонируйте проект
git clone https://github.com/A1pox/DiscordBotNet.git
cd DiscordBotManager
```

### 2 Активация виртуального окружения
- **Windows:**
  ```bash
  venv\Scripts\activate
  ```
- **Linux/MacOS:**
  ```bash
  source venv/bin/activate
  ```

### 3 апуск приложения
```bash
python app.py
```

После запуска откройте браузер и перейдите по адресу: [http://127.0.0.1:5000](http://127.0.0.1:5000)

---

## Использование

1. Введите токен бота на главной странице для авторизации.
2. После авторизации доступны:
   - Просмотр серверов и их структуры.
   - Просмотр сообщений в каналах.
   - Управление участниками и ролями.
   - Управление сообщениями и каналами.

---

## Требования

- Python 3.10+
- Активированные необходимые интенты для бота в Discord Developer Portal:
  - **Message Content Intent**
  - **Server Members Intent**

---

## Лицензия

Этот проект распространяется под лицензией [MIT](https://opensource.org/licenses/MIT). Вы можете свободно использовать, модифицировать и распространять проект при сохранении авторства.
