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

        binding.btnGenerate.setOnClickListener {
            generateSingBoxConfig()
        }

        binding.btnCopyConfig.setOnClickListener {
            if (lastGeneratedJson.isEmpty()) {
                generateSingBoxConfig()
            }
            if (lastGeneratedJson.isNotEmpty()) {
                val clipboard = getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
                val clip = ClipData.newPlainText("Sing-box Config", lastGeneratedJson)
                clipboard.setPrimaryClip(clip)
                Toast.makeText(this, "JSON конфиг скопирован в буфер!", Toast.LENGTH_SHORT).show()
            }
        }

        binding.btnShareConfig.setOnClickListener {
            if (lastGeneratedJson.isEmpty()) {
                generateSingBoxConfig()
            }
            if (lastGeneratedJson.isNotEmpty()) {
                val sendIntent = Intent().apply {
                    action = Intent.ACTION_SEND
                    putExtra(Intent.EXTRA_TEXT, lastGeneratedJson)
                    type = "text/plain"
                }
                val shareIntent = Intent.createChooser(sendIntent, "Поделиться Sing-box конфигурацией")
                startActivity(shareIntent)
            }
        }
    }

    private fun generateSingBoxConfig() {
        val link = binding.etVlessLink.text?.toString()?.trim() ?: ""
        if (link.isEmpty()) {
            Toast.makeText(this, "Пожалуйста, укажите ссылку на сервер или подписку", Toast.LENGTH_LONG).show()
            return
        }

        lifecycleScope.launch {
            try {
                val node = withContext(Dispatchers.IO) {
                    configGenerator.parseLinkOrSubscription(link)
                }
                val selectedPackages = appAdapter.getSelectedPackages()
                lastGeneratedJson = configGenerator.generateConfigJson(node, selectedPackages)

                MaterialAlertDialogBuilder(this@MainActivity)
                    .setTitle("Конфигурация готова!")
                    .setMessage("Сгенерирован профиль Sing-box для узла «${node.name}» с ${selectedPackages.size} приложениями в прямом обходе (Direct).\n\nВы можете скопировать или поделиться им для импорта в Hiddify, Sing-box или v2rayNG.")
                    .setPositiveButton("Скопировать") { _, _ ->
                        val clipboard = getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
                        clipboard.setPrimaryClip(ClipData.newPlainText("Sing-box Config", lastGeneratedJson))
                        Toast.makeText(this@MainActivity, "Конфиг скопирован!", Toast.LENGTH_SHORT).show()
                    }
                    .setNegativeButton("Закрыть", null)
                    .show()

            } catch (e: Exception) {
                MaterialAlertDialogBuilder(this@MainActivity)
                    .setTitle("Ошибка формирования")
                    .setMessage(e.localizedMessage ?: "Неверный формат ссылки")
                    .setPositiveButton("OK", null)
                    .show()
            }
        }
    }
}
