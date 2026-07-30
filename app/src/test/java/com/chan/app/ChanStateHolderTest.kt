package com.chan.app

import com.chan.app.domain.FailureReason
import com.chan.app.domain.InputMode
import com.chan.app.domain.Risk
import com.chan.app.ui.ChanStateHolder
import com.chan.app.ui.navigation.Screen
import com.chan.app.ui.navigation.Tab
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class ChanStateHolderTest {

    private fun holder(repository: FakeChanRepository = FakeChanRepository()) =
        ChanStateHolder(repository) to repository

    @Test
    fun emptyTrimmedMessageDisablesAnalysis() {
        val (h, _) = holder()
        h.updateMessageText("   ")
        assertFalse("Blank message must disable analysis", h.state.value.canAnalyze)

        h.updateMessageText("  Có tin nhắn  ")
        assertTrue("Non-empty trimmed message must enable analysis", h.state.value.canAnalyze)
    }

    @Test
    fun analyzeTransitionsToTheResultScreen() = runTest {
        val (h, repository) = holder()
        h.openMessageInput()
        h.updateMessageText("nội dung nghi ngờ")
        h.analyze()

        val state = h.state.value
        assertEquals(Screen.AnalysisResult, state.current)
        assertEquals(Tab.CHECK, state.selectedTab)
        assertFalse(state.isAnalyzing)
        assertEquals(Risk.HIGH, state.analysis?.risk)
        assertEquals(InputMode.MANUAL, repository.analyzeCalls.single().second)
    }

    @Test
    fun aFailedAnalysisShowsAUserSafeStateAndKeepsTheRetryPath() = runTest {
        val repository = FakeChanRepository(analysis = FakeChanRepository.failure(FailureReason.TIMEOUT))
        val (h, _) = holder(repository)
        h.openMessageInput()
        h.updateMessageText("nội dung nghi ngờ")
        h.analyze()

        assertEquals(Screen.AnalysisResult, h.state.value.current)
        assertNull(h.state.value.analysis)
        assertEquals(FailureReason.TIMEOUT, h.state.value.analysisFailure)

        // The retry is a separate, user-initiated call — never automatic.
        assertEquals(1, repository.analyzeCalls.size)
        h.retryAnalysis()
        assertEquals(2, repository.analyzeCalls.size)
    }

    @Test
    fun sharedTextIsImportedOnlyAfterConfirmation() {
        val (h, _) = holder()
        h.receiveSharedText("tin nhắn được chia sẻ")

        // Before confirming, nothing is imported into the input.
        assertEquals("", h.state.value.messageText)
        assertTrue(h.state.value.pendingShare != null)

        h.confirmSharedContent()
        assertEquals("tin nhắn được chia sẻ", h.state.value.messageText)
        assertNull(h.state.value.pendingShare)
        assertEquals(Screen.MessageInput, h.state.value.current)
        assertEquals(InputMode.SHARE, h.state.value.inputMode)
    }

    @Test
    fun cancelingShareRetainsNothing() {
        val (h, _) = holder()
        h.receiveSharedText("tin nhắn được chia sẻ")
        h.cancelSharedContent()

        assertNull(h.state.value.pendingShare)
        assertEquals("", h.state.value.messageText)
    }

    @Test
    fun allFourTabsAreReachable() {
        val (h, _) = holder()
        h.selectTab(Tab.HOME)
        assertEquals(Screen.Home, h.state.value.current)
        h.selectTab(Tab.CHECK)
        assertEquals(Screen.CheckHub, h.state.value.current)
        h.selectTab(Tab.PROTECT)
        assertEquals(Screen.Protection, h.state.value.current)
        h.selectTab(Tab.SETTINGS)
        assertEquals(Screen.Settings, h.state.value.current)
    }

    @Test
    fun lookupFlowShowsTheResultAndDropsTheRawValue() = runTest {
        val (h, repository) = holder()
        h.openCommunityLookup()
        h.updateLookupValue("0900000000")
        h.runLookup()

        assertEquals(Screen.LookupResult, h.state.value.current)
        assertEquals(Risk.MEDIUM, h.state.value.lookup?.risk)
        assertEquals("0900000000", repository.lookupCalls.single().second)
        // The value the user typed does not survive into the result flow.
        assertEquals("", h.state.value.lookupValue)
    }

    @Test
    fun backPopsWithinTabStack() {
        val (h, _) = holder()
        h.openMessageInput() // CHECK: [CheckHub, MessageInput]
        assertTrue(h.state.value.canGoBack)
        assertTrue(h.back())
        assertEquals(Screen.CheckHub, h.state.value.current)
        assertFalse(h.state.value.canGoBack)
        assertFalse(h.back())
    }

    @Test
    fun checkingAnotherMessageClearsTheEarlierContent() = runTest {
        val (h, _) = holder()
        h.openMessageInput()
        h.updateMessageText("nội dung nghi ngờ")
        h.analyze()
        h.checkAnotherMessage()

        assertEquals("", h.state.value.messageText)
        assertNull(h.state.value.analysis)
        assertNull(h.state.value.analysisFailure)
        assertEquals(Screen.MessageInput, h.state.value.current)
    }
}
