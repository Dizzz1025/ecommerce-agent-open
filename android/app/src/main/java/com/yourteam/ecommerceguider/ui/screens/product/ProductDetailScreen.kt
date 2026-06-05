@file:OptIn(ExperimentalMaterial3Api::class, ExperimentalLayoutApi::class)

package com.yourteam.ecommerceguider.ui.screens.product

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.AssistChip
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.yourteam.ecommerceguider.data.model.ProductUiModel
import com.yourteam.ecommerceguider.ui.components.ProductImage
import com.yourteam.ecommerceguider.ui.components.ProductTagRow
import com.yourteam.ecommerceguider.ui.components.formatPrice
import com.yourteam.ecommerceguider.viewmodel.ProductDetailViewModel
import com.yourteam.ecommerceguider.viewmodel.simpleViewModelFactory

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
    val snackbarHostState = remember { SnackbarHostState() }

    LaunchedEffect(skuId) {
        viewModel.loadProduct(skuId)
    }

    LaunchedEffect(cartMessage) {
        cartMessage?.let {
            snackbarHostState.showSnackbar(it)
            viewModel.clearCartMessage()
        }
    }

    Scaffold(
        snackbarHost = { SnackbarHost(snackbarHostState) },
        topBar = {
            DetailTopBar(
                onBack = onBack,
                onCartClick = onCartClick,
            )
        },
        bottomBar = {
            DetailBottomBar(
                product = product,
                onAddToCart = { viewModel.addToCart(skuId) },
                onCartClick = onCartClick,
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
                    modifier = Modifier.padding(innerPadding),
                )
            }
        }
    }
}

@Composable
private fun DetailTopBar(
    onBack: () -> Unit,
    onCartClick: () -> Unit,
) {
    Surface(
        color = MaterialTheme.colorScheme.surface,
        shadowElevation = 2.dp,
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 16.dp, vertical = 14.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            AssistChip(onClick = onBack, label = { Text("返回") })
            Text(
                text = "商品详情",
                style = MaterialTheme.typography.titleLarge,
                fontWeight = FontWeight.Bold,
                modifier = Modifier.weight(1f),
            )
            AssistChip(onClick = onCartClick, label = { Text("购物车") })
        }
    }
}

@Composable
private fun ProductDetailContent(
    product: ProductUiModel,
    modifier: Modifier = Modifier,
) {
    LazyColumn(
        modifier = modifier
            .fillMaxSize()
            .padding(horizontal = 16.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        item {
            ProductImage(
                imageUrl = product.imageUrl,
                contentDescription = product.displayTitle,
                modifier = Modifier
                    .fillMaxWidth()
                    .height(300.dp)
                    .padding(top = 16.dp),
                cornerRadius = 30.dp,
            )
        }
        item { CoreInfoCard(product) }
        item { HighlightCard(product) }
        item { SkuCard(product) }
        item { FactsCard(product) }
        item { Spacer(modifier = Modifier.height(96.dp)) }
    }
}

@Composable
private fun CoreInfoCard(product: ProductUiModel) {
    Card(
        shape = RoundedCornerShape(28.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        modifier = Modifier.fillMaxWidth(),
    ) {
        Column(
            modifier = Modifier.padding(18.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            Text(
                text = product.displayTitle,
                style = MaterialTheme.typography.titleLarge,
                fontWeight = FontWeight.Bold,
            )
            Text(
                text = "¥${formatPrice(product.price)}",
                style = MaterialTheme.typography.headlineSmall,
                fontWeight = FontWeight.Bold,
                color = MaterialTheme.colorScheme.primary,
            )
            ProductTagRow(product.displayTags)
            InfoRow("品牌", product.brand)
            InfoRow("类目", listOfNotNull(product.category, product.subCategory).joinToString(" / "))
            InfoRow("库存", if (product.stock > 0) "现货 ${product.stock} 件" else "暂无库存")
        }
    }
}

@Composable
private fun HighlightCard(product: ProductUiModel) {
    val primaryText = product.highlightDetail.ifBlank {
        product.highlightShort.ifBlank {
            product.productHighlight.ifBlank {
                product.spotlight.description
            }
        }
    }
    val reviewsText = product.reviewsSummary.takeIf { it.isNotBlank() }
    val features = product.spotlight.features.take(6)
    if (primaryText.isBlank() && reviewsText == null && features.isEmpty()) {
        return
    }

    var reasonExpanded by remember { mutableStateOf(false) }
    var reasonHasOverflow by remember { mutableStateOf(false) }
    var reviewsExpanded by remember { mutableStateOf(false) }
    var reviewsHasOverflow by remember { mutableStateOf(false) }

    DetailSectionCard(title = "推荐依据") {
        // ── AI 推荐理由 ──
        if (primaryText.isNotBlank()) {
            SectionLabel("AI 推荐理由")
            Text(
                text = primaryText,
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                maxLines = if (reasonExpanded) Int.MAX_VALUE else 3,
                overflow = TextOverflow.Ellipsis,
                onTextLayout = { layoutResult ->
                    if (!reasonExpanded && layoutResult.hasVisualOverflow) {
                        reasonHasOverflow = true
                    }
                },
            )
            if (reasonHasOverflow || reasonExpanded) {
                Text(
                    text = if (reasonExpanded) "收起" else "展开",
                    style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.primary,
                    modifier = Modifier
                        .clickable { reasonExpanded = !reasonExpanded }
                        .padding(vertical = 8.dp),
                )
            }
        }

        // ── 用户评分与口碑 ──
        if (reviewsText != null) {
            Spacer(modifier = Modifier.height(12.dp))
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(1.dp)
                    .background(MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.3f)),
            )
            Spacer(modifier = Modifier.height(10.dp))
            SectionLabel("用户评分与口碑")
            Text(
                text = reviewsText,
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.85f),
                maxLines = if (reviewsExpanded) Int.MAX_VALUE else 2,
                overflow = TextOverflow.Ellipsis,
                onTextLayout = { layoutResult ->
                    if (!reviewsExpanded && layoutResult.hasVisualOverflow) {
                        reviewsHasOverflow = true
                    }
                },
            )
            if (reviewsHasOverflow || reviewsExpanded) {
                Text(
                    text = if (reviewsExpanded) "收起" else "展开",
                    style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.primary,
                    modifier = Modifier
                        .clickable { reviewsExpanded = !reviewsExpanded }
                        .padding(vertical = 8.dp),
                )
            }
        }

        // ── 亮点标签 ──
        if (features.isNotEmpty()) {
            Spacer(modifier = Modifier.height(10.dp))
            ProductTagRow(features)
        }
    }
}

@Composable
private fun SectionLabel(text: String) {
    Text(
        text = text,
        style = MaterialTheme.typography.labelLarge,
        fontWeight = FontWeight.SemiBold,
        color = MaterialTheme.colorScheme.primary,
        modifier = Modifier.padding(bottom = 4.dp),
    )
}

@Composable
private fun SkuCard(product: ProductUiModel) {
    if (product.skus.isEmpty()) {
        return
    }
    DetailSectionCard(title = "规格参数") {
        product.skus.forEach { sku ->
            Card(
                colors = CardDefaults.cardColors(
                    containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.4f),
                ),
                shape = RoundedCornerShape(18.dp),
            ) {
                Column(
                    modifier = Modifier.padding(12.dp),
                    verticalArrangement = Arrangement.spacedBy(6.dp),
                ) {
                    InfoRow("价格", "¥${formatPrice(sku.price)}")
                    sku.properties.forEach { (key, value) ->
                        InfoRow(key, value)
                    }
                }
            }
        }
    }
}

@Composable
private fun FactsCard(product: ProductUiModel) {
    val scenarioTags = (product.suitableScenarios + product.targetUserTags + product.nonStandardQueryTags)
        .filter { tag -> tag.isNotBlank() && tag.length <= 12 }
        .filter { tag -> !QUESTION_PATTERN.containsMatchIn(tag) }
        .filter { tag -> !SENTENCE_PUNCTUATION.containsMatchIn(tag) }
        .distinct()
        .take(10)
    if (scenarioTags.isEmpty()) {
        return
    }
    DetailSectionCard(title = "适用场景 / 人群") {
        FlowRow(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(6.dp),
            verticalArrangement = Arrangement.spacedBy(6.dp),
        ) {
            scenarioTags.forEach { tag ->
                Surface(
                    shape = RoundedCornerShape(999.dp),
                    color = MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.55f),
                ) {
                    Text(
                        text = tag,
                        modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp),
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onPrimaryContainer,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                }
            }
        }
    }
}

private val QUESTION_PATTERN = Regex(
    "[?？]|吗|能不能|适不适合|为什么|怎么办|怎么|用什么|哪个|" +
    "有没有|会不会|可以不|行不行|值不值得|需不需要|能不能够|" +
    "如何|怎样|哪里|哪些|什么|谁|哪款|怎么样|好不好|多少|几时"
)

private val SENTENCE_PUNCTUATION = Regex("[。，！…、；：]")

@Composable
private fun DetailSectionCard(
    title: String,
    content: @Composable ColumnScope.() -> Unit,
) {
    Card(
        shape = RoundedCornerShape(26.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        modifier = Modifier.fillMaxWidth(),
    ) {
        Column(
            modifier = Modifier.padding(18.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            Text(
                text = title,
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Bold,
            )
            content()
        }
    }
}

@Composable
private fun InfoRow(label: String, value: String) {
    if (value.isBlank()) {
        return
    }
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Text(
            text = label,
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            modifier = Modifier.size(width = 72.dp, height = 22.dp),
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
        )
        Text(
            text = value,
            style = MaterialTheme.typography.bodyMedium,
            modifier = Modifier.weight(1f),
        )
    }
}

@Composable
private fun DetailBottomBar(
    product: ProductUiModel?,
    onAddToCart: () -> Unit,
    onCartClick: () -> Unit,
) {
    Surface(
        color = MaterialTheme.colorScheme.surface,
        shadowElevation = 8.dp,
        modifier = Modifier.navigationBarsPadding(),
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            horizontalArrangement = Arrangement.spacedBy(10.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = product?.let { "¥${formatPrice(it.price)}" } ?: "加载中",
                    style = MaterialTheme.typography.titleLarge,
                    color = MaterialTheme.colorScheme.primary,
                    fontWeight = FontWeight.Bold,
                )
                Text(
                    text = "价格来自后端商品详情",
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
            OutlinedButton(
                onClick = onCartClick,
                shape = RoundedCornerShape(999.dp),
            ) {
                Text("去购物车")
            }
            Button(
                onClick = onAddToCart,
                enabled = product != null,
                shape = RoundedCornerShape(999.dp),
                colors = ButtonDefaults.buttonColors(
                    containerColor = MaterialTheme.colorScheme.primary,
                ),
            ) {
                Text("加入购物车")
            }
        }
    }
}
