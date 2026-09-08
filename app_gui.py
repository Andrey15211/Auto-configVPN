import sys
import os
import re
import json
import urllib.request
import urllib.error
from io import BytesIO
from pathlib import Path
from typing import List, Dict
from datetime import datetime, timedelta

from PySide6.QtCore import Qt, QThread, Signal, QSize, QTimer
from PySide6.QtGui import QIcon, QPixmap, QImage, QFont, QColor, QDesktopServices
from PySide6.QtCore import QUrl
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTabWidget, QTableWidget,
    QTableWidgetItem, QHeaderView, QCheckBox, QGroupBox, QMessageBox,
    QFileDialog, QScrollArea, QFrame, QTextEdit, QSplitter, QComboBox
)

from scanner import scan_all_games
from catalog import RU_DIRECT_CATEGORIES
from pc_generator import (
    parse_any_source, parse_vless_link, generate_clash_yaml,
    deploy_to_clash_verge, get_clash_verge_paths
)
from mobile_generator import build_vless_uri, generate_singbox_json, generate_qr_image

# Dark Theme Stylesheet
MODERN_DARK_QSS = """
QMainWindow, QWidget {
    background-color: #0f131a;
    color: #e2e8f0;
    font-family: 'Segoe UI', sans-serif;
    font-size: 13px;
}

QGroupBox {
    border: 1px solid #232a3b;
    border-radius: 8px;
    margin-top: 14px;
    padding: 12px;
    font-weight: bold;
    color: #94a3b8;
    background-color: #151a24;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 0 4px;
}

QLineEdit {
    background-color: #1a2130;
    border: 1px solid #2c364d;
    border-radius: 6px;
    padding: 8px 12px;
    color: #f8fafc;
    selection-background-color: #3b82f6;
}
QLineEdit:focus {
    border: 1px solid #3b82f6;
    background-color: #1e2638;
}

QPushButton {
    background-color: #232c40;
    border: 1px solid #33405c;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 600;
    color: #f1f5f9;
}
QPushButton:hover {
    background-color: #2e3b55;
    border-color: #475569;
}
QPushButton:pressed {
    background-color: #1e2638;
}

QPushButton#btnPrimary {
    background-color: #2563eb;
    border: 1px solid #3b82f6;
    color: #ffffff;
    font-size: 14px;
    padding: 10px 20px;
}
QPushButton#btnPrimary:hover {
    background-color: #1d4ed8;
    border-color: #60a5fa;
}

QPushButton#btnSuccess {
    background-color: #059669;
    border: 1px solid #10b981;
    color: #ffffff;
    font-size: 14px;
    padding: 10px 20px;
}
QPushButton#btnSuccess:hover {
    background-color: #047857;
}

QTabWidget::pane {
    border: 1px solid #232a3b;
    border-radius: 8px;
    background-color: #131822;
    padding: 12px;
}
QTabBar::tab {
    background-color: #161c28;
    color: #94a3b8;
    border: 1px solid #232a3b;
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    padding: 10px 20px;
    margin-right: 4px;
    font-weight: bold;
}
QTabBar::tab:selected {
    background-color: #1e2638;
    color: #60a5fa;
    border-color: #3b82f6;
}
QTabBar::tab:hover:!selected {
    background-color: #1a2233;
    color: #cbd5e1;
}

QTableWidget {
    background-color: #131822;
    alternate-background-color: #181f2c;
    border: 1px solid #232a3b;
    border-radius: 6px;
    gridline-color: #232a3b;
    color: #f1f5f9;
}
QTableWidget::item {
    padding: 6px;
}
QTableWidget::item:selected {
    background-color: #2563eb;
    color: #ffffff;
}
QHeaderView::section {
    background-color: #1c2333;
    color: #94a3b8;
    font-weight: bold;
    padding: 8px;
    border: none;
    border-bottom: 1px solid #2d3748;
}

QCheckBox {
    spacing: 8px;
    color: #e2e8f0;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 1px solid #475569;
    background-color: #1a2233;
}
QCheckBox::indicator:checked {
    background-color: #2563eb;
    border-color: #3b82f6;
}

QScrollBar:vertical {
    background: #0f131a;
    width: 10px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: #2d3748;
    min-height: 20px;
    border-radius: 5px;
}
QScrollBar::handle:vertical:hover {
    background: #4a5568;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

QComboBox {
    background-color: #1a2130;
    border: 1px solid #2c364d;
    border-radius: 6px;
    padding: 6px 12px;
    color: #f8fafc;
    font-size: 13px;
}
QComboBox:hover {
    border-color: #3b82f6;
}
QComboBox::drop-down {
    border: none;
    width: 24px;
}
QComboBox QAbstractItemView {
    background-color: #161c28;
    border: 1px solid #2c364d;
    selection-background-color: #2563eb;
    color: #f8fafc;
    padding: 4px;
}
"""


APP_VERSION = "1.1.0"
GITHUB_REPO = "Andrey15211/Auto-configVPN"


class UpdateCheckerThread(QThread):
    update_available = Signal(str, str, str)  # tag, changelog, download_url
    check_finished = Signal(bool, str)        # found, message

    def __init__(self, manual: bool = False):
        super().__init__()
        self.manual = manual

    def run(self):
        try:
            url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Auto-configVPN-PC", "Accept": "application/vnd.github.v3+json"}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    tag = data.get("tag_name", "").lstrip("vV")
                    body = data.get("body", "")
                    assets = data.get("assets", [])
                    exe_asset = next(
                        (a["browser_download_url"] for a in assets if a.get("name", "").endswith(".exe")),
                        data.get("html_url", f"https://github.com/{GITHUB_REPO}/releases")
                    )

                    if self._is_newer(tag, APP_VERSION):
                        self.update_available.emit(tag, body, exe_asset)
                        self.check_finished.emit(True, f"Доступна новая версия v{tag}")
                    else:
                        self.check_finished.emit(False, "У вас установлена актуальная версия")
                elif resp.status == 404:
                    self.check_finished.emit(False, f"Релизов пока нет. У вас актуальная версия (v{APP_VERSION}).")
                else:
                    self.check_finished.emit(False, f"Ответ сервера: {resp.status}")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                self.check_finished.emit(False, f"Релизов пока нет. У вас актуальная версия (v{APP_VERSION}).")
            else:
                self.check_finished.emit(False, f"Ошибка проверки ({e.code})")
        except Exception as e:
            self.check_finished.emit(False, f"Не удалось проверить: {e}")

    def _is_newer(self, remote: str, current: str) -> bool:
        r_parts = [int(p) for p in re.findall(r"\d+", remote)]
        c_parts = [int(p) for p in re.findall(r"\d+", current)]
        max_l = max(len(r_parts), len(c_parts))
        r_parts += [0] * (max_l - len(r_parts))
        c_parts += [0] * (max_l - len(c_parts))
        return r_parts > c_parts


class ScannerThread(QThread):
    finished = Signal(list)

    def run(self):
        games = scan_all_games()
        self.finished.emit(games)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"Smart Split-Tunneling Wizard v{APP_VERSION} (ПК & Телефон)")
        self.resize(1020, 780)
        self.setMinimumSize(880, 650)
        self.setStyleSheet(MODERN_DARK_QSS)

        self.current_nodes: List[Dict] = []
        self.current_node: Dict = {}
        self.detected_games: List[Dict[str, str]] = []
        self.category_checkboxes: Dict[str, QCheckBox] = {}

        self._build_ui()
        self._start_scan()
        self._start_update_check(manual=False)
        self._schedule_periodic_update_check()

    def _schedule_periodic_update_check(self):
        """Schedule automatic update check twice a day: at 12:00 PM and 12:00 AM (midnight)."""
        now = datetime.now()
        if now.hour < 12:
            target = now.replace(hour=12, minute=0, second=0, microsecond=0)
        else:
            target = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)

        delay_ms = max(5000, int((target - now).total_seconds() * 1000))
        self.update_timer = QTimer(self)
        self.update_timer.setSingleShot(True)
        self.update_timer.timeout.connect(self._on_periodic_update_tick)
        self.update_timer.start(delay_ms)

    def _on_periodic_update_tick(self):
        self._start_update_check(manual=False)
        self._schedule_periodic_update_check()

    def _start_update_check(self, manual: bool = False):
        self.update_thread = UpdateCheckerThread(manual=manual)
        self.update_thread.update_available.connect(self._on_update_available)
        if manual:
            self.update_thread.check_finished.connect(self._on_manual_check_finished)
        self.update_thread.start()

    def _on_update_available(self, tag: str, body: str, download_url: str):
        msg = QMessageBox(self)
        msg.setWindowTitle("Доступно обновление Auto-configVPN")
        msg.setText(f"<b>Вышло обновление v{tag}!</b><br><br>Текущая версия: v{APP_VERSION}")
        msg.setInformativeText(f"Что нового:\n{body[:400] if body else 'Оптимизации маршрутизации и исправления'}")
        btn_update = msg.addButton("Скачать обновление", QMessageBox.AcceptRole)
        msg.addButton("Позже", QMessageBox.RejectRole)
        msg.exec()

        if msg.clickedButton() == btn_update:
            QDesktopServices.openUrl(QUrl(download_url))

    def _on_manual_check_finished(self, found: bool, message: str):
        if not found:
            QMessageBox.information(self, "Проверка обновлений", message)

    def _build_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # 1. Header
        header_layout = QHBoxLayout()
        title_label = QLabel("⚡ Smart Split-Tunneling Wizard")
        title_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #60a5fa;")
        subtitle = QLabel("Раздельное туннелирование (ПК & Android)")
        subtitle.setStyleSheet("color: #64748b; font-size: 13px;")

        self.btn_check_update = QPushButton("🔄 Проверить обновления")
        self.btn_check_update.setStyleSheet("""
            QPushButton {
                background-color: #1a2130;
                border: 1px solid #2d3748;
                border-radius: 6px;
                padding: 6px 12px;
                color: #94a3b8;
                font-size: 12px;
            }
            QPushButton:hover {
                border-color: #3b82f6;
                color: #60a5fa;
            }
        """)
        self.btn_check_update.clicked.connect(lambda: self._start_update_check(manual=True))

        header_layout.addWidget(title_label)
        header_layout.addSpacing(10)
        header_layout.addWidget(subtitle)
        header_layout.addStretch()
        header_layout.addWidget(self.btn_check_update)
        main_layout.addLayout(header_layout)

        # 2. Server Input Box
        node_group = QGroupBox("1. Конфигурация вашего сервера (VLESS Reality / Shadowsocks / Подписка)")
        node_layout = QVBoxLayout(node_group)
        node_layout.setSpacing(8)

        input_row = QHBoxLayout()
        self.link_input = QLineEdit()
        self.link_input.setPlaceholderText("Вставьте vless://, hysteria2:// ссылку или URL подписки (https://)...")
        # Pre-fill with user's active working link
        default_link = "vless://a9f3ec7e-f680-4067-94a1-96b515e642c3@176.124.207.182:443?type=tcp&security=reality&pbk=VhgG8Gv5D66I_nsTlvRyEAu3oIc7TPpyw9vuWHBEuj4&fp=chrome&sni=gateway.icloud.com&sid=a9a2084614af6db0&spx=%2F&flow=xtls-rprx-vision#Aeza%20Sweden%20(Reality)"
        self.link_input.setText(default_link)
        self.link_input.textChanged.connect(self._on_link_changed)

        btn_paste = QPushButton("📋 Вставить")
        btn_paste.clicked.connect(self._paste_clipboard)
        btn_clear = QPushButton("✕")
        btn_clear.clicked.connect(lambda: self.link_input.setText(""))

        input_row.addWidget(self.link_input, 1)
        input_row.addWidget(btn_paste)
        input_row.addWidget(btn_clear)
        node_layout.addLayout(input_row)

        self.server_combo = QComboBox()
        self.server_combo.currentIndexChanged.connect(self._on_server_selected)
        self.server_combo.setVisible(False)
        node_layout.addWidget(self.server_combo)

        self.node_info_label = QLabel("Узел распознан:")
        self.node_info_label.setStyleSheet("color: #10b981; font-weight: 500;")
        node_layout.addWidget(self.node_info_label)
        main_layout.addWidget(node_group)

        # 3. Main Tabs (ПК / Телефон / Игры / Настройки)
        self.tabs = QTabWidget()

        # Tab 1: PC
        self.tab_pc = QWidget()
        self._build_pc_tab()
        self.tabs.addTab(self.tab_pc, "🖥️ Для Компьютера (Clash Verge)")

        # Tab 2: Mobile
        self.tab_mobile = QWidget()
        self._build_mobile_tab()
        self.tabs.addTab(self.tab_mobile, "📱 Для Телефона (Hiddify / v2rayNG)")

        # Tab 3: Games List
        self.tab_games = QWidget()
        self._build_games_tab()
        self.tabs.addTab(self.tab_games, "🎮 Игры в DIRECT (0)")

        # Tab 4: Categories
        self.tab_categories = QWidget()
        self._build_categories_tab()
        self.tabs.addTab(self.tab_categories, "🇷🇺 Российские Сервисы")

        main_layout.addWidget(self.tabs, 1)

        # Initial link parse
        self._on_link_changed(self.link_input.text())

    # --- TAB 1: PC ---
    def _build_pc_tab(self):
        layout = QVBoxLayout(self.tab_pc)
        layout.setSpacing(14)

        desc = QLabel(
            "<b>Как это работает на ПК:</b> Все отмеченные игры (Dota 2, CS2, Overwatch и др.) и российские ресурсы "
            "пойдут <b>напрямую (DIRECT)</b> с родным пингом 35 мс. Зарубежные сервисы (Discord, YouTube, Antigravity) "
            "пойдут через ваш сервер в Швеции. Рекомендуемый клиент: <b>Clash Verge Rev</b> (ядро Mihomo) в режиме TUN."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #cbd5e1; line-height: 140%;")
        layout.addWidget(desc)

        action_card = QGroupBox("Развёртывание в 1 клик")
        ac_layout = QVBoxLayout(action_card)
        ac_layout.setSpacing(10)

        self.btn_deploy_pc = QPushButton("🚀 Применить настройки в Clash Verge")
        self.btn_deploy_pc.setObjectName("btnSuccess")
        self.btn_deploy_pc.clicked.connect(self._deploy_clash)
        ac_layout.addWidget(self.btn_deploy_pc)

        self.pc_status_label = QLabel("Статус: Готов к развёртыванию")
        self.pc_status_label.setStyleSheet("color: #94a3b8; font-weight: 500;")
        ac_layout.addWidget(self.pc_status_label)

        btn_row = QHBoxLayout()
        btn_save_file = QPushButton("💾 Сохранить .yaml файл")
        btn_save_file.clicked.connect(self._save_yaml_file)
        btn_copy_yaml = QPushButton("📋 Скопировать YAML в буфер")
        btn_copy_yaml.clicked.connect(self._copy_yaml)
        btn_view_preview = QPushButton("👁️ Показать превью конфигурации")
        btn_view_preview.clicked.connect(self._toggle_yaml_preview)

        btn_row.addWidget(btn_save_file)
        btn_row.addWidget(btn_copy_yaml)
        btn_row.addWidget(btn_view_preview)
        ac_layout.addLayout(btn_row)
        layout.addWidget(action_card)

        # YAML Preview text
        self.yaml_preview = QTextEdit()
        self.yaml_preview.setReadOnly(True)
        self.yaml_preview.setStyleSheet("font-family: Consolas, monospace; font-size: 11px; background-color: #0d1117;")
        self.yaml_preview.setVisible(False)
        layout.addWidget(self.yaml_preview, 1)

        layout.addStretch()

    # --- TAB 2: MOBILE ---
    def _build_mobile_tab(self):
        layout = QHBoxLayout(self.tab_mobile)
        layout.setSpacing(16)

        # Left Column: QR Code
        qr_box = QGroupBox("QR-код для импорта на смартфон")
        qr_layout = QVBoxLayout(qr_box)
        qr_layout.setAlignment(Qt.AlignCenter)

        self.qr_label = QLabel()
        self.qr_label.setFixedSize(320, 320)
        self.qr_label.setStyleSheet("background-color: #ffffff; border-radius: 12px; padding: 10px;")
        self.qr_label.setAlignment(Qt.AlignCenter)
        qr_layout.addWidget(self.qr_label)

        btn_copy_uri = QPushButton("📋 Скопировать VLESS ссылку")
        btn_copy_uri.setObjectName("btnPrimary")
        btn_copy_uri.clicked.connect(self._copy_mobile_link)
        qr_layout.addWidget(btn_copy_uri)

        layout.addWidget(qr_box)

        # Right Column: Instructions & Clients
        info_box = QGroupBox("Инструкция по настройке на телефоне")
        info_layout = QVBoxLayout(info_box)
        info_layout.setSpacing(10)

        guide_text = QLabel(
            "<b>Рекомендуемые приложения:</b><br>"
            "• <b>Hiddify</b> (Android / iOS) — <i>Лучший выбор!</i> Поддерживает раздельное туннелирование из коробки.<br>"
            "• <b>v2rayNG</b> (Android) — Классический быстрый клиент.<br><br>"
            "<b>Как подключить за 10 секунд:</b><br>"
            "1. Установите <b>Hiddify</b> из Google Play или App Store.<br>"
            "2. В приложении нажмите иконку <b>«+»</b> вверху справа.<br>"
            "3. Выберите <b>«Сканировать QR-код»</b> и наведите камеру на экран слева.<br>"
            "4. В Hiddify перейдите в Настройки → Регион маршрутизации → выберите <b>«Россия» (Bypass RU)</b>.<br>"
            "5. Нажмите большую кнопку подключения!<br><br>"
            "<b>Результат:</b> Сбербанк, Госуслуги, Т-Банк, Яндекс и доставка работают напрямую без замедления, "
            "а YouTube, Instagram и Discord летают через ваш сервер."
        )
        guide_text.setWordWrap(True)
        guide_text.setStyleSheet("color: #cbd5e1; line-height: 140%;")
        info_layout.addWidget(guide_text)

        btn_copy_json = QPushButton("📋 Скопировать полный Sing-box JSON")
        btn_copy_json.clicked.connect(self._copy_singbox_json)
        info_layout.addWidget(btn_copy_json)

        info_layout.addStretch()
        layout.addWidget(info_box, 1)

    # --- TAB 3: GAMES ---
    def _build_games_tab(self):
        layout = QVBoxLayout(self.tab_games)
        layout.setSpacing(10)

        top_row = QHBoxLayout()
        self.games_search = QLineEdit()
        self.games_search.setPlaceholderText("🔍 Поиск игры...")
        self.games_search.textChanged.connect(self._filter_games)

        btn_rescan = QPushButton("🔄 Пересканировать")
        btn_rescan.clicked.connect(self._start_scan)
        btn_add_exe = QPushButton("➕ Добавить свой .exe...")
        btn_add_exe.clicked.connect(self._add_custom_exe)
        btn_select_all = QPushButton("Выбрать все")
        btn_select_all.clicked.connect(lambda: self._set_all_games(True))
        btn_deselect_all = QPushButton("Снять все")
        btn_deselect_all.clicked.connect(lambda: self._set_all_games(False))

        top_row.addWidget(self.games_search, 1)
        top_row.addWidget(btn_rescan)
        top_row.addWidget(btn_add_exe)
        top_row.addWidget(btn_select_all)
        top_row.addWidget(btn_deselect_all)
        layout.addLayout(top_row)

        self.games_table = QTableWidget()
        self.games_table.setColumnCount(5)
        self.games_table.setHorizontalHeaderLabels(["DIRECT (Обход)", "Название игры", "Исполняемый файл (.exe)", "Источник", "Путь"])
        self.games_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.games_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.games_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.games_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.games_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.games_table.verticalHeader().setVisible(False)
        layout.addWidget(self.games_table)

    # --- TAB 4: CATEGORIES ---
    def _build_categories_tab(self):
        layout = QVBoxLayout(self.tab_categories)
        layout.setSpacing(12)

        desc = QLabel("Выберите категории российских сервисов, которые должны работать напрямую (DIRECT) без VPN:")
        desc.setStyleSheet("color: #94a3b8; font-weight: bold;")
        layout.addWidget(desc)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        c_layout = QVBoxLayout(container)
        c_layout.setSpacing(10)

        for cat_name, domains in RU_DIRECT_CATEGORIES.items():
            box = QGroupBox(cat_name)
            b_layout = QVBoxLayout(box)

            cb = QCheckBox(f"Включить обход для категории «{cat_name}» ({len(domains)} сервисов)")
            cb.setChecked(True)
            self.category_checkboxes[cat_name] = cb
            b_layout.addWidget(cb)

            sample_text = QLabel("Примеры: " + ", ".join(domains[:7]) + ("..." if len(domains) > 7 else ""))
            sample_text.setStyleSheet("color: #64748b; font-size: 11px;")
            b_layout.addWidget(sample_text)

            c_layout.addWidget(box)

        c_layout.addStretch()
        scroll.setWidget(container)
        layout.addWidget(scroll)

    # --- ACTIONS & LOGIC ---
    def _paste_clipboard(self):
        text = QApplication.clipboard().text().strip()
        if text:
            self.link_input.setText(text)

    def _on_link_changed(self, text: str):
        text = text.strip()
        if not text:
            self.node_info_label.setText("Ожидание ссылки...")
            self.node_info_label.setStyleSheet("color: #64748b; font-weight: 500;")
            self.server_combo.setVisible(False)
            self.current_nodes = []
            self.current_node = {}
            return

        try:
            nodes = parse_any_source(text)
            self.current_nodes = nodes
            if not nodes:
                raise ValueError("Серверы не найдены в ссылке")

            self.server_combo.blockSignals(True)
            self.server_combo.clear()

            if len(nodes) > 1:
                self.server_combo.addItem(f"🌐 Все серверы подписки ({len(nodes)} шт.) — выбор в Clash Verge")
                for i, n in enumerate(nodes, 1):
                    self.server_combo.addItem(f"{i}. {n.get('name', 'Proxy')} ({n.get('server')}:{n.get('port')})")
                self.server_combo.setVisible(True)
                self.current_node = nodes[0]
                self.node_info_label.setText(
                    f"✅ Подписка загружена: {len(nodes)} серверов | Все узлы будут добавлены в Clash Verge с раздельным туннелированием"
                )
            else:
                self.server_combo.setVisible(False)
                self.current_node = nodes[0]
                self.node_info_label.setText(
                    f"✅ Узел: {self.current_node.get('name')} | Сервер: {self.current_node.get('server')}:{self.current_node.get('port')} | Протокол: {self.current_node.get('type')}"
                )

            self.server_combo.blockSignals(False)
            self.node_info_label.setStyleSheet("color: #10b981; font-weight: 500;")
            self._update_qr()
            if self.yaml_preview.isVisible():
                self._update_yaml_preview()
        except Exception as e:
            self.node_info_label.setText(f"⚠️ Ошибка формата ссылки: {e}")
            self.node_info_label.setStyleSheet("color: #f59e0b; font-weight: 500;")
            self.server_combo.setVisible(False)

    def _on_server_selected(self, idx: int):
        if not self.current_nodes:
            return
        if idx == 0 and len(self.current_nodes) > 1:
            self.current_node = self.current_nodes[0]
            self.node_info_label.setText(
                f"✅ Выбраны все {len(self.current_nodes)} серверов для ПК | Для мобильного QR выбран: {self.current_node.get('name')}"
            )
        elif idx > 0 and (idx - 1) < len(self.current_nodes):
            self.current_node = self.current_nodes[idx - 1]
            self.node_info_label.setText(
                f"✅ Выбран сервер #{idx}: {self.current_node.get('name')} ({self.current_node.get('server')}:{self.current_node.get('port')})"
            )
        self._update_qr()
        if self.yaml_preview.isVisible():
            self._update_yaml_preview()

    def _update_qr(self):
        if not self.current_node or not self.current_node.get("server"):
            return
        try:
            uri = build_vless_uri(self.current_node)
            pil_img = generate_qr_image(uri, size=300)

            # Convert PIL to QPixmap
            buffer = BytesIO()
            pil_img.save(buffer, format="PNG")
            qimg = QImage.fromData(buffer.getvalue())
            pixmap = QPixmap.fromImage(qimg)
            self.qr_label.setPixmap(pixmap)
        except Exception as e:
            print("QR Error:", e)

    def _start_scan(self):
        self.games_table.setRowCount(0)
        self.detected_games.clear()
        self.thread = ScannerThread()
        self.thread.finished.connect(self._on_scan_finished)
        self.thread.start()

    def _on_scan_finished(self, games: List[Dict[str, str]]):
        self.detected_games = games
        self.tabs.setTabText(2, f"🎮 Игры в DIRECT ({len(games)})")
        self._populate_games_table(games)

    def _populate_games_table(self, games: List[Dict[str, str]]):
        self.games_table.setRowCount(len(games))
        for row, g in enumerate(games):
            # Checkbox
            cb = QCheckBox()
            cb.setChecked(True)
            cb_widget = QWidget()
            cb_layout = QHBoxLayout(cb_widget)
            cb_layout.addWidget(cb)
            cb_layout.setAlignment(Qt.AlignCenter)
            cb_layout.setContentsMargins(0, 0, 0, 0)
            self.games_table.setCellWidget(row, 0, cb_widget)

            # Name
            item_name = QTableWidgetItem(g["name"])
            item_name.setFlags(item_name.flags() ^ Qt.ItemIsEditable)
            self.games_table.setItem(row, 1, item_name)

            # Executable
            item_exe = QTableWidgetItem(g["exe"])
            item_exe.setFlags(item_exe.flags() ^ Qt.ItemIsEditable)
            item_exe.setForeground(QColor("#38bdf8"))
            self.games_table.setItem(row, 2, item_exe)

            # Source
            item_src = QTableWidgetItem(g["source"])
            item_src.setFlags(item_src.flags() ^ Qt.ItemIsEditable)
            self.games_table.setItem(row, 3, item_src)

            # Path
            item_path = QTableWidgetItem(g.get("path", ""))
            item_path.setFlags(item_path.flags() ^ Qt.ItemIsEditable)
            item_path.setForeground(QColor("#64748b"))
            self.games_table.setItem(row, 4, item_path)

    def _filter_games(self, text: str):
        text = text.lower().strip()
        for row in range(self.games_table.rowCount()):
            name_item = self.games_table.item(row, 1)
            exe_item = self.games_table.item(row, 2)
            match = (name_item and text in name_item.text().lower()) or (exe_item and text in exe_item.text().lower())
            self.games_table.setRowHidden(row, not match if text else False)

    def _set_all_games(self, state: bool):
        for row in range(self.games_table.rowCount()):
            w = self.games_table.cellWidget(row, 0)
            if w:
                cb = w.findChild(QCheckBox)
                if cb:
                    cb.setChecked(state)

    def _add_custom_exe(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Выберите исполняемый файл игры", "", "Executable Files (*.exe)")
        if file_path:
            p = Path(file_path)
            new_game = {
                "name": p.stem,
                "exe": p.name,
                "path": str(p),
                "source": "Custom"
            }
            self.detected_games.insert(0, new_game)
            self.tabs.setTabText(2, f"🎮 Игры в DIRECT ({len(self.detected_games)})")
            self._populate_games_table(self.detected_games)

    def _get_selected_game_exes(self) -> List[str]:
        selected = []
        for row in range(self.games_table.rowCount()):
            w = self.games_table.cellWidget(row, 0)
            if w:
                cb = w.findChild(QCheckBox)
                if cb and cb.isChecked():
                    exe_item = self.games_table.item(row, 2)
                    if exe_item:
                        selected.append(exe_item.text().strip())
        return selected

    def _get_enabled_categories(self) -> List[str]:
        return [cat for cat, cb in self.category_checkboxes.items() if cb.isChecked()]

    def _get_nodes_for_pc(self) -> List[Dict]:
        if not self.current_nodes:
            return [self.current_node] if self.current_node else []
        if self.server_combo.isVisible() and self.server_combo.currentIndex() == 0 and len(self.current_nodes) > 1:
            return self.current_nodes
        return [self.current_node] if self.current_node else self.current_nodes[:1]

    def _deploy_clash(self):
        nodes = self._get_nodes_for_pc()
        if not nodes:
            QMessageBox.warning(self, "Внимание", "Пожалуйста, введите корректную vless:// ссылку или URL подписки.")
            return

        try:
            exes = self._get_selected_game_exes()
            cats = self._get_enabled_categories()
            yaml_content = generate_clash_yaml(nodes, exes, cats)
            result = deploy_to_clash_verge(yaml_content, profile_name="Smart Split-Tunneling")

            if result["status"] == "success":
                clash_running = result.get("clash_running", False)
                if clash_running:
                    msg = (
                        f"✅ Отдельный профиль успешно создан!\n\n"
                        f"• Файл профиля: {Path(result['path']).name}\n"
                        f"• Серверов в профиле: {len(nodes)}\n"
                        f"• Игр в прямом обходе (DIRECT): {len(exes)}\n\n"
                        f"📌 Clash Verge сейчас открыт.\n"
                        f"Чтобы в Clash Verge сразу отобразилась вторая карточка рядом с Амнезией:\n"
                        f"• Нажмите значок 🔄 (Обновить) в правом верхнем углу вкладки «Профили» в Clash Verge\n"
                        f"• Или перезапустите Clash Verge (правый клик в трее → «Выход» / «Quit», затем запустить снова).\n\n"
                        f"Обе карточки будут доступны независимо!\n"
                        f"(Ваш профиль Амнезии полностью защищён и не изменялся)."
                    )
                else:
                    msg = (
                        f"✅ Отдельный профиль успешно добавлен в Clash Verge!\n\n"
                        f"• Серверов в профиле: {len(nodes)}\n"
                        f"• Игр в DIRECT: {len(exes)}\n\n"
                        f"При следующем запуске Clash Verge вы увидите обе независимые карточки:\n"
                        f"1. «Aeza Sweden (Reality)» (Амнезия)\n"
                        f"2. «Smart Split-Tunneling» ({len(nodes)} серверов)"
                    )
                self.pc_status_label.setText(f"✅ Создан отдельный профиль ({len(nodes)} серв., {len(exes)} игр в DIRECT)")
                self.pc_status_label.setStyleSheet("color: #10b981; font-weight: bold;")
                QMessageBox.information(self, "Новый профиль создан", msg)
            else:
                self.pc_status_label.setText(f"⚠️ Ошибка: {result['message']}")
                self.pc_status_label.setStyleSheet("color: #ef4444; font-weight: bold;")
                QMessageBox.critical(self, "Ошибка развёртывания", result["message"])
        except Exception as e:
            QMessageBox.critical(self, "Исключение", str(e))

    def _save_yaml_file(self):
        nodes = self._get_nodes_for_pc()
        if not nodes:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Сохранить профиль Clash", "smart_split_tunnel.yaml", "YAML Files (*.yaml *.yml)")
        if path:
            exes = self._get_selected_game_exes()
            cats = self._get_enabled_categories()
            content = generate_clash_yaml(nodes, exes, cats)
            Path(path).write_text(content, encoding="utf-8")
            QMessageBox.information(self, "Успех", f"Файл сохранён ({len(nodes)} серверов):\n{path}")

    def _copy_yaml(self):
        nodes = self._get_nodes_for_pc()
        if not nodes:
            return
        exes = self._get_selected_game_exes()
        cats = self._get_enabled_categories()
        content = generate_clash_yaml(nodes, exes, cats)
        QApplication.clipboard().setText(content)
        QMessageBox.information(self, "Скопировано", f"YAML-профиль ({len(nodes)} серверов) скопирован в буфер обмена!")

    def _update_yaml_preview(self):
        nodes = self._get_nodes_for_pc()
        if not nodes:
            return
        exes = self._get_selected_game_exes()
        cats = self._get_enabled_categories()
        content = generate_clash_yaml(nodes, exes, cats)
        self.yaml_preview.setText(content)

    def _toggle_yaml_preview(self):
        vis = not self.yaml_preview.isVisible()
        self.yaml_preview.setVisible(vis)
        if vis:
            self._update_yaml_preview()

    def _copy_mobile_link(self):
        if not self.current_node:
            return
        uri = build_vless_uri(self.current_node)
        QApplication.clipboard().setText(uri)
        QMessageBox.information(self, "Скопировано", "VLESS-ссылка скопирована в буфер обмена!")

    def _copy_singbox_json(self):
        if not self.current_node:
            return
        cats = self._get_enabled_categories()
        content = generate_singbox_json(self.current_node, cats)
        QApplication.clipboard().setText(content)
        QMessageBox.information(self, "Скопировано", "Sing-box JSON скопирован в буфер обмена!")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
