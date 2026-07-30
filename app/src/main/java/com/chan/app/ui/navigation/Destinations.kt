package com.chan.app.ui.navigation

/** The four bottom-navigation destinations. */
enum class Tab {
    HOME,
    CHECK,
    PROTECT,
    SETTINGS,
}

/** Every screen state. Screens belong to a [Tab]'s back stack. */
sealed interface Screen {
    data object Home : Screen
    data object CheckHub : Screen
    data object MessageInput : Screen
    data object Analyzing : Screen

    /** Renders a live analysis at any risk level, or a user-safe failure. */
    data object AnalysisResult : Screen
    data object CommunityLookup : Screen
    data object LookupResult : Screen
    data object Protection : Screen
    data object Settings : Screen
}
