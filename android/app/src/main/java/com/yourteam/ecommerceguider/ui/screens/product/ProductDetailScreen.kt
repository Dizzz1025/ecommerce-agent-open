@file:OptIn(ExperimentalMaterial3Api::class, ExperimentalLayoutApi::class)

package com.yourteam.ecommerceguider.ui.screens.product

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Badge
import androidx.compose.material3.BadgedBox
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.rotate
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.yourteam.ecommerceguider.R
import com.yourteam.ecommerceguider.data.model.ProductReviewUiModel
import com.yourteam.ecommerceguider.data.model.ProductSkuUiModel
import com.yourteam.ecommerceguider.data.model.ProductUiModel
import com.yourteam.ecommerceguider.ui.components.ProductImage
import com.yourteam.ecommerceguider.ui.components.formatPrice
import com.yourteam.ecommerceguider.viewmodel.ProductDetailViewModel
import com.yourteam.ecommerceguider.viewmodel.simpleViewModelFactory
import kotlin.math.roundToInt

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
    val cartMessage by viewModel.cartMessage.collectAsState()
    val cartItemCount by viewModel.cartItemCount.collectAsState()
    val snackbarHostState = remember { SnackbarHostState() }
    var selectedSkuId by rememberSaveable(skuId) { mutableStateOf<String?>(null) }
    var selectedReviewFilter by rememberSaveable(skuId) { mutableStateOf(ReviewFilter.All) }

    LaunchedEffect(skuId) {
        viewModel.loadProduct(skuId)
    }

    LaunchedEffect(product?.skuId) {
        val currentProduct = product ?: return@LaunchedEffect
        selectedSkuId = currentProduct.defaultSelectedSkuId(routeSkuId = skuId)
    }

    LaunchedEffect(cartMessage) {
        cartMessage?.let {
            snackbarHostState.showSnackbar(it)
            viewModel.clearCartMessage()
        }
    }

    val selectedSku = product?.selectedSku(selectedSkuId, routeSkuId = skuId)
    val displayPrice = selectedSku?.price ?: product?.price

    Scaffold(
        snackbarHost = { SnackbarHost(snackbarHostState) },
        topBar = {
            DetailTopBar(
                cartItemCount = cartItemCount,
                onBack = onBack,
                onCartClick = onCartClick,
            )
        },
        bottomBar = {
            DetailBottomBar(
                price = displayPrice,
                inStock = product?.stock?.let { it > 0 } ?: false,
                onAddToCart = {
                    product?.let { viewModel.addToCart(it, selectedSku) }
                },
            )
        },
        containerColor = MaterialTheme.colorScheme.background,
    ) { innerPadding ->
        when {
            isLoading -> {
                Box(
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(innerPadding),
                    contentAlignment = Alignment.Center,
                ) {
                    CircularProgressIndicator()
                }
            }

            error != null -> {
                Box(
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(innerPadding)
                        .padding(24.dp),
                    contentAlignment = Alignment.Center,
                ) {
                    Text(
                        text = error.orEmpty(),
                        style = MaterialTheme.typography.bodyLarge,
                        color = MaterialTheme.colorScheme.error,
                    )
                }
            }

            product != null -> {
                ProductDetailContent(
                    product = product!!,
                    selectedSku = selectedSku,
                    selectedSkuId = selectedSkuId,
                    onSkuSelected = { selectedSkuId = it },
                    selectedReviewFilter = selectedReviewFilter,
                    onReviewFilterSelected = { selectedReviewFilter = it },
                    modifier = Modifier.padding(innerPadding),
                )
            }
        }
    }
}

@Composable
private fun DetailTopBar(
    cartItemCount: Int,
    onBack: () -> Unit,
    onCartClick: () -> Unit,
) {
    TopAppBar(
        title = {
            Text(
                text = "商品详情",
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
        },
        navigationIcon = {
            IconButton(onClick = onBack) {
                Icon(
                    painter = painterResource(R.drawable.ic_chevron_right_20),
                    contentDescription = "返回",
                    modifier = Modifier.rotate(180f),
                )
            }
        },
        actions = {
            BadgedBox(
                badge = {
                    if (cartItemCount > 0) {
                        Badge { Text(cartItemCount.coerceAtMost(99).toString()) }
                    }
                },
            ) {
                IconButton(onClick = onCartClick) {
                    Icon(
                        painter = painterResource(R.drawable.ic_cart_24),
                        contentDescription = "购物车",
                    )
                }
            }
        },
        colors = TopAppBarDefaults.topAppBarColors(
            containerColor = MaterialTheme.colorScheme.surface,
        ),
    )
}

@Composable
private fun ProductDetailContent(
    product: ProductUiModel,
    selectedSku: ProductSkuUiModel?,
    selectedSkuId: String?,
    onSkuSelected: (String) -> Unit,
    selectedReviewFilter: ReviewFilter,
    onReviewFilterSelected: (ReviewFilter) -> Unit,
    modifier: Modifier = Modifier,
) {
    LazyColumn(
        modifier = modifier.fillMaxSize(),
        contentPadding = PaddingValues(bottom = 112.dp),
        verticalArrangement = Arrangement.spacedBy(22.dp),
    ) {
        item { ProductImageCarousel(product = product) }
        item {
            ProductBasicInfo(
                product = product,
                selectedSku = selectedSku,
                modifier = Modifier.padding(horizontal = 16.dp),
            )
        }
        item {
            SmartGuideSection(
                product = product,
                modifier = Modifier.padding(horizontal = 16.dp),
            )
        }
        item {
            SpecificationSection(
                product = product,
                selectedSku = selectedSku,
                selectedSkuId = selectedSkuId,
                onSkuSelected = onSkuSelected,
                modifier = Modifier.padding(horizontal = 16.dp),
            )
        }
        item {
            CoreParametersSection(
                product = product,
                selectedSku = selectedSku,
                modifier = Modifier.padding(horizontal = 16.dp),
            )
        }
        item {
            UserReviewSection(
                product = product,
                selectedFilter = selectedReviewFilter,
                onFilterSelected = onReviewFilterSelected,
                modifier = Modifier.padding(horizontal = 16.dp),
            )
        }
        item {
            ScenarioAudienceSection(
                product = product,
                modifier = Modifier.padding(horizontal = 16.dp),
            )
        }
        item { Spacer(modifier = Modifier.height(12.dp)) }
    }
}

@Composable
private fun ProductImageCarousel(product: ProductUiModel) {
    val images = product.detailImages()
    val listState = rememberLazyListState()
    val currentIndex = listState.firstVisibleItemIndex.coerceIn(0, (images.size - 1).coerceAtLeast(0))

    Box(
        modifier = Modifier
            .fillMaxWidth()
            .height(304.dp)
            .background(MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f)),
    ) {
        if (images.isEmpty()) {
            ProductImage(
                imageUrl = "",
                contentDescription = product.displayTitle,
                modifier = Modifier.fillMaxSize(),
                cornerRadius = 0.dp,
                contentScale = ContentScale.Fit,
            )
        } else {
            LazyRow(
                state = listState,
                modifier = Modifier.fillMaxSize(),
            ) {
                itemsIndexed(images, key = { index, url -> "$index-$url" }) { _, imageUrl ->
                    ProductImage(
                        imageUrl = imageUrl,
                        contentDescription = product.displayTitle,
                        modifier = Modifier
                            .fillParentMaxWidth()
                            .fillMaxSize(),
                        cornerRadius = 0.dp,
                        contentScale = ContentScale.Fit,
                    )
                }
            }
        }

        if (images.size > 1) {
            Row(
                modifier = Modifier
                    .align(Alignment.BottomCenter)
                    .padding(bottom = 12.dp),
                horizontalArrangement = Arrangement.spacedBy(6.dp),
            ) {
                images.forEachIndexed { index, _ ->
                    Box(
                        modifier = Modifier
                            .size(if (index == currentIndex) 8.dp else 6.dp)
                            .background(
                                color = if (index == currentIndex) {
                                    MaterialTheme.colorScheme.primary
                                } else {
                                    MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.35f)
                                },
                                shape = CircleShape,
                            ),
                    )
                }
            }
        }
    }
}

@Composable
private fun ProductBasicInfo(
    product: ProductUiModel,
    selectedSku: ProductSkuUiModel?,
    modifier: Modifier = Modifier,
) {
    Column(
        modifier = modifier.fillMaxWidth(),
        verticalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        Text(
            text = product.displayTitle,
            style = MaterialTheme.typography.headlineSmall,
            fontWeight = FontWeight.Bold,
            maxLines = 3,
            overflow = TextOverflow.Ellipsis,
        )
        Text(
            text = "¥${formatPrice(selectedSku?.price ?: product.price)}",
            style = MaterialTheme.typography.headlineMedium,
            fontWeight = FontWeight.Bold,
            color = MaterialTheme.colorScheme.primary,
        )
        val tags = product.coreTags()
        if (tags.isNotEmpty()) {
            CompactTagRow(tags = tags, maxItems = 3)
        }
        val selectedText = selectedSku?.specSummary().orEmpty().ifBlank { "默认规格" }
        Text(
            text = "${if (product.stock > 0) "现货" else "暂无库存"} · 已选：$selectedText",
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
        )
        val meta = listOf(product.brand, product.subCategory ?: product.category)
            .filter { it.isNotBlank() }
            .distinct()
            .joinToString(" · ")
        if (meta.isNotBlank()) {
            Text(
                text = meta,
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
        }
    }
}

@Composable
private fun SmartGuideSection(
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

    Card(
        modifier = modifier.fillMaxWidth(),
        shape = RoundedCornerShape(12.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        elevation = CardDefaults.cardElevation(defaultElevation = 1.dp),
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.primary.copy(alpha = 0.18f)),
    ) {
        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Text(
                text = "智能导购建议",
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Bold,
            )
            if (reason.isNotBlank()) {
                Text(
                    text = "为什么适合你",
                    style = MaterialTheme.typography.labelLarge,
                    fontWeight = FontWeight.SemiBold,
                    color = MaterialTheme.colorScheme.primary,
                )
                if (reasonBullets.size >= 2) {
                    reasonBullets.take(3).forEach { item ->
                        Text(
                            text = "· $item",
                            style = MaterialTheme.typography.bodyMedium,
                            color = MaterialTheme.colorScheme.onSurface,
                        )
                    }
                } else {
                    Text(
                        text = reason,
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurface,
                        maxLines = if (expanded) Int.MAX_VALUE else 4,
                        overflow = TextOverflow.Ellipsis,
                    )
                    if (reason.length > 80) {
                        Text(
                            text = if (expanded) "收起" else "展开全文",
                            style = MaterialTheme.typography.labelMedium,
                            color = MaterialTheme.colorScheme.primary,
                            modifier = Modifier
                                .clickable { expanded = !expanded }
                                .padding(top = 2.dp),
                        )
                    }
                }
            }
            tradeOff?.let {
                HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.45f))
                Text(
                    text = "需要注意",
                    style = MaterialTheme.typography.labelLarge,
                    fontWeight = FontWeight.SemiBold,
                    color = MaterialTheme.colorScheme.primary,
                )
                Text(
                    text = it,
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
        }
    }
}

@Composable
private fun SpecificationSection(
    product: ProductUiModel,
    selectedSku: ProductSkuUiModel?,
    selectedSkuId: String?,
    onSkuSelected: (String) -> Unit,
    modifier: Modifier = Modifier,
) {
    if (product.skus.isEmpty()) {
        return
    }
    DetailSection(title = "规格选择", modifier = modifier) {
        val optionKeys = product.skus.flatMap { it.properties.keys }.distinct()
        if (optionKeys.isEmpty()) {
            FlowRow(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp),
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
            return@DetailSection
        }

        optionKeys.take(4).forEach { key ->
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text(
                    text = "选择$key",
                    style = MaterialTheme.typography.labelLarge,
                    fontWeight = FontWeight.SemiBold,
                )
                FlowRow(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    val values = product.skus.mapNotNull { it.properties[key] }
                        .filter { it.isNotBlank() }
                        .distinct()
                    values.forEach { value ->
                        val selected = selectedSku?.properties?.get(key) == value
                        val enabled = product.stock > 0 && product.findSkuForOption(
                            currentSku = selectedSku,
                            key = key,
                            value = value,
                        ) != null
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
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
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
            .heightIn(min = 38.dp)
            .clickable(enabled = enabled, onClick = onClick),
        shape = RoundedCornerShape(8.dp),
        color = when {
            selected -> MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.75f)
            enabled -> MaterialTheme.colorScheme.surface
            else -> MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.36f)
        },
        border = BorderStroke(
            width = 1.dp,
            color = when {
                selected -> MaterialTheme.colorScheme.primary
                enabled -> MaterialTheme.colorScheme.outlineVariant
                else -> MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.35f)
            },
        ),
    ) {
        Text(
            text = label,
            modifier = Modifier.padding(horizontal = 12.dp, vertical = 8.dp),
            style = MaterialTheme.typography.labelMedium,
            color = when {
                !enabled -> MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.55f)
                selected -> MaterialTheme.colorScheme.onPrimaryContainer
                else -> MaterialTheme.colorScheme.onSurface
            },
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
        )
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
        Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
            display.chunked(2).forEach { rowItems ->
                Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
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
                style = MaterialTheme.typography.labelMedium,
                color = MaterialTheme.colorScheme.primary,
                modifier = Modifier
                    .clickable { expanded = !expanded }
                    .padding(top = 2.dp),
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
                color = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.36f),
                shape = RoundedCornerShape(8.dp),
            )
            .padding(10.dp),
        verticalArrangement = Arrangement.spacedBy(4.dp),
    ) {
        Text(
            text = label,
            style = MaterialTheme.typography.labelSmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
        )
        Text(
            text = value,
            style = MaterialTheme.typography.bodyMedium,
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
                                modifier = Modifier.padding(vertical = 14.dp),
                                color = MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.45f),
                            )
                        }
                    }
                }
            }
        }
    }
}

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
            style = MaterialTheme.typography.labelMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
        )
        Icon(
            painter = painterResource(R.drawable.ic_chevron_right_20),
            contentDescription = null,
            modifier = Modifier.size(16.dp),
            tint = MaterialTheme.colorScheme.onSurfaceVariant,
        )
    }
}

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
            style = MaterialTheme.typography.headlineSmall,
            fontWeight = FontWeight.Bold,
            color = MaterialTheme.colorScheme.primary,
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
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
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
                color = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.28f),
                shape = RoundedCornerShape(10.dp),
            )
            .padding(12.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        Text(
            text = "评价总结",
            style = MaterialTheme.typography.labelLarge,
            fontWeight = FontWeight.SemiBold,
            color = MaterialTheme.colorScheme.onSurface,
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
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
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
    Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
        Text(
            text = title,
            style = MaterialTheme.typography.labelMedium,
            fontWeight = FontWeight.SemiBold,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        FlowRow(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(8.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            tags.forEach { tag ->
                val container = when (tone) {
                    ReviewTagTone.Positive -> MaterialTheme.colorScheme.secondaryContainer.copy(alpha = 0.52f)
                    ReviewTagTone.Concern -> MaterialTheme.colorScheme.surface
                }
                val contentColor = when (tone) {
                    ReviewTagTone.Positive -> MaterialTheme.colorScheme.onSecondaryContainer
                    ReviewTagTone.Concern -> MaterialTheme.colorScheme.onSurfaceVariant
                }
                val border = when (tone) {
                    ReviewTagTone.Positive -> null
                    ReviewTagTone.Concern -> BorderStroke(
                        width = 1.dp,
                        color = MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.65f),
                    )
                }
                Surface(
                    shape = RoundedCornerShape(999.dp),
                    color = container,
                    border = border,
                ) {
                    Text(
                        text = tag,
                        modifier = Modifier.padding(horizontal = 10.dp, vertical = 5.dp),
                        style = MaterialTheme.typography.labelMedium,
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
        horizontalArrangement = Arrangement.spacedBy(8.dp),
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
        shape = RoundedCornerShape(999.dp),
        color = if (selected) {
            MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.72f)
        } else {
            MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.42f)
        },
    ) {
        Text(
            text = label,
            modifier = Modifier.padding(horizontal = 14.dp, vertical = 8.dp),
            style = MaterialTheme.typography.labelMedium,
            fontWeight = if (selected) FontWeight.SemiBold else FontWeight.Normal,
            color = if (selected) {
                MaterialTheme.colorScheme.onPrimaryContainer
            } else {
                MaterialTheme.colorScheme.onSurfaceVariant
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
        verticalArrangement = Arrangement.spacedBy(7.dp),
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            review.nickname.cleanNullable()?.let {
                Text(
                    text = it,
                    style = MaterialTheme.typography.bodyMedium,
                    fontWeight = FontWeight.SemiBold,
                    color = MaterialTheme.colorScheme.onSurface,
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
                horizontalArrangement = Arrangement.spacedBy(8.dp),
                verticalArrangement = Arrangement.spacedBy(4.dp),
            ) {
                meta.forEach { item ->
                    Text(
                        text = item,
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
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
    Column(verticalArrangement = Arrangement.spacedBy(5.dp)) {
        Text(
            text = text,
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurface,
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
                style = MaterialTheme.typography.labelMedium,
                color = MaterialTheme.colorScheme.primary,
                modifier = Modifier
                    .clickable(onClick = onToggle)
                    .padding(vertical = 2.dp),
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
                color = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.28f),
                shape = RoundedCornerShape(8.dp),
            )
            .padding(vertical = 18.dp),
        contentAlignment = Alignment.Center,
    ) {
        Text(
            text = text,
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
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
                tint = MaterialTheme.colorScheme.primary,
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
                style = MaterialTheme.typography.labelLarge,
                fontWeight = FontWeight.SemiBold,
            )
            CompactTagRow(tags = scenarios, maxItems = 5)
        }
        if (audiences.isNotEmpty()) {
            Text(
                text = "适合人群",
                style = MaterialTheme.typography.labelLarge,
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
        horizontalArrangement = Arrangement.spacedBy(8.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        displayTags.forEach { tag ->
            Surface(
                shape = RoundedCornerShape(999.dp),
                color = MaterialTheme.colorScheme.secondaryContainer.copy(alpha = 0.55f),
            ) {
                Text(
                    text = tag,
                    modifier = Modifier.padding(horizontal = 10.dp, vertical = 5.dp),
                    style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.onSecondaryContainer,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
            }
        }
        if (hasMore) {
            Surface(
                shape = RoundedCornerShape(999.dp),
                color = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.55f),
            ) {
                Text(
                    text = "更多",
                    modifier = Modifier.padding(horizontal = 10.dp, vertical = 5.dp),
                    style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
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
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Text(
                text = title,
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Bold,
                modifier = Modifier.weight(1f),
            )
            trailing?.invoke()
        }
        HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.45f))
        content()
    }
}

@Composable
private fun DetailBottomBar(
    price: Double?,
    inStock: Boolean,
    onAddToCart: () -> Unit,
) {
    Surface(
        color = MaterialTheme.colorScheme.surface,
        shadowElevation = 8.dp,
        modifier = Modifier.navigationBarsPadding(),
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 16.dp, vertical = 12.dp),
            horizontalArrangement = Arrangement.spacedBy(12.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = price?.let { "¥${formatPrice(it)}" } ?: "加载中",
                    style = MaterialTheme.typography.titleLarge,
                    color = MaterialTheme.colorScheme.primary,
                    fontWeight = FontWeight.Bold,
                    maxLines = 1,
                )
                Text(
                    text = "当前价格",
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
            Button(
                onClick = onAddToCart,
                enabled = price != null && inStock,
                modifier = Modifier
                    .width(148.dp)
                    .heightIn(min = 48.dp),
                shape = RoundedCornerShape(999.dp),
                colors = ButtonDefaults.buttonColors(
                    containerColor = MaterialTheme.colorScheme.primary,
                ),
            ) {
                Text(
                    text = "加入购物车",
                    maxLines = 1,
                    softWrap = false,
                )
            }
        }
    }
}

private data class ReviewDisplay(
    val rating: Double?,
    val reviewCount: Int?,
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
    return listOf(imageUrl)
        .map { it.trim() }
        .filter { it.isNotBlank() }
        .distinct()
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

private fun ProductUiModel.coreTags(): List<String> {
    return (tags + spotlight.features + suitableScenarios + targetUserTags)
        .cleanDisplayTags()
        .take(3)
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
