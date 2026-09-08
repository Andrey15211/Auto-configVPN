package com.smartvpn.wizard.scanner

import android.content.Context
import android.content.pm.ApplicationInfo
import android.content.pm.PackageManager
import com.smartvpn.wizard.model.AppItem
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

class AppScanner(private val context: Context) {

    // Default package IDs for Russian services (Banks, Gov, Retail, Delivery, Media)
    val DEFAULT_DIRECT_PACKAGES = setOf(
        // Banks & Finance
        "ru.sberbankmobile",
        "com.idamob.tinkoff.android",
        "ru.vtb24.mobilebanking.android",
        "ru.alfabank.mobile.android",
        "ru.raiffeisennews",
        "ru.gazprombank.android.mobilebank.app",
        "ru.yoomoney.android",
        "com.bspb",
        "ru.sovcomcard.halva.v1",
        "ru.nspk.mirpay",
        "ru.sberbank.sberinvestor",

        // Government & Utilities
        "ru.rostel",
        "ru.gosuslugi.fito",
        "ru.gosuslugi.post",
        "ru.nalog.NalogFL",
        "ru.mos.app",
        "ru.mos.emias.app",

        // E-Commerce & Retail
        "com.wildberries.work",
        "ru.wildberries.buyer",
        "ru.ozon.app.android",
        "ru.yandex.market",
        "com.avito.android",
        "ru.dns.shop",
        "com.mvideo",
        "ru.eldorado",
        "ru.magnit.app",
        "ru.x5.delivery",
        "ru.perekrestok",
        "ru.samokat.app",
        "ru.vk.store",

        // Telecom & Transport
        "ru.yandex.taxi",
        "ru.yandex.yandexnavi",
        "ru.yandex.yandexmaps",
        "ru.yandex.searchplugin",
        "ru.mts.bank",
        "ru.mts.mymts",
        "ru.megafon.mlk",
        "ru.beeline.services",
        "ru.tele2.mytele2",
        "ru.t2.app",

        // Media & Social
        "com.vkontakte.android",
        "ru.ok.android",
        "ru.kinopoisk",
        "ru.rutube.app",
        "ru.yandex.music"
    )

    suspend fun getInstalledApps(): List<AppItem> = withContext(Dispatchers.IO) {
        val pm = context.packageManager
        val apps = pm.getInstalledApplications(PackageManager.GET_META_DATA)
        val result = mutableListOf<AppItem>()

        for (appInfo in apps) {
            // Check if application has a launchable intent or is a known direct package
            val launchIntent = pm.getLaunchIntentForPackage(appInfo.packageName)
            val isKnown = DEFAULT_DIRECT_PACKAGES.contains(appInfo.packageName)

            val isSystemApp = (appInfo.flags and ApplicationInfo.FLAG_SYSTEM) != 0
            val isUpdatedSystemApp = (appInfo.flags and ApplicationInfo.FLAG_UPDATED_SYSTEM_APP) != 0

            // Skip internal non-launchable background system packages unless they are in our direct list
            if (isSystemApp && !isUpdatedSystemApp && launchIntent == null && !isKnown) {
                continue
            }

            try {
                val label = pm.getApplicationLabel(appInfo).toString()
                val icon = pm.getApplicationIcon(appInfo)
                val isDirect = isKnown

                result.add(
                    AppItem(
                        name = label,
                        packageName = appInfo.packageName,
                        icon = icon,
                        isDirect = isDirect
                    )
                )
            } catch (e: Exception) {
                // Ignore individual package retrieval errors
            }
        }

        // Sort: direct apps first, then alphabetically by name
        result.sortedWith(compareByDescending<AppItem> { it.isDirect }.thenBy { it.name.lowercase() })
    }
}
