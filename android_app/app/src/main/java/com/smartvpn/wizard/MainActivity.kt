package com.smartvpn.wizard

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.os.Bundle
import android.view.Menu
import android.view.MenuItem
import android.view.View
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.core.widget.doAfterTextChanged
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import com.google.android.material.dialog.MaterialAlertDialogBuilder
import com.smartvpn.wizard.databinding.ActivityMainBinding
import com.smartvpn.wizard.generator.SingBoxConfigGenerator
import com.smartvpn.wizard.scanner.AppScanner
import com.smartvpn.wizard.ui.AppAdapter
import com.smartvpn.wizard.updater.GitHubUpdateChecker
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding
    private lateinit var appAdapter: AppAdapter
    private lateinit var appScanner: AppScanner
    private lateinit var updateChecker: GitHubUpdateChecker
    private val configGenerator = SingBoxConfigGenerator()

    private var lastGeneratedJson: String = ""

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        setSupportActionBar(binding.toolbar)

        appScanner = AppScanner(this)
        updateChecker = GitHubUpdateChecker(this)

        setupRecyclerView()
        setupListeners()
        loadInstalledApps()

        // Schedule periodic update check (2 times a day at 12:00 and 00:00)
        com.smartvpn.wizard.updater.UpdateWorker.schedulePeriodicCheck(this)

        // Immediate update check on app launch
        val showUpdatePopup = intent.getBooleanExtra("EXTRA_SHOW_UPDATE", false)
        lifecycleScope.launch {
            updateChecker.checkForUpdates(isManualCheck = showUpdatePopup)
        }
    }

    override fun onCreateOptionsMenu(menu: Menu?): Boolean {
        menuInflater.inflate(R.menu.menu_main, menu)
        return true
    }

    override fun onOptionsItemSelected(item: MenuItem): Boolean {
        return when (item.itemId) {
            R.id.action_check_update -> {
                lifecycleScope.launch {
                    Toast.makeText(this@MainActivity, "Проверка обновлений...", Toast.LENGTH_SHORT).show()
                    updateChecker.checkForUpdates(isManualCheck = true)
                }
                true
            }
            else -> super.onOptionsItemSelected(item)
        }
    }

    private fun setupRecyclerView() {
        appAdapter = AppAdapter(emptyList())
        binding.rvApps.apply {
            layoutManager = LinearLayoutManager(this@MainActivity)
            adapter = appAdapter
        }
    }

    private fun loadInstalledApps() {
        binding.pbScanApps.visibility = View.VISIBLE
        lifecycleScope.launch {
            val apps = appScanner.getInstalledApps()
            binding.pbScanApps.visibility = View.GONE
            appAdapter.updateData(apps)
        }
    }

    private fun setupListeners() {
        binding.btnPaste.setOnClickListener {
            val clipboard = getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
            val item = clipboard.primaryClip?.getItemAt(0)
            val text = item?.text?.toString()?.trim() ?: ""
            if (text.startsWith("vless://") || text.startsWith("http://") || text.startsWith("https://")) {
                binding.etVlessLink.setText(text)
                Toast.makeText(this, "Ссылка вставлена", Toast.LENGTH_SHORT).show()
            } else {
                Toast.makeText(this, "В буфере нет подходящей ссылки (vless:// или https://)", Toast.LENGTH_SHORT).show()
            }
        }

        binding.etSearchApp.doAfterTextChanged { text ->
            appAdapter.filter(text?.toString() ?: "")
        }

        binding.btnResetDefault.setOnClickListener {
            appAdapter.resetToDefault(appScanner.DEFAULT_DIRECT_PACKAGES)
            Toast.makeText(this, "Сброшено к рекомендованным российским сервисам", Toast.LENGTH_SHORT).show()
        }

        binding.btnHelpClients.setOnClickListener {
            showClientsHelpDialog()
        }

        // --- Sing-box Actions ---
        binding.btnCopySingbox.setOnClickListener {
            exportSingBox(share = false)
        }

        binding.btnShareSingbox.setOnClickListener {
            exportSingBox(share = true)
        }

        binding.btnSaveSingbox.setOnClickListener {
            saveSingBoxFile()
        }

        // --- Xray / v2rayNG Actions ---
        binding.btnCopyVless.setOnClickListener {
            exportVlessLinks()
        }

        binding.btnCopyBase64.setOnClickListener {
            exportBase64()
        }

        binding.btnSaveVless.setOnClickListener {
            saveVlessFile()
        }

        // --- Clash / Flclash Actions ---
        binding.btnCopyClash.setOnClickListener {
            exportClash(share = false)
        }

        binding.btnShareClash.setOnClickListener {
            exportClash(share = true)
        }

        binding.btnSaveClash.setOnClickListener {
            saveClashFile()
        }
    }

    private fun getValidatedLink(): String? {
        val link = binding.etVlessLink.text?.toString()?.trim() ?: ""
        if (link.isEmpty()) {
            Toast.makeText(this, "Укажите ссылку vless:// или подписку https://", Toast.LENGTH_LONG).show()
            return null
        }
        return link
    }

    private fun copyToClipboard(label: String, text: String) {
        val clipboard = getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
        clipboard.setPrimaryClip(ClipData.newPlainText(label, text))
    }

    private fun shareText(title: String, text: String) {
        val sendIntent = Intent().apply {
            action = Intent.ACTION_SEND
            putExtra(Intent.EXTRA_TEXT, text)
            type = "text/plain"
        }
        startActivity(Intent.createChooser(sendIntent, title))
    }

    private fun exportSingBox(share: Boolean) {
        val link = getValidatedLink() ?: return
        lifecycleScope.launch {
            try {
                val nodes = withContext(Dispatchers.IO) { configGenerator.parseNodes(link) }
                val selectedPackages = appAdapter.getSelectedPackages()
                val json = configGenerator.generateSingBoxJson(nodes, selectedPackages)
                lastGeneratedJson = json

                if (share) {
                    shareText("Поделиться Sing-box конфигурацией", json)
                } else {
                    copyToClipboard("Sing-box Config", json)
                    MaterialAlertDialogBuilder(this@MainActivity)
                        .setTitle("✅ Sing-box JSON скопирован!")
                        .setMessage("Узлов: ${nodes.size}, приложений в обходе: ${selectedPackages.size}.\n\nПоддерживаемые клиенты:\n• Hiddify\n• NekoBox for Android\n• Karing\n• Sing-box\n\nВ приложении клиента выберите «Добавить из буфера обмена». Все выбранные приложения пойдут напрямую без VPN!")
                        .setPositiveButton("Понятно", null)
                        .show()
                }
            } catch (e: Exception) {
                showErrorDialog(e.localizedMessage ?: "Ошибка формирования Sing-box")
            }
        }
    }

    private fun exportVlessLinks() {
        val link = getValidatedLink() ?: return
        lifecycleScope.launch {
            try {
                val nodes = withContext(Dispatchers.IO) { configGenerator.parseNodes(link) }
                val rawLinks = configGenerator.buildRawLinks(nodes)
                copyToClipboard("VLESS Links", rawLinks)

                MaterialAlertDialogBuilder(this@MainActivity)
                    .setTitle("✅ vless:// ссылки скопированы!")
                    .setMessage("Скопировано узлов: ${nodes.size}.\n\nКак использовать в v2rayNG / v2rayTun:\n1. Откройте v2rayNG.\n2. Нажмите [+] в правом верхнем углу ➔ «Импорт профиля из буфера обмена».\n\n⚠️ ВНИМАНИЕ ПО ОБХОДУ ПРИЛОЖЕНИЙ:\nЯдро Xray не принимает правила приложений внутри ссылки. Чтобы банки и маркетплейсы шли мимо VPN, в v2rayNG откройте:\nМеню ➔ Настройки ➔ «Раздельное туннелирование» ➔ отметьте нужные приложения.")
                    .setPositiveButton("Понятно", null)
                    .show()
            } catch (e: Exception) {
                showErrorDialog(e.localizedMessage ?: "Ошибка парсинга ссылок")
            }
        }
    }

    private fun exportBase64() {
        val link = getValidatedLink() ?: return
        lifecycleScope.launch {
            try {
                val nodes = withContext(Dispatchers.IO) { configGenerator.parseNodes(link) }
                val b64 = configGenerator.buildBase64Subscription(nodes)
                copyToClipboard("Base64 Subscription", b64)

                MaterialAlertDialogBuilder(this@MainActivity)
                    .setTitle("✅ Base64 подписка скопирована!")
                    .setMessage("Сгенерирована единая строка подписки для узлов: ${nodes.size}.\n\nПодходит для v2rayNG, Incy, Happ, Streisand, V2Box.\n\nВ клиенте выберите «Импорт из буфера обмена».")
                    .setPositiveButton("Понятно", null)
                    .show()
            } catch (e: Exception) {
                showErrorDialog(e.localizedMessage ?: "Ошибка создания Base64")
            }
        }
    }

    private fun exportClash(share: Boolean) {
        val link = getValidatedLink() ?: return
        lifecycleScope.launch {
            try {
                val nodes = withContext(Dispatchers.IO) { configGenerator.parseNodes(link) }
                val yaml = configGenerator.generateClashYaml(nodes)

                if (share) {
                    shareText("Поделиться Clash YAML конфигурацией", yaml)
                } else {
                    copyToClipboard("Clash Config", yaml)
                    MaterialAlertDialogBuilder(this@MainActivity)
                        .setTitle("✅ Clash YAML скопирован!")
                        .setMessage("Сгенерирован профиль Clash/Mihomo для узлов: ${nodes.size} с правилами fake-ip, TUN и прямым обходом доменов .RU / российских сервисов.\n\nПоддерживаемые клиенты:\n• Flclash (Android)\n• Clash Meta for Android (CMFA)\n• Clash MI\n\nВ клиенте откройте Profiles ➔ [+] ➔ Import from Clipboard.")
                        .setPositiveButton("Понятно", null)
                        .show()
                }
            } catch (e: Exception) {
                showErrorDialog(e.localizedMessage ?: "Ошибка формирования Clash YAML")
            }
        }
    }

    private fun saveSingBoxFile() {
        val link = getValidatedLink() ?: return
        lifecycleScope.launch {
            try {
                val nodes = withContext(Dispatchers.IO) { configGenerator.parseNodes(link) }
                val selectedPackages = appAdapter.getSelectedPackages()
                val json = configGenerator.generateSingBoxJson(nodes, selectedPackages)
                val (success, path) = withContext(Dispatchers.IO) {
                    com.smartvpn.wizard.util.FileExportHelper.saveFileToDownloads(
                        this@MainActivity,
                        "smart_singbox.json",
                        "application/json",
                        json
                    )
                }

                if (success) {
                    MaterialAlertDialogBuilder(this@MainActivity)
                        .setTitle("💾 Файл сохранён!")
                        .setMessage("Конфигурация успешно сохранена:\n$path\n\nКак импортировать в Hiddify / NekoBox:\n1. Откройте Hiddify (или NekoBox).\n2. Нажмите «Новый профиль» (или [+]).\n3. Выберите «Импорт из файла» ➔ выберите smart_singbox.json из папки Загрузки.")
                        .setPositiveButton("Понятно", null)
                        .show()
                } else {
                    showErrorDialog(path)
                }
            } catch (e: Exception) {
                showErrorDialog(e.localizedMessage ?: "Ошибка сохранения файла")
            }
        }
    }

    private fun saveVlessFile() {
        val link = getValidatedLink() ?: return
        lifecycleScope.launch {
            try {
                val nodes = withContext(Dispatchers.IO) { configGenerator.parseNodes(link) }
                val rawLinks = configGenerator.buildRawLinks(nodes)
                val (success, path) = withContext(Dispatchers.IO) {
                    com.smartvpn.wizard.util.FileExportHelper.saveFileToDownloads(
                        this@MainActivity,
                        "vless_nodes.txt",
                        "text/plain",
                        rawLinks
                    )
                }

                if (success) {
                    MaterialAlertDialogBuilder(this@MainActivity)
                        .setTitle("💾 Файл сохранён!")
                        .setMessage("Ссылки узлов сохранены:\n$path\n\nКак импортировать в v2rayNG:\n1. Откройте v2rayNG.\n2. Нажмите [+] ➔ «Импорт из файла» ➔ выберите vless_nodes.txt.")
                        .setPositiveButton("Понятно", null)
                        .show()
                } else {
                    showErrorDialog(path)
                }
            } catch (e: Exception) {
                showErrorDialog(e.localizedMessage ?: "Ошибка сохранения файла")
            }
        }
    }

    private fun saveClashFile() {
        val link = getValidatedLink() ?: return
        lifecycleScope.launch {
            try {
                val nodes = withContext(Dispatchers.IO) { configGenerator.parseNodes(link) }
                val yaml = configGenerator.generateClashYaml(nodes)
                val (success, path) = withContext(Dispatchers.IO) {
                    com.smartvpn.wizard.util.FileExportHelper.saveFileToDownloads(
                        this@MainActivity,
                        "smart_clash.yaml",
                        "application/x-yaml",
                        yaml
                    )
                }

                if (success) {
                    MaterialAlertDialogBuilder(this@MainActivity)
                        .setTitle("💾 Файл сохранён!")
                        .setMessage("Clash-профиль сохранён:\n$path\n\nКак импортировать в Flclash / CMFA:\n1. Откройте Flclash.\n2. Перейдите в Profiles ➔ [+].\n3. Выберите «File» (Импорт из файла) ➔ выберите smart_clash.yaml.")
                        .setPositiveButton("Понятно", null)
                        .show()
                } else {
                    showErrorDialog(path)
                }
            } catch (e: Exception) {
                showErrorDialog(e.localizedMessage ?: "Ошибка сохранения файла")
            }
        }
    }

    private fun showClientsHelpDialog() {
        MaterialAlertDialogBuilder(this)
            .setTitle("Поддерживаемые клиенты на Android")
            .setMessage(
                "1. 📱 Sing-box Core (Hiddify, NekoBox, Karing, Throne):\n" +
                "Формат: Sing-box JSON.\n" +
                "Плюсы: Автоматически применяет выбранный список приложений (Direct) прямо из конфига.\n\n" +
                "2. 🚀 Xray Core (v2rayNG, v2rayTun, Incy, Happ):\n" +
                "Формат: Прямые vless:// ссылки или Base64 подписка.\n" +
                "Особенность: v2rayNG НЕ принимает Sing-box JSON! Обход приложений в v2rayNG включается вручную: Настройки ➔ «Раздельное туннелирование».\n\n" +
                "3. 🐱 Clash / Mihomo Core (Flclash, Clash Meta):\n" +
                "Формат: Clash YAML.\n" +
                "Особенность: Импортируется в профили Flclash на телефоне.\n\n" +
                "❌ AmneziaVPN: Использует закрытый формат AWG, сторонние конфиги не принимает."
            )
            .setPositiveButton("Понятно", null)
            .show()
    }

    private fun showErrorDialog(message: String) {
        MaterialAlertDialogBuilder(this)
            .setTitle("Ошибка")
            .setMessage(message)
            .setPositiveButton("OK", null)
            .show()
    }
}
