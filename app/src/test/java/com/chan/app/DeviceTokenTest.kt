package com.chan.app

import com.chan.app.data.net.AnalyzeRequestDto
import com.chan.app.data.net.ChanApiFailure
import com.chan.app.domain.FailureReason
import kotlinx.coroutines.async
import kotlinx.coroutines.awaitAll
import kotlinx.coroutines.test.runTest
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertThrows
import org.junit.Test
import java.util.concurrent.TimeUnit

/**
 * Device identity (§A3). The device token is the client's only credential, so
 * how many are minted and when they are replaced is a privacy question, not
 * just a correctness one: one phone that issues five identities fragments its
 * own rate limits and looks like five users to the server.
 */
class DeviceTokenTest {

    private val harness = ApiTestHarness()

    @After
    fun tearDown() = harness.shutdown()

    private fun analyzeRequest() = AnalyzeRequestDto(
        text = "nội dung cần kiểm tra",
        source = "android",
        inputMode = "manual",
        appPackage = null,
        localSignals = emptyList(),
        truncated = false,
        locale = "vi-VN",
    )

    @Test
    fun theDeviceTokenIsRequestedForTheAndroidPlatform() = runTest {
        harness.router.enqueue("/v1/devices/token", ApiTestHarness.tokenResponse("token-1"))
        harness.router.enqueue("/v1/analyze", ApiTestHarness.json(200, ApiTestHarness.ANALYZE_HIGH))

        harness.api.analyze(analyzeRequest())

        val request = harness.router.requestsFor("/v1/devices/token").single()
        val body = Json.parseToJsonElement(request.body.readUtf8()).jsonObject
        assertEquals("android", body.getValue("platform").jsonPrimitive.content)
        // `push_token` is sent explicitly as null: the server forbids extra keys
        // and CHAN has no push registration in Sprint 02.
        assertEquals(setOf("platform", "push_token"), body.keys)
        assertEquals("Bearer token-1", harness.router.requestsFor("/v1/analyze").single().getHeader("Authorization"))
    }

    @Test
    fun concurrentAuthenticatedCallsIssueOnlyOneToken() = runTest {
        // A slow token response widens the window in which a second caller could
        // start minting its own identity.
        harness.router.always("/v1/devices/token") {
            ApiTestHarness.tokenResponse("token-1").setBodyDelay(150, TimeUnit.MILLISECONDS)
        }
        harness.router.always("/v1/analyze") { ApiTestHarness.json(200, ApiTestHarness.ANALYZE_HIGH) }

        val calls = (1..4).map { async { harness.api.analyze(analyzeRequest()) } }
        calls.awaitAll()

        assertEquals("Exactly one device identity", 1, harness.router.tokenRequestCount)
        assertEquals(4, harness.router.analyzeRequestCount)
    }

    @Test
    fun oneUnauthorizedResponseReissuesTheTokenAndRetriesOnce() = runTest {
        harness.router.enqueue("/v1/devices/token", ApiTestHarness.tokenResponse("stale-token"))
        harness.router.enqueue("/v1/analyze", ApiTestHarness.json(401, """{"detail":"invalid_device_token"}"""))
        harness.router.enqueue("/v1/devices/token", ApiTestHarness.tokenResponse("fresh-token"))
        harness.router.enqueue("/v1/analyze", ApiTestHarness.json(200, ApiTestHarness.ANALYZE_HIGH))

        val response = harness.api.analyze(analyzeRequest())

        assertEquals("high", response.risk)
        assertEquals(2, harness.router.tokenRequestCount)
        assertEquals(2, harness.router.analyzeRequestCount)

        val authHeaders = harness.router.requestsFor("/v1/analyze").map { it.getHeader("Authorization") }
        assertEquals(listOf("Bearer stale-token", "Bearer fresh-token"), authHeaders)
        assertEquals("fresh-token", harness.tokenStore.read())
    }

    @Test
    fun aSecondUnauthorizedResponseStops() = runTest {
        harness.router.always("/v1/devices/token") { ApiTestHarness.tokenResponse("token-x") }
        harness.router.always("/v1/analyze") {
            ApiTestHarness.json(401, """{"detail":"invalid_device_token"}""")
        }

        val failure = assertThrows(ChanApiFailure::class.java) {
            kotlinx.coroutines.runBlocking { harness.api.analyze(analyzeRequest()) }
        }

        // Two attempts, never a third: retrying again would only mint identities
        // against a server that is refusing us for some other reason.
        assertEquals(2, harness.router.analyzeRequestCount)
        assertEquals(FailureReason.BACKEND_UNAVAILABLE, failure.reason)
    }

    @Test
    fun aRejectedTokenIsRemovedFromStorage() = runTest {
        harness.tokenStore.write("stale-token")
        harness.router.enqueue("/v1/analyze", ApiTestHarness.json(401, """{"detail":"invalid_device_token"}"""))
        harness.router.enqueue("/v1/devices/token", ApiTestHarness.tokenResponse("fresh-token"))
        harness.router.enqueue("/v1/analyze", ApiTestHarness.json(200, ApiTestHarness.ANALYZE_HIGH))

        harness.api.analyze(analyzeRequest())
        assertEquals("fresh-token", harness.tokenStore.read())
    }

    @Test
    fun aRateLimitedResponseBecomesItsOwnUserSafeReason() = runTest {
        harness.router.enqueue("/v1/devices/token", ApiTestHarness.tokenResponse("token-1"))
        harness.router.enqueue("/v1/analyze", ApiTestHarness.json(429, """{"detail":"rate_limited"}"""))

        val failure = assertThrows(ChanApiFailure::class.java) {
            kotlinx.coroutines.runBlocking { harness.api.analyze(analyzeRequest()) }
        }
        assertEquals(FailureReason.RATE_LIMITED, failure.reason)
    }

    @Test
    fun anEmptyStoreStartsWithNoIdentity() {
        assertNull(harness.tokenStore.read())
    }
}
