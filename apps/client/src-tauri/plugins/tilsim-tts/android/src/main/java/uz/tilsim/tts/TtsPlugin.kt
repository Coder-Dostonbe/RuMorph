package uz.tilsim.tts

import android.app.Activity
import android.speech.tts.TextToSpeech
import app.tauri.annotation.Command
import app.tauri.annotation.InvokeArg
import app.tauri.annotation.TauriPlugin
import app.tauri.plugin.Invoke
import app.tauri.plugin.JSObject
import app.tauri.plugin.Plugin
import java.util.Locale

@InvokeArg
class SpeakArgs {
    lateinit var text: String
    /** 1.0 is the engine's normal speed; the app sends 0.25 to 1.0. */
    var rate: Float = 0.85f
}

/**
 * Reads a Russian word aloud with the phone's own text-to-speech engine, for words that have no
 * recorded pronunciation. The engine starts on first use.
 *
 * state: "starting", "ready", "no_engine" (no TTS engine on the phone) or "no_russian" (the
 * engine has no Russian voice; the user can add one in the phone's settings).
 */
@TauriPlugin
class TtsPlugin(private val activity: Activity) : Plugin(activity) {
    private val lock = Any()
    private var tts: TextToSpeech? = null
    private var state = "idle"
    private val waiting = mutableListOf<() -> Unit>()

    private fun whenReady(block: () -> Unit) {
        synchronized(lock) {
            if (state == "idle") {
                state = "starting"
                waiting.add(block)
                activity.runOnUiThread { start() }
                return
            }
            if (state == "starting") {
                waiting.add(block)
                return
            }
        }
        block()
    }

    private fun start() {
        var engine: TextToSpeech? = null
        engine = TextToSpeech(activity) { status ->
            val result = if (status != TextToSpeech.SUCCESS) {
                "no_engine"
            } else {
                val language = engine?.setLanguage(Locale("ru", "RU")) ?: TextToSpeech.LANG_NOT_SUPPORTED
                if (language == TextToSpeech.LANG_MISSING_DATA || language == TextToSpeech.LANG_NOT_SUPPORTED) {
                    "no_russian"
                } else {
                    "ready"
                }
            }
            val run: List<() -> Unit>
            synchronized(lock) {
                tts = engine
                state = result
                run = waiting.toList()
                waiting.clear()
            }
            run.forEach { it() }
        }
    }

    @Command
    fun status(invoke: Invoke) {
        whenReady {
            val result = JSObject()
            result.put("state", state)
            invoke.resolve(result)
        }
    }

    @Command
    fun speak(invoke: Invoke) {
        val args = invoke.parseArgs(SpeakArgs::class.java)
        whenReady {
            val engine = tts
            if (state != "ready" || engine == null) {
                invoke.reject(state)
                return@whenReady
            }
            engine.setSpeechRate(args.rate.coerceIn(0.25f, 1.0f))
            val code = engine.speak(args.text.take(200), TextToSpeech.QUEUE_FLUSH, null, "zabon-word")
            if (code == TextToSpeech.SUCCESS) {
                val result = JSObject()
                result.put("state", state)
                invoke.resolve(result)
            } else {
                invoke.reject("speak_failed")
            }
        }
    }
}
