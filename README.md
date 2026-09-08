# 🚀 Smart Split-Tunneling Wizard (PC & Android)

Универсальный комплекс раздельного туннелирования (Smart Split-Tunneling) для **Windows** и **Android**.

Приложение автоматически решает главную проблему современных VPN: **игры, банки, Госуслуги и российские сервисы работают напрямую с минимальным пингом и без блокировок, а заблокированные ресурсы и соцсети идут через быстрый VLESS Reality прокси.**

---

## 🌟 Основные возможности

### 💻 1. Версия для Windows (`SmartVPNWizard.exe`)
* **Автоматическое сканирование установленных игр:**
  * Интеграция с библиотеками **Steam** (парсинг `appmanifest_*.acf`).
  * Сканирование **Battle.net, Epic Games, Riot Games, Wargaming/Lesta** и системного реестра.
  * Все игровые процессы (например, `cs2.exe`, `dota2.exe`, `Deadlock.exe`, `Overwatch.exe`) направляются напрямую (`DIRECT`) для нулевой задержки (0ms ping overhead).
* **Каталог российских сервисов:**
  * Банки (Сбер, Т-Банк, ВТБ, Альфа, Райффайзен, МИР Pay).
  * Госуслуги, Мос.ру, Налог.ру.
  * Маркетплейсы и доставка (Ozon, Wildberries, DNS, Яндекс Маркет, Авито, Самокат).
  * Рунет TLDs (`.ru`, `.su`, `.xn--p1ai`).
* **Бесшовный деплой в 1 клик:**
  * Генерация профиля для ядра **Mihomo / Clash Verge Rev** с правилами Fake-IP, TUN stack: system, sniff.
  * Мгновенное применение профиля через IPC Named Pipe (`\\.\pipe\verge-mihomo`) без необходимости перезапуска клиента.
* **Генерация QR-кода для смартфона:**
  * Создание динамического QR-кода прямо в окне программы для быстрого сканирования с телефона.

---

### 📱 2. Мобильное приложение для Android (`SmartVPNWizard.apk`)
* **Сканирование мобильных приложений:**
  * Автоматический опрос установленных на телефоне приложений через Android `PackageManager`.
  * «Умный» предвыбор: банковские клиенты, Госуслуги и доставка по умолчанию включены в прямой обход (Direct).
* **Генерация Sing-box 1.10+ JSON:**
  * Формирование профиля с правилами `package_name`, `geosite: category-ru`, `geoip: ru`.
  * Экспорт в 1 клик в буфер обмена или через системное меню «Поделиться» для прямого импорта в **Sing-box**, **NekoBox** или **v2rayNG**.
* **🔄 Автообновления прямо в приложении (в стиле Morphe / ReVanced Manager):**
  * Встроенный модуль `GitHubUpdateChecker`.
  * Приложение проверяет наличие новых версий через GitHub Releases API (`api.github.com/repos/.../releases/latest`).
  * Отображает окно обновления со списком изменений (Changelog) и прогресс-баром загрузки.
  * Автоматически запускает установщик APK через защищенный `FileProvider` и `REQUEST_INSTALL_PACKAGES`.

---

## 🛠️ Структура проекта

```
vpn_config_wizard/
├── .github/
│   └── workflows/
│       └── release.yml          # GitHub Actions: автосборка .exe и .apk при релизе
├── android_app/                 # Нативный Android-проект (Kotlin + Material 3)
│   ├── app/
│   │   ├── src/main/java/com/smartvpn/wizard/
│   │   │   ├── MainActivity.kt
│   │   │   ├── updater/GitHubUpdateChecker.kt   # Morphe/ReVanced автообновления
│   │   │   ├── scanner/AppScanner.kt            # Сканер установленных APK
│   │   │   ├── generator/SingBoxConfigGenerator.kt
│   │   │   ├── model/
│   │   │   └── ui/
│   │   └── build.gradle.kts
│   ├── build.gradle.kts
│   ├── settings.gradle.kts
│   ├── gradlew
│   └── gradlew.bat
├── app_gui.py                   # PySide6 GUI для Windows
├── scanner.py                   # Модуль сканирования игр на ПК
├── catalog.py                   # Каталог доменов, процессов и пакетов Direct
├── pc_generator.py              # Генератор Clash/Mihomo YAML + Named Pipe IPC
├── mobile_generator.py          # Генератор Sing-box JSON + QR-генератор
├── main.py                      # Точка входа для сборки Windows EXE
└── README.md
```

---

## 📦 Сборка и запуск

### Запуск на Windows:
Готовый исполняемый файл находится в:
```
dist/SmartVPNWizard.exe
```
(Также ярлык доступен прямо на Рабочем столе: `SmartVPNWizard.exe`).

Для ручной пересборки `.exe`:
```powershell
pip install PySide6 PyYAML Pillow qrcode pyinstaller
pyinstaller --clean --noconsole --onefile --name "SmartVPNWizard" main.py
```

### Сборка Android APK:
```bash
cd android_app
./gradlew assembleRelease
```
Готовый файл APK сформируется по пути:
`android_app/app/build/outputs/apk/release/app-release.apk`.

---

## 🚀 Деплой на GitHub

1. Удаленный репозиторий:
   ```bash
   git remote add origin https://github.com/Andrey15211/Auto-configVPN.git
   git branch -M main
   git push -u origin main
   ```

2. Для автоматического выпуска релиза с готовыми файлами `.exe` и `.apk`:
   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```
   *GitHub Actions автоматически соберет `SmartVPNWizard.exe` и `SmartVPNWizard.apk` и прикрепит их к GitHub Release.*
