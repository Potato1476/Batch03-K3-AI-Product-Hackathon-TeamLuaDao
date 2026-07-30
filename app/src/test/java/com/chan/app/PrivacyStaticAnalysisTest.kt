package com.chan.app

import com.chan.app.domain.Risk
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File

/**
 * Build-failing checks for the invariants that no amount of careful review
 * keeps true over time.
 *
 * These read the module's own sources. A reviewer can forget that a logging
 * interceptor leaks message content, or that a `SAFE` risk contradicts the
 * product's central promise; the build cannot.
 */
class PrivacyStaticAnalysisTest {

    private val projectDir: File = TestBundles.projectDir()
    private val mainSources: List<File> = File(projectDir, "src/main/java")
        .walkTopDown()
        .filter { it.isFile && it.extension == "kt" }
        .toList()
    /**
     * Comments are stripped first: the manifest documents the permissions CHAN
     * refuses to request, and a prose mention of `READ_SMS` is the opposite of
     * a violation.
     */
    private val manifest: String = File(projectDir, "src/main/AndroidManifest.xml")
        .readText()
        .replace(Regex("<!--.*?-->", RegexOption.DOT_MATCHES_ALL), "")
    private val buildScript: String = File(projectDir, "build.gradle.kts").readText()

    @Test
    fun sourcesWereFound() {
        assertTrue("Static analysis found no sources to check", mainSources.size > 20)
    }

    @Test
    fun theDemoRepositoryIsNotTheProductionDefault() {
        val offenders = mainSources.filter { it.readText().contains("DemoChanRepository") }
        assertTrue(
            "A canned repository must never ship as the app's default: ${offenders.map { it.name }}",
            offenders.isEmpty(),
        )

        // The ViewModel's default must come from the live graph.
        val viewModel = File(projectDir, "src/main/java/com/chan/app/ui/ChanViewModel.kt").readText()
        assertTrue(
            "ChanViewModel must default to the live repository",
            viewModel.contains("ChanGraph.of(app).repository"),
        )
    }

    @Test
    fun thereIsNoSafeRisk() {
        assertEquals(setOf("HIGH", "MEDIUM", "UNKNOWN"), Risk.entries.map { it.name }.toSet())

        val offenders = mainSources.filter { file ->
            Regex("""\bRisk\.SAFE\b|\bSAFE\s*[,;)]""").containsMatchIn(file.readText())
        }
        assertTrue("`SAFE` must not appear as a risk: ${offenders.map { it.name }}", offenders.isEmpty())
    }

    @Test
    fun noHttpBodyLoggingIsWiredUp() {
        val forbidden = listOf(
            "HttpLoggingInterceptor",
            "logging-interceptor",
            "Level.BODY",
            "EventListener.Factory",
        )
        mainSources.forEach { file ->
            val text = file.readText()
            forbidden.forEach { needle ->
                assertFalse("${file.name} must not enable HTTP logging ($needle)", text.contains(needle))
            }
        }
        assertFalse(
            "The logging interceptor dependency must not be declared",
            buildScript.contains("logging-interceptor"),
        )
    }

    @Test
    fun messageContentIsNeverWrittenToLogcat() {
        // Any Android logging at all in the data/notification/speech layers is
        // treated as a leak: those are the only places content exists.
        val contentLayers = mainSources.filter {
            val path = it.path.replace('\\', '/')
            path.contains("/com/chan/app/data/") ||
                path.contains("/com/chan/app/notification/") ||
                path.contains("/com/chan/app/speech/")
        }
        assertTrue("Content-handling sources must exist", contentLayers.isNotEmpty())
        contentLayers.forEach { file ->
            val text = file.readText()
            assertFalse("${file.name} must not use android.util.Log", text.contains("android.util.Log"))
            assertFalse("${file.name} must not print", Regex("""\bprintln\s*\(""").containsMatchIn(text))
        }
    }

    @Test
    fun theReleaseBaseUrlCannotBeCleartext() {
        assertTrue(
            "The release build must verify an explicit HTTPS base URL",
            buildScript.contains("verifyReleaseApiBaseUrl") &&
                buildScript.contains("""startsWith("https://")"""),
        )
        assertTrue(
            "The verification must be wired into the release build",
            buildScript.contains("preReleaseBuild") && buildScript.contains("dependsOn(verifyReleaseApiBaseUrl)"),
        )
        // Release must reject cleartext; only the debug source set may permit it.
        val releaseConfig = File(projectDir, "src/main/res/xml/network_security_config.xml").readText()
        assertTrue(
            "The default network security config must forbid cleartext",
            releaseConfig.contains("""cleartextTrafficPermitted="false""""),
        )
        val debugConfig = File(projectDir, "src/debug/res/xml/network_security_config.xml")
        assertTrue("The cleartext override must live in the debug source set", debugConfig.isFile)

        // No hardcoded production host anywhere in Kotlin.
        mainSources.forEach { file ->
            val text = file.readText()
            assertFalse(
                "${file.name} must not hardcode an API URL",
                Regex("""https?://(?!10\.0\.2\.2|schemas\.android\.com|www\.w3\.org)[a-z0-9.-]+\.[a-z]{2,}""")
                    .containsMatchIn(text),
            )
        }
    }

    @Test
    fun noProhibitedPermissionIsDeclared() {
        val prohibited = listOf(
            "READ_SMS",
            "RECEIVE_SMS",
            "SEND_SMS",
            "READ_CONTACTS",
            "WRITE_CONTACTS",
            "READ_CALL_LOG",
            "WRITE_CALL_LOG",
            "READ_PHONE_STATE",
            "READ_EXTERNAL_STORAGE",
            "WRITE_EXTERNAL_STORAGE",
            "MANAGE_EXTERNAL_STORAGE",
            "BIND_ACCESSIBILITY_SERVICE",
            "PACKAGE_USAGE_STATS",
            "SYSTEM_ALERT_WINDOW",
        )
        prohibited.forEach { permission ->
            assertFalse("$permission must never be requested", manifest.contains(permission))
        }
        assertFalse("No accessibility service may be declared", manifest.contains("accessibilityservice"))
    }

    @Test
    fun onlyTheIntendedPermissionsAndOneListenerAreDeclared() {
        val requested = Regex("""uses-permission android:name="android\.permission\.([A-Z_]+)"""")
            .findAll(manifest)
            .map { it.groupValues[1] }
            .toSet()
        assertEquals(setOf("INTERNET", "POST_NOTIFICATIONS", "RECORD_AUDIO"), requested)

        val listeners = Regex("""android:name="\.([A-Za-z.]*NotificationListenerService)"""")
            .findAll(manifest)
            .map { it.groupValues[1] }
            .toList()
        assertEquals(listOf("notification.ZaloNotificationListenerService"), listeners)
    }

    @Test
    fun onlyZaloIsMonitoredPassively() {
        val watchedPackages = mainSources
            .filter { it.path.replace('\\', '/').contains("/com/chan/app/notification/") }
            .flatMap { Regex("""com\.(?:zing|facebook|google|samsung|android|viber|whatsapp)[a-z.]*""").findAll(it.readText()).map { m -> m.value } }
            .toSet()
        assertEquals(
            "Sprint 02 monitors exactly one package",
            setOf("com.zing.zalo"),
            watchedPackages,
        )
    }

    @Test
    fun noPersistenceEntityIsNamedAfterRawContent() {
        // Anything that reaches durable storage goes through a string key. A key
        // named after the message is the signature of content being persisted.
        val forbiddenKeyWord = Regex(
            """(?:const\s+val|val)\s+KEY_[A-Z_]*(?:TEXT|MESSAGE|CONTENT|BODY|RAW|TRANSCRIPT|SENDER)""",
        )
        val keyLiteral = Regex(
            """"[a-z_]*(?:raw_|_raw|message|content|body|transcript|sender|notification_text)[a-z_]*"""",
        )
        mainSources.forEach { file ->
            val text = file.readText()
            assertFalse(
                "${file.name} names a persisted field after source content",
                forbiddenKeyWord.containsMatchIn(text),
            )
            if (text.contains("SharedPreferences") || text.contains("preferencesKey")) {
                assertFalse(
                    "${file.name} stores a key named after source content",
                    keyLiteral.containsMatchIn(text),
                )
            }
        }
    }

    @Test
    fun ruleLogicIsNotHardcodedInKotlin() {
        // The Rule Bundle is the source of truth; a scam regex in Kotlin would
        // silently break Web/Android equivalence.
        val engineSources = mainSources.filter {
            it.path.replace('\\', '/').contains("/com/chan/app/data/rules/")
        }
        assertTrue(engineSources.isNotEmpty())
        val suspiciousVietnameseRule = Regex("""Regex\("[^"]*(?:otp|cong an|chuyen khoan|trung thuong)""", RegexOption.IGNORE_CASE)
        engineSources.forEach { file ->
            assertFalse(
                "${file.name} must not hardcode rule content",
                suspiciousVietnameseRule.containsMatchIn(file.readText()),
            )
        }
    }
}
