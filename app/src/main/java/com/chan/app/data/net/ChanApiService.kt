package com.chan.app.data.net

import okhttp3.ResponseBody
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.Header
import retrofit2.http.POST
import retrofit2.http.Path
import retrofit2.http.Query

/**
 * The raw Retrofit surface. Authentication and one-shot 401 recovery live in
 * [ChanApi]; this interface only describes the endpoints.
 *
 * `Response<T>` rather than `T` everywhere: a 401 or 429 is an expected
 * outcome to be handled, not an exception to be caught.
 */
interface ChanApiService {

    /** Unauthenticated bootstrap. The token is returned exactly once. */
    @POST("v1/devices/token")
    suspend fun issueDeviceToken(@Body body: DeviceTokenRequestDto): Response<DeviceTokenResponseDto>

    @POST("v1/analyze")
    suspend fun analyze(
        @Header("Authorization") authorization: String,
        @Body body: AnalyzeRequestDto,
    ): Response<AnalyzeResponseDto>

    /** k-anonymity lookup: `prefix` is five lowercase hex characters, nothing more. */
    @GET("v1/lookup/{kind}")
    suspend fun lookup(
        @Header("Authorization") authorization: String,
        @Path("kind") kind: String,
        @Query("prefix") prefix: String,
    ): Response<LookupResponseDto>

    /** Unauthenticated. Returned as a raw body so the ETag matches the bytes. */
    @GET("v1/rules/bundle")
    suspend fun ruleBundle(
        @Header("If-None-Match") ifNoneMatch: String?,
    ): Response<ResponseBody>
}
