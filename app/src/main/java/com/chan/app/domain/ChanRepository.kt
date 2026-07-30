package com.chan.app.domain

/**
 * The integration seam kept from Sprint 01. Sprint 02 ships a live
 * implementation; the UI still talks only to this interface.
 *
 * Privacy invariant for every implementation: never log or persist the message
 * text, lookup value, OTPs, phone numbers, account numbers, or URLs passed in
 * here. Content is used for the duration of one call and then released.
 */
interface ChanRepository {

    /**
     * Analyze a message. Runs L0/L1 on-device first; the backend is called only
     * when the local gate says the content warrants it.
     *
     * @param message raw user text; implementations must NOT log or store it.
     * @param inputMode how the content arrived.
     * @param appPackage the source package, only for [InputMode.NOTIFICATION].
     * @param truncated true when the OS gave CHAN a shortened copy.
     */
    suspend fun analyzeMessage(
        message: String,
        inputMode: InputMode,
        appPackage: String? = null,
        truncated: Boolean = false,
    ): ChanOutcome<AnalysisResult>

    /**
     * Look up community reports for an account, phone number, or link.
     *
     * The raw value never leaves the device: the implementation normalizes it,
     * hashes it, sends only the first five hex characters, and compares the
     * full hash locally.
     */
    suspend fun lookup(type: LookupType, value: String): ChanOutcome<LookupResult>
}
