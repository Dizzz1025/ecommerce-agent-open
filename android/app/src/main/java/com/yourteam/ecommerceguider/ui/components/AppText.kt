package com.yourteam.ecommerceguider.ui.components

import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.style.TextDecoration
import androidx.compose.ui.text.style.TextOverflow
import com.yourteam.ecommerceguider.theme.AppColors
import com.yourteam.ecommerceguider.theme.AppTypography

enum class PriceTextLevel {
    Normal,
    Highlight,
    Large,
}

@Composable
fun PriceText(
    modifier: Modifier = Modifier,
    formattedText: String? = null,
    price: Double? = null,
    currencyPrefix: String = "\u00A5",
    level: PriceTextLevel = PriceTextLevel.Normal,
    color: Color = AppColors.TextPrimary,
) {
    val displayText = formattedText
        ?.takeIf { it.isNotBlank() }
        ?: price?.let { "$currencyPrefix${formatPrice(it)}" }
        ?: return

    Text(
        text = displayText,
        modifier = modifier,
        style = when (level) {
            PriceTextLevel.Normal -> AppTypography.PriceSmall
            PriceTextLevel.Highlight -> AppTypography.Price
            PriceTextLevel.Large -> AppTypography.PriceLarge
        },
        color = color,
        maxLines = 1,
        overflow = TextOverflow.Ellipsis,
        softWrap = false,
    )
}

@Composable
fun OriginalPriceText(
    modifier: Modifier = Modifier,
    formattedText: String? = null,
    price: Double? = null,
    currencyPrefix: String = "\u00A5",
    color: Color = AppColors.TextTertiary,
) {
    val displayText = formattedText
        ?.takeIf { it.isNotBlank() }
        ?: price?.let { "$currencyPrefix${formatPrice(it)}" }
        ?: return

    Text(
        text = displayText,
        modifier = modifier,
        style = AppTypography.BodySmall,
        color = color,
        textDecoration = TextDecoration.LineThrough,
        maxLines = 1,
        overflow = TextOverflow.Ellipsis,
        softWrap = false,
    )
}
