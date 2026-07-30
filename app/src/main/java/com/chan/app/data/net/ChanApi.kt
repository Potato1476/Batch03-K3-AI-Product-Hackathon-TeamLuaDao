package com.chan.app.data.net

import com.chan.app.data.rules.CachedBundle
import com.chan.app.data.rules.RuleBundleFetcher
import com.chan.app.domain.FailureReason
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import retrofit2.Response
import java.io.IOException
import java.io.InterruptedIOException
import java.net.ConnectException
import java.net.SocketTimeoutException
import java.net.UnknownHostException

/** An API failure reduced to a safe reason. No status, body, or trace escapes. */
class ChanApiFailure(val reason: FailureReason) : Exception(reason.name)

/**
 * The authenticated API facade (§A3, §A5, §A6).
 *
 * Everything the repository needs, with two behaviours the raw Retrofit
 * interface cannot express:
 *
 *  - **one-shot 401 recovery.** A rejected token is discarded, a new one is
 *    issued, and the original request is replayed exactly once. A second 401 is
 *    returned to the caller: retrying again would only mint device identities
 *    against a server that is refusing us for some other reason.
 *  - **error reduction.** HTTP codes and bodies are turned into a
 *    [FailureReason] here so no status code, JSON, or identifier can reach the
 *    UI.
 */
class ChanApi(
    private val service: ChanApiService,
    private val tokens: DeviceTokenProvider,
) : RuleBundleFetcher {

    suspend fun analyze(request: AnalyzeRequestDto): AnalyzeResponseDto {
        val response = authorized { auth -> service.analyze(auth, request) }
        return response.body() ?: throw ChanApiFailure(FailureReason.UNEXPECTED)
    }

    suspend fun lookup(kind: String, prefix: String): LookupResponseDto {
        val response = authorized { auth -> service.lookup(auth, kind, prefix) }
        return response.body() ?: throw ChanApiFailure(FailureReason.UNEXPECTED)
    }

    override suspend fun fetch(etag: String?): CachedBundle? {
        val response = try {
            service.ruleBundle(etag)
        } catch (error: IOException) {
            throw ChanApiFailure(transportReason(error))
        }
        if (response.code() == HTTP_NOT_MODIFIED) return null
        val body = response.body()?.string()
        if (!response.isSuccessful || body.isNullOrBlank()) {
            throw ChanApiFailure(reasonFor(response.code(), null))
        }
        return CachedBundle(body, response.headers()[HEADER_ETAG])
    }

    private suspend fun <T> authorized(call: suspend (String) -> Response<T>): Response<T> {
        val token = obtainToken()
        val first = attempt(call, token)
        if (first.code() != HTTP_UNAUTHORIZED) return checked(first)

        // Exactly one recovery attempt.
        tokens.invalidate(token)
        val replacement = obtainToken()
        val second = attempt(call, replacement)
        return checked(second)
    }

    private suspend fun obtainToken(): String = try {
        tokens.token()
    } catch (error: DeviceTokenUnavailable) {
        throw ChanApiFailure(reasonFor(error.status, null))
    } catch (error: IOException) {
        throw ChanApiFailure(transportReason(error))
    }

    private suspend fun <T> attempt(call: suspend (String) -> Response<T>, token: String): Response<T> = try {
        call("Bearer $token")
    } catch (error: IOException) {
        throw ChanApiFailure(transportReason(error))
    }

    private fun <T> checked(response: Response<T>): Response<T> {
        if (response.isSuccessful) return response
        val detail = response.errorBody()?.let { safeDetail(it.string()) }
        throw ChanApiFailure(reasonFor(response.code(), detail))
    }

    private companion object {
        const val HTTP_UNAUTHORIZED = 401
        const val HTTP_NOT_MODIFIED = 304
        const val HEADER_ETAG = "ETag"

        private val json = Json { ignoreUnknownKeys = true }

        /**
         * Reads the machine-readable `detail` code. A 422 answers with an array
         * of field positions instead of a string; that is not a code we act on,
         * so anything non-string is ignored rather than stringified.
         */
        fun safeDetail(body: String): String? = runCatching {
            (json.parseToJsonElement(body) as? JsonObject)
                ?.get("detail")
                ?.let { it as? JsonPrimitive }
                ?.takeIf { it.isString }
                ?.content
        }.getOrNull()

        fun transportReason(error: IOException): FailureReason = when (error) {
            is SocketTimeoutException, is InterruptedIOException -> FailureReason.TIMEOUT
            is UnknownHostException, is ConnectException -> FailureReason.OFFLINE
            else -> FailureReason.OFFLINE
        }

        fun reasonFor(status: Int, detail: String?): FailureReason = when {
            detail == "unknown_local_signal" -> FailureReason.BUNDLE_MISMATCH
            detail == "rule_bundle_unavailable" -> FailureReason.BACKEND_UNAVAILABLE
            status == 429 -> FailureReason.RATE_LIMITED
            status == 401 -> FailureReason.BACKEND_UNAVAILABLE
            status in 500..599 -> FailureReason.BACKEND_UNAVAILABLE
            status == 408 -> FailureReason.TIMEOUT
            else -> FailureReason.UNEXPECTED
        }
    }
}
