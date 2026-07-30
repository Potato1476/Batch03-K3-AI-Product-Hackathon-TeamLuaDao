package com.chan.app.data

import android.content.Context
import com.chan.app.BuildConfig
import com.chan.app.data.net.ChanApi
import com.chan.app.data.net.ChanNetwork
import com.chan.app.data.net.DeviceTokenProvider
import com.chan.app.data.rules.BootstrapBundleSource
import com.chan.app.data.rules.FileBundleCache
import com.chan.app.data.rules.RuleBundleStore
import com.chan.app.data.token.KeystoreDeviceTokenStore
import com.chan.app.domain.ChanRepository
import com.chan.app.notification.AndroidSafeAlertPublisher
import com.chan.app.notification.PendingAlertStore
import com.chan.app.notification.ProtectionPreferences
import com.chan.app.notification.SafeAlertPublisher
import com.chan.app.notification.SharedPreferencesAlertStorage
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch
import java.io.File

/**
 * The application's object graph, assembled by hand.
 *
 * Sprint 02 adds one Activity, one Service, and a handful of collaborators
 * shared between them. That is not enough surface to justify a dependency
 * injection framework, and the brief rules one out; a lazily-built holder keyed
 * to the application context is the whole mechanism.
 */
object ChanGraph {

    @Volatile
    private var components: Components? = null

    fun of(context: Context): Components {
        components?.let { return it }
        return synchronized(this) {
            components ?: Components(context.applicationContext).also { components = it }
        }
    }

    class Components internal constructor(private val application: Context) {

        private val service = ChanNetwork.service(BuildConfig.CHAN_API_BASE_URL)

        val api: ChanApi = ChanApi(
            service = service,
            tokens = DeviceTokenProvider(KeystoreDeviceTokenStore(application), service),
        )

        val bundles: RuleBundleStore = RuleBundleStore(
            bootstrap = BootstrapBundleSource {
                application.assets.open(BOOTSTRAP_ASSET).use { it.readBytes().toString(Charsets.UTF_8) }
            },
            cache = FileBundleCache(File(application.filesDir, "rules")),
            fetcher = api,
        )

        val repository: ChanRepository = LiveChanRepository(api = api, bundles = bundles)

        val protection: ProtectionPreferences = ProtectionPreferences(application)

        val pendingAlerts: PendingAlertStore =
            PendingAlertStore(SharedPreferencesAlertStorage(application))

        val alerts: SafeAlertPublisher by lazy { AndroidSafeAlertPublisher(application) }

        private val backgroundScope = CoroutineScope(SupervisorJob() + Dispatchers.IO)

        /**
         * Best-effort ETag refresh. Failure is silent by design: the app already
         * holds a usable bundle and must keep working offline.
         */
        fun refreshRulesInBackground() {
            backgroundScope.launch { bundles.refresh() }
        }
    }

    private const val BOOTSTRAP_ASSET = "rule_bundle_bootstrap.json"
}
