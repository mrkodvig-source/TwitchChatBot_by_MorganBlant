import sys
import asyncio
import threading
import os
from PyQt6.QtWidgets import (
    QApplication, QWidget, QPushButton, QLineEdit, QLabel, QSlider,
    QFileDialog, QTextEdit, QVBoxLayout, QHBoxLayout, QMessageBox, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QObject
from twitch_bot import TwitchBot  # локальный файл twitch_bot.py

class LoggerSignal(QObject):
    log_signal = pyqtSignal(str)

class UIControlSignal(QObject):
    control_signal = pyqtSignal(dict)

logger_signal = LoggerSignal()
ui_control_signal = UIControlSignal()

class TwitchBotGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Twitch Bot — Modern UI")
        self.setGeometry(120, 120, 820, 560)

        self.accounts_file = None
        self.proxies_file = None
        self.phrases_file = None
        self.channel_name = ''
        self.delay = 30

        self.bots = []
        self.loop = None
        self.thread = None
        self.running = False

        self.init_ui()
        logger_signal.log_signal.connect(self.append_log)
        ui_control_signal.control_signal.connect(self.handle_control)

    def init_ui(self):
        # Основной layout
        layout = QVBoxLayout()
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        # Заголовок
        title = QLabel("Twitch Chat Bot")
        title.setStyleSheet("font-size:22px; font-weight:600; color: #ffffff;")
        layout.addWidget(title)

        # Поля
        # Имя канала
        h_channel = QHBoxLayout()
        h_channel.setSpacing(8)
        h_channel.addWidget(QLabel("<span style='color:#cfe8ff'>Имя канала:</span>"))
        self.channel_input = QLineEdit()
        self.channel_input.setPlaceholderText("Например: some_channel_name")
        h_channel.addWidget(self.channel_input)
        layout.addLayout(h_channel)

        # Выбор файла аккаунтов
        h_accounts = QHBoxLayout()
        self.accounts_btn = QPushButton("Выбрать файл аккаунтов")
        self.accounts_btn.clicked.connect(self.select_accounts_file)
        self.accounts_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.accounts_label = QLabel("Файл не выбран")
        self.accounts_label.setStyleSheet("color:#dfefff")
        h_accounts.addWidget(self.accounts_btn)
        h_accounts.addWidget(self.accounts_label)
        layout.addLayout(h_accounts)

        # Выбор файла прокси
        h_proxies = QHBoxLayout()
        self.proxies_btn = QPushButton("Выбрать файл прокси (опц.)")
        self.proxies_btn.clicked.connect(self.select_proxies_file)
        self.proxies_label = QLabel("Файл не выбран")
        self.proxies_label.setStyleSheet("color:#dfefff")
        h_proxies.addWidget(self.proxies_btn)
        h_proxies.addWidget(self.proxies_label)
        layout.addLayout(h_proxies)

        # Выбор файла с фразами
        h_phrases = QHBoxLayout()
        self.phrases_btn = QPushButton("Выбрать файл с фразами")
        self.phrases_btn.clicked.connect(self.select_phrases_file)
        self.phrases_label = QLabel("Файл не выбран")
        self.phrases_label.setStyleSheet("color:#dfefff")
        h_phrases.addWidget(self.phrases_btn)
        h_phrases.addWidget(self.phrases_label)
        layout.addLayout(h_phrases)

        # Ползунок задержки
        h_delay = QHBoxLayout()
        h_delay.addWidget(QLabel("<span style='color:#cfe8ff'>Задержка (сек):</span>"))
        self.delay_slider = QSlider(Qt.Orientation.Horizontal)
        self.delay_slider.setMinimum(1)
        self.delay_slider.setMaximum(120)
        self.delay_slider.setValue(30)
        self.delay_slider.valueChanged.connect(self.delay_changed)
        self.delay_label = QLabel("30")
        h_delay.addWidget(self.delay_slider)
        h_delay.addWidget(self.delay_label)
        layout.addLayout(h_delay)

        # Кнопки Старт / Стоп
        h_buttons = QHBoxLayout()
        h_buttons.setSpacing(12)
        self.start_btn = QPushButton("Старт")
        self.start_btn.clicked.connect(self.start_bots)
        self.stop_btn = QPushButton("Стоп")
        self.stop_btn.clicked.connect(self.stop_bots)
        self.stop_btn.setEnabled(False)
        for b in (self.start_btn, self.stop_btn):
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setMinimumHeight(38)
            b.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        h_buttons.addWidget(self.start_btn)
        h_buttons.addWidget(self.stop_btn)

        # Статус (цветной индикатор)
        self.status_label = QLabel("Отключено")
        self.status_label.setStyleSheet("color:#ffdddd; font-weight:600;")
        h_buttons.addStretch(1)
        h_buttons.addWidget(self.status_label)
        layout.addLayout(h_buttons)

        # Лог
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("""
            QTextEdit {
                background: rgba(255,255,255,0.06);
                border-radius: 10px;
                padding: 10px;
                color: #e8f6ff;
                font-family: Consolas, monospace;
                font-size: 12px;
            }
        """)
        layout.addWidget(self.log_text, stretch=1)

        self.setLayout(layout)

        # Применяем современный стиль к виджетам (градиентный фон, кнопки)
        # <-- УБРАНО: transform: translateY(-1px); (не поддерживается Qt)
        self.setStyleSheet("""
            QWidget {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 #0f1724, stop:0.5 #102033, stop:1 #032035
                );
                border-radius: 12px;
                color: #eaf7ff;
            }
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #3aa0ff, stop:1 #0066d6);
                border: none;
                color: white;
                padding: 8px 14px;
                border-radius: 8px;
                font-weight: 600;
            }
            QPushButton:disabled {
                background: rgba(255,255,255,0.08);
                color: rgba(255,255,255,0.4);
            }
            QPushButton:hover {
                /* Убрана transform (Qt не поддерживает). Добавлены тень и более светлый градиент */
                box-shadow: 0px 6px 18px rgba(0,0,0,0.45);
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #66baff, stop:1 #0078ff);
            }
            QLineEdit {
                background: rgba(255,255,255,0.04);
                border: 1px solid rgba(255,255,255,0.06);
                padding: 8px;
                border-radius: 8px;
                color: #eaf7ff;
            }
            QLabel { color: #dfefff; }
            QSlider::groove:horizontal {
                height: 6px;
                background: rgba(255,255,255,0.08);
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #ffffff;
                border: 2px solid #3aa0ff;
                width: 14px;
                margin: -5px 0;
                border-radius: 7px;
            }
        """)

    def append_log(self, text):
        # Печать лога (с автопрокруткой)
        self.log_text.append(text)
        self.log_text.verticalScrollBar().setValue(self.log_text.verticalScrollBar().maximum())

    def handle_control(self, data: dict):
        action = data.get('action')
        if action == 'started':
            self.status_label.setText("Запущено")
            self.status_label.setStyleSheet("color:#bfffe0; font-weight:700;")
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
        elif action == 'stopped':
            self.status_label.setText("Отключено")
            self.status_label.setStyleSheet("color:#ffbdbd; font-weight:700;")
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            self.running = False

    def select_accounts_file(self):
        fname, _ = QFileDialog.getOpenFileName(self, "Выберите файл аккаунтов", "", "Text Files (*.txt);;All Files (*)")
        if fname:
            self.accounts_file = fname
            self.accounts_label.setText(os.path.basename(fname))

    def select_proxies_file(self):
        fname, _ = QFileDialog.getOpenFileName(self, "Выберите файл прокси", "", "Text Files (*.txt);;All Files (*)")
        if fname:
            self.proxies_file = fname
            self.proxies_label.setText(os.path.basename(fname))

    def select_phrases_file(self):
        fname, _ = QFileDialog.getOpenFileName(self, "Выберите файл с фразами", "", "Text Files (*.txt);;All Files (*)")
        if fname:
            self.phrases_file = fname
            self.phrases_label.setText(os.path.basename(fname))

    def delay_changed(self, value):
        self.delay = value
        self.delay_label.setText(str(value))

    def start_bots(self):
        if self.running:
            QMessageBox.warning(self, "Внимание", "Боты уже запущены")
            return

        self.channel_name = self.channel_input.text().strip()
        if not self.channel_name:
            QMessageBox.warning(self, "Ошибка", "Введите имя канала")
            return
        if not self.accounts_file:
            QMessageBox.warning(self, "Ошибка", "Выберите файл аккаунтов")
            return
        if not self.phrases_file:
            QMessageBox.warning(self, "Ошибка", "Выберите файл с фразами")
            return

        self.running = True
        ui_control_signal.control_signal.emit({'action': 'started'})

        # Запуск в отдельном потоке, где будет выполняться свой asyncio loop
        self.thread = threading.Thread(target=self.run_asyncio_loop, daemon=True)
        self.thread.start()

    def stop_bots(self):
        if not self.running:
            return
        self.running = False
        # Попросим цикл остановиться
        if self.loop:
            try:
                self.loop.call_soon_threadsafe(self.loop.stop)
            except Exception:
                pass
        logger_signal.log_signal.emit("Остановка: остановлен флаг running (ожидаем завершения задач)")

    def run_asyncio_loop(self):
        # Windows selector policy for compatibility
        if sys.platform == 'win32':
            try:
                asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
            except Exception:
                pass
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        try:
            self.loop.run_until_complete(self.async_main())
        except Exception as e:
            logger_signal.log_signal.emit(f"Ошибка в asyncio loop: {e}")
        finally:
            # clean up UI через сигнал (в главном потоке)
            ui_control_signal.control_signal.emit({'action': 'stopped'})
            self.loop.close()

    async def async_main(self):
        # Чтение аккаунтов
        accounts = []
        try:
            with open(self.accounts_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or ';' not in line:
                        continue
                    username, oauth = line.split(';', 1)
                    accounts.append((username.strip(), oauth.strip()))
        except Exception as e:
            logger_signal.log_signal.emit(f"Ошибка чтения аккаунтов: {e}")
            return

        if not accounts:
            logger_signal.log_signal.emit("Нет аккаунтов в файле")
            return

        # Чтение прокси (не используется по умолчанию)
        proxies = []
        if self.proxies_file:
            try:
                with open(self.proxies_file, 'r', encoding='utf-8') as f:
                    proxies = [line.strip() for line in f if line.strip()]
            except Exception as e:
                logger_signal.log_signal.emit(f"Ошибка чтения прокси: {e}")

        # Чтение фраз
        messages = []
        try:
            with open(self.phrases_file, 'r', encoding='utf-8') as f:
                messages = [line.strip() for line in f if line.strip()]
        except Exception as e:
            logger_signal.log_signal.emit(f"Ошибка чтения фраз: {e}")
            return

        if not messages:
            logger_signal.log_signal.emit("Файл с фразами пуст")
            return

        # Создаем ботов
        self.bots = []
        for i, (username, oauth) in enumerate(accounts):
            proxy = proxies[i] if i < len(proxies) else None
            bot = TwitchBot(username, oauth, proxy=proxy, channel=self.channel_name)
            self.bots.append(bot)

        logger_signal.log_signal.emit(f"Запуск {len(self.bots)} ботов для канала #{self.channel_name}")

        # Подключение ботов
        for bot in self.bots:
            try:
                await bot.connect()
                logger_signal.log_signal.emit(f"{bot.username} подключен")
            except Exception as e:
                logger_signal.log_signal.emit(f"{bot.username} ошибка подключения: {e}")

        # Основной цикл отправки сообщений
        try:
            idx = 0
            while self.running:
                for i, bot in enumerate(self.bots):
                    if not self.running:
                        break
                    if not bot.connected:
                        try:
                            await bot.connect()
                            logger_signal.log_signal.emit(f"{bot.username} переподключен")
                        except Exception as e:
                            logger_signal.log_signal.emit(f"{bot.username} ошибка переподключения: {e}")
                            continue
                    msg = messages[idx % len(messages)]
                    try:
                        await bot.send_message(msg)
                        logger_signal.log_signal.emit(f"{bot.username} -> {msg}")
                    except Exception as e:
                        logger_signal.log_signal.emit(f"{bot.username} ошибка отправки: {e}")
                    idx += 1
                    await asyncio.sleep(self.delay)
        except asyncio.CancelledError:
            logger_signal.log_signal.emit("Основной цикл отменён")
        finally:
            # Отключаем ботов
            for bot in self.bots:
                try:
                    await bot.close()
                    logger_signal.log_signal.emit(f"{bot.username} отключен")
                except Exception:
                    pass
            logger_signal.log_signal.emit("Все боты остановлены")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = TwitchBotGUI()
    window.show()
    sys.exit(app.exec())