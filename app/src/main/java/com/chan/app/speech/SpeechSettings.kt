package com.chan.app.speech

import android.content.Context
import android.content.Intent
import android.net.Uri
import android.provider.Settings

/**
 * Where to send someone whose phone cannot recognise speech at all (§A4).
 *
 * CHAN never names a provider package. If Android has no recognition service —
 * or the one it has cannot do Vietnamese — the honest move is to hand the user
 * the system screen where that is configured and leave paste and image input
 * working in the meantime.
 */
object SpeechSettings {

    /**
     * Android's voice-input screen, falling back to CHAN's app details on the
     * phones that do not expose it.
     */
    fun open(context: Context): Boolean {
        val voiceInput = Intent(Settings.ACTION_VOICE_INPUT_SETTINGS)
            .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        if (runCatching { context.startActivity(voiceInput) }.isSuccess) return true
        return openAppSettings(context)
    }

    /**
     * CHAN's own app page, where a denied microphone permission is turned back
     * on. Offered instead of a retry button that would only be denied again.
     */
    fun openAppSettings(context: Context): Boolean {
        val appDetails = Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS)
            .setData(Uri.fromParts("package", context.packageName, null))
            .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        return runCatching { context.startActivity(appDetails) }.isSuccess
    }
}
