package com.chan.app

import com.chan.app.data.LiveChanRepository
import com.chan.app.data.lookup.IndicatorHasher
import com.chan.app.data.rules.BootstrapBundleSource
import com.chan.app.data.rules.CachedBundle
import com.chan.app.data.rules.FileBundleCache
import com.chan.app.data.rules.RuleBundleFetcher
import com.chan.app.data.rules.RuleBundleStore
import com.chan.app.domain.ChanOutcome
import com.chan.app.domain.InputMode
import com.chan.app.domain.LookupType
import com.chan.app.domain.Risk
import kotlinx.coroutines.test.runTest
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import okhttp3.mockwebserver.RecordedRequest
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.rules.TemporaryFolder
import java.io.IOException

/**
 * End-to-end behaviour of the production repository: the on-device gate, the
 * exact request schema, and the k-anonymity lookup.
 *
 * The assertions that matter most are the negative ones — the requests that
 * must *not* happen.
 */
class LiveChanRepositoryTest {

    @get:Rule
    val temporaryFolder = TemporaryFolder()

    private val harness = ApiTestHarness()

    @After
    fun tearDown() = harness.shutdown()

    private fun repository(): LiveChanRepository {
        val bundles = RuleBundleStore(
            bootstrap = BootstrapBundleSource { TestBundles.bootstrapJson() },
            cache = FileBundleCache(temporaryFolder.newFolder()),
            // Offline: the test exercises the bundle that ships in the APK.
            fetcher = object : RuleBundleFetcher {
                override suspend fun fetch(etag: String?): CachedBundle? = throw IOException("offline")
            },
        )
        return LiveChanRepository(harness.api, bundles, now = { FIXED_NOW })
    }

    private fun readyServer() {
        harness.router.always("/v1/devices/token") { ApiTestHarness.tokenResponse("token-1") }
        harness.router.always("/v1/analyze") { ApiTestHarness.json(200, ApiTestHarness.ANALYZE_HIGH) }
    }

    private fun analyzeBody(request: RecordedRequest) =
        Json.parseToJsonElement(request.body.readUtf8()).jsonObject

    // --- the on-device gate ------------------------------------------------

    @Test
    fun otpContentProducesLocalHighAndMakesZeroHttpRequests() = runTest {
        readyServer()
        val outcome = repository().analyzeMessage("Mã OTP là 837 261, bác đọc cho cháu nhé", InputMode.MANUAL)

        val result = (outcome as ChanOutcome.Success).value
        assertEquals(Risk.HIGH, result.risk)
        assertTrue(result.decidedOnDevice)
        assertEquals(listOf("yeu_cau_otp"), result.signals.map { it.code })
        // Quoting the message back would echo the digits that must not travel.
        assertEquals("", result.signals.single().evidence)

        assertEquals("An OTP must never reach the network", 0, harness.server.requestCount)
    }

    @Test
    fun contentBelowTheGateMakesZeroHttpRequests() = runTest {
        readyServer()
        val outcome = repository().analyzeMessage("Chào bác, con về nhà lúc bảy giờ tối", InputMode.MANUAL)

        val result = (outcome as ChanOutcome.Success).value
        assertEquals(Risk.UNKNOWN, result.risk)
        assertTrue(result.decidedOnDevice)
        assertEquals(0, harness.server.requestCount)
    }

    @Test
    fun contentAboveTheGateSendsOnlyLocalSignalNamesFromTheBundle() = runTest {
        readyServer()
        val engine = LocalRuleEngineFixture.engine()
        val text = "Tôi là cán bộ thuế, anh chuyển 20 trieu vào 19001234567890 truoc 17h hom nay, " +
            "khong noi voi ai ke ca gia dinh"

        repository().analyzeMessage(text, InputMode.MANUAL)

        val body = analyzeBody(harness.router.requestsFor("/v1/analyze").single())
        val sent = body.getValue("local_signals").jsonArray.map { it.jsonPrimitive.content }
        assertTrue("Something must have matched", sent.isNotEmpty())
        sent.forEach { name ->
            assertTrue("$name is not a rule in the bundle", engine.knowsLocalSignal(name))
        }
        // L1 vocabulary, never the eight-signal taxonomy the server returns.
        assertFalse(sent.contains("yeu_cau_bi_mat"))
    }

    // --- request schema ----------------------------------------------------

    @Test
    fun theAnalyzeRequestUsesTheExactSchemaWithNoExtraFields() = runTest {
        readyServer()
        repository().analyzeMessage(ABOVE_GATE_TEXT, InputMode.MANUAL)

        val body = analyzeBody(harness.router.requestsFor("/v1/analyze").single())
        assertEquals(
            setOf("text", "source", "input_mode", "app_package", "local_signals", "truncated", "locale"),
            body.keys,
        )
        assertEquals("android", body.getValue("source").jsonPrimitive.content)
        assertEquals("vi-VN", body.getValue("locale").jsonPrimitive.content)
        assertEquals("false", body.getValue("truncated").jsonPrimitive.content)
    }

    @Test
    fun eachIntakePathMapsToItsOwnInputMode() = runTest {
        readyServer()
        val repository = repository()
        repository.analyzeMessage(ABOVE_GATE_TEXT, InputMode.MANUAL)
        repository.analyzeMessage(ABOVE_GATE_TEXT, InputMode.SHARE)
        repository.analyzeMessage(ABOVE_GATE_TEXT, InputMode.NOTIFICATION, appPackage = "com.zing.zalo")

        val modes = harness.router.requestsFor("/v1/analyze")
            .map { analyzeBody(it).getValue("input_mode").jsonPrimitive.content }
        assertEquals(listOf("manual", "share", "notification"), modes)
    }

    @Test
    fun onlyANotificationRequestNamesItsSourceApp() = runTest {
        readyServer()
        val repository = repository()
        repository.analyzeMessage(ABOVE_GATE_TEXT, InputMode.NOTIFICATION, appPackage = "com.zing.zalo")
        repository.analyzeMessage(ABOVE_GATE_TEXT, InputMode.MANUAL, appPackage = "com.zing.zalo")

        val packages = harness.router.requestsFor("/v1/analyze")
            .map { analyzeBody(it).getValue("app_package").jsonPrimitive.content }
        // A manual check does not leak which app the user happened to copy from.
        assertEquals(listOf("com.zing.zalo", "null"), packages)
    }

    @Test
    fun aTruncatedNotificationIsDeclaredToTheBackend() = runTest {
        readyServer()
        repository().analyzeMessage(
            ABOVE_GATE_TEXT,
            InputMode.NOTIFICATION,
            appPackage = "com.zing.zalo",
            truncated = true,
        )

        val body = analyzeBody(harness.router.requestsFor("/v1/analyze").single())
        assertEquals("true", body.getValue("truncated").jsonPrimitive.content)
    }

    @Test
    fun theBackendResponseIsMappedIntoDomainWithoutRestoringRedactions() = runTest {
        readyServer()
        val outcome = repository().analyzeMessage(ABOVE_GATE_TEXT, InputMode.MANUAL)

        val result = (outcome as ChanOutcome.Success).value
        assertEquals(Risk.HIGH, result.risk)
        assertFalse(result.decidedOnDevice)
        assertEquals("ml-0.3.0", result.engineVersion)
        assertEquals("rb-2026-07-30", result.ruleBundleVersion)
        assertEquals("19008888", result.verifiedHotline?.number)
        // Placeholders arrive redacted and stay that way.
        assertTrue(result.signals.single().evidence.contains("<ACCOUNT>"))
    }

    // --- lookup ------------------------------------------------------------

    @Test
    fun lookupSendsOnlyAFiveCharacterHashPrefix() = runTest {
        harness.router.always("/v1/devices/token") { ApiTestHarness.tokenResponse("token-1") }
        harness.router.always("/v1/lookup") {
            ApiTestHarness.json(
                200,
                """{"prefix":"00000","kind":"phone","hashes":[],"cluster_size":0,
                   "bundle_version":"rb-test","no_match_message":"Chưa có báo cáo về số này."}""",
            )
        }

        val value = "0912 345 678"
        repository().lookup(LookupType.PHONE, value)

        val request = harness.router.requestsFor("/v1/lookup").single()
        val query = request.requestUrl?.queryParameter("prefix")
        assertEquals(5, query?.length)
        assertEquals(IndicatorHasher.hash(LookupType.PHONE, value).take(5), query)
        assertTrue("prefix must be lowercase hex", query!!.matches(Regex("[0-9a-f]{5}")))

        // Neither the raw value nor the full hash may appear anywhere in the request.
        val url = request.requestUrl.toString()
        assertFalse(url.contains("0912"))
        assertFalse(url.contains(IndicatorHasher.hash(LookupType.PHONE, value)))
        assertEquals("GET", request.method)
    }

    @Test
    fun theFullHashComparisonHappensOnTheDevice() = runTest {
        val value = "0912345678"
        val fullHash = IndicatorHasher.hash(LookupType.PHONE, value)
        val decoyHash = "0".repeat(64 - 5).let { fullHash.take(5) + it }

        harness.router.always("/v1/devices/token") { ApiTestHarness.tokenResponse("token-1") }
        harness.router.always("/v1/lookup") {
            // The server returns the whole cluster and learns nothing about which
            // member the client was asking for.
            ApiTestHarness.json(
                200,
                """{"prefix":"${fullHash.take(5)}","kind":"phone","hashes":[
                     {"hash":"$decoyHash","report_cnt":9,"first_seen":"2026-07-01T00:00:00Z",
                      "last_seen":"2026-07-01T00:00:00Z","origin":"feed_listed"},
                     {"hash":"$fullHash","report_cnt":4,"first_seen":"2026-07-20T00:00:00Z",
                      "last_seen":"2026-07-27T00:00:00Z","origin":"community_reviewed"}
                   ],"cluster_size":2,"bundle_version":"rb-test",
                   "no_match_message":"Chưa có báo cáo về số này."}""",
            )
        }

        val matched = (repository().lookup(LookupType.PHONE, value) as ChanOutcome.Success).value
        assertTrue(matched.matched)
        assertEquals(4, matched.reportCount)
        assertEquals("community_reviewed", matched.origin)
        assertEquals(3, matched.lastReportedDaysAgo)
        assertEquals(Risk.MEDIUM, matched.risk)

        // A different number with the same prefix cluster must not match.
        val other = (repository().lookup(LookupType.PHONE, "0987654321") as ChanOutcome.Success).value
        assertFalse(other.matched)
        assertEquals(Risk.UNKNOWN, other.risk)
    }

    private companion object {
        /** 2026-07-30T00:00:00Z, so "3 ngày trước" is deterministic. */
        const val FIXED_NOW = 1_785_369_600_000L

        const val ABOVE_GATE_TEXT =
            "Tôi là cán bộ thuế, anh chuyển tiền ngay lập tức, khong noi voi ai ke ca gia dinh"
    }
}

/** Shared engine over the shipped bootstrap bundle. */
object LocalRuleEngineFixture {
    fun engine() = com.chan.app.data.rules.LocalRuleEngine(
        com.chan.app.data.rules.RuleBundleParser.parse(TestBundles.bootstrapJson()),
    )
}
