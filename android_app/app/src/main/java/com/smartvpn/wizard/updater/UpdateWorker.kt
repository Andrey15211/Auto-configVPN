package com.smartvpn.wizard.updater

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.work.CoroutineWorker
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.WorkerParameters
import com.smartvpn.wizard.MainActivity
import java.util.Calendar
import java.util.concurrent.TimeUnit

class UpdateWorker(
    private val context: Context,
    workerParams: WorkerParameters
) : CoroutineWorker(context, workerParams) {

    companion object {
        const val WORK_NAME = "PeriodicUpdateCheckWork"
        const val CHANNEL_ID = "updates_channel"
        const val NOTIFICATION_ID = 1001

        fun schedulePeriodicCheck(context: Context) {
            val initialDelayMillis = calculateDelayToNextTargetTime()

            val workRequest = PeriodicWorkRequestBuilder<UpdateWorker>(12, TimeUnit.HOURS)
                .setInitialDelay(initialDelayMillis, TimeUnit.MILLISECONDS)
                .build()

            WorkManager.getInstance(context).enqueueUniquePeriodicWork(
                WORK_NAME,
                ExistingPeriodicWorkPolicy.KEEP,
                workRequest
            )
        }

        private fun calculateDelayToNextTargetTime(): Long {
            val now = Calendar.getInstance()
            val hour = now.get(Calendar.HOUR_OF_DAY)

            val target = Calendar.getInstance().apply {
                set(Calendar.MINUTE, 0)
                set(Calendar.SECOND, 0)
                set(Calendar.MILLISECOND, 0)
                if (hour < 12) {
                    set(Calendar.HOUR_OF_DAY, 12) // 12:00 PM
                } else {
                    add(Calendar.DAY_OF_YEAR, 1)
                    set(Calendar.HOUR_OF_DAY, 0) // 12:00 AM (midnight)
                }
            }
            return target.timeInMillis - now.timeInMillis
        }
    }

    override suspend fun doWork(): Result {
        val checker = GitHubUpdateChecker(context)
        val releaseInfo = checker.fetchLatestRelease()

        if (releaseInfo != null) {
            val (release, _) = releaseInfo
            showUpdateNotification(release.tagName, release.body)
        }

        return Result.success()
    }

    private fun showUpdateNotification(tagName: String, changelog: String?) {
        val notificationManager = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                "Обновления Auto-configVPN",
                NotificationManager.IMPORTANCE_DEFAULT
            ).apply {
                description = "Уведомления о новых версиях и патчах Auto-configVPN"
            }
            notificationManager.createNotificationChannel(channel)
        }

        val intent = Intent(context, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
            putExtra("EXTRA_SHOW_UPDATE", true)
        }

        val pendingIntent = PendingIntent.getActivity(
            context,
            0,
            intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        val notification = NotificationCompat.Builder(context, CHANNEL_ID)
            .setSmallIcon(android.R.drawable.stat_sys_download)
            .setContentTitle("Доступно обновление $tagName")
            .setContentText(changelog?.take(100) ?: "Новая версия сплит-туннелирования готова к установке.")
            .setPriority(NotificationCompat.PRIORITY_DEFAULT)
            .setAutoCancel(true)
            .setContentIntent(pendingIntent)
            .build()

        notificationManager.notify(NOTIFICATION_ID, notification)
    }
}
