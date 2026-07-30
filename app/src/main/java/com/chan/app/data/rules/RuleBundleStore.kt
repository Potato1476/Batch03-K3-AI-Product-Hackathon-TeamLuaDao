package com.chan.app.data.rules

import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import java.io.File

/** A bundle document plus the ETag it was served with. */
data class CachedBundle(val json: String, val etag: String?)

/** Supplies the known-good bundle shipped inside the APK. */
fun interface BootstrapBundleSource {
    fun read(): String
}

/** Durable storage for the last server bundle that validated. */
interface BundleCache {
    fun read(): CachedBundle?
    fun write(json: String, etag: String?)
    fun clear()
}

/** What the store needs from the network. Implemented by the API layer. */
interface RuleBundleFetcher {
    /**
     * @param etag the cached ETag to send as `If-None-Match`.
     * @return null when the server answered 304 (cached copy still current).
     * @throws Exception on any transport or server failure.
     */
    suspend fun fetch(etag: String?): CachedBundle?
}

/**
 * Holds the bundle the rule engine runs on (§A4).
 *
 * Guarantees:
 *  - there is always a usable bundle, because the APK ships a validated one;
 *  - a server bundle replaces it only after parsing and validating;
 *  - a failed refresh leaves the previous bundle in place;
 *  - the on-disk copy is replaced atomically, so a killed process cannot leave
 *    a half-written document behind.
 */
class RuleBundleStore(
    private val bootstrap: BootstrapBundleSource,
    private val cache: BundleCache,
    private val fetcher: RuleBundleFetcher,
) {

    private val mutex = Mutex()
    private var loaded: LoadedBundle? = null
    private var cachedEngine: LocalRuleEngine? = null

    private data class LoadedBundle(val bundle: RuleBundle, val etag: String?, val fromCache: Boolean)

    /** The bundle to run L0/L1 against, loading from cache or bootstrap once. */
    suspend fun bundle(): RuleBundle = mutex.withLock { load().bundle }

    /** The engine for the current bundle. Regex compilation happens once. */
    suspend fun engine(): LocalRuleEngine = mutex.withLock {
        val current = load().bundle
        val existing = cachedEngine
        if (existing != null && existing.bundle === current) {
            existing
        } else {
            LocalRuleEngine(current).also { cachedEngine = it }
        }
    }

    /** True when the active bundle came from the server rather than the APK. */
    suspend fun isServerBundle(): Boolean = mutex.withLock { load().fromCache }

    /**
     * Refreshes in the background. Returns true when the active bundle changed.
     * Never throws: a refresh failure is not a reason to stop protecting.
     */
    suspend fun refresh(): Boolean = mutex.withLock {
        val current = load()
        val fetched = try {
            fetcher.fetch(current.etag)
        } catch (error: Exception) {
            return@withLock false
        } ?: return@withLock false // 304: the cached bundle is still current.

        val candidate = try {
            RuleBundleParser.parse(fetched.json)
        } catch (error: RuleBundleInvalid) {
            // A bad server bundle is discarded; the working one stays active.
            return@withLock false
        }
        if (candidate.bundleVersion == current.bundle.bundleVersion && current.fromCache) {
            // Same rules, possibly a new ETag — record it and skip the swap.
            cache.write(fetched.json, fetched.etag)
            loaded = current.copy(etag = fetched.etag)
            return@withLock false
        }
        cache.write(fetched.json, fetched.etag)
        loaded = LoadedBundle(candidate, fetched.etag, fromCache = true)
        cachedEngine = null
        true
    }

    private fun load(): LoadedBundle {
        loaded?.let { return it }

        val cached = cache.read()
        if (cached != null) {
            val parsed = runCatching { RuleBundleParser.parse(cached.json) }.getOrNull()
            if (parsed != null) {
                return LoadedBundle(parsed, cached.etag, fromCache = true).also { loaded = it }
            }
            // The cached document no longer validates against this build.
            cache.clear()
        }
        val fallback = RuleBundleParser.parse(bootstrap.read())
        return LoadedBundle(fallback, etag = null, fromCache = false).also { loaded = it }
    }
}

/**
 * File-backed bundle cache. Plain `java.io`, so the real implementation is what
 * the unit tests exercise against a temporary directory.
 */
class FileBundleCache(private val directory: File) : BundleCache {

    private val bundleFile get() = File(directory, "bundle.json")
    private val etagFile get() = File(directory, "bundle.etag")

    override fun read(): CachedBundle? {
        val file = bundleFile
        if (!file.isFile) return null
        val json = runCatching { file.readText() }.getOrNull() ?: return null
        if (json.isBlank()) return null
        val etag = runCatching { etagFile.takeIf { it.isFile }?.readText() }.getOrNull()
        return CachedBundle(json, etag?.takeIf { it.isNotBlank() })
    }

    override fun write(json: String, etag: String?) {
        runCatching {
            directory.mkdirs()
            // Atomic replacement: a torn write can never become the live bundle.
            val temp = File(directory, "bundle.json.tmp")
            temp.writeText(json)
            if (!temp.renameTo(bundleFile)) {
                bundleFile.writeText(json)
                temp.delete()
            }
            if (etag.isNullOrBlank()) etagFile.delete() else etagFile.writeText(etag)
        }
    }

    override fun clear() {
        runCatching {
            bundleFile.delete()
            etagFile.delete()
        }
    }
}
