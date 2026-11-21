package uz.tilsim.update

import android.app.Activity
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.provider.Settings
import androidx.core.content.FileProvider
import app.tauri.annotation.Command
import app.tauri.annotation.InvokeArg
import app.tauri.annotation.TauriPlugin
import app.tauri.plugin.Invoke
import app.tauri.plugin.JSObject
import app.tauri.plugin.Plugin
import java.io.File
import java.io.InputStream
import java.net.HttpURLConnection
import java.net.URL
import java.security.MessageDigest

/** Shares the downloaded update with the system installer only (see res/xml/tilsim_update_paths.xml). */
class UpdateFileProvider : FileProvider()

@InvokeArg
class UrlArgs {
    lateinit var url: String
}

@InvokeArg
class InstallArgs {
    lateinit var url: String
    lateinit var sha256: String
}

/**
 * Downloads a newer APK of this app from its GitHub releases and opens Android's installer.
 * Only https URLs under the project's own release downloads are accepted.
 */
@TauriPlugin
class UpdatePlugin(private val activity: Activity) : Plugin(activity) {
    private val allowedPrefix = "https://github.com/Coder-Dostonbe/RuMorph/releases/download/"
    private val maxTextBytes = 64 * 1024
    private val maxApkBytes = 300L * 1024 * 1024

    private fun open(url: String): HttpURLConnection {
        require(url.startsWith(allowedPrefix)) { "url not allowed" }
        val connection = URL(url).openConnection() as HttpURLConnection
        connection.instanceFollowRedirects = true
        connection.connectTimeout = 15_000
        connection.readTimeout = 30_000
        connection.setRequestProperty("Cache-Control", "no-cache")
        val code = connection.responseCode
        if (code != 200) {
            connection.disconnect()
            throw IllegalStateException("HTTP $code")
        }
        return connection
    }

    private fun readLimited(input: InputStream, limit: Int): ByteArray {
        val out = java.io.ByteArrayOutputStream()
        val buffer = ByteArray(8192)
        while (true) {
            val n = input.read(buffer)
            if (n < 0) break
            out.write(buffer, 0, n)
            if (out.size() > limit) throw IllegalStateException("response too large")
        }
        return out.toByteArray()
    }

    @Command
    fun fetchText(invoke: Invoke) {
        val args = invoke.parseArgs(UrlArgs::class.java)
        Thread {
            try {
                val connection = open(args.url)
                val bytes = connection.inputStream.use { readLimited(it, maxTextBytes) }
                connection.disconnect()
                val result = JSObject()
                result.put("text", String(bytes, Charsets.UTF_8))
                invoke.resolve(result)
            } catch (e: Exception) {
                invoke.reject(e.message ?: e.toString())
            }
        }.start()
    }

    @Command
    fun install(invoke: Invoke) {
        val args = invoke.parseArgs(InstallArgs::class.java)
        Thread {
            try {
                val dir = File(activity.cacheDir, "updates")
                dir.mkdirs()
                dir.listFiles()?.forEach { it.delete() }
                val apk = File(dir, "Tilsim-update.apk")
                val digest = MessageDigest.getInstance("SHA-256")
                val connection = open(args.url)
                var total = 0L
                connection.inputStream.use { input ->
                    apk.outputStream().use { output ->
                        val buffer = ByteArray(64 * 1024)
                        while (true) {
                            val n = input.read(buffer)
                            if (n < 0) break
                            total += n
                            if (total > maxApkBytes) throw IllegalStateException("download too large")
                            digest.update(buffer, 0, n)
                            output.write(buffer, 0, n)
                        }
                    }
                }
                connection.disconnect()
                val actual = digest.digest().joinToString("") { "%02x".format(it) }
                if (!actual.equals(args.sha256, ignoreCase = true)) {
                    apk.delete()
                    throw IllegalStateException("checksum mismatch")
                }
                activity.runOnUiThread {
                    try {
                        val result = JSObject()
                        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O &&
                            !activity.packageManager.canRequestPackageInstalls()
                        ) {
                            // The user allows "install unknown apps" for Tilsim once, then taps again.
                            val settings = Intent(
                                Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES,
                                Uri.parse("package:" + activity.packageName)
                            )
                            activity.startActivity(settings)
                            result.put("status", "permission")
                        } else {
                            val uri = FileProvider.getUriForFile(activity, activity.packageName + ".tilsim_update", apk)
                            val intent = Intent(Intent.ACTION_VIEW)
                            intent.setDataAndType(uri, "application/vnd.android.package-archive")
                            intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION or Intent.FLAG_ACTIVITY_NEW_TASK)
                            activity.startActivity(intent)
                            result.put("status", "installer")
                        }
                        invoke.resolve(result)
                    } catch (e: Exception) {
                        invoke.reject(e.message ?: e.toString())
                    }
                }
            } catch (e: Exception) {
                invoke.reject(e.message ?: e.toString())
            }
        }.start()
    }
}
