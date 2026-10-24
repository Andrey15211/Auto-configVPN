# Инструкция по генерации нового keystore

## ⚠️ ВАЖНО
Старый `release.keystore` был удалён из репозитория по соображениям безопасности.
Все приложения, подписанные старым ключом, потребуют переустановки после обновления с новым ключом.

## Генерация нового ключа

```bash
keytool -genkey -v -keystore release.keystore -alias smartvpn -keyalg RSA -keysize 2048 -validity 10000
```

**Параметры:**
- Пароль keystore: придумайте новый сложный пароль (НЕ используйте старый `smartvpnwizard`)
- Пароль ключа: рекомендуется использовать тот же пароль
- CN (Common Name): ваше имя или название организации
- OU, O, L, ST, C: можно оставить пустыми (нажать Enter)

## Настройка в проекте

1. Сохраните файл `release.keystore` в `android_app/app/`
2. **НЕ КОММИТЬТЕ ФАЙЛ В GIT** (уже добавлен в `.gitignore`)
3. Создайте файл `android_app/key.properties`:

```properties
storePassword=ваш_пароль_keystore
keyPassword=ваш_пароль_ключа
keyAlias=smartvpn
storeFile=app/release.keystore
```

4. Добавьте `key.properties` в `.gitignore` (если ещё не добавлено)

## Хранение паролей

**Для локальной разработки:**
- Храните `release.keystore` и `key.properties` ВНЕ git-репозитория
- Используйте менеджер паролей для хранения паролей

**Для GitHub Actions CI/CD:**
- Закодируйте keystore в base64: `base64 release.keystore > release.keystore.base64`
- Добавьте в GitHub Secrets:
  - `KEYSTORE_BASE64` — содержимое файла base64
  - `KEYSTORE_PASSWORD` — пароль keystore
  - `KEY_PASSWORD` — пароль ключа
  - `KEY_ALIAS` — алиас ключа (smartvpn)

## Использование в CI/CD

В `.github/workflows/android-release.yml`:

```yaml
- name: Decode keystore
  run: |
    echo "${{ secrets.KEYSTORE_BASE64 }}" | base64 -d > android_app/app/release.keystore
    
- name: Build release APK
  run: |
    cd android_app
    ./gradlew assembleRelease
  env:
    KEYSTORE_PASSWORD: ${{ secrets.KEYSTORE_PASSWORD }}
    KEY_PASSWORD: ${{ secrets.KEY_PASSWORD }}
    KEY_ALIAS: ${{ secrets.KEY_ALIAS }}
```

## Проверка подписи

```bash
keytool -list -v -keystore release.keystore -alias smartvpn
```

## Важные замечания

- **Никогда не коммитьте keystore в git**
- **Создайте резервную копию keystore** — без неё невозможно выпускать обновления
- Храните резервную копию в безопасном месте (зашифрованное хранилище, менеджер паролей)
- Если потеряете ключ, все пользователи должны будут удалить и переустановить приложение
