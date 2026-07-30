package com.chan.app.speech

import android.content.Context
import android.content.Intent
import android.os.Build
import android.os.Bundle
import android.speech.RecognitionListener
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer

/**
 * The Android side of dictation (§C2).
 *
 * On API 31+ CHAN asks for `createOnDeviceSpeechRecognizer` first. Only if the
 * phone has none — and only after the user says yes — does it fall back to the
 * device's speech service, because that service may send audio to a provider
 * and the UI must not claim on-device privacy it does not have.
 *
 * Every call here must happen on the main thread; `SpeechRecognizer` requires it.
 */
class AndroidRecognizerProvider(context: Context) : RecognizerProvider {

    private val context = context.applicationContext

    override fun isOnDeviceAvailable(): Boolean =
        Build.VERSION.SDK_INT >= Build.VERSION_CODES.S &&
            runCatching { SpeechRecognizer.isOnDeviceRecognitionAvailable(context) }.getOrDefault(false)

    override fun createOnDevice(): RecognizerHandle? {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.S) return null
        return try {
            AndroidRecognizerHandle(SpeechRecognizer.createOnDeviceSpeechRecognizer(context), context)
        } catch (error: UnsupportedOperationException) {
            null
        } catch (error: RuntimeException) {
            null
        }
    }

    override fun createDeviceService(): RecognizerHandle? {
        if (!runCatching { SpeechRecognizer.isRecognitionAvailable(context) }.getOrDefault(false)) return null
        return try {
            AndroidRecognizerHandle(SpeechRecognizer.createSpeechRecognizer(context), context)
        } catch (error: RuntimeException) {
            null
        }
    }
}

/** Adapts one `SpeechRecognizer` to [RecognizerHandle]. */
private class AndroidRecognizerHandle(
    private val recognizer: SpeechRecognizer,
    private val context: Context,
) : RecognizerHandle {

    private var events: RecognitionEvents? = null

    override fun setListener(events: RecognitionEvents) {
        this.events = events
        recognizer.setRecognitionListener(object : RecognitionListener {
            override fun onReadyForSpeech(params: Bundle?) = Unit
            override fun onBeginningOfSpeech() = Unit
            override fun onRmsChanged(rmsdB: Float) = Unit
            override fun onBufferReceived(buffer: ByteArray?) = Unit
            override fun onEndOfSpeech() = Unit
            override fun onEvent(eventType: Int, params: Bundle?) = Unit

            override fun onPartialResults(partialResults: Bundle?) {
                firstResult(partialResults)?.let { events.onPartial(it) }
            }

            override fun onResults(results: Bundle?) {
                events.onFinal(firstResult(results).orEmpty())
            }

            override fun onError(error: Int) {
                events.onError(mapError(error))
            }
        })
    }

    override fun start(request: SpeechRequest) {
        recognizer.startListening(intentFor(request))
    }

    override fun stop() = recognizer.stopListening()

    override fun cancel() = recognizer.cancel()

    override fun destroy() {
        events = null
        recognizer.destroy()
    }

    private fun intentFor(request: SpeechRequest) =
        Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
            putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
            putExtra(RecognizerIntent.EXTRA_LANGUAGE, request.languageTag)
            putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, request.partialResults)
            // A hint to the provider, not a promise the UI may repeat.
            putExtra(RecognizerIntent.EXTRA_PREFER_OFFLINE, request.preferOffline)
            putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 1)
            putExtra(RecognizerIntent.EXTRA_CALLING_PACKAGE, context.packageName)
        }

    private fun firstResult(bundle: Bundle?): String? =
        bundle?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)?.firstOrNull()

    private fun mapError(error: Int): RecognizerErrorCode = when (error) {
        SpeechRecognizer.ERROR_NO_MATCH, SpeechRecognizer.ERROR_SPEECH_TIMEOUT -> RecognizerErrorCode.NO_SPEECH
        SpeechRecognizer.ERROR_RECOGNIZER_BUSY -> RecognizerErrorCode.BUSY
        SpeechRecognizer.ERROR_INSUFFICIENT_PERMISSIONS -> RecognizerErrorCode.PERMISSION
        SpeechRecognizer.ERROR_NETWORK,
        SpeechRecognizer.ERROR_NETWORK_TIMEOUT,
        SpeechRecognizer.ERROR_SERVER,
        -> RecognizerErrorCode.NETWORK_OR_PROVIDER
        else -> RecognizerErrorCode.OTHER
    }
}
