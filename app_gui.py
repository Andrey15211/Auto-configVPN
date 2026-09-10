import sys
import os
import re
import json
import urllib.request
import urllib.error
from io import BytesIO
from pathlib import Path
from typing import List, Dict
import subprocess
import tempfile
from datetime import datetime, timedelta

from PySide6.QtCore import Qt, QThread, Signal, QSize, QTimer, QUrl, QSettings
from PySide6.QtGui import QIcon, QPixmap, QImage, QFont, QColor, QDesktopServices
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTabWidget, QTableWidget,
    QTableWidgetItem, QHeaderView, QCheckBox, QGroupBox, QMessageBox,
    QFileDialog, QScrollArea, QFrame, QTextEdit, QSplitter, QComboBox,
    QProgressBar, QDialog
)

from scanner import scan_all_games
from catalog import RU_DIRECT_CATEGORIES
from pc_generator import (
    parse_any_source, parse_vless_link, generate_clash_yaml,
    deploy_to_clash_verge, get_clash_verge_paths
)

def resource_path(relative_path: str) -> str:
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(base_path, relative_path)


def safe_copy_to_clipboard(text: str) -> bool:
    """Safely copy text to clipboard without freezing UI or deadlocking on Windows hooks."""
    try:
        cb = QApplication.clipboard()
        if cb:
            cb.setText(text)
            return True
    except Exception:
        pass
    try:
        import subprocess
        p = subprocess.Popen(["clip"], stdin=subprocess.PIPE, shell=True)
        p.communicate(input=text.encode("utf-16le"), timeout=2)
        return True
    except Exception:
        pass
    return False

from mobile_generator import (
    build_vless_uri, build_all_uris, generate_base64_subscription,
    generate_singbox_json, generate_qr_image
)

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


APP_VERSION = "1.3.3"
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
                    return
                elif resp.status == 404:
                    self.check_finished.emit(False, f"Релизов пока нет. У вас актуальная версия (v{APP_VERSION}).")
                    return
        except urllib.error.HTTPError as e:
            if e.code == 404:
                self.check_finished.emit(False, f"Релизов пока нет. У вас актуальная версия (v{APP_VERSION}).")
                return
            # On 403 or other API errors, fall back to web redirect
        except Exception:
            pass

        # Fallback to web redirect to bypass GitHub API rate limits
        self._fetch_from_web()

    def _fetch_from_web(self):
        try:
            web_url = f"https://github.com/{GITHUB_REPO}/releases/latest"
            req_web = urllib.request.Request(
                web_url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            )
            with urllib.request.urlopen(req_web, timeout=10) as resp_web:
                final_url = resp_web.geturl()
                tag = final_url.rstrip("/").split("/")[-1].lstrip("vV")
                if not tag or tag == "latest":
                    self.check_finished.emit(False, "Не удалось определить последнюю версию")
                    return
                exe_url = f"https://github.com/{GITHUB_REPO}/releases/download/v{tag}/SmartVPNWizard.exe"
                if self._is_newer(tag, APP_VERSION):
                    self.update_available.emit(tag, f"Доступна новая версия v{tag}", exe_url)
                    self.check_finished.emit(True, f"Доступна новая версия v{tag}")
                else:
                    self.check_finished.emit(False, "У вас установлена актуальная версия")
        except Exception as e:
            self.check_finished.emit(False, f"Не удалось проверить: {e}")

    def _is_newer(self, remote: str, current: str) -> bool:
        r_parts = [int(p) for p in re.findall(r"\d+", remote)]
        c_parts = [int(p) for p in re.findall(r"\d+", current)]
        max_l = max(len(r_parts), len(c_parts))
        r_parts += [0] * (max_l - len(r_parts))
        c_parts += [0] * (max_l - len(c_parts))
        return r_parts > c_parts


class UpdateDownloaderThread(QThread):
    progress = Signal(int, int, int)      # percentage, downloaded_bytes, total_bytes
    finished = Signal(str)                # temp_file_path
    error = Signal(str)                   # error_message

    def __init__(self, download_url: str):
        super().__init__()
        self.download_url = download_url
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        try:
            req = urllib.request.Request(
                self.download_url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            )
            temp_dir = tempfile.gettempdir()
            dest_file = os.path.join(temp_dir, "SmartVPNWizard_update.exe")

            with urllib.request.urlopen(req, timeout=30) as resp:
                total_length = resp.headers.get('content-length')
                total_bytes = int(total_length) if total_length else 0
                downloaded = 0
                chunk_size = 65536

                with open(dest_file, 'wb') as f:
                    while True:
                        if self._is_cancelled:
                            return
                        chunk = resp.read(chunk_size)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)
                        pct = int((downloaded / total_bytes * 100)) if total_bytes > 0 else 0
                        self.progress.emit(pct, downloaded, total_bytes)

            if downloaded < 1024 * 1024:
                self.error.emit("Загруженный файл слишком мал или повреждён.")
                return

            with open(dest_file, 'rb') as f:
                header = f.read(2)
                if header != b'MZ':
                    self.error.emit("Загруженный файл не является исполняемым файлом Windows.")
                    return

            self.finished.emit(dest_file)
        except Exception as e:
            self.error.emit(str(e))


class UpdateProgressDialog(QDialog):
    def __init__(self, parent, tag: str, download_url: str):
        super().__init__(parent)
        self.tag = tag
        self.download_url = download_url
        self.setWindowTitle(f"Обновление Auto-configVPN до v{tag}")
        self.resize(460, 180)
        self.setModal(True)
        self.setStyleSheet(MODERN_DARK_QSS)

        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(20, 20, 20, 20)

        self.lbl_title = QLabel(f"<b>Загрузка обновления v{tag}</b>")
        self.lbl_title.setStyleSheet("font-size: 15px; color: #60a5fa;")
        layout.addWidget(self.lbl_title)

        self.lbl_status = QLabel("Подключение к серверу...")
        self.lbl_status.setStyleSheet("color: #94a3b8; font-size: 12px;")
        layout.addWidget(self.lbl_status)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #334155;
                border-radius: 6px;
                text-align: center;
                color: #ffffff;
                background-color: #0f172a;
                height: 22px;
            }
            QProgressBar::chunk {
                background-color: #2563eb;
                border-radius: 5px;
            }
        """)
        layout.addWidget(self.progress_bar)

        self.btn_cancel = QPushButton("Отмена")
        self.btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 8px 16px;
                color: #94a3b8;
            }
            QPushButton:hover {
                color: #f8fafc;
                border-color: #ef4444;
            }
        """)
        self.btn_cancel.clicked.connect(self._on_cancel)
        layout.addWidget(self.btn_cancel, alignment=Qt.AlignRight)

        self.downloader = UpdateDownloaderThread(download_url)
        self.downloader.progress.connect(self._on_progress)
        self.downloader.finished.connect(self._on_finished)
        self.downloader.error.connect(self._on_error)
        self.downloader.start()

    def _on_progress(self, pct: int, downloaded: int, total: int):
        self.progress_bar.setValue(pct)
        mb_down = downloaded / (1024 * 1024)
        mb_tot = total / (1024 * 1024)
        if total > 0:
            self.lbl_status.setText(f"Загрузка: {mb_down:.1f} MB из {mb_tot:.1f} MB ({pct}%)")
        else:
            self.lbl_status.setText(f"Загрузка: {mb_down:.1f} MB...")

    def _on_finished(self, temp_exe: str):
        self.lbl_status.setText("Установка обновления и перезапуск...")
        self.progress_bar.setValue(100)
        self._apply_update(temp_exe)

    def _on_error(self, err: str):
        QMessageBox.critical(
            self,
            "Ошибка обновления",
            f"Не удалось загрузить обновление:\n{err}\n\nВы можете скачать обновление вручную с GitHub."
        )
        self.reject()

    def _on_cancel(self):
        self.downloader.cancel()
        self.reject()

    def _apply_update(self, temp_exe: str):
        is_frozen = getattr(sys, 'frozen', False)
        current_exe = os.path.abspath(sys.executable)

        if not is_frozen:
            QMessageBox.information(
                self,
                "Обновление загружено",
                f"Обновление успешно скачано в:\n{temp_exe}\n\n"
                "Так как приложение запущено из исходного кода (python.exe), "
                "автоматическая замена исполняемого файла отключена."
            )
            self.accept()
            return

        # Prepare self-update script via PowerShell
        ps_script = os.path.join(tempfile.gettempdir(), "smartvpn_self_update.ps1")
        ps_code = f"""# SmartVPN Self-Updater with Visible GUI & Clean Process Detach
$ErrorActionPreference = "Continue"
$logFile = "$env:TEMP\\smartvpn_update.log"
"Starting update at $(Get-Date)" | Out-File $logFile -Encoding utf8

$target = "{current_exe}"
$source = "{temp_exe}"

"Target: $target" | Out-File $logFile -Append -Encoding utf8
"Source: $source" | Out-File $logFile -Append -Encoding utf8

# 1. Show native Windows Forms installation progress window
$form = $null
$label = $null
$bar = $null
try {{
    Add-Type -AssemblyName System.Windows.Forms
    Add-Type -AssemblyName System.Drawing
    [System.Windows.Forms.Application]::EnableVisualStyles()

    $form = New-Object System.Windows.Forms.Form
    $form.Text = "Обновление Auto-configVPN"
    $form.Size = New-Object System.Drawing.Size(430, 165)
    $form.StartPosition = "CenterScreen"
    $form.FormBorderStyle = "FixedDialog"
    $form.MaximizeBox = $false
    $form.MinimizeBox = $false
    $form.TopMost = $true
    $form.BackColor = [System.Drawing.Color]::FromArgb(30, 41, 59)

    $label = New-Object System.Windows.Forms.Label
    $label.Text = "Завершение работы предыдущей версии..."
    $label.ForeColor = [System.Drawing.Color]::White
    $label.Font = New-Object System.Drawing.Font("Segoe UI", 10, [System.Drawing.FontStyle]::Regular)
    $label.Size = New-Object System.Drawing.Size(380, 25)
    $label.Location = New-Object System.Drawing.Point(20, 20)
    $form.Controls.Add($label)

    $bar = New-Object System.Windows.Forms.ProgressBar
    $bar.Size = New-Object System.Drawing.Size(370, 24)
    $bar.Location = New-Object System.Drawing.Point(20, 55)
    $bar.Minimum = 0
    $bar.Maximum = 100
    $bar.Value = 20
    $form.Controls.Add($bar)

    $form.Show()
    $form.Refresh()
}} catch {{
    "WinForms UI error: $_" | Out-File $logFile -Append -Encoding utf8
}}

# 2. Wait for old executable to unlock and release file locks
Start-Sleep -Milliseconds 1200

$retries = 50
while ($retries -gt 0) {{
    try {{
        if (Test-Path -LiteralPath $target) {{
            Remove-Item -LiteralPath $target -Force -ErrorAction Stop
        }}
        "Old exe removed successfully" | Out-File $logFile -Append -Encoding utf8
        break
    }} catch {{
        "Target still locked ($retries left): $_" | Out-File $logFile -Append -Encoding utf8
        Start-Sleep -Milliseconds 300
        $retries--
    }}
}}

# 3. Move new executable into place
if ($form -and $label -and $bar) {{
    $label.Text = "Установка новой версии..."
    $bar.Value = 70
    $form.Refresh()
}}

try {{
    Move-Item -LiteralPath $source -Destination $target -Force -ErrorAction Stop
    "Moved $source to $target successfully" | Out-File $logFile -Append -Encoding utf8
}} catch {{
    "Move failed: $_" | Out-File $logFile -Append -Encoding utf8
    Copy-Item -LiteralPath $source -Destination $target -Force -ErrorAction SilentlyContinue
}}

# 4. Clean PyInstaller environment variables so new process doesn't think it's a child process
if ($form -and $label -and $bar) {{
    $label.Text = "Запуск обновлённого приложения..."
    $bar.Value = 100
    $form.Refresh()
    Start-Sleep -Milliseconds 400
}}

Get-ChildItem env:* | Where-Object {{ $_.Name -like "*_MEI*" -or $_.Name -like "*PYI*" }} | ForEach-Object {{
    [System.Environment]::SetEnvironmentVariable($_.Name, $null, "Process")
    Remove-Item "env:$($_.Name)" -Force -ErrorAction SilentlyContinue
}}

# 5. Launch cleanly via Windows Explorer Shell (clean detachment from old PyInstaller process tree)
$targetDir = [System.IO.Path]::GetDirectoryName($target)
try {{
    $shell = New-Object -ComObject Shell.Application
    $shell.ShellExecute($target, "", $targetDir, "open", 1)
    "Started $target via Shell.Application" | Out-File $logFile -Append -Encoding utf8
}} catch {{
    "ShellExecute failed: $_. Falling back to explorer.exe" | Out-File $logFile -Append -Encoding utf8
    Start-Process -FilePath "explorer.exe" -ArgumentList "`"$target`""
}}

if ($form) {{
    $form.Close()
    $form.Dispose()
}}

Start-Sleep -Seconds 1
Remove-Item -LiteralPath $MyInvocation.MyCommand.Path -Force -ErrorAction SilentlyContinue
"""
        try:
            with open(ps_script, "w", encoding="utf-8-sig") as f:
                f.write(ps_code)

            subprocess.Popen(
                ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", ps_script],
                creationflags=subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP,
                close_fds=True
            )
            QApplication.instance().quit()
        except Exception as e:
            QMessageBox.critical(
                self,
                "Ошибка установки",
                f"Не удалось запустить скрипт обновления:\n{e}\n\nФайл сохранён в: {temp_exe}"
            )
            self.reject()


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

        # Set Window Icon
        icon_path = resource_path("icon.ico")
        if not os.path.exists(icon_path):
            icon_path = resource_path("icon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

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
        msg.setText(f"<b>Вышла новая версия v{tag}!</b><br><br>Текущая версия: v{APP_VERSION}")
        msg.setInformativeText(f"Что нового:\n{body[:400] if body else 'Оптимизации маршрутизации и повышение стабильности'}")
        btn_auto = msg.addButton("⚡ Обновить автоматически", QMessageBox.AcceptRole)
        btn_manual = msg.addButton("🌐 Скачать в браузере", QMessageBox.ActionRole)
        msg.addButton("Позже", QMessageBox.RejectRole)
        msg.setDefaultButton(btn_auto)
        msg.exec()

        if msg.clickedButton() == btn_auto:
            dlg = UpdateProgressDialog(self, tag, download_url)
            dlg.exec()
        elif msg.clickedButton() == btn_manual:
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
        subtitle = QLabel("Универсальное раздельное туннелирование (Clash / Sing-box / Xray)")
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
        self.link_input.setPlaceholderText("Вставьте vless://, hysteria2://, vpn:// ссылку Amnezia или URL подписки...")
        # Load previously saved link on this machine, if any (fresh stock installs start empty)
        self.settings = QSettings("SmartVPN", "Wizard")
        last_link = self.settings.value("last_link", "")
        if "176.124.207.182" in str(last_link) or "a9f3ec7e-f680" in str(last_link):
            last_link = ""
            self.settings.setValue("last_link", "")
        if last_link:
            self.link_input.setText(last_link)
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

        # 3. Main Tabs (Clash / Sing-box / Ссылки / Игры / Настройки)
        self.tabs = QTabWidget()

        # Tab 1: Clash / FlClash (YAML)
        self.tab_pc = QWidget()
        self._build_pc_tab()
        self.tabs.addTab(self.tab_pc, "🖥️ Clash Verge / FClashX (YAML)")

        # Tab 2: Sing-box (Hiddify / Throne / NekoBox)
        self.tab_singbox = QWidget()
        self._build_singbox_tab()
        self.tabs.addTab(self.tab_singbox, "⚡ Hiddify (Sing-box JSON)")

        # Tab 3: Links & QR (Happ / v2rayNG / Incy)
        self.tab_links = QWidget()
        self._build_links_tab()
        self.tabs.addTab(self.tab_links, "📱 Ссылки и QR (Hiddify / FClashX / Amnezia)")

        # Tab 4: Games List
        self.tab_games = QWidget()
        self._build_games_tab()
        self.tabs.addTab(self.tab_games, "🎮 Игры в DIRECT (0)")

        # Tab 5: Categories
        self.tab_categories = QWidget()
        self._build_categories_tab()
        self.tabs.addTab(self.tab_categories, "🇷🇺 Российские Сервисы")

        main_layout.addWidget(self.tabs, 1)

        # Initial link parse
        self._on_link_changed(self.link_input.text())

    # --- TAB 1: CLASH / FLCLASH ---
    def _build_pc_tab(self):
        layout = QVBoxLayout(self.tab_pc)
        layout.setSpacing(14)

        desc = QLabel(
            "<b>Для клиентов:</b> <b>Clash Verge Rev</b> (ПК) и <b>FClashX (FlClash)</b> (Android / iOS / Mac).<br>"
            "Использует формат <b>Mihomo (Clash Meta) YAML</b>. Все отмеченные игры (.exe) и сервисы РФ идут "
            "<b>напрямую (DIRECT)</b> с минимальным пингом. Discord, YouTube и заблокированные сайты идут через прокси."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #cbd5e1; line-height: 140%;")
        layout.addWidget(desc)

        action_card = QGroupBox("Развёртывание и экспорт для Clash Verge / FClashX")
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
        btn_save_file = QPushButton("💾 Сохранить .yaml (Clash Verge / FClashX)")
        btn_save_file.clicked.connect(self._save_yaml_file)
        self.btn_copy_yaml = QPushButton("📋 Скопировать YAML в буфер")
        self.btn_copy_yaml.clicked.connect(self._copy_yaml)
        btn_view_preview = QPushButton("👁️ Превью YAML")
        btn_view_preview.clicked.connect(self._toggle_yaml_preview)

        btn_row.addWidget(btn_save_file)
        btn_row.addWidget(self.btn_copy_yaml)
        btn_row.addWidget(btn_view_preview)
        ac_layout.addLayout(btn_row)
        layout.addWidget(action_card)

        # Instruction & Path Helper Box
        guide_box = QGroupBox("📖 Пошаговая инструкция: как добавить профиль в Clash Verge")
        g_layout = QVBoxLayout(guide_box)
        g_layout.setSpacing(10)

        steps_text = QLabel(
            "<b>Если Clash Verge запущен и карточка не появилась автоматически:</b><br>"
            "1. В Clash Verge откройте вкладку <b>«Профили»</b> слева.<br>"
            "2. Вверху нажмите <b>«+ Новый»</b> (или «Импорт») → выберите <b>«Локальный» (Local)</b>.<br>"
            "3. Нажмите <b>«Выбрать файл»</b> (Browse) и выберите созданный файл <code>smart_split_tunnel.yaml</code>.<br>"
            "4. Нажмите <b>«Сохранить»</b> — карточка появится в списке, нажмите на неё для активации!"
        )
        steps_text.setWordWrap(True)
        steps_text.setStyleSheet("color: #cbd5e1; line-height: 140%;")
        g_layout.addWidget(steps_text)

        path_card = QWidget()
        path_layout = QHBoxLayout(path_card)
        path_layout.setContentsMargins(0, 0, 0, 0)
        path_layout.setSpacing(8)

        self.profiles_path_input = QLineEdit()
        _, p_dir = get_clash_verge_paths()
        p_dir_str = str(p_dir) if p_dir else os.path.expandvars(r"%APPDATA%\io.github.clash-verge-rev.clash-verge-rev\profiles")
        self.profiles_path_input.setText(p_dir_str)
        self.profiles_path_input.setReadOnly(True)
        self.profiles_path_input.setStyleSheet("background-color: #0d1117; color: #38bdf8; font-family: Consolas, monospace; font-size: 12px; padding: 6px 10px;")

        self.btn_copy_path = QPushButton("📋 Скопировать путь к профилям")
        self.btn_copy_path.clicked.connect(self._copy_profiles_path)

        btn_open_folder = QPushButton("📂 Открыть папку профилей")
        btn_open_folder.clicked.connect(self._open_profiles_folder)

        path_layout.addWidget(self.profiles_path_input, 1)
        path_layout.addWidget(self.btn_copy_path)
        path_layout.addWidget(btn_open_folder)
        g_layout.addWidget(path_card)

        layout.addWidget(guide_box)

        # YAML Preview text
        self.yaml_preview = QTextEdit()
        self.yaml_preview.setReadOnly(True)
        self.yaml_preview.setStyleSheet("font-family: Consolas, monospace; font-size: 11px; background-color: #0d1117;")
        self.yaml_preview.setVisible(False)
        layout.addWidget(self.yaml_preview, 1)

        layout.addStretch()

    # --- TAB 2: SING-BOX (HIDDIFY / THRONE / NEKOBOX / NEKORAY) ---
    def _build_singbox_tab(self):
        layout = QVBoxLayout(self.tab_singbox)
        layout.setSpacing(14)

        desc = QLabel(
            "<b>Для клиентов:</b> <b>Hiddify</b> (Android / iOS / Windows / Mac).<br>"
            "Использует официальную спецификацию <b>Sing-box 1.10+ JSON</b>. Включает мультисерверный селектор (`selector`), "
            "прямой обход для игр на ПК (`process_name`) и обход российских мобильных приложений (`package_name`)."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #cbd5e1; line-height: 140%;")
        layout.addWidget(desc)

        action_card = QGroupBox("Экспорт конфигурации для Hiddify (Sing-box)")
        ac_layout = QVBoxLayout(action_card)
        ac_layout.setSpacing(10)

        self.btn_save_singbox = QPushButton("💾 Сохранить .json файл (Hiddify)")
        self.btn_save_singbox.setObjectName("btnPrimary")
        self.btn_save_singbox.clicked.connect(self._save_singbox_file)
        ac_layout.addWidget(self.btn_save_singbox)

        self.singbox_status_label = QLabel("Статус: Готов к экспорту Sing-box JSON")
        self.singbox_status_label.setStyleSheet("color: #94a3b8; font-weight: 500;")
        ac_layout.addWidget(self.singbox_status_label)

        btn_row = QHBoxLayout()
        self.btn_copy_singbox = QPushButton("📋 Скопировать Sing-box JSON (Hiddify)")
        self.btn_copy_singbox.clicked.connect(self._copy_singbox_json)
        btn_view_preview = QPushButton("👁️ Превью Sing-box JSON")
        btn_view_preview.clicked.connect(self._toggle_singbox_preview)

        btn_row.addWidget(self.btn_copy_singbox)
        btn_row.addWidget(btn_view_preview)
        ac_layout.addLayout(btn_row)
        layout.addWidget(action_card)

        # JSON Preview text
        self.singbox_preview = QTextEdit()
        self.singbox_preview.setReadOnly(True)
        self.singbox_preview.setStyleSheet("font-family: Consolas, monospace; font-size: 11px; background-color: #0d1117;")
        self.singbox_preview.setVisible(False)
        layout.addWidget(self.singbox_preview, 1)

        layout.addStretch()

    # --- TAB 3: LINKS & QR (HAPP / V2RAYNG / V2RAYTUN / INCY / V2RAYN) ---
    def _build_links_tab(self):
        layout = QHBoxLayout(self.tab_links)
        layout.setSpacing(16)

        # Left Column: QR Code & Quick Actions
        qr_box = QGroupBox("QR-код и универсальные ссылки")
        qr_layout = QVBoxLayout(qr_box)
        qr_layout.setSpacing(8)
        qr_layout.setAlignment(Qt.AlignCenter)

        self.qr_label = QLabel()
        self.qr_label.setFixedSize(270, 270)
        self.qr_label.setStyleSheet("background-color: #ffffff; border-radius: 12px; padding: 10px;")
        self.qr_label.setAlignment(Qt.AlignCenter)
        qr_layout.addWidget(self.qr_label)

        self.btn_copy_uri = QPushButton("📋 Скопировать активную VLESS ссылку")
        self.btn_copy_uri.setObjectName("btnPrimary")
        self.btn_copy_uri.clicked.connect(self._copy_mobile_link)
        qr_layout.addWidget(self.btn_copy_uri)

        self.btn_copy_all_links = QPushButton("📋 Скопировать ВСЕ серверы (список)")
        self.btn_copy_all_links.clicked.connect(self._copy_all_links)
        qr_layout.addWidget(self.btn_copy_all_links)

        self.btn_copy_routing_json = QPushButton("📋 Профиль с маршрутизацией (Hiddify)")
        self.btn_copy_routing_json.setStyleSheet("background-color: #0284c7; color: white; font-weight: bold;")
        self.btn_copy_routing_json.clicked.connect(self._copy_singbox_json)
        qr_layout.addWidget(self.btn_copy_routing_json)

        btn_save_b64 = QPushButton("💾 Экспорт Base64 подписки (.txt)")
        btn_save_b64.clicked.connect(self._save_base64_file)
        qr_layout.addWidget(btn_save_b64)

        layout.addWidget(qr_box)

        # Right Column: Instructions & Clients
        info_box = QGroupBox("Поддерживаемые приложения и инструкция")
        info_layout = QVBoxLayout(info_box)
        info_layout.setSpacing(10)

        guide_text = QLabel(
            "<b>Рекомендуемые клиенты:</b><br>"
            "• <b>Clash Verge Rev</b> (Windows / Mac / Linux) — Основной клиент для ПК с раздельным туннелированием для игр.<br>• <b>FClashX (FlClash)</b> (Android / iOS) — Рекомендуемый клиент для телефона на базе Mihomo.<br>• <b>Hiddify</b> (Android / iOS / Windows) — Рекомендуемый клиент на базе Sing-box.<br>• <b>AmneziaVPN</b> (Android / iOS / Windows) — Для протокола Amnezia.<br>"
            ""
            "<br>"
            "<b>💡 Самый надёжный способ импорта (без опечаток):</b><br>"
            "1. Нажмите <b>«📋 Скопировать активную VLESS ссылку»</b> слева.<br>"
            "2. Перешлите её себе/подруге в Telegram/WhatsApp.<br>"
            "3. На телефоне скопируйте ссылку → в приложении нажмите <b>«+»</b> → <b>«Импорт из буфера обмена»</b>.<br><br>"
            "<b>🛣️ Готовая маршрутизация (РФ напрямую, запреты через VPN):</b><br>"
            "• <b>В Hiddify:</b> Нажмите <i>«📋 Профиль с маршрутизацией»</i> и вставьте в Hiddify через буфер, либо в самом Hiddify зайдите в <i>Настройки → Маршрутизация → Регион: Россия</i>.<br>"
            ""
            "<b>⚠️ Внимание по ручному вводу ключей:</b><br>"
            "Никогда не вбивайте ключ Reality руками с клавиатуры! В криптографическом ключе легко спутать "
            "символы <code>I</code> (большая i) и <code>l</code> (маленькая L). Если ошибиться хоть в одной букве, "
            "TCP-пинг будет работать (49 мс), но соединение сбросится сервером и сайты не будут открываться."
        )
        guide_text.setWordWrap(True)
        guide_text.setStyleSheet("color: #cbd5e1; line-height: 140%;")
        info_layout.addWidget(guide_text)

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
        if hasattr(self, 'settings'):
            if "176.124.207.182" not in text and "a9f3ec7e-f680" not in text:
                self.settings.setValue("last_link", text)
            else:
                self.settings.setValue("last_link", "")
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
            if self.singbox_preview.isVisible():
                self._update_singbox_preview()
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
            pil_img = generate_qr_image(uri, size=250)

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
        self.tabs.setTabText(3, f"🎮 Игры в DIRECT ({len(games)})")
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
            self.tabs.setTabText(3, f"🎮 Игры в DIRECT ({len(self.detected_games)})")
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
                        f"1. Исходный профиль (например, Амнезия)\n"
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

    def _reset_btn(self, btn: QPushButton, original_text: str):
        try:
            btn.setText(original_text)
            btn.setStyleSheet("")
        except Exception:
            pass

    def _copy_yaml(self):
        nodes = self._get_nodes_for_pc()
        if not nodes:
            return
        exes = self._get_selected_game_exes()
        cats = self._get_enabled_categories()
        content = generate_clash_yaml(nodes, exes, cats)
        safe_copy_to_clipboard(content)
        self.btn_copy_yaml.setText(f"✅ Скопировано ({len(nodes)} серв.)!")
        self.btn_copy_yaml.setStyleSheet("background-color: #059669; color: white; font-weight: bold;")
        QTimer.singleShot(2500, lambda: self._reset_btn(self.btn_copy_yaml, "📋 Скопировать YAML в буфер"))

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

    def _save_singbox_file(self):
        nodes = self._get_nodes_for_pc()
        if not nodes:
            QMessageBox.warning(self, "Внимание", "Пожалуйста, введите корректный сервер или подписку.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Сохранить конфигурацию Sing-box", "singbox_config.json", "JSON Files (*.json)")
        if path:
            exes = self._get_selected_game_exes()
            cats = self._get_enabled_categories()
            content = generate_singbox_json(nodes, enabled_categories=cats, game_exes=exes)
            Path(path).write_text(content, encoding="utf-8")
            self.singbox_status_label.setText(f"✅ Файл сохранён: {Path(path).name} ({len(nodes)} серверов)")
            QMessageBox.information(self, "Успех", f"Конфигурация Sing-box сохранена ({len(nodes)} серверов, {len(exes)} игр в DIRECT):\n{path}")

    def _copy_singbox_json(self):
        nodes = self._get_nodes_for_pc()
        if not nodes:
            return
        exes = self._get_selected_game_exes()
        cats = self._get_enabled_categories()
        content = generate_singbox_json(nodes, enabled_categories=cats, game_exes=exes)
        safe_copy_to_clipboard(content)
        self.btn_copy_singbox.setText(f"✅ Скопировано ({len(nodes)} серв.)!")
        self.btn_copy_singbox.setStyleSheet("background-color: #059669; color: white; font-weight: bold;")
        QTimer.singleShot(2500, lambda: self._reset_btn(self.btn_copy_singbox, "📋 Скопировать Sing-box JSON в буфер"))

    def _update_singbox_preview(self):
        nodes = self._get_nodes_for_pc()
        if not nodes:
            return
        exes = self._get_selected_game_exes()
        cats = self._get_enabled_categories()
        content = generate_singbox_json(nodes, enabled_categories=cats, game_exes=exes)
        self.singbox_preview.setText(content)

    def _toggle_singbox_preview(self):
        vis = not self.singbox_preview.isVisible()
        self.singbox_preview.setVisible(vis)
        if vis:
            self._update_singbox_preview()

    def _copy_mobile_link(self):
        if not self.current_node:
            return
        uri = build_vless_uri(self.current_node)
        safe_copy_to_clipboard(uri)
        self.btn_copy_uri.setText("✅ VLESS ссылка скопирована!")
        self.btn_copy_uri.setStyleSheet("background-color: #059669; color: white; font-weight: bold;")
        QTimer.singleShot(2500, lambda: self._reset_btn(self.btn_copy_uri, "📋 Скопировать активную VLESS ссылку"))

    def _copy_all_links(self):
        nodes = self._get_nodes_for_pc()
        if not nodes:
            return
        all_uris = build_all_uris(nodes)
        safe_copy_to_clipboard(all_uris)
        self.btn_copy_all_links.setText(f"✅ Скопировано ({len(nodes)} серв.)!")
        self.btn_copy_all_links.setStyleSheet("background-color: #059669; color: white; font-weight: bold;")
        QTimer.singleShot(2500, lambda: self._reset_btn(self.btn_copy_all_links, "📋 Скопировать ВСЕ серверы (список)"))

    def _save_base64_file(self):
        nodes = self._get_nodes_for_pc()
        if not nodes:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Сохранить Base64 подписку", "subscription.txt", "Text Files (*.txt)")
        if path:
            b64 = generate_base64_subscription(nodes)
            Path(path).write_text(b64, encoding="utf-8")
            QMessageBox.information(self, "Успех", f"Base64 подписка ({len(nodes)} серверов) сохранена:\n{path}")

    def _copy_profiles_path(self):
        path = self.profiles_path_input.text().strip()
        safe_copy_to_clipboard(path)
        self.btn_copy_path.setText("✅ Путь скопирован!")
        self.btn_copy_path.setStyleSheet("background-color: #059669; color: white; font-weight: bold;")
        QTimer.singleShot(2500, lambda: self._reset_btn(self.btn_copy_path, "📋 Скопировать путь к профилям"))

    def _open_profiles_folder(self):
        path = self.profiles_path_input.text().strip()
        if os.path.exists(path):
            os.startfile(path)
        else:
            # Try to create or open parent AppData dir
            parent = Path(path).parent
            if parent.exists():
                os.startfile(str(parent))
            else:
                QMessageBox.warning(self, "Внимание", f"Папка пока не существует:\n{path}\nСначала нажмите «Применить настройки» или создайте её.")


if __name__ == "__main__":
    # Windows Taskbar Icon Fix (Set AppUserModelID)
    try:
        import ctypes
        myappid = 'smartvpn.wizard.client.v1'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except Exception:
        pass

    app = QApplication(sys.argv)

    # Set Application Icon
    icon_path = resource_path("icon.ico")
    if not os.path.exists(icon_path):
        icon_path = resource_path("icon.png")
    if os.path.exists(icon_path):
        app_icon = QIcon(icon_path)
        app.setWindowIcon(app_icon)

    window = MainWindow()
    if os.path.exists(icon_path):
        window.setWindowIcon(QIcon(icon_path))
    window.show()
    sys.exit(app.exec())
