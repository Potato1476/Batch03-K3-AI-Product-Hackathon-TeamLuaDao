package com.chan.app

import android.content.Intent
import android.net.Uri
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.viewModels
import androidx.core.content.IntentCompat
import com.chan.app.ui.ChanApp
import com.chan.app.ui.ChanViewModel

class MainActivity : ComponentActivity() {

    private val viewModel: ChanViewModel by viewModels()

    override fun onCreate(savedInstanceState: Bundle?) {
        enableEdgeToEdge()
        super.onCreate(savedInstanceState)
        handleIntent(intent)
        setContent { ChanApp(viewModel) }
    }

    // Handle a new share or warning tap while the activity is open (singleTask).
    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        handleIntent(intent)
    }

    override fun onResume() {
        super.onResume()
        // Notification access, warning permission, and the microphone can all be
        // changed in Android settings while CHAN is in the background. The
        // platform's answer is re-read here rather than assumed.
        viewModel.refreshSystemStatus()
    }

    override fun onStop() {
        // Listening never continues once the app is no longer in front.
        viewModel.releaseRecognizer()
        super.onStop()
    }

    private fun handleIntent(intent: Intent?) {
        if (intent == null) return
        if (intent.action == ACTION_OPEN_ALERT) {
            // Opens the redacted result behind a CHAN warning. No source content
            // travels in the intent.
            viewModel.openPendingAlert()
            return
        }
        handleShareIntent(intent)
    }

    /**
     * Turns an ACTION_SEND intent into a pending share awaiting confirmation.
     * The shared text/URI is NEVER logged; only the URI is retained for images.
     */
    private fun handleShareIntent(intent: Intent) {
        if (intent.action != Intent.ACTION_SEND) return
        val type = intent.type ?: return
        when {
            type == "text/plain" -> {
                val text = intent.getStringExtra(Intent.EXTRA_TEXT)
                if (!text.isNullOrBlank()) viewModel.receiveSharedText(text)
            }
            type.startsWith("image/") -> {
                val uri = IntentCompat.getParcelableExtra(intent, Intent.EXTRA_STREAM, Uri::class.java)
                if (uri != null) viewModel.receiveSharedImage(uri.toString())
            }
        }
    }

    companion object {
        /** Sent by a CHAN warning notification; carries no content of its own. */
        const val ACTION_OPEN_ALERT = "com.chan.app.action.OPEN_ALERT"
    }
}
