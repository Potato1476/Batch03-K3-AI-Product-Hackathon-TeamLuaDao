package com.chan.app.speech

import android.content.Context
import android.content.Intent
import android.os.Build
import android.os.Bundle
import android.speech.RecognitionListener
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer

/**
 * The Android side of dictation (§A2, §A4).
 *
 * On API 31+ CHAN asks for `createOnDeviceSpeechRecognizer` first. The device's
 * own speech service is created **only** when the controller passes an
 * explicitly consented request, because that service may send audio to a
 * provider and the UI must not claim on-device privacy it does not have.
 *
 * No provider package is named here. Whatever Android has selected as the
 * system recognition service is what runs.
 *
 * Every call must happen on the main thread; `SpeechRecognizer` requires it.
 */
class AndroidRecognizerProvider(context: Context) : RecognizerProvider {

    private val context = context.applicationContext

    override fun isOnDeviceAvailable(): Boolean =
        Build.VERSION.SDK_INT >= Build.VERSION_CODES.S &&
            runCatching { SpeechRecognizer.isOnDeviceRecognitionAvailable(context) }.getOrDefault(false)

    override fun isDeviceServiceAvailable(): Boolean =
        runCatching { SpeechRecognizer.isRecognitionAvailable(context) }.getOrDefault(false)

    override fun createOnDevice(): RecognizerHandle? {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.S) return null
        return try {
            AndroidRecognizerHandle(SpeechRecognizer.createOnDeviceSpeechRecognizer(context), context)
        } catch (error: UnsupportedOperationException) {
            null
        } catch (error: SecurityException) {
            null
        } catch (error: RuntimeException) {
            null
        }
    }

    override fun createDeviceService(): RecognizerHandle? {
        if (!isDeviceServiceAvailable()) return null
        return try {
            AndroidRecognizerHandle(SpeechRecognizer.createSpeechRecognizer(context), context)
        } catch (error: SecurityException) {
            null
        } catch (error: RuntimeException) {
            null
        }
    }
}

/**
 * Adapts one `SpeechRecognizer` to [RecognizerHandle].
 *
 * The platform throws from `startListening` and `setRecognitionListener` in
 * states the documentation does not describe. Every crossing is guarded here
 * and turned into a [RecognizerErrorCode]; an exception message must never
 * reach the screen (§A3).
 */
private class AndroidRecognizerHandle(
    private val recognizer: SpeechRecognizer,
    private val context: Context,
) : RecognizerHandle {

    private var events: RecognitionEvents? = null
    private var destroyed = false

    override fun setListener(events: RecognitionEvents) {
        this.events = events
        guard {
            recognizer.setRecognitionListener(object : RecognitionListener {
                // Everything below is asynchronous: these are the platform's own
                // callbacks and the only place `events` is notified.
                /** The microphone is genuinely open. Not before. */
                override fun onReadyForSpeech(params: Bundle?) {
                    this@AndroidRecognizerHandle.events?.onReady()
                }

                override fun onBeginningOfSpeech() = Unit
                override fun onRmsChanged(rmsdB: Float) = Unit
                override fun onBufferReceived(buffer: ByteArray?) = Unit
                override fun onEvent(eventType: Int, params: Bundle?) = Unit

                /** Not a result. The controller starts its bounded wait here. */
                override fun onEndOfSpeech() {
                    this@AndroidRecognizerHandle.events?.onEnd()
                }

                override fun onPartialResults(partialResults: Bundle?) {
                    firstResult(partialResults)?.let { this@AndroidRecognizerHandle.events?.onPartial(it) }
                }

                override fun onResults(results: Bundle?) {
                    this@AndroidRecognizerHandle.events?.onFinal(firstResult(results).orEmpty())
                }

                override fun onError(error: Int) {
                    this@AndroidRecognizerHandle.events?.onError(mapError(error))
                }
            })
        }
    }

    override fun start(request: SpeechRequest) {
        guard { recognizer.startListening(intentFor(request)) }
    }

    override fun stop() {
        guard { recognizer.stopListening() }
    }

    override fun cancel() {
        guard { recognizer.cancel() }
    }

    override fun destroy() {
        if (destroyed) return
        destroyed = true
        events = null
        runCatching { recognizer.destroy() }
    }

    /**
     * Runs a synchronous platform call and translates its failure into a
     * [RecognizerFailure].
     *
     * It deliberately does **not** notify `events`. Reporting through a
     * callback and then returning normally told the controller the call had
     * succeeded, so a recognizer that was already destroyed went on to be
     * rendered as "Đang nghe trên máy…". A throw is the only signal a caller
     * cannot miss, and the exception's own message never escapes.
     */
    private inline fun guard(block: () -> Unit) {
        try {
            block()
        } catch (error: SecurityException) {
            throw RecognizerFailure(RecognizerErrorCode.PERMISSION)
        } catch (error: RuntimeException) {
            throw RecognizerFailure(RecognizerErrorCode.CLIENT)
        }
    }

    private fun intentFor(request: SpeechRequest) =
        Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
            putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
            putExtra(RecognizerIntent.EXTRA_LANGUAGE, request.languageTag)
            putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, request.partialResults)
            putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 1)
            putExtra(RecognizerIntent.EXTRA_CALLING_PACKAGE, context.packageName)
            // Sent only for the on-device attempt. For a consented device
            // service it would be a hint CHAN cannot keep, and the UI says so.
            if (request.preferOffline) {
                putExtra(RecognizerIntent.EXTRA_PREFER_OFFLINE, true)
            }
        }

    private fun firstResult(bundle: Bundle?): String? =
        bundle?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)?.firstOrNull()

    /**
     * The complete error set at compile SDK 35.
     *
     * The API 33 codes are written as literals on purpose: `minSdk` is 24, and
     * inlining a newer constant would make the mapping look version-safe while
     * hiding which numbers the older platforms can actually deliver.
     */
    private fun mapError(error: Int): RecognizerErrorCode = when (error) {
        SpeechRecognizer.ERROR_NO_MATCH,
        SpeechRecognizer.ERROR_SPEECH_TIMEOUT,
        -> RecognizerErrorCode.NO_SPEECH

        SpeechRecognizer.ERROR_RECOGNIZER_BUSY -> RecognizerErrorCode.BUSY
        SpeechRecognizer.ERROR_INSUFFICIENT_PERMISSIONS -> RecognizerErrorCode.PERMISSION
        SpeechRecognizer.ERROR_AUDIO -> RecognizerErrorCode.AUDIO
        SpeechRecognizer.ERROR_NETWORK, SpeechRecognizer.ERROR_NETWORK_TIMEOUT -> RecognizerErrorCode.NETWORK
        SpeechRecognizer.ERROR_SERVER -> RecognizerErrorCode.SERVER
        SpeechRecognizer.ERROR_CLIENT -> RecognizerErrorCode.CLIENT

        ERROR_TOO_MANY_REQUESTS -> RecognizerErrorCode.TOO_MANY_REQUESTS
        ERROR_SERVER_DISCONNECTED -> RecognizerErrorCode.SERVER_DISCONNECTED
        ERROR_LANGUAGE_NOT_SUPPORTED -> RecognizerErrorCode.LANGUAGE_NOT_SUPPORTED
        ERROR_LANGUAGE_UNAVAILABLE -> RecognizerErrorCode.LANGUAGE_UNAVAILABLE
        ERROR_CANNOT_CHECK_SUPPORT, ERROR_CANNOT_LISTEN_TO_DOWNLOAD_EVENTS -> RecognizerErrorCode.CLIENT

        else -> RecognizerErrorCode.OTHER
    }

    private companion object {
        // android.speech.SpeechRecognizer, API 33+ / 34+.
        const val ERROR_TOO_MANY_REQUESTS = 10
        const val ERROR_SERVER_DISCONNECTED = 11
        const val ERROR_LANGUAGE_NOT_SUPPORTED = 12
        const val ERROR_LANGUAGE_UNAVAILABLE = 13
        const val ERROR_CANNOT_CHECK_SUPPORT = 14
        const val ERROR_CANNOT_LISTEN_TO_DOWNLOAD_EVENTS = 15
    }
}
