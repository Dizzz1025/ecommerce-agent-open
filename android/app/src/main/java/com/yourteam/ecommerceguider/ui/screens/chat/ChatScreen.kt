package com.yourteam.ecommerceguider.ui.screens.chat

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
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
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.yourteam.ecommerceguider.ui.components.ChatBubble
import com.yourteam.ecommerceguider.ui.components.ChatInputBar
import com.yourteam.ecommerceguider.ui.components.SpatialAmbientBlue
import com.yourteam.ecommerceguider.ui.components.SpatialAmbientSilver
import com.yourteam.ecommerceguider.ui.components.SpatialAmbientViolet
import com.yourteam.ecommerceguider.ui.components.SpatialBackgroundBrush
import com.yourteam.ecommerceguider.ui.screens.chat.components.AssistantAnswerIntroCard
import com.yourteam.ecommerceguider.ui.screens.chat.components.CartCheckoutBar
import com.yourteam.ecommerceguider.ui.screens.chat.components.EmptyProductsCard
import com.yourteam.ecommerceguider.ui.screens.chat.components.FinalComparisonSummary
import com.yourteam.ecommerceguider.ui.screens.chat.components.FollowUpSuggestionChips
import com.yourteam.ecommerceguider.ui.screens.chat.components.GuideTopBar
import com.yourteam.ecommerceguider.ui.screens.chat.components.HistoryRequestsDialog
import com.yourteam.ecommerceguider.ui.screens.chat.components.ProductCompareCard
import com.yourteam.ecommerceguider.ui.screens.chat.components.RecommendationSection
import com.yourteam.ecommerceguider.ui.screens.chat.components.SpecSelectionCard
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
    val recommendationSections by viewModel.recommendationSections.collectAsState()
    val specSelections by viewModel.specSelections.collectAsState()
    val activeProductCardSpecSelection by viewModel.activeProductCardSpecSelection.collectAsState()
    val activeTurnId by viewModel.activeTurnId.collectAsState()
    val cartItemCount by viewModel.cartItemCount.collectAsState()
    val isStreaming by viewModel.isStreaming.collectAsState()
    val errorMessage by viewModel.errorMessage.collectAsState()
    val snackbarHostState = remember { SnackbarHostState() }
    val scope = rememberCoroutineScope()
    val activeRecommendationSections = remember(recommendationSections, activeTurnId) {
        recommendationSections.filter { section -> section.turnId == activeTurnId }
    }
    val sectionsByTurn = remember(recommendationSections) {
        recommendationSections.groupBy { section -> section.turnId }
    }
    val specSelectionsByTurn = remember(specSelections) {
        specSelections.groupBy { selection -> selection.turnId }
    }
    val visibleProducts = if (activeRecommendationSections.isNotEmpty()) {
        activeRecommendationSections.mapNotNull { it.product }
    } else {
        products
    }
    val hasActiveAssistant = messages.any { message ->
        !message.isUser && message.turnId == activeTurnId
    }
    val hasResultMode = isStreaming ||
        answer.isNotBlank() ||
        products.isNotEmpty() ||
        recommendationSections.isNotEmpty() ||
        specSelections.isNotEmpty() ||
        !errorMessage.isNullOrBlank()
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

    LaunchedEffect(visibleProducts) {
        showCompare = false
        if (visibleProducts.isNotEmpty()) {
            thinkingExpanded = false
        }
    }

    LaunchedEffect(answer) {
        if (answer.isNotBlank()) {
            thinkingExpanded = false
        }
    }

    LaunchedEffect(isStreaming) {
        if (isStreaming && products.isEmpty() && answer.isBlank()) {
            thinkingExpanded = true
        }
    }

    if (showHistory) {
        HistoryRequestsDialog(
            messages = messages,
            recommendationSections = recommendationSections,
            onProductClick = onProductClick,
            onAddToCart = viewModel::addProductCardToCart,
            activeSpecSelection = activeProductCardSpecSelection,
            onSpecOptionClick = viewModel::addSelectedSpecToCart,
            onDismiss = { showHistory = false },
        )
    }

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(SpatialBackgroundBrush),
    ) {
        Box(
            modifier = Modifier
                .size(500.dp)
                .offset(x = (-190).dp, y = (-34).dp)
                .background(SpatialAmbientBlue),
        )
        Box(
            modifier = Modifier
                .size(480.dp)
                .offset(x = 118.dp, y = 126.dp)
                .background(SpatialAmbientViolet),
        )
        Box(
            modifier = Modifier
                .size(380.dp)
                .offset(x = (-18).dp, y = 474.dp)
                .background(SpatialAmbientSilver),
        )
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
                        .imePadding()
                        .padding(horizontal = 14.dp, vertical = 14.dp),
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
            containerColor = Color.Transparent,
        ) { innerPadding ->
            LazyColumn(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(innerPadding)
                    .padding(horizontal = 16.dp),
                contentPadding = PaddingValues(top = 18.dp, bottom = 28.dp),
                verticalArrangement = Arrangement.spacedBy(22.dp),
            ) {
                if (showWelcome) {
                    item { WelcomeCard() }
                } else {
                    messages.forEach { message ->
                        item(key = message.id) {
                            ChatBubble(message = message)
                        }
                        if (!message.isUser) {
                            if (message.turnId == activeTurnId) {
                                item(key = "thinking-${message.turnId}") {
                                    AssistantAnswerIntroCard(
                                        thinking = thinking,
                                        isStreaming = isStreaming,
                                        answer = answer,
                                        errorMessage = errorMessage,
                                        products = visibleProducts,
                                        thinkingExpanded = thinkingExpanded,
                                        onToggleThinking = { thinkingExpanded = !thinkingExpanded },
                                    )
                                }
                            }
                            val turnSpecSelections = specSelectionsByTurn[message.turnId].orEmpty()
                            turnSpecSelections.forEach { selection ->
                                item(key = selection.stableKey) {
                                    SpecSelectionCard(
                                        selection = selection,
                                        onOptionClick = { option ->
                                            viewModel.addSelectedSpecToCart(selection, option)
                                        },
                                    )
                                }
                            }
                            val turnSections = sectionsByTurn[message.turnId].orEmpty()
                            if (turnSections.isNotEmpty()) {
                                turnSections.forEach { section ->
                                    item(key = section.stableKey) {
                                        RecommendationSection(
                                            section = section,
                                            totalCount = turnSections.size,
                                            onProductClick = onProductClick,
                                            onAddToCart = viewModel::addProductCardToCart,
                                            activeSpecSelection = activeProductCardSpecSelection,
                                            onSpecOptionClick = viewModel::addSelectedSpecToCart,
                                        )
                                    }
                                }
                                val turnProducts = turnSections.mapNotNull { it.product }
                                if (message.turnId == activeTurnId && turnProducts.isNotEmpty()) {
                                    item(key = "summary-${message.turnId}") {
                                        FinalComparisonSummary(products = turnProducts)
                                    }
                                    if (turnProducts.size >= 2) {
                                        item(key = "followups-${message.turnId}") {
                                            FollowUpSuggestionChips(
                                                products = turnProducts,
                                                onSend = viewModel::sendMessage,
                                                onCompare = { showCompare = !showCompare },
                                            )
                                        }
                                        if (showCompare) {
                                            item(key = "compare-${message.turnId}") {
                                                ProductCompareCard(products = turnProducts)
                                            }
                                        }
                                    }
                                }
                            } else if (message.turnId == activeTurnId && products.isNotEmpty()) {
                                products.forEachIndexed { index, product ->
                                    item(key = "product-${message.turnId}-${product.skuId}") {
                                        RecommendationSection(
                                            product = product,
                                            index = index,
                                            totalCount = products.size,
                                            onProductClick = onProductClick,
                                            onAddToCart = viewModel::addProductCardToCart,
                                            activeSpecSelection = activeProductCardSpecSelection,
                                            onSpecOptionClick = viewModel::addSelectedSpecToCart,
                                        )
                                    }
                                }
                                item(key = "summary-${message.turnId}") {
                                    FinalComparisonSummary(products = products)
                                }
                                if (products.size >= 2) {
                                    item(key = "followups-${message.turnId}") {
                                        FollowUpSuggestionChips(
                                            products = products,
                                            onSend = viewModel::sendMessage,
                                            onCompare = { showCompare = !showCompare },
                                        )
                                    }
                                    if (showCompare) {
                                        item(key = "compare-${message.turnId}") {
                                            ProductCompareCard(products = products)
                                        }
                                    }
                                }
                            } else if (message.turnId == activeTurnId && !isStreaming && answer.isNotBlank()) {
                                item(key = "empty-products-${message.turnId}") { EmptyProductsCard() }
                            }
                        }
                    }
                }
                if (!showWelcome && !hasActiveAssistant && (isStreaming || !errorMessage.isNullOrBlank())) {
                    item(key = "thinking-active") {
                        AssistantAnswerIntroCard(
                            thinking = thinking,
                            isStreaming = isStreaming,
                            answer = answer,
                            errorMessage = errorMessage,
                            products = visibleProducts,
                            thinkingExpanded = thinkingExpanded,
                            onToggleThinking = { thinkingExpanded = !thinkingExpanded },
                        )
                    }
                    if (activeRecommendationSections.isNotEmpty()) {
                        activeRecommendationSections.forEach { section ->
                            item(key = section.stableKey) {
                                RecommendationSection(
                                    section = section,
                                    totalCount = activeRecommendationSections.size,
                                    onProductClick = onProductClick,
                                    onAddToCart = viewModel::addProductCardToCart,
                                    activeSpecSelection = activeProductCardSpecSelection,
                                    onSpecOptionClick = viewModel::addSelectedSpecToCart,
                                )
                            }
                        }
                    }
                }
                item { Spacer(modifier = Modifier.size(12.dp)) }
            }
        }
    }
}
