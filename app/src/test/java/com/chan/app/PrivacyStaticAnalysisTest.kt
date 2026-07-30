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

    // --- Sprint 03 additions ------------------------------------------------

    @Test
    fun noContinuousAudioCaptureOrRecordingStorageExists() {
        // Dictation is one utterance through the platform recognizer. A raw
        // audio API or an audio file would be a different product.
        val forbidden = listOf(
            "AudioRecord",
            "MediaRecorder",
            "AudioTrack",
            "createAudioRecord",
            "setAudioSource",
            ".wav",
            ".3gp",
            ".m4a",
        )
        mainSources.forEach { file ->
            val text = file.readText()
            forbidden.forEach { needle ->
                assertFalse("${file.name} must not capture or store audio ($needle)", text.contains(needle))
            }
        }
    }

    @Test
    fun noForegroundServiceIsIntroduced() {
        // §B4/§11: the system-managed NotificationListenerService remains the
        // intake. A foreground service to keep the process alive is out of
        // scope and would need its own permission and disclosure.
        assertFalse("No foreground service permission", manifest.contains("FOREGROUND_SERVICE"))
        assertFalse("No foreground service type", manifest.contains("foregroundServiceType"))
        mainSources.forEach { file ->
            val text = file.readText()
            assertFalse("${file.name} must not start a foreground service", text.contains("startForeground"))
            assertFalse("${file.name} must not declare a foreground service", text.contains("ServiceCompat.startForeground"))
        }
    }

    @Test
    fun theCurrentListenerConnectionIsNeverPersistedAsATrustedFlag() {
        // §B1: a stored `connected=true` becomes a lie the moment the process
        // dies. Only a timestamp may be written, and only as history.
        val connectionFlag = Regex(
            """putBoolean\s*\(\s*[^)]*(?:connect|bound|listener_?active|listener_?live)""",
            RegexOption.IGNORE_CASE,
        )
        mainSources.forEach { file ->
            assertFalse(
                "${file.name} persists a runtime connection flag",
                connectionFlag.containsMatchIn(file.readText()),
            )
        }

        val monitor = File(projectDir, "src/main/java/com/chan/app/notification/ProtectionRuntimeMonitor.kt")
            .readText()
        assertTrue(
            "The monitor must start Unknown in every process",
            monitor.contains("MutableStateFlow<ListenerConnection>(ListenerConnection.Unknown)"),
        )
        assertFalse("The monitor must not read a connection back from storage", monitor.contains("getBoolean"))
    }

    @Test
    fun theStatusNotificationCannotAcceptSourceText() {
        // §B4: the indicator's copy comes from string resources and its API
        // takes no parameters, so no caller can put content into it.
        val notifier = File(projectDir, "src/main/java/com/chan/app/notification/ProtectionStatusNotifier.kt")
            .readText()
        assertTrue("show() must take no arguments", notifier.contains("fun show(): Boolean"))
        assertTrue("cancel() must take no arguments", notifier.contains("fun cancel()"))
        assertTrue(
            "The title must come from a string resource",
            notifier.contains("R.string.status_notification_title"),
        )
        assertTrue(
            "The body must come from a string resource",
            notifier.contains("R.string.status_notification_body"),
        )
        // No format placeholder that a caller could fill with a message.
        val statusStrings = File(projectDir, "src/main/res/values/strings.xml").readText()
        val statusCopy = Regex("""<string name="status_notification_[a-z]+">([^<]*)</string>""")
            .findAll(statusStrings)
            .map { it.groupValues[1] }
            .toList()
        assertEquals("Both status strings must exist", 2, statusCopy.size)
        statusCopy.forEach { copy ->
            assertFalse("The indicator must not interpolate anything: $copy", copy.contains("%"))
        }
    }

    @Test
    fun analyzeRequestsHaveNoHiddenTransportReplay() {
        // §C1: OkHttp would otherwise re-send a POST body on a new connection.
        val network = File(projectDir, "src/main/java/com/chan/app/data/net/ChanNetwork.kt").readText()
        assertTrue(
            "retryOnConnectionFailure must be disabled",
            network.contains("retryOnConnectionFailure(false)"),
        )
        assertFalse(
            "Transport retries must not be re-enabled",
            network.contains("retryOnConnectionFailure(true)"),
        )
        // The only retry left is the explicit, single 401 recovery.
        val api = File(projectDir, "src/main/java/com/chan/app/data/net/ChanApi.kt").readText()
        assertTrue("The one-shot 401 recovery must remain", api.contains("Exactly one recovery attempt"))
    }

    @Test
    fun theBaseUrlDocumentationMatchesTheBuild() {
        // §C2: the README may only describe forms the build actually reads.
        assertTrue(
            "The build must read local.properties for the debug base URL",
            buildScript.contains("localProperty(\"CHAN_API_BASE_URL\")") &&
                buildScript.contains("rootProject.file(\"local.properties\")"),
        )
        assertTrue(
            "The -P form must keep working",
            buildScript.contains("providers.gradleProperty(\"CHAN_API_BASE_URL\")"),
        )

        val readme = File(projectDir.parentFile, "README.md").readText()
        assertTrue("README must document the -P form", readme.contains("-PCHAN_API_BASE_URL="))
        assertTrue(
            "README must document the local.properties form the build implements",
            readme.contains("CHAN_API_BASE_URL=http://"),
        )
        // No machine LAN address may be committed anywhere.
        val lanAddress = Regex("""\b(?:10\.(?!0\.2\.2)\d{1,3}|172\.(?:1[6-9]|2\d|3[01])|192\.168)\.\d{1,3}\.\d{1,3}\b""")
        mainSources.forEach { file ->
            assertFalse("${file.name} must not contain a LAN address", lanAddress.containsMatchIn(file.readText()))
        }
        readme.lineSequence().forEach { line ->
            if (lanAddress.containsMatchIn(line)) {
                assertTrue(
                    "A LAN address in the README must be the documented example: $line",
                    line.contains("192.168.1.42"),
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
