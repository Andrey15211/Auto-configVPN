package com.smartvpn.wizard.generator

import android.net.Uri
import android.util.Base64
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
    val fingerprint: String,
    val rawUri: String = ""
)

class SingBoxConfigGenerator {

    fun parseNodes(link: String): List<VlessNode> {
        val trimmed = link.trim()
        if (trimmed.startsWith("http://") || trimmed.startsWith("https://")) {
            val url = java.net.URL(trimmed)
            val conn = url.openConnection() as java.net.HttpURLConnection
            conn.setRequestProperty("User-Agent", "v2rayNG/1.8.5")
            conn.connectTimeout = 10000
            conn.readTimeout = 10000
            val raw = conn.inputStream.bufferedReader().use { it.readText().trim() }
            val decoded = try {
                val clean = raw.replace("\r", "").replace("\n", "").trim()
                String(Base64.decode(clean, Base64.DEFAULT), Charsets.UTF_8)
            } catch (e: Exception) {
                raw
            }
            val lines = decoded.lines().map { it.trim() }.filter { it.isNotBlank() }
            val nodes = mutableListOf<VlessNode>()
            for (line in lines) {
                if (line.startsWith("vless://")) {
                    try {
                        nodes.add(parseVlessUri(line))
                    } catch (_: Exception) {}
                }
            }
            if (nodes.isEmpty()) {
                throw IllegalArgumentException("В подписке не найдено подходящих узлов VLESS")
            }
            return nodes
        }

        if (trimmed.startsWith("vless://")) {
            return listOf(parseVlessUri(trimmed))
        }

        throw IllegalArgumentException("Ссылка должна начинаться с vless:// или https://")
    }

    fun parseLinkOrSubscription(link: String): VlessNode {
        return parseNodes(link).first()
    }

    fun parseVlessUri(link: String): VlessNode {
        val trimmed = link.trim()
        if (!trimmed.startsWith("vless://")) {
            throw IllegalArgumentException("Ссылка должна начинаться с vless:// или https://")
        }

        val uri = Uri.parse(trimmed)
        val userInfo = uri.userInfo ?: ""
        val host = uri.host ?: ""
        val port = if (uri.port != -1) uri.port else 443
        val fragment = uri.fragment ?: "Smart Mobile Node"
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
            fingerprint = fp,
            rawUri = trimmed
        )
    }

    fun buildRawLinks(nodes: List<VlessNode>): String {
        return nodes.joinToString("\n") { it.rawUri }
    }

    fun buildBase64Subscription(nodes: List<VlessNode>): String {
        val allLinks = buildRawLinks(nodes)
        return Base64.encodeToString(allLinks.toByteArray(Charsets.UTF_8), Base64.NO_WRAP)
    }

    fun generateSingBoxJson(nodes: List<VlessNode>, directPackages: List<String>): String {
        val root = mutableMapOf<String, Any>()
        root["log"] = mapOf("level" to "warn")

        root["dns"] = mapOf(
            "servers" to listOf(
                mapOf("tag" to "remote-dns", "address" to "https://1.1.1.1/dns-query", "detour" to "proxy"),
                mapOf("tag" to "local-dns", "address" to "77.88.8.8", "detour" to "direct")
            ),
            "rules" to listOf(
                mapOf("outbound" to "any", "server" to "local-dns"),
                mapOf(
                    "domain_suffix" to listOf(".ru", ".su", ".xn--p1ai", "yandex.ru", "yandex.net", "vk.com", "vk.ru", "mail.ru", "gosuslugi.ru", "ozon.ru", "wildberries.ru", "sberbank.ru", "tbank.ru", "tinkoff.ru", "avito.ru", "kinopoisk.ru"),
                    "server" to "local-dns"
                ),
                mapOf("geosite" to listOf("category-ru"), "server" to "local-dns")
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

        if (nodes.size <= 1) {
            val node = nodes.first()
            outbounds.add(buildSingBoxOutbound(node, "proxy"))
        } else {
            val nodeTags = mutableListOf<String>()
            for ((index, node) in nodes.withIndex()) {
                val tag = if (node.name.isNotBlank()) node.name else "Server ${index + 1}"
                nodeTags.add(tag)
                outbounds.add(buildSingBoxOutbound(node, tag))
            }
            val selector = mapOf(
                "type" to "selector",
                "tag" to "proxy",
                "outbounds" to nodeTags,
                "default" to (nodeTags.firstOrNull() ?: "direct")
            )
            outbounds.add(0, selector)
        }

        outbounds.add(mapOf("type" to "direct", "tag" to "direct"))
        outbounds.add(mapOf("type" to "block", "tag" to "block"))
        outbounds.add(mapOf("type" to "dns", "tag" to "dns-out"))
        root["outbounds"] = outbounds

        val rules = mutableListOf<Map<String, Any>>()
        rules.add(mapOf("protocol" to "dns", "outbound" to "dns-out"))

        if (directPackages.isNotEmpty()) {
            rules.add(mapOf(
                "package_name" to directPackages,
                "outbound" to "direct"
            ))
        }

        rules.add(mapOf(
            "domain_suffix" to listOf(".ru", ".su", ".xn--p1ai", "yandex.ru", "yandex.net", "vk.com", "vk.ru", "mail.ru", "gosuslugi.ru", "ozon.ru", "wildberries.ru", "sberbank.ru", "tbank.ru", "tinkoff.ru", "avito.ru", "kinopoisk.ru"),
            "outbound" to "direct"
        ))
        rules.add(mapOf("geosite" to listOf("category-ru"), "outbound" to "direct"))
        rules.add(mapOf("geoip" to listOf("ru", "private"), "outbound" to "direct"))

        root["route"] = mapOf(
            "auto_detect_interface" to true,
            "rules" to rules,
            "final" to "proxy"
        )

        val gson = GsonBuilder().setPrettyPrinting().disableHtmlEscaping().create()
        return gson.toJson(root)
    }

    fun generateConfigJson(node: VlessNode, directPackages: List<String>): String {
        return generateSingBoxJson(listOf(node), directPackages)
    }

    private fun buildSingBoxOutbound(node: VlessNode, tag: String): Map<String, Any> {
        val proxyMap = mutableMapOf<String, Any>(
            "type" to "vless",
            "tag" to tag,
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
        return proxyMap
    }

    fun generateClashYaml(nodes: List<VlessNode>): String {
        val sb = StringBuilder()
        sb.append("port: 7890\n")
        sb.append("socks-port: 7891\n")
        sb.append("allow-lan: false\n")
        sb.append("mode: rule\n")
        sb.append("log-level: info\n")
        sb.append("unified-delay: true\n\n")

        sb.append("dns:\n")
        sb.append("  enable: true\n")
        sb.append("  listen: :1053\n")
        sb.append("  ipv6: false\n")
        sb.append("  enhanced-mode: fake-ip\n")
        sb.append("  fake-ip-range: 198.18.0.1/16\n")
        sb.append("  nameserver:\n")
        sb.append("    - 77.88.8.8\n")
        sb.append("    - 1.1.1.1\n\n")

        sb.append("tun:\n")
        sb.append("  enable: true\n")
        sb.append("  stack: system\n")
        sb.append("  auto-route: true\n")
        sb.append("  auto-redirect: true\n")
        sb.append("  auto-detect-interface: true\n")
        sb.append("  dns-hijack:\n")
        sb.append("    - any:53\n")
        sb.append("    - tcp://any:53\n\n")

        sb.append("proxies:\n")
        val proxyNames = mutableListOf<String>()
        for ((idx, node) in nodes.withIndex()) {
            val safeName = if (node.name.isNotBlank()) node.name.replace("\"", "\\\"") else "Node ${idx + 1}"
            proxyNames.add(safeName)
            sb.append("  - name: \"$safeName\"\n")
            sb.append("    type: vless\n")
            sb.append("    server: ${node.server}\n")
            sb.append("    port: ${node.port}\n")
            sb.append("    uuid: ${node.uuid}\n")
            sb.append("    network: tcp\n")
            sb.append("    udp: true\n")
            sb.append("    tls: true\n")
            sb.append("    flow: ${node.flow}\n")
            sb.append("    servername: ${node.serverName}\n")
            sb.append("    reality-opts:\n")
            sb.append("      public-key: ${node.publicKey}\n")
            sb.append("      short-id: ${node.shortId}\n")
            sb.append("    client-fingerprint: ${node.fingerprint}\n")
        }

        sb.append("\nproxy-groups:\n")
        sb.append("  - name: PROXY\n")
        sb.append("    type: select\n")
        sb.append("    proxies:\n")
        for (name in proxyNames) {
            sb.append("      - \"$name\"\n")
        }

        sb.append("\nrules:\n")
        // Russian TLDs
        sb.append("  - DOMAIN-SUFFIX,ru,DIRECT\n")
        sb.append("  - DOMAIN-SUFFIX,su,DIRECT\n")
        sb.append("  - DOMAIN-SUFFIX,xn--p1ai,DIRECT\n")
        // Major Russian Services & Infrastructure
        sb.append("  - DOMAIN-SUFFIX,yandex.ru,DIRECT\n")
        sb.append("  - DOMAIN-SUFFIX,yandex.net,DIRECT\n")
        sb.append("  - DOMAIN-SUFFIX,ya.ru,DIRECT\n")
        sb.append("  - DOMAIN-SUFFIX,vk.com,DIRECT\n")
        sb.append("  - DOMAIN-SUFFIX,vk.ru,DIRECT\n")
        sb.append("  - DOMAIN-SUFFIX,mail.ru,DIRECT\n")
        sb.append("  - DOMAIN-SUFFIX,ok.ru,DIRECT\n")
        sb.append("  - DOMAIN-SUFFIX,gosuslugi.ru,DIRECT\n")
        sb.append("  - DOMAIN-SUFFIX,sberbank.ru,DIRECT\n")
        sb.append("  - DOMAIN-SUFFIX,sber.ru,DIRECT\n")
        sb.append("  - DOMAIN-SUFFIX,tinkoff.ru,DIRECT\n")
        sb.append("  - DOMAIN-SUFFIX,tbank.ru,DIRECT\n")
        sb.append("  - DOMAIN-SUFFIX,alfabank.ru,DIRECT\n")
        sb.append("  - DOMAIN-SUFFIX,vtb.ru,DIRECT\n")
        sb.append("  - DOMAIN-SUFFIX,ozon.ru,DIRECT\n")
        sb.append("  - DOMAIN-SUFFIX,wildberries.ru,DIRECT\n")
        sb.append("  - DOMAIN-SUFFIX,avito.ru,DIRECT\n")
        sb.append("  - DOMAIN-SUFFIX,kinopoisk.ru,DIRECT\n")
        sb.append("  - DOMAIN-SUFFIX,rutube.ru,DIRECT\n")
        sb.append("  - DOMAIN-SUFFIX,dzen.ru,DIRECT\n")
        sb.append("  - DOMAIN-SUFFIX,2gis.ru,DIRECT\n")
        sb.append("  - DOMAIN-SUFFIX,mos.ru,DIRECT\n")
        sb.append("  - DOMAIN-SUFFIX,spb.ru,DIRECT\n")
        sb.append("  - DOMAIN-SUFFIX,nalog.gov.ru,DIRECT\n")
        sb.append("  - DOMAIN-SUFFIX,cbr.ru,DIRECT\n")
        sb.append("  - DOMAIN-SUFFIX,hh.ru,DIRECT\n")
        sb.append("  - DOMAIN-SUFFIX,auto.ru,DIRECT\n")
        sb.append("  - DOMAIN-SUFFIX,kp.ru,DIRECT\n")
        sb.append("  - DOMAIN-SUFFIX,rbc.ru,DIRECT\n")
        sb.append("  - DOMAIN-SUFFIX,ria.ru,DIRECT\n")
        sb.append("  - DOMAIN-SUFFIX,tass.ru,DIRECT\n")
        sb.append("  - DOMAIN-SUFFIX,ozonusercontent.com,DIRECT\n")
        sb.append("  - DOMAIN-SUFFIX,wbstatic.net,DIRECT\n")
        sb.append("  - DOMAIN-SUFFIX,yandex.com,DIRECT\n")
        sb.append("  - DOMAIN-SUFFIX,aeza.net,DIRECT\n")
        // Local and Private Networks (Self-contained, NO MMDB dependency)
        sb.append("  - IP-CIDR,127.0.0.0/8,DIRECT,no-resolve\n")
        sb.append("  - IP-CIDR,10.0.0.0/8,DIRECT,no-resolve\n")
        sb.append("  - IP-CIDR,172.16.0.0/12,DIRECT,no-resolve\n")
        sb.append("  - IP-CIDR,192.168.0.0/16,DIRECT,no-resolve\n")
        sb.append("  - IP-CIDR,100.64.0.0/10,DIRECT,no-resolve\n")
        // Everything else -> PROXY
        sb.append("  - MATCH,PROXY\n")

        return sb.toString()
    }
}
