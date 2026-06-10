package com.yourteam.ecommerceguider.ui.screens.chat

import android.Manifest
import android.content.pm.PackageManager
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
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
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.derivedStateOf
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.compose.LocalLifecycleOwner
import androidx.lifecycle.viewmodel.compose.viewModel
import com.yourteam.ecommerceguider.data.model.VoiceInputState
import com.yourteam.ecommerceguider.theme.AppDimensions
import com.yourteam.ecommerceguider.theme.AppRadius
import com.yourteam.ecommerceguider.theme.AppSpacing
import com.yourteam.ecommerceguider.theme.AppTypography
import com.yourteam.ecommerceguider.theme.ChatColors
import com.yourteam.ecommerceguider.ui.components.ChatBubble
import com.yourteam.ecommerceguider.ui.components.ChatInputBar
import com.yourteam.ecommerceguider.ui.screens.chat.components.AssistantAnswerIntroCard
import com.yourteam.ecommerceguider.ui.screens.chat.components.EmptyProductsCard
import com.yourteam.ecommerceguider.ui.screens.chat.components.GuideTopBar
import com.yourteam.ecommerceguider.ui.screens.chat.components.HistoryRequestsDialog
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
    val activeTurnAllowsEmptyProducts by viewModel.activeTurnAllowsEmptyProducts.collectAsState()
    val cartItemCount by viewModel.cartItemCount.collectAsState()
    val displayName by viewModel.displayName.collectAsState()
    val isStreaming by viewModel.isStreaming.collectAsState()
    val voiceInputState by viewModel.voiceInputState.collectAsState()
    val errorMessage by viewModel.errorMessage.collectAsState()
    val snackbarHostState = remember { SnackbarHostState() }
    val scope = rememberCoroutineScope()
    val context = LocalContext.current
    val lifecycleOwner = LocalLifecycleOwner.current
    val listState = rememberLazyListState()
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
    var thinkingExpanded by rememberSaveable { mutableStateOf(false) }
    var autoCollapsedThinkingTurnId by rememberSaveable { mutableStateOf<String?>(null) }
    val hasFormalAssistantOutput = answer.isNotBlank() || visibleProducts.isNotEmpty()
    val onToggleThinking = {
        thinkingExpanded = !thinkingExpanded
    }
    val voicePermissionLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.RequestPermission(),
    ) { granted ->
        if (granted) {
            viewModel.toggleVoiceRecording(context.cacheDir)
        } else {
            scope.launch { snackbarHostState.showSnackbar("需要麦克风权限才能语音输入") }
        }
    }
    val onVoiceClick = {
        if (voiceInputState is VoiceInputState.Recording) {
            viewModel.toggleVoiceRecording(context.cacheDir)
        } else {
            val granted = ContextCompat.checkSelfPermission(
                context,
                Manifest.permission.RECORD_AUDIO,
            ) == PackageManager.PERMISSION_GRANTED
            if (granted) {
                viewModel.toggleVoiceRecording(context.cacheDir)
            } else {
                voicePermissionLauncher.launch(Manifest.permission.RECORD_AUDIO)
            }
        }
    }
    val isNearBottom by remember {
        derivedStateOf {
            val layout = listState.layoutInfo
            val total = layout.totalItemsCount
            if (total == 0) {
                true
            } else {
                val lastVisible = layout.visibleItemsInfo.lastOrNull()?.index ?: 0
                lastVisible >= total - 3
            }
        }
    }

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

    DisposableEffect(lifecycleOwner) {
        val observer = LifecycleEventObserver { _, event ->
            if (event == Lifecycle.Event.ON_STOP) {
                viewModel.cancelVoiceInput()
            }
        }
        lifecycleOwner.lifecycle.addObserver(observer)
        onDispose {
            lifecycleOwner.lifecycle.removeObserver(observer)
        }
    }

    LaunchedEffect(activeTurnId, isStreaming, hasFormalAssistantOutput) {
        if (isStreaming && !hasFormalAssistantOutput) {
            thinkingExpanded = true
            autoCollapsedThinkingTurnId = null
        } else if (
            hasFormalAssistantOutput &&
            activeTurnId != null &&
            autoCollapsedThinkingTurnId != activeTurnId
        ) {
            thinkingExpanded = false
            autoCollapsedThinkingTurnId = activeTurnId
        }
    }

    LaunchedEffect(
        messages.size,
        recommendationSections.size,
        products.size,
        specSelections.size,
        answer.length / 120,
        isStreaming,
    ) {
        if (isNearBottom) {
            val lastIndex = listState.layoutInfo.totalItemsCount - 1
            if (lastIndex >= 0) {
                listState.scrollToItem(lastIndex)
            }
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
            .background(ChatColors.Background),
    ) {
        Scaffold(
            snackbarHost = { SnackbarHost(snackbarHostState) },
            topBar = {
                GuideTopBar(
                    cartItemCount = cartItemCount,
                    displayName = displayName,
                    onHistoryClick = { showHistory = true },
                    onCartClick = onCartClick,
                )
            },
            bottomBar = {
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .navigationBarsPadding()
                        .imePadding()
                        .background(ChatColors.Background)
                        .padding(horizontal = AppSpacing.Lg, vertical = 3.dp),
                ) {
                    ChatInputBar(
                        onSend = viewModel::sendMessage,
                        onStop = viewModel::stopStreaming,
                        onImageClick = onImageSearchClick,
                        onVoiceClick = onVoiceClick,
                        isStreaming = isStreaming,
                        voiceInputState = voiceInputState,
                    )
                }
            },
            containerColor = ChatColors.Background,
        ) { innerPadding ->
            LazyColumn(
                state = listState,
                modifier = Modifier
                    .fillMaxSize()
                    .padding(innerPadding)
                    .padding(horizontal = AppSpacing.Lg),
                contentPadding = PaddingValues(top = AppSpacing.Md, bottom = AppSpacing.Xl),
                verticalArrangement = Arrangement.spacedBy(AppSpacing.Md),
            ) {
                if (showWelcome) {
                    item { WelcomeCard() }
                } else {
                    messages.forEach { message ->
                        val hideActiveAssistantBubble = !message.isUser && message.turnId == activeTurnId
                        if (!hideActiveAssistantBubble) {
                            item(key = message.id) {
                                ChatBubble(message = message)
                            }
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
                                        onToggleThinking = onToggleThinking,
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
                            val turnHasValidRecommendation = turnSections.any { it.product != null } ||
                                (message.turnId == activeTurnId && products.isNotEmpty())
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
                            } else if (
                                message.turnId == activeTurnId &&
                                activeTurnAllowsEmptyProducts &&
                                !turnHasValidRecommendation &&
                                activeProductCardSpecSelection == null &&
                                turnSpecSelections.isEmpty() &&
                                !isStreaming &&
                                answer.isNotBlank()
                            ) {
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
                            onToggleThinking = onToggleThinking,
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
        if (!showWelcome && !isNearBottom) {
            Surface(
                modifier = Modifier
                    .align(Alignment.BottomCenter)
                    .padding(bottom = AppDimensions.ChatInputMinHeight + AppSpacing.Xl)
                    .clickable {
                        scope.launch {
                            val lastIndex = listState.layoutInfo.totalItemsCount - 1
                            if (lastIndex >= 0) {
                                listState.animateScrollToItem(lastIndex)
                            }
                        }
                    },
                shape = androidx.compose.foundation.shape.RoundedCornerShape(AppRadius.Pill),
                color = ChatColors.Surface,
                border = androidx.compose.foundation.BorderStroke(1.dp, ChatColors.Border),
            ) {
                Text(
                    text = "回到底部",
                    modifier = Modifier.padding(horizontal = AppSpacing.Md, vertical = AppSpacing.Sm),
                    style = AppTypography.CaptionStrong,
                    color = ChatColors.TextPrimary,
                )
            }
        }
    }
}
