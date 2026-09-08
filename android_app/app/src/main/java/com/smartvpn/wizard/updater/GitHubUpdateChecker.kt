package com.smartvpn.wizard.updater

import android.app.Activity
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.provider.Settings
import android.view.LayoutInflater
import android.view.View
import android.widget.ProgressBar
import android.widget.TextView
import android.widget.Toast
import androidx.core.content.FileProvider
import com.google.android.material.button.MaterialButton
import com.google.android.material.dialog.MaterialAlertDialogBuilder
import com.google.gson.Gson
import com.smartvpn.wizard.R
import com.smartvpn.wizard.model.GitHubRelease
import com.smartvpn.wizard.model.GitHubAsset
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import java.io.File
import java.io.FileOutputStream
import java.util.concurrent.TimeUnit

class GitHubUpdateChecker(
    private val context: Context,
    var repoOwner: String = "Andrey15211",
    var repoName: String = "Auto-configVPN"
) {
    private val client = OkHttpClient.Builder()
        .connectTimeout(15, TimeUnit.SECONDS)
        .readTimeout(30, TimeUnit.SECONDS)
        .build()

    private val gson = Gson()

    fun configureRepo(owner: String, name: String) {
        this.repoOwner = owner
        this.repoName = name
    }

    suspend fun checkForUpdates(isManualCheck: Boolean = false) = withContext(Dispatchers.IO) {
        try {
            val url = "https://api.github.com/repos/$repoOwner/$repoName/releases/latest"
            val request = Request.Builder()
                .url(url)
                .header("Accept", "application/vnd.github.v3+json")
                .header("User-Agent", "SmartVPNWizard-Android")
                .build()

            val response = client.newCall(request).execute()
            if (!response.isSuccessful) {
                if (isManualCheck) {
                    withContext(Dispatchers.Main) {
                        if (response.code == 404) {
                            Toast.makeText(context, context.getString(R.string.update_latest), Toast.LENGTH_SHORT).show()
                        } else {
                            Toast.makeText(context, "Не удалось проверить обновления (${response.code})", Toast.LENGTH_SHORT).show()
                        }
                    }
                }
                return@withContext
            }

            val body = response.body?.string() ?: return@withContext
            val release = gson.fromJson(body, GitHubRelease::class.java)

            val currentVersion = getCurrentAppVersion()
            val remoteVersion = release.tagName.trimStart('v', 'V')

            if (isNewerVersion(remoteVersion, currentVersion)) {
                val apkAsset = release.assets.firstOrNull { it.name.endsWith(".apk", ignoreCase = true) }
                if (apkAsset != null) {
                    withContext(Dispatchers.Main) {
                        showUpdateDialog(release, apkAsset.browserDownloadUrl, apkAsset.name)
                    }
                }
            } else if (isManualCheck) {
                withContext(Dispatchers.Main) {
                    Toast.makeText(context, context.getString(R.string.update_latest), Toast.LENGTH_SHORT).show()
                }
            }
        } catch (e: Exception) {
            e.printStackTrace()
            if (isManualCheck) {
                withContext(Dispatchers.Main) {
                    Toast.makeText(context, "Ошибка проверки: ${e.localizedMessage}", Toast.LENGTH_SHORT).show()
                }
            }
        }
    }

    suspend fun fetchLatestRelease(): Pair<GitHubRelease, GitHubAsset>? = withContext(Dispatchers.IO) {
        try {
            val url = "https://api.github.com/repos/$repoOwner/$repoName/releases/latest"
            val request = Request.Builder()
                .url(url)
                .header("Accept", "application/vnd.github.v3+json")
                .header("User-Agent", "SmartVPNWizard-Android")
                .build()

            val response = client.newCall(request).execute()
            if (!response.isSuccessful) return@withContext null
            val body = response.body?.string() ?: return@withContext null
            val release = gson.fromJson(body, GitHubRelease::class.java)

            val currentVersion = getCurrentAppVersion()
            val remoteVersion = release.tagName.trimStart('v', 'V')

            if (isNewerVersion(remoteVersion, currentVersion)) {
                val apkAsset = release.assets.firstOrNull { it.name.endsWith(".apk", ignoreCase = true) }
                if (apkAsset != null) {
                    return@withContext Pair(release, apkAsset)
                }
            }
            null
        } catch (e: Exception) {
            null
        }
    }

    fun getCurrentAppVersion(): String {
        return try {
            val pInfo = context.packageManager.getPackageInfo(context.packageName, 0)
            pInfo.versionName ?: "1.0.0"
        } catch (e: Exception) {
            "1.0.0"
        }
    }

    fun isNewerVersion(remote: String, current: String): Boolean {
        val remoteParts = remote.split(".").mapNotNull { it.filter { c -> c.isDigit() }.toIntOrNull() }
        val currentParts = current.split(".").mapNotNull { it.filter { c -> c.isDigit() }.toIntOrNull() }

        val maxLen = maxOf(remoteParts.size, currentParts.size)
        for (i in 0 until maxLen) {
            val r = remoteParts.getOrElse(i) { 0 }
            val c = currentParts.getOrElse(i) { 0 }
            if (r > c) return true
            if (r < c) return false
        }
        return false
    }

    private fun showUpdateDialog(release: GitHubRelease, downloadUrl: String, apkFileName: String) {
        val view = LayoutInflater.from(context).inflate(R.layout.dialog_update, null)
        val tvVersion = view.findViewById<TextView>(R.id.tvUpdateVersion)
        val tvChangelog = view.findViewById<TextView>(R.id.tvChangelog)
        val pbDownload = view.findViewById<ProgressBar>(R.id.pbDownload)
        val tvStatus = view.findViewById<TextView>(R.id.tvDownloadStatus)
        val btnCancel = view.findViewById<MaterialButton>(R.id.btnUpdateCancel)
        val btnAction = view.findViewById<MaterialButton>(R.id.btnUpdateAction)

        tvVersion.text = "Версия: ${release.tagName}"
        tvChangelog.text = release.body ?: "Новое обновление с улучшениями стабильности и оптимизациями маршрутизации."

        val dialog = MaterialAlertDialogBuilder(context)
            .setView(view)
            .setCancelable(false)
            .create()

        btnCancel.setOnClickListener {
            dialog.dismiss()
        }

        btnAction.setOnClickListener {
            btnAction.isEnabled = false
            btnCancel.isEnabled = false
            pbDownload.visibility = View.VISIBLE
            tvStatus.visibility = View.VISIBLE
            tvStatus.text = "Подключение..."

            kotlinx.coroutines.CoroutineScope(Dispatchers.IO).launch {
                downloadAndInstallApk(downloadUrl, apkFileName, pbDownload, tvStatus, dialog)
            }
        }

        dialog.show()
    }

    private suspend fun downloadAndInstallApk(
        url: String,
        fileName: String,
        progressBar: ProgressBar,
        statusText: TextView,
        dialog: androidx.appcompat.app.AlertDialog
    ) {
        try {
            val request = Request.Builder().url(url).build()
            val response = client.newCall(request).execute()

            if (!response.isSuccessful) {
                withContext(Dispatchers.Main) {
                    Toast.makeText(context, "Ошибка загрузки (${response.code})", Toast.LENGTH_SHORT).show()
                    dialog.dismiss()
                }
                return
            }

            val body = response.body ?: return
            val totalBytes = body.contentLength()
            val destDir = context.getExternalFilesDir(null) ?: context.cacheDir
            val apkFile = File(destDir, fileName)

            body.byteStream().use { input ->
                FileOutputStream(apkFile).use { output ->
                    val buffer = ByteArray(8192)
                    var bytesRead: Int
                    var downloaded: Long = 0

                    while (input.read(buffer).also { bytesRead = it } != -1) {
                        output.write(buffer, 0, bytesRead)
                        downloaded += bytesRead

                        if (totalBytes > 0) {
                            val progress = ((downloaded * 100) / totalBytes).toInt()
                            withContext(Dispatchers.Main) {
                                progressBar.progress = progress
                                val mbDownloaded = String.format("%.1f", downloaded / (1024.0 * 1024.0))
                                val mbTotal = String.format("%.1f", totalBytes / (1024.0 * 1024.0))
                                statusText.text = "$mbDownloaded MB / $mbTotal MB ($progress%)"
                            }
                        }
                    }
                    output.flush()
                }
            }

            withContext(Dispatchers.Main) {
                dialog.dismiss()
                promptInstall(apkFile)
            }

        } catch (e: Exception) {
            e.printStackTrace()
            withContext(Dispatchers.Main) {
                Toast.makeText(context, "Сбой при загрузке: ${e.localizedMessage}", Toast.LENGTH_LONG).show()
                dialog.dismiss()
            }
        }
    }

    fun promptInstall(apkFile: File) {
        if (!apkFile.exists()) return

        // For Android 8.0 (API 26) and above, check if unknown sources permission is granted
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            if (!context.packageManager.canRequestPackageInstalls()) {
                val intent = Intent(Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES).apply {
                    data = Uri.parse("package:${context.packageName}")
                    addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                }
                context.startActivity(intent)
                Toast.makeText(context, "Разрешите установку из этого источника для обновления", Toast.LENGTH_LONG).show()
                return
            }
        }

        val apkUri = FileProvider.getUriForFile(
            context,
            "${context.packageName}.fileprovider",
            apkFile
        )

        val installIntent = Intent(Intent.ACTION_VIEW).apply {
            setDataAndType(apkUri, "application/vnd.android.package-archive")
            addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        }

        context.startActivity(installIntent)
    }
}
