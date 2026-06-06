@file:OptIn(androidx.compose.material3.ExperimentalMaterial3Api::class)

package com.yourteam.ecommerceguider.ui.screens.image

import android.content.ContentResolver
import android.graphics.BitmapFactory
import android.net.Uri
import android.provider.OpenableColumns
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.ImageBitmap
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.yourteam.ecommerceguider.ui.screens.chat.components.AssistantAnswerIntroCard
import com.yourteam.ecommerceguider.ui.screens.chat.components.FinalComparisonSummary
import com.yourteam.ecommerceguider.ui.screens.chat.components.RecommendationSection
import com.yourteam.ecommerceguider.ui.screens.chat.components.SpecSelectionCard
import com.yourteam.ecommerceguider.viewmodel.ChatViewModel
import com.yourteam.ecommerceguider.viewmodel.simpleViewModelFactory
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

private const val MAX_IMAGE_BYTES = 8L * 1024L * 1024L

@Composable
fun ImageSearchScreen(
    onBack: () -> Unit,
    onProductClick: (String) -> Unit,
    onCartClick: () -> Unit,
    viewModel: ChatViewModel = viewModel(factory = simpleViewModelFactory { ChatViewModel() }),
) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    val snackbarHostState = remember { SnackbarHostState() }
    val answer by viewModel.answer.collectAsState()
    val messages by viewModel.messages.collectAsState()
    val products by viewModel.products.collectAsState()
    val recommendationSections by viewModel.recommendationSections.collectAsState()
    val specSelections by viewModel.specSelections.collectAsState()
    val activeProductCardSpecSelection by viewModel.activeProductCardSpecSelection.collectAsState()
    val activeTurnId by viewModel.activeTurnId.collectAsState()
    val thinking by viewModel.thinking.collectAsState()
    val cartItemCount by viewModel.cartItemCount.collectAsState()
    val isStreaming by viewModel.isStreaming.collectAsState()
    val errorMessage by viewModel.errorMessage.collectAsState()

    var selectedImageUri by remember { mutableStateOf<Uri?>(null) }
    var selectedImageSize by remember { mutableStateOf<Long?>(null) }
    var previewBitmap by remember { mutableStateOf<ImageBitmap?>(null) }
    var prompt by rememberSaveable { mutableStateOf("") }
    var localError by remember { mutableStateOf<String?>(null) }
    var isCheckingImage by remember { mutableStateOf(false) }
    var hasSubmittedImageSearch by remember { mutableStateOf(false) }
    var thinkingExpanded by remember { mutableStateOf(false) }
    val activeRecommendationSections = remember(recommendationSections, activeTurnId) {
        recommendationSections.filter { section -> section.turnId == activeTurnId }
    }
    val visibleProducts = if (activeRecommendationSections.isNotEmpty()) {
        activeRecommendationSections.mapNotNull { it.product }
    } else {
        products
    }

    val pickImageLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.GetContent(),
    ) { uri ->
        if (uri == null) {
            return@rememberLauncherForActivityResult
        }
        scope.launch {
            isCheckingImage = true
            val imageSize = withContext(Dispatchers.IO) {
                context.contentResolver.getImageSize(uri)
            }
            isCheckingImage = false
            if (imageSize != null && imageSize > MAX_IMAGE_BYTES) {
                selectedImageUri = null
                selectedImageSize = null
                previewBitmap = null
                localError = "图片超过 8MB，请压缩后再上传。"
            } else {
                selectedImageUri = uri
                selectedImageSize = imageSize
                localError = null
            }
        }
    }

    LaunchedEffect(selectedImageUri) {
        previewBitmap = null
        val uri = selectedImageUri ?: return@LaunchedEffect
        previewBitmap = withContext(Dispatchers.IO) {
            context.contentResolver.decodePreviewBitmap(uri)
        }
        if (previewBitmap == null) {
            localError = "图片预览失败，请重新选择。"
        }
    }

    LaunchedEffect(errorMessage) {
        val message = errorMessage ?: return@LaunchedEffect
        snackbarHostState.showSnackbar(message)
    }

    LaunchedEffect(viewModel) {
        viewModel.cartTip.collect { snackbarHostState.showSnackbar(it) }
    }

    LaunchedEffect(answer) {
        if (answer.isNotBlank()) {
            thinkingExpanded = false
        }
    }

    Scaffold(
        snackbarHost = { SnackbarHost(snackbarHostState) },
        topBar = {
            TopAppBar(
                title = {
                    Text(
                        text = "拍图找同款",
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                },
                navigationIcon = {
                    TextButton(onClick = onBack) {
                        Text("返回")
                    }
                },
                actions = {
                    TextButton(onClick = onCartClick) {
                        Text("购物车 $cartItemCount")
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.surface,
                ),
            )
        },
        containerColor = MaterialTheme.colorScheme.background,
    ) { innerPadding ->
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .navigationBarsPadding()
                .imePadding()
                .padding(horizontal = 16.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp),
        ) {
            item {
                ImagePickerCard(
                    previewBitmap = previewBitmap,
                    imageSize = selectedImageSize,
                    localError = localError,
                    isCheckingImage = isCheckingImage,
                    isStreaming = isStreaming,
                    onPickImage = { pickImageLauncher.launch("image/*") },
                    onClearImage = {
                        selectedImageUri = null
                        selectedImageSize = null
                        previewBitmap = null
                        localError = null
                    },
                )
            }

            item {
                OutlinedTextField(
                    value = prompt,
                    onValueChange = { prompt = it },
                    modifier = Modifier.fillMaxWidth(),
                    enabled = !isStreaming,
                    minLines = 2,
                    maxLines = 4,
                    shape = RoundedCornerShape(8.dp),
                    label = { Text("补充需求，可不填") },
                    placeholder = {
                        Text("例如：想要便宜一点、同款黑色、适合通勤")
                    },
                )
            }

            item {
                Button(
                    onClick = {
                        val uri = selectedImageUri ?: return@Button
                        hasSubmittedImageSearch = true
                        viewModel.uploadImageForRecommendation(
                            contentResolver = context.contentResolver,
                            imageUri = uri,
                            message = prompt,
                        )
                    },
                    modifier = Modifier.fillMaxWidth(),
                    enabled = selectedImageUri != null && localError == null && !isStreaming && !isCheckingImage,
                    shape = RoundedCornerShape(8.dp),
                ) {
                    Text(if (isStreaming) "识别中..." else "搜索同款")
                }
            }

            item {
                if (hasSubmittedImageSearch) {
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

            if (hasSubmittedImageSearch) {
                val activeSpecSelections = specSelections.filter { selection -> selection.turnId == activeTurnId }
                itemsIndexed(activeSpecSelections, key = { _, selection -> selection.stableKey }) { _, selection ->
                    SpecSelectionCard(
                        selection = selection,
                        onOptionClick = { option -> viewModel.addSelectedSpecToCart(selection, option) },
                    )
                }
            }

            if (hasSubmittedImageSearch && activeRecommendationSections.isNotEmpty()) {
                itemsIndexed(activeRecommendationSections, key = { _, section -> section.stableKey }) { _, section ->
                    RecommendationSection(
                        section = section,
                        totalCount = activeRecommendationSections.size,
                        onProductClick = onProductClick,
                        onAddToCart = viewModel::addProductCardToCart,
                        activeSpecSelection = activeProductCardSpecSelection,
                        onSpecOptionClick = viewModel::addSelectedSpecToCart,
                    )
                }
                if (visibleProducts.isNotEmpty()) {
                    item { FinalComparisonSummary(products = visibleProducts) }
                }
            } else if (hasSubmittedImageSearch && products.isNotEmpty()) {
                itemsIndexed(products, key = { _, product -> product.skuId }) { index, product ->
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
                item { FinalComparisonSummary(products = products) }
            } else if (hasSubmittedImageSearch && !isStreaming && answer.isNotBlank()) {
                item {
                    EmptyResultCard()
                }
            }

            item { Spacer(modifier = Modifier.height(16.dp)) }
        }
    }
}

@Composable
private fun ImagePickerCard(
    previewBitmap: ImageBitmap?,
    imageSize: Long?,
    localError: String?,
    isCheckingImage: Boolean,
    isStreaming: Boolean,
    onPickImage: () -> Unit,
    onClearImage: () -> Unit,
) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .padding(top = 14.dp),
        shape = RoundedCornerShape(8.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        elevation = CardDefaults.cardElevation(defaultElevation = 1.dp),
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.45f)),
    ) {
        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .aspectRatio(1.25f)
                    .background(
                        color = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.55f),
                        shape = RoundedCornerShape(8.dp),
                    ),
                contentAlignment = Alignment.Center,
            ) {
                when {
                    isCheckingImage -> CircularProgressIndicator()
                    previewBitmap != null -> {
                        Image(
                            bitmap = previewBitmap,
                            contentDescription = "已选择的图片",
                            modifier = Modifier.fillMaxSize(),
                            contentScale = ContentScale.Crop,
                        )
                    }
                    else -> {
                        Column(
                            horizontalAlignment = Alignment.CenterHorizontally,
                            verticalArrangement = Arrangement.spacedBy(8.dp),
                        ) {
                            Text(
                                text = "选择一张商品图片",
                                style = MaterialTheme.typography.titleMedium,
                                fontWeight = FontWeight.SemiBold,
                            )
                            Text(
                                text = "支持 JPG、PNG、WebP，最大 8MB",
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant,
                            )
                        }
                    }
                }
            }

            if (imageSize != null) {
                Text(
                    text = "图片大小：${formatImageSize(imageSize)}",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }

            if (localError != null) {
                Text(
                    text = localError,
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.error,
                )
            }

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(10.dp),
            ) {
                OutlinedButton(
                    onClick = onPickImage,
                    modifier = Modifier.weight(1f),
                    enabled = !isStreaming && !isCheckingImage,
                    shape = RoundedCornerShape(8.dp),
                ) {
                    Text(if (previewBitmap == null) "选择图片" else "重新选择")
                }
                Button(
                    onClick = onClearImage,
                    modifier = Modifier.weight(1f),
                    enabled = previewBitmap != null && !isStreaming,
                    shape = RoundedCornerShape(8.dp),
                    colors = ButtonDefaults.buttonColors(
                        containerColor = MaterialTheme.colorScheme.secondary,
                    ),
                ) {
                    Text("取消图片")
                }
            }
        }
    }
}

@Composable
private fun EmptyResultCard() {
    Surface(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(8.dp),
        color = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.45f),
    ) {
        Text(
            text = "暂时没有找到相似商品，可以换一张图片试试。",
            modifier = Modifier.padding(16.dp),
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
    }
}

private fun ContentResolver.getImageSize(uri: Uri): Long? {
    val queriedSize = query(uri, arrayOf(OpenableColumns.SIZE), null, null, null)
        ?.use { cursor ->
            val sizeIndex = cursor.getColumnIndex(OpenableColumns.SIZE)
            if (cursor.moveToFirst() && sizeIndex >= 0) {
                cursor.getLong(sizeIndex).takeIf { it >= 0L }
            } else {
                null
            }
        }
    if (queriedSize != null) {
        return queriedSize
    }

    return runCatching {
        openInputStream(uri)?.use { input ->
            val buffer = ByteArray(DEFAULT_BUFFER_SIZE)
            var total = 0L
            while (true) {
                val read = input.read(buffer)
                if (read < 0) {
                    break
                }
                total += read
                if (total > MAX_IMAGE_BYTES) {
                    break
                }
            }
            total
        }
    }.getOrNull()
}

private fun ContentResolver.decodePreviewBitmap(uri: Uri): ImageBitmap? {
    return runCatching {
        openInputStream(uri)?.use { input ->
            BitmapFactory.decodeStream(input)?.asImageBitmap()
        }
    }.getOrNull()
}

private fun formatImageSize(size: Long): String {
    val mb = size / 1024.0 / 1024.0
    return if (mb >= 1.0) {
        "%.2f MB".format(mb)
    } else {
        "${(size / 1024L).coerceAtLeast(1L)} KB"
    }
}
