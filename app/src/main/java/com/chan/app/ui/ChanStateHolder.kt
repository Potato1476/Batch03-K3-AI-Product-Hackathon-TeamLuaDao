package com.chan.app.ui

import com.chan.app.domain.AnalysisResult
import com.chan.app.domain.ChanOutcome
import com.chan.app.domain.ChanRepository
import com.chan.app.domain.FailureReason
import com.chan.app.domain.InputMode
import com.chan.app.domain.LookupResult
import com.chan.app.domain.LookupType
import com.chan.app.notification.EffectiveProtection
import com.chan.app.notification.ListenerConnection
import com.chan.app.notification.ProtectionActivity
import com.chan.app.notification.ProtectionHealth
import com.chan.app.ui.navigation.Screen
import com.chan.app.ui.navigation.Tab
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update

/** Content awaiting the user's confirmation before CHAN imports it. */
data class ShareIntake(
    val text: String?,
    val imageUri: String?,
    val isImage: Boolean,
)

/**
 * Live state of the layers the protection screens report on.
 *
 * Green on any of these means "this layer is switched on" — never that a
 * message, caller, or account is safe.
 *
 * [listenerConnection] is the Sprint 03 addition and the one that changes the
 * story: a granted permission is a *setting*, while a connected listener is a
 * fact about this process. They are reported separately because during physical
 * testing they disagreed, and the app believed the setting.
 */
data class SystemStatus(
    val notificationAccessGranted: Boolean = false,
    val zaloScanningEnabled: Boolean = false,
    val warningsAllowed: Boolean = false,
    val microphoneGranted: Boolean = false,
    /** True once the rule layer is running a bundle fetched from the server. */
    val rulesFromServer: Boolean = false,
    /** What CHAN's listener is actually doing right now (§B1). */
    val listenerConnection: ListenerConnection = ListenerConnection.Unknown,
    /** History for explanatory copy only. Never current health. */
    val lastConnectedAt: Long? = null,
    /** Content-free record of the last Zalo callback (§D3). */
    val activity: ProtectionActivity = ProtectionActivity(),
) {
    /** The single user-facing state, computed from every layer (§B2). */
    val protectionHealth: ProtectionHealth
        get() = EffectiveProtection.evaluate(
            zaloScanningEnabled = zaloScanningEnabled,
            notificationAccessGranted = notificationAccessGranted,
            connection = listenerConnection,
            warningsAllowed = warningsAllowed,
        )

    /** A real `onListenerConnected` happened in this process. */
    val listenerConnected: Boolean get() = listenerConnection is ListenerConnection.Connected

    /** Scanning runs, but CHAN cannot show the warning it would produce. */
    val scanningWithoutWarnings: Boolean
        get() = protectionHealth == ProtectionHealth.ACTIVE_WITHOUT_WARNINGS

    /** The listener is configured but not bound: a rebind is worth offering. */
    val canRequestReconnect: Boolean
        get() = zaloScanningEnabled && notificationAccessGranted && !listenerConnected
}

/** Immutable UI state consumed by the Compose tree. */
data class ChanUiState(
    val darkMode: Boolean = false,
    val selectedTab: Tab = Tab.HOME,
    val current: Screen = Screen.Home,
    val canGoBack: Boolean = false,
    val messageText: String = "",
    val inputMode: InputMode = InputMode.MANUAL,
    val selectedImageUri: String? = null,
    val lookupType: LookupType = LookupType.ACCOUNT,
    val lookupValue: String = "",
    val analysis: AnalysisResult? = null,
    val analysisFailure: FailureReason? = null,
    val lookup: LookupResult? = null,
    val lookupFailure: FailureReason? = null,
    val isAnalyzing: Boolean = false,
    val isLookingUp: Boolean = false,
    val pendingShare: ShareIntake? = null,
    val guardianSharingEnabled: Boolean = true,
    val systemStatus: SystemStatus = SystemStatus(),
) {
    /** Analysis is enabled only when the trimmed message is non-empty. */
    val canAnalyze: Boolean get() = messageText.trim().isNotEmpty()

    /** Lookup is enabled only when the trimmed value is non-empty. */
    val canLookup: Boolean get() = lookupValue.trim().isNotEmpty()
}

/**
 * Android-free state machine for CHAN. All navigation and flow logic lives here
 * so it can be unit-tested on the JVM without a device. The Android
 * [ChanViewModel] owns one of these and adds persistence, permissions, speech,
 * and coroutine scope.
 */
class ChanStateHolder(private val repository: ChanRepository) {

    // Per-tab back stacks. The last element of the selected tab is the visible
    // screen. Roots are never popped.
    private val stacks: MutableMap<Tab, MutableList<Screen>> = mutableMapOf(
        Tab.HOME to mutableListOf(Screen.Home),
        Tab.CHECK to mutableListOf(Screen.CheckHub),
        Tab.PROTECT to mutableListOf(Screen.Protection),
        Tab.SETTINGS to mutableListOf(Screen.Settings),
    )

    private val _state = MutableStateFlow(ChanUiState())
    val state: StateFlow<ChanUiState> = _state.asStateFlow()

    private fun stack(tab: Tab) = stacks.getValue(tab)

    private fun sync() {
        val tab = _state.value.selectedTab
        val s = stack(tab)
        _state.update { it.copy(current = s.last(), canGoBack = s.size > 1) }
    }

    // --- Dark mode (persistence handled by the ViewModel) ---
    fun applyDarkMode(enabled: Boolean) = _state.update { it.copy(darkMode = enabled) }

    // --- System status (refreshed by the ViewModel on resume) ---
    fun applySystemStatus(status: SystemStatus) = _state.update { it.copy(systemStatus = status) }

    // --- Bottom navigation ---
    fun selectTab(tab: Tab) {
        _state.update { it.copy(selectedTab = tab) }
        sync()
    }

    /** Handles system/back-arrow. Returns false when there is nothing to pop. */
    fun back(): Boolean {
        val tab = _state.value.selectedTab
        val s = stack(tab)
        if (s.size <= 1) return false
        s.removeAt(s.lastIndex)
        sync()
        return true
    }

    private fun push(tab: Tab, screen: Screen) {
        stack(tab).add(screen)
        _state.update { it.copy(selectedTab = tab) }
        sync()
    }

    private fun replaceTop(tab: Tab, screen: Screen) {
        val s = stack(tab)
        s[s.lastIndex] = screen
        sync()
    }

    /** Reset the CHECK tab back to its hub (used by "check another"). */
    private fun resetCheckTo(screen: Screen) {
        val s = stack(Tab.CHECK)
        s.clear()
        s.add(Screen.CheckHub)
        if (screen != Screen.CheckHub) s.add(screen)
        _state.update { it.copy(selectedTab = Tab.CHECK) }
        sync()
    }

    // --- Entering the check flows ---
    fun openMessageInput() {
        _state.update { it.copy(analysis = null, analysisFailure = null) }
        resetCheckTo(Screen.MessageInput)
    }

    fun openCommunityLookup() {
        _state.update { it.copy(lookup = null, lookupFailure = null) }
        resetCheckTo(Screen.CommunityLookup)
    }

    /**
     * Opens a warning that arrived from the notification listener. The result is
     * already redacted; no source content travels with it.
     */
    fun openAlertResult(result: AnalysisResult) {
        _state.update { it.copy(analysis = result, analysisFailure = null, messageText = "") }
        resetCheckTo(Screen.AnalysisResult)
    }

    // --- Message input ---
    fun updateMessageText(text: String) =
        _state.update { it.copy(messageText = text, inputMode = InputMode.MANUAL) }

    fun selectImage(uri: String) = _state.update { it.copy(selectedImageUri = uri) }

    fun clearSelectedImage() = _state.update { it.copy(selectedImageUri = null) }

    // --- Analysis: begin -> loading -> result ---
    /**
     * Runs one analysis. Never called automatically: dictation, sharing, and
     * pasting all stop at an editable field until the user taps the CTA.
     */
    suspend fun analyze() {
        val message = _state.value.messageText
        if (message.trim().isEmpty()) return

        _state.update { it.copy(isAnalyzing = true, analysis = null, analysisFailure = null) }
        push(Tab.CHECK, Screen.Analyzing)

        when (val outcome = repository.analyzeMessage(message, _state.value.inputMode)) {
            is ChanOutcome.Success ->
                _state.update { it.copy(isAnalyzing = false, analysis = outcome.value) }
            is ChanOutcome.Failure ->
                _state.update { it.copy(isAnalyzing = false, analysisFailure = outcome.reason) }
        }
        replaceTop(Tab.CHECK, Screen.AnalysisResult)
    }

    /** A retry is always something the user asked for, never automatic. */
    suspend fun retryAnalysis() {
        if (_state.value.messageText.trim().isEmpty()) return
        _state.update { it.copy(isAnalyzing = true, analysisFailure = null) }
        replaceTop(Tab.CHECK, Screen.Analyzing)

        when (val outcome = repository.analyzeMessage(_state.value.messageText, _state.value.inputMode)) {
            is ChanOutcome.Success ->
                _state.update { it.copy(isAnalyzing = false, analysis = outcome.value) }
            is ChanOutcome.Failure ->
                _state.update { it.copy(isAnalyzing = false, analysisFailure = outcome.reason) }
        }
        replaceTop(Tab.CHECK, Screen.AnalysisResult)
    }

    fun checkAnotherMessage() {
        _state.update {
            it.copy(
                messageText = "",
                selectedImageUri = null,
                analysis = null,
                analysisFailure = null,
                inputMode = InputMode.MANUAL,
            )
        }
        resetCheckTo(Screen.MessageInput)
    }

    // --- Community lookup ---
    fun setLookupType(type: LookupType) = _state.update { it.copy(lookupType = type, lookupValue = "") }
    fun updateLookupValue(value: String) = _state.update { it.copy(lookupValue = value) }

    suspend fun runLookup() {
        val value = _state.value.lookupValue
        if (value.trim().isEmpty()) return
        _state.update { it.copy(isLookingUp = true, lookup = null, lookupFailure = null) }

        when (val outcome = repository.lookup(_state.value.lookupType, value)) {
            is ChanOutcome.Success ->
                _state.update { it.copy(isLookingUp = false, lookup = outcome.value) }
            is ChanOutcome.Failure ->
                _state.update { it.copy(isLookingUp = false, lookupFailure = outcome.reason) }
        }
        // The raw value is dropped as the result flow opens; only the verdict remains.
        _state.update { it.copy(lookupValue = "") }
        push(Tab.CHECK, Screen.LookupResult)
    }

    fun lookupDifferent() {
        _state.update { it.copy(lookupValue = "", lookup = null, lookupFailure = null) }
        resetCheckTo(Screen.CommunityLookup)
    }

    // --- Android share intake (confirmation-gated) ---
    fun receiveSharedText(text: String) =
        _state.update { it.copy(pendingShare = ShareIntake(text = text, imageUri = null, isImage = false)) }

    fun receiveSharedImage(uri: String) =
        _state.update { it.copy(pendingShare = ShareIntake(text = null, imageUri = uri, isImage = true)) }

    /** Import shared content — only ever reached after explicit confirmation. */
    fun confirmSharedContent() {
        val pending = _state.value.pendingShare ?: return
        if (pending.isImage) {
            _state.update {
                it.copy(
                    selectedImageUri = pending.imageUri,
                    inputMode = InputMode.SHARE,
                    pendingShare = null,
                )
            }
        } else {
            _state.update {
                it.copy(
                    messageText = pending.text.orEmpty(),
                    inputMode = InputMode.SHARE,
                    pendingShare = null,
                )
            }
        }
        resetCheckTo(Screen.MessageInput)
    }

    /** Cancel the share sheet: nothing shared is retained. */
    fun cancelSharedContent() = _state.update { it.copy(pendingShare = null) }

    // --- Protection ---
    fun setGuardianSharing(enabled: Boolean) = _state.update { it.copy(guardianSharingEnabled = enabled) }
}
