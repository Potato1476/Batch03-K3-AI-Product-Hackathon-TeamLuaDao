package com.chan.app.data.token

/**
 * Durable storage for the device token (§A3).
 *
 * The token is the device's only credential and is returned by the server
 * exactly once, so losing it costs a new device identity — but keeping it in
 * plaintext would hand it to anyone who can read app storage on a rooted phone.
 * The production implementation wraps it with an Android Keystore key.
 */
interface DeviceTokenStore {
    fun read(): String?
    fun write(token: String)
    fun clear()
}

/** In-memory store. Used by unit tests and by any build without a Keystore. */
class InMemoryDeviceTokenStore(initial: String? = null) : DeviceTokenStore {
    @Volatile
    private var token: String? = initial

    override fun read(): String? = token
    override fun write(token: String) {
        this.token = token
    }

    override fun clear() {
        token = null
    }
}
