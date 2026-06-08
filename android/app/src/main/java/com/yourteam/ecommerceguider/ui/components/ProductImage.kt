package com.yourteam.ecommerceguider.ui.components

import android.graphics.BitmapFactory
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.ImageBitmap
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import java.net.HttpURLConnection
import java.net.URL
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

private enum class ProductImageState {
    Loading,
    Loaded,
    Empty,
    Failed,
}

enum class ResolvedImageSource {
    Detail,
    Original,
}

@Composable
fun ProductImage(
    imageUrl: String,
    contentDescription: String?,
    modifier: Modifier = Modifier,
    fallbackImageUrl: String? = null,
    onResolvedImageSourceChange: (ResolvedImageSource?) -> Unit = {},
    cornerRadius: Dp = 20.dp,
    contentScale: ContentScale = ContentScale.Crop,
    backgroundColor: Color = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.55f),
) {
    val loadAttempts = remember(imageUrl, fallbackImageUrl) {
        val primaryUrl = imageUrl.trim()
        buildList {
            primaryUrl.takeIf { it.isNotBlank() }?.let { add(ResolvedImageSource.Detail to it) }
            fallbackImageUrl
                ?.trim()
                ?.takeIf { it.isNotBlank() }
                ?.takeIf { it != primaryUrl }
                ?.let { add(ResolvedImageSource.Original to it) }
        }.distinctBy { it.second }
    }
    var imageBitmap by remember(loadAttempts) { mutableStateOf<ImageBitmap?>(null) }
    var imageState by remember(loadAttempts) { mutableStateOf(ProductImageState.Loading) }

    LaunchedEffect(loadAttempts) {
        imageBitmap = null
        if (loadAttempts.isEmpty()) {
            imageState = ProductImageState.Empty
            onResolvedImageSourceChange(null)
            return@LaunchedEffect
        }
        imageState = ProductImageState.Loading
        var bitmap: ImageBitmap? = null
        var resolvedSource: ResolvedImageSource? = null
        for ((source, url) in loadAttempts) {
            bitmap = loadProductImageBitmap(url)
            if (bitmap != null) {
                resolvedSource = source
                break
            }
        }
        imageBitmap = bitmap
        imageState = if (bitmap == null) ProductImageState.Failed else ProductImageState.Loaded
        onResolvedImageSourceChange(resolvedSource)
    }

    Box(
        modifier = modifier
            .clip(RoundedCornerShape(cornerRadius))
            .background(backgroundColor),
        contentAlignment = Alignment.Center,
    ) {
        val bitmap = imageBitmap
        if (bitmap != null) {
            Image(
                bitmap = bitmap,
                contentDescription = contentDescription,
                modifier = Modifier.fillMaxSize(),
                contentScale = contentScale,
            )
        } else {
            Text(
                text = when (imageState) {
                    ProductImageState.Loading -> "加载中"
                    ProductImageState.Empty -> "暂无商品图"
                    ProductImageState.Failed -> "图片加载失败"
                    ProductImageState.Loaded -> "商品图"
                },
                style = MaterialTheme.typography.labelMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.padding(12.dp),
            )
        }
    }
}

private suspend fun loadProductImageBitmap(imageUrl: String): ImageBitmap? {
    return runCatching {
        withContext(Dispatchers.IO) {
            val connection = URL(imageUrl).openConnection() as HttpURLConnection
            connection.connectTimeout = 8_000
            connection.readTimeout = 12_000
            connection.instanceFollowRedirects = true
            try {
                if (connection.responseCode !in 200..299) {
                    null
                } else {
                    connection.inputStream.use { stream ->
                        BitmapFactory.decodeStream(stream)?.asImageBitmap()
                    }
                }
            } finally {
                connection.disconnect()
            }
        }
    }.getOrNull()
}
