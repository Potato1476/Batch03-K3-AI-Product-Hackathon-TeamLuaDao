package com.chan.app.ui

import android.Manifest
import android.app.Application
import android.content.pm.PackageManager
import androidx.core.content.ContextCompat
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.chan.app.data.ChanGraph
import com.chan.app.data.DataStoreThemePreferenceStore
import com.chan.app.data.ThemePreferenceStore
import com.chan.app.domain.ChanRepository
import com.chan.app.domain.LookupType
import com.chan.app.notification.NotificationAccess
import com.chan.app.speech.AndroidRecognizerProvider
import com.chan.app.speech.DefaultSpeechToTextController
import com.chan.app.speech.SpeechState
import com.chan.app.speech.SpeechToTextController
import com.chan.app.ui.navigation.Tab
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch

/**
 * Android state holder. Delegates flow/navigation logic to [ChanStateHolder]
 * (unit-tested separately) and adds persistence, live permission state, the
 * speech controller, and the coroutine scope that cancels in-flight analysis
 * when the screen goes away.
 */
class ChanViewModel @JvmOverloads constructor(
    app: Application,
    private val repository: ChanRepository = ChanGraph.of(app).repository,
    private val themeStore: ThemePreferenceStore = DataStoreThemePreferenceStore(app),
    val speech: SpeechToTextController = DefaultSpeechToTextController(AndroidRecognizerProvider(app)),
) : AndroidViewModel(app) {

    private val holder = ChanStateHolder(repository)
    private val graph = ChanGraph.of(app)

    val state: StateFlow<ChanUiState> = holder.state
    val speechState: StateFlow<SpeechState> = speech.state

    init {
        viewModelScope.launch {
            themeStore.darkMode.collect { holder.applyDarkMode(it) }
        }
        // Dictation lands in the editable field and stops there. Nothing is
        // analyzed until the user taps "Kiểm tra ngay".
        viewModelScope.launch {
            speech.state.collect { current ->
                if (current is SpeechState.FinalText) appendDictatedText(current.text)
            }
        }
        graph.refreshRulesInBackground()
        refreshSystemStatus()
    }

    // Navigation
    fun selectTab(tab: Tab) = holder.selectTab(tab)
    fun back(): Boolean = holder.back()

    // Home
    fun openMessageInput() = holder.openMessageInput()
    fun openCommunityLookup() = holder.openCommunityLookup()

    /** Opens the redacted result behind a CHAN warning notification, if it is still valid. */
    fun openPendingAlert() {
        graph.pendingAlerts.take()?.let { holder.openAlertResult(it) }
    }

    // Message input
    fun updateMessageText(text: String) = holder.updateMessageText(text)
    fun selectImage(uri: String) = holder.selectImage(uri)
    fun clearSelectedImage() = holder.clearSelectedImage()

    fun analyze() {
        viewModelScope.launch { holder.analyze() }
    }

    fun retryAnalysis() {
        viewModelScope.launch { holder.retryAnalysis() }
    }

    fun checkAnotherMessage() = holder.checkAnotherMessage()

    // Community lookup
    fun setLookupType(type: LookupType) = holder.setLookupType(type)
    fun updateLookupValue(value: String) = holder.updateLookupValue(value)

    fun runLookup() {
        viewModelScope.launch { holder.runLookup() }
    }

    fun lookupDifferent() = holder.lookupDifferent()

    // Share intake
    fun receiveSharedText(text: String) = holder.receiveSharedText(text)
    fun receiveSharedImage(uri: String) = holder.receiveSharedImage(uri)
    fun confirmSharedContent() = holder.confirmSharedContent()
    fun cancelSharedContent() = holder.cancelSharedContent()

    // Protection
    fun setGuardianSharing(enabled: Boolean) = holder.setGuardianSharing(enabled)

    /** The in-app switch. Turning it off stops processing on the next callback. */
    fun setZaloScanning(enabled: Boolean) {
        graph.protection.zaloScanningEnabled = enabled
        refreshSystemStatus()
    }

    /**
     * Re-reads the platform's answer for each system layer. Called whenever the
     * app returns to the foreground: the user may have changed any of them in
     * Android settings while CHAN was in the background.
     */
    fun refreshSystemStatus() {
        val context = getApplication<Application>()
        val microphoneGranted = ContextCompat.checkSelfPermission(
            context,
            Manifest.permission.RECORD_AUDIO,
        ) == PackageManager.PERMISSION_GRANTED

        holder.applySystemStatus(
            SystemStatus(
                notificationAccessGranted = NotificationAccess.isListenerEnabled(context),
                zaloScanningEnabled = graph.protection.zaloScanningEnabled,
                warningsAllowed = NotificationAccess.areWarningsAllowed(context),
                microphoneGranted = microphoneGranted,
                rulesFromServer = state.value.systemStatus.rulesFromServer,
            ),
        )
        viewModelScope.launch {
            val fromServer = graph.bundles.isServerBundle()
            holder.applySystemStatus(state.value.systemStatus.copy(rulesFromServer = fromServer))
        }
    }

    // Speech
    fun startDictation(allowDeviceService: Boolean = false) = speech.start(allowDeviceService)
    fun stopDictation() = speech.stop()
    fun cancelDictation() = speech.cancel()
    fun onMicrophonePermissionDenied() = speech.onPermissionDenied()
    fun acknowledgeSpeech() = speech.acknowledge()

    /** Called when the input screen is left or the app backgrounds (§C3). */
    fun releaseRecognizer() = speech.dispose()

    // Settings
    fun setDarkMode(enabled: Boolean) {
        holder.applyDarkMode(enabled)
        viewModelScope.launch { themeStore.setDarkMode(enabled) }
    }

    override fun onCleared() {
        speech.dispose()
        super.onCleared()
    }

    private fun appendDictatedText(dictated: String) {
        val existing = state.value.messageText
        val combined = if (existing.isBlank()) dictated else "${existing.trimEnd()} $dictated"
        holder.updateMessageText(combined)
    }
}
