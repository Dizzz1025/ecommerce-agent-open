package com.yourteam.ecommerceguider.data.repository

import android.content.ContentResolver
import android.net.Uri
import android.provider.OpenableColumns
import android.util.Log
import com.yourteam.ecommerceguider.BuildConfig
import com.yourteam.ecommerceguider.data.model.BackendNavigationUiModel
import com.yourteam.ecommerceguider.data.model.CartItemRestoreSnapshotUiModel
import com.yourteam.ecommerceguider.data.model.CartItemUiModel
import com.yourteam.ecommerceguider.data.model.CartSnapshotUiModel
import com.yourteam.ecommerceguider.data.model.ChatStreamEvent
import com.yourteam.ecommerceguider.data.model.ProductPresentationUiModel
import com.yourteam.ecommerceguider.data.model.ProductReviewUiModel
import com.yourteam.ecommerceguider.data.model.ProductSkuUiModel
import com.yourteam.ecommerceguider.data.model.ProductUiModel
import com.yourteam.ecommerceguider.data.model.RecommendationSectionUiModel
import com.yourteam.ecommerceguider.data.model.ScenarioBundleItemUiModel
import com.yourteam.ecommerceguider.data.model.ScenarioPlanItemUiModel
import com.yourteam.ecommerceguider.data.model.ScenarioBundleUiModel
import com.yourteam.ecommerceguider.data.model.SpecSelectionOptionUiModel
import com.yourteam.ecommerceguider.data.model.SpecSelectionUiModel
import com.yourteam.ecommerceguider.data.model.SpotlightUiModel
import com.yourteam.ecommerceguider.data.model.asRecommendationTitleOrNull
import com.yourteam.ecommerceguider.data.model.sanitizeRecommendReason
import java.io.BufferedOutputStream
import java.io.File
import java.io.FileInputStream
import java.io.IOException
import java.io.InputStream
import java.io.OutputStream
import java.io.OutputStreamWriter
import java.net.HttpURLConnection
import java.net.URLEncoder
import java.net.URL
import java.nio.charset.StandardCharsets
import java.util.UUID
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flow
import kotlinx.coroutines.flow.flowOn
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONException
import org.json.JSONObject

private const val STREAM_DEBUG_TAG = "RecommendationStream"

object ShoppingSession {
    val sessionId: String by lazy {
        "${BuildConfig.DEFAULT_SESSION_ID}-${UUID.randomUUID().toString().take(8)}"
    }
    var userId: String? = null
}

class ShoppingRepository(
    private val baseUrl: String = BuildConfig.API_BASE_URL.removeSuffix("/"),
    private val sessionId: String = ShoppingSession.sessionId,
    private val userId: String? = ShoppingSession.userId,
) {
    val currentUserId: String?
        get() = userId

    fun streamChat(message: String): Flow<ChatStreamEvent> = flow {
        val payload = JSONObject()
            .put("session_id", sessionId)
            .put("message", message)
            .put("input_type", "text")
        userId?.let { payload.put("user_id", it) }

        val connection = openJsonConnection(path = "/api/chat/stream", method = "POST")

        try {
            writeJson(connection, payload)
            val responseCode = connection.responseCode
            if (responseCode !in 200..299) {
                emit(
                    ChatStreamEvent(
                        event = "error",
                        errorMessage = extractErrorMessage(connection),
                    )
                )
                emit(ChatStreamEvent(event = "done"))
                return@flow
            }

            readSseStream(connection.inputStream) { emit(it) }
        } finally {
            connection.disconnect()
        }
    }.flowOn(Dispatchers.IO)

    fun streamImageChat(
        contentResolver: ContentResolver,
        imageUri: Uri,
        message: String,
    ): Flow<ChatStreamEvent> = flow {
        val boundary = "----EcommerceGuider${UUID.randomUUID()}"
        val connection = openMultipartConnection(
            path = "/api/chat/stream/upload",
            boundary = boundary,
        )

        try {
            BufferedOutputStream(connection.outputStream).use { output ->
                writeMultipartField(output, boundary, "session_id", sessionId)
                userId?.let { writeMultipartField(output, boundary, "user_id", it) }
                writeMultipartField(output, boundary, "input_type", "image_text")
                message.trim().takeIf { it.isNotBlank() }?.let {
                    writeMultipartField(output, boundary, "message", it)
                }

                val mimeType = contentResolver.getType(imageUri) ?: "image/jpeg"
                val fileName = contentResolver.displayName(imageUri) ?: "image_search.jpg"
                writeMultipartFile(
                    output = output,
                    boundary = boundary,
                    fieldName = "image",
                    fileName = fileName.sanitizeMultipartFileName(),
                    mimeType = mimeType,
                ) {
                    contentResolver.openInputStream(imageUri)
                        ?: throw IOException("Unable to read selected image.")
                }
                output.writeUtf8("--$boundary--\r\n")
                output.flush()
            }

            val responseCode = connection.responseCode
            if (responseCode !in 200..299) {
                emit(
                    ChatStreamEvent(
                        event = "error",
                        errorMessage = extractErrorMessage(connection),
                    )
                )
                emit(ChatStreamEvent(event = "done"))
                return@flow
            }

            readSseStream(connection.inputStream) { emit(it) }
        } finally {
            connection.disconnect()
        }
    }.flowOn(Dispatchers.IO)

    suspend fun transcribeVoice(audioFile: File): Result<String> = withContext(Dispatchers.IO) {
        if (!audioFile.exists() || audioFile.length() <= 0L) {
            return@withContext Result.failure(IOException("录音文件为空，请重新录音。"))
        }
        val boundary = "----EcommerceGuiderVoice${UUID.randomUUID()}"
        val connection = openMultipartConnection(
            path = "/api/voice/transcribe",
            boundary = boundary,
            readTimeoutMs = 120_000,
        )

        try {
            BufferedOutputStream(connection.outputStream).use { output ->
                writeMultipartField(output, boundary, "language", "zh")
                writeMultipartFile(
                    output = output,
                    boundary = boundary,
                    fieldName = "audio",
                    fileName = audioFile.name.sanitizeMultipartFileName(),
                    mimeType = audioFile.guessAudioMimeType(),
                ) {
                    FileInputStream(audioFile)
                }
                output.writeUtf8("--$boundary--\r\n")
                output.flush()
            }

            val responseCode = connection.responseCode
            val body = connection.readBodyText()
            if (responseCode !in 200..299) {
                return@withContext Result.failure(IOException(parseApiMessage(body, "语音识别请求失败。")))
            }
            val json = JSONObject(body)
            val text = json.optString("text").trim()
            val ok = json.optNullableBoolean("ok") ?: text.isNotBlank()
            if (ok && text.isNotBlank()) {
                Result.success(text)
            } else {
                Result.failure(IOException(parseApiMessage(body, "没有识别到语音内容，请再试一次。")))
            }
        } catch (error: Exception) {
            Result.failure(error)
        } finally {
            connection.disconnect()
        }
    }

    suspend fun synthesizeVoice(text: String): Result<String> = withContext(Dispatchers.IO) {
        val content = text.trim()
        if (content.isBlank()) {
            return@withContext Result.failure(IOException("待播放文本为空。"))
        }
        val connection = openFormConnection(path = "/api/voice/synthesize", readTimeoutMs = 120_000)
        try {
            writeForm(connection, mapOf("text" to content.take(600)))
            val responseCode = connection.responseCode
            val body = connection.readBodyText()
            if (responseCode !in 200..299) {
                return@withContext Result.failure(IOException(parseApiMessage(body, "语音合成请求失败。")))
            }
            val json = JSONObject(body)
            val url = json.optString("url").trim()
            val ok = json.optNullableBoolean("ok") ?: url.isNotBlank()
            if (ok && url.isNotBlank()) {
                Result.success(absolutizeUrl(url))
            } else {
                Result.failure(IOException(parseApiMessage(body, "语音播放暂不可用。")))
            }
        } catch (error: Exception) {
            Result.failure(error)
        } finally {
            connection.disconnect()
        }
    }

    suspend fun fetchProduct(skuId: String): ProductUiModel? = withContext(Dispatchers.IO) {
        val connection = openJsonConnection(path = "/api/products/$skuId", method = "GET")
        try {
            when (connection.responseCode) {
                HttpURLConnection.HTTP_OK -> {
                    val body = connection.inputStream.readUtf8Text()
                    JSONObject(body).optJSONObject("product")?.toProduct()
                }

                HttpURLConnection.HTTP_NOT_FOUND -> null
                else -> throw IOException(extractErrorMessage(connection))
            }
        } finally {
            connection.disconnect()
        }
    }

    suspend fun getCart(): CartSnapshotUiModel = withContext(Dispatchers.IO) {
        val encodedSessionId = URLEncoder.encode(sessionId, StandardCharsets.UTF_8.name())
        val connection = openJsonConnection(path = "/api/cart?session_id=$encodedSessionId", method = "GET")
        try {
            if (connection.responseCode !in 200..299) {
                throw IOException(extractErrorMessage(connection))
            }
            JSONObject(connection.inputStream.readUtf8Text()).toCartSnapshot()
        } finally {
            connection.disconnect()
        }
    }

    suspend fun addToCart(
        skuId: String,
        quantity: Int = 1,
        selectedSkuId: String? = null,
        selectedSpecs: Map<String, String> = emptyMap(),
        unitPrice: Double? = null,
        productName: String? = null,
        imageUrl: String? = null,
        specSummary: String? = null,
    ): CartSnapshotUiModel = withContext(Dispatchers.IO) {
        val payload = JSONObject()
            .put("session_id", sessionId)
            .put("sku_id", skuId)
            .put("quantity", quantity)
            .put("source", "button")
        selectedSkuId?.takeIf { it.isNotBlank() }?.let { payload.put("selected_sku_id", it) }
        if (selectedSpecs.isNotEmpty()) {
            payload.put("selected_specs", JSONObject(selectedSpecs))
        }
        unitPrice?.let { payload.put("unit_price", it) }
        productName?.takeIf { it.isNotBlank() }?.let { payload.put("product_name", it) }
        imageUrl?.takeIf { it.isNotBlank() }?.let { payload.put("image_url", it) }
        specSummary?.takeIf { it.isNotBlank() }?.let { payload.put("spec_summary", it) }
        val connection = openJsonConnection(path = "/api/cart/add", method = "POST")
        try {
            writeJson(connection, payload)
            if (connection.responseCode !in 200..299) {
                throw IOException(extractErrorMessage(connection))
            }
            JSONObject(connection.inputStream.readUtf8Text()).toCartSnapshot()
        } finally {
            connection.disconnect()
        }
    }

    suspend fun restoreCartItem(snapshot: CartItemRestoreSnapshotUiModel): CartSnapshotUiModel {
        return addToCart(
            skuId = snapshot.skuId,
            quantity = snapshot.quantity,
            selectedSkuId = snapshot.selectedSkuId,
            selectedSpecs = snapshot.selectedSpecs,
            unitPrice = snapshot.price,
            productName = snapshot.name,
            imageUrl = snapshot.imageUrl,
            specSummary = snapshot.specSummary,
        )
    }

    suspend fun updateCartQuantity(
        skuId: String,
        quantity: Int,
        cartItemId: String? = null,
    ): CartSnapshotUiModel = withContext(Dispatchers.IO) {
        val payload = JSONObject()
            .put("session_id", sessionId)
            .put("sku_id", skuId)
            .put("quantity", quantity.coerceAtLeast(1))
        cartItemId?.takeIf { it.isNotBlank() }?.let { payload.put("cart_item_id", it) }
        val connection = openJsonConnection(path = "/api/cart/update", method = "POST")
        try {
            writeJson(connection, payload)
            if (connection.responseCode !in 200..299) {
                throw IOException(extractErrorMessage(connection))
            }
            JSONObject(connection.inputStream.readUtf8Text()).toCartSnapshot()
        } finally {
            connection.disconnect()
        }
    }

    suspend fun removeFromCart(skuId: String, cartItemId: String? = null): CartSnapshotUiModel = withContext(Dispatchers.IO) {
        val payload = JSONObject()
            .put("session_id", sessionId)
            .put("sku_id", skuId)
        cartItemId?.takeIf { it.isNotBlank() }?.let { payload.put("cart_item_id", it) }
        val connection = openJsonConnection(path = "/api/cart/remove", method = "POST")
        try {
            writeJson(connection, payload)
            if (connection.responseCode !in 200..299) {
                throw IOException(extractErrorMessage(connection))
            }
            JSONObject(connection.inputStream.readUtf8Text()).toCartSnapshot()
        } finally {
            connection.disconnect()
        }
    }

    suspend fun clearCart(): CartSnapshotUiModel = withContext(Dispatchers.IO) {
        val payload = JSONObject().put("session_id", sessionId)
        val connection = openJsonConnection(path = "/api/cart/clear", method = "POST")
        try {
            writeJson(connection, payload)
            if (connection.responseCode !in 200..299) {
                throw IOException(extractErrorMessage(connection))
            }
            JSONObject(connection.inputStream.readUtf8Text()).toCartSnapshot()
        } finally {
            connection.disconnect()
        }
    }

    private fun openJsonConnection(path: String, method: String): HttpURLConnection {
        val connection = URL("$baseUrl$path").openConnection() as HttpURLConnection
        connection.requestMethod = method
        connection.connectTimeout = 10_000
        connection.readTimeout = 60_000
        connection.setRequestProperty("Accept", "application/json, text/event-stream")
        connection.setRequestProperty("Content-Type", "application/json; charset=utf-8")
        connection.doInput = true
        if (method != "GET") {
            connection.doOutput = true
        }
        return connection
    }

    private fun openMultipartConnection(
        path: String,
        boundary: String,
        readTimeoutMs: Int = 60_000,
    ): HttpURLConnection {
        val connection = URL("$baseUrl$path").openConnection() as HttpURLConnection
        connection.requestMethod = "POST"
        connection.connectTimeout = 10_000
        connection.readTimeout = readTimeoutMs
        connection.setRequestProperty("Accept", "text/event-stream, application/json")
        connection.setRequestProperty("Content-Type", "multipart/form-data; boundary=$boundary")
        connection.doInput = true
        connection.doOutput = true
        connection.useCaches = false
        connection.setChunkedStreamingMode(0)
        return connection
    }

    private fun openFormConnection(path: String, readTimeoutMs: Int = 60_000): HttpURLConnection {
        val connection = URL("$baseUrl$path").openConnection() as HttpURLConnection
        connection.requestMethod = "POST"
        connection.connectTimeout = 10_000
        connection.readTimeout = readTimeoutMs
        connection.setRequestProperty("Accept", "application/json")
        connection.setRequestProperty("Content-Type", "application/x-www-form-urlencoded; charset=utf-8")
        connection.doInput = true
        connection.doOutput = true
        return connection
    }

    private fun writeJson(connection: HttpURLConnection, payload: JSONObject) {
        OutputStreamWriter(connection.outputStream, StandardCharsets.UTF_8).use { writer ->
            writer.write(payload.toString())
            writer.flush()
        }
    }

    private fun writeForm(connection: HttpURLConnection, fields: Map<String, String>) {
        val payload = fields.entries.joinToString("&") { (key, value) ->
            "${URLEncoder.encode(key, StandardCharsets.UTF_8.name())}=" +
                URLEncoder.encode(value, StandardCharsets.UTF_8.name())
        }
        OutputStreamWriter(connection.outputStream, StandardCharsets.UTF_8).use { writer ->
            writer.write(payload)
            writer.flush()
        }
    }

    private suspend fun readSseStream(
        inputStream: InputStream,
        emitEvent: suspend (ChatStreamEvent) -> Unit,
    ) {
        inputStream.bufferedReader(StandardCharsets.UTF_8).use { reader ->
            var currentEvent = "message"
            val dataLines = mutableListOf<String>()
            var lastRecommendationDeltaAt: Long? = null

            suspend fun flushEvent() {
                if (dataLines.isEmpty()) {
                    currentEvent = "message"
                    return
                }
                val json = try {
                    JSONObject(dataLines.joinToString(separator = "\n"))
                } catch (_: JSONException) {
                    JSONObject()
                }
                json.toChatStreamEvent(currentEvent)?.let { event ->
                    val section = event.recommendationSection
                    if (
                        event.event == "recommendation_section_start" ||
                        event.event == "recommendation_text_done" ||
                        event.event == "product_card"
                    ) {
                        Log.d(
                            STREAM_DEBUG_TAG,
                            "[recommendation_android_parse] event=${event.event} " +
                                "sectionIndex=${section?.sectionIndex} skuId=${section?.skuId} " +
                                "displayTitle='${section?.displayTitle.orEmpty()}' " +
                                "recommendReasonLength=${section?.recommendReason?.length ?: 0}",
                        )
                    }
                    when (event.event) {
                        "recommendation_text_delta" -> {
                            val now = System.currentTimeMillis()
                            val intervalMs = lastRecommendationDeltaAt?.let { now - it }
                            lastRecommendationDeltaAt = now
                            Log.d(
                                STREAM_DEBUG_TAG,
                                "[android_recv_delta] ts=$now sectionIndex=${section?.sectionIndex} " +
                                    "sku=${section?.skuId} len=${section?.text?.length ?: 0} interval_ms=$intervalMs",
                            )
                        }
                        "recommendation_text_done" -> {
                            val now = System.currentTimeMillis()
                            Log.d(
                                STREAM_DEBUG_TAG,
                                "[recommendation_text_done] ts=$now sectionIndex=${section?.sectionIndex} " +
                                    "sku=${section?.skuId} len=${section?.text?.length ?: section?.reason?.length ?: 0}",
                            )
                        }
                    }
                    emitEvent(event)
                }
                currentEvent = "message"
                dataLines.clear()
            }

            while (true) {
                val line = reader.readLine() ?: break
                if (line.isBlank()) {
                    flushEvent()
                    continue
                }
                when {
                    line.startsWith("event: ") -> currentEvent = line.removePrefix("event: ").trim()
                    line.startsWith("data: ") -> dataLines += line.removePrefix("data: ").trim()
                }
            }

            flushEvent()
        }
    }

    private fun JSONObject.toChatStreamEvent(eventName: String): ChatStreamEvent? {
        return when (eventName) {
            "token" -> {
                val text = optString("text").ifBlank { optString("content") }
                ChatStreamEvent(event = "token", text = text)
            }

            "generation_started" -> {
                ChatStreamEvent(
                    event = "generation_started",
                    requestId = optNullableString("request_id"),
                    sequence = optNullableLong("sequence"),
                    progressStageId = optString("stage_key").ifBlank { optString("stage_id") },
                    progressDisplayLabel = optNullableString("display_label")
                        ?: optNullableString("user_facing_label"),
                    progressText = optString("message").ifBlank { optString("text") },
                    totalDurationMs = optNullableLong("elapsed_ms"),
                    responseStreamSupported = optNullableBoolean("stream_supported"),
                )
            }

            "response_delta" -> {
                ChatStreamEvent(
                    event = "response_delta",
                    text = optString("delta")
                        .ifBlank { optString("text") }
                        .ifBlank { optString("content") },
                    totalDurationMs = optNullableLong("elapsed_ms"),
                    responseStreamSupported = optNullableBoolean("stream_supported"),
                )
            }

            "response_completed" -> {
                ChatStreamEvent(
                    event = "response_completed",
                    requestId = optNullableString("request_id"),
                    sequence = optNullableLong("sequence"),
                    text = optString("text").ifBlank { optString("content") },
                    progressStageId = optString("stage_key").ifBlank { optString("stage_id") },
                    progressDisplayLabel = optNullableString("display_label")
                        ?: optNullableString("user_facing_label"),
                    totalDurationMs = optNullableLong("total_duration_ms"),
                    responseStreamSupported = optNullableBoolean("stream_supported"),
                )
            }

            "product_cards" -> {
                ChatStreamEvent(
                    event = "product_cards",
                    products = optJSONArray("products").toProducts(),
                )
            }

            "product_card" -> {
                val product = optJSONObject("product")?.toProduct()?.withPlanFieldsFrom(this)
                val isScenarioBundleProduct = optString("recommendation_type") == "scenario_bundle" ||
                    optNullableString("plan_role") != null ||
                    optNullableString("scheme_role") != null ||
                    product?.isScenarioBundleProduct == true
                ChatStreamEvent(
                    event = "product_card",
                    product = product,
                    recommendationSection = if (isScenarioBundleProduct) {
                        null
                    } else {
                        toRecommendationSection(text = null, product = product)
                    },
                )
            }

            "recommendation_section_start" -> {
                ChatStreamEvent(
                    event = eventName,
                    recommendationSection = toRecommendationSection(),
                )
            }

            "recommendation_text_delta" -> {
                ChatStreamEvent(
                    event = "recommendation_text_delta",
                    recommendationSection = toRecommendationSection(text = optNullableString("delta")),
                )
            }

            "recommendation_text_done" -> {
                ChatStreamEvent(
                    event = "recommendation_text_done",
                    recommendationSection = toRecommendationSection(
                        text = optNullableString("reason"),
                        done = true,
                    ),
                )
            }

            "recommendation_section_done" -> {
                ChatStreamEvent(
                    event = "recommendation_section_done",
                    recommendationSection = toRecommendationSection(done = true),
                )
            }

            "generation_degraded" -> {
                ChatStreamEvent(
                    event = "generation_degraded",
                    requestId = optNullableString("request_id"),
                    sequence = optNullableLong("sequence"),
                    errorMessage = optNullableString("message") ?: optNullableString("reason"),
                )
            }

            "products", "alternatives" -> {
                ChatStreamEvent(
                    event = eventName,
                    products = optJSONArray("products").toProducts(),
                )
            }

            "plan_overview_start", "plan_overview", "plan_overview_done" -> {
                val bundle = toScenarioBundle()
                ChatStreamEvent(
                    event = eventName,
                    scenarioBundle = bundle,
                )
            }

            "scenario_bundle" -> {
                val bundle = toScenarioBundle()
                ChatStreamEvent(
                    event = "scenario_bundle",
                    products = bundle?.items.orEmpty().map { it.product },
                    scenarioBundle = bundle,
                )
            }

            "product_detail" -> {
                ChatStreamEvent(
                    event = "product_detail",
                    product = optJSONObject("product")?.toProduct(),
                )
            }

            "cart_update" -> {
                ChatStreamEvent(event = "cart_update", cart = toCartSnapshot())
            }

            "cart" -> {
                ChatStreamEvent(event = "cart", cart = optJSONObject("cart")?.toCartSnapshot())
            }

            "progress", "process" -> {
                val text = optString("text")
                    .ifBlank { optString("stage") }
                    .ifBlank { optString("stage_key") }
                ChatStreamEvent(
                    event = eventName,
                    progressText = text.takeIf { it.isNotBlank() },
                    progressStageId = optString("stage_key").ifBlank { optString("stage_id") },
                    progressDisplayLabel = optNullableString("user_facing_label")
                        ?: optNullableString("display_label"),
                    progressSummary = optNullableString("summary") ?: text.takeIf { it.isNotBlank() },
                    totalDurationMs = optNullableLong("total_duration_ms"),
                )
            }

            "frontend_action" -> {
                ChatStreamEvent(
                    event = "frontend_action",
                    navigation = toNavigation(product = null),
                )
            }

            "spec_selection" -> {
                ChatStreamEvent(
                    event = "spec_selection",
                    specSelection = toSpecSelection(),
                )
            }

            "turn_result" -> toTurnResultEvent()

            "error" -> {
                ChatStreamEvent(
                    event = "error",
                    errorMessage = optString("message").ifBlank {
                        "Request failed. Please try again."
                    },
                )
            }

            "done" -> ChatStreamEvent(event = "done")
            else -> null
        }
    }

    internal fun parseChatStreamEventForTest(eventName: String, payload: JSONObject): ChatStreamEvent? {
        return payload.toChatStreamEvent(eventName)
    }

    private fun writeMultipartField(
        output: OutputStream,
        boundary: String,
        name: String,
        value: String,
    ) {
        output.writeUtf8("--$boundary\r\n")
        output.writeUtf8("Content-Disposition: form-data; name=\"$name\"\r\n")
        output.writeUtf8("\r\n")
        output.writeUtf8(value)
        output.writeUtf8("\r\n")
    }

    private fun writeMultipartFile(
        output: OutputStream,
        boundary: String,
        fieldName: String,
        fileName: String,
        mimeType: String,
        inputStreamProvider: () -> InputStream,
    ) {
        output.writeUtf8("--$boundary\r\n")
        output.writeUtf8("Content-Disposition: form-data; name=\"$fieldName\"; filename=\"$fileName\"\r\n")
        output.writeUtf8("Content-Type: $mimeType\r\n")
        output.writeUtf8("\r\n")
        inputStreamProvider().use { input ->
            input.copyTo(output)
        }
        output.writeUtf8("\r\n")
    }

    private fun OutputStream.writeUtf8(value: String) {
        write(value.toByteArray(StandardCharsets.UTF_8))
    }

    private fun JSONObject.toTurnResultEvent(): ChatStreamEvent {
        val frontendData = optJSONObject("frontend_data") ?: JSONObject()
        val productDetail = frontendData
            .optJSONObject("product_detail")
            ?.optJSONObject("product")
            ?.toProduct()
        val recommendedProducts = frontendData
            .optJSONObject("recommended_products")
            ?.optJSONArray("products")
            .toProducts()
        val alternativeProducts = frontendData
            .optJSONObject("alternative_products")
            ?.optJSONArray("products")
            .toProducts()
        val navigation = frontendData.optJSONObject("navigation").toNavigation(productDetail)
        val cart = frontendData
            .optJSONObject("cart_state")
            ?.optJSONObject("cart")
            ?.toCartSnapshot()
        val specSelection = frontendData
            .optJSONObject("spec_selection")
            ?.toSpecSelection()
        val scenarioBundle = frontendData
            .optJSONObject("scenario_bundle")
            ?.toScenarioBundle()
        val scenarioBundleProducts = scenarioBundle?.items.orEmpty().map { it.product }

        return ChatStreamEvent(
            event = "turn_result",
            text = frontendData
                .optJSONObject("reply_message")
                ?.optString("text")
                ?.takeIf { it.isNotBlank() },
            products = when {
                scenarioBundleProducts.isNotEmpty() -> scenarioBundleProducts
                recommendedProducts.isNotEmpty() -> recommendedProducts
                alternativeProducts.isNotEmpty() -> alternativeProducts
                else -> emptyList()
            },
            cart = cart,
            navigation = navigation,
            product = productDetail,
            scenarioBundle = scenarioBundle,
            specSelection = specSelection,
            errorMessage = frontendData.optJSONObject("error_message")?.optString("message"),
        )
    }

    private fun JSONObject.toScenarioBundle(): ScenarioBundleUiModel? {
        val container = optJSONObject("bundle") ?: this
        val items = container.optJSONArray("items").toScenarioBundleItems()
        val planItems = container.optJSONArray("plan_items").toScenarioPlanItems().ifEmpty {
            items.map { item ->
                ScenarioPlanItemUiModel(
                    roleName = item.roleName,
                    categoryName = item.categoryName,
                    skuId = item.skuId,
                    planRole = item.planRole,
                )
            }
        }
        val title = (container.optNullableString("plan_title")
            ?: container.optNullableString("planTitle")
            ?: container.optNullableString("title")
            ?: "").trim()
        val summary = (container.optNullableString("plan_summary")
            ?: container.optNullableString("planSummary")
            ?: container.optNullableString("summary")
            ?: "").trim()
        if (title.isBlank() && summary.isBlank() && items.isEmpty() && planItems.isEmpty()) {
            return null
        }
        return ScenarioBundleUiModel(
            turnId = optString("turn_id")
                .ifBlank { optString("turnId") }
                .ifBlank { container.optString("turn_id") }
                .ifBlank { container.optString("turnId") }
                .ifBlank { "turn_current" },
            title = title,
            summary = summary,
            planItems = planItems,
            items = items,
        )
    }

    private fun JSONArray?.toScenarioPlanItems(): List<ScenarioPlanItemUiModel> {
        if (this == null) {
            return emptyList()
        }
        return buildList(length()) {
            for (index in 0 until length()) {
                val item = optJSONObject(index) ?: continue
                val roleName = item.optNullableString("role_name")
                    ?: item.optNullableString("roleName")
                    ?: item.optNullableString("role")
                    ?: continue
                val categoryName = item.optNullableString("category_name")
                    ?: item.optNullableString("categoryName")
                    ?: item.optNullableString("category")
                    ?: ""
                add(
                    ScenarioPlanItemUiModel(
                        roleName = roleName,
                        categoryName = categoryName,
                        skuId = item.optNullableString("sku_id") ?: item.optNullableString("skuId"),
                        planRole = item.optNullableString("plan_role")
                            ?: item.optNullableString("planRole")
                            ?: item.optNullableString("short_reason")
                            ?: "",
                    )
                )
            }
        }
    }

    private fun JSONArray?.toScenarioBundleItems(): List<ScenarioBundleItemUiModel> {
        if (this == null) {
            return emptyList()
        }
        return buildList(length()) {
            for (index in 0 until length()) {
                val item = optJSONObject(index) ?: continue
                val roleName = item.optNullableString("role_name")
                    ?: item.optNullableString("roleName")
                    ?: item.optNullableString("role")
                val categoryName = item.optNullableString("category_name")
                    ?: item.optNullableString("categoryName")
                val product = item.optJSONObject("product")
                    ?.toProduct()
                    ?.withPlanFieldsFrom(item)
                    ?: continue
                val shortReason = item.optNullableString("short_reason")
                    ?: item.optNullableString("shortReason")
                    ?: item.optNullableString("plan_role")
                    ?: item.optNullableString("planRole")
                    ?: product.presentation?.bundleReason
                    ?: product.displayPlanRole.takeIf { it.isNotBlank() }
                    ?: product.recommendReason
                    ?: product.reason
                    ?: ""
                val resolvedRole = roleName
                    ?: product.displayPlanRoleName.takeIf { it.isNotBlank() }
                    ?: product.presentation?.bundleRole
                    ?: product.subCategory
                    ?: product.category
                add(
                    ScenarioBundleItemUiModel(
                        role = resolvedRole,
                        shortReason = shortReason,
                        product = product.withResolvedPlanRole(
                            planRole = shortReason,
                            roleName = resolvedRole,
                            categoryName = categoryName,
                        ),
                        roleName = resolvedRole,
                        categoryName = categoryName
                            ?: product.displayPlanCategoryName,
                        skuId = item.optNullableString("sku_id")
                            ?: item.optNullableString("skuId")
                            ?: product.skuId,
                        planRole = shortReason,
                    )
                )
            }
        }
    }

    private fun JSONObject.toSpecSelection(): SpecSelectionUiModel? {
        val productId = optString("product_id").ifBlank { optString("productId") }
        val productName = optString("product_name").ifBlank { optString("productName") }
        val options = (optJSONArray("sku_options") ?: optJSONArray("skuOptions")).toSpecOptions(productId)
        if (productId.isBlank() || productName.isBlank() || options.isEmpty()) {
            return null
        }
        val id = optString("id").ifBlank { "spec-$productId" }
        return SpecSelectionUiModel(
            id = id,
            turnId = optString("turn_id").ifBlank { optString("turnId") }.ifBlank { "turn_current" },
            productId = productId,
            productName = productName,
            imageUrl = absolutizeUrl(optString("image_url").ifBlank { optString("imageUrl") }),
            quantity = optInt("quantity", 1).coerceAtLeast(1),
            options = options,
            selectedSkuId = optNullableString("selected_sku_id") ?: optNullableString("selectedSkuId"),
        )
    }

    private fun JSONArray?.toSpecOptions(productId: String): List<SpecSelectionOptionUiModel> {
        if (this == null) {
            return emptyList()
        }
        return buildList(length()) {
            for (index in 0 until length()) {
                val option = optJSONObject(index) ?: continue
                val skuId = option.optString("sku_id").ifBlank { option.optString("skuId") }
                val specs = option.optJSONObject("selected_specs").toStringMap()
                    .ifEmpty { option.optJSONObject("selectedSpecs").toStringMap() }
                val specText = option.optString("spec_text")
                    .ifBlank { option.optString("specText") }
                    .ifBlank { option.optJSONObject("selected_specs").toSpecSummary().orEmpty() }
                    .ifBlank { option.optJSONObject("selectedSpecs").toSpecSummary().orEmpty() }
                if (skuId.isBlank() || specText.isBlank()) {
                    continue
                }
                val stock = option.optNullableInt("stock")
                add(
                    SpecSelectionOptionUiModel(
                        productId = option.optString("product_id")
                            .ifBlank { option.optString("productId") }
                            .ifBlank { productId },
                        skuId = skuId,
                        specText = specText,
                        selectedSpecs = specs,
                        price = option.optNumber("price"),
                        stock = stock,
                        available = option.optNullableBoolean("available") ?: (stock == null || stock > 0),
                    )
                )
            }
        }
    }

    private fun JSONObject?.toNavigation(product: ProductUiModel?): BackendNavigationUiModel? {
        if (this == null) {
            return null
        }
        val targetPage = optString("target_page").ifBlank { optString("targetPage") }
            .ifBlank { optString("target_page", "") }
        val normalizedTargetPage = when (targetPage) {
            "product_detail" -> "product_detail_page"
            "cart" -> "cart_page"
            "checkout" -> "checkout_page"
            else -> targetPage
        }
        if (targetPage.isBlank()) {
            return null
        }
        val params = optJSONObject("params")
            ?: optJSONObject("payload")
        val skuId = params?.optString("sku_id").takeUnless { it.isNullOrBlank() }
            ?: params?.optJSONArray("product_ids")?.optStringOrNull(0)
            ?: optString("sku_id").takeIf { it.isNotBlank() }
            ?: product?.skuId

        return BackendNavigationUiModel(
            targetPage = normalizedTargetPage,
            skuId = skuId,
        )
    }

    private fun JSONArray?.toProducts(): List<ProductUiModel> {
        if (this == null) {
            return emptyList()
        }
        return buildList(length()) {
            for (index in 0 until length()) {
                optJSONObject(index)?.toProduct()?.let(::add)
            }
        }
    }

    private fun JSONObject.toProduct(): ProductUiModel {
        val imageUrl = absolutizeUrl(optString("image_url").ifBlank { optString("imageUrl") })
        val detailImageUrl = (optNullableString("detail_image_url") ?: optNullableString("detailImageUrl"))
            ?.let(::absolutizeUrl)
            ?.takeIf { it.isNotBlank() }
        val recommendationDisplayTitle = optNullableString("display_title")
            ?: optNullableString("displayTitle")
        val explicitRecommendTitle = optNullableString("recommend_title")
            ?: optNullableString("recommendTitle")
            ?: recommendationDisplayTitle
        val rawRecommendReason = optNullableString("recommend_reason")
            ?: optNullableString("recommendReason")
            ?: optNullableString("reason")
        val recommendReason = rawRecommendReason.sanitizeRecommendReason().takeIf { it.isNotBlank() }
        return ProductUiModel(
            skuId = optString("sku_id"),
            productId = optNullableString("product_id"),
            name = optString("name").ifBlank { optString("title") },
            title = optNullableString("title"),
            shortTitle = optNullableString("short_title") ?: optNullableString("shortTitle"),
            recommendationDisplayTitle = recommendationDisplayTitle,
            category = optString("category"),
            brand = optString("brand"),
            price = optNumber("price"),
            basePrice = optNullableNumber("base_price"),
            stock = optInt("stock"),
            imageUrl = imageUrl,
            detailImageUrl = detailImageUrl,
            imagePath = optNullableString("image_path"),
            subCategory = optNullableString("sub_category"),
            reason = recommendReason ?: optNullableString("highlight_short"),
            recommendTitle = explicitRecommendTitle?.takeIf { it.isNotBlank() },
            recommendReason = recommendReason?.takeIf { it.isNotBlank() },
            planRole = optNullableString("plan_role") ?: optNullableString("planRole"),
            schemeRole = optNullableString("scheme_role") ?: optNullableString("schemeRole"),
            planRoleName = optNullableString("plan_role_name")
                ?: optNullableString("planRoleName")
                ?: optNullableString("role_name")
                ?: optNullableString("roleName"),
            planCategoryName = optNullableString("plan_category_name")
                ?: optNullableString("planCategoryName")
                ?: optNullableString("category_name")
                ?: optNullableString("categoryName"),
            highlightShort = optString("highlight_short"),
            highlightDetail = optString("highlight_detail"),
            productHighlight = optString("product_highlight"),
            reviewsSummary = optString("reviews_summary"),
            suitableScenarios = optJSONArray("suitable_scenarios").toStringList(),
            targetUserTags = optJSONArray("target_user_tags").toStringList(),
            nonStandardQueryTags = optJSONArray("non_standard_query_tags").toStringList(),
            tags = optJSONArray("tags").toStringList(),
            matchedReasons = optJSONArray("matched_reasons").toStringList(),
            skus = optJSONArray("skus").toSkus(),
            reviews = optJSONObject("rag_knowledge").toReviews(),
            ragKnowledge = optJSONObject("rag_knowledge").toStringMap(),
            score = optNullableNumber("score"),
            spotlight = optJSONObject("spotlight").toSpotlight(),
            presentation = optJSONObject("presentation").toPresentation(),
        )
    }

    private fun JSONObject?.toPresentation(): ProductPresentationUiModel? {
        if (this == null) {
            return null
        }
        val type = optString("type")
        if (type.isBlank()) {
            return null
        }
        return ProductPresentationUiModel(
            type = type,
            title = optNullableString("title")
                ?: optNullableString("display_title")
                ?: optNullableString("displayTitle"),
            shortTitle = optNullableString("short_title") ?: optNullableString("shortTitle"),
            optionLabel = optNullableString("option_label"),
            reason = optNullableString("reason"),
            tradeOff = optNullableString("trade_off"),
            status = optString("status").ifBlank { "complete" },
            summary = optNullableString("summary"),
            advantages = optJSONArray("advantages").toStringList(),
            suitableFor = optNullableString("suitable_for"),
            keyFeatures = optJSONArray("key_features").toStringList(),
            matchedNeed = optNullableString("matched_need"),
            usageAdvice = optNullableString("usage_advice"),
            bundleRole = optNullableString("bundle_role"),
            bundleReason = optNullableString("bundle_reason"),
            planRole = optNullableString("plan_role") ?: optNullableString("planRole"),
            schemeRole = optNullableString("scheme_role") ?: optNullableString("schemeRole"),
            usageScenario = optNullableString("usage_scenario"),
            contentSource = optString("content_source"),
        )
    }

    private fun ProductUiModel.withPlanFieldsFrom(source: JSONObject): ProductUiModel {
        return withResolvedPlanRole(
            planRole = source.optNullableString("plan_role")
                ?: source.optNullableString("planRole")
                ?: source.optNullableString("scheme_role")
                ?: source.optNullableString("schemeRole"),
            roleName = source.optNullableString("role_name")
                ?: source.optNullableString("roleName")
                ?: source.optNullableString("role"),
            categoryName = source.optNullableString("category_name")
                ?: source.optNullableString("categoryName"),
        )
    }

    private fun ProductUiModel.withResolvedPlanRole(
        planRole: String?,
        roleName: String?,
        categoryName: String?,
    ): ProductUiModel {
        return copy(
            planRole = this.planRole ?: planRole?.takeIf { it.isNotBlank() },
            schemeRole = this.schemeRole ?: planRole?.takeIf { it.isNotBlank() },
            planRoleName = this.planRoleName ?: roleName?.takeIf { it.isNotBlank() },
            planCategoryName = this.planCategoryName ?: categoryName?.takeIf { it.isNotBlank() },
        )
    }

    private fun JSONObject.toRecommendationSection(
        text: String? = null,
        product: ProductUiModel? = null,
        done: Boolean = false,
    ): RecommendationSectionUiModel? {
        val resolvedProduct = product ?: optJSONObject("product")?.toProduct()
        val skuId = optString("sku_id").ifBlank {
            resolvedProduct?.skuId ?: optJSONObject("product")?.optString("sku_id").orEmpty()
        }
        if (skuId.isBlank()) {
            return null
        }
        val sectionIndex = if (has("section_index")) optInt("section_index") else 1
        val turnId = optNullableString("turn_id") ?: "turn_current"
        val optionLabel = optNullableString("option_label").orEmpty()
        val rawRecommendReason = optNullableString("recommend_reason")
            ?: optNullableString("recommendReason")
            ?: optNullableString("reason")
            ?: resolvedProduct?.reason
        val recommendReason = rawRecommendReason.sanitizeRecommendReason()
        return RecommendationSectionUiModel(
            eventId = optNullableString("event_id"),
            requestId = optNullableString("request_id"),
            sequence = optNullableLong("sequence"),
            turnId = turnId,
            sectionIndex = sectionIndex,
            skuId = skuId,
            optionLabel = optionLabel,
            displayTitle = resolveRecommendationDisplayTitle(resolvedProduct),
            text = text.orEmpty(),
            recommendReason = recommendReason,
            reason = rawRecommendReason,
            tradeOff = optNullableString("trade_off"),
            recommendationTags = resolvedProduct?.recommendationTags.orEmpty(),
            productName = optNullableString("product_name") ?: resolvedProduct?.displayTitleShort,
            brand = optNullableString("brand") ?: resolvedProduct?.brand,
            product = resolvedProduct,
            done = done,
        )
    }

    private fun JSONObject.resolveRecommendationDisplayTitle(
        product: ProductUiModel?,
    ): String {
        val presentationJson = optJSONObject("presentation")
        val candidates = listOf(
            optNullableString("display_title"),
            optNullableString("displayTitle"),
            optNullableString("section_title"),
            optNullableString("sectionTitle"),
            optNullableString("recommendation_title"),
            optNullableString("recommendationTitle"),
            optNullableString("recommend_title"),
            optNullableString("recommendTitle"),
            presentationJson?.optNullableString("title"),
            presentationJson?.optNullableString("display_title"),
            presentationJson?.optNullableString("displayTitle"),
            presentationJson?.optNullableString("short_title"),
            presentationJson?.optNullableString("shortTitle"),
            product?.recommendationDisplayTitle,
            product?.recommendTitle,
            product?.presentation?.title,
            product?.presentation?.shortTitle,
        )
        return candidates.firstNotNullOfOrNull { it.cleanRecommendationTitle(product) }.orEmpty()
    }

    private fun String?.cleanRecommendationTitle(product: ProductUiModel?): String? {
        val value = asRecommendationTitleOrNull() ?: return null
        if (product != null && value == product.displayTitle && value.length > 18) {
            return null
        }
        return value
    }

    private fun String.isMechanicalRecommendationTitle(): Boolean {
        val normalized = trim().replace(" ", "")
        return normalized.matches(Regex("""^方案[一二三四五六七八九十\d]+$""")) ||
            normalized.matches(Regex("""^推荐[一二三四五六七八九十\d]+$""")) ||
            normalized.matches(Regex("""^第[一二三四五六七八九十\d]+个?推荐$""")) ||
            normalized == "首选方案" ||
            normalized == "备选方案"
    }

    private fun JSONArray?.toSkus(): List<ProductSkuUiModel> {
        if (this == null) {
            return emptyList()
        }
        return buildList(length()) {
            for (index in 0 until length()) {
                val sku = optJSONObject(index) ?: continue
                add(
                    ProductSkuUiModel(
                        skuId = sku.optString("sku_id"),
                        properties = sku.optJSONObject("properties").toStringMap(),
                        price = sku.optNumber("price"),
                    )
                )
            }
        }
    }

    private fun JSONObject?.toSpotlight(): SpotlightUiModel {
        if (this == null) {
            return SpotlightUiModel()
        }
        return SpotlightUiModel(
            skinType = optJSONArray("skin_type").toStringList(),
            features = optJSONArray("features").toStringList(),
            exclude = optJSONArray("exclude").toStringList(),
            description = optString("description"),
        )
    }

    private fun JSONObject.toCartSnapshot(): CartSnapshotUiModel {
        val items = optJSONArray("items").toCartItems()
        val totalItems = optInt("total_items", items.sumOf { it.quantity })
        return CartSnapshotUiModel(
            items = items,
            totalPrice = optNumber("total_price"),
            totalItems = totalItems,
        )
    }

    private fun JSONArray?.toCartItems(): List<CartItemUiModel> {
        if (this == null) {
            return emptyList()
        }
        return buildList(length()) {
            for (index in 0 until length()) {
                val item = optJSONObject(index) ?: continue
                add(
                    CartItemUiModel(
                        cartItemId = item.optString("cart_item_id")
                            .ifBlank { item.optString("item_id") }
                            .ifBlank { item.optString("sku_id") },
                        skuId = item.optString("sku_id"),
                        selectedSkuId = item.optNullableString("selected_sku_id"),
                        selectedSpecs = item.optJSONObject("selected_specs").toStringMap(),
                        name = item.optString("name"),
                        price = item.optNumber("price"),
                        originalPrice = item.optNullableNumber("original_price")
                            ?: item.optNullableNumber("base_price")
                            ?: item.optNullableNumber("originalPrice")
                            ?: item.optNullableNumber("basePrice"),
                        quantity = item.optInt("quantity"),
                        imageUrl = absolutizeUrl(item.optString("image_url")),
                        specSummary = item.optNullableString("spec_summary")
                            ?: item.optNullableString("selected_spec")
                            ?: item.optNullableString("spec")
                            ?: item.optJSONObject("selected_specs").toSpecSummary()
                            ?: item.optJSONObject("properties").toSpecSummary(),
                        stock = item.optNullableInt("stock"),
                    )
                )
            }
        }
    }

    private fun JSONObject?.toReviews(): List<ProductReviewUiModel> {
        val reviews = this?.optJSONArray("user_reviews") ?: return emptyList()
        return buildList(reviews.length()) {
            for (index in 0 until reviews.length()) {
                val review = reviews.optJSONObject(index) ?: continue
                val content = review.optString("content").trim()
                if (content.isBlank()) {
                    continue
                }
                add(
                    ProductReviewUiModel(
                        rating = review.optNullableNumber("rating")?.coerceIn(0.0, 5.0),
                        nickname = review.optNullableString("nickname")
                            ?: review.optNullableString("user_name")
                            ?: review.optNullableString("userName"),
                        createdAt = review.optNullableString("created_at")
                            ?: review.optNullableString("createdAt")
                            ?: review.optNullableString("date")
                            ?: review.optNullableString("time"),
                        userTags = review.optJSONArray("user_tags").toStringList()
                            .ifEmpty { review.optJSONArray("userTags").toStringList() }
                            .ifEmpty { review.optJSONArray("tags").toStringList() }
                            .ifEmpty { review.optNullableString("skin_type")?.let(::listOf).orEmpty() },
                        purchased = review.optNullableBoolean("purchased")
                            ?: review.optNullableBoolean("is_purchased")
                            ?: review.optNullableBoolean("verified_purchase"),
                        content = content,
                    )
                )
            }
        }
    }

    private fun JSONArray?.toStringList(): List<String> {
        if (this == null) {
            return emptyList()
        }
        return buildList(length()) {
            for (index in 0 until length()) {
                val value = optString(index)
                if (value.isNotBlank()) {
                    add(value)
                }
            }
        }
    }

    private fun JSONObject.optNullableString(key: String): String? {
        val value = optString(key)
        return value.takeIf { it.isNotBlank() && !it.equals("null", ignoreCase = true) }
    }

    private fun JSONObject.optNumber(key: String): Double {
        return when (val value = opt(key)) {
            is Number -> value.toDouble()
            is String -> value.toDoubleOrNull() ?: 0.0
            else -> 0.0
        }
    }

    private fun JSONObject.optNullableNumber(key: String): Double? {
        if (!has(key) || isNull(key)) {
            return null
        }
        return when (val value = opt(key)) {
            is Number -> value.toDouble()
            is String -> value.toDoubleOrNull()
            else -> null
        }
    }

    private fun JSONObject.optNullableInt(key: String): Int? {
        if (!has(key) || isNull(key)) {
            return null
        }
        return when (val value = opt(key)) {
            is Number -> value.toInt()
            is String -> value.toIntOrNull()
            else -> null
        }
    }

    private fun JSONObject.optNullableLong(key: String): Long? {
        if (!has(key) || isNull(key)) {
            return null
        }
        return when (val value = opt(key)) {
            is Number -> value.toLong()
            is String -> value.toDoubleOrNull()?.toLong()
            else -> null
        }
    }

    private fun JSONObject.optNullableBoolean(key: String): Boolean? {
        if (!has(key) || isNull(key)) {
            return null
        }
        return when (val value = opt(key)) {
            is Boolean -> value
            is Number -> value.toInt() != 0
            is String -> when (value.trim().lowercase()) {
                "true", "1", "yes", "y", "已购", "verified" -> true
                "false", "0", "no", "n" -> false
                else -> null
            }
            else -> null
        }
    }

    private fun JSONObject?.toStringMap(): Map<String, String> {
        if (this == null) {
            return emptyMap()
        }
        return buildMap {
            val iterator = keys()
            while (iterator.hasNext()) {
                val key = iterator.next()
                val value = opt(key)
                if (value != null && value != JSONObject.NULL) {
                    put(key, value.toString())
                }
            }
        }
    }

    private fun JSONObject?.toSpecSummary(): String? {
        if (this == null) {
            return null
        }
        val values = toStringMap()
            .entries
            .sortedBy { it.key }
            .map { it.value }
            .map { it.trim() }
            .filter { it.isNotBlank() }
            .distinct()
        return values.joinToString(" / ").takeIf { it.isNotBlank() }
    }

    private fun JSONArray.optStringOrNull(index: Int): String? {
        if (index < 0 || index >= length()) {
            return null
        }
        return optString(index).takeIf { it.isNotBlank() }
    }

    private fun InputStream.readUtf8Text(): String {
        return bufferedReader(StandardCharsets.UTF_8).use { reader ->
            reader.readText()
        }
    }

    private fun HttpURLConnection.readBodyText(): String {
        val stream = if (responseCode in 200..299) {
            inputStream
        } else {
            errorStream ?: runCatching { inputStream }.getOrNull()
        }
        return runCatching { stream?.readUtf8Text().orEmpty() }.getOrDefault("")
    }

    private fun ContentResolver.displayName(uri: Uri): String? {
        return query(uri, arrayOf(OpenableColumns.DISPLAY_NAME), null, null, null)
            ?.use { cursor ->
                val nameIndex = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME)
                if (cursor.moveToFirst() && nameIndex >= 0) {
                    cursor.getString(nameIndex)
                } else {
                    null
                }
            }
    }

    private fun String.sanitizeMultipartFileName(): String {
        return replace("\"", "")
            .replace("\r", "")
            .replace("\n", "")
            .ifBlank { "image_search.jpg" }
    }

    private fun File.guessAudioMimeType(): String {
        return when (extension.lowercase()) {
            "m4a" -> "audio/mp4"
            "aac" -> "audio/aac"
            "mp3" -> "audio/mpeg"
            "wav" -> "audio/wav"
            "ogg" -> "audio/ogg"
            "webm" -> "audio/webm"
            else -> "audio/mp4"
        }
    }

    private fun extractErrorMessage(connection: HttpURLConnection): String {
        val stream = connection.errorStream ?: runCatching { connection.inputStream }.getOrNull()
        val body = runCatching { stream?.readUtf8Text().orEmpty() }.getOrDefault("")
        if (body.isBlank()) {
            return "Request failed. Please try again."
        }
        return runCatching {
            JSONObject(body).optString("detail").ifBlank {
                JSONObject(body).optString("message")
            }.ifBlank {
                body
            }
        }.getOrDefault(body)
    }

    private fun parseApiMessage(body: String, fallback: String): String {
        if (body.isBlank()) {
            return fallback
        }
        return runCatching {
            val json = JSONObject(body)
            json.optString("message")
                .ifBlank { json.optString("detail") }
                .ifBlank { fallback }
        }.getOrDefault(body.ifBlank { fallback })
    }

    private fun absolutizeUrl(raw: String): String {
        if (raw.isBlank()) {
            return raw
        }
        return when {
            raw.startsWith("http://") || raw.startsWith("https://") -> raw
            raw.startsWith("/") -> "$baseUrl$raw"
            else -> "$baseUrl/$raw"
        }
    }
}
