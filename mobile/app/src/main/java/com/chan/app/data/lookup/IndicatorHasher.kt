package com.chan.app.data.lookup

import com.chan.app.domain.LookupType
import java.security.MessageDigest
import java.text.Normalizer
import java.util.Locale

/** The value the user typed is not a usable account, phone number, or link. */
class IndicatorInvalid(val kind: String) : Exception(kind)

/**
 * The client half of the k-anonymity protocol (§A6, invariant I4).
 *
 * The server must never learn what a person looked up. That is achieved by
 * sending five hex characters of a hash and comparing the full digest here — so
 * the normalisation below has to match the web client and `chan_ml.redact`
 * exactly, or the same account would hash differently on two platforms and the
 * comparison would silently never match.
 */
object IndicatorHasher {

    /** How many hex characters of the digest may leave the device. Never more. */
    const val PREFIX_LENGTH = 5

    fun normalize(type: LookupType, value: String): String = when (type) {
        LookupType.PHONE -> normalizePhone(value)
        LookupType.ACCOUNT -> normalizeAccount(value)
        LookupType.URL -> normalizeUrl(value)
    }

    /** `SHA256("chan:" + kind + ":v1:" + normalizedValue)`, lowercase hex. */
    fun hash(type: LookupType, value: String): String {
        val normalized = normalize(type, value)
        val digest = MessageDigest.getInstance("SHA-256")
            .digest("chan:${type.wireValue}:v1:$normalized".toByteArray(Charsets.UTF_8))
        return digest.joinToString("") { byte -> "%02x".format(byte) }
    }

    /** The only part of [hash] that is allowed onto the network. */
    fun prefixOf(fullHash: String): String = fullHash.take(PREFIX_LENGTH)

    private fun normalizePhone(value: String): String {
        var normalized = Normalizer.normalize(value, Normalizer.Form.NFKC).trim()
        if (normalized.startsWith("+")) normalized = normalized.substring(1)
        var digits = normalized.replace(PHONE_SEPARATORS, "")
        if (digits.startsWith("0084")) {
            digits = digits.substring(2)
        } else if (digits.startsWith("0") && digits.length == 10) {
            digits = "84${digits.substring(1)}"
        }
        if (!DIGITS_8_TO_15.matches(digits)) throw IndicatorInvalid("invalid_phone")
        return digits
    }

    private fun normalizeAccount(value: String): String {
        val normalized = Normalizer.normalize(value, Normalizer.Form.NFKC)
            .trim()
            .uppercase(Locale.ROOT)
            .replace(ACCOUNT_SEPARATORS, "")
        if (!ACCOUNT_SHAPE.matches(normalized)) throw IndicatorInvalid("invalid_account")
        return normalized
    }

    private fun normalizeUrl(value: String): String {
        val trimmed = value.trim()
        if (trimmed.isEmpty()) throw IndicatorInvalid("invalid_http_url")
        val raw = if (trimmed.contains("://")) trimmed else "https://$trimmed"
        val parsed = runCatching { java.net.URI(raw) }.getOrNull() ?: throw IndicatorInvalid("invalid_http_url")
        val scheme = parsed.scheme?.lowercase(Locale.ROOT) ?: throw IndicatorInvalid("invalid_http_url")
        val host = parsed.host?.lowercase(Locale.ROOT) ?: throw IndicatorInvalid("invalid_http_url")
        if (scheme != "http" && scheme != "https") throw IndicatorInvalid("invalid_http_url")
        if (!host.contains(".")) throw IndicatorInvalid("invalid_http_url")

        val port = parsed.port
        val defaultPort = (scheme == "http" && port == 80) || (scheme == "https" && port == 443)
        val authority = if (port == -1 || defaultPort) host else "$host:$port"
        val path = parsed.rawPath.takeIf { !it.isNullOrEmpty() } ?: "/"
        val query = parsed.rawQuery?.let { "?$it" }.orEmpty()
        return "$scheme://$authority$path$query"
    }

    private val PHONE_SEPARATORS = Regex("[\\s().-]")
    private val ACCOUNT_SEPARATORS = Regex("[\\s.-]")
    private val DIGITS_8_TO_15 = Regex("^\\d{8,15}$")
    private val ACCOUNT_SHAPE = Regex("^[A-Z0-9]{6,34}$")
}
