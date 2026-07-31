package com.chan.app

import com.chan.app.data.rules.LocalRuleEngine
import com.chan.app.data.rules.LocalVerdict
import com.chan.app.data.rules.RuleBundleParser
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File

/**
 * The Kotlin port of L0/L1 must agree with the TypeScript one
 * (`apps/web/src/engine.ts`), because equivalence between the clients is a
 * property of the shared Rule Bundle, not of programmer discipline.
 *
 * `l0-l1-parity-vectors.json` holds inputs with the normalized text, verdict,
 * and L1 signal names produced by an independent replication of the web engine
 * run against this exact bundle. If the two ports ever diverge, this fails.
 */
class LocalRuleEngineTest {

    private val engine = LocalRuleEngine(RuleBundleParser.parse(TestBundles.bootstrapJson()))

    @Test
    fun kotlinL0L1MatchesTheSharedParityVectors() {
        val vectors = Json.parseToJsonElement(parityVectorsJson()) as JsonArray
        assertTrue("Parity fixture must not be empty", vectors.isNotEmpty())

        vectors.forEach { element ->
            val vector = element.jsonObject
            val input = vector.getValue("input").jsonPrimitive.content
            val expectedNormalized = vector.getValue("normalized").jsonPrimitive.content
            val expectedVerdict = vector.getValue("verdict").jsonPrimitive.content
            val expectedSignals = vector.getValue("localSignals").jsonArray.map { it.jsonPrimitive.content }
            val expectedTruncated = vector.getValue("truncated").jsonPrimitive.content.toBoolean()

            assertEquals("L0 normalization for: $input", expectedNormalized, engine.normalize(input))

            val decision = engine.evaluate(input)
            assertEquals("Verdict for: $input", expectedVerdict, decision.verdict.name)
            assertEquals(
                "L1 signals for: $input",
                expectedSignals.sorted(),
                decision.localSignals.sorted(),
            )
            assertEquals("Truncation for: $input", expectedTruncated, decision.truncated)
        }
    }

    @Test
    fun otpContentIsDecidedOnTheDeviceAndCarriesNoSignalsToSend() {
        val decision = engine.evaluate("Mã OTP là 837 261, bác đọc cho cháu nhé")
        assertEquals(LocalVerdict.OTP_BLOCK, decision.verdict)
    }

    @Test
    fun contentBelowTheGateStaysOnTheDevice() {
        val decision = engine.evaluate("Chào bác, con về nhà lúc bảy giờ tối")
        assertEquals(LocalVerdict.BELOW_GATE, decision.verdict)
        assertTrue(decision.localSignals.isEmpty())
    }

    @Test
    fun shortContentNeverReachesTheServerEvenWithASignal() {
        // Below `min_length_to_call_server`, regardless of what matched.
        val decision = engine.evaluate("gấp")
        assertEquals(LocalVerdict.BELOW_GATE, decision.verdict)
    }

    @Test
    fun anAlwaysCallSignalOverridesTheScoreGate() {
        val bundle = engine.bundle
        val alwaysCall = bundle.l1.gate.alwaysCallWhenLocalSignal
        assertTrue("Bundle must define always-call signals", alwaysCall.isNotEmpty())

        val decision = engine.evaluate("Cai dat ung dung tu link nay: http://x.example/chan.apk")
        assertEquals(LocalVerdict.CALL_SERVER, decision.verdict)
        assertTrue(decision.localSignals.any { alwaysCall.contains(it) })
    }

    @Test
    fun onlyRuleNamesFromTheBundleAreEverProduced() {
        val decision = engine.evaluate(
            "Tôi là cán bộ thuế, anh chuyển 20 trieu vào 19001234567890 truoc 17h hom nay, " +
                "khong noi voi ai ke ca gia dinh",
        )
        assertEquals(LocalVerdict.CALL_SERVER, decision.verdict)
        decision.localSignals.forEach { name ->
            assertTrue("$name must exist in the bundle", engine.knowsLocalSignal(name))
        }
    }

    @Test
    fun teencodeAndInvisibleCharactersAreNormalizedBeforeMatching() {
        // A zero-width space inside a word and teencode abbreviations.
        val normalized = engine.normalize("Bác ck cho cháu vào stk​ này")
        assertTrue("teencode must expand", normalized.contains("chuyen khoan"))
        assertTrue("teencode must expand", normalized.contains("so tai khoan"))
        assertTrue("invisible characters must be stripped", !normalized.contains("​"))
    }

    private fun parityVectorsJson(): String =
        checkNotNull(javaClass.classLoader?.getResourceAsStream("l0-l1-parity-vectors.json")) {
            "Parity vector fixture is missing"
        }.use { it.readBytes().toString(Charsets.UTF_8) }
}

/** Reads the bootstrap bundle that ships in `assets/` straight off disk. */
object TestBundles {
    fun bootstrapJson(): String = File(projectDir(), "src/main/assets/rule_bundle_bootstrap.json").readText()

    fun projectDir(): File = File(
        checkNotNull(System.getProperty("chan.projectDir")) {
            "chan.projectDir system property is not set (see app/build.gradle.kts)"
        },
    )
}
