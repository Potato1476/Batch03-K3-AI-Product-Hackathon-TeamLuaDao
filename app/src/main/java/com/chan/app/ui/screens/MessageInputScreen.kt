package com.chan.app.ui.screens

import android.Manifest
import android.content.pm.PackageManager
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.PickVisualMediaRequest
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Image
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material.icons.filled.Mic
import androidx.compose.material.icons.filled.Stop
import androidx.compose.material3.Icon
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.input.KeyboardCapitalization
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import com.chan.app.R
import com.chan.app.speech.SpeechState
import com.chan.app.ui.UserSafeMessages
import com.chan.app.ui.components.BackTopBar
import com.chan.app.ui.components.ChanCard
import com.chan.app.ui.components.PrimaryCta
import com.chan.app.ui.components.PrivacyBox
import com.chan.app.ui.components.SecondaryButton
import com.chan.app.ui.components.SegmentedControl
import com.chan.app.ui.components.screenContentPadding
import com.chan.app.ui.theme.ChanTheme

/**
 * Paste, dictate, or pick an image, then decide to check.
 *
 * The microphone replaces Sprint 01's inert affordance, but the rule it obeys
 * is the same one the whole product obeys: recognized speech lands in this
 * editable field and goes no further until the user presses the CTA.
 */
@Composable
fun MessageInputScreen(
    message: String,
    selectedImageUri: String?,
    canAnalyze: Boolean,
    speechState: SpeechState,
    usingOnDeviceRecognizer: Boolean,
    onMessageChange: (String) -> Unit,
    onImageSelected: (String) -> Unit,
    onClearImage: () -> Unit,
    onAnalyze: () -> Unit,
    onStartDictation: (Boolean) -> Unit,
    onStopDictation: () -> Unit,
    onMicrophoneDenied: () -> Unit,
    onReleaseRecognizer: () -> Unit,
    onBack: () -> Unit,
) {
    val colors = ChanTheme.colors
    val context = LocalContext.current
    // 0 = text mode, 1 = image mode.
    var mode by remember { mutableIntStateOf(0) }

    // Leaving the screen always stops listening and destroys the recognizer.
    DisposableEffect(Unit) { onDispose { onReleaseRecognizer() } }

    val picker = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.PickVisualMedia(),
    ) { uri ->
        // Retain only the URI needed for the active screen; do not copy or upload.
        if (uri != null) onImageSelected(uri.toString())
    }

    val microphonePermission = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.RequestPermission(),
    ) { granted ->
        if (granted) onStartDictation(false) else onMicrophoneDenied()
    }

    fun requestDictation() {
        val granted = ContextCompat.checkSelfPermission(
            context,
            Manifest.permission.RECORD_AUDIO,
        ) == PackageManager.PERMISSION_GRANTED
        // The permission is asked for here, at the tap — never at first launch.
        if (granted) onStartDictation(false) else microphonePermission.launch(Manifest.permission.RECORD_AUDIO)
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(screenContentPadding()),
    ) {
        BackTopBar(
            title = stringResource(R.string.input_title),
            backDescription = stringResource(R.string.cd_back),
            onBack = onBack,
        )
        Spacer(Modifier.height(16.dp))

        SegmentedControl(
            options = listOf(
                stringResource(R.string.input_mode_text),
                stringResource(R.string.input_mode_image),
            ),
            selectedIndex = mode,
            onSelect = { mode = it },
        )
        Spacer(Modifier.height(16.dp))

        if (mode == 0) {
            OutlinedTextField(
                value = message,
                onValueChange = onMessageChange,
                modifier = Modifier
                    .fillMaxWidth()
                    .heightIn(min = 160.dp),
                textStyle = ChanTheme.type.body,
                placeholder = { Text(stringResource(R.string.input_placeholder), style = ChanTheme.type.body) },
                keyboardOptions = KeyboardOptions(capitalization = KeyboardCapitalization.Sentences),
            )
            Spacer(Modifier.height(16.dp))
            DictationPanel(
                speechState = speechState,
                usingOnDeviceRecognizer = usingOnDeviceRecognizer,
                onStart = { requestDictation() },
                onStop = onStopDictation,
                onAllowDeviceService = { onStartDictation(true) },
            )
        } else {
            ChanCard {
                if (selectedImageUri == null) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Icon(Icons.Filled.Image, contentDescription = null, tint = colors.brand, modifier = Modifier.size(28.dp))
                        Spacer(Modifier.width(12.dp))
                        Text(
                            text = stringResource(R.string.input_image_hint),
                            style = ChanTheme.type.body,
                            color = colors.bodyText,
                        )
                    }
                    Spacer(Modifier.height(12.dp))
                    SecondaryButton(
                        text = stringResource(R.string.input_pick_image),
                        onClick = {
                            picker.launch(
                                PickVisualMediaRequest(ActivityResultContracts.PickVisualMedia.ImageOnly),
                            )
                        },
                        leadingIcon = Icons.Filled.Image,
                    )
                } else {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Icon(Icons.Filled.CheckCircle, contentDescription = null, tint = colors.success, modifier = Modifier.size(28.dp))
                        Spacer(Modifier.width(12.dp))
                        Column(Modifier.weight(1f)) {
                            Text(
                                text = stringResource(R.string.input_image_selected),
                                style = ChanTheme.type.bodyStrong,
                                color = colors.secondaryHeading,
                            )
                            // Honest about the gap rather than inventing a result.
                            Text(
                                text = stringResource(R.string.input_image_note),
                                style = ChanTheme.type.caption,
                                color = colors.mutedText,
                            )
                        }
                    }
                    Spacer(Modifier.height(12.dp))
                    SecondaryButton(
                        text = stringResource(R.string.input_pick_another),
                        onClick = { onClearImage() },
                    )
                }
            }
        }

        Spacer(Modifier.height(16.dp))
        PrivacyBox(text = stringResource(R.string.input_privacy_box), icon = Icons.Filled.Lock)
        Spacer(Modifier.height(20.dp))

        // Image selection never enables analysis on its own: CHAN cannot read a
        // picture yet, and a result from nothing would be a lie.
        PrimaryCta(
            text = stringResource(R.string.input_analyze_now),
            onClick = onAnalyze,
            enabled = canAnalyze,
        )
    }
}

@Composable
private fun DictationPanel(
    speechState: SpeechState,
    usingOnDeviceRecognizer: Boolean,
    onStart: () -> Unit,
    onStop: () -> Unit,
    onAllowDeviceService: () -> Unit,
) {
    val colors = ChanTheme.colors
    val listening = speechState is SpeechState.Listening || speechState is SpeechState.ReceivingPartial
    val statusRes = UserSafeMessages.forSpeech(speechState)
    val statusLabel = stringResource(R.string.cd_speech_status)

    ChanCard {
        if (listening) {
            PrimaryCta(
                text = stringResource(R.string.speech_button_stop),
                onClick = onStop,
                leadingIcon = Icons.Filled.Stop,
            )
        } else {
            SecondaryButton(
                text = stringResource(R.string.speech_button_start),
                onClick = onStart,
                leadingIcon = Icons.Filled.Mic,
            )
        }

        if (statusRes != null) {
            Spacer(Modifier.height(10.dp))
            Text(
                text = stringResource(statusRes),
                style = ChanTheme.type.bodyStrong,
                color = if (listening) colors.brand else colors.bodyText,
                // Announced to a screen reader as it changes.
                modifier = Modifier.semantics {
                    contentDescription = statusLabel
                    liveRegion = LiveRegionMode.Polite
                },
            )
        }

        // Partial text is visible but stays out of the editable field until the
        // recognizer commits to it.
        (speechState as? SpeechState.ReceivingPartial)?.let { partial ->
            Spacer(Modifier.height(8.dp))
            Text(
                text = partial.text,
                style = ChanTheme.type.body,
                color = colors.mutedText,
            )
        }

        if (speechState is SpeechState.OnDeviceUnavailable) {
            Spacer(Modifier.height(12.dp))
            SecondaryButton(
                text = stringResource(R.string.speech_use_device_service),
                onClick = onAllowDeviceService,
            )
        }

        if (listening && usingOnDeviceRecognizer) {
            Spacer(Modifier.height(8.dp))
            // Only claimed when the on-device factory is genuinely in use.
            Text(
                text = stringResource(R.string.speech_on_device_note),
                style = ChanTheme.type.caption,
                color = colors.mutedText,
            )
        }

        Spacer(Modifier.height(10.dp))
        Text(
            text = stringResource(R.string.speech_explanation),
            style = ChanTheme.type.caption,
            color = colors.mutedText,
        )
    }
}
