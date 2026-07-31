package com.chan.app

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import org.junit.Rule
import org.junit.Test

/**
 * Verifies the four bottom-navigation labels are present and each destination
 * is reachable. Requires a device/emulator to run; not executed in Sprint 01.
 */
class NavigationUiTest {

    @get:Rule
    val composeRule = createAndroidComposeRule<MainActivity>()

    @Test
    fun allFourBottomDestinationsAreReachable() {
        // Labels render.
        composeRule.onNodeWithText("Trang chủ").assertIsDisplayed()
        composeRule.onNodeWithText("Kiểm tra").assertIsDisplayed()
        composeRule.onNodeWithText("Bảo vệ").assertIsDisplayed()
        composeRule.onNodeWithText("Cài đặt").assertIsDisplayed()

        // Each destination opens its screen.
        composeRule.onNodeWithText("Bảo vệ").performClick()
        composeRule.onNodeWithText("Bảo vệ & riêng tư").assertIsDisplayed()

        composeRule.onNodeWithText("Cài đặt").performClick()
        composeRule.onNodeWithText("Chế độ tối").assertIsDisplayed()

        composeRule.onNodeWithText("Kiểm tra").performClick()
        composeRule.onNodeWithText("Bác muốn kiểm tra điều gì?").assertIsDisplayed()
    }
}
