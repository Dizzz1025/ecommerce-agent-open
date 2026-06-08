@file:OptIn(ExperimentalMaterial3Api::class, ExperimentalLayoutApi::class)

package com.yourteam.ecommerceguider.ui.screens.product

import android.app.Activity
import android.content.Intent
import android.util.Log
import androidx.activity.compose.BackHandler
import androidx.compose.animation.core.animate
import androidx.compose.animation.core.tween
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.gestures.Orientation
import androidx.compose.foundation.gestures.draggable
import androidx.compose.foundation.gestures.rememberDraggableState
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.navigationBars
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBars
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.pager.HorizontalPager
import androidx.compose.foundation.pager.PagerState
import androidx.compose.foundation.pager.rememberPagerState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.ui.input.nestedscroll.NestedScrollConnection
import androidx.compose.ui.input.nestedscroll.NestedScrollSource
import androidx.compose.ui.input.nestedscroll.nestedScroll
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.derivedStateOf
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.runtime.SideEffect
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.draw.clipToBounds
import androidx.compose.ui.draw.rotate
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.platform.LocalView
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextDecoration
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.IntOffset
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.Velocity
import androidx.compose.ui.zIndex
import androidx.core.view.WindowCompat
import androidx.lifecycle.viewmodel.compose.viewModel
import com.yourteam.ecommerceguider.R
import com.yourteam.ecommerceguider.data.model.ProductReviewUiModel
import com.yourteam.ecommerceguider.data.model.ProductSkuUiModel
import com.yourteam.ecommerceguider.data.model.ProductUiModel
import com.yourteam.ecommerceguider.theme.AppColors
import com.yourteam.ecommerceguider.theme.AppDimensions
import com.yourteam.ecommerceguider.theme.AppElevation
import com.yourteam.ecommerceguider.theme.AppMotion
import com.yourteam.ecommerceguider.theme.AppRadius
import com.yourteam.ecommerceguider.theme.AppSpacing
import com.yourteam.ecommerceguider.theme.AppTypography
import com.yourteam.ecommerceguider.ui.components.AppIconButton
import com.yourteam.ecommerceguider.ui.components.AppIconButtonStyle
import com.yourteam.ecommerceguider.ui.components.EmptyState
import com.yourteam.ecommerceguider.ui.components.ErrorState
import com.yourteam.ecommerceguider.ui.components.LoadingState
import com.yourteam.ecommerceguider.ui.components.OriginalPriceText
import com.yourteam.ecommerceguider.ui.components.PriceText
import com.yourteam.ecommerceguider.ui.components.PriceTextLevel
import com.yourteam.ecommerceguider.ui.components.ProductImage
import com.yourteam.ecommerceguider.ui.components.ProductImagePager
import com.yourteam.ecommerceguider.ui.components.ProductBottomActionBar
import com.yourteam.ecommerceguider.ui.components.ResolvedImageSource
import com.yourteam.ecommerceguider.ui.components.TagChip
import com.yourteam.ecommerceguider.ui.components.TagChipTone
import com.yourteam.ecommerceguider.ui.components.formatPrice
import com.yourteam.ecommerceguider.viewmodel.ProductDetailViewModel
import com.yourteam.ecommerceguider.viewmodel.simpleViewModelFactory
import kotlinx.coroutines.launch
import kotlin.math.roundToInt

private const val PRODUCT_VARIANT_ITEM_INDEX = 2
private const val PRODUCT_VARIANT_ITEM_KEY = "variant-anchor"
private const val SHEET_FLING_THRESHOLD = 900f
private const val DETAIL_SHEET_DEBUG_TAG = "ProductDetailSheet"
private const val DETAIL_SHEET_DEBUG_LOGS = false
private val HERO_TITLE_DELIMITERS = arrayOf(
    "\uFF0C",
    ",",
    "\u3002",
    "\uFF1B",
    ";",
    "\u3001",
    "\uFF5C",
    "|",
    "\u2014\u2014",
    "-",
    "\uFF1A",
    ":",
)
private val PRODUCT_HERO_CORE_KEYWORDS = listOf(
    "\u9694\u79BB\u9732",
    "\u9632\u62A4\u4E73",
    "\u9632\u6652\u4E73",
    "\u9632\u6652\u971C",
    "\u9632\u6652",
    "\u7CBE\u534E\u6DB2",
    "\u7CBE\u534E",
    "\u9762\u971C",
    "\u4E73\u6DB2",
    "\u6D01\u9762\u4E73",
    "\u6D01\u9762",
    "\u723D\u80A4\u6C34",
    "\u5316\u5986\u6C34",
    "\u9762\u819C",
    "\u53E3\u7EA2",
    "\u7C89\u5E95\u6DB2",
    "\u624B\u673A",
    "\u8033\u673A",
    "\u80CC\u5305",
    "\u8DD1\u978B",
)

private enum class DetailSheetAnchor {
    Immersive,
    HalfExpanded,
    Expanded,
}

private enum class HeroImageMode {
    Scene,
    Packshot,
}

private enum class HeroImageResolution {
    Pending,
    Detail,
    Original,
    Failed,
}

private data class DetailSheetAnchors(
    val immersiveTopPx: Float,
    val halfExpandedTopPx: Float,
    val expandedTopPx: Float,
) {
    fun position(anchor: DetailSheetAnchor): Float {
        return when (anchor) {
            DetailSheetAnchor.Immersive -> immersiveTopPx
            DetailSheetAnchor.HalfExpanded -> halfExpandedTopPx
            DetailSheetAnchor.Expanded -> expandedTopPx
        }
    }

    fun nearest(positionPx: Float): DetailSheetAnchor {
        return DetailSheetAnchor.entries.minBy { anchor ->
            kotlin.math.abs(position(anchor) - positionPx)
        }
    }

    fun nextUp(anchor: DetailSheetAnchor): DetailSheetAnchor {
        return when (anchor) {
            DetailSheetAnchor.Immersive -> DetailSheetAnchor.HalfExpanded
            DetailSheetAnchor.HalfExpanded -> DetailSheetAnchor.HalfExpanded
            DetailSheetAnchor.Expanded -> DetailSheetAnchor.HalfExpanded
        }
    }

    fun nextDown(anchor: DetailSheetAnchor): DetailSheetAnchor {
        return when (anchor) {
            DetailSheetAnchor.Immersive -> DetailSheetAnchor.Immersive
            DetailSheetAnchor.HalfExpanded -> DetailSheetAnchor.Immersive
            DetailSheetAnchor.Expanded -> DetailSheetAnchor.Immersive
        }
    }
}

@Composable
fun ProductDetailScreen(
    skuId: String,
    onBack: () -> Unit,
    onCartClick: () -> Unit,
    viewModel: ProductDetailViewModel = viewModel(
        factory = simpleViewModelFactory { ProductDetailViewModel() },
    ),
) {
    val product by viewModel.product.collectAsState()
    val isLoading by viewModel.isLoading.collectAsState()
    val error by viewModel.error.collectAsState()
    val cartItemCount by viewModel.cartItemCount.collectAsState()
    val isAddingToCart by viewModel.isAddingToCart.collectAsState()
    val snackbarHostState = remember { SnackbarHostState() }
    val context = LocalContext.current
    val screenScope = rememberCoroutineScope()
    val listState = rememberLazyListState()
    var selectedSkuId by rememberSaveable(skuId) { mutableStateOf<String?>(null) }
    var selectedReviewFilter by rememberSaveable(skuId) { mutableStateOf(ReviewFilter.All) }
    var showAllReviews by rememberSaveable(skuId) { mutableStateOf(false) }
    var favorite by rememberSaveable(skuId) { mutableStateOf(false) }
    var highlightSpecs by rememberSaveable(skuId) { mutableStateOf(false) }
    val favoriteAddedMessage = stringResource(R.string.product_detail_favorite_added)
    val favoriteRemovedMessage = stringResource(R.string.product_detail_favorite_removed)

    LaunchedEffect(skuId) {
        viewModel.loadProduct(skuId)
    }

    LaunchedEffect(product?.skuId) {
        val currentProduct = product ?: return@LaunchedEffect
        selectedSkuId = currentProduct.defaultSelectedSkuId(routeSkuId = skuId)
    }

    LaunchedEffect(viewModel) {
        viewModel.effects.collect { effect ->
            when (effect) {
                is ProductDetailUiEffect.ShowMessage -> snackbarHostState.showSnackbar(effect.message)
            }
        }
    }

    val selectedSku = product?.selectedSku(selectedSkuId, routeSkuId = skuId)
    val displayPrice = selectedSku?.price ?: product?.price
    val originalPrice = product?.basePrice?.takeIf { base -> displayPrice != null && base > displayPrice }
    val canAttemptPurchase = product?.stock?.let { it > 0 } ?: false

    LaunchedEffect(selectedSkuId) {
        if (selectedSku != null) {
            highlightSpecs = false
        }
    }

    ProductDetailImmersiveScaffold(
        skuId = skuId,
        product = product,
        isLoading = isLoading,
        error = error,
        selectedSku = selectedSku,
        selectedSkuId = selectedSkuId,
        onSkuSelected = {
            selectedSkuId = it
            highlightSpecs = false
        },
        selectedReviewFilter = selectedReviewFilter,
        onReviewFilterSelected = { selectedReviewFilter = it },
        showAllReviews = showAllReviews,
        onShowAllReviewsChange = { showAllReviews = it },
        displayPrice = displayPrice,
        originalPrice = originalPrice,
        canAttemptPurchase = canAttemptPurchase,
        cartItemCount = cartItemCount,
        isAddingToCart = isAddingToCart,
        favorite = favorite,
        onFavoriteToggle = {
            favorite = !favorite
            screenScope.launch {
                snackbarHostState.showSnackbar(if (favorite) favoriteAddedMessage else favoriteRemovedMessage)
            }
        },
        highlightSpecs = highlightSpecs,
        onHighlightSpecsChange = { highlightSpecs = it },
        snackbarHostState = snackbarHostState,
        context = context,
        screenScope = screenScope,
        listState = listState,
        onBack = onBack,
        onCartClick = onCartClick,
        onLoadProduct = { viewModel.loadProduct(skuId) },
        onAddToCart = { currentProduct, currentSku -> viewModel.addToCart(currentProduct, currentSku) },
    )
    return

    fun promptForMissingSpecs(currentProduct: ProductUiModel) {
        val message = currentProduct.missingSpecPrompt(selectedSku)
        highlightSpecs = true
        screenScope.launch {
            listState.animateScrollToItem(index = PRODUCT_VARIANT_ITEM_INDEX)
            snackbarHostState.showSnackbar(message)
        }
    }

    BoxWithConstraints(modifier = Modifier.fillMaxSize()) {
        val heroHeight = (maxHeight * 0.68f).coerceIn(320.dp, 560.dp)

        Scaffold(
            snackbarHost = { SnackbarHost(snackbarHostState) },
            bottomBar = {
                ProductBottomActionBar(
                    price = displayPrice,
                    originalPrice = originalPrice,
                    cartItemCount = cartItemCount,
                    inStock = canAttemptPurchase,
                    addToCartLoading = isAddingToCart,
                    onCartClick = onCartClick,
                    onAddToCart = {
                        val currentProduct = product ?: return@ProductBottomActionBar
                        if (currentProduct.skus.isNotEmpty() && selectedSku == null) {
                            promptForMissingSpecs(currentProduct)
                        } else {
                            viewModel.addToCart(currentProduct, selectedSku)
                        }
                    },
                    onBuyNow = {
                        val currentProduct = product ?: return@ProductBottomActionBar
                        if (currentProduct.skus.isNotEmpty() && selectedSku == null) {
                            promptForMissingSpecs(currentProduct)
                        } else {
                            screenScope.launch {
                                snackbarHostState.showSnackbar("立即购买暂未接入商品详情直达流程")
                            }
                        }
                    },
                )
            },
            containerColor = AppColors.Background,
        ) { innerPadding ->
            when {
                isLoading -> {
                    LoadingState(
                        modifier = Modifier.padding(innerPadding),
                        message = "正在加载商品详情",
                    )
                }

                error != null -> {
                    ErrorState(
                        title = "商品详情加载失败",
                        message = error,
                        actionLabel = "重试",
                        onAction = { viewModel.loadProduct(skuId) },
                        modifier = Modifier.padding(innerPadding),
                    )
                }

                product == null -> {
                    EmptyState(
                        title = "未找到该商品",
                        message = "商品可能已下架或链接已失效。",
                        actionLabel = "返回",
                        onAction = onBack,
                        modifier = Modifier.padding(innerPadding),
                    )
                }

                else -> {
                    ProductDetailContent(
                        product = product!!,
                        selectedSku = selectedSku,
                        selectedSkuId = selectedSkuId,
                        onSkuSelected = {
                            selectedSkuId = it
                            highlightSpecs = false
                        },
                        selectedReviewFilter = selectedReviewFilter,
                        onReviewFilterSelected = { selectedReviewFilter = it },
                        heroHeight = heroHeight,
                        listState = listState,
                        highlightSpecs = highlightSpecs,
                        modifier = Modifier.padding(innerPadding),
                    )
                }
            }
        }

        product?.let { currentProduct ->
            FloatingProductActions(
                favorite = favorite,
                onBack = onBack,
                onFavoriteClick = {
                    favorite = !favorite
                    screenScope.launch {
                        snackbarHostState.showSnackbar(if (favorite) "已收藏" else "已取消收藏")
                    }
                },
                onShareClick = {
                    val shareText = currentProduct.shareText(selectedSku)
                    val intent = Intent(Intent.ACTION_SEND).apply {
                        type = "text/plain"
                        putExtra(Intent.EXTRA_TEXT, shareText)
                    }
                    runCatching {
                        context.startActivity(Intent.createChooser(intent, "分享商品"))
                    }.onFailure {
                        screenScope.launch { snackbarHostState.showSnackbar("分享失败，请稍后重试") }
                    }
                },
            )
        }
    }
}

@Composable
private fun ProductDetailImmersiveScaffold(
    skuId: String,
    product: ProductUiModel?,
    isLoading: Boolean,
    error: String?,
    selectedSku: ProductSkuUiModel?,
    selectedSkuId: String?,
    onSkuSelected: (String) -> Unit,
    selectedReviewFilter: ReviewFilter,
    onReviewFilterSelected: (ReviewFilter) -> Unit,
    showAllReviews: Boolean,
    onShowAllReviewsChange: (Boolean) -> Unit,
    displayPrice: Double?,
    originalPrice: Double?,
    canAttemptPurchase: Boolean,
    cartItemCount: Int,
    isAddingToCart: Boolean,
    favorite: Boolean,
    onFavoriteToggle: () -> Unit,
    highlightSpecs: Boolean,
    onHighlightSpecsChange: (Boolean) -> Unit,
    snackbarHostState: SnackbarHostState,
    context: android.content.Context,
    screenScope: kotlinx.coroutines.CoroutineScope,
    listState: androidx.compose.foundation.lazy.LazyListState,
    onBack: () -> Unit,
    onCartClick: () -> Unit,
    onLoadProduct: () -> Unit,
    onAddToCart: (ProductUiModel, ProductSkuUiModel?) -> Unit,
) {
    ProductDetailEdgeToEdge()

    BoxWithConstraints(
        modifier = Modifier
            .fillMaxSize()
            .background(AppColors.Background),
    ) {
        val density = LocalDensity.current
        val screenHeightPx = with(density) { maxHeight.toPx() }
        val detailTopPx = screenHeightPx * 0.38f
        val anchors = remember(screenHeightPx, detailTopPx, density) {
            DetailSheetAnchors(
                immersiveTopPx = screenHeightPx - with(density) { 18.dp.toPx() },
                halfExpandedTopPx = detailTopPx,
                expandedTopPx = detailTopPx,
            )
        }
        var sheetAnchor by rememberSaveable(skuId) { mutableStateOf(DetailSheetAnchor.Immersive) }
        var sheetTopPx by remember(skuId) { mutableFloatStateOf(Float.NaN) }
        val currentSheetTopPx = if (sheetTopPx.isNaN()) anchors.position(sheetAnchor) else sheetTopPx

        fun logSheetDebug(message: String) {
            if (DETAIL_SHEET_DEBUG_LOGS) {
                Log.d(DETAIL_SHEET_DEBUG_TAG, message)
            }
        }

        LaunchedEffect(anchors) {
            sheetTopPx = if (sheetTopPx.isNaN()) {
                anchors.position(sheetAnchor)
            } else {
                sheetTopPx.coerceIn(anchors.halfExpandedTopPx, anchors.immersiveTopPx)
            }
            logSheetDebug(
                "containerHeightPx=$screenHeightPx " +
                    "immersiveAnchor=${anchors.immersiveTopPx} " +
                    "halfExpandedAnchor=${anchors.halfExpandedTopPx} " +
                    "expandedAnchor=${anchors.expandedTopPx} " +
                    "currentSheetOffset=$sheetTopPx",
            )
        }

        fun moveSheetBy(deltaY: Float, source: String): Float {
            val old = if (sheetTopPx.isNaN()) anchors.position(sheetAnchor) else sheetTopPx
            val new = (old + deltaY).coerceIn(anchors.halfExpandedTopPx, anchors.immersiveTopPx)
            sheetTopPx = new
            val consumed = new - old
            if (DETAIL_SHEET_DEBUG_LOGS && kotlin.math.abs(consumed) > 0.5f) {
                logSheetDebug(
                    "source=$source dragDelta=$deltaY consumed=$consumed currentSheetOffset=$sheetTopPx",
                )
            }
            return consumed
        }

        fun dragSheetBy(source: String, deltaY: Float) {
            moveSheetBy(deltaY, source)
        }

        suspend fun animateSheetTo(targetAnchor: DetailSheetAnchor) {
            sheetAnchor = targetAnchor
            val start = if (sheetTopPx.isNaN()) anchors.position(targetAnchor) else sheetTopPx
            animate(
                initialValue = start,
                targetValue = anchors.position(targetAnchor),
                animationSpec = tween(
                    durationMillis = AppMotion.Slow,
                    easing = AppMotion.StandardEasing,
                ),
            ) { value, _ ->
                sheetTopPx = value
            }
        }

        suspend fun settleSheet(velocityY: Float = 0f) {
            val nearest = anchors.nearest(if (sheetTopPx.isNaN()) currentSheetTopPx else sheetTopPx)
            val target = when {
                velocityY < -SHEET_FLING_THRESHOLD -> anchors.nextUp(nearest)
                velocityY > SHEET_FLING_THRESHOLD -> anchors.nextDown(nearest)
                else -> nearest
            }
            logSheetDebug(
                "settle velocityY=$velocityY currentSheetOffset=$currentSheetTopPx targetState=$target",
            )
            animateSheetTo(target)
        }

        fun handleBack() {
            val current = anchors.nearest(currentSheetTopPx)
            if (current == DetailSheetAnchor.Immersive) {
                onBack()
            } else {
                screenScope.launch { animateSheetTo(anchors.nextDown(current)) }
            }
        }

        BackHandler(enabled = true) {
            if (showAllReviews) {
                onShowAllReviewsChange(false)
            } else {
                handleBack()
            }
        }

        when {
            isLoading -> {
                LoadingState(
                    modifier = Modifier.fillMaxSize(),
                    message = "正在加载商品详情",
                )
            }

            error != null -> {
                ErrorState(
                    title = "商品详情加载失败",
                    message = error,
                    actionLabel = "重试",
                    onAction = onLoadProduct,
                    modifier = Modifier.fillMaxSize(),
                )
            }

            product == null -> {
                EmptyState(
                    title = "未找到该商品",
                    message = "商品可能已下架或链接已失效。",
                    actionLabel = "返回",
                    onAction = onBack,
                    modifier = Modifier.fillMaxSize(),
                )
            }

            else -> {
                val detailProgress = ((anchors.immersiveTopPx - currentSheetTopPx) /
                    (anchors.immersiveTopPx - anchors.halfExpandedTopPx)).coerceIn(0f, 1f)
                val sheetHeight = with(density) {
                    (screenHeightPx - currentSheetTopPx).coerceAtLeast(0f).toDp()
                }
                val heroTopAlpha = (1f - detailProgress * 0.18f).coerceIn(0f, 1f)
                val heroBottomAlpha = (1f - detailProgress).coerceIn(0f, 1f)
                val swipeHintAlpha = (1f - detailProgress * 2f).coerceIn(0f, 1f)
                val bottomBarAlpha = detailProgress
                val heroImageScale = 1f - detailProgress * 0.18f
                val heroImageTranslationY = -screenHeightPx * 0.07f * detailProgress
                val heroImages = remember(product.skuId, product.imageUrl, product.detailImageUrl) {
                    product.detailImages()
                }
                val heroFallbackImages = remember(product.skuId, product.imageUrl, product.detailImageUrl) {
                    product.detailFallbackImages()
                }
                val heroPagerState = rememberPagerState(pageCount = { heroImages.size.coerceAtLeast(1) })
                var heroImageResolution by remember(
                    product.skuId,
                    heroImages.firstOrNull(),
                    heroFallbackImages.firstOrNull(),
                ) {
                    mutableStateOf(HeroImageResolution.Pending)
                }
                val hasDistinctDetailImage = product.detailImageUrl.cleanNullable() != null &&
                    product.detailImageUrl.cleanNullable() != product.imageUrl.cleanNullable()
                val heroImageMode = when (heroImageResolution) {
                    HeroImageResolution.Detail -> {
                        if (hasDistinctDetailImage) {
                            HeroImageMode.Scene
                        } else {
                            HeroImageMode.Packshot
                        }
                    }
                    HeroImageResolution.Pending -> {
                        if (hasDistinctDetailImage) HeroImageMode.Scene else HeroImageMode.Packshot
                    }
                    HeroImageResolution.Original,
                    HeroImageResolution.Failed -> HeroImageMode.Packshot
                }
                val listAtTop by remember {
                    derivedStateOf {
                        listState.firstVisibleItemIndex == 0 &&
                            listState.firstVisibleItemScrollOffset == 0
                    }
                }

                fun promptForMissingSpecs(currentProduct: ProductUiModel) {
                    val message = currentProduct.missingSpecPrompt(selectedSku)
                    onHighlightSpecsChange(true)
                    screenScope.launch {
                        animateSheetTo(DetailSheetAnchor.HalfExpanded)
                        listState.animateScrollToItem(index = PRODUCT_VARIANT_ITEM_INDEX)
                        snackbarHostState.showSnackbar(message)
                    }
                }

                val nestedScrollConnection = object : NestedScrollConnection {
                    override fun onPreScroll(available: Offset, source: NestedScrollSource): Offset {
                        val deltaY = available.y
                        val consumedY = when {
                            deltaY < 0f && currentSheetTopPx > anchors.halfExpandedTopPx -> moveSheetBy(deltaY, "nestedPreScroll")
                            deltaY > 0f && listAtTop && currentSheetTopPx < anchors.immersiveTopPx -> moveSheetBy(deltaY, "nestedPreScroll")
                            else -> 0f
                        }
                        return if (consumedY != 0f) Offset(0f, consumedY) else Offset.Zero
                    }

                    override suspend fun onPostFling(consumed: Velocity, available: Velocity): Velocity {
                        if (currentSheetTopPx in anchors.halfExpandedTopPx..anchors.immersiveTopPx) {
                            settleSheet(available.y)
                        }
                        return Velocity.Zero
                    }
                }

                val dragState = rememberDraggableState { deltaY ->
                    dragSheetBy("rootDrag", deltaY)
                }

                Box(
                    modifier = Modifier
                        .fillMaxSize()
                        .draggable(
                            state = dragState,
                            orientation = Orientation.Vertical,
                            enabled = currentSheetTopPx > anchors.halfExpandedTopPx + 0.5f,
                            onDragStopped = { velocity -> screenScope.launch { settleSheet(velocity) } },
                        )
                        .zIndex(0f),
                ) {
                    HeroMedia(
                        imageUrls = heroImages,
                        fallbackImageUrls = heroFallbackImages,
                        mode = heroImageMode,
                        pagerState = heroPagerState,
                        contentDescription = product.displayTitle,
                        imageScale = heroImageScale,
                        imageTranslationY = heroImageTranslationY,
                        onResolvedImageSourceChange = { source ->
                            heroImageResolution = when (source) {
                                ResolvedImageSource.Detail -> HeroImageResolution.Detail
                                ResolvedImageSource.Original -> HeroImageResolution.Original
                                null -> HeroImageResolution.Failed
                            }
                        },
                        modifier = Modifier.fillMaxSize(),
                    )
                    TopScrim(
                        modifier = Modifier
                            .align(Alignment.TopCenter)
                            .graphicsLayer { alpha = heroTopAlpha },
                    )
                    BottomScrim(
                        modifier = Modifier
                            .align(Alignment.BottomCenter)
                            .graphicsLayer { alpha = heroBottomAlpha },
                    )

                    HeroTopOverlay(
                        product = product,
                        selectedSku = selectedSku,
                        favorite = favorite,
                        onBack = { handleBack() },
                        onFavoriteClick = onFavoriteToggle,
                        onShareClick = {
                            val shareText = product.shareText(selectedSku)
                            val intent = Intent(Intent.ACTION_SEND).apply {
                                type = "text/plain"
                                putExtra(Intent.EXTRA_TEXT, shareText)
                            }
                            runCatching {
                                context.startActivity(
                                    Intent.createChooser(
                                        intent,
                                        context.getString(R.string.product_detail_share_chooser_title),
                                    ),
                                )
                            }.onFailure {
                                screenScope.launch {
                                    snackbarHostState.showSnackbar(
                                        context.getString(R.string.product_detail_share_failed),
                                    )
                                }
                            }
                        },
                        modifier = Modifier
                            .align(Alignment.TopCenter)
                            .graphicsLayer { alpha = heroTopAlpha },
                    )
                    HeroBottomSummary(
                        product = product,
                        selectedSku = selectedSku,
                        imageCount = heroImages.size,
                        currentImageIndex = heroPagerState.currentPage,
                        modifier = Modifier
                            .align(Alignment.BottomCenter)
                            .padding(
                                start = AppSpacing.Xl,
                                end = AppSpacing.Xl,
                                bottom = 46.dp,
                            )
                            .graphicsLayer { alpha = heroBottomAlpha },
                    )
                    HeroSwipeHint(
                        modifier = Modifier
                            .align(Alignment.BottomCenter)
                            .padding(bottom = AppSpacing.Xxl)
                            .graphicsLayer { alpha = swipeHintAlpha },
                    )
                }

                ProductDetailSheet(
                    product = product,
                    selectedSku = selectedSku,
                    selectedSkuId = selectedSkuId,
                    onSkuSelected = onSkuSelected,
                    onViewAllReviews = { onShowAllReviewsChange(true) },
                    listState = listState,
                    highlightSpecs = highlightSpecs,
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(sheetHeight)
                        .offset { IntOffset(x = 0, y = currentSheetTopPx.roundToInt()) }
                        .nestedScroll(nestedScrollConnection)
                        .zIndex(2f),
                )

                if (bottomBarAlpha > 0.01f) {
                    ProductBottomActionBar(
                        price = displayPrice,
                        originalPrice = originalPrice,
                        cartItemCount = cartItemCount,
                        inStock = canAttemptPurchase,
                        addToCartLoading = isAddingToCart,
                        onCartClick = onCartClick,
                        onAddToCart = {
                            if (product.skus.isNotEmpty() && selectedSku == null) {
                                promptForMissingSpecs(product)
                            } else {
                                onAddToCart(product, selectedSku)
                            }
                        },
                        onBuyNow = {
                            if (product.skus.isNotEmpty() && selectedSku == null) {
                                promptForMissingSpecs(product)
                            } else {
                                screenScope.launch {
                                    snackbarHostState.showSnackbar("立即购买暂未接入商品详情直达流程")
                                }
                            }
                        },
                        modifier = Modifier
                            .align(Alignment.BottomCenter)
                            .zIndex(3f)
                            .graphicsLayer {
                                alpha = bottomBarAlpha
                                translationY = (1f - bottomBarAlpha) * 48.dp.toPx()
                            },
                    )
                }

                SnackbarHost(
                    hostState = snackbarHostState,
                    modifier = Modifier
                        .align(Alignment.BottomCenter)
                        .padding(bottom = AppDimensions.BottomActionBarMinHeight + AppSpacing.Xxl)
                        .zIndex(4f),
                )

                if (showAllReviews) {
                    ProductReviewsOverlay(
                        product = product,
                        initialFilter = selectedReviewFilter,
                        onFilterSelected = onReviewFilterSelected,
                        onBack = { onShowAllReviewsChange(false) },
                        modifier = Modifier
                            .fillMaxSize()
                            .zIndex(5f),
                    )
                }
            }
        }
    }
}

@Composable
private fun ProductDetailEdgeToEdge() {
    val view = LocalView.current
    SideEffect {
        val window = (view.context as? Activity)?.window ?: return@SideEffect
        WindowCompat.setDecorFitsSystemWindows(window, false)
        window.statusBarColor = Color.Transparent.toArgb()
        window.navigationBarColor = AppColors.Surface.toArgb()
        WindowCompat.getInsetsController(window, view).apply {
            isAppearanceLightStatusBars = false
            isAppearanceLightNavigationBars = true
        }
    }
    DisposableEffect(view) {
        val window = (view.context as? Activity)?.window
        val previousStatusBarColor = window?.statusBarColor
        val previousNavigationBarColor = window?.navigationBarColor
        onDispose {
            window ?: return@onDispose
            WindowCompat.setDecorFitsSystemWindows(window, true)
            previousStatusBarColor?.let { window.statusBarColor = it }
            previousNavigationBarColor?.let { window.navigationBarColor = it }
            WindowCompat.getInsetsController(window, view).apply {
                isAppearanceLightStatusBars = true
                isAppearanceLightNavigationBars = true
            }
        }
    }
}

@Composable
private fun ProductDetailSheet(
    product: ProductUiModel,
    selectedSku: ProductSkuUiModel?,
    selectedSkuId: String?,
    onSkuSelected: (String) -> Unit,
    onViewAllReviews: () -> Unit,
    listState: androidx.compose.foundation.lazy.LazyListState,
    highlightSpecs: Boolean,
    modifier: Modifier = Modifier,
) {
    Surface(
        modifier = modifier,
        shape = RoundedCornerShape(topStart = AppRadius.Panel, topEnd = AppRadius.Panel),
        color = AppColors.Surface,
        shadowElevation = AppElevation.Low,
        border = BorderStroke(1.dp, AppColors.Border),
    ) {
        Column(modifier = Modifier.fillMaxSize()) {
            SheetDragHandle()
            ProductDetailSheetContent(
                product = product,
                selectedSku = selectedSku,
                selectedSkuId = selectedSkuId,
                onSkuSelected = onSkuSelected,
                onViewAllReviews = onViewAllReviews,
                listState = listState,
                highlightSpecs = highlightSpecs,
                modifier = Modifier.weight(1f),
            )
        }
    }
}

@Composable
private fun SheetDragHandle() {
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .padding(top = AppSpacing.Sm, bottom = AppSpacing.Xs),
        contentAlignment = Alignment.Center,
    ) {
        Box(
            modifier = Modifier
                .size(width = 40.dp, height = 4.dp)
                .background(AppColors.BorderStrong, RoundedCornerShape(AppRadius.Pill)),
        )
    }
}

@Composable
private fun HeroMedia(
    imageUrls: List<String>,
    fallbackImageUrls: List<String>,
    mode: HeroImageMode,
    pagerState: PagerState,
    contentDescription: String?,
    imageScale: Float,
    imageTranslationY: Float,
    onResolvedImageSourceChange: (ResolvedImageSource?) -> Unit,
    modifier: Modifier = Modifier,
) {
    val heroScale = imageScale.coerceIn(0.82f, 1f)
    Box(
        modifier = modifier
            .background(if (mode == HeroImageMode.Scene) AppColors.TextPrimary else AppColors.BackgroundElevated)
            .clipToBounds(),
        contentAlignment = Alignment.Center,
    ) {
        HorizontalPager(
            state = pagerState,
            modifier = Modifier.fillMaxSize(),
        ) { page ->
            Box(
                modifier = Modifier.fillMaxSize(),
                contentAlignment = Alignment.Center,
            ) {
                ProductImage(
                    imageUrl = imageUrls.getOrNull(page).orEmpty(),
                    fallbackImageUrl = fallbackImageUrls.getOrNull(page),
                    contentDescription = contentDescription,
                    modifier = if (mode == HeroImageMode.Scene) {
                        Modifier
                            .fillMaxSize()
                            .graphicsLayer {
                                scaleX = heroScale
                                scaleY = heroScale
                                translationY = imageTranslationY
                            }
                    } else {
                        Modifier
                            .fillMaxWidth(0.88f)
                            .fillMaxHeight(0.78f)
                            .graphicsLayer {
                                scaleX = heroScale
                                scaleY = heroScale
                                translationY = imageTranslationY
                            }
                    },
                    onResolvedImageSourceChange = if (page == pagerState.currentPage) {
                        onResolvedImageSourceChange
                    } else {
                        {}
                    },
                    cornerRadius = AppSpacing.None,
                    contentScale = if (mode == HeroImageMode.Scene) ContentScale.Crop else ContentScale.Fit,
                    backgroundColor = Color.Transparent,
                )
            }
        }
    }
}

@Composable
private fun TopScrim(
    modifier: Modifier = Modifier,
) {
    Box(
        modifier = modifier
            .fillMaxWidth()
            .height(150.dp)
            .background(
                Brush.verticalGradient(
                    colors = listOf(
                        Color.Black.copy(alpha = 0.34f),
                        Color.Transparent,
                    ),
                ),
            ),
    )
}

@Composable
private fun BottomScrim(
    modifier: Modifier = Modifier,
) {
    Box(
        modifier = modifier
            .fillMaxWidth()
            .height(260.dp)
            .background(
                Brush.verticalGradient(
                    colors = listOf(
                        Color.Transparent,
                        Color.Black.copy(alpha = 0.20f),
                        Color.Black.copy(alpha = 0.52f),
                    ),
                ),
            ),
    )
}

@Composable
private fun ProductDetailSheetContent(
    product: ProductUiModel,
    selectedSku: ProductSkuUiModel?,
    selectedSkuId: String?,
    onSkuSelected: (String) -> Unit,
    onViewAllReviews: () -> Unit,
    listState: androidx.compose.foundation.lazy.LazyListState,
    highlightSpecs: Boolean,
    modifier: Modifier = Modifier,
) {
    val density = LocalDensity.current
    val navigationBottomPadding = with(density) {
        WindowInsets.navigationBars.getBottom(this).toDp()
    }
    LazyColumn(
        state = listState,
        modifier = modifier
            .fillMaxWidth()
            .background(AppColors.Surface),
        contentPadding = PaddingValues(
            bottom = AppDimensions.BottomActionBarMinHeight +
                navigationBottomPadding +
                AppSpacing.Xxl,
        ),
        verticalArrangement = Arrangement.spacedBy(AppSpacing.Lg),
    ) {
        item(key = "basic-info") {
            ProductInfoPanel(
                modifier = Modifier.padding(horizontal = AppSpacing.Lg),
            ) {
                ProductBasicInfo(
                    product = product,
                    selectedSku = selectedSku,
                )
            }
        }

        item(key = "ai-recommendation") {
            AiRecommendationBlock(
                product = product,
                modifier = Modifier.padding(horizontal = AppSpacing.Lg),
            )
        }

        item(key = PRODUCT_VARIANT_ITEM_KEY) {
            ProductInfoPanel(
                modifier = Modifier.padding(horizontal = AppSpacing.Lg),
            ) {
                ProductVariantSelector(
                    product = product,
                    selectedSku = selectedSku,
                    selectedSkuId = selectedSkuId,
                    onSkuSelected = onSkuSelected,
                    highlight = highlightSpecs,
                )
            }
        }

        item(key = "reviews") {
            ReviewSummaryCard(
                product = product,
                onViewAll = onViewAllReviews,
                modifier = Modifier.padding(horizontal = AppSpacing.Lg),
            )
        }
        item(key = "bottom-space") { Spacer(modifier = Modifier.height(AppSpacing.Xxl)) }
    }
}

@Composable
private fun HeroTopOverlay(
    product: ProductUiModel,
    selectedSku: ProductSkuUiModel?,
    favorite: Boolean,
    onBack: () -> Unit,
    onFavoriteClick: () -> Unit,
    onShareClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val backLabel = stringResource(R.string.product_detail_back)
    val favoriteLabel = stringResource(
        if (favorite) {
            R.string.product_detail_unfavorite
        } else {
            R.string.product_detail_favorite
        },
    )
    val shareLabel = stringResource(R.string.product_detail_share)
    val spec = selectedSku?.specSummary()?.takeIf { it.isNotBlank() }
    Box(
        modifier = modifier
            .fillMaxWidth()
            .statusBarsPadding()
            .padding(horizontal = AppSpacing.Md, vertical = AppSpacing.Xs)
            .heightIn(min = 44.dp),
    ) {
        AppIconButton(
            onClick = onBack,
            style = AppIconButtonStyle.Hero,
            containerSize = 40.dp,
            hitAreaSize = 44.dp,
            iconSize = 20.dp,
            modifier = Modifier.align(Alignment.CenterStart),
        ) {
            Icon(
                painter = painterResource(R.drawable.ic_chevron_right_20),
                contentDescription = backLabel,
                modifier = Modifier.rotate(180f),
            )
        }
        Column(
            modifier = Modifier
                .align(Alignment.Center)
                .fillMaxWidth()
                .padding(start = 60.dp, end = 108.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(AppSpacing.Xxs),
        ) {
            Text(
                text = product.heroTitle(),
                style = AppTypography.TitleSmall,
                fontWeight = FontWeight.Medium,
                color = AppColors.HeroText,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
                textAlign = TextAlign.Center,
            )
            spec?.let {
                Text(
                    text = it,
                    style = AppTypography.CaptionStrong,
                    fontWeight = FontWeight.Normal,
                    color = AppColors.HeroText.copy(alpha = 0.76f),
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                    textAlign = TextAlign.Center,
                )
            }
        }
        Row(
            modifier = Modifier.align(Alignment.CenterEnd),
            horizontalArrangement = Arrangement.spacedBy(AppSpacing.Sm),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            AppIconButton(
                onClick = onFavoriteClick,
                selected = favorite,
                style = AppIconButtonStyle.Hero,
                containerSize = 40.dp,
                hitAreaSize = 44.dp,
                iconSize = 20.dp,
            ) {
                Icon(
                    painter = painterResource(if (favorite) R.drawable.ic_star_20 else R.drawable.ic_star_border_20),
                    contentDescription = favoriteLabel,
                )
            }
            AppIconButton(
                onClick = onShareClick,
                style = AppIconButtonStyle.Hero,
                containerSize = 40.dp,
                hitAreaSize = 44.dp,
                iconSize = 20.dp,
            ) {
                Icon(
                    painter = painterResource(R.drawable.ic_share_20),
                    contentDescription = shareLabel,
                )
            }
        }
    }
}

@Composable
private fun HeroBottomSummary(
    product: ProductUiModel,
    selectedSku: ProductSkuUiModel?,
    imageCount: Int,
    currentImageIndex: Int,
    modifier: Modifier = Modifier,
) {
    val currentPrice = selectedSku?.price ?: product.price
    Row(
        modifier = modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.spacedBy(AppSpacing.Lg),
        verticalAlignment = Alignment.Bottom,
    ) {
        Column(
            modifier = Modifier.weight(1f),
            verticalArrangement = Arrangement.spacedBy(AppSpacing.Sm),
        ) {
            product.brand.cleanNullable()?.let {
                Text(
                    text = it,
                    style = AppTypography.BodySmall,
                    color = AppColors.HeroText.copy(alpha = 0.82f),
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
            }
            Row(
                verticalAlignment = Alignment.Bottom,
                horizontalArrangement = Arrangement.spacedBy(AppSpacing.Sm),
            ) {
                Text(
                    text = "\u00A5${formatPrice(currentPrice)}",
                    style = AppTypography.HeroPrice,
                    color = AppColors.HeroText,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
                product.basePrice
                    ?.takeIf { it > currentPrice }
                    ?.let {
                        OriginalPriceText(
                            price = it,
                            color = AppColors.HeroText.copy(alpha = 0.62f),
                        )
                    }
            }
        }
        Column(
            horizontalAlignment = Alignment.End,
            verticalArrangement = Arrangement.spacedBy(AppSpacing.Md),
        ) {
            product.detailRating()?.let {
                Row(
                    horizontalArrangement = Arrangement.spacedBy(AppSpacing.Xs),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Text(
                        text = "%.1f/5".format(it),
                        style = AppTypography.BodySmall,
                        color = AppColors.HeroText.copy(alpha = 0.88f),
                        maxLines = 1,
                    )
                    Icon(
                        painter = painterResource(R.drawable.ic_star_20),
                        contentDescription = null,
                        modifier = Modifier.size(15.dp),
                        tint = AppColors.HeroText.copy(alpha = 0.88f),
                    )
                }
            }
            HeroImageIndicators(
                imageCount = imageCount,
                currentImageIndex = currentImageIndex,
            )
        }
    }
}

@Composable
private fun HeroImageIndicators(
    imageCount: Int,
    currentImageIndex: Int,
    modifier: Modifier = Modifier,
) {
    if (imageCount <= 1) {
        return
    }
    Row(
        modifier = modifier,
        horizontalArrangement = Arrangement.spacedBy(AppSpacing.Xs),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        repeat(imageCount) { index ->
            val selected = index == currentImageIndex
            Box(
                modifier = Modifier
                    .size(if (selected) 7.dp else 6.dp)
                    .background(
                        color = AppColors.HeroText.copy(alpha = if (selected) 0.86f else 0.38f),
                        shape = CircleShape,
                    ),
            )
        }
    }
}

@Composable
private fun HeroSwipeHint(
    modifier: Modifier = Modifier,
) {
    Box(
        modifier = modifier,
        contentAlignment = Alignment.Center,
    ) {
        Text(
            text = stringResource(R.string.product_detail_swipe_up_hint),
            style = AppTypography.Caption,
            color = AppColors.HeroText.copy(alpha = 0.68f),
            maxLines = 1,
        )
    }
}

@Composable
private fun ProductDetailContent(
    product: ProductUiModel,
    selectedSku: ProductSkuUiModel?,
    selectedSkuId: String?,
    onSkuSelected: (String) -> Unit,
    selectedReviewFilter: ReviewFilter,
    onReviewFilterSelected: (ReviewFilter) -> Unit,
    heroHeight: androidx.compose.ui.unit.Dp,
    listState: androidx.compose.foundation.lazy.LazyListState,
    highlightSpecs: Boolean,
    modifier: Modifier = Modifier,
) {
    LazyColumn(
        state = listState,
        modifier = modifier
            .fillMaxSize()
            .background(AppColors.Background),
        contentPadding = PaddingValues(bottom = AppDimensions.BottomActionBarMinHeight + AppSpacing.Huge),
        verticalArrangement = Arrangement.spacedBy(AppSpacing.Xl),
    ) {
        item(key = "hero") {
            ProductHero(
                product = product,
                selectedSku = selectedSku,
                height = heroHeight,
            )
        }
        item(key = "info") {
            ProductInfoPanel(
                modifier = Modifier
                    .offset(y = (-AppSpacing.Xxl))
                    .padding(horizontal = AppSpacing.Lg),
            ) {
                ProductBasicInfo(
                    product = product,
                    selectedSku = selectedSku,
                )
                AiRecommendationBlock(product = product)
                ProductTagSection(product = product)
                ProductVariantSelector(
                    product = product,
                    selectedSku = selectedSku,
                    selectedSkuId = selectedSkuId,
                    onSkuSelected = onSkuSelected,
                    highlight = highlightSpecs,
                )
                SelectedSkuStatus(product = product, selectedSku = selectedSku)
            }
        }
        item(key = PRODUCT_VARIANT_ITEM_KEY) {
            Spacer(modifier = Modifier.height(AppSpacing.None))
        }
        item(key = "parameters") {
            CoreParametersSection(
                product = product,
                selectedSku = selectedSku,
                modifier = Modifier.padding(horizontal = AppSpacing.Lg),
            )
        }
        item(key = "reviews") {
            UserReviewSection(
                product = product,
                selectedFilter = selectedReviewFilter,
                onFilterSelected = onReviewFilterSelected,
                modifier = Modifier.padding(horizontal = AppSpacing.Lg),
            )
        }
        item(key = "scenario-audience") {
            ScenarioAudienceSection(
                product = product,
                modifier = Modifier.padding(horizontal = AppSpacing.Lg),
            )
        }
        item(key = "bottom-space") { Spacer(modifier = Modifier.height(AppSpacing.Xxl)) }
    }
}

@Composable
private fun ProductHero(
    product: ProductUiModel,
    selectedSku: ProductSkuUiModel?,
    height: androidx.compose.ui.unit.Dp,
) {
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .height(height),
    ) {
        ProductImagePager(
            imageUrls = product.detailImages(),
            fallbackImageUrls = product.detailFallbackImages(),
            contentDescription = product.displayTitle,
            modifier = Modifier.fillMaxSize(),
            contentScale = ContentScale.Fit,
        )
        Box(
            modifier = Modifier
                .align(Alignment.BottomStart)
                .padding(horizontal = AppSpacing.Lg, vertical = AppSpacing.Xl)
                .background(
                    color = AppColors.HeroIconBackground.copy(alpha = 0.72f),
                    shape = RoundedCornerShape(AppRadius.Large),
                )
                .padding(horizontal = AppSpacing.Md, vertical = AppSpacing.Sm),
        ) {
            Column(verticalArrangement = Arrangement.spacedBy(AppSpacing.Xs)) {
                product.brand.cleanNullable()?.let {
                    Text(
                        text = it,
                        style = AppTypography.BodySmall,
                        color = AppColors.HeroIcon,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                }
                Row(
                    verticalAlignment = Alignment.Bottom,
                    horizontalArrangement = Arrangement.spacedBy(AppSpacing.Sm),
                ) {
                    val currentPrice = selectedSku?.price ?: product.price
                    PriceText(
                        price = currentPrice,
                        level = PriceTextLevel.Normal,
                        color = AppColors.HeroIcon,
                    )
                    product.basePrice
                        ?.takeIf { it > currentPrice }
                        ?.let {
                            OriginalPriceText(
                                price = it,
                                color = AppColors.TextSecondary,
                            )
                        }
                    val rating = product.detailRating()
                    rating?.let {
                        Text(
                            text = "%.1f/5".format(it),
                            style = AppTypography.BodySmall,
                            color = AppColors.HeroIcon,
                            maxLines = 1,
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun FloatingProductActions(
    favorite: Boolean,
    onBack: () -> Unit,
    onFavoriteClick: () -> Unit,
    onShareClick: () -> Unit,
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .statusBarsPadding()
            .padding(horizontal = AppSpacing.Lg, vertical = AppSpacing.Sm),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(AppSpacing.Sm),
    ) {
        AppIconButton(
            onClick = onBack,
            style = AppIconButtonStyle.Hero,
        ) {
            Icon(
                painter = painterResource(R.drawable.ic_chevron_right_20),
                contentDescription = "返回",
                modifier = Modifier.rotate(180f),
            )
        }
        Spacer(modifier = Modifier.weight(1f))
        AppIconButton(
            onClick = onFavoriteClick,
            selected = favorite,
            style = AppIconButtonStyle.Hero,
        ) {
            Icon(
                painter = painterResource(if (favorite) R.drawable.ic_star_20 else R.drawable.ic_star_border_20),
                contentDescription = if (favorite) "取消收藏" else "收藏",
            )
        }
        AppIconButton(
            onClick = onShareClick,
            style = AppIconButtonStyle.Hero,
        ) {
            Icon(
                painter = painterResource(R.drawable.ic_share_20),
                contentDescription = "分享",
            )
        }
    }
}

@Composable
private fun ProductInfoPanel(
    modifier: Modifier = Modifier,
    content: @Composable () -> Unit,
) {
    Surface(
        modifier = modifier.fillMaxWidth(),
        shape = RoundedCornerShape(AppRadius.Panel),
        color = AppColors.Surface,
        shadowElevation = AppElevation.None,
        border = BorderStroke(1.dp, AppColors.Border),
    ) {
        Column(
            modifier = Modifier.padding(AppSpacing.Md),
            verticalArrangement = Arrangement.spacedBy(AppSpacing.Md),
        ) {
            content()
        }
    }
}

@Composable
private fun ProductBasicInfo(
    product: ProductUiModel,
    selectedSku: ProductSkuUiModel?,
    modifier: Modifier = Modifier,
) {
    val currentPrice = selectedSku?.price ?: product.price
    val originalPrice = product.basePrice?.takeIf { it > currentPrice }
    val discountText = originalPrice?.let { "%.1f折".format(currentPrice / it * 10) }
    Column(
        modifier = modifier.fillMaxWidth(),
        verticalArrangement = Arrangement.spacedBy(AppSpacing.Md),
    ) {
        Text(
            text = product.displayTitle,
            style = AppTypography.Title,
            color = AppColors.TextPrimary,
            maxLines = 2,
            overflow = TextOverflow.Ellipsis,
        )
        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.Bottom,
            horizontalArrangement = Arrangement.spacedBy(AppSpacing.Sm),
        ) {
            PriceText(
                price = currentPrice,
                level = PriceTextLevel.Large,
            )
            originalPrice?.let { OriginalPriceText(price = it) }
            discountText?.let {
                TagChip(text = it, tone = TagChipTone.Warm)
            }
        }
        val meta = listOf(product.brand, product.subCategory ?: product.category)
            .filter { it.isNotBlank() }
            .distinct()
            .joinToString(" · ")
        if (meta.isNotBlank()) {
            Text(
                text = meta,
                style = AppTypography.BodySmall,
                color = AppColors.TextSecondary,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
        }
    }
}

@Composable
private fun AiRecommendationBlock(
    product: ProductUiModel,
    modifier: Modifier = Modifier,
) {
    val reason = product.guideReason()
    val reasonBullets = remember(reason) { splitReasonBullets(reason) }
    val tradeOff = product.presentation?.tradeOff.cleanNullable()
    var expanded by remember(product.skuId, reason) { mutableStateOf(false) }
    if (reason.isBlank() && tradeOff == null) {
        return
    }

    Surface(
        modifier = modifier.fillMaxWidth(),
        shape = RoundedCornerShape(AppRadius.Large),
        color = AppColors.AccentWarmSoft,
        border = BorderStroke(1.dp, AppColors.Border),
    ) {
        Column(
            modifier = Modifier.padding(AppSpacing.Md),
            verticalArrangement = Arrangement.spacedBy(AppSpacing.Sm),
        ) {
            TagChip(text = "AI 匹配推荐", tone = TagChipTone.Warm)
            if (reason.isNotBlank()) {
                Text(
                    text = "为什么适合你",
                    style = AppTypography.CaptionStrong,
                    color = AppColors.AccentWarm,
                )
                if (reasonBullets.size >= 2) {
                    reasonBullets.take(3).forEach { item ->
                        Text(
                            text = "· $item",
                            style = AppTypography.BodySmall,
                            color = AppColors.TextPrimary,
                        )
                    }
                } else {
                    Text(
                        text = reason,
                        style = AppTypography.BodySmall,
                        color = AppColors.TextPrimary,
                        maxLines = if (expanded) Int.MAX_VALUE else 3,
                        overflow = TextOverflow.Ellipsis,
                    )
                    if (reason.length > 80) {
                        Text(
                            text = if (expanded) "收起" else "展开全文",
                            style = AppTypography.CaptionStrong,
                            color = AppColors.AccentWarm,
                            modifier = Modifier
                                .clickable { expanded = !expanded }
                                .padding(top = AppSpacing.Xs),
                        )
                    }
                }
            }
            tradeOff?.let {
                HorizontalDivider(color = AppColors.Border)
                Text(
                    text = "需要注意",
                    style = AppTypography.CaptionStrong,
                    color = AppColors.AccentWarm,
                )
                Text(
                    text = it,
                    style = AppTypography.BodySmall,
                    color = AppColors.TextSecondary,
                )
            }
        }
    }
}

@Composable
private fun ProductTagSection(
    product: ProductUiModel,
    modifier: Modifier = Modifier,
) {
    val tags = product.productTags()
    if (tags.isEmpty()) {
        return
    }
    Column(
        modifier = modifier.fillMaxWidth(),
        verticalArrangement = Arrangement.spacedBy(AppSpacing.Sm),
    ) {
        Text(
            text = "商品标签",
            style = AppTypography.CaptionStrong,
            color = AppColors.TextSecondary,
        )
        FlowRow(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(AppSpacing.Sm),
            verticalArrangement = Arrangement.spacedBy(AppSpacing.Sm),
        ) {
            tags.forEachIndexed { index, tag ->
                TagChip(
                    text = tag,
                    tone = if (index == 0 && tag in product.aiAccentTags()) {
                        TagChipTone.Warm
                    } else {
                        TagChipTone.Neutral
                    },
                )
            }
        }
    }
}

@Composable
private fun ProductVariantSelector(
    product: ProductUiModel,
    selectedSku: ProductSkuUiModel?,
    selectedSkuId: String?,
    onSkuSelected: (String) -> Unit,
    highlight: Boolean,
    modifier: Modifier = Modifier,
) {
    if (product.skus.isEmpty()) {
        return
    }
    Column(
        modifier = modifier
            .fillMaxWidth()
            .background(
                color = if (highlight) AppColors.AccentWarmSoft else AppColors.Surface,
                shape = RoundedCornerShape(AppRadius.Large),
            )
            .padding(if (highlight) AppSpacing.Md else AppSpacing.None),
        verticalArrangement = Arrangement.spacedBy(AppSpacing.Md),
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(AppSpacing.Sm),
        ) {
            Text(
                text = "规格选择",
                style = AppTypography.BodyStrong,
                color = AppColors.TextPrimary,
                modifier = Modifier.weight(1f),
            )
            selectedSku?.specSummary()?.takeIf { it.isNotBlank() }?.let {
                Text(
                    text = it,
                    style = AppTypography.CaptionStrong,
                    color = AppColors.TextSecondary,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
            }
        }
        val optionKeys = product.skus.flatMap { it.properties.keys }.distinct()
        if (optionKeys.isEmpty()) {
            FlowRow(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(AppSpacing.Sm),
                verticalArrangement = Arrangement.spacedBy(AppSpacing.Sm),
            ) {
                product.skus.forEach { sku ->
                    SpecOptionChip(
                        label = sku.skuId.ifBlank { "默认规格" },
                        selected = sku.skuId == selectedSkuId,
                        enabled = product.stock > 0,
                        onClick = { onSkuSelected(sku.skuId) },
                    )
                }
            }
            return@Column
        }

        optionKeys.forEach { key ->
            val selectedValue = selectedSku?.properties?.get(key).cleanNullable()
            Column(verticalArrangement = Arrangement.spacedBy(AppSpacing.Sm)) {
                Text(
                    text = selectedValue?.let { "$key · $it" } ?: "选择$key",
                    style = AppTypography.CaptionStrong,
                    fontWeight = FontWeight.SemiBold,
                    color = AppColors.TextPrimary,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
                FlowRow(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(AppSpacing.Sm),
                    verticalArrangement = Arrangement.spacedBy(AppSpacing.Sm),
                ) {
                    val values = product.skus.mapNotNull { it.properties[key] }
                        .filter { it.isNotBlank() }
                        .distinct()
                    values.forEach { value ->
                        val selected = selectedSku?.properties?.get(key) == value
                        val enabled = product.stock > 0 && product.hasAnySkuForOption(key, value)
                        SpecOptionChip(
                            label = value,
                            selected = selected,
                            enabled = enabled,
                            onClick = {
                                product.findSkuForOption(
                                    currentSku = selectedSku,
                                    key = key,
                                    value = value,
                                )?.skuId?.let(onSkuSelected)
                            },
                        )
                    }
                }
            }
        }
        Text(
            text = "价格会随已选规格更新",
            style = AppTypography.BodySmall,
            color = AppColors.TextSecondary,
        )
    }
}

@Composable
private fun SpecOptionChip(
    label: String,
    selected: Boolean,
    enabled: Boolean,
    onClick: () -> Unit,
) {
    Surface(
        modifier = Modifier
            .heightIn(min = 36.dp)
            .clickable(enabled = enabled, onClick = onClick),
        shape = RoundedCornerShape(AppRadius.Medium),
        color = when {
            selected -> AppColors.Primary
            enabled -> AppColors.Surface
            else -> AppColors.SurfaceSoft
        },
        border = BorderStroke(
            width = 1.dp,
            color = when {
                selected -> AppColors.Primary
                enabled -> AppColors.BorderStrong
                else -> AppColors.Border
            },
        ),
    ) {
        Text(
            text = label,
            modifier = Modifier.padding(horizontal = AppSpacing.Md, vertical = AppSpacing.Sm),
            style = AppTypography.CaptionStrong,
            color = when {
                !enabled -> AppColors.TextDisabled
                selected -> AppColors.OnPrimary
                else -> AppColors.TextPrimary
            },
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
        )
    }
}

@Composable
private fun SelectedSkuStatus(
    product: ProductUiModel,
    selectedSku: ProductSkuUiModel?,
    modifier: Modifier = Modifier,
) {
    val stockText = if (product.stock > 0) "库存 ${product.stock}" else "暂时缺货"
    val specText = selectedSku?.specSummary()?.takeIf { it.isNotBlank() } ?: "未选择完整规格"
    val statusColor = if (product.stock > 0) AppColors.TextSecondary else AppColors.Danger

    Surface(
        modifier = modifier.fillMaxWidth(),
        shape = RoundedCornerShape(AppRadius.Large),
        color = if (product.stock > 0) AppColors.SurfaceSoft else AppColors.DangerSoft,
        border = BorderStroke(1.dp, if (product.stock > 0) AppColors.Border else AppColors.DangerSoft),
    ) {
        Column(
            modifier = Modifier.padding(AppSpacing.Md),
            verticalArrangement = Arrangement.spacedBy(AppSpacing.Xs),
        ) {
            Text(
                text = "$stockText · $specText",
                style = AppTypography.BodySmall,
                color = statusColor,
                maxLines = 2,
                overflow = TextOverflow.Ellipsis,
            )
            Text(
                text = "加入购物车和购买会使用当前选中的真实 SKU",
                style = AppTypography.Caption,
                color = AppColors.TextTertiary,
            )
        }
    }
}

@Composable
private fun CoreParametersSection(
    product: ProductUiModel,
    selectedSku: ProductSkuUiModel?,
    modifier: Modifier = Modifier,
) {
    val coreParams = product.coreParameters(selectedSku)
    if (coreParams.isEmpty()) {
        return
    }
    var expanded by remember(product.skuId, selectedSku?.skuId) { mutableStateOf(false) }
    DetailSection(title = "核心参数", modifier = modifier) {
        val display = if (expanded) coreParams else coreParams.take(6)
        Column(verticalArrangement = Arrangement.spacedBy(AppSpacing.Sm)) {
            display.chunked(2).forEach { rowItems ->
                Row(horizontalArrangement = Arrangement.spacedBy(AppSpacing.Sm)) {
                    rowItems.forEach { (label, value) ->
                        ParameterCell(
                            label = label,
                            value = value,
                            modifier = Modifier.weight(1f),
                        )
                    }
                    if (rowItems.size == 1) {
                        Spacer(modifier = Modifier.weight(1f))
                    }
                }
            }
        }
        if (coreParams.size > 6) {
            Text(
                text = if (expanded) "收起参数" else "查看完整参数",
                style = AppTypography.CaptionStrong,
                color = AppColors.TextPrimary,
                modifier = Modifier
                    .clickable { expanded = !expanded }
                    .padding(top = AppSpacing.Xs),
            )
        }
    }
}

@Composable
private fun ParameterCell(
    label: String,
    value: String,
    modifier: Modifier = Modifier,
) {
    Column(
        modifier = modifier
            .background(
                color = AppColors.SurfaceSoft,
                shape = RoundedCornerShape(AppRadius.Medium),
            )
            .padding(AppSpacing.Md),
        verticalArrangement = Arrangement.spacedBy(AppSpacing.Xs),
    ) {
        Text(
            text = label,
            style = AppTypography.Caption,
            color = AppColors.TextSecondary,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
        )
        Text(
            text = value,
            style = AppTypography.BodySmall,
            color = AppColors.TextPrimary,
            fontWeight = FontWeight.SemiBold,
            maxLines = 2,
            overflow = TextOverflow.Ellipsis,
        )
    }
}

@Composable
private fun UserReviewSection(
    product: ProductUiModel,
    selectedFilter: ReviewFilter,
    onFilterSelected: (ReviewFilter) -> Unit,
    modifier: Modifier = Modifier,
) {
    val review = remember(product.reviewsSummary, product.reviews) {
        parseReviewSummary(product.reviewsSummary, product)
    }
    if (review == null) {
        return
    }
    val filteredReviews = remember(review.reviews, selectedFilter) {
        review.reviews.filterBy(selectedFilter)
    }
    DetailSection(
        title = "用户评价",
        modifier = modifier,
        trailing = {
            ReviewViewAllAction(
                reviewCount = review.reviewCount,
                onClick = { onFilterSelected(ReviewFilter.All) },
                enabled = true,
            )
        },
    ) {
        ReviewRatingOverview(
            rating = review.rating,
            reviewCount = review.reviewCount,
        )
        ReviewSummaryTags(
            positives = review.positives,
            concerns = review.concerns,
            reviewCount = review.reviewCount,
        )
        if (review.reviews.isNotEmpty()) {
            ReviewFilterBar(
                selectedFilter = selectedFilter,
                counts = review.filterCounts,
                onFilterSelected = onFilterSelected,
            )
            if (filteredReviews.isEmpty()) {
                ReviewEmptyState(filter = selectedFilter)
            } else {
                Column(verticalArrangement = Arrangement.spacedBy(0.dp)) {
                    filteredReviews.forEachIndexed { index, item ->
                        ReviewListItem(review = item)
                        if (index != filteredReviews.lastIndex) {
                            HorizontalDivider(
                                modifier = Modifier.padding(vertical = AppSpacing.Md),
                                color = AppColors.Divider,
                            )
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun ReviewSummaryCard(
    product: ProductUiModel,
    onViewAll: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val review = remember(product.reviewsSummary, product.reviews) {
        parseReviewSummary(product.reviewsSummary, product)
    }
    ProductInfoPanel(modifier = modifier) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(AppSpacing.Sm),
        ) {
            Text(
                text = "\u7528\u6237\u8BC4\u4EF7",
                style = AppTypography.TitleSmall,
                color = AppColors.TextPrimary,
                fontWeight = FontWeight.Bold,
                modifier = Modifier.weight(1f),
            )
            ReviewViewAllAction(
                reviewCount = review?.reviewCount,
                onClick = onViewAll,
                enabled = true,
            )
        }
        HorizontalDivider(color = AppColors.Divider)
        if (review == null) {
            ReviewEmptyState(filter = ReviewFilter.All)
            return@ProductInfoPanel
        }
        CompactReviewSummaryTags(
            positives = review.positives,
            concerns = review.concerns,
            reviewCount = review.reviewCount,
        )
    }
}

@Composable
private fun CompactReviewSummaryTags(
    positives: List<String>,
    concerns: List<String>,
    reviewCount: Int?,
) {
    if (positives.isEmpty() && concerns.isEmpty()) {
        return
    }
    Column(
        modifier = Modifier.fillMaxWidth(),
        verticalArrangement = Arrangement.spacedBy(AppSpacing.Md),
    ) {
        if (positives.isNotEmpty()) {
            ReviewTagGroup(
                title = "\u597D\u8BC4\u53CD\u9988",
                tags = positives.take(5),
                tone = ReviewTagTone.Positive,
            )
        }
        if (concerns.isNotEmpty()) {
            ReviewTagGroup(
                title = "\u9700\u8981\u5173\u6CE8",
                tags = concerns.take(5),
                tone = ReviewTagTone.Concern,
            )
        }
        reviewCount?.let {
            Text(
                text = "\u57FA\u4E8E $it \u6761\u7528\u6237\u8BC4\u4EF7\u6574\u7406\uFF0C\u4EC5\u4F9B\u53C2\u8003",
                style = AppTypography.Caption,
                color = AppColors.TextTertiary,
            )
        }
    }
}

@Composable
private fun ProductReviewsOverlay(
    product: ProductUiModel,
    initialFilter: ReviewFilter,
    onFilterSelected: (ReviewFilter) -> Unit,
    onBack: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val review = remember(product.reviewsSummary, product.reviews) {
        parseReviewSummary(product.reviewsSummary, product)
    }
    var selectedFilter by rememberSaveable(product.skuId) { mutableStateOf(initialFilter) }
    LaunchedEffect(selectedFilter) {
        onFilterSelected(selectedFilter)
    }
    Surface(
        modifier = modifier,
        color = AppColors.Background,
    ) {
        Column(modifier = Modifier.fillMaxSize()) {
            ReviewsTopBar(
                reviewCount = review?.reviewCount,
                onBack = onBack,
            )
            LazyColumn(
                modifier = Modifier.fillMaxSize(),
                contentPadding = PaddingValues(
                    start = AppSpacing.Lg,
                    end = AppSpacing.Lg,
                    bottom = AppSpacing.Xxl,
                ),
                verticalArrangement = Arrangement.spacedBy(AppSpacing.Lg),
            ) {
                if (review == null) {
                    item(key = "empty") {
                        ReviewEmptyState(filter = ReviewFilter.All)
                    }
                } else {
                    item(key = "filters") {
                        ReviewFilterBar(
                            selectedFilter = selectedFilter,
                            counts = review.filterCounts,
                            onFilterSelected = { selectedFilter = it },
                        )
                    }
                    val filteredReviews = review.reviews.filterBy(selectedFilter)
                    if (filteredReviews.isEmpty()) {
                        item(key = "filtered-empty") {
                            ReviewEmptyState(filter = selectedFilter)
                        }
                    } else {
                        filteredReviews.forEach { item ->
                            item(
                                key = "${item.nickname.orEmpty()}-${item.createdAt.orEmpty()}-${item.content.hashCode()}",
                            ) {
                                ProductInfoPanel {
                                    ReviewListItem(review = item)
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun ReviewsTopBar(
    reviewCount: Int?,
    onBack: () -> Unit,
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .statusBarsPadding()
            .padding(horizontal = AppSpacing.Md, vertical = AppSpacing.Sm)
            .heightIn(min = AppDimensions.TopBarHeight),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(AppSpacing.Md),
    ) {
        AppIconButton(
            onClick = onBack,
            style = AppIconButtonStyle.Surface,
            containerSize = 40.dp,
            hitAreaSize = 44.dp,
            iconSize = 20.dp,
        ) {
            Icon(
                painter = painterResource(R.drawable.ic_chevron_right_20),
                contentDescription = "\u8FD4\u56DE",
                modifier = Modifier.rotate(180f),
            )
        }
        Column(modifier = Modifier.weight(1f)) {
            Text(
                text = "\u7528\u6237\u8BC4\u4EF7",
                style = AppTypography.Title,
                color = AppColors.TextPrimary,
                maxLines = 1,
            )
            Text(
                text = reviewCount?.let { "\u5171 $it \u6761" } ?: "\u6682\u65E0\u8BC4\u4EF7",
                style = AppTypography.BodySmall,
                color = AppColors.TextSecondary,
                maxLines = 1,
            )
        }
    }
}

@Composable
private fun ReviewViewAllAction(
    reviewCount: Int?,
    onClick: () -> Unit,
    enabled: Boolean,
) {
    Row(
        modifier = Modifier
            .clickable(enabled = enabled, onClick = onClick)
            .padding(vertical = 4.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(2.dp),
    ) {
        Text(
            text = reviewCount?.let { "\u67E5\u770B\u5168\u90E8\uFF0C\u5171 $it \u6761" }
                ?: "\u67E5\u770B\u5168\u90E8",
            style = AppTypography.CaptionStrong,
            color = if (enabled) AppColors.TextSecondary else AppColors.TextDisabled,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
        )
        Icon(
            painter = painterResource(R.drawable.ic_chevron_right_20),
            contentDescription = null,
            modifier = Modifier.size(AppDimensions.IconSmall),
            tint = if (enabled) AppColors.TextSecondary else AppColors.TextDisabled,
        )
    }
}

/*
@Composable
private fun ReviewViewAllAction(
    reviewCount: Int?,
    onClick: () -> Unit,
) {
    Row(
        modifier = Modifier
            .clickable(onClick = onClick)
            .padding(vertical = 4.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(2.dp),
    ) {
        Text(
            text = reviewCount?.let { "查看全部，共 $it 条" } ?: "查看全部",
            style = AppTypography.CaptionStrong,
            color = AppColors.TextSecondary,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
        )
        Icon(
            painter = painterResource(R.drawable.ic_chevron_right_20),
            contentDescription = null,
            modifier = Modifier.size(AppDimensions.IconSmall),
            tint = AppColors.TextSecondary,
        )
    }
}
*/

@Composable
private fun ReviewRatingOverview(
    rating: Double?,
    reviewCount: Int?,
) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        Text(
            text = rating?.let { "%.1f / 5".format(it) } ?: "暂无评分",
            style = AppTypography.TitleLarge,
            fontWeight = FontWeight.Bold,
            color = AppColors.TextPrimary,
            maxLines = 1,
        )
        rating?.let {
            RatingStars(
                rating = it,
                iconSize = 18,
                spacing = 1,
            )
        }
        reviewCount?.let {
            Text(
                text = "共 $it 条评价",
                style = AppTypography.BodySmall,
                color = AppColors.TextSecondary,
                maxLines = 1,
            )
        }
    }
}

@Composable
private fun ReviewSummaryTags(
    positives: List<String>,
    concerns: List<String>,
    reviewCount: Int?,
) {
    if (positives.isEmpty() && concerns.isEmpty()) {
        return
    }
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .background(
                color = AppColors.SurfaceSoft,
                shape = RoundedCornerShape(AppRadius.Large),
            )
            .padding(AppSpacing.Md),
        verticalArrangement = Arrangement.spacedBy(AppSpacing.Md),
    ) {
        Text(
            text = "评价总结",
            style = AppTypography.CaptionStrong,
            fontWeight = FontWeight.SemiBold,
            color = AppColors.TextPrimary,
        )
        if (positives.isNotEmpty()) {
            ReviewTagGroup(
                title = "好评反馈",
                tags = positives,
                tone = ReviewTagTone.Positive,
            )
        }
        if (concerns.isNotEmpty()) {
            ReviewTagGroup(
                title = "需要关注",
                tags = concerns,
                tone = ReviewTagTone.Concern,
            )
        }
        reviewCount?.let {
            Text(
                text = "基于 $it 条用户评价整理，仅供参考",
                style = AppTypography.Caption,
                color = AppColors.TextTertiary,
            )
        }
    }
}

@Composable
private fun ReviewTagGroup(
    title: String,
    tags: List<String>,
    tone: ReviewTagTone,
) {
    Column(verticalArrangement = Arrangement.spacedBy(AppSpacing.Sm)) {
        Text(
            text = title,
            style = AppTypography.CaptionStrong,
            fontWeight = FontWeight.SemiBold,
            color = AppColors.TextSecondary,
        )
        FlowRow(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(AppSpacing.Sm),
            verticalArrangement = Arrangement.spacedBy(AppSpacing.Sm),
        ) {
            tags.forEach { tag ->
                val container = when (tone) {
                    ReviewTagTone.Positive -> AppColors.SuccessSoft
                    ReviewTagTone.Concern -> AppColors.Surface
                }
                val contentColor = when (tone) {
                    ReviewTagTone.Positive -> AppColors.Success
                    ReviewTagTone.Concern -> AppColors.TextSecondary
                }
                val border = when (tone) {
                    ReviewTagTone.Positive -> null
                    ReviewTagTone.Concern -> BorderStroke(
                        width = 1.dp,
                        color = AppColors.BorderStrong,
                    )
                }
                Surface(
                    shape = RoundedCornerShape(AppRadius.Pill),
                    color = container,
                    border = border,
                ) {
                    Text(
                        text = tag,
                        modifier = Modifier.padding(horizontal = AppSpacing.Md, vertical = AppSpacing.Xs),
                        style = AppTypography.CaptionStrong,
                        color = contentColor,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                }
            }
        }
    }
}

@Composable
private fun ReviewFilterBar(
    selectedFilter: ReviewFilter,
    counts: ReviewFilterCounts,
    onFilterSelected: (ReviewFilter) -> Unit,
) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.spacedBy(AppSpacing.Sm),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        ReviewFilter.entries.forEach { filter ->
            ReviewFilterChip(
                label = filter.displayLabel(counts),
                selected = filter == selectedFilter,
                onClick = { onFilterSelected(filter) },
            )
        }
    }
}

@Composable
private fun ReviewFilterChip(
    label: String,
    selected: Boolean,
    onClick: () -> Unit,
) {
    Surface(
        modifier = Modifier.clickable(onClick = onClick),
        shape = RoundedCornerShape(AppRadius.Pill),
        color = if (selected) {
            AppColors.Primary
        } else {
            AppColors.SurfaceSoft
        },
    ) {
        Text(
            text = label,
            modifier = Modifier.padding(horizontal = AppSpacing.Md, vertical = AppSpacing.Sm),
            style = AppTypography.CaptionStrong,
            fontWeight = if (selected) FontWeight.SemiBold else FontWeight.Normal,
            color = if (selected) {
                AppColors.OnPrimary
            } else {
                AppColors.TextSecondary
            },
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
        )
    }
}

@Composable
private fun ReviewListItem(review: ProductReviewUiModel) {
    var expanded by rememberSaveable(review.content) { mutableStateOf(false) }
    Column(
        modifier = Modifier.fillMaxWidth(),
        verticalArrangement = Arrangement.spacedBy(AppSpacing.Sm),
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(AppSpacing.Sm),
        ) {
            review.nickname.cleanNullable()?.let {
                Text(
                    text = it,
                    style = AppTypography.BodyStrong,
                    fontWeight = FontWeight.SemiBold,
                    color = AppColors.TextPrimary,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                    modifier = Modifier.weight(1f),
                )
            } ?: Spacer(modifier = Modifier.weight(1f))
            review.rating?.let {
                RatingStars(rating = it, iconSize = 15, spacing = 0)
            }
        }
        val meta = review.displayMeta()
        if (meta.isNotEmpty()) {
            FlowRow(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(AppSpacing.Sm),
                verticalArrangement = Arrangement.spacedBy(AppSpacing.Xs),
            ) {
                meta.forEach { item ->
                    Text(
                        text = item,
                        style = AppTypography.Caption,
                        color = AppColors.TextTertiary,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                }
            }
        }
        ExpandableReviewBody(
            text = review.content.cleanReviewText(),
            expanded = expanded,
            onToggle = { expanded = !expanded },
        )
    }
}

@Composable
private fun ExpandableReviewBody(
    text: String,
    expanded: Boolean,
    onToggle: () -> Unit,
) {
    var hasOverflow by remember(text) { mutableStateOf(false) }
    Column(verticalArrangement = Arrangement.spacedBy(AppSpacing.Xs)) {
        Text(
            text = text,
            style = AppTypography.Body,
            color = AppColors.TextPrimary,
            maxLines = if (expanded) Int.MAX_VALUE else 4,
            overflow = TextOverflow.Ellipsis,
            onTextLayout = { layoutResult ->
                if (!expanded) {
                    hasOverflow = layoutResult.hasVisualOverflow
                }
            },
        )
        if (hasOverflow || expanded) {
            Text(
                text = if (expanded) "收起" else "展开全文",
                style = AppTypography.CaptionStrong,
                color = AppColors.TextPrimary,
                modifier = Modifier
                    .clickable(onClick = onToggle)
                    .padding(vertical = AppSpacing.Xs),
            )
        }
    }
}

@Composable
private fun ReviewEmptyState(filter: ReviewFilter) {
    val text = when (filter) {
        ReviewFilter.All -> "暂无评价"
        ReviewFilter.Positive -> "暂无好评"
        ReviewFilter.Negative -> "暂无差评"
    }
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .background(
                color = AppColors.SurfaceSoft,
                shape = RoundedCornerShape(AppRadius.Medium),
            )
            .padding(vertical = AppSpacing.Xl),
        contentAlignment = Alignment.Center,
    ) {
        Text(
            text = text,
            style = AppTypography.BodySmall,
            color = AppColors.TextSecondary,
        )
    }
}

@Composable
private fun RatingStars(
    rating: Double,
    iconSize: Int,
    spacing: Int,
) {
    val halfSteps = (rating.coerceIn(0.0, 5.0) * 2).roundToInt()
    Row(
        horizontalArrangement = Arrangement.spacedBy(spacing.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        repeat(5) { index ->
            val starStep = (index + 1) * 2
            val iconRes = when {
                halfSteps >= starStep -> R.drawable.ic_star_20
                halfSteps == starStep - 1 -> R.drawable.ic_star_half_20
                else -> R.drawable.ic_star_border_20
            }
            Icon(
                painter = painterResource(iconRes),
                contentDescription = null,
                modifier = Modifier.size(iconSize.dp),
                tint = AppColors.AccentWarm,
            )
        }
    }
}

@Composable
private fun ScenarioAudienceSection(
    product: ProductUiModel,
    modifier: Modifier = Modifier,
) {
    val core = product.coreTags().toSet()
    val scenarios = product.suitableScenarios.cleanDisplayTags(exclude = core).take(6)
    val audiences = (product.targetUserTags + product.nonStandardQueryTags)
        .cleanDisplayTags(exclude = core + scenarios.toSet())
        .take(6)
    if (scenarios.isEmpty() && audiences.isEmpty()) {
        return
    }
    DetailSection(title = "适用场景与人群", modifier = modifier) {
        if (scenarios.isNotEmpty()) {
            Text(
                text = "适合场景",
                style = AppTypography.CaptionStrong,
                color = AppColors.TextPrimary,
                fontWeight = FontWeight.SemiBold,
            )
            CompactTagRow(tags = scenarios, maxItems = 5)
        }
        if (audiences.isNotEmpty()) {
            Text(
                text = "适合人群",
                style = AppTypography.CaptionStrong,
                color = AppColors.TextPrimary,
                fontWeight = FontWeight.SemiBold,
            )
            CompactTagRow(tags = audiences, maxItems = 5)
        }
    }
}

@Composable
private fun CompactTagRow(
    tags: List<String>,
    maxItems: Int,
) {
    val displayTags = tags.cleanDisplayTags().take(maxItems)
    val hasMore = tags.cleanDisplayTags().size > maxItems
    FlowRow(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.spacedBy(AppSpacing.Sm),
        verticalArrangement = Arrangement.spacedBy(AppSpacing.Sm),
    ) {
        displayTags.forEach { tag ->
            TagChip(text = tag)
        }
        if (hasMore) {
            TagChip(text = "更多")
        }
    }
}

@Composable
private fun DetailSection(
    title: String,
    modifier: Modifier = Modifier,
    trailing: @Composable (() -> Unit)? = null,
    content: @Composable () -> Unit,
) {
    Column(
        modifier = modifier.fillMaxWidth(),
        verticalArrangement = Arrangement.spacedBy(AppSpacing.Md),
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(AppSpacing.Sm),
        ) {
            Text(
                text = title,
                style = AppTypography.TitleSmall,
                color = AppColors.TextPrimary,
                fontWeight = FontWeight.Bold,
                modifier = Modifier.weight(1f),
            )
            trailing?.invoke()
        }
        HorizontalDivider(color = AppColors.Divider)
        content()
    }
}

private data class ReviewDisplay(
    val rating: Double?,
    val reviewCount: Int?,
    val summary: String,
    val positives: List<String>,
    val concerns: List<String>,
    val reviews: List<ProductReviewUiModel>,
    val filterCounts: ReviewFilterCounts,
)

private data class ReviewFilterCounts(
    val all: Int? = null,
    val positive: Int? = null,
    val negative: Int? = null,
)

private data class ReviewTagRule(
    val label: String,
    val concern: Boolean,
    val pattern: Regex,
)

private enum class ReviewFilter {
    All,
    Positive,
    Negative,
}

private enum class ReviewTagTone {
    Positive,
    Concern,
}

private fun ProductUiModel.detailImages(): List<String> {
    val primaryImageUrl = detailImageUrl.cleanNullable() ?: imageUrl
    return listOf(primaryImageUrl)
        .map { it.trim() }
        .filter { it.isNotBlank() }
        .distinct()
}

private fun ProductUiModel.detailFallbackImages(): List<String> {
    val primaryImageUrl = detailImageUrl.cleanNullable()
    val fallbackImageUrl = imageUrl.cleanNullable()
    return when {
        primaryImageUrl == null -> emptyList()
        fallbackImageUrl == null -> emptyList()
        primaryImageUrl == fallbackImageUrl -> emptyList()
        else -> listOf(fallbackImageUrl)
    }
}

private fun ProductUiModel.heroTitle(): String {
    return listOfNotNull(
        presentation?.shortTitle.heroTitleCandidate(),
        shortTitle.heroTitleCandidate(),
        highlightShort.heroTitleCandidate(),
        brandCoreHeroTitle(),
        displayTitle.cleanNullable(),
    ).firstOrNull().orEmpty()
        .ifBlank { displayTitle }
}

private fun String?.heroTitleCandidate(): String? {
    val raw = cleanNullable() ?: return null
    val candidate = raw
        .split(*HERO_TITLE_DELIMITERS)
        .firstOrNull()
        ?.cleanNullable()
        ?: raw
    return candidate
        .removeMarketingPrefix()
        .cleanNullable()
        ?.takeIf { it.length <= 24 }
}

private fun String.removeMarketingPrefix(): String {
    return replace(
        Regex(
            """^(\u63A8\u8350\u7406\u7531|\u4EAE\u70B9|\u5356\u70B9|\u6838\u5FC3\u4F18\u52BF)\s*[:\uFF1A]\s*""",
        ),
        "",
    )
        .replace(Regex("""\s{2,}"""), " ")
        .trim()
}

private fun ProductUiModel.brandCoreHeroTitle(): String? {
    val brandValue = brand.cleanNullable()
    val titleValue = displayTitleShort.cleanNullable() ?: displayTitle.cleanNullable() ?: return null
    val normalized = titleValue
        .replace(
            Regex(
                """\d+(?:\.\d+)?\s*(ml|mL|ML|g|G|kg|KG|L|l|\u7247|\u7C92|\u652F|\u74F6|\u888B|\u76D2|\u5305|GB|TB)""",
            ),
            "",
        )
        .replace(Regex("""SPF\s*\d+\+?\s*PA\+*""", RegexOption.IGNORE_CASE), "")
        .replace(Regex("""\s{2,}"""), " ")
        .trim()
    val titleWithoutBrand = brandValue
        ?.let { normalized.removePrefix(it).trim() }
        ?: normalized
    val coreName = PRODUCT_HERO_CORE_KEYWORDS
        .firstNotNullOfOrNull { keyword ->
            val endIndex = titleWithoutBrand.indexOf(keyword)
                .takeIf { it >= 0 }
                ?.plus(keyword.length)
            endIndex
                ?.let { titleWithoutBrand.take(it) }
                ?.cleanNullable()
        }
    val candidate = when {
        brandValue != null && coreName != null -> {
            "$brandValue$coreName"
        }
        normalized.length <= 24 -> normalized
        else -> null
    }
    return candidate
        ?.replace(Regex("""(.{2,}?)\1+"""), "\$1")
        ?.cleanNullable()
        ?.takeIf { it.length <= 24 }
}

private fun ProductUiModel.defaultSelectedSkuId(routeSkuId: String): String? {
    return skus.firstOrNull { it.skuId == routeSkuId }?.skuId
        ?: skus.firstOrNull()?.skuId
}

private fun ProductUiModel.selectedSku(
    selectedSkuId: String?,
    routeSkuId: String,
): ProductSkuUiModel? {
    return skus.firstOrNull { it.skuId == selectedSkuId }
        ?: skus.firstOrNull { it.skuId == routeSkuId }
        ?: skus.firstOrNull()
}

private fun ProductSkuUiModel.specSummary(): String {
    return properties.entries
        .sortedBy { it.key }
        .map { it.value }
        .map { it.trim() }
        .filter { it.isNotBlank() }
        .distinct()
        .joinToString(" / ")
}

private fun ProductUiModel.findSkuForOption(
    currentSku: ProductSkuUiModel?,
    key: String,
    value: String,
): ProductSkuUiModel? {
    val currentProperties = currentSku?.properties.orEmpty()
    return skus.firstOrNull { sku ->
        sku.properties[key] == value &&
            currentProperties.all { (otherKey, otherValue) ->
                otherKey == key || sku.properties[otherKey] == otherValue
            }
    } ?: skus.firstOrNull { it.properties[key] == value }
}

private fun ProductUiModel.hasAnySkuForOption(key: String, value: String): Boolean {
    return skus.any { sku -> sku.properties[key] == value }
}

private fun ProductUiModel.coreTags(): List<String> {
    return (tags + spotlight.features + suitableScenarios + targetUserTags)
        .cleanDisplayTags()
        .take(3)
}

private fun ProductUiModel.productTags(): List<String> {
    return (tags + spotlight.features + matchedReasons + suitableScenarios + targetUserTags)
        .cleanDisplayTags()
        .take(8)
}

private fun ProductUiModel.aiAccentTags(): List<String> {
    return (matchedReasons + spotlight.features + presentation?.advantages.orEmpty())
        .cleanDisplayTags()
}

private fun ProductUiModel.guideReason(): String {
    return listOfNotNull(
        presentation?.reason.cleanNullable(),
        reason.cleanNullable(),
        highlightDetail.cleanNullable(),
        productHighlight.cleanNullable(),
        highlightShort.cleanNullable(),
        spotlight.description.cleanNullable(),
    ).firstOrNull().orEmpty()
}

private fun ProductUiModel.missingSpecPrompt(selectedSku: ProductSkuUiModel?): String {
    val allKeys = skus
        .flatMap { it.properties.keys }
        .map { it.trim() }
        .filter { it.isNotBlank() }
        .distinct()
    if (allKeys.isEmpty()) {
        return "请选择商品规格"
    }
    val selectedKeys = selectedSku?.properties
        ?.filter { it.key.isNotBlank() && it.value.isNotBlank() }
        ?.keys
        .orEmpty()
    val missing = allKeys.filterNot { it in selectedKeys }.ifEmpty { allKeys.take(1) }
    return "请选择${missing.joinToString("和")}"
}

private fun ProductUiModel.shareText(selectedSku: ProductSkuUiModel?): String {
    val lines = buildList {
        add(displayTitle)
        brand.cleanNullable()?.let { add("品牌：$it") }
        selectedSku?.specSummary()?.takeIf { it.isNotBlank() }?.let { add("规格：$it") }
        add("价格：¥${formatPrice(selectedSku?.price ?: price)}")
        reason.cleanNullable()?.let { add("推荐理由：$it") }
    }
    return lines.joinToString(separator = "\n")
}

private fun ProductUiModel.detailRating(): Double? {
    val reviewAverage = reviews
        .mapNotNull { it.rating }
        .takeIf { it.isNotEmpty() }
        ?.average()
        ?.coerceIn(0.0, 5.0)
    if (reviewAverage != null) {
        return reviewAverage
    }
    return RATING_PATTERN.find(reviewsSummary)
        ?.groupValues
        ?.getOrNull(1)
        ?.toDoubleOrNull()
        ?.coerceIn(0.0, 5.0)
        ?: score?.takeIf { it in 0.0..5.0 }
}

private fun ProductUiModel.coreParameters(selectedSku: ProductSkuUiModel?): List<Pair<String, String>> {
    val params = mutableListOf<Pair<String, String>>()
    if (brand.isNotBlank()) params += "品牌" to brand
    if (subCategory?.isNotBlank() == true) params += "品类" to subCategory
    if (category.isNotBlank()) params += "类目" to category
    selectedSku?.properties
        ?.filterKeys { !it.contains("价格") && !it.equals("price", ignoreCase = true) }
        ?.forEach { (key, value) ->
            if (key.isNotBlank() && value.isNotBlank()) {
                params += key to value
            }
        }
    spotlight.features
        .cleanDisplayTags()
        .take(2)
        .forEachIndexed { index, value ->
            params += "亮点${index + 1}" to value
        }
    params += "库存" to if (stock > 0) "现货" else "暂无库存"
    return params.distinctBy { it.first to it.second }
}

private fun splitReasonBullets(reason: String): List<String> {
    return reason
        .split(Regex("[。；;\\n]+"))
        .map { it.trim().trimStart('·', '-', '—') }
        .filter { it.length >= 4 }
        .distinct()
}

private fun parseReviewSummary(text: String, product: ProductUiModel): ReviewDisplay? {
    val summary = text.trim()
    val realReviews = product.reviews.filter { it.content.isNotBlank() }
    if (summary.isBlank() && realReviews.isEmpty()) {
        return null
    }

    if (realReviews.isNotEmpty()) {
        val ratings = realReviews.mapNotNull { it.rating }
        val rating = ratings.takeIf { it.isNotEmpty() }?.average()?.coerceIn(0.0, 5.0)
        val positiveReviews = realReviews.filter { it.reviewTone() == ReviewFilter.Positive }
        val negativeReviews = realReviews.filter { it.reviewTone() == ReviewFilter.Negative }
        val positives = reviewSummaryTags(
            reviews = positiveReviews,
            fallbackTexts = listOf(explicitReviewPart(summary, "好评提到：")),
            concern = false,
        )
        val concerns = reviewSummaryTags(
            reviews = negativeReviews,
            fallbackTexts = listOf(explicitReviewPart(summary, "差评提醒：")),
            concern = true,
        )
        return ReviewDisplay(
            rating = rating,
            reviewCount = realReviews.size,
            summary = summary.cleanReviewText(),
            positives = positives,
            concerns = concerns,
            reviews = realReviews,
            filterCounts = ReviewFilterCounts(
                all = realReviews.size,
                positive = positiveReviews.size,
                negative = negativeReviews.size,
            ),
        )
    }

    val rating = RATING_PATTERN.find(summary)
        ?.groupValues
        ?.getOrNull(1)
        ?.toDoubleOrNull()
        ?.coerceIn(0.0, 5.0)
    val positives = reviewSummaryTags(
        reviews = emptyList(),
        fallbackTexts = listOf(explicitReviewPart(summary, "好评提到：")),
        concern = false,
    )
    val concerns = reviewSummaryTags(
        reviews = emptyList(),
        fallbackTexts = listOf(explicitReviewPart(summary, "差评提醒：")),
        concern = true,
    )
    if (rating == null && positives.isEmpty() && concerns.isEmpty()) return null
    return ReviewDisplay(
        rating = rating,
        reviewCount = null,
        summary = summary.cleanReviewText(),
        positives = positives,
        concerns = concerns,
        reviews = emptyList(),
        filterCounts = ReviewFilterCounts(),
    )
}

private fun explicitReviewPart(summary: String, label: String): String {
    if (!summary.contains(label)) {
        return ""
    }
    return summary.substringAfter(label)
        .substringBefore("；")
        .substringBefore(";")
        .cleanReviewText()
}

private fun String.cleanReviewText(): String {
    return trim()
        .trim('；', ';', '。', '，', ',', ' ')
        .replace(Regex("\\s+"), " ")
}

private fun List<ProductReviewUiModel>.filterBy(filter: ReviewFilter): List<ProductReviewUiModel> {
    return when (filter) {
        ReviewFilter.All -> this
        ReviewFilter.Positive -> filter { it.reviewTone() == ReviewFilter.Positive }
        ReviewFilter.Negative -> filter { it.reviewTone() == ReviewFilter.Negative }
    }
}

private fun ProductReviewUiModel.reviewTone(): ReviewFilter? {
    return when {
        (rating ?: return null) >= 4.0 -> ReviewFilter.Positive
        rating <= 2.0 -> ReviewFilter.Negative
        else -> null
    }
}

private fun ReviewFilter.displayLabel(counts: ReviewFilterCounts): String {
    val count = when (this) {
        ReviewFilter.All -> counts.all
        ReviewFilter.Positive -> counts.positive
        ReviewFilter.Negative -> counts.negative
    }
    val label = when (this) {
        ReviewFilter.All -> "全部"
        ReviewFilter.Positive -> "好评"
        ReviewFilter.Negative -> "差评"
    }
    return count?.let { "$label $it" } ?: label
}

private fun ProductReviewUiModel.displayMeta(): List<String> {
    return buildList {
        userTags.cleanDisplayTags().take(2).forEach(::add)
        if (purchased == true) add("已购")
        createdAt.cleanNullable()?.let(::add)
    }
}

private fun reviewSummaryTags(
    reviews: List<ProductReviewUiModel>,
    fallbackTexts: List<String>,
    concern: Boolean,
): List<String> {
    val texts = (reviews.map { it.content } + fallbackTexts)
        .map { it.cleanReviewText() }
        .filter { it.isNotBlank() }
    if (texts.isEmpty()) return emptyList()

    val matched = REVIEW_TAG_RULES
        .filter { rule -> rule.concern == concern && texts.any { rule.pattern.containsMatchIn(it) } }
        .map { it.label }
        .distinct()

    val fallback = texts
        .flatMap { it.extractShortReviewPhrases(concern) }
        .distinct()

    return (matched + fallback)
        .map { if (concern) it.toConcernTag() else it }
        .map { it.trim() }
        .filter { it.length in 4..10 }
        .distinct()
        .take(4)
}

private fun String.extractShortReviewPhrases(concern: Boolean): List<String> {
    return split(Regex("[，。；,;！!、\\n]+"))
        .map { it.cleanReviewText() }
        .mapNotNull { phrase ->
            val compact = phrase
                .replace(Regex("^(真的|整体|就是|但是|而且|另外|感觉|用了|收到|这款|这个|可能|部分用户|少数用户)"), "")
                .replace(Regex("(太爱了|很明显|挺明显|很失望|有点失望|不满意|一般般)$"), "")
                .trim()
            when {
                compact.length in 4..10 && compact.hasReviewSignal(concern) -> compact
                else -> null
            }
        }
        .take(2)
}

private fun String.hasReviewSignal(concern: Boolean): Boolean {
    val pattern = if (concern) {
        CONCERN_FALLBACK_PATTERN
    } else {
        POSITIVE_FALLBACK_PATTERN
    }
    return pattern.containsMatchIn(this)
}

private fun String.toConcernTag(): String {
    val text = trim()
    return when {
        text.contains("敏感肌") && !text.contains("分歧") -> "敏感肌反馈分歧"
        text.contains("不适合") -> text.replace("不适合", "适配反馈分歧")
        text.contains("没效果") -> text.replace("没效果", "效果反馈有限")
        text.contains("无效") -> text.replace("无效", "效果反馈有限")
        text.contains("太贵") || text.contains("性价比") -> "性价比反馈一般"
        text.contains("刺激") || text.contains("刺痛") -> "刺激反馈需留意"
        text.contains("泛红") -> "泛红反馈需留意"
        text.contains("闭口") || text.contains("冒痘") -> "闭口反馈需留意"
        text.endsWith("不足") || text.endsWith("一般") || text.endsWith("偏弱") -> text
        else -> text
    }.take(10)
}

private fun List<String>.cleanDisplayTags(exclude: Set<String> = emptySet()): List<String> {
    return map { it.trim() }
        .filter { it.isNotBlank() }
        .filter { it.length <= 12 }
        .filterNot { it in exclude }
        .filterNot { QUESTION_PATTERN.containsMatchIn(it) }
        .filterNot { SENTENCE_PUNCTUATION.containsMatchIn(it) }
        .distinct()
}

private fun String?.cleanNullable(): String? {
    return this
        ?.trim()
        ?.takeIf { it.isNotBlank() && !it.equals("null", ignoreCase = true) }
}

private val QUESTION_PATTERN = Regex(
    "[?？]|吗|能不能|适不适合|为什么|怎么办|怎么|用什么|哪个|" +
        "有没有|会不会|可以不|行不行|值不值得|需不需要|能不能够|" +
        "如何|怎样|哪里|哪些|什么|谁|哪款|怎么样|好不好|多少|几时"
)

private val SENTENCE_PUNCTUATION = Regex("[。，！…；：]")
private val RATING_PATTERN = Regex("""评分约?([0-9]+(?:\.[0-9]+)?)/5""")
private val POSITIVE_FALLBACK_PATTERN = Regex(
    "吸收|清爽|不黏|不油|保湿|滋润|稳定|维稳|细腻|透亮|提亮|淡纹|紧致|舒服|轻薄|好喝|划算|方便|耐用|回购|推荐|效果|香|解腻|速干|防水|百搭|做工"
)
private val CONCERN_FALLBACK_PATTERN = Regex(
    "刺痛|刺激|泛红|过敏|闭口|冒痘|不适合|没效果|不明显|一般|太贵|性价比|浪费|失望|偏干|紧绷|漏|破|变形|压|淡|酸|苦|硌|磨|掉色|起球|偏窄"
)
private val REVIEW_TAG_RULES = listOf(
    ReviewTagRule("吸收较快", concern = false, pattern = Regex("吸收")),
    ReviewTagRule("肤感不黏腻", concern = false, pattern = Regex("不黏|黏腻少|不油|清爽")),
    ReviewTagRule("保湿反馈好", concern = false, pattern = Regex("保湿|滋润|不干")),
    ReviewTagRule("维稳反馈好", concern = false, pattern = Regex("稳定|维稳|不敏感")),
    ReviewTagRule("提亮反馈好", concern = false, pattern = Regex("提亮|透亮|不暗沉|肤色")),
    ReviewTagRule("细腻毛孔", concern = false, pattern = Regex("毛孔|细腻")),
    ReviewTagRule("淡纹反馈好", concern = false, pattern = Regex("淡纹|干纹|紧致")),
    ReviewTagRule("使用方便", concern = false, pattern = Regex("方便|便携|顺手|好打开")),
    ReviewTagRule("性价比反馈好", concern = false, pattern = Regex("性价比|划算|值")),
    ReviewTagRule("愿意回购", concern = false, pattern = Regex("回购|再买|复购|推荐")),
    ReviewTagRule("敏感肌反馈分歧", concern = true, pattern = Regex("敏感肌|过敏|泛红|刺痛|刺激")),
    ReviewTagRule("效果反馈有限", concern = true, pattern = Regex("没效果|无效|不明显|没看到|谈不上")),
    ReviewTagRule("性价比反馈一般", concern = true, pattern = Regex("性价比|太贵|价格|不值|浪费")),
    ReviewTagRule("肤感反馈分歧", concern = true, pattern = Regex("黏|油|偏干|紧绷|闷|厚")),
    ReviewTagRule("包装反馈需留意", concern = true, pattern = Regex("包装|瓶口|按压|漏|破|压|变形")),
    ReviewTagRule("适配反馈分歧", concern = true, pattern = Regex("不适合|不耐受|闲置")),
)
