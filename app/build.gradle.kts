plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.compose")
    id("org.jetbrains.kotlin.plugin.serialization")
}

/**
 * Base URL configuration (Sprint 02 §A2).
 *
 * No production URL or secret is ever hardcoded in Kotlin. The debug default is
 * the Android emulator loopback alias; a physical phone overrides it from an
 * uncommitted `local.properties` / `-P` Gradle property. The release build has
 * no default at all and fails if an explicit HTTPS URL is not supplied.
 */
fun String.ensureTrailingSlash(): String = if (endsWith("/")) this else "$this/"

val debugApiBaseUrl: String =
    (providers.gradleProperty("CHAN_API_BASE_URL").orNull ?: "http://10.0.2.2:8000/").ensureTrailingSlash()
val releaseApiBaseUrl: String? =
    providers.gradleProperty("CHAN_RELEASE_API_BASE_URL").orNull?.ensureTrailingSlash()

android {
    namespace = "com.chan.app"
    compileSdk = 35
    buildToolsVersion = "36.0.0"

    defaultConfig {
        applicationId = "com.chan.app"
        minSdk = 24
        targetSdk = 35
        versionCode = 2
        versionName = "0.2.0-sprint02"

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
        vectorDrawables { useSupportLibrary = true }
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro",
            )
            // Empty here is not a fallback: `verifyReleaseApiBaseUrl` below fails
            // the build before any release artifact can be produced.
            buildConfigField("String", "CHAN_API_BASE_URL", "\"${releaseApiBaseUrl.orEmpty()}\"")
        }
        debug {
            isMinifyEnabled = false
            buildConfigField("String", "CHAN_API_BASE_URL", "\"$debugApiBaseUrl\"")
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions {
        jvmTarget = "17"
    }
    buildFeatures {
        compose = true
        buildConfig = true
    }
    packaging {
        resources {
            excludes += "/META-INF/{AL2.0,LGPL2.1}"
        }
    }
    testOptions {
        unitTests {
            isReturnDefaultValues = true
            all {
                // The privacy static-analysis test reads the module's own sources.
                it.systemProperty("chan.projectDir", projectDir.absolutePath)
            }
        }
    }
}

/**
 * Release safety gate (§A2): a release build must point at an explicit HTTPS
 * URL. Cleartext is permitted only by the debug network security configuration.
 */
val verifyReleaseApiBaseUrl = tasks.register("verifyReleaseApiBaseUrl") {
    doLast {
        val url = releaseApiBaseUrl
        if (url.isNullOrBlank()) {
            throw GradleException(
                "Release build requires -PCHAN_RELEASE_API_BASE_URL=https://<host>/ " +
                    "(no default is provided on purpose).",
            )
        }
        if (!url.startsWith("https://")) {
            throw GradleException("CHAN_RELEASE_API_BASE_URL must start with https:// — got a cleartext URL.")
        }
    }
}

afterEvaluate {
    tasks.named("preReleaseBuild") { dependsOn(verifyReleaseApiBaseUrl) }
}

dependencies {
    val composeBom = platform("androidx.compose:compose-bom:2024.09.03")
    implementation(composeBom)
    androidTestImplementation(composeBom)

    implementation("androidx.core:core-ktx:1.13.1")
    implementation("androidx.activity:activity-compose:1.9.3")
    implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.8.7")
    implementation("androidx.lifecycle:lifecycle-runtime-compose:2.8.7")
    implementation("androidx.lifecycle:lifecycle-viewmodel-compose:2.8.7")

    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.ui:ui-graphics")
    implementation("androidx.compose.ui:ui-tooling-preview")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.material:material-icons-extended")

    implementation("androidx.datastore:datastore-preferences:1.1.1")

    // Sprint 02 networking. No logging interceptor is declared anywhere: a body
    // log would defeat the "never log message content" invariant.
    implementation("com.squareup.retrofit2:retrofit:2.11.0")
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
    implementation("com.jakewharton.retrofit:retrofit2-kotlinx-serialization-converter:1.0.0")
    implementation("org.jetbrains.kotlinx:kotlinx-serialization-json:1.7.3")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.8.1")

    debugImplementation("androidx.compose.ui:ui-tooling")
    debugImplementation("androidx.compose.ui:ui-test-manifest")

    testImplementation("junit:junit:4.13.2")
    testImplementation("org.jetbrains.kotlinx:kotlinx-coroutines-test:1.8.1")
    testImplementation("com.squareup.okhttp3:mockwebserver:4.12.0")

    androidTestImplementation("androidx.test.ext:junit:1.2.1")
    androidTestImplementation("androidx.test.espresso:espresso-core:3.6.1")
    androidTestImplementation("androidx.compose.ui:ui-test-junit4")
    debugImplementation("androidx.compose.ui:ui-test-manifest")
}
