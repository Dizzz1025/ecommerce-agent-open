package com.yourteam.ecommerceguider.ui.components

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
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
    containerColor: Color? = null,
    contentColor: Color? = null,
    borderColor: Color? = null,
) {
    if (text.isBlank()) {
        return
    }

    val resolvedContainerColor = containerColor ?: when (tone) {
        TagChipTone.Neutral -> AppColors.SurfaceSoft
        TagChipTone.Warm -> AppColors.AccentWarmSoft
    }
    val resolvedContentColor = contentColor ?: when (tone) {
        TagChipTone.Neutral -> AppColors.TextSecondary
        TagChipTone.Warm -> AppColors.AccentWarm
    }
    val resolvedBorderColor = borderColor ?: if (tone == TagChipTone.Warm) {
        AppColors.AccentWarmSoft
    } else {
        AppColors.Border
    }

    Surface(
        modifier = modifier.heightIn(min = 28.dp),
        shape = androidx.compose.foundation.shape.RoundedCornerShape(AppRadius.Pill),
        color = resolvedContainerColor,
        border = BorderStroke(1.dp, resolvedBorderColor),
    ) {
        Box(
            modifier = Modifier
                .heightIn(min = 28.dp)
                .padding(PaddingValues(horizontal = AppSpacing.Md)),
            contentAlignment = Alignment.Center,
        ) {
            Text(
                text = text,
                style = AppTypography.CaptionStrong.copy(lineHeight = 14.sp),
                color = resolvedContentColor,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
        }
    }
}
