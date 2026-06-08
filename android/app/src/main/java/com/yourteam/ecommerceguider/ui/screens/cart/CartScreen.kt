package com.yourteam.ecommerceguider.ui.screens.cart

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.core.tween
import androidx.compose.animation.expandVertically
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.shrinkVertically
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarDuration
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.SnackbarResult
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.runtime.snapshotFlow
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.rotate
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.yourteam.ecommerceguider.R
import com.yourteam.ecommerceguider.data.model.CartItemUiModel
import com.yourteam.ecommerceguider.theme.AppColors
import com.yourteam.ecommerceguider.theme.AppDimensions
import com.yourteam.ecommerceguider.theme.AppElevation
import com.yourteam.ecommerceguider.theme.AppMotion
import com.yourteam.ecommerceguider.theme.AppRadius
import com.yourteam.ecommerceguider.theme.AppSpacing
import com.yourteam.ecommerceguider.theme.AppTypography
import com.yourteam.ecommerceguider.ui.components.AppIconButton
import com.yourteam.ecommerceguider.ui.components.AppIconButtonStyle
import com.yourteam.ecommerceguider.ui.components.CartSummaryBar
import com.yourteam.ecommerceguider.ui.components.EmptyState
import com.yourteam.ecommerceguider.ui.components.ErrorState
import com.yourteam.ecommerceguider.ui.components.LoadingState
import com.yourteam.ecommerceguider.ui.components.OriginalPriceText
import com.yourteam.ecommerceguider.ui.components.PriceText
import com.yourteam.ecommerceguider.ui.components.ProductImage
import com.yourteam.ecommerceguider.ui.components.PriceTextLevel
import com.yourteam.ecommerceguider.ui.components.QuantityStepper
import com.yourteam.ecommerceguider.ui.components.QuantityStepperSize
import com.yourteam.ecommerceguider.ui.components.SwipeToDeleteCartItem
import com.yourteam.ecommerceguider.viewmodel.CartViewModel
import com.yourteam.ecommerceguider.viewmodel.simpleViewModelFactory
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

@Composable
fun CartScreen(
    onBack: () -> Unit,
    onCheckoutClick: () -> Unit,
    onProductClick: (String) -> Unit,
    viewModel: CartViewModel = viewModel(factory = simpleViewModelFactory { CartViewModel() }),
) {
    val cart by viewModel.cart.collectAsState()
    val isLoading by viewModel.isLoading.collectAsState()
    val errorMessage by viewModel.errorMessage.collectAsState()
    val updatingItemIds by viewModel.updatingItemIds.collectAsState()

    val snackbarHostState = remember { SnackbarHostState() }
    val scope = rememberCoroutineScope()
    val listState = rememberLazyListState()
    var openedItemId by rememberSaveable { mutableStateOf<String?>(null) }
    var removingItemIds by remember { mutableStateOf<Set<String>>(emptySet()) }

    val visibleItems = cart.items.filterNot { it.cartItemId in removingItemIds }
    val visibleQuantity = visibleItems.sumOf { it.quantity }
    val visibleTotal = visibleItems.sumOf { it.lineTotal }
    val visibleOriginalTotal = visibleItems
        .sumOf { item ->
            val original = item.originalPrice?.takeIf { it > item.price }
            (original ?: item.price) * item.quantity
        }
        .takeIf { it > visibleTotal }

    LaunchedEffect(Unit) {
        viewModel.loadCart()
    }

    LaunchedEffect(errorMessage, cart.items.isNotEmpty()) {
        if (errorMessage != null && cart.items.isNotEmpty()) {
            snackbarHostState.showSnackbar(errorMessage.orEmpty())
        }
    }

    LaunchedEffect(listState) {
        snapshotFlow { listState.isScrollInProgress }.collect { isScrolling ->
            if (isScrolling) {
                openedItemId = null
            }
        }
    }

    LaunchedEffect(viewModel) {
        viewModel.effects.collect { effect ->
            when (effect) {
                is CartUiEffect.ShowMessage -> {
                    effect.cartItemId?.let { removingItemIds -= it }
                    snackbarHostState.showSnackbar(effect.message)
                }

                is CartUiEffect.ItemRemoved -> {
                    removingItemIds -= effect.cartItemId
                    openedItemId = null
                    val result = snackbarHostState.showSnackbar(
                        message = effect.message,
                        actionLabel = "撤销",
                        duration = SnackbarDuration.Short,
                    )
                    if (result == SnackbarResult.ActionPerformed) {
                        viewModel.undoLastRemove(effect.cartItemId)
                    } else {
                        viewModel.discardLastRemoved(effect.cartItemId)
                    }
                }
            }
        }
    }

    Scaffold(
        snackbarHost = { SnackbarHost(snackbarHostState) },
        topBar = {
            CartTopBar(
                totalQuantity = visibleQuantity,
                onBack = onBack,
            )
        },
        bottomBar = {
            if (visibleItems.isNotEmpty()) {
                CartSummaryBar(
                    totalQuantity = visibleQuantity,
                    totalPrice = visibleTotal,
                    originalTotalPrice = visibleOriginalTotal,
                    enabled = visibleQuantity > 0,
                    onCheckoutClick = {
                        openedItemId = null
                        onCheckoutClick()
                    },
                )
            }
        },
        containerColor = AppColors.Background,
    ) { innerPadding ->
        when {
            isLoading && cart.items.isEmpty() -> {
                LoadingState(
                    modifier = Modifier.padding(innerPadding),
                    message = "正在加载购物车",
                )
            }

            errorMessage != null && cart.items.isEmpty() -> {
                ErrorState(
                    title = "购物车加载失败",
                    message = errorMessage,
                    actionLabel = "重试",
                    onAction = viewModel::loadCart,
                    modifier = Modifier.padding(innerPadding),
                )
            }

            visibleItems.isEmpty() -> {
                EmptyState(
                    title = "购物车还是空的",
                    message = "把喜欢的商品加入购物车后，再来这里统一结算。",
                    actionLabel = "去逛逛",
                    onAction = onBack,
                    modifier = Modifier.padding(innerPadding),
                )
            }

            else -> {
                LazyColumn(
                    state = listState,
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(innerPadding),
                    contentPadding = PaddingValues(
                        start = AppSpacing.Lg,
                        top = AppSpacing.Md,
                        end = AppSpacing.Lg,
                        bottom = AppSpacing.Xxl,
                    ),
                    verticalArrangement = Arrangement.spacedBy(AppSpacing.Md),
                ) {
                    items(
                        items = cart.items,
                        key = { it.cartItemId },
                    ) { item ->
                        CartItemCard(
                            item = item,
                            isUpdating = item.cartItemId in updatingItemIds,
                            isRemoving = item.cartItemId in removingItemIds,
                            isOpen = openedItemId == item.cartItemId,
                            onOpenRequest = { openedItemId = item.cartItemId },
                            onCloseRequest = {
                                if (openedItemId == item.cartItemId) {
                                    openedItemId = null
                                }
                            },
                            onProductClick = {
                                openedItemId = null
                                onProductClick(item.skuId)
                            },
                            onIncrease = {
                                openedItemId = null
                                viewModel.increase(item.cartItemId)
                            },
                            onDecrease = {
                                openedItemId = null
                                viewModel.decrease(item.cartItemId)
                            },
                            onDelete = {
                                openedItemId = null
                                if (item.cartItemId !in removingItemIds) {
                                    removingItemIds += item.cartItemId
                                    scope.launch {
                                        delay(AppMotion.Normal.toLong())
                                        viewModel.remove(item)
                                    }
                                }
                            },
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun CartTopBar(
    totalQuantity: Int,
    onBack: () -> Unit,
) {
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .height(AppDimensions.TopBarHeight + AppSpacing.Sm)
            .padding(horizontal = AppSpacing.Lg),
    ) {
        AppIconButton(
            onClick = onBack,
            style = AppIconButtonStyle.Surface,
            containerSize = AppDimensions.IconButtonSmall,
            hitAreaSize = AppDimensions.IconButton,
            iconSize = AppDimensions.IconSmall,
            modifier = Modifier.align(Alignment.CenterStart),
        ) {
            Icon(
                painter = painterResource(R.drawable.ic_chevron_right_20),
                contentDescription = "返回",
                modifier = Modifier.rotate(180f),
            )
        }
        Column(
            modifier = Modifier.align(Alignment.Center),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(AppSpacing.Xxs),
        ) {
            Text(
                text = "购物车",
                style = AppTypography.Title,
                color = AppColors.TextPrimary,
                maxLines = 1,
            )
            Text(
                text = "$totalQuantity 件商品",
                style = AppTypography.CaptionStrong,
                color = AppColors.TextSecondary,
                maxLines = 1,
            )
        }
    }
}

@Composable
private fun CartItemCard(
    item: CartItemUiModel,
    isUpdating: Boolean,
    isRemoving: Boolean,
    isOpen: Boolean,
    onOpenRequest: () -> Unit,
    onCloseRequest: () -> Unit,
    onProductClick: () -> Unit,
    onIncrease: () -> Unit,
    onDecrease: () -> Unit,
    onDelete: () -> Unit,
) {
    AnimatedVisibility(
        visible = !isRemoving,
        enter = fadeIn(tween(AppMotion.Normal)) + expandVertically(tween(AppMotion.Normal)),
        exit = fadeOut(tween(AppMotion.Normal)) + shrinkVertically(tween(AppMotion.Normal)),
    ) {
        SwipeToDeleteCartItem(
            isOpen = isOpen,
            onOpenRequest = onOpenRequest,
            onCloseRequest = onCloseRequest,
            onDeleteClick = onDelete,
            enabled = !isUpdating,
        ) {
            Card(
                modifier = Modifier
                    .fillMaxWidth()
                    .heightIn(min = 132.dp),
                shape = RoundedCornerShape(AppRadius.Card),
                colors = CardDefaults.cardColors(containerColor = AppColors.Surface),
                elevation = CardDefaults.cardElevation(defaultElevation = AppElevation.None),
                border = BorderStroke(1.dp, AppColors.Border),
            ) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(AppSpacing.Md),
                    verticalAlignment = Alignment.Top,
                    horizontalArrangement = Arrangement.spacedBy(AppSpacing.Md),
                ) {
                    ProductImage(
                        imageUrl = item.imageUrl,
                        contentDescription = item.name,
                        modifier = Modifier
                            .size(AppDimensions.CartImageSize)
                            .clickable(onClick = onProductClick),
                        cornerRadius = AppRadius.Medium,
                        contentScale = ContentScale.Fit,
                    )
                    Column(
                        modifier = Modifier.weight(1f),
                        verticalArrangement = Arrangement.spacedBy(AppSpacing.Xs),
                    ) {
                        Text(
                            text = item.name,
                            style = AppTypography.BodyStrong,
                            color = AppColors.TextPrimary,
                            maxLines = 2,
                            overflow = TextOverflow.Ellipsis,
                            modifier = Modifier.clickable(onClick = onProductClick),
                        )
                        item.specSummary?.takeIf { it.isNotBlank() }?.let { spec ->
                            Text(
                                text = spec,
                                style = AppTypography.BodySmall,
                                color = AppColors.TextSecondary,
                                maxLines = 1,
                                overflow = TextOverflow.Ellipsis,
                            )
                        }
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.spacedBy(AppSpacing.Sm),
                        ) {
                            PriceText(
                                price = item.price,
                                level = PriceTextLevel.Normal,
                                modifier = Modifier.weight(1f, fill = false),
                            )
                            item.originalPrice
                                ?.takeIf { it > item.price }
                                ?.let { original ->
                                    OriginalPriceText(price = original)
                                }
                        }
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            verticalAlignment = Alignment.CenterVertically,
                        ) {
                            Spacer(modifier = Modifier.weight(1f))
                            QuantityStepper(
                                quantity = item.quantity,
                                enabled = !isUpdating,
                                loading = isUpdating,
                                minimum = 1,
                                maximum = item.stock?.takeIf { it > 0 },
                                onIncrease = onIncrease,
                                onDecrease = onDecrease,
                                size = QuantityStepperSize.Compact,
                            )
                        }
                    }
                }
            }
        }
    }
}
