package com.chan.app.data.net

import com.chan.app.data.token.DeviceTokenStore
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock

/** Raised when the Gateway would not issue a device identity. */
class DeviceTokenUnavailable(val status: Int) : Exception("device_token_unavailable")

/**
 * Owns the device's identity (§A3).
 *
 * A device token is the only credential the Android client has — there is no
 * compile-time API key. The token is returned once, stored encrypted, and
 * normally expires after 90 days.
 *
 * The mutex is the whole point of this class: several screens can start
 * authenticated work at the same moment, and without serialisation each would
 * mint a separate device identity, fragmenting rate limits and analytics for
 * one physical phone.
 */
class DeviceTokenProvider(
    private val store: DeviceTokenStore,
    private val service: ChanApiService,
    private val platform: String = "android",
) {

    private val mutex = Mutex()

    /** Returns the stored token, issuing one only if there is none. */
    suspend fun token(): String = mutex.withLock {
        store.read()?.takeIf { it.isNotBlank() } ?: issue()
    }

    /**
     * Discards [rejected] after the server refused it. A token issued by
     * another coroutine in the meantime is left alone.
     */
    suspend fun invalidate(rejected: String) = mutex.withLock {
        if (store.read() == rejected) store.clear()
    }

    private suspend fun issue(): String {
        val response = service.issueDeviceToken(DeviceTokenRequestDto(platform = platform, pushToken = null))
        val token = response.body()?.token
        if (!response.isSuccessful || token.isNullOrBlank()) {
            throw DeviceTokenUnavailable(response.code())
        }
        store.write(token)
        return token
    }
}
