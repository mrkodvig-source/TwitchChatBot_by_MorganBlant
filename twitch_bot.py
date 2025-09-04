import asyncio
import ssl
import time

class TwitchBot:
    """
    Простой асинхронный Twitch IRC бот (через TLS на irc.chat.twitch.tv:6697).
    Параметры:
      - username: логин аккаунта (без #)
      - oauth_token: строка вида "oauth:..." (обязательно включать oauth:)
      - proxy: не реализован в этом примере (оставлен для совместимости)
      - channel: имя канала (без #)
    """
    def __init__(self, username, oauth_token, proxy=None, channel='your_channel'):
        self.username = username
        self.oauth_token = oauth_token
        self.proxy = proxy
        self.channel = channel.lstrip('#')
        self.connected = False

        self.reader = None
        self.writer = None
        self._read_task = None
        self._send_lock = asyncio.Lock()
        self._last_sent = 0.0
        # минимальная пауза между сообщениями от одного аккаунта (чтобы избегать мгновенных банов)
        self._min_interval = 1.6

    async def connect(self):
        """
        Подключаемся к Twitch IRC через TLS.
        Не реализуем SOCKS/HTTP proxy в этом примере (для этого нужен дополнительный модуль).
        """
        if self.connected:
            return

        host = 'irc.chat.twitch.tv'
        port = 6697

        sslctx = ssl.create_default_context()
        try:
            self.reader, self.writer = await asyncio.open_connection(host=host, port=port, ssl=sslctx)
        except Exception as e:
            raise RuntimeError(f"Не удалось открыть соединение: {e}")

        # Авторизация
        # oauth токен должен быть в формате "oauth:..."
        auth_pass = self.oauth_token
        if not auth_pass.lower().startswith("oauth:"):
            raise ValueError("oauth_token должен начинаться с 'oauth:'")

        self._write(f"PASS {auth_pass}")
        self._write(f"NICK {self.username}")
        self._write(f"JOIN #{self.channel}")

        # запустим чтение сообщений в фоне
        self._read_task = asyncio.create_task(self._read_loop())
        # небольшая пауза, чтобы получить ответ сервера
        await asyncio.sleep(0.5)
        self.connected = True

    async def _read_loop(self):
        try:
            while True:
                line = await self.reader.readline()
                if not line:
                    break
                text = line.decode(errors='ignore').rstrip('\r\n')
                # Обработка PING
                if text.startswith("PING"):
                    # отправляем PONG
                    self._write("PONG :tmi.twitch.tv")
                # тут можно добавить разбор сообщений, если нужно
        except asyncio.CancelledError:
            # отмена чтения при закрытии
            pass
        except Exception:
            pass
        finally:
            self.connected = False

    def _write(self, data: str):
        if self.writer is None:
            return
        try:
            self.writer.write((data + "\r\n").encode())
        except Exception:
            pass

    async def send_message(self, message: str):
        """
        Отправка сообщения в чат. Проводится простая локальная проверка интервала между сообщениями.
        """
        if not self.connected or self.writer is None:
            raise RuntimeError("Бот не подключен")

        async with self._send_lock:
            now = time.time()
            wait = self._min_interval - (now - self._last_sent)
            if wait > 0:
                await asyncio.sleep(wait)
            # Команда для отправки в чат
            msg = f"PRIVMSG #{self.channel} :{message}"
            self._write(msg)
            try:
                await self.writer.drain()
            except Exception:
                pass
            self._last_sent = time.time()

    async def close(self):
        """
        Закрытие соединения корректно.
        """
        self.connected = False
        try:
            if self._read_task:
                self._read_task.cancel()
                try:
                    await self._read_task
                except asyncio.CancelledError:
                    pass
            if self.writer:
                try:
                    # выход из канала и закрытие
                    self._write(f"PART #{self.channel}")
                    await asyncio.sleep(0.05)
                    self.writer.close()
                    await self.writer.wait_closed()
                except Exception:
                    pass
        finally:
            self.reader = None
            self.writer = None
            self._read_task = None