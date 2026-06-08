package com.yourteam.ecommerceguider.ui.components

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.yourteam.ecommerceguider.theme.AppColors
import com.yourteam.ecommerceguider.theme.AppRadius
import com.yourteam.ecommerceguider.theme.AppSpacing
import com.yourteam.ecommerceguider.theme.AppTypography

enum class TagChipTone {
    Neutral,
    Warm,
}

@Composable
fun TagChip(
    text: String,
    modifier: Modifier = Modifier,
    tone: TagChipTone = TagChipTone.Neutral,
) {
    if (text.isBlank()) {
        return
    }

    val containerColor = when (tone) {
        TagChipTone.Neutral -> AppColors.SurfaceSoft
        TagChipTone.Warm -> AppColors.AccentWarmSoft
    }
    val contentColor = when (tone) {
        TagChipTone.Neutral -> AppColors.TextSecondary
        TagChipTone.Warm -> AppColors.AccentWarm
    }

    Surface(
        modifier = modifier.heightIn(min = 28.dp),
        shape = androidx.compose.foundation.shape.RoundedCornerShape(AppRadius.Pill),
        color = containerColor,
        border = BorderStroke(1.dp, if (tone == TagChipTone.Warm) AppColors.AccentWarmSoft else AppColors.Border),
    ) {
        Text(
            text = text,
            modifier = Modifier.padding(PaddingValues(horizontal = AppSpacing.Md, vertical = AppSpacing.Xs)),
            style = AppTypography.CaptionStrong,
            color = contentColor,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
        )
    }
}
