package com.yourteam.ecommerceguider.ui.screens.chat

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.yourteam.ecommerceguider.ui.components.ChatBubble
import com.yourteam.ecommerceguider.ui.components.ChatInputBar
import com.yourteam.ecommerceguider.ui.screens.chat.components.AssistantAnswerIntroCard
import com.yourteam.ecommerceguider.ui.screens.chat.components.CartCheckoutBar
import com.yourteam.ecommerceguider.ui.screens.chat.components.EmptyProductsCard
import com.yourteam.ecommerceguider.ui.screens.chat.components.FinalComparisonSummary
import com.yourteam.ecommerceguider.ui.screens.chat.components.FollowUpSuggestionChips
import com.yourteam.ecommerceguider.ui.screens.chat.components.GuideTopBar
import com.yourteam.ecommerceguider.ui.screens.chat.components.HistoryRequestsDialog
import com.yourteam.ecommerceguider.ui.screens.chat.components.ProductCompareCard
import com.yourteam.ecommerceguider.ui.screens.chat.components.RecommendationSection
import com.yourteam.ecommerceguider.ui.screens.chat.components.RequirementSummaryCard
import com.yourteam.ecommerceguider.ui.screens.chat.components.WelcomeCard
import com.yourteam.ecommerceguider.viewmodel.ChatViewModel
import com.yourteam.ecommerceguider.viewmodel.simpleViewModelFactory
import kotlinx.coroutines.launch

@Composable
fun ChatScreen(
    onProductClick: (String) -> Unit,
    onCartClick: () -> Unit,
    onCheckoutClick: () -> Unit,
    onImageSearchClick: () -> Unit,
    onAddressClick: () -> Unit,
    viewModel: ChatViewModel = viewModel(factory = simpleViewModelFactory { ChatViewModel() }),
) {
    val messages by viewModel.messages.collectAsState()
    val thinking by viewModel.thinking.collectAsState()
    val answer by viewModel.answer.collectAsState()
    val products by viewModel.products.collectAsState()
    val cartItemCount by viewModel.cartItemCount.collectAsState()
    val isStreaming by viewModel.isStreaming.collectAsState()
    val errorMessage by viewModel.errorMessage.collectAsState()
    val snackbarHostState = remember { SnackbarHostState() }
    val scope = rememberCoroutineScope()
    val hasResultMode = isStreaming || answer.isNotBlank() || products.isNotEmpty() || !errorMessage.isNullOrBlank()
    val activeRequirement = messages
        .asReversed()
        .firstOrNull { it.isUser && isEffectiveRequirement(it.content) }
        ?.content
    val showWelcome = messages.isEmpty() && !hasResultMode
    var showHistory by remember { mutableStateOf(false) }
    var showCompare by remember { mutableStateOf(false) }
    var thinkingExpanded by remember { mutableStateOf(false) }

    LaunchedEffect(viewModel) {
        viewModel.navigation.collect { navigation ->
            when (navigation.targetPage) {
                "product_detail_page" -> navigation.skuId?.let(onProductClick)
                "cart_page" -> onCartClick()
                "checkout_page" -> onCheckoutClick()
            }
        }
    }

    LaunchedEffect(viewModel) {
        viewModel.cartTip.collect { snackbarHostState.showSnackbar(it) }
    }

    LaunchedEffect(errorMessage) {
        errorMessage?.let { snackbarHostState.showSnackbar(it) }
    }

    LaunchedEffect(products) {
        showCompare = false
    }

    LaunchedEffect(answer) {
        if (answer.isNotBlank()) {
            thinkingExpanded = false
        }
    }

    if (showHistory) {
        HistoryRequestsDialog(
            messages = messages,
            onDismiss = { showHistory = false },
        )
    }

    Scaffold(
        snackbarHost = { SnackbarHost(snackbarHostState) },
        topBar = {
            GuideTopBar(
                cartItemCount = cartItemCount,
                historyCount = messages.count { it.isUser },
                onHistoryClick = { showHistory = true },
                onCartClick = onCartClick,
                onAddressClick = onAddressClick,
            )
        },
        bottomBar = {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .navigationBarsPadding()
                    .imePadding(),
            ) {
                CartCheckoutBar(
                    cartItemCount = cartItemCount,
                    onCartClick = onCartClick,
                    onCheckoutClick = onCheckoutClick,
                )
                ChatInputBar(
                    onSend = viewModel::sendMessage,
                    onStop = viewModel::stopStreaming,
                    onImageClick = onImageSearchClick,
                    onVoiceClick = { scope.launch { snackbarHostState.showSnackbar("语音输入暂未接入") } },
                    isStreaming = isStreaming,
                )
            }
        },
        containerColor = MaterialTheme.colorScheme.background,
    ) { innerPadding ->
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .padding(horizontal = 16.dp),
            contentPadding = PaddingValues(top = 14.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            if (showWelcome) {
                item { WelcomeCard() }
            } else if (hasResultMode) {
                activeRequirement?.let { requirement ->
                    item(key = "current-requirement") {
                        RequirementSummaryCard(
                            content = requirement,
                            onModifyClick = {
                                scope.launch { snackbarHostState.showSnackbar("可以直接在底部输入新的筛选条件") }
                            },
                        )
                    }
                }
            } else {
                items(messages, key = { it.id }) { message ->
                    ChatBubble(message = message)
                }
            }
            item {
                AssistantAnswerIntroCard(
                    thinking = thinking,
                    isStreaming = isStreaming,
                    answer = answer,
                    errorMessage = errorMessage,
                    products = products,
                    thinkingExpanded = thinkingExpanded,
                    onToggleThinking = { thinkingExpanded = !thinkingExpanded },
                )
            }
            if (products.isNotEmpty()) {
                itemsIndexed(products, key = { _, product -> product.skuId }) { index, product ->
                    RecommendationSection(
                        product = product,
                        index = index,
                        totalCount = products.size,
                        onProductClick = onProductClick,
                        onAddToCart = viewModel::addToCart,
                    )
                }
                item { FinalComparisonSummary(products = products) }
                if (products.size >= 2) {
                    item {
                        FollowUpSuggestionChips(
                            products = products,
                            onSend = viewModel::sendMessage,
                            onCompare = { showCompare = !showCompare },
                        )
                    }
                    if (showCompare) {
                        item { ProductCompareCard(products = products) }
                    }
                }
            } else if (!isStreaming && answer.isNotBlank()) {
                item { EmptyProductsCard() }
            }
            item { Spacer(modifier = Modifier.size(12.dp)) }
        }
    }
}

private fun isEffectiveRequirement(content: String): Boolean {
    val normalized = content.trim()
    if (normalized.isBlank()) {
        return false
    }
    val actionOnly = setOf("换一批", "再来一批", "重新推荐", "对比这几款", "查看差异")
    if (normalized in actionOnly) {
        return false
    }
    return !normalized.startsWith("正在") &&
        !normalized.contains("商品库") &&
        !normalized.contains("生成导购建议")
}
