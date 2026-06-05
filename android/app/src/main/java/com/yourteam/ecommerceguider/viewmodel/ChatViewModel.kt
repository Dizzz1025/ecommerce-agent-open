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
        _isStreaming.value = false
        finishThinking()
    }

    fun toggleThinkingExpanded() {
        _thinking.value = _thinking.value.copy(expanded = !_thinking.value.expanded)
    }

    fun addToCart(skuId: String) {
        viewModelScope.launch {
            runCatching { repository.addToCart(skuId = skuId) }
                .onSuccess { snapshot ->
                    _cartItemCount.value = snapshot.totalItems
                    _cartTip.tryEmit("已加入购物车")
                }
                .onFailure { _cartTip.tryEmit("加购失败，请稍后重试") }
        }
    }

    fun clearError() {
        _errorMessage.value = null
    }

    private fun startStream(
        userMessage: String,
        initialThinking: String,
        stream: Flow<ChatStreamEvent>,
    ) {
        _products.value = emptyList()
        _answer.value = ""
        _errorMessage.value = null
        _thinking.value = AssistantThinkingUiModel(
            status = AssistantThinkingStatus.Started,
            lines = listOf(initialThinking),
            expanded = true,
        )
        _messages.value = _messages.value + ChatMessageUiModel(
            id = "user-${System.currentTimeMillis()}",
            content = userMessage,
            isUser = true,
        )
        _isStreaming.value = true

        streamJob = viewModelScope.launch {
            runCatching {
                stream.collect(::handleStreamEvent)
            }.onFailure {
                if (it is CancellationException) {
                    finishThinking()
                    _isStreaming.value = false
                    return@onFailure
                }
                _errorMessage.value = "请求失败，请检查后端服务和真机端口转发。"
                finishThinking()
                _isStreaming.value = false
            }
        }
    }

    private fun handleStreamEvent(event: ChatStreamEvent) {
        when (event.event) {
            "progress", "process" -> appendThinkingLine(event.progressText ?: "正在分析用户需求")
            "token" -> appendAnswerChunk(event.text.orEmpty())
            "product_cards", "products", "alternatives" -> _products.value = event.products
            "cart_update" -> _cartItemCount.value = event.cart?.totalItems ?: _cartItemCount.value
            "cart" -> _cartItemCount.value = event.cart?.totalItems ?: _cartItemCount.value
            "product_detail" -> event.product?.let { _products.value = listOf(it) }
            "frontend_action" -> event.navigation?.let { _navigation.tryEmit(it) }
            "turn_result" -> {
                event.text?.let { replaceAnswerIfBlank(it) }
                if (event.products.isNotEmpty()) {
                    _products.value = event.products
                }
                event.cart?.let { _cartItemCount.value = it.totalItems }
                event.navigation?.let { _navigation.tryEmit(it) }
                event.errorMessage?.let { _errorMessage.value = it }
            }
            "error" -> _errorMessage.value = event.errorMessage ?: "请求失败，请检查后端服务。"
            "done" -> {
                _isStreaming.value = false
                finishThinking()
                refreshCartCount()
            }
        }
    }

    private fun appendAnswerChunk(chunk: String) {
        if (chunk.isBlank()) {
            return
        }
        _answer.value += chunk
    }

    private fun replaceAnswerIfBlank(text: String) {
        if (_answer.value.isBlank()) {
            _answer.value = text
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

    private fun finishThinking() {
        val current = _thinking.value
        if (current.status != AssistantThinkingStatus.Idle) {
            _thinking.value = current.copy(status = AssistantThinkingStatus.Done)
        }
    }

    private fun refreshCartCount() {
        viewModelScope.launch {
            _cartItemCount.value = runCatching { repository.getCart().totalItems }.getOrDefault(0)
        }
    }
}
