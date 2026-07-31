package com.chan.app

import com.chan.app.data.rules.BootstrapBundleSource
import com.chan.app.data.rules.CachedBundle
import com.chan.app.data.rules.FileBundleCache
import com.chan.app.data.rules.RuleBundleFetcher
import com.chan.app.data.rules.RuleBundleInvalid
import com.chan.app.data.rules.RuleBundleParser
import com.chan.app.data.rules.RuleBundleStore
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertThrows
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.rules.TemporaryFolder
import java.io.IOException

/**
 * The rule layer must survive a hostile network: the app can never be left
 * without a bundle it can run, and a bad server document must not become the
 * live one.
 */
class RuleBundleStoreTest {

    @get:Rule
    val temporaryFolder = TemporaryFolder()

    private val bootstrapJson = TestBundles.bootstrapJson()
    private val bootstrap = BootstrapBundleSource { bootstrapJson }

    private class RecordingFetcher(
        var next: () -> CachedBundle? = { null },
    ) : RuleBundleFetcher {
        val requestedEtags = mutableListOf<String?>()
        override suspend fun fetch(etag: String?): CachedBundle? {
            requestedEtags += etag
            return next()
        }
    }

    @Test
    fun theBootstrapBundleThatShipsInTheApkIsValid() {
        val bundle = RuleBundleParser.parse(bootstrapJson)
        assertTrue(bundle.bundleVersion.isNotBlank())
        assertEquals(RuleBundleParser.SUPPORTED_SCHEMA_VERSION, bundle.schemaVersion)
        assertTrue(bundle.l1.otpBlock.patterns.isNotEmpty())
    }

    @Test
    fun aFailedRefreshFallsBackToTheBootstrapBundle() = runTest {
        val fetcher = RecordingFetcher { throw IOException("no network") }
        val store = RuleBundleStore(bootstrap, FileBundleCache(temporaryFolder.newFolder()), fetcher)

        assertFalse("A failed refresh must not report a change", store.refresh())
        // The app is still protected, using the copy inside the APK.
        assertEquals(RuleBundleParser.parse(bootstrapJson).bundleVersion, store.bundle().bundleVersion)
        assertFalse(store.isServerBundle())
    }

    @Test
    fun anInvalidServerBundleIsRejectedAndTheWorkingOneStaysActive() = runTest {
        val fetcher = RecordingFetcher { CachedBundle("{\"bundle_version\":\"rb-bad\"}", "\"etag-bad\"") }
        val store = RuleBundleStore(bootstrap, FileBundleCache(temporaryFolder.newFolder()), fetcher)

        assertFalse(store.refresh())
        assertEquals(RuleBundleParser.parse(bootstrapJson).bundleVersion, store.bundle().bundleVersion)
    }

    @Test
    fun aNotModifiedResponseKeepsTheCachedBundleAndItsEtag() = runTest {
        val directory = temporaryFolder.newFolder()
        val cache = FileBundleCache(directory)
        val serverJson = bootstrapJson.replace("\"rb-", "\"rbserver-")
        val fetcher = RecordingFetcher { CachedBundle(serverJson, "\"etag-1\"") }
        val store = RuleBundleStore(bootstrap, cache, fetcher)

        assertTrue("First refresh installs the server bundle", store.refresh())
        val installed = store.bundle().bundleVersion
        assertTrue(installed.startsWith("rbserver-"))

        // 304: the fetcher returns null and nothing may change.
        fetcher.next = { null }
        assertFalse(store.refresh())
        assertEquals(installed, store.bundle().bundleVersion)
        // The stored ETag was offered as If-None-Match on the second request.
        assertEquals("\"etag-1\"", fetcher.requestedEtags.last())
    }

    @Test
    fun aCachedServerBundleIsReusedByTheNextProcess() = runTest {
        val directory = temporaryFolder.newFolder()
        val serverJson = bootstrapJson.replace("\"rb-", "\"rbserver-")
        val first = RuleBundleStore(
            bootstrap,
            FileBundleCache(directory),
            RecordingFetcher { CachedBundle(serverJson, "\"etag-1\"") },
        )
        assertTrue(first.refresh())

        // A new store over the same directory models an app restart.
        val second = RuleBundleStore(bootstrap, FileBundleCache(directory), RecordingFetcher { null })
        assertTrue(second.bundle().bundleVersion.startsWith("rbserver-"))
        assertTrue(second.isServerBundle())
    }

    @Test
    fun anUnsupportedSchemaVersionIsRefused() {
        val futureBundle = bootstrapJson.replace("\"schema_version\": 1", "\"schema_version\": 99")
        val error = assertThrows(RuleBundleInvalid::class.java) { RuleBundleParser.parse(futureBundle) }
        assertEquals("bundle_schema_unsupported", error.code)
    }
}
