# Catalog of domains, IP rules, and mobile packages for Smart Split-Tunneling

# Strict PROXY domains (Google, AI, Overseas services that MUST go through VPN)
PROTECTED_PROXY_DOMAINS = [
    "googleapis.com",
    "google.com",
    "gstatic.com",
    "googleusercontent.com",
    "googlevideo.com",
    "youtube.com",
    "ytimg.com",
    "discord.com",
    "discord.gg",
    "discordapp.com",
    "discordapp.net",
    "openai.com",
    "anthropic.com",
    "claude.ai",
    "chatgpt.com",
    "gemini.google.com",
    "cloudaicompanion.googleapis.com",
    "generativelanguage.googleapis.com"
]

# Strict PROXY processes for PC
PROTECTED_PROXY_PROCESSES = [
    "antigravity.exe",
    "language_server.exe",
    "discord.exe",
    "telegram.exe"
]

# Russian services categorized for DIRECT routing
RU_DIRECT_CATEGORIES = {
    "Банки и Финансы": [
        "sberbank.ru", "sberbank.com", "sber.ru", "sber.pub",
        "tinkoff.ru", "tbank.ru", "t-bank.ru",
        "vtb.ru", "vtb.com",
        "alfabank.ru", "alfa-bank.ru",
        "raiffeisen.ru", "rshb.ru", "gazprombank.ru",
        "ozon.ru/bank", "yoomoney.ru", "qiwi.com", "cbr.ru", "nspk.ru", "sbp.nspk.ru"
    ],
    "Госуслуги и Налоги": [
        "gosuslugi.ru", "gosuslugi43.ru", "gosuslugi71.ru",
        "nalog.gov.ru", "nalog.ru", "mos.ru", "emias.info", "pfr.gov.ru", "sfr.gov.ru"
    ],
    "Маркетплейсы и Магазины": [
        "ozon.ru", "ozonusercontent.com",
        "wildberries.ru", "wb.ru", "wbstatic.net",
        "dns-shop.ru", "citilink.ru", "mvideo.ru", "eldorado.ru",
        "market.yandex.ru", "megamarket.ru", "avito.ru", "samokat.ru", "kuper.ru"
    ],
    "Поисковики, Почта и Порталы": [
        "yandex.ru", "ya.ru", "yandex.net", "yandex.com",
        "vk.com", "vk.ru", "vkvideo.ru", "dzen.ru",
        "mail.ru", "ok.ru", "rambler.ru", "2gis.ru"
    ],
    "Кино, Музыка и Медиа": [
        "kinopoisk.ru", "hd.kinopoisk.ru", "ivi.ru", "okko.tv",
        "rutube.ru", "smotrim.ru", "kion.ru", "premier.one"
    ],
    "Хостинги и Связь": [
        "aeza.ru", "aeza.net", "selectel.ru", "timeweb.ru",
        "beeline.ru", "mts.ru", "megafon.ru", "tele2.ru", "t-mobile.ru",
        "rostelecom.ru", "rt.ru"
    ]
}

# TLDs to bypass by default
RU_DIRECT_TLDS = [
    "ru",
    "su",
    "xn--p1ai",  # .рф
    "by",
    "kz"
]

# Android Mobile App Packages for Split-Tunneling (DIRECT / Bypass VPN)
ANDROID_DIRECT_PACKAGES = [
    # Banking
    "ru.sberbankmobile",                     # Сбербанк
    "com.idamob.tinkoff.android",            # Т-Банк
    "ru.vtb24.mobilebanking.android",        # ВТБ
    "ru.alfabank.mobile.android",            # Альфа-Банк
    "ru.raiffeisennews",                     # Райффайзен
    "ru.gazprombank.android.mobilebank.app", # Газпромбанк
    "ru.nspk.mirpay",                        # Mir Pay
    "com.yoomoney.android",                  # ЮMoney

    # Government
    "ru.gosuslugi.online",                   # Госуслуги
    "ru.gosuslugi.pos",                      # Госуслуги Решаем вместе
    "com.tax.fl",                            # Налоги ФЛ

    # Marketplaces & Shopping
    "ru.ozon.app.android",                   # Ozon
    "com.wildberries.wbdeti",                # Wildberries
    "ru.dns.shop.android",                   # DNS
    "com.avito.android",                     # Авито
    "ru.yandex.market",                      # Яндекс Маркет
    "ru.megamarket.android",                 # Мегамаркет
    "ru.samokat.app",                        # Самокат
    "ru.sbermarket",                         # Купер (Сбермаркет)

    # Transport & Maps
    "ru.yandex.yandexmaps",                  # Яндекс Карты
    "ru.yandex.taxi",                        # Яндекс Go
    "ru.dublgis.dgismobile",                 # 2ГИС

    # Social & Media
    "com.vkontakte.android",                 # ВКонтакте
    "ru.vk.video",                           # VK Видео
    "ru.rutube.app",                         # Rutube
    "ru.kinopoisk"                           # Кинопоиск
]
