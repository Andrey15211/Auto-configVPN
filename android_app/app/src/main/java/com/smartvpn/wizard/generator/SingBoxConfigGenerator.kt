package com.smartvpn.wizard.generator

import android.net.Uri
import com.google.gson.GsonBuilder
import java.net.URLDecoder

data class VlessNode(
    val name: String,
    val server: String,
    val port: Int,
    val uuid: String,
    val flow: String,
    val publicKey: String,
    val shortId: String,
    val serverName: String,
    val fingerprint: String
)

class SingBoxConfigGenerator {

    fun parseVlessUri(link: String): VlessNode {
        val trimmed = link.trim()
        if (!trimmed.startsWith("vless://")) {
            throw IllegalArgumentException("Ссылка должна начинаться с vless://")
        }

        // Format: vless://uuid@host:port?params#name
        val uri = Uri.parse(trimmed)
        val userInfo = uri.userInfo ?: ""
        val host = uri.host ?: ""
        val port = if (uri.port != -1) uri.port else 443
        val fragment = uri.fragment ?: "Smart Mobile VPN"
        val name = try { URLDecoder.decode(fragment, "UTF-8") } catch (e: Exception) { fragment }

        val flow = uri.getQueryParameter("flow") ?: "xtls-rprx-vision"
        val pbk = uri.getQueryParameter("pbk") ?: ""
        val sid = uri.getQueryParameter("sid") ?: ""
        val sni = uri.getQueryParameter("sni") ?: "gateway.icloud.com"
        val fp = uri.getQueryParameter("fp") ?: "chrome"

        return VlessNode(
            name = name,
            server = host,
            port = port,
            uuid = userInfo,
            flow = flow,
            publicKey = pbk,
            shortId = sid,
            serverName = sni,
            fingerprint = fp
        )
    }

    fun generateConfigJson(node: VlessNode, directPackages: List<String>): String {
        val root = mutableMapOf<String, Any>()

        root["log"] = mapOf("level" to "warn")

        root["dns"] = mapOf(
            "servers" to listOf(
                mapOf("tag" to "remote-dns", "address" to "https://1.1.1.1/dns-query", "detour" to "proxy"),
                mapOf("tag" to "local-dns", "address" to "77.88.8.8", "detour" to "direct")
            ),
            "rules" to listOf(
                mapOf("outbound" to "any", "server" to "local-dns"),
                mapOf("geosite" to listOf("category-ru", "gov-ru"), "server" to "local-dns")
            )
        )

        root["inbounds"] = listOf(
            mapOf(
                "type" to "tun",
                "tag" to "tun-in",
                "interface_name" to "tun0",
                "inet4_address" to "172.19.0.1/30",
                "auto_route" to true,
                "strict_route" to true,
                "stack" to "system",
                "sniff" to true
            )
        )

        val outbounds = mutableListOf<Map<String, Any>>()

        // Proxy VLESS Outbound
        val proxyMap = mutableMapOf<String, Any>(
            "type" to "vless",
            "tag" to "proxy",
            "server" to node.server,
            "server_port" to node.port,
            "uuid" to node.uuid,
            "flow" to node.flow,
            "packet_encoding" to "xudp"
        )

        val tlsMap = mutableMapOf<String, Any>(
            "enabled" to true,
            "server_name" to node.serverName,
            "utls" to mapOf("enabled" to true, "fingerprint" to node.fingerprint)
        )

        if (node.publicKey.isNotEmpty()) {
            tlsMap["reality"] = mapOf(
                "enabled" to true,
                "public_key" to node.publicKey,
                "short_id" to node.shortId
            )
        }
        proxyMap["tls"] = tlsMap
        outbounds.add(proxyMap)

        outbounds.add(mapOf("type" to "direct", "tag" to "direct"))
        outbounds.add(mapOf("type" to "block", "tag" to "block"))
        outbounds.add(mapOf("type" to "dns", "tag" to "dns-out"))
        root["outbounds"] = outbounds

        // Routing Rules
        val rules = mutableListOf<Map<String, Any>>()
        rules.add(mapOf("protocol" to "dns", "outbound" to "dns-out"))

        // Add package_name direct routing for selected Android apps
        if (directPackages.isNotEmpty()) {
            rules.add(mapOf(
                "package_name" to directPackages,
                "outbound" to "direct"
            ))
        }

        // Direct routing for Russian domains & geoip
        rules.add(mapOf("geosite" to listOf("category-ru", "gov-ru"), "outbound" to "direct"))
        rules.add(mapOf("geoip" to listOf("ru", "private"), "outbound" to "direct"))

        root["route"] = mapOf(
            "auto_detect_interface" to true,
            "rules" to rules,
            "final" to "proxy"
        )

        val gson = GsonBuilder().setPrettyPrinting().disableHtmlEscaping().create()
        return gson.toJson(root)
    }
}
