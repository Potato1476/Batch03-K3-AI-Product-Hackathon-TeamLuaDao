package com.chan.app

import com.chan.app.data.net.ChanApi
import com.chan.app.data.net.ChanApiService
import com.chan.app.data.net.ChanNetwork
import com.chan.app.data.net.DeviceTokenProvider
import com.chan.app.data.token.InMemoryDeviceTokenStore
import okhttp3.OkHttpClient
import okhttp3.mockwebserver.Dispatcher
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import okhttp3.mockwebserver.RecordedRequest
import java.util.concurrent.TimeUnit

/**
 * A real HTTP stack pointed at MockWebServer.
 *
 * The tests exercise the production Retrofit interface, converter, and
 * authentication path rather than a hand-rolled double: the invariants worth
 * proving (exact request schema, one-shot 401 recovery, five-hex prefixes) all
 * live in the bytes that go over the wire.
 */
class ApiTestHarness {

    val server = MockWebServer()

    /** Routes by path so token and analyze responses can be queued separately. */
    val router = PathDispatcher()

    val tokenStore = InMemoryDeviceTokenStore()

    /**
     * The production client with test-sized timeouts. Derived with `newBuilder`
     * on purpose: every transport policy that matters — above all
     * `retryOnConnectionFailure(false)` (§C1) — is inherited rather than
     * re-declared, so a test cannot pass against settings the app does not use.
     */
    private val client: OkHttpClient = ChanNetwork.client().newBuilder()
        .connectTimeout(2, TimeUnit.SECONDS)
        .readTimeout(5, TimeUnit.SECONDS)
        .callTimeout(10, TimeUnit.SECONDS)
        .build()

    val service: ChanApiService by lazy { ChanNetwork.service(server.url("/").toString(), client) }
    val tokens: DeviceTokenProvider by lazy { DeviceTokenProvider(tokenStore, service) }
    val api: ChanApi by lazy { ChanApi(service, tokens) }

    init {
        server.dispatcher = router
    }

    fun shutdown() = server.shutdown()

    companion object {
        fun tokenResponse(token: String): MockResponse = MockResponse()
            .setResponseCode(201)
            .setHeader("Content-Type", "application/json")
            .setBody(
                """{"device_id":"dev_test","token":"$token","expires_at":"2026-10-28T08:08:43Z"}""",
            )

        fun json(code: Int, body: String): MockResponse = MockResponse()
            .setResponseCode(code)
            .setHeader("Content-Type", "application/json")
            .setBody(body)

        val ANALYZE_HIGH = """
            {
              "analysis_id": "an_test000001",
              "risk": "high",
              "score": 1.0,
              "signals": [
                {"code": "yeu_cau_bi_mat", "confidence": 1.0, "evidence": "chuyen <AMOUNT:trieu> vao <ACCOUNT>"}
              ],
              "explanation": "Người gửi yêu cầu giữ bí mật với gia đình.",
              "questions": ["Tại sao việc này lại không được nói với người thân?"],
              "verified_hotline": {"name": "Tổng cục Thuế", "number": "19008888"},
              "actions": ["report", "share_to_guardian"],
              "engine_version": "ml-0.3.0",
              "rule_bundle_version": "rb-2026-07-30"
            }
        """.trimIndent()
    }
}

/** Dispatches MockWebServer responses by request path, counting each hit. */
class PathDispatcher : Dispatcher() {

    private val queues = mutableMapOf<String, ArrayDeque<MockResponse>>()
    val requests = mutableListOf<RecordedRequest>()

    var tokenRequestCount = 0
        private set
    var analyzeRequestCount = 0
        private set
    var lookupRequestCount = 0
        private set

    fun enqueue(pathPrefix: String, response: MockResponse) {
        queues.getOrPut(pathPrefix) { ArrayDeque() }.addLast(response)
    }

    /** Answers every request for this path, however many arrive. */
    fun always(pathPrefix: String, response: () -> MockResponse) {
        standing[pathPrefix] = response
    }

    private val standing = mutableMapOf<String, () -> MockResponse>()

    override fun dispatch(request: RecordedRequest): MockResponse {
        val path = request.path.orEmpty()
        synchronized(this) {
            requests += request
            when {
                path.startsWith("/v1/devices/token") -> tokenRequestCount++
                path.startsWith("/v1/analyze") -> analyzeRequestCount++
                path.startsWith("/v1/lookup") -> lookupRequestCount++
            }
        }
        queues.entries.firstOrNull { path.startsWith(it.key) && it.value.isNotEmpty() }
            ?.let { return it.value.removeFirst() }
        standing.entries.firstOrNull { path.startsWith(it.key) }?.let { return it.value() }
        return MockResponse().setResponseCode(404).setBody("""{"detail":"not_found"}""")
    }

    fun requestsFor(pathPrefix: String): List<RecordedRequest> =
        requests.filter { it.path.orEmpty().startsWith(pathPrefix) }
}
