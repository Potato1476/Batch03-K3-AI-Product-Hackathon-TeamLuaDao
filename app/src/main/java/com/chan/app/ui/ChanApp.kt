package com.chan.app.ui

import android.Manifest
import android.os.Build
import androidx.activity.compose.BackHandler
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.Search
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.filled.Shield
import androidx.compose.material3.Icon
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.chan.app.R
import com.chan.app.domain.InputMode
import com.chan.app.notification.NotificationAccess
import com.chan.app.ui.components.ShareConfirmationSheet
import com.chan.app.ui.navigation.Screen
import com.chan.app.ui.navigation.Tab
import com.chan.app.ui.screens.AnalysisResultScreen
import com.chan.app.ui.screens.AnalyzingScreen
import com.chan.app.ui.screens.CheckHubScreen
import com.chan.app.ui.screens.CommunityLookupScreen
import com.chan.app.ui.screens.HomeScreen
import com.chan.app.ui.screens.LookupResultScreen
import com.chan.app.ui.screens.MessageInputScreen
import com.chan.app.ui.screens.ProtectionScreen
import com.chan.app.ui.screens.SettingsScreen
import com.chan.app.ui.theme.ChanTheme

private data class TabSpec(val tab: Tab, val icon: ImageVector, val labelRes: Int)

@Composable
fun ChanApp(viewModel: ChanViewModel) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val speechState by viewModel.speechState.collectAsStateWithLifecycle()

    ChanTheme(darkTheme = state.darkMode) {
        val tabs = listOf(
            TabSpec(Tab.HOME, Icons.Filled.Home, R.string.nav_home),
            TabSpec(Tab.CHECK, Icons.Filled.Search, R.string.nav_check),
            TabSpec(Tab.PROTECT, Icons.Filled.Shield, R.string.nav_protect),
            TabSpec(Tab.SETTINGS, Icons.Filled.Settings, R.string.nav_settings),
        )

        // System back pops the current tab's stack when possible.
        BackHandler(enabled = state.canGoBack) { viewModel.back() }

        Scaffold(
            containerColor = ChanTheme.colors.screenBackground,
            bottomBar = {
                NavigationBar(containerColor = ChanTheme.colors.card) {
                    tabs.forEach { spec ->
                        val label = stringResource(spec.labelRes)
                        NavigationBarItem(
                            selected = state.selectedTab == spec.tab,
                            onClick = { viewModel.selectTab(spec.tab) },
                            icon = { Icon(spec.icon, contentDescription = label) },
                            label = { Text(label, style = ChanTheme.type.caption) },
                        )
                    }
                }
            },
        ) { innerPadding ->
            Box(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(innerPadding),
            ) {
                ScreenContent(state = state, speechState = speechState, viewModel = viewModel)
            }
        }

        // Share confirmation modal: content is imported ONLY on confirmation.
        state.pendingShare?.let { pending ->
            ShareConfirmationSheet(
                isImage = pending.isImage,
                onConfirm = { viewModel.confirmSharedContent() },
                onCancel = { viewModel.cancelSharedContent() },
            )
        }
    }
}

@Composable
private fun ScreenContent(
    state: ChanUiState,
    speechState: com.chan.app.speech.SpeechState,
    viewModel: ChanViewModel,
) {
    val context = LocalContext.current

    /**
     * POST_NOTIFICATIONS is requested here, when the user turns Zalo protection
     * on — not at launch. Denying it does not switch protection off; the
     * protection screen then explains that warnings cannot be shown.
     */
    val warningPermission = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.RequestPermission(),
    ) { viewModel.refreshSystemStatus() }

    fun openNotificationAccessSettings() {
        runCatching { context.startActivity(NotificationAccess.listenerSettingsIntent()) }
    }

    fun openWarningSettings() {
        runCatching { context.startActivity(NotificationAccess.appNotificationSettingsIntent(context)) }
    }

    /** Zalo's own notification settings. CHAN cannot read them, only open them. */
    fun openZaloNotificationSettings() {
        runCatching { context.startActivity(NotificationAccess.watchedAppNotificationSettingsIntent()) }
    }

    fun enableZaloProtection() {
        viewModel.setZaloScanning(true)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            warningPermission.launch(Manifest.permission.POST_NOTIFICATIONS)
        }
        if (!state.systemStatus.notificationAccessGranted) openNotificationAccessSettings()
    }

    when (state.current) {
        Screen.Home -> HomeScreen(
            protectionHealth = state.systemStatus.protectionHealth,
            onOpenMessage = viewModel::openMessageInput,
            onOpenLookup = viewModel::openCommunityLookup,
            onOpenProtection = { viewModel.selectTab(Tab.PROTECT) },
        )

        Screen.CheckHub -> CheckHubScreen(
            onOpenMessage = viewModel::openMessageInput,
            onOpenLookup = viewModel::openCommunityLookup,
        )

        Screen.MessageInput -> MessageInputScreen(
            message = state.messageText,
            selectedImageUri = state.selectedImageUri,
            canAnalyze = state.canAnalyze,
            speechState = speechState,
            onMessageChange = viewModel::updateMessageText,
            onImageSelected = viewModel::selectImage,
            onClearImage = viewModel::clearSelectedImage,
            onAnalyze = viewModel::analyze,
            onStartDictation = viewModel::startDictation,
            onStopDictation = viewModel::stopDictation,
            onCancelDictation = viewModel::cancelDictation,
            onDismissSpeech = viewModel::acknowledgeSpeech,
            onMicrophoneDenied = viewModel::onMicrophonePermissionDenied,
            onReleaseRecognizer = viewModel::releaseRecognizer,
            onBack = { viewModel.back() },
        )

        Screen.Analyzing -> AnalyzingScreen()

        Screen.AnalysisResult -> AnalysisResultScreen(
            result = state.analysis,
            failure = state.analysisFailure,
            fromNotification = state.inputMode == InputMode.NOTIFICATION,
            onRetry = viewModel::retryAnalysis,
            onCheckAnother = viewModel::checkAnotherMessage,
        )

        Screen.CommunityLookup -> CommunityLookupScreen(
            lookupType = state.lookupType,
            value = state.lookupValue,
            canLookup = state.canLookup,
            isLookingUp = state.isLookingUp,
            onTypeChange = viewModel::setLookupType,
            onValueChange = viewModel::updateLookupValue,
            onLookup = viewModel::runLookup,
            onBack = { viewModel.back() },
        )

        Screen.LookupResult -> LookupResultScreen(
            result = state.lookup,
            failure = state.lookupFailure,
            onRetry = viewModel::lookupDifferent,
            onLookupDifferent = viewModel::lookupDifferent,
        )

        Screen.Protection -> ProtectionScreen(
            status = state.systemStatus,
            guardianSharingEnabled = state.guardianSharingEnabled,
            onEnableZaloProtection = { enableZaloProtection() },
            onDisableZaloProtection = { viewModel.setZaloScanning(false) },
            onOpenNotificationAccessSettings = { openNotificationAccessSettings() },
            onOpenWarningSettings = { openWarningSettings() },
            onOpenZaloNotificationSettings = { openZaloNotificationSettings() },
            onReconnect = { viewModel.reconnectNow() },
            onStopSharing = { viewModel.setGuardianSharing(false) },
        )

        Screen.Settings -> SettingsScreen(
            darkMode = state.darkMode,
            status = state.systemStatus,
            onDarkModeChange = viewModel::setDarkMode,
            onOpenNotificationAccessSettings = { openNotificationAccessSettings() },
            onOpenWarningSettings = { openWarningSettings() },
            onOpenMicrophoneSettings = {
                runCatching { context.startActivity(NotificationAccess.appDetailsIntent(context)) }
            },
        )
    }
}
