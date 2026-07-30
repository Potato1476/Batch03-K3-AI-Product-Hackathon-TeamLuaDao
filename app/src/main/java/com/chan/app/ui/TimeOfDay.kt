package com.chan.app.ui

import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

/**
 * Clock times for the protection screen ("Kết nối gần nhất lúc 18:42").
 *
 * A time is the only thing CHAN is willing to show about past activity. It says
 * *that* something happened, never what it was.
 */
object TimeOfDay {

    fun format(epochMillis: Long, locale: Locale = Locale.getDefault()): String =
        SimpleDateFormat(PATTERN, locale).format(Date(epochMillis))

    private const val PATTERN = "HH:mm"
}
