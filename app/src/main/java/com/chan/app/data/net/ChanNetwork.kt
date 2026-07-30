package com.chan.app.data.net

import kotlinx.serialization.json.Json
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import retrofit2.Retrofit
import com.jakewharton.retrofit2.converter.kotlinx.serialization.asConverterFactory
import java.util.concurrent.TimeUnit

/**
 * Builds the HTTP stack.
 *
 * There is deliberately **no logging interceptor** here, not even one
 * configured to `Level.NONE`. Message text, OTPs, account numbers, and lookup
 * prefixes all travel through this client; the only way to guarantee none of
 * them reaches Logcat is for the capability not to be wired up at all. A
 * privacy unit test fails the build if one is ever added.
 *
 * Timeouts are sized for a person waiting in front of the screen: a slow answer
 * is worse than an honest "máy chủ trả lời chậm".
 */
object ChanNetwork {

    private const val CONNECT_TIMEOUT_SECONDS = 10L
    private const val READ_TIMEOUT_SECONDS = 20L
    private const val WRITE_TIMEOUT_SECONDS = 15L
    private const val CALL_TIMEOUT_SECONDS = 25L

    /** Requests must be explicit; the server rejects unexpected fields. */
    val json: Json = Json {
        ignoreUnknownKeys = true
        encodeDefaults = true
        explicitNulls = true
    }

    fun client(): OkHttpClient = OkHttpClient.Builder()
        .connectTimeout(CONNECT_TIMEOUT_SECONDS, TimeUnit.SECONDS)
        .readTimeout(READ_TIMEOUT_SECONDS, TimeUnit.SECONDS)
        .writeTimeout(WRITE_TIMEOUT_SECONDS, TimeUnit.SECONDS)
        .callTimeout(CALL_TIMEOUT_SECONDS, TimeUnit.SECONDS)
        .retryOnConnectionFailure(true)
        .build()

    fun service(baseUrl: String, client: OkHttpClient = client()): ChanApiService = Retrofit.Builder()
        .baseUrl(baseUrl)
        .client(client)
        .addConverterFactory(json.asConverterFactory("application/json".toMediaType()))
        .build()
        .create(ChanApiService::class.java)
}
