package com.yourteam.ecommerceguider.ui.components

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.widthIn
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.yourteam.ecommerceguider.theme.AppColors
import com.yourteam.ecommerceguider.theme.AppSpacing
import com.yourteam.ecommerceguider.theme.AppTypography

@Composable
fun LoadingState(
    modifier: Modifier = Modifier,
    message: String? = null,
) {
    StateContainer(modifier = modifier) {
        CircularProgressIndicator(color = AppColors.Primary)
        message?.takeIf { it.isNotBlank() }?.let {
            StateMessage(message = it)
        }
    }
}

@Composable
fun EmptyState(
    title: String,
    modifier: Modifier = Modifier,
    message: String? = null,
    actionLabel: String? = null,
    onAction: (() -> Unit)? = null,
    icon: (@Composable () -> Unit)? = null,
) {
    StateContainer(modifier = modifier) {
        icon?.invoke()
        StateTitle(title = title)
        message?.takeIf { it.isNotBlank() }?.let {
            StateMessage(message = it)
        }
        StateAction(actionLabel = actionLabel, onAction = onAction)
    }
}

@Composable
fun ErrorState(
    title: String,
    modifier: Modifier = Modifier,
    message: String? = null,
    actionLabel: String? = null,
    onAction: (() -> Unit)? = null,
    icon: (@Composable () -> Unit)? = null,
) {
    StateContainer(modifier = modifier) {
        icon?.invoke()
        StateTitle(title = title, danger = true)
        message?.takeIf { it.isNotBlank() }?.let {
            StateMessage(message = it)
        }
        StateAction(actionLabel = actionLabel, onAction = onAction)
    }
}

@Composable
private fun StateContainer(
    modifier: Modifier,
    content: @Composable () -> Unit,
) {
    Box(
        modifier = modifier
            .fillMaxSize()
            .padding(AppSpacing.Xxl),
        contentAlignment = Alignment.Center,
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .widthIn(max = 320.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(AppSpacing.Md),
        ) {
            content()
        }
    }
}

@Composable
private fun StateTitle(
    title: String,
    danger: Boolean = false,
) {
    Text(
        text = title,
        style = AppTypography.TitleSmall,
        color = if (danger) AppColors.Danger else AppColors.TextPrimary,
        textAlign = TextAlign.Center,
        maxLines = 2,
        overflow = TextOverflow.Ellipsis,
    )
}

@Composable
private fun StateMessage(message: String) {
    Text(
        text = message,
        style = AppTypography.BodySmall,
        color = AppColors.TextSecondary,
        textAlign = TextAlign.Center,
    )
}

@Composable
private fun StateAction(
    actionLabel: String?,
    onAction: (() -> Unit)?,
) {
    if (actionLabel.isNullOrBlank() || onAction == null) {
        return
    }
    SecondaryButton(
        text = actionLabel,
        onClick = onAction,
    )
}
