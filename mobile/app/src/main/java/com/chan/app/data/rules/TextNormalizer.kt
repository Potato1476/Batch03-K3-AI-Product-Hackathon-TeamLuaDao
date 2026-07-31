package com.chan.app.data.rules

import java.text.Normalizer
import java.util.Locale

/**
 * The L0 layer, ported step-for-step from the web engine
 * (`apps/web/src/engine.ts::matchingText`) so both clients feed byte-identical
 * text to the same regexes.
 *
 * Order matters and must not be "tidied": NFKC, strip invisibles, lowercase,
 * collapse whitespace, strip diacritics, then teencode. Teencode keys are
 * accent-free, so substituting before the diacritic pass would miss them.
 */
object TextNormalizer {

    private val VIETNAMESE = Locale.forLanguageTag("vi")
    private val WHITESPACE = Regex("\\s+")

    /**
     * Combining marks produced by NFD. Vietnamese tones and vowel modifiers all
     * live in U+0300–U+036F; the wider `Mn` category also covers marks the
     * bundle may see in mixed-script text.
     */
    private val COMBINING_MARKS = Regex("\\p{Mn}+")

    fun normalize(text: String, config: L0Config): String {
        var value = Normalizer.normalize(text, Normalizer.Form.NFKC)

        for (invisible in config.stripInvisible) {
            if (invisible.isNotEmpty()) value = value.replace(invisible, "")
        }
        if (config.lowercase) value = value.lowercase(VIETNAMESE)
        if (config.collapseWhitespace) value = WHITESPACE.replace(value, " ").trim()
        if (config.stripDiacriticsForMatching) {
            value = COMBINING_MARKS.replace(Normalizer.normalize(value, Normalizer.Form.NFD), "")
                .replace("đ", "d")
                .replace("Đ", "D")
        }
        if (config.teencode.isNotEmpty()) {
            value = value.split(" ").joinToString(" ") { word -> config.teencode[word] ?: word }
        }
        return value
    }
}
