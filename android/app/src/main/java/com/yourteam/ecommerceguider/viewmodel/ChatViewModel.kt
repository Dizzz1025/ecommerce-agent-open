package com.yourteam.ecommerceguider.viewmodel

import android.content.ContentResolver
import android.net.Uri
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.yourteam.ecommerceguider.data.model.AssistantThinkingStatus
import com.yourteam.ecommerceguider.data.model.AssistantThinkingUiModel
import com.yourteam.ecommerceguider.data.model.BackendNavigationUiModel
import com.yourteam.ecommerceguider.data.model.ChatMessageUiModel
import com.yourteam.ecommerceguider.data.model.ChatStreamEvent
import com.yourteam.ecommerceguider.data.model.ProductUiModel
import com.yourteam.ecommerceguider.data.model.RecommendationSectionUiModel
import com.yourteam.ecommerceguider.data.model.SpecSelectionOptionUiModel
import com.yourteam.ecommerceguider.data.model.SpecSelectionUiModel
import com.yourteam.ecommerceguider.data.repository.ShoppingRepository
import java.util.concurrent.CancellationException
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asSharedFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

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

    private val _specSelections = MutableStateFlow<List<SpecSelectionUiModel>>(emptyList())
    val specSelections: StateFlow<List<SpecSelectionUiModel>> = _specSelections.asStateFlow()

    private val _activeProductCardSpecSelection = MutableStateFlow<SpecSelectionUiModel?>(null)
    val activeProductCardSpecSelection: StateFlow<SpecSelectionUiModel?> =
        _activeProductCardSpecSelection.asStateFlow()

    private val _activeTurnId = MutableStateFlow<String?>(null)
    val activeTurnId: StateFlow<String?> = _activeTurnId.asStateFlow()

    private val _cartItemCount = MutableStateFlow(0)
    val cartItemCount: StateFlow<Int> = _cartItemCount.asStateFlow()

    private val _isStreaming = MutableStateFlow(false)
    val isStreaming: StateFlow<Boolean> = _isStreaming.asStateFlow()

    private val _errorMessage = MutableStateFlow<String?>(null)
    val errorMessage: StateFlow<String?> = _errorMessage.asStateFlow()

    private val _cartTip = MutableSharedFlow<String>(extraBufferCapacity = 1)
    val cartTip: SharedFlow<String> = _cartTip.asSharedFlow()

    private val _navigation = MutableSharedFlow<BackendNavigationUiModel>(extraBufferCapacity = 1)
    val navigation: SharedFlow<BackendNavigationUiModel> = _navigation.asSharedFlow()

    private var streamJob: Job? = null
    private val appliedSectionDeltas = mutableSetOf<String>()
    private var currentTurnId: String? = null
    private var currentAssistantMessageId: String? = null

    init {
        refreshCartCount()
    }

    fun sendMessage(message: String) {
        if (message.isBlank() || _isStreaming.value) {
            return
        }

        startStream(
            userMessage = message.trim(),
            initialThinking = "分析用户需求",
            stream = repository.streamChat(message.trim()),
        )
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
        markInterruptedSections()
        markAssistantMessageDone()
        _isStreaming.value = false
        finishThinking()
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
                        markSpecSelectionChosen(selection, option)
                        appendSystemCartMessage(selection.turnId, "已加入购物车：${option.specText}")
                    }
                    _cartTip.tryEmit("已加入购物车：${option.specText}")
                }
                .onFailure { _cartTip.tryEmit("加购失败，请稍后重试") }
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
        val candidates = _products.value + _recommendationSections.value.mapNotNull { it.product }
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
    ) {
        val startedAt = System.currentTimeMillis()
        val turnId = "turn-local-$startedAt"
        currentTurnId = turnId
        currentAssistantMessageId = null
        _activeTurnId.value = turnId
        _products.value = emptyList()
        _answer.value = ""
        _errorMessage.value = null
        _activeProductCardSpecSelection.value = null
        appliedSectionDeltas.clear()
        _thinking.value = AssistantThinkingUiModel(
            status = AssistantThinkingStatus.Started,
            lines = listOf(initialThinking),
            expanded = true,
        )
        _messages.value = _messages.value + ChatMessageUiModel(
            id = "user-$startedAt",
            turnId = turnId,
            content = userMessage,
            isUser = true,
            timestamp = startedAt,
        )
        _isStreaming.value = true

        streamJob = viewModelScope.launch {
            runCatching {
                stream.collect(::handleStreamEvent)
            }.onFailure {
                if (it is CancellationException) {
                    finishThinking()
                    markAssistantMessageDone()
                    _isStreaming.value = false
                    return@onFailure
                }
                _errorMessage.value = "请求失败，请检查后端服务和真机端口转发。"
                finishThinking()
                markAssistantMessageDone()
                _isStreaming.value = false
            }
        }
    }

    private fun handleStreamEvent(event: ChatStreamEvent) {
        when (event.event) {
            "progress", "process" -> appendThinkingLine(event.progressText ?: "正在分析用户需求")
            "token" -> appendAnswerChunk(event.text.orEmpty())
            "recommendation_section_start" -> {
                event.recommendationSection?.let(::normalizeSectionTurnId)?.let { section ->
                    adoptTurnId(section.turnId)
                    upsertRecommendationSection(section)
                }
                collapseThinking()
            }
            "recommendation_text_delta" -> {
                event.recommendationSection?.let(::normalizeSectionTurnId)?.let { section ->
                    adoptTurnId(section.turnId)
                    appendRecommendationSectionDelta(section)
                }
                collapseThinking()
            }
            "recommendation_text_done" -> {
                event.recommendationSection?.let(::normalizeSectionTurnId)?.let { section ->
                    adoptTurnId(section.turnId)
                    finishRecommendationSection(section)
                }
                collapseThinking()
            }
            "product_card" -> {
                event.recommendationSection?.let(::normalizeSectionTurnId)?.let { section ->
                    adoptTurnId(section.turnId)
                    attachRecommendationProduct(section)
                }
                event.product?.let { _products.value = mergeProductsBySku(_products.value, listOf(it)) }
                collapseThinking()
            }
            "product_cards", "products", "alternatives" -> {
                _products.value = mergeProductsBySku(_products.value, event.products)
                mergeSectionProductSnapshots(event.products)
                if (event.products.isNotEmpty()) {
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
                event.text?.let { replaceAnswerIfBlank(it) }
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
                finishThinking()
            }
            "done" -> {
                _isStreaming.value = false
                finishThinking()
                markAssistantMessageDone()
                refreshCartCount()
            }
        }
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
            )
        }
        collapseThinking()
    }

    private fun replaceAnswerIfBlank(text: String) {
        if (text.isBlank()) {
            return
        }
        val messageId = ensureAssistantMessage()
        _answer.value = text
        updateAssistantMessage(messageId) { message ->
            message.copy(
                content = text,
                isStreaming = false,
            )
        }
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
                message.copy(isStreaming = false)
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
        _specSelections.value = _specSelections.value.map { selection ->
            if (selection.turnId == previousTurnId) {
                selection.copy(turnId = turnId)
            } else {
                selection
            }
        }
    }

    private fun appendThinkingLine(line: String) {
        if (line.isBlank()) {
            return
        }
        val current = _thinking.value
        _thinking.value = current.copy(
            status = AssistantThinkingStatus.Streaming,
            lines = (current.lines + line).distinct().takeLast(8),
        )
    }

    private fun collapseThinking() {
        val current = _thinking.value
        if (current.status != AssistantThinkingStatus.Idle) {
            _thinking.value = current.copy(
                status = AssistantThinkingStatus.Done,
                expanded = false,
            )
        }
    }

    private fun finishThinking() {
        val current = _thinking.value
        if (current.status != AssistantThinkingStatus.Idle) {
            _thinking.value = current.copy(
                status = AssistantThinkingStatus.Done,
                expanded = false,
            )
        }
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
                productName = section.productName ?: current.productName,
                brand = section.brand ?: current.brand,
            )
        }
    }

    private fun appendRecommendationSectionDelta(section: RecommendationSectionUiModel) {
        val delta = section.text.takeIf { it.isNotBlank() } ?: return
        val key = section.eventId ?: "${section.stableKey}:${delta.hashCode()}"
        if (!appliedSectionDeltas.add(key)) {
            return
        }
        updateRecommendationSection(section) { current ->
            current.copy(
                text = current.text + delta,
                productName = section.productName ?: current.productName,
                brand = section.brand ?: current.brand,
            )
        }
    }

    private fun finishRecommendationSection(section: RecommendationSectionUiModel) {
        updateRecommendationSection(section) { current ->
            val finalText = section.reason
                ?.takeIf { it.isNotBlank() }
                ?: section.text.takeIf { it.isNotBlank() }
                ?: current.text
            current.copy(
                text = finalText,
                reason = section.reason ?: current.reason,
                tradeOff = section.tradeOff ?: current.tradeOff,
                productName = section.productName ?: current.productName,
                brand = section.brand ?: current.brand,
                done = true,
            )
        }
    }

    private fun attachRecommendationProduct(section: RecommendationSectionUiModel) {
        val product = section.product
        updateRecommendationSection(section) { current ->
            val reason = section.reason
                ?: product?.presentation?.reason
                ?: current.reason
            val finalText = current.text.takeIf { it.isNotBlank() }
                ?: reason.orEmpty()
            current.copy(
                text = finalText,
                reason = reason,
                tradeOff = section.tradeOff ?: product?.presentation?.tradeOff ?: current.tradeOff,
                productName = section.productName ?: product?.displayTitleShort ?: current.productName,
                brand = section.brand ?: product?.brand ?: current.brand,
                product = product ?: current.product,
                done = true,
            )
        }
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
            )
        }
    }

    private fun updateRecommendationSection(
        incoming: RecommendationSectionUiModel,
        update: (RecommendationSectionUiModel) -> RecommendationSectionUiModel,
    ) {
        val current = _recommendationSections.value
        val index = current.indexOfFirst { it.stableKey == incoming.stableKey }
        _recommendationSections.value = if (index >= 0) {
            current.mapIndexed { itemIndex, item ->
                if (itemIndex == index) update(item) else item
            }
        } else {
            (current + update(incoming)).sortedWith(
                compareBy<RecommendationSectionUiModel> { it.sectionIndex }.thenBy { it.skuId }
            )
        }
    }

    private fun upsertSpecSelection(selection: SpecSelectionUiModel) {
        val current = _specSelections.value
        val index = current.indexOfFirst { it.stableKey == selection.stableKey }
        _specSelections.value = if (index >= 0) {
            current.mapIndexed { itemIndex, item ->
                if (itemIndex == index) {
                    selection.copy(selectedSkuId = item.selectedSkuId ?: selection.selectedSkuId)
                } else {
                    item
                }
            }
        } else {
            current + selection
        }
    }

    private fun markSpecSelectionChosen(
        selection: SpecSelectionUiModel,
        option: SpecSelectionOptionUiModel,
    ) {
        _specSelections.value = _specSelections.value.map { item ->
            if (item.stableKey == selection.stableKey) {
                item.copy(selectedSkuId = option.skuId)
            } else {
                item
            }
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
                section.copy(text = stoppedText, done = true)
            }
        }
    }

    private fun refreshCartCount() {
        viewModelScope.launch {
            _cartItemCount.value = runCatching { repository.getCart().totalItems }.getOrDefault(0)
        }
    }
}
