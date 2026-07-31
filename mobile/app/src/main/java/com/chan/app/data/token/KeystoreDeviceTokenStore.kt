package com.chan.app.data.token

import android.content.Context
import android.content.SharedPreferences
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

/**
 * Stores the device token encrypted with a hardware-backed key where the phone
 * provides one.
 *
 * The AES key never leaves the Android Keystore — this class only ever holds a
 * handle to it. What lands in SharedPreferences is `base64(iv | ciphertext)`,
 * which is useless without the key.
 *
 * Every failure path degrades to "no token": a phone whose Keystore has been
 * reset (a common consequence of changing the lock screen) simply gets a new
 * device identity rather than a crash on launch.
 */
class KeystoreDeviceTokenStore(context: Context) : DeviceTokenStore {

    private val preferences: SharedPreferences =
        context.applicationContext.getSharedPreferences(PREFERENCES_NAME, Context.MODE_PRIVATE)

    override fun read(): String? {
        val stored = preferences.getString(KEY_TOKEN, null) ?: return null
        return try {
            val raw = Base64.decode(stored, Base64.NO_WRAP)
            if (raw.size <= IV_LENGTH) return null
            val iv = raw.copyOfRange(0, IV_LENGTH)
            val payload = raw.copyOfRange(IV_LENGTH, raw.size)
            val cipher = Cipher.getInstance(TRANSFORMATION)
            cipher.init(Cipher.DECRYPT_MODE, secretKey(), GCMParameterSpec(GCM_TAG_BITS, iv))
            String(cipher.doFinal(payload), Charsets.UTF_8)
        } catch (error: Exception) {
            // Unreadable ciphertext is indistinguishable from no token.
            clear()
            null
        }
    }

    override fun write(token: String) {
        try {
            val cipher = Cipher.getInstance(TRANSFORMATION)
            cipher.init(Cipher.ENCRYPT_MODE, secretKey())
            val payload = cipher.doFinal(token.toByteArray(Charsets.UTF_8))
            val combined = cipher.iv + payload
            preferences.edit()
                .putString(KEY_TOKEN, Base64.encodeToString(combined, Base64.NO_WRAP))
                .apply()
        } catch (error: Exception) {
            // Better to re-issue a token next launch than to persist it in the clear.
            clear()
        }
    }

    override fun clear() {
        preferences.edit().remove(KEY_TOKEN).apply()
    }

    private fun secretKey(): SecretKey {
        val keyStore = KeyStore.getInstance(ANDROID_KEYSTORE).apply { load(null) }
        (keyStore.getEntry(KEY_ALIAS, null) as? KeyStore.SecretKeyEntry)?.let { return it.secretKey }

        val generator = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, ANDROID_KEYSTORE)
        generator.init(
            KeyGenParameterSpec.Builder(
                KEY_ALIAS,
                KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT,
            )
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                .setRandomizedEncryptionRequired(true)
                .build(),
        )
        return generator.generateKey()
    }

    private companion object {
        const val ANDROID_KEYSTORE = "AndroidKeyStore"
        const val KEY_ALIAS = "chan.device_token.v1"
        const val TRANSFORMATION = "AES/GCM/NoPadding"
        const val PREFERENCES_NAME = "chan_device_identity"

        /** Field name is deliberately about the credential, never about content. */
        const val KEY_TOKEN = "device_token_ciphertext"
        const val IV_LENGTH = 12
        const val GCM_TAG_BITS = 128
    }
}
