package com.yourteam.ecommerceguider.viewmodel

import android.content.ContentResolver
import android.media.MediaPlayer
import android.media.MediaRecorder
import android.net.Uri
import android.os.SystemClock
import android.util.Log
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.yourteam.ecommerceguider.data.model.AssistantProcessStageStatus
import com.yourteam.ecommerceguider.data.model.AssistantProcessStageUiModel
import com.yourteam.ecommerceguider.data.model.AssistantThinkingStatus
import com.yourteam.ecommerceguider.data.model.AssistantThinkingUiModel
import com.yourteam.ecommerceguider.data.model.BackendNavigationUiModel
import com.yourteam.ecommerceguider.data.model.ChatMessageUiModel
import com.yourteam.ecommerceguider.data.model.ChatStreamEvent
import com.yourteam.ecommerceguider.data.model.ProductUiModel
import com.yourteam.ecommerceguider.data.model.RecommendationSectionUiModel
import com.yourteam.ecommerceguider.data.model.ScenarioBundleItemUiModel
import com.yourteam.ecommerceguider.data.model.ScenarioBundleUiModel
import com.yourteam.ecommerceguider.data.model.ScenarioPlanItemUiModel
import com.yourteam.ecommerceguider.data.model.SpecSelectionOptionUiModel
import com.yourteam.ecommerceguider.data.model.SpecSelectionUiModel
import com.yourteam.ecommerceguider.data.model.TtsPlaybackState
import com.yourteam.ecommerceguider.data.model.VoiceInputState
import com.yourteam.ecommerceguider.data.model.asRecommendationTitleOrNull
import com.yourteam.ecommerceguider.data.model.mergeRecommendationDisplayTitle
import com.yourteam.ecommerceguider.data.model.sanitizeRecommendReason
import com.yourteam.ecommerceguider.data.repository.ShoppingRepository
import java.io.File
import java.util.concurrent.CancellationException
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asSharedFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

private const val STREAM_DEBUG_TAG = "RecommendationStream"
private const val MIN_VOICE_RECORDING_MS = 700L

fun resolveDisplayName(userId: String?): String? {
    return userId
        ?.trim()
        ?.takeIf { it.isNotEmpty() }
        ?.substringBefore("_")
        ?.trim()
        ?.takeIf { it.isNotEmpty() }
}

class ChatViewModel(
    private val repository: ShoppingRepository = ShoppingRepository(),
) : ViewModel() {
    private val _messages = MutableStateFlow<List<ChatMessageUiModel>>(emptyList())
    val messages: StateFlow<List<ChatMessageUiModel>> = _messages.asStateFlow()

    private val _thinking = MutableStateFlow(AssistantThinkingUiModel())
    val thinking: StateFlow<AssistantThinkingUiModel> = _thinking.asStateFlow()

    private val _answer = MutableStateFlow("")
    val answer: StateFlow<String> = _answer.asStateFlow()

    private val _products = MutableStateFlow<List<ProductUiModel>>(emptyList())
    val products: StateFlow<List<ProductUiModel>> = _products.asStateFlow()

    private val _recommendationSections = MutableStateFlow<List<RecommendationSectionUiModel>>(emptyList())
    val recommendationSections: StateFlow<List<RecommendationSectionUiModel>> = _recommendationSections.asStateFlow()

    private val _scenarioBundles = MutableStateFlow<List<ScenarioBundleUiModel>>(emptyList())
    val scenarioBundles: StateFlow<List<ScenarioBundleUiModel>> = _scenarioBundles.asStateFlow()

    private val _specSelections = MutableStateFlow<List<SpecSelectionUiModel>>(emptyList())
    val specSelections: StateFlow<List<SpecSelectionUiModel>> = _specSelections.asStateFlow()

    private val _activeProductCardSpecSelection = MutableStateFlow<SpecSelectionUiModel?>(null)
    val activeProductCardSpecSelection: StateFlow<SpecSelectionUiModel?> =
        _activeProductCardSpecSelection.asStateFlow()

    private val _activeTurnId = MutableStateFlow<String?>(null)
    val activeTurnId: StateFlow<String?> = _activeTurnId.asStateFlow()

    private val _activeTurnAllowsEmptyProducts = MutableStateFlow(false)
    val activeTurnAllowsEmptyProducts: StateFlow<Boolean> = _activeTurnAllowsEmptyProducts.asStateFlow()

    private val _cartItemCount = MutableStateFlow(0)
    val cartItemCount: StateFlow<Int> = _cartItemCount.asStateFlow()

    private val _displayName = MutableStateFlow(resolveDisplayName(repository.currentUserId))
    val displayName: StateFlow<String?> = _displayName.asStateFlow()

    private val _isStreaming = MutableStateFlow(false)
    val isStreaming: StateFlow<Boolean> = _isStreaming.asStateFlow()

    private val _voiceInputState = MutableStateFlow<VoiceInputState>(VoiceInputState.Idle)
    val voiceInputState: StateFlow<VoiceInputState> = _voiceInputState.asStateFlow()

    private val _ttsPlaybackState = MutableStateFlow<TtsPlaybackState>(TtsPlaybackState.Idle)
    val ttsPlaybackState: StateFlow<TtsPlaybackState> = _ttsPlaybackState.asStateFlow()

    private val _errorMessage = MutableStateFlow<String?>(null)
    val errorMessage: StateFlow<String?> = _errorMessage.asStateFlow()

    private val _cartTip = MutableSharedFlow<String>(extraBufferCapacity = 1)
    val cartTip: SharedFlow<String> = _cartTip.asSharedFlow()

    private val _navigation = MutableSharedFlow<BackendNavigationUiModel>(extraBufferCapacity = 1)
    val navigation: SharedFlow<BackendNavigationUiModel> = _navigation.asSharedFlow()

    private var streamJob: Job? = null
    private var elapsedTickerJob: Job? = null
    private val recommendationTypewriterJobs = mutableMapOf<String, Job>()
    private val appliedSectionDeltas = mutableSetOf<String>()
    private var currentTurnId: String? = null
    private var currentAssistantMessageId: String? = null
    private var currentRequestStartElapsedMs: Long = 0L
    private var responseCompletedForCurrentTurn: Boolean = false
    private var voiceRecorder: MediaRecorder? = null
    private var voiceFile: File? = null
    private var voiceTranscriptionJob: Job? = null
    private var voiceRecordingStartedElapsedMs: Long = 0L
    private var ttsPlayer: MediaPlayer? = null
    private var ttsJob: Job? = null
    private var speakResponseForCurrentTurn: Boolean = false

    init {
        refreshCartCount()
    }

    override fun onCleared() {
        stopElapsedTicker()
        cancelRecommendationTypewriters()
        streamJob?.cancel()
        cancelVoiceInput()
        stopTtsPlayback()
        super.onCleared()
    }

    fun sendMessage(message: String) {
        sendTextMessage(message = message, speakResponse = false)
    }

    private fun sendTextMessage(message: String, speakResponse: Boolean): Boolean {
        val trimmedMessage = message.trim()
        if (trimmedMessage.isBlank() || _isStreaming.value) {
            return false
        }
        if (!speakResponse) {
            stopTtsPlayback()
        }
        startStream(
            userMessage = trimmedMessage,
            initialThinking = "分析用户需求",
            stream = repository.streamChat(trimmedMessage),
            speakResponse = speakResponse,
        )
        return true
    }

    fun uploadImageForRecommendation(
        contentResolver: ContentResolver,
        imageUri: Uri,
        message: String,
    ) {
        if (_isStreaming.value) {
            return
        }

        startStream(
            userMessage = message.trim().ifBlank { "已上传一张图片，请帮我找同款" },
            initialThinking = "识别图片并匹配相似商品",
            stream = repository.streamImageChat(
                contentResolver = contentResolver,
                imageUri = imageUri,
                message = message.trim(),
            ),
        )
    }

    fun stopStreaming() {
        streamJob?.cancel()
        streamJob = null
        speakResponseForCurrentTurn = false
        stopElapsedTicker()
        markInterruptedSections()
        cancelRecommendationTypewritersForTurn(currentTurnId)
        markAssistantMessageDone()
        _isStreaming.value = false
        if (_voiceInputState.value is VoiceInputState.Sending) {
            _voiceInputState.value = VoiceInputState.Idle
        }
        markThinkingFailed()
    }

    fun toggleVoiceRecording(cacheDir: File) {
        when (_voiceInputState.value) {
            VoiceInputState.Recording -> stopVoiceRecordingAndSend()
            VoiceInputState.Transcribing,
            VoiceInputState.Sending -> Unit

            VoiceInputState.Idle,
            is VoiceInputState.Error -> startVoiceRecording(cacheDir)
        }
    }

    fun cancelVoiceInput() {
        val recorder = voiceRecorder
        voiceRecorder = null
        voiceTranscriptionJob?.cancel()
        voiceTranscriptionJob = null
        runCatching { recorder?.release() }
        voiceFile?.delete()
        voiceFile = null
        voiceRecordingStartedElapsedMs = 0L
        if (_voiceInputState.value !is VoiceInputState.Idle) {
            _voiceInputState.value = VoiceInputState.Idle
        }
    }

    fun stopTtsPlayback() {
        ttsJob?.cancel()
        ttsJob = null
        val player = ttsPlayer
        ttsPlayer = null
        runCatching {
            if (player?.isPlaying == true) {
                player.stop()
            }
        }
        runCatching { player?.release() }
        if (_ttsPlaybackState.value !is TtsPlaybackState.Idle) {
            _ttsPlaybackState.value = TtsPlaybackState.Idle
        }
    }

    @Suppress("DEPRECATION")
    private fun startVoiceRecording(cacheDir: File) {
        if (_isStreaming.value) {
            _cartTip.tryEmit("请先等待当前回复结束")
            return
        }
        stopTtsPlayback()
        cancelVoiceInput()
        val result = runCatching {
            val voiceDir = File(cacheDir, "voice")
            if (!voiceDir.exists()) {
                voiceDir.mkdirs()
            }
            val file = File.createTempFile("voice_input_", ".m4a", voiceDir)
            val recorder = MediaRecorder().apply {
                setAudioSource(MediaRecorder.AudioSource.MIC)
                setOutputFormat(MediaRecorder.OutputFormat.MPEG_4)
                setAudioEncoder(MediaRecorder.AudioEncoder.AAC)
                setAudioSamplingRate(44_100)
                setAudioEncodingBitRate(128_000)
                setOutputFile(file.absolutePath)
                prepare()
                start()
            }
            voiceFile = file
            voiceRecorder = recorder
            voiceRecordingStartedElapsedMs = SystemClock.elapsedRealtime()
        }
        result
            .onSuccess {
                _voiceInputState.value = VoiceInputState.Recording
                _cartTip.tryEmit("正在录音，再点一次发送")
            }
            .onFailure {
                releaseVoiceRecordingFile()
                showVoiceError("录音启动失败，请检查麦克风权限。")
            }
    }

    private fun stopVoiceRecordingAndSend() {
        val recorder = voiceRecorder
        val file = voiceFile
        val durationMs = SystemClock.elapsedRealtime() - voiceRecordingStartedElapsedMs
        voiceRecorder = null
        voiceFile = null
        voiceRecordingStartedElapsedMs = 0L

        val stopResult = runCatching { recorder?.stop() }
        runCatching { recorder?.release() }
        if (stopResult.isFailure || file == null || !file.exists() || file.length() <= 0L) {
            file?.delete()
            showVoiceError("录音保存失败，请重新录音。")
            return
        }
        if (durationMs < MIN_VOICE_RECORDING_MS) {
            file.delete()
            showVoiceError("录音太短，请稍微说长一点。")
            return
        }

        _voiceInputState.value = VoiceInputState.Transcribing
        voiceTranscriptionJob?.cancel()
        voiceTranscriptionJob = viewModelScope.launch {
            try {
                val result = repository.transcribeVoice(file)
                result
                    .onSuccess { transcript ->
                        val text = transcript.trim()
                        if (text.isBlank()) {
                            showVoiceError("没有识别到语音内容，请再试一次。")
                            return@onSuccess
                        }
                        _voiceInputState.value = VoiceInputState.Sending
                        if (!sendTextMessage(message = text, speakResponse = true)) {
                            showVoiceError("当前无法发送语音消息，请稍后再试。")
                        }
                    }
                    .onFailure { error ->
                        if (error is CancellationException) {
                            return@onFailure
                        }
                        showVoiceError(error.message ?: "语音识别失败，请稍后再试。")
                    }
            } finally {
                file.delete()
                voiceTranscriptionJob = null
            }
        }
    }

    private fun releaseVoiceRecordingFile() {
        runCatching { voiceRecorder?.release() }
        voiceRecorder = null
        voiceFile?.delete()
        voiceFile = null
        voiceRecordingStartedElapsedMs = 0L
    }

    private fun showVoiceError(message: String) {
        _voiceInputState.value = VoiceInputState.Error(message)
        _cartTip.tryEmit(message)
    }

    fun toggleThinkingExpanded() {
        _thinking.value = _thinking.value.copy(expanded = !_thinking.value.expanded)
    }

    fun addToCart(skuId: String) {
        viewModelScope.launch {
            val product = findCachedProduct(skuId) ?: runCatching { repository.fetchProduct(skuId) }.getOrNull()
            if (product != null) {
                addKnownProductToCart(product)
            } else {
                addProductIdToCart(skuId)
            }
        }
    }

    fun addToCart(product: ProductUiModel) {
        viewModelScope.launch {
            addKnownProductToCart(product)
        }
    }

    fun addProductCardToCart(product: ProductUiModel, anchorRecommendationId: String?) {
        viewModelScope.launch {
            addKnownProductCardToCart(product, anchorRecommendationId)
        }
    }

    fun addSelectedSpecToCart(selection: SpecSelectionUiModel, option: SpecSelectionOptionUiModel) {
        if (!option.available || option.stock == 0) {
            _cartTip.tryEmit("该规格暂时无库存")
            return
        }
        if (selection.selectedSkuId != null) {
            _cartTip.tryEmit("该规格已加入购物车")
            return
        }
        if (option.skuId.isBlank() || option.selectedSpecs.isEmpty()) {
            _cartTip.tryEmit("规格信息缺失，请重新选择商品")
            return
        }
        clearSpecSelectionError(selection)
        viewModelScope.launch {
            runCatching {
                repository.addToCart(
                    skuId = selection.productId,
                    selectedSkuId = option.skuId,
                    selectedSpecs = option.selectedSpecs,
                    unitPrice = option.price,
                    productName = selection.productName,
                    imageUrl = selection.imageUrl,
                    specSummary = option.specText,
                    quantity = selection.quantity,
                )
            }
                .onSuccess { snapshot ->
                    _cartItemCount.value = snapshot.totalItems
                    if (selection.source == "product_card") {
                        if (_activeProductCardSpecSelection.value?.stableKey == selection.stableKey) {
                            _activeProductCardSpecSelection.value = null
                        }
                    } else {
                        val successText = buildSpecSelectionSuccessText(selection, option)
                        markSpecSelectionCompleted(selection, option, successText)
                        _cartTip.tryEmit(successText)
                        return@onSuccess
                    }
                    _cartTip.tryEmit("已加入购物车：${option.specText}")
                }
                .onFailure {
                    val errorText = "加入购物车失败，请稍后重试"
                    if (selection.source != "product_card") {
                        markSpecSelectionError(selection, errorText)
                    }
                    _cartTip.tryEmit(errorText)
                }
        }
    }

    private suspend fun addKnownProductToCart(product: ProductUiModel) {
        val resolvedProduct = if (product.skus.isEmpty()) {
            runCatching { repository.fetchProduct(product.skuId) }.getOrNull() ?: product
        } else {
            product
        }
        addResolvedProductToCart(resolvedProduct)
    }

    private suspend fun addKnownProductCardToCart(
        product: ProductUiModel,
        anchorRecommendationId: String?,
    ) {
        val resolvedProduct = if (product.skus.isEmpty()) {
            runCatching { repository.fetchProduct(product.skuId) }.getOrNull() ?: product
        } else {
            product
        }
        if (resolvedProduct.skus.size > 1) {
            val turnId = currentTurnId ?: _activeTurnId.value ?: "turn-product-card-${System.currentTimeMillis()}"
            _activeProductCardSpecSelection.value = resolvedProduct.toSpecSelection(turnId).copy(
                source = "product_card",
                anchorProductId = resolvedProduct.productId ?: resolvedProduct.skuId,
                anchorSkuId = resolvedProduct.skuId,
                anchorRecommendationId = anchorRecommendationId,
            )
            _cartTip.tryEmit("请选择商品规格")
            return
        }
        _activeProductCardSpecSelection.value = null
        addSingleResolvedProductToCart(resolvedProduct)
    }

    private suspend fun addResolvedProductToCart(product: ProductUiModel) {
        if (product.skus.size > 1) {
            val turnId = currentTurnId ?: "turn-local-${System.currentTimeMillis()}".also { generatedTurnId ->
                currentTurnId = generatedTurnId
                _activeTurnId.value = generatedTurnId
            }
            upsertSpecSelection(product.toSpecSelection(turnId))
            ensureAssistantMessage()
            _cartTip.tryEmit("请选择商品规格")
            return
        }
        addSingleResolvedProductToCart(product)
    }

    private suspend fun addSingleResolvedProductToCart(product: ProductUiModel) {
        val onlySku = product.skus.singleOrNull()
        val selectedSpecs = onlySku?.properties.orEmpty()
        val specSummary = selectedSpecs.toSpecSummary()
        runCatching {
            repository.addToCart(
                skuId = product.skuId,
                selectedSkuId = onlySku?.skuId,
                selectedSpecs = selectedSpecs,
                unitPrice = onlySku?.price ?: product.price,
                productName = product.displayTitle,
                imageUrl = product.imageUrl,
                specSummary = specSummary,
            )
        }
            .onSuccess { snapshot ->
                _cartItemCount.value = snapshot.totalItems
                _cartTip.tryEmit(specSummary?.let { "已加入购物车：$it" } ?: "已加入购物车")
            }
            .onFailure { _cartTip.tryEmit("加购失败，请稍后重试") }
    }

    private fun findCachedProduct(skuId: String): ProductUiModel? {
        if (skuId.isBlank()) {
            return null
        }
        val bundleProducts = _scenarioBundles.value.flatMap { bundle -> bundle.items.map { it.product } }
        val candidates = _products.value + _recommendationSections.value.mapNotNull { it.product } + bundleProducts
        return candidates.firstOrNull { product ->
            product.skuId == skuId ||
                product.productId == skuId ||
                product.skus.any { sku -> sku.skuId == skuId }
        }
    }

    private suspend fun addProductIdToCart(skuId: String) {
        runCatching {
            repository.addToCart(skuId = skuId)
        }
            .onSuccess { snapshot ->
                _cartItemCount.value = snapshot.totalItems
                _cartTip.tryEmit("已加入购物车")
            }
            .onFailure { _cartTip.tryEmit("加购失败，请稍后重试") }
    }

    fun clearError() {
        _errorMessage.value = null
    }

    private fun startStream(
        userMessage: String,
        initialThinking: String,
        stream: Flow<ChatStreamEvent>,
        speakResponse: Boolean = false,
    ) {
        flushRecommendationTypewriters()
        cancelRecommendationTypewriters()
        val startedAt = System.currentTimeMillis()
        val startedElapsed = SystemClock.elapsedRealtime()
        val turnId = "turn-local-$startedAt"
        currentTurnId = turnId
        currentAssistantMessageId = null
        currentRequestStartElapsedMs = startedElapsed
        responseCompletedForCurrentTurn = false
        speakResponseForCurrentTurn = speakResponse
        _activeTurnId.value = turnId
        _activeTurnAllowsEmptyProducts.value = shouldAllowEmptyProductsCard(userMessage)
        _products.value = emptyList()
        _answer.value = ""
        _errorMessage.value = null
        _activeProductCardSpecSelection.value = null
        appliedSectionDeltas.clear()
        stopElapsedTicker()
        _thinking.value = AssistantThinkingUiModel(
            status = AssistantThinkingStatus.Running,
            stages = defaultProcessStages().markStageRunning(
                stageId = "need_understanding",
                startedElapsedMs = 0L,
                summary = initialThinking.takeIf { it.isNotBlank() },
            ),
            expanded = true,
            totalElapsedMs = 0L,
        )
        _messages.value = _messages.value + ChatMessageUiModel(
            id = "user-$startedAt",
            turnId = turnId,
            content = userMessage,
            isUser = true,
            timestamp = startedAt,
        )
        _isStreaming.value = true
        startElapsedTicker()

        streamJob = viewModelScope.launch {
            runCatching {
                stream.collect(::handleStreamEvent)
            }.onFailure {
                if (it is CancellationException) {
                    stopElapsedTicker()
                    finishThinking()
                    markAssistantMessageDone()
                    _isStreaming.value = false
                    if (_voiceInputState.value is VoiceInputState.Sending) {
                        _voiceInputState.value = VoiceInputState.Idle
                    }
                    speakResponseForCurrentTurn = false
                    return@onFailure
                }
                _errorMessage.value = "请求失败，请检查后端服务和真机端口转发。"
                stopElapsedTicker()
                markThinkingFailed()
                markAssistantMessageDone()
                _isStreaming.value = false
                if (_voiceInputState.value is VoiceInputState.Sending) {
                    _voiceInputState.value = VoiceInputState.Error("请求失败，请检查后端服务和真机端口转发。")
                }
                speakResponseForCurrentTurn = false
            }
        }
    }

    private fun handleStreamEvent(event: ChatStreamEvent) {
        logRecommendationVmReceive(event)
        when (event.event) {
            "progress", "process" -> handleProgressEvent(event)
            "generation_started" -> handleGenerationStarted(event)
            "response_delta" -> appendAnswerChunk(event.text.orEmpty())
            "response_completed" -> handleResponseCompleted(event)
            "token" -> {
                if (!responseCompletedForCurrentTurn) {
                    appendAnswerChunk(event.text.orEmpty())
                }
            }
            "recommendation_section_start" -> {
                event.recommendationSection?.let(::normalizeSectionTurnId)?.let { section ->
                    adoptTurnId(section.turnId)
                    ensureAssistantMessage()
                    upsertRecommendationSection(section)
                }
                collapseThinking()
            }
            "recommendation_text_delta" -> {
                event.recommendationSection?.let(::normalizeSectionTurnId)?.let { section ->
                    adoptTurnId(section.turnId)
                    ensureAssistantMessage()
                    appendRecommendationSectionDelta(section)
                }
                collapseThinking()
            }
            "recommendation_text_done" -> {
                event.recommendationSection?.let(::normalizeSectionTurnId)?.let { section ->
                    adoptTurnId(section.turnId)
                    ensureAssistantMessage()
                    finishRecommendationSection(section)
                }
                collapseThinking()
            }
            "recommendation_section_done" -> {
                event.recommendationSection?.let(::normalizeSectionTurnId)?.let { section ->
                    adoptTurnId(section.turnId)
                    ensureAssistantMessage()
                    markRecommendationSectionDone(section)
                }
                collapseThinking()
            }
            "generation_degraded" -> {
                // Keep already streamed text; fallback section events will arrive separately.
            }
            "product_card" -> {
                event.recommendationSection?.let(::normalizeSectionTurnId)?.let { section ->
                    adoptTurnId(section.turnId)
                    ensureAssistantMessage()
                    attachRecommendationProduct(section)
                }
                event.product?.let {
                    ensureAssistantMessage()
                    _products.value = mergeProductsBySku(_products.value, listOf(it))
                    if (it.isScenarioBundleProduct) {
                        upsertScenarioBundleProduct(it)
                    }
                }
                collapseThinking()
            }
            "product_cards", "products", "alternatives" -> {
                if (event.products.isNotEmpty()) {
                    ensureAssistantMessage()
                }
                _products.value = mergeProductsBySku(_products.value, event.products)
                mergeSectionProductSnapshots(event.products)
                event.products
                    .filter { it.isScenarioBundleProduct }
                    .forEach(::upsertScenarioBundleProduct)
                if (event.products.isNotEmpty()) {
                    collapseThinking()
                }
            }
            "plan_overview_start", "plan_overview", "plan_overview_done", "scenario_bundle" -> {
                event.scenarioBundle?.let(::normalizeScenarioBundleTurnId)?.let { bundle ->
                    adoptTurnId(bundle.turnId)
                    ensureAssistantMessage()
                    upsertScenarioBundle(bundle)
                    _products.value = mergeProductsBySku(_products.value, bundle.items.map { it.product })
                    collapseThinking()
                }
            }
            "cart_update" -> _cartItemCount.value = event.cart?.totalItems ?: _cartItemCount.value
            "cart" -> _cartItemCount.value = event.cart?.totalItems ?: _cartItemCount.value
            "product_detail" -> event.product?.let { _products.value = listOf(it) }
            "spec_selection" -> {
                event.specSelection?.let(::normalizeSpecSelectionTurnId)?.let { selection ->
                    adoptTurnId(selection.turnId)
                    upsertSpecSelection(selection)
                    ensureAssistantMessage()
                }
                collapseThinking()
            }
            "frontend_action" -> event.navigation?.let { _navigation.tryEmit(it) }
            "turn_result" -> {
                if (shouldApplyTurnResultText(event)) {
                    event.text?.let { replaceAnswerIfBlank(it) }
                }
                event.scenarioBundle?.let(::normalizeScenarioBundleTurnId)?.let { bundle ->
                    adoptTurnId(bundle.turnId)
                    ensureAssistantMessage()
                    upsertScenarioBundle(bundle)
                }
                if (event.products.isNotEmpty()) {
                    _products.value = mergeProductsBySku(_products.value, event.products)
                    mergeSectionProductSnapshots(event.products)
                    collapseThinking()
                }
                event.cart?.let { _cartItemCount.value = it.totalItems }
                event.specSelection?.let(::normalizeSpecSelectionTurnId)?.let { selection ->
                    adoptTurnId(selection.turnId)
                    upsertSpecSelection(selection)
                }
                event.navigation?.let { _navigation.tryEmit(it) }
                event.errorMessage?.let { _errorMessage.value = it }
            }
            "error" -> {
                _errorMessage.value = event.errorMessage ?: "请求失败，请检查后端服务。"
                markAssistantMessageDone()
                stopElapsedTicker()
                markThinkingFailed()
                if (_voiceInputState.value is VoiceInputState.Sending) {
                    _voiceInputState.value = VoiceInputState.Error(event.errorMessage ?: "请求失败，请检查后端服务。")
                }
                speakResponseForCurrentTurn = false
            }
            "done" -> {
                _isStreaming.value = false
                stopElapsedTicker()
                finishThinking()
                markAssistantMessageDone()
                refreshCartCount()
                if (_voiceInputState.value is VoiceInputState.Sending) {
                    _voiceInputState.value = VoiceInputState.Idle
                }
                if (speakResponseForCurrentTurn) {
                    val spokenText = buildSpokenResponseText()
                    speakResponseForCurrentTurn = false
                    synthesizeAndPlay(spokenText)
                }
            }
        }
    }

    private fun logRecommendationVmReceive(event: ChatStreamEvent) {
        val section = event.recommendationSection ?: return
        if (
            event.event != "recommendation_section_start" &&
            event.event != "recommendation_text_done" &&
            event.event != "product_card"
        ) {
            return
        }
        Log.d(
            STREAM_DEBUG_TAG,
            "[recommendation_vm_receive] event=${event.event} sectionIndex=${section.sectionIndex} " +
                "skuId=${section.skuId} productId=${section.product?.productId.orEmpty()} " +
                "displayTitle='${section.displayTitle}' recommendReasonLength=${section.recommendReason.length}",
        )
    }

    private fun normalizeSectionTurnId(section: RecommendationSectionUiModel): RecommendationSectionUiModel {
        val current = currentTurnId
        val shouldUseCurrent = section.turnId.isBlank() || section.turnId == "turn_current" || section.turnId == "snapshot"
        return if (shouldUseCurrent && !current.isNullOrBlank()) {
            section.copy(turnId = current)
        } else {
            section
        }
    }

    private fun normalizeScenarioBundleTurnId(bundle: ScenarioBundleUiModel): ScenarioBundleUiModel {
        val current = currentTurnId
        val shouldUseCurrent = bundle.turnId.isBlank() || bundle.turnId == "turn_current" || bundle.turnId == "snapshot"
        return if (shouldUseCurrent && !current.isNullOrBlank()) {
            bundle.copy(turnId = current)
        } else {
            bundle
        }
    }

    private fun normalizeSpecSelectionTurnId(selection: SpecSelectionUiModel): SpecSelectionUiModel {
        val current = currentTurnId
        val shouldUseCurrent = selection.turnId.isBlank() || selection.turnId == "turn_current" || selection.turnId == "snapshot"
        return if (shouldUseCurrent && !current.isNullOrBlank()) {
            selection.copy(turnId = current)
        } else {
            selection
        }
    }

    private fun appendAnswerChunk(chunk: String) {
        if (chunk.isBlank()) {
            return
        }
        val messageId = ensureAssistantMessage()
        _answer.value += chunk
        updateAssistantMessage(messageId) { message ->
            message.copy(
                content = message.content + chunk,
                isStreaming = true,
                thinking = snapshotCurrentThinking(),
            )
        }
        collapseThinking()
    }

    private fun replaceAnswerIfBlank(text: String) {
        if (text.isBlank()) {
            return
        }
        if (_answer.value.isNotBlank()) {
            return
        }
        val messageId = ensureAssistantMessage()
        _answer.value = text
        updateAssistantMessage(messageId) { message ->
            message.copy(
                content = text,
                isStreaming = false,
                thinking = snapshotCurrentThinking(),
            )
        }
    }

    private fun buildSpokenResponseText(): String {
        val activeTurn = currentTurnId
        val sections = _recommendationSections.value
            .filter { section -> activeTurn == null || section.turnId == activeTurn }
            .sortedWith(compareBy<RecommendationSectionUiModel> { it.sectionIndex }.thenBy { it.skuId })
            .take(3)
            .flatMap { section ->
                listOf(
                    section.displayTitle,
                    section.recommendReason
                        .ifBlank { section.displayText }
                        .ifBlank { section.text }
                        .ifBlank { section.reason.orEmpty() },
                )
            }
        val bundleTexts = _scenarioBundles.value
            .filter { bundle -> activeTurn == null || bundle.turnId == activeTurn }
            .flatMap { bundle ->
                listOf(bundle.title, bundle.summary) +
                    bundle.items.take(3).flatMap { item -> listOf(item.role, item.shortReason) }
            }
        return listOf(_answer.value)
            .plus(bundleTexts)
            .plus(sections)
            .map { it.cleanForSpeech() }
            .filter { it.isNotBlank() }
            .distinct()
            .joinToString("。")
            .take(600)
    }

    private fun String.cleanForSpeech(): String {
        return replace(Regex("""https?://\S+"""), "")
            .replace(Regex("""\b[pPsS]_[A-Za-z0-9_]+\b"""), "")
            .replace(Regex("""\s+"""), " ")
            .trim()
    }

    private fun synthesizeAndPlay(text: String) {
        if (text.isBlank()) {
            return
        }
        _ttsPlaybackState.value = TtsPlaybackState.Preparing
        ttsJob?.cancel()
        ttsJob = viewModelScope.launch {
            try {
                repository.synthesizeVoice(text)
                    .onSuccess { url -> playTtsUrl(url) }
                    .onFailure {
                        if (it is CancellationException) {
                            return@onFailure
                        }
                        _ttsPlaybackState.value = TtsPlaybackState.Error("语音播放暂不可用")
                        _cartTip.tryEmit("语音播放暂不可用")
                    }
            } finally {
                ttsJob = null
            }
        }
    }

    private fun playTtsUrl(url: String) {
        stopTtsPlayback()
        _ttsPlaybackState.value = TtsPlaybackState.Preparing
        val player = MediaPlayer()
        ttsPlayer = player
        runCatching {
            player.setDataSource(url)
            player.setOnPreparedListener { preparedPlayer ->
                if (ttsPlayer === preparedPlayer) {
                    _ttsPlaybackState.value = TtsPlaybackState.Playing
                    preparedPlayer.start()
                } else {
                    preparedPlayer.release()
                }
            }
            player.setOnCompletionListener { completedPlayer ->
                if (ttsPlayer === completedPlayer) {
                    ttsPlayer = null
                }
                runCatching { completedPlayer.release() }
                _ttsPlaybackState.value = TtsPlaybackState.Idle
            }
            player.setOnErrorListener { erroredPlayer, _, _ ->
                if (ttsPlayer === erroredPlayer) {
                    ttsPlayer = null
                }
                runCatching { erroredPlayer.release() }
                _ttsPlaybackState.value = TtsPlaybackState.Error("语音播放失败")
                true
            }
            player.prepareAsync()
        }.onFailure {
            if (ttsPlayer === player) {
                ttsPlayer = null
            }
            runCatching { player.release() }
            _ttsPlaybackState.value = TtsPlaybackState.Error("语音播放失败")
        }
    }

    private fun shouldApplyTurnResultText(event: ChatStreamEvent): Boolean {
        if (event.text.isNullOrBlank()) {
            return false
        }
        if (event.scenarioBundle != null || hasScenarioBundleForCurrentTurn()) {
            return false
        }
        if (hasRecommendationSectionsForCurrentTurn() || event.products.isNotEmpty()) {
            return false
        }
        return true
    }

    private fun hasScenarioBundleForCurrentTurn(): Boolean {
        val activeTurn = currentTurnId
        if (activeTurn.isNullOrBlank()) {
            return _scenarioBundles.value.isNotEmpty()
        }
        return _scenarioBundles.value.any { bundle -> bundle.turnId == activeTurn }
    }

    private fun hasRecommendationSectionsForCurrentTurn(): Boolean {
        val activeTurn = currentTurnId
        if (activeTurn.isNullOrBlank()) {
            return _recommendationSections.value.isNotEmpty()
        }
        return _recommendationSections.value.any { section -> section.turnId == activeTurn }
    }

    private fun shouldAllowEmptyProductsCard(userMessage: String): Boolean {
        val normalized = userMessage.lowercase()
        val cartTerms = listOf(
            "购物车",
            "加入",
            "加购",
            "规格",
            "下单",
            "结算",
            "付款",
            "删除",
            "移除",
            "清空",
            "保留",
            "数量",
            "checkout",
            "cart",
        )
        if (cartTerms.any { term -> normalized.contains(term) }) {
            return false
        }
        val recommendationTerms = listOf(
            "推荐",
            "帮我找",
            "找一款",
            "找一个",
            "挑",
            "筛",
            "筛选",
            "有没有",
            "想买",
            "预算",
            "适合",
            "换一款",
            "换一批",
            "recommend",
            "find",
        )
        return recommendationTerms.any { term -> normalized.contains(term) }
    }

    private fun ensureAssistantMessage(): String {
        val turnId = currentTurnId ?: "turn-local-${System.currentTimeMillis()}".also { generatedTurnId ->
            currentTurnId = generatedTurnId
            _activeTurnId.value = generatedTurnId
        }
        currentAssistantMessageId
            ?.takeIf { messageId -> _messages.value.any { it.id == messageId } }
            ?.let { return it }

        val messageId = "assistant-${System.currentTimeMillis()}"
        currentAssistantMessageId = messageId
        _messages.value = _messages.value + ChatMessageUiModel(
            id = messageId,
            turnId = turnId,
            content = "",
            isUser = false,
            isStreaming = true,
            thinking = snapshotCurrentThinking(),
        )
        return messageId
    }

    private fun updateAssistantMessage(
        messageId: String,
        update: (ChatMessageUiModel) -> ChatMessageUiModel,
    ) {
        _messages.value = _messages.value.map { message ->
            if (message.id == messageId) {
                update(message)
            } else {
                message
            }
        }
    }

    private fun markAssistantMessageDone() {
        currentAssistantMessageId?.let { messageId ->
            updateAssistantMessage(messageId) { message ->
                message.copy(
                    isStreaming = false,
                    thinking = snapshotCurrentThinking(),
                )
            }
        }
    }

    private fun snapshotCurrentThinking(): AssistantThinkingUiModel? {
        val current = _thinking.value
        if (current.status == AssistantThinkingStatus.Idle) {
            return null
        }
        return current.copy(
            expanded = false,
            isGeneratingResponse = false,
        )
    }

    private fun syncCurrentAssistantThinkingSnapshot() {
        currentAssistantMessageId?.let { messageId ->
            updateAssistantMessage(messageId) { message ->
                message.copy(thinking = snapshotCurrentThinking())
            }
        }
    }

    private fun adoptTurnId(turnId: String) {
        if (turnId.isBlank()) {
            return
        }
        val previousTurnId = currentTurnId
        currentTurnId = turnId
        _activeTurnId.value = turnId
        if (previousTurnId.isNullOrBlank() || previousTurnId == turnId) {
            return
        }
        _messages.value = _messages.value.map { message ->
            if (message.turnId == previousTurnId) {
                message.copy(turnId = turnId)
            } else {
                message
            }
        }
        _recommendationSections.value = _recommendationSections.value.map { section ->
            if (section.turnId == previousTurnId) {
                section.copy(turnId = turnId)
            } else {
                section
            }
        }
        _scenarioBundles.value = _scenarioBundles.value.map { bundle ->
            if (bundle.turnId == previousTurnId) {
                bundle.copy(turnId = turnId)
            } else {
                bundle
            }
        }
        _specSelections.value = _specSelections.value.map { selection ->
            if (selection.turnId == previousTurnId) {
                selection.copy(turnId = turnId)
            } else {
                selection
            }
        }
    }

    private fun appendResponsePreviewDelta(delta: String, backendElapsedMs: Long?) {
        if (delta.isBlank()) {
            return
        }
        val current = _thinking.value
        _thinking.value = current.copy(
            status = AssistantThinkingStatus.Generating,
            previewText = current.previewText + delta,
            totalElapsedMs = backendElapsedMs ?: currentElapsedMs(),
            isGeneratingResponse = true,
            expanded = false,
        )
    }

    private fun handleProgressEvent(event: ChatStreamEvent) {
        val stageId = mapProgressStage(
            rawStageId = event.progressStageId,
            fallbackText = event.progressText,
        )
        advanceProcessStage(
            stageId = stageId,
            summary = event.progressSummary ?: event.progressText,
            totalElapsedMs = null,
        )
    }

    private fun handleGenerationStarted(event: ChatStreamEvent) {
        advanceProcessStage(
            stageId = "response_generation",
            summary = event.progressText ?: "正在生成推荐结论",
            totalElapsedMs = null,
            status = AssistantThinkingStatus.Generating,
            expanded = false,
            isGeneratingResponse = true,
            responseStreamSupported = event.responseStreamSupported == true,
        )
    }

    private fun handleResponseCompleted(event: ChatStreamEvent) {
        responseCompletedForCurrentTurn = true
        stopElapsedTicker()
        val completedElapsedMs = currentElapsedMs().takeIf { it > 0L } ?: event.totalDurationMs ?: 0L
        val stages = completeAllStages(
            stages = _thinking.value.stages.ifEmpty { defaultProcessStages() },
        )
        _thinking.value = _thinking.value.copy(
            status = AssistantThinkingStatus.Done,
            stages = stages,
            expanded = false,
            previewText = "",
            totalElapsedMs = completedElapsedMs,
            isGeneratingResponse = false,
            responseStreamSupported = event.responseStreamSupported == true,
        )
        event.text?.takeIf { it.isNotBlank() }?.let { replaceFinalAnswer(it) }
        markAssistantMessageDone()
    }

    private fun advanceProcessStage(
        stageId: String,
        summary: String?,
        totalElapsedMs: Long? = null,
        status: AssistantThinkingStatus = AssistantThinkingStatus.Running,
        expanded: Boolean = _thinking.value.expanded,
        isGeneratingResponse: Boolean = false,
        responseStreamSupported: Boolean = _thinking.value.responseStreamSupported,
    ) {
        val elapsed = totalElapsedMs ?: currentElapsedMs()
        val current = _thinking.value
        val stages = current.stages.ifEmpty { defaultProcessStages() }
        val targetIndex = stages.indexOfFirst { it.stageId == stageId }
        if (targetIndex < 0) {
            return
        }
        val updatedStages = stages.mapIndexed { index, stage ->
            when {
                index < targetIndex -> stage.complete()
                index == targetIndex -> {
                    if (stage.status == AssistantProcessStageStatus.Completed) {
                        stage.copy(summary = summary ?: stage.summary)
                    } else {
                        stage.copy(
                            status = AssistantProcessStageStatus.Running,
                            startedElapsedMs = stage.startedElapsedMs ?: elapsed,
                            summary = summary ?: stage.summary,
                        )
                    }
                }
                else -> stage
            }
        }
        _thinking.value = current.copy(
            status = status,
            stages = updatedStages,
            expanded = expanded,
            totalElapsedMs = elapsed,
            isGeneratingResponse = isGeneratingResponse,
            responseStreamSupported = responseStreamSupported,
        )
    }

    private fun collapseThinking() {
        val current = _thinking.value
        if (current.status != AssistantThinkingStatus.Idle && current.status != AssistantThinkingStatus.Failed) {
            _thinking.value = current.copy(expanded = false)
            syncCurrentAssistantThinkingSnapshot()
        }
    }

    private fun finishThinking() {
        val current = _thinking.value
        if (current.status == AssistantThinkingStatus.Idle || current.status == AssistantThinkingStatus.Failed) {
            return
        }
        if (current.status == AssistantThinkingStatus.Done) {
            _thinking.value = current.copy(expanded = false)
            syncCurrentAssistantThinkingSnapshot()
            return
        }
        val elapsed = current.totalElapsedMs.takeIf { it > 0 } ?: currentElapsedMs()
        _thinking.value = current.copy(
            status = AssistantThinkingStatus.Done,
            stages = completeAllStages(
                stages = current.stages.ifEmpty { defaultProcessStages() },
            ),
            expanded = false,
            previewText = "",
            totalElapsedMs = elapsed,
            isGeneratingResponse = false,
        )
        syncCurrentAssistantThinkingSnapshot()
    }

    private fun markThinkingFailed() {
        val current = _thinking.value
        if (current.status == AssistantThinkingStatus.Idle) {
            return
        }
        val elapsed = currentElapsedMs()
        val stages = current.stages.ifEmpty { defaultProcessStages() }
        val failedStages = stages.map { stage ->
            if (stage.status == AssistantProcessStageStatus.Running) {
                stage.copy(status = AssistantProcessStageStatus.Failed)
            } else {
                stage
            }
        }
        _thinking.value = current.copy(
            status = AssistantThinkingStatus.Failed,
            stages = failedStages,
            expanded = false,
            previewText = "",
            totalElapsedMs = elapsed,
            isGeneratingResponse = false,
        )
        syncCurrentAssistantThinkingSnapshot()
    }

    private fun mergeProductsBySku(
        current: List<ProductUiModel>,
        incoming: List<ProductUiModel>,
    ): List<ProductUiModel> {
        if (incoming.isEmpty()) {
            return current
        }
        if (current.isEmpty()) {
            return incoming
        }
        val incomingBySku = incoming.associateBy { it.skuId }
        val currentSkus = current.map { it.skuId }.toSet()
        return current.map { product ->
            incomingBySku[product.skuId] ?: product
        } + incoming.filterNot { it.skuId in currentSkus }
    }

    private fun upsertRecommendationSection(section: RecommendationSectionUiModel) {
        updateRecommendationSection(section) { current ->
            current.copy(
                optionLabel = section.optionLabel.ifBlank { current.optionLabel },
                displayTitle = mergeRecommendationDisplayTitle(current.displayTitle, section.displayTitle),
                recommendReason = section.recommendReason.ifBlank { current.recommendReason },
                reason = section.reason ?: current.reason,
                recommendationTags = section.recommendationTags.ifEmpty { current.recommendationTags },
                productName = section.productName ?: current.productName,
                brand = section.brand ?: current.brand,
            )
        }
    }

    private fun appendRecommendationSectionDelta(section: RecommendationSectionUiModel) {
        val delta = section.text.takeIf { it.isNotBlank() } ?: return
        val key = section.eventId
            ?: section.sequence?.let { sequence -> "${section.requestId ?: section.turnId}:${section.sectionIndex}:$sequence" }
            ?: "${section.stableKey}:${delta.hashCode()}"
        if (!appliedSectionDeltas.add(key)) {
            return
        }
        val updateAt = System.currentTimeMillis()
        updateRecommendationSection(section) { current ->
            val rawReason = current.reason.orEmpty() + delta
            val nextText = rawReason.sanitizeRecommendReason()
            val nextDisplayText = alignedRecommendationDisplayText(nextText, current.displayText)
            Log.d(
                STREAM_DEBUG_TAG,
                "state recommendation_text_delta ts=$updateAt section=${section.sectionIndex} " +
                    "sku=${section.skuId} delta_len=${delta.length} cumulative_len=${rawReason.length}",
            )
            val nextSection = current.copy(
                reason = rawReason,
                displayTitle = mergeRecommendationDisplayTitle(current.displayTitle, section.displayTitle),
                recommendReason = nextText,
                text = nextText,
                displayText = nextDisplayText,
                recommendationTags = section.recommendationTags.ifEmpty { current.recommendationTags },
                productName = section.productName ?: current.productName,
                brand = section.brand ?: current.brand,
            )
            nextSection
        }
        advanceRecommendationDisplayText(section.stableKey)
        ensureRecommendationTypewriter(section.stableKey)
    }

    private fun markRecommendationSectionDone(section: RecommendationSectionUiModel) {
        updateRecommendationSection(section) { current ->
            current.copy(
                done = true,
                recommendationTags = section.recommendationTags.ifEmpty { current.recommendationTags },
                productName = section.productName ?: current.productName,
                brand = section.brand ?: current.brand,
            )
        }
        ensureRecommendationTypewriter(section.stableKey)
    }

    private fun finishRecommendationSection(section: RecommendationSectionUiModel) {
        updateRecommendationSection(section) { current ->
            val finalText = section.recommendReason
                .ifBlank { section.text }
                .ifBlank { current.recommendReason }
                .ifBlank { current.text }
                .ifBlank { section.reason.orEmpty() }
                .ifBlank { current.reason.orEmpty() }
                .sanitizeRecommendReason()
            val rawReason = section.reason
                ?.takeIf { it.isNotBlank() }
                ?: finalText.takeIf { it.isNotBlank() }
                ?: current.reason
            current.copy(
                displayTitle = mergeRecommendationDisplayTitle(current.displayTitle, section.displayTitle),
                recommendReason = finalText,
                text = finalText,
                displayText = alignedRecommendationDisplayText(finalText, current.displayText),
                reason = rawReason?.takeIf { it.isNotBlank() } ?: current.reason,
                tradeOff = section.tradeOff ?: current.tradeOff,
                recommendationTags = section.recommendationTags.ifEmpty { current.recommendationTags },
                productName = section.productName ?: current.productName,
                brand = section.brand ?: current.brand,
                done = true,
            )
        }
        ensureRecommendationTypewriter(section.stableKey)
    }

    private fun attachRecommendationProduct(section: RecommendationSectionUiModel) {
        val product = section.product
        updateRecommendationSection(section) { current ->
            val rawReason = current.reason
                ?: section.reason
                ?: current.recommendReason.takeIf { it.isNotBlank() }
                ?: section.recommendReason.takeIf { it.isNotBlank() }
                ?: product?.recommendReason
                ?: product?.presentation?.reason
                ?: product?.reason
            val finalText = current.text
                .takeIf { it.isNotBlank() }
                ?: current.recommendReason.takeIf { it.isNotBlank() }
                ?: section.recommendReason.takeIf { it.isNotBlank() }
                ?: section.text.takeIf { it.isNotBlank() }
                ?: section.reason?.takeIf { it.isNotBlank() }
                ?: product?.recommendReason.orEmpty()
            val cleanFinalText = finalText.sanitizeRecommendReason()
            val nextProduct = product ?: current.product
            val nextSection = current.copy(product = nextProduct)
            current.copy(
                displayTitle = mergeRecommendationDisplayTitle(nextSection.displayTitle, section.displayTitle),
                recommendReason = cleanFinalText,
                text = cleanFinalText,
                displayText = alignedRecommendationDisplayText(cleanFinalText, current.displayText),
                reason = rawReason ?: current.reason,
                tradeOff = section.tradeOff ?: product?.presentation?.tradeOff ?: current.tradeOff,
                recommendationTags = section.recommendationTags
                    .ifEmpty { product?.recommendationTags.orEmpty() }
                    .ifEmpty { current.recommendationTags },
                productName = section.productName ?: product?.displayTitleShort ?: current.productName,
                brand = section.brand ?: product?.brand ?: current.brand,
                product = nextProduct,
                done = true,
            )
        }
        ensureRecommendationTypewriter(section.stableKey)
    }

    private fun ensureRecommendationTypewriter(sectionKey: String) {
        if (sectionKey.isBlank() || recommendationTypewriterJobs[sectionKey]?.isActive == true) {
            return
        }
        recommendationTypewriterJobs[sectionKey] = viewModelScope.launch {
            try {
                while (true) {
                    val section = _recommendationSections.value.firstOrNull { it.stableKey == sectionKey } ?: break
                    val fullText = section.text
                    val shownLength = section.displayText.length.coerceAtMost(fullText.length)
                    val backlog = fullText.length - shownLength
                    if (backlog <= 0) {
                        break
                    }
                    if (!advanceRecommendationDisplayText(sectionKey)) {
                        break
                    }
                    delay(recommendationTypewriterDelayMillis(backlog, section.done))
                }
            } finally {
                recommendationTypewriterJobs.remove(sectionKey)
            }
        }
    }

    private fun advanceRecommendationDisplayText(sectionKey: String): Boolean {
        var advanced = false
        _recommendationSections.value = _recommendationSections.value.map { current ->
            if (current.stableKey != sectionKey) {
                current
            } else {
                val fullText = current.text
                val shownLength = current.displayText.length.coerceAtMost(fullText.length)
                val backlog = fullText.length - shownLength
                if (backlog <= 0) {
                    current
                } else {
                    val targetLength = (shownLength + recommendationTypewriterStepSize(backlog, current.done))
                        .coerceAtMost(fullText.length)
                    advanced = true
                    Log.d(
                        STREAM_DEBUG_TAG,
                        "[typewriter_tick] ts=${System.currentTimeMillis()} sectionIndex=${current.sectionIndex} " +
                            "sku=${current.skuId} display_len=$targetLength full_len=${fullText.length}",
                    )
                    current.copy(displayText = fullText.substring(0, targetLength))
                }
            }
        }
        return advanced
    }

    private fun recommendationTypewriterStepSize(backlog: Int, done: Boolean): Int = when {
        done && backlog > 100 -> 8
        done && backlog > 30 -> 6
        done -> 3
        backlog > 100 -> 6
        backlog > 30 -> 3
        else -> 2
    }

    private fun recommendationTypewriterDelayMillis(backlog: Int, done: Boolean): Long = when {
        done && backlog > 100 -> 6L
        done && backlog > 30 -> 8L
        done -> 10L
        backlog > 100 -> 8L
        backlog > 30 -> 12L
        else -> 18L
    }

    private fun alignedRecommendationDisplayText(fullText: String, displayText: String): String {
        if (fullText.isBlank() || displayText.isBlank()) {
            return ""
        }
        if (fullText.startsWith(displayText)) {
            return displayText
        }
        return fullText.take(displayText.length.coerceAtMost(fullText.length))
    }

    private fun mergeSectionProductSnapshots(products: List<ProductUiModel>) {
        val activeTurnId = currentTurnId
        if (products.isEmpty() || _recommendationSections.value.isEmpty() || activeTurnId.isNullOrBlank()) {
            return
        }
        val bySku = products.associateBy { it.skuId }
        _recommendationSections.value = _recommendationSections.value.map { section ->
            if (section.turnId != activeTurnId) {
                return@map section
            }
            val product = bySku[section.skuId] ?: return@map section
            section.copy(
                product = section.product ?: product,
                productName = section.productName ?: product.displayTitleShort,
                brand = section.brand ?: product.brand,
                recommendationTags = section.recommendationTags.ifEmpty { product.recommendationTags },
            ).withResolvedRecommendationTitle()
        }
    }

    private fun upsertScenarioBundle(bundle: ScenarioBundleUiModel) {
        if (
            bundle.title.isBlank() &&
            bundle.summary.isBlank() &&
            bundle.planItems.isEmpty() &&
            bundle.items.isEmpty()
        ) {
            return
        }
        val current = _scenarioBundles.value
        val index = current.indexOfFirst { it.turnId == bundle.turnId }
        _scenarioBundles.value = if (index >= 0) {
            current.mapIndexed { itemIndex, existing ->
                if (itemIndex == index) {
                    val mergedPlanItems = if (bundle.planItems.isNotEmpty()) {
                        mergeScenarioPlanItems(existing.planItems, bundle.planItems)
                    } else {
                        existing.planItems
                    }
                    existing.copy(
                        title = bundle.title.ifBlank { existing.title },
                        summary = bundle.summary.ifBlank { existing.summary },
                        planItems = mergedPlanItems,
                        items = mergeScenarioBundleItems(existing.items, bundle.items, mergedPlanItems),
                    )
                } else {
                    existing
                }
            }
        } else {
            current + bundle
        }
    }

    private fun upsertScenarioBundleProduct(product: ProductUiModel) {
        if (!product.isScenarioBundleProduct) {
            return
        }
        val turnId = currentTurnId ?: _activeTurnId.value ?: "turn_current"
        val roleName = product.displayPlanRoleName
            .ifBlank { product.subCategory ?: product.category }
        val categoryName = product.displayPlanCategoryName
        val planRole = product.displayPlanRole
            .ifBlank { product.recommendReason ?: product.reason ?: "" }
        val item = ScenarioBundleItemUiModel(
            role = roleName,
            shortReason = planRole,
            product = product,
            roleName = roleName,
            categoryName = categoryName,
            skuId = product.skuId,
            planRole = planRole,
        )
        upsertScenarioBundle(
            ScenarioBundleUiModel(
                turnId = turnId,
                planItems = listOf(
                    ScenarioPlanItemUiModel(
                        roleName = roleName,
                        categoryName = categoryName,
                        skuId = product.skuId,
                        planRole = planRole,
                    )
                ),
                items = listOf(item),
            )
        )
    }

    private fun mergeScenarioPlanItems(
        existing: List<ScenarioPlanItemUiModel>,
        incoming: List<ScenarioPlanItemUiModel>,
    ): List<ScenarioPlanItemUiModel> {
        if (existing.isEmpty()) {
            return incoming
        }
        if (incoming.isEmpty()) {
            return existing
        }
        val incomingBySku = incoming
            .mapNotNull { item -> item.skuId?.takeIf { it.isNotBlank() }?.let { it to item } }
            .toMap()
        val incomingByRole = incoming.associateBy { it.roleName }
        val merged = existing.map { item ->
            item.skuId?.let { incomingBySku[it] }
                ?: incomingByRole[item.roleName]
                ?: item
        }.toMutableList()
        val seenSkus = merged.mapNotNull { it.skuId }.toMutableSet()
        val seenRoles = merged.map { it.roleName }.toMutableSet()
        incoming.forEach { item ->
            val hasSeenSku = item.skuId?.let { it in seenSkus } == true
            if (!hasSeenSku && item.roleName !in seenRoles) {
                merged += item
                item.skuId?.let(seenSkus::add)
                seenRoles += item.roleName
            }
        }
        return merged
    }

    private fun mergeScenarioBundleItems(
        existing: List<ScenarioBundleItemUiModel>,
        incoming: List<ScenarioBundleItemUiModel>,
        planItems: List<ScenarioPlanItemUiModel>,
    ): List<ScenarioBundleItemUiModel> {
        if (incoming.isEmpty()) {
            return orderScenarioBundleItems(existing, planItems)
        }
        if (existing.isEmpty()) {
            return orderScenarioBundleItems(incoming, planItems)
        }
        val incomingBySku = incoming.associateBy { it.skuId }
        val merged = existing.map { item -> incomingBySku[item.skuId] ?: item }.toMutableList()
        val seen = merged.map { it.skuId }.toMutableSet()
        incoming.forEach { item ->
            if (item.skuId !in seen) {
                merged += item
                seen += item.skuId
            }
        }
        return orderScenarioBundleItems(merged, planItems)
    }

    private fun orderScenarioBundleItems(
        items: List<ScenarioBundleItemUiModel>,
        planItems: List<ScenarioPlanItemUiModel>,
    ): List<ScenarioBundleItemUiModel> {
        if (items.isEmpty() || planItems.isEmpty()) {
            return items
        }
        val orderBySku = planItems.mapIndexedNotNull { index, item ->
            item.skuId?.takeIf { it.isNotBlank() }?.let { it to index }
        }.toMap()
        val orderByRole = planItems.mapIndexed { index, item -> item.roleName to index }.toMap()
        return items
            .mapIndexed { index, item -> index to item }
            .sortedWith(
                compareBy<Pair<Int, ScenarioBundleItemUiModel>> {
                    orderBySku[it.second.skuId] ?: orderByRole[it.second.roleName] ?: Int.MAX_VALUE
                }.thenBy { it.first }
            )
            .map { it.second }
    }

    private fun updateRecommendationSection(
        incoming: RecommendationSectionUiModel,
        update: (RecommendationSectionUiModel) -> RecommendationSectionUiModel,
    ) {
        val current = _recommendationSections.value
        val index = current.indexOfFirst { it.stableKey == incoming.stableKey }
        val nextSections = if (index >= 0) {
            current.mapIndexed { itemIndex, item ->
                if (itemIndex == index) {
                    val updated = update(item)
                    updated
                        .copy(displayTitle = mergeRecommendationDisplayTitle(incoming.displayTitle, updated.displayTitle))
                        .withResolvedRecommendationTitle()
                } else {
                    item
                }
            }
        } else {
            (current + update(incoming).withResolvedRecommendationTitle()).sortedWith(
                compareBy<RecommendationSectionUiModel> { it.sectionIndex }.thenBy { it.skuId }
            )
        }
        _recommendationSections.value = nextSections
        logRecommendationUiState(incoming)
    }

    private fun logRecommendationUiState(incoming: RecommendationSectionUiModel) {
        if (incoming.product == null && !incoming.done) {
            return
        }
        val section = _recommendationSections.value.firstOrNull { it.stableKey == incoming.stableKey } ?: return
        Log.d(
            STREAM_DEBUG_TAG,
            "[recommendation_ui_state] stableKey=${section.stableKey} sectionIndex=${section.sectionIndex} " +
                "skuId=${section.skuId} displayTitle='${section.displayTitle}' " +
                "recommendReasonLength=${section.recommendReason.length} hasProduct=${section.product != null}",
        )
    }

    private fun RecommendationSectionUiModel.withResolvedRecommendationTitle(): RecommendationSectionUiModel {
        val resolvedTitle = resolveRecommendationDisplayTitle(this)
        val resolvedReason = recommendReason
            .ifBlank { text }
            .ifBlank { reason.orEmpty() }
            .ifBlank { product?.recommendReason.orEmpty() }
            .sanitizeRecommendReason()
        val resolvedText = text.ifBlank { resolvedReason }
        val resolvedDisplayText = when {
            displayText.isNotBlank() -> displayText
            done -> resolvedText
            else -> ""
        }
        return copy(
            displayTitle = resolvedTitle,
            recommendReason = resolvedReason,
            text = resolvedText,
            displayText = resolvedDisplayText,
        )
    }

    private fun resolveRecommendationDisplayTitle(
        section: RecommendationSectionUiModel,
    ): String {
        val product = section.product
        val title = listOf(
            section.displayTitle,
            product?.recommendationDisplayTitle,
            product?.recommendTitle,
            product?.presentation?.title,
            product?.presentation?.shortTitle,
        ).firstNotNullOfOrNull { it.cleanRecommendationTitle(product) }
        return title.orEmpty()
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

    private fun String.isGeneratedRecommendationFallbackTitle(): Boolean {
        return this == "稳妥选择" ||
            this == "适合当前需求的稳妥选择" ||
            this.endsWith("里的稳妥选择")
    }

    private fun buildRecommendationDisplayTitle(section: RecommendationSectionUiModel): String {
        val product = section.product
        val context = listOf(
            _messages.value.lastOrNull { it.isUser && it.turnId == section.turnId }?.content,
            section.text,
            section.reason,
            product?.displayReason,
            product?.productHighlight,
            product?.highlightDetail,
            product?.tags?.joinToString(" "),
            product?.matchedReasons?.joinToString(" "),
            product?.suitableScenarios?.joinToString(" "),
            product?.targetUserTags?.joinToString(" "),
            product?.category,
            product?.subCategory,
            product?.brand,
        )
            .filterNotNull()
            .joinToString(" ")
            .lowercase()

        val scenario = when {
            context.hasAny("通勤", "上班", "日常") && context.hasAny("户外", "运动", "海边", "旅行", "军训") ->
                "通勤户外兼顾"
            context.hasAny("敏感", "敏感肌", "孕", "儿童", "温和") -> "敏感肌更友好"
            context.hasAny("补涂", "便携", "随身", "小支", "小瓶") -> "随身补涂方便"
            context.hasAny("预算", "性价比", "平价", "便宜", "学生") -> "预算内更稳妥"
            context.hasAny("户外", "运动", "海边", "旅行", "军训") -> "户外防护更安心"
            context.hasAny("通勤", "上班", "日常") -> "通勤日常适用"
            context.hasAny("干皮", "保湿", "滋润") -> "干皮保湿兼顾"
            context.hasAny("油皮", "混油", "控油", "清爽", "不黏") -> "清爽肤感优先"
            else -> ""
        }
        val advantage = when {
            context.hasAny("防水", "防汗", "耐汗", "遇水") -> "防水防汗选择"
            context.hasAny("清爽", "控油", "不黏", "轻薄", "水感") -> "清爽肤感选择"
            context.hasAny("温和", "敏感", "无酒精", "低刺激") -> "温和防护选择"
            context.hasAny("高倍", "spf50", "pa++++", "长效", "强防护") -> "高倍防护选择"
            context.hasAny("保湿", "滋润", "修护") -> "兼顾保湿选择"
            product?.category?.isNotBlank() == true -> "${product.category}选择"
            else -> "稳妥选择"
        }
        return if (scenario.isBlank() || advantage.startsWith(scenario)) {
            advantage
        } else {
            "${scenario}的$advantage"
        }
    }

    private fun String.hasAny(vararg keywords: String): Boolean {
        return keywords.any { keyword -> contains(keyword, ignoreCase = true) }
    }

    private fun upsertSpecSelection(selection: SpecSelectionUiModel) {
        val current = _specSelections.value
        val index = current.indexOfFirst { it.stableKey == selection.stableKey }
        _specSelections.value = if (index >= 0) {
            current.mapIndexed { itemIndex, item ->
                if (itemIndex == index) {
                    selection.copy(
                        selectedSkuId = item.selectedSkuId ?: selection.selectedSkuId,
                        completed = item.completed || selection.completed,
                        successText = item.successText ?: selection.successText,
                        errorText = selection.errorText ?: item.errorText,
                        hideOptions = item.hideOptions || selection.hideOptions,
                    )
                } else {
                    item
                }
            }
        } else {
            current + selection
        }
    }

    private fun markSpecSelectionCompleted(
        selection: SpecSelectionUiModel,
        option: SpecSelectionOptionUiModel,
        successText: String,
    ) {
        _specSelections.value = _specSelections.value.map { item ->
            if (item.stableKey == selection.stableKey) {
                item.copy(
                    selectedSkuId = option.skuId,
                    completed = true,
                    successText = successText,
                    errorText = null,
                    hideOptions = true,
                )
            } else {
                item
            }
        }
    }

    private fun markSpecSelectionError(selection: SpecSelectionUiModel, errorText: String) {
        _specSelections.value = _specSelections.value.map { item ->
            if (item.stableKey == selection.stableKey) {
                item.copy(errorText = errorText)
            } else {
                item
            }
        }
    }

    private fun clearSpecSelectionError(selection: SpecSelectionUiModel) {
        _specSelections.value = _specSelections.value.map { item ->
            if (item.stableKey == selection.stableKey && item.errorText != null) {
                item.copy(errorText = null)
            } else {
                item
            }
        }
    }

    private fun buildSpecSelectionSuccessText(
        selection: SpecSelectionUiModel,
        option: SpecSelectionOptionUiModel,
    ): String {
        val specText = option.specText.trim()
        return if (specText.isBlank()) {
            "已加入购物车：${selection.productName}"
        } else {
            "已加入购物车：${selection.productName}，$specText"
        }
    }

    private fun appendSystemCartMessage(turnId: String, content: String) {
        val current = _messages.value
        val index = current.indexOfLast { message -> !message.isUser && message.turnId == turnId }
        if (index >= 0) {
            _messages.value = current.mapIndexed { itemIndex, message ->
                if (itemIndex == index && !message.content.contains(content)) {
                    message.copy(
                        content = listOf(message.content, content)
                            .filter { it.isNotBlank() }
                            .joinToString("\n"),
                        isStreaming = false,
                    )
                } else {
                    message
                }
            }
        } else {
            _messages.value = current + ChatMessageUiModel(
                id = "assistant-cart-${System.currentTimeMillis()}",
                turnId = turnId,
                content = content,
                isUser = false,
                isStreaming = false,
            )
        }
    }

    private fun ProductUiModel.toSpecSelection(turnId: String): SpecSelectionUiModel {
        return SpecSelectionUiModel(
            id = "spec-$skuId",
            turnId = turnId,
            productId = skuId,
            productName = displayTitle,
            imageUrl = imageUrl,
            quantity = 1,
            options = skus.map { sku ->
                SpecSelectionOptionUiModel(
                    productId = this.skuId,
                    skuId = sku.skuId,
                    specText = sku.properties.toSpecSummary().orEmpty().ifBlank { sku.skuId },
                    selectedSpecs = sku.properties,
                    price = sku.price,
                    stock = stock,
                    available = stock > 0,
                )
            },
        )
    }

    private fun Map<String, String>.toSpecSummary(): String? {
        return entries
            .filter { it.key.isNotBlank() && it.value.isNotBlank() }
            .sortedBy { it.key }
            .joinToString(" · ") { it.value.trim() }
            .takeIf { it.isNotBlank() }
    }

    private fun markInterruptedSections() {
        val activeTurnId = currentTurnId
        _recommendationSections.value = _recommendationSections.value.map { section ->
            if (section.done || (!activeTurnId.isNullOrBlank() && section.turnId != activeTurnId)) {
                section
            } else {
                val stoppedText = if (section.text.isBlank()) {
                    "生成已停止"
                } else {
                    "${section.text}\n生成已停止"
                }
                section.copy(text = stoppedText, displayText = stoppedText, done = true)
            }
        }
    }

    private fun flushRecommendationTypewriters() {
        _recommendationSections.value = _recommendationSections.value.map { section ->
            if (section.text == section.displayText) {
                section
            } else {
                section.copy(displayText = section.text)
            }
        }
    }

    private fun cancelRecommendationTypewriters() {
        recommendationTypewriterJobs.values.forEach { job -> job.cancel() }
        recommendationTypewriterJobs.clear()
    }

    private fun cancelRecommendationTypewritersForTurn(turnId: String?) {
        if (turnId.isNullOrBlank()) {
            cancelRecommendationTypewriters()
            return
        }
        val prefix = "$turnId-"
        recommendationTypewriterJobs.keys
            .filter { key -> key.startsWith(prefix) }
            .forEach { key -> recommendationTypewriterJobs.remove(key)?.cancel() }
    }

    private fun startElapsedTicker() {
        stopElapsedTicker()
        elapsedTickerJob = viewModelScope.launch {
            while (_isStreaming.value) {
                val current = _thinking.value
                if (current.status == AssistantThinkingStatus.Running || current.status == AssistantThinkingStatus.Generating) {
                    _thinking.value = current.copy(totalElapsedMs = currentElapsedMs())
                }
                delay(100)
            }
        }
    }

    private fun stopElapsedTicker() {
        elapsedTickerJob?.cancel()
        elapsedTickerJob = null
    }

    private fun currentElapsedMs(): Long {
        if (currentRequestStartElapsedMs <= 0L) {
            return 0L
        }
        return (SystemClock.elapsedRealtime() - currentRequestStartElapsedMs).coerceAtLeast(0L)
    }

    private fun defaultProcessStages(): List<AssistantProcessStageUiModel> = listOf(
        AssistantProcessStageUiModel(
            stageId = "need_understanding",
            displayLabel = "理解你的需求",
        ),
        AssistantProcessStageUiModel(
            stageId = "constraint_confirmation",
            displayLabel = "确认预算和使用场景",
        ),
        AssistantProcessStageUiModel(
            stageId = "product_filtering",
            displayLabel = "筛选符合条件的商品",
        ),
        AssistantProcessStageUiModel(
            stageId = "candidate_matching",
            displayLabel = "比较候选商品的匹配程度",
        ),
        AssistantProcessStageUiModel(
            stageId = "recommendation_plan",
            displayLabel = "形成个性化推荐方案",
        ),
        AssistantProcessStageUiModel(
            stageId = "response_generation",
            displayLabel = "生成推荐结论",
        ),
    )

    private fun List<AssistantProcessStageUiModel>.markStageRunning(
        stageId: String,
        startedElapsedMs: Long,
        summary: String? = null,
    ): List<AssistantProcessStageUiModel> = map { stage ->
        if (stage.stageId == stageId) {
            stage.copy(
                status = AssistantProcessStageStatus.Running,
                startedElapsedMs = startedElapsedMs,
                summary = summary,
            )
        } else {
            stage
        }
    }

    private fun AssistantProcessStageUiModel.complete(
        summary: String? = null,
    ): AssistantProcessStageUiModel {
        if (status == AssistantProcessStageStatus.Completed) {
            return copy(summary = summary ?: this.summary)
        }
        return copy(
            status = AssistantProcessStageStatus.Completed,
            summary = summary ?: this.summary,
        )
    }

    private fun completeAllStages(
        stages: List<AssistantProcessStageUiModel>,
    ): List<AssistantProcessStageUiModel> {
        return stages.map { stage -> stage.complete() }
    }

    private fun mapProgressStage(rawStageId: String?, fallbackText: String?): String {
        val raw = rawStageId.orEmpty()
        return when (raw) {
            "intent_understanding",
            "cart_intent_understanding" -> "need_understanding"
            "constraint_extraction",
            "memory_context",
            "cart_inventory_check",
            "cart_checkout_processing" -> "constraint_confirmation"
            "retrieval",
            "cart_updating",
            "multimodal_processing",
            "image_analysis" -> "product_filtering"
            "selection_rerank",
            "product_postprocessing",
            "cart_completion" -> "candidate_matching"
            "response_composition" -> "recommendation_plan"
            "response_generation",
            "generation" -> "response_generation"
            else -> mapProgressText(fallbackText)
        }
    }

    private fun mapProgressText(text: String?): String {
        val value = text.orEmpty()
        return when {
            value.contains("预算") || value.contains("场景") || value.contains("条件") || value.contains("偏好") -> "constraint_confirmation"
            value.contains("商品库") || value.contains("检索") || value.contains("查找") || value.contains("筛选") -> "product_filtering"
            value.contains("比较") || value.contains("候选") || value.contains("排序") || value.contains("匹配") -> "candidate_matching"
            value.contains("整理") || value.contains("推荐理由") || value.contains("商品卡片") -> "recommendation_plan"
            value.contains("生成") || value.contains("结论") || value.contains("回复") -> "response_generation"
            else -> "need_understanding"
        }
    }

    private fun replaceFinalAnswer(text: String) {
        if (text.isBlank()) {
            return
        }
        val messageId = ensureAssistantMessage()
        _answer.value = text
        updateAssistantMessage(messageId) { message ->
            message.copy(
                content = text,
                isStreaming = false,
                thinking = snapshotCurrentThinking(),
            )
        }
    }

    private fun refreshCartCount() {
        viewModelScope.launch {
            _cartItemCount.value = runCatching { repository.getCart().totalItems }.getOrDefault(0)
        }
    }
}
