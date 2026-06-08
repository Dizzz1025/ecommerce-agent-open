package com.yourteam.ecommerceguider.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.pager.HorizontalPager
import androidx.compose.foundation.pager.rememberPagerState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.unit.dp
import com.yourteam.ecommerceguider.theme.AppColors
import com.yourteam.ecommerceguider.theme.AppSpacing

@Composable
fun ProductImagePager(
    imageUrls: List<String>,
    contentDescription: String?,
    modifier: Modifier = Modifier,
    fallbackImageUrls: List<String> = emptyList(),
    contentScale: ContentScale = ContentScale.Crop,
    containerColor: Color = AppColors.SurfaceSoft,
    imageBackgroundColor: Color = AppColors.SurfaceSoft,
    showIndicators: Boolean = true,
) {
    val images = remember(imageUrls, fallbackImageUrls) {
        imageUrls
            .mapIndexedNotNull { index, rawUrl ->
                val imageUrl = rawUrl.trim().takeIf { it.isNotBlank() } ?: return@mapIndexedNotNull null
                ProductPagerImage(
                    imageUrl = imageUrl,
                    fallbackImageUrl = fallbackImageUrls
                        .getOrNull(index)
                        ?.trim()
                        ?.takeIf { it.isNotBlank() && it != imageUrl },
                )
            }
            .distinctBy { it.imageUrl }
    }
    val pagerState = rememberPagerState(pageCount = { images.size.coerceAtLeast(1) })

    Box(
        modifier = modifier.background(containerColor),
    ) {
        if (images.isEmpty()) {
            ProductImage(
                imageUrl = "",
                contentDescription = contentDescription,
                modifier = Modifier.fillMaxSize(),
                cornerRadius = AppSpacing.None,
                contentScale = ContentScale.Fit,
                backgroundColor = imageBackgroundColor,
            )
        } else {
            HorizontalPager(
                state = pagerState,
                key = { index -> images[index] },
                modifier = Modifier.fillMaxSize(),
            ) { page ->
                val image = images[page]
                ProductImage(
                    imageUrl = image.imageUrl,
                    fallbackImageUrl = image.fallbackImageUrl,
                    contentDescription = contentDescription,
                    modifier = Modifier.fillMaxSize(),
                    cornerRadius = AppSpacing.None,
                    contentScale = contentScale,
                    backgroundColor = imageBackgroundColor,
                )
            }
        }

        if (showIndicators && images.size > 1) {
            Row(
                modifier = Modifier
                    .align(Alignment.BottomCenter)
                    .padding(bottom = AppSpacing.Lg),
                horizontalArrangement = Arrangement.spacedBy(AppSpacing.Sm),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                images.forEachIndexed { index, _ ->
                    val selected = pagerState.currentPage == index
                    Box(
                        modifier = Modifier
                            .size(if (selected) 8.dp else 6.dp)
                            .clip(CircleShape)
                            .background(
                                if (selected) {
                                    AppColors.HeroText
                                } else {
                                    AppColors.HeroText.copy(alpha = 0.46f)
                                },
                            ),
                    )
                }
            }
        }
    }
}

private data class ProductPagerImage(
    val imageUrl: String,
    val fallbackImageUrl: String?,
)
