package com.chan.app.notification

import android.content.Context
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update

/**
 * Why the listener is not connected. A category only — never a platform
 * message, and never anything read from a notification.
 */
enum class DisconnectReason {
    /** Android called `onListenerDisconnected`. */
    LISTENER_DISCONNECTED,

    /** The service instance was destroyed. */
    SERVICE_DESTROYED,

    /**
     * A rebind was requested and Android never called `onListenerConnected`.
     *
     * On the Xiaomi handset this is the normal case, not an edge case: the
     * component is listed under Notification Access, the process is alive, and
     * the system simply does not bind the service. `requestRebind` is a
     * request, and the platform is free to ignore it — so this state must lead
     * the user to the settings toggle rather than to another wait.
     */
    REBIND_NOT_ANSWERED,
}

/**
 * Whether CHAN's notification listener is bound *in this process, right now*
 * (§B1).
 *
 * Sprint 02 treated the Notification Access grant as proof of this. It is not:
 * during physical testing the grant was on while the listener was not bound,
 * and every screen still said protection was active.
 */
sealed interface ListenerConnection {
    /** A new process. No listener callback has been seen yet. */
    data object Unknown : ListenerConnection

    /**
     * A bind is pending and the callback has not arrived.
     *
     * [rebindRequested] separates "the service was just created and we are
     * waiting for the system" from "the user asked us to try again". Only the
     * second one may claim to be *retrying*, and it is the one that must block
     * a second tap until it resolves.
     */
    data class Connecting(
        val since: Long,
        val rebindRequested: Boolean = false,
    ) : ListenerConnection

    /** `onListenerConnected` happened in this process at [connectedAt]. */
    data class Connected(val connectedAt: Long) : ListenerConnection

    data class Disconnected(val reason: DisconnectReason? = null) : ListenerConnection
}

/** Somewhere to keep the one fact worth surviving a restart. */
interface LastConnectedStore {
    var lastConnectedAt: Long?
}

/** Test and in-process implementation. */
class InMemoryLastConnectedStore(initial: Long? = null) : LastConnectedStore {
    @Volatile
    override var lastConnectedAt: Long? = initial
}

/**
 * SharedPreferences-backed store.
 *
 * Only a timestamp is written. A `connected=true` flag is deliberately absent:
 * it would be a lie the moment the process died, and the screen that read it
 * back would tell the user they were protected when nothing was bound (§B1).
 */
class SharedPreferencesLastConnectedStore(context: Context) : LastConnectedStore {

    private val preferences = context.applicationContext
        .getSharedPreferences("chan_protection_runtime", Context.MODE_PRIVATE)

    override var lastConnectedAt: Long?
        get() = preferences.getLong(KEY_LAST_CONNECTED_AT, 0L).takeIf { it > 0L }
        set(value) {
            preferences.edit().putLong(KEY_LAST_CONNECTED_AT, value ?: 0L).apply()
        }

    private companion object {
        const val KEY_LAST_CONNECTED_AT = "last_connected_at"
    }
}

/**
 * The single source of truth for listener liveness (§B1).
 *
 * It starts [ListenerConnection.Unknown] in every new process and moves only on
 * real lifecycle evidence. `lastConnectedAt` may be read back from disk for
 * explanatory copy — "Kết nối gần nhất lúc 18:42" — but it is history, never
 * current health, and nothing in this class can promote it to one.
 */
class ProtectionRuntimeMonitor(
    private val store: LastConnectedStore = InMemoryLastConnectedStore(),
    private val now: () -> Long = System::currentTimeMillis,
) {

    private val _connection = MutableStateFlow<ListenerConnection>(ListenerConnection.Unknown)
    val connection: StateFlow<ListenerConnection> = _connection.asStateFlow()

    /** The last time a listener was genuinely connected, if it is known. */
    val lastConnectedAt: Long? get() = store.lastConnectedAt

    /**
     * A bind or rebind has been asked for. Not evidence of a connection: only
     * [onConnected] is.
     */
    fun onConnecting(rebindRequested: Boolean = false) {
        _connection.value = ListenerConnection.Connecting(now(), rebindRequested)
    }

    /** True while an attempt is outstanding, so the UI can refuse a second tap. */
    val attemptPending: Boolean
        get() = (_connection.value as? ListenerConnection.Connecting)?.rebindRequested == true

    /** Called only from `NotificationListenerService.onListenerConnected`. */
    fun onConnected() {
        val timestamp = now()
        store.lastConnectedAt = timestamp
        _connection.value = ListenerConnection.Connected(timestamp)
    }

    fun onDisconnected(reason: DisconnectReason) {
        _connection.value = ListenerConnection.Disconnected(reason)
    }

    /**
     * Ends an attempt that produced no callback (§B3).
     *
     * The window is not a diagnosis and waiting longer is not a fix: Android
     * either binds the service or it does not. All this does is stop CHAN from
     * claiming to be connecting once it plainly is not, so the screen can move
     * on to the one thing that does work — re-toggling the grant by hand.
     *
     * A no-op once the real callback has arrived, so a late timer can never
     * undo a live connection.
     */
    fun endAttemptIfUnanswered() {
        _connection.update { current ->
            if (current is ListenerConnection.Connecting) {
                ListenerConnection.Disconnected(DisconnectReason.REBIND_NOT_ANSWERED)
            } else {
                current
            }
        }
    }

    val isConnected: Boolean get() = _connection.value is ListenerConnection.Connected
}
