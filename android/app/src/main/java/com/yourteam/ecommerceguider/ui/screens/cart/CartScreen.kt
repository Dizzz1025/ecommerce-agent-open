@file:OptIn(androidx.compose.material3.ExperimentalMaterial3Api::class)

package com.yourteam.ecommerceguider.ui.screens.cart

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Checkbox
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
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
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.rotate
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.yourteam.ecommerceguider.R
import com.yourteam.ecommerceguider.data.model.CartItemUiModel
import com.yourteam.ecommerceguider.ui.components.ProductImage
import com.yourteam.ecommerceguider.ui.components.formatPrice
import com.yourteam.ecommerceguider.viewmodel.CartViewModel
import com.yourteam.ecommerceguider.viewmodel.simpleViewModelFactory

@Composable
fun CartScreen(
    onBack: () -> Unit,
    onCheckoutClick: () -> Unit,
    onProductClick: (String) -> Unit,
    viewModel: CartViewModel = viewModel(factory = simpleViewModelFactory { CartViewModel() }),
) {
    val cart by viewModel.cart.collectAsState()
    val isLoading by viewModel.isLoading.collectAsState()
    val errorMessage by viewModel.errorMessage.collectAsState()
    val operationMessage by viewModel.operationMessage.collectAsState()
    val selectedItemIds by viewModel.selectedItemIds.collectAsState()
    val updatingItemIds by viewModel.updatingItemIds.collectAsState()
    val snackbarHostState = remember { SnackbarHostState() }
    var showClearConfirm by remember { mutableStateOf(false) }
    var pendingRemoveItem by remember { mutableStateOf<CartItemUiModel?>(null) }

    val currentItemIds = cart.items.map { it.cartItemId }.toSet()
    val selectedItems = cart.items.filter { it.cartItemId in selectedItemIds }
    val selectedQuantity = selectedItems.sumOf { it.quantity }
    val selectedTotal = selectedItems.sumOf { it.lineTotal }
    val allSelected = currentItemIds.isNotEmpty() && selectedItemIds.containsAll(currentItemIds)

    LaunchedEffect(Unit) {
        viewModel.loadCart()
    }

    LaunchedEffect(errorMessage) {
        errorMessage?.let { snackbarHostState.showSnackbar(it) }
    }

    LaunchedEffect(operationMessage) {
        operationMessage?.let {
            snackbarHostState.showSnackbar(it)
            viewModel.clearOperationMessage()
        }
    }

    if (showClearConfirm) {
        AlertDialog(
            onDismissRequest = { showClearConfirm = false },
            title = { Text("确认清空购物车？") },
            text = { Text("购物车中的全部商品将被移除。") },
            confirmButton = {
                TextButton(
                    onClick = {
                        showClearConfirm = false
                        viewModel.clearCart()
                    },
                ) {
                    Text("确认清空", color = MaterialTheme.colorScheme.error)
                }
            },
            dismissButton = {
                TextButton(onClick = { showClearConfirm = false }) {
                    Text("取消")
                }
            },
        )
    }

    pendingRemoveItem?.let { item ->
        AlertDialog(
            onDismissRequest = { pendingRemoveItem = null },
            title = { Text("删除这件商品？") },
            text = {
                Text(
                    text = item.name,
                    maxLines = 3,
                    overflow = TextOverflow.Ellipsis,
                )
            },
            confirmButton = {
                TextButton(
                    onClick = {
                        pendingRemoveItem = null
                        viewModel.remove(item)
                    },
                ) {
                    Text("删除", color = MaterialTheme.colorScheme.error)
                }
            },
            dismissButton = {
                TextButton(onClick = { pendingRemoveItem = null }) {
                    Text("取消")
                }
            },
        )
    }

    Scaffold(
        snackbarHost = { SnackbarHost(snackbarHostState) },
        topBar = {
            CartTopBar(
                totalItems = cart.totalItems,
                onBack = onBack,
                onClearClick = { showClearConfirm = true },
            )
        },
        bottomBar = {
            if (cart.items.isNotEmpty()) {
                CartBottomBar(
                    allSelected = allSelected,
                    selectedQuantity = selectedQuantity,
                    selectedTotal = selectedTotal,
                    onToggleSelectAll = viewModel::toggleSelectAll,
                    onCheckoutClick = onCheckoutClick,
                )
            }
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

            cart.items.isEmpty() -> {
                EmptyCart(
                    modifier = Modifier.padding(innerPadding),
                    onBack = onBack,
                )
            }

            else -> {
                LazyColumn(
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(innerPadding),
                    contentPadding = PaddingValues(horizontal = 16.dp, vertical = 14.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp),
                ) {
                    items(cart.items, key = { it.cartItemId }) { item ->
                        CartItemCard(
                            item = item,
                            selected = item.cartItemId in selectedItemIds,
                            isUpdating = item.cartItemId in updatingItemIds,
                            onSelectionChange = { viewModel.toggleItemSelection(item.cartItemId) },
                            onProductClick = { onProductClick(item.skuId) },
                            onIncrease = { viewModel.increase(item.cartItemId) },
                            onDecrease = { viewModel.decrease(item.cartItemId) },
                            onRemove = { pendingRemoveItem = item },
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun CartTopBar(
    totalItems: Int,
    onBack: () -> Unit,
    onClearClick: () -> Unit,
) {
    TopAppBar(
        title = {
            Text(
                text = "购物车（$totalItems）",
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
            if (totalItems > 0) {
                TextButton(onClick = onClearClick) {
                    Text("清空")
                }
            }
        },
        colors = TopAppBarDefaults.topAppBarColors(
            containerColor = MaterialTheme.colorScheme.surface,
        ),
    )
}

@Composable
private fun CartItemCard(
    item: CartItemUiModel,
    selected: Boolean,
    isUpdating: Boolean,
    onSelectionChange: () -> Unit,
    onProductClick: () -> Unit,
    onIncrease: () -> Unit,
    onDecrease: () -> Unit,
    onRemove: () -> Unit,
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(12.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        elevation = CardDefaults.cardElevation(defaultElevation = 1.dp),
    ) {
        Row(
            modifier = Modifier.padding(12.dp),
            verticalAlignment = Alignment.Top,
            horizontalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            Checkbox(
                checked = selected,
                onCheckedChange = { onSelectionChange() },
                modifier = Modifier.size(44.dp),
            )
            ProductImage(
                imageUrl = item.imageUrl,
                contentDescription = item.name,
                modifier = Modifier
                    .size(92.dp)
                    .clickable(onClick = onProductClick),
                cornerRadius = 8.dp,
            )
            Column(
                modifier = Modifier.weight(1f),
                verticalArrangement = Arrangement.spacedBy(7.dp),
            ) {
                Text(
                    text = item.name,
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.SemiBold,
                    maxLines = 3,
                    overflow = TextOverflow.Ellipsis,
                    modifier = Modifier.clickable(onClick = onProductClick),
                )
                item.specSummary?.takeIf { it.isNotBlank() }?.let { spec ->
                    Text(
                        text = spec,
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        maxLines = 2,
                        overflow = TextOverflow.Ellipsis,
                    )
                }
                Text(
                    text = "¥${formatPrice(item.price)}",
                    style = MaterialTheme.typography.titleMedium,
                    color = MaterialTheme.colorScheme.primary,
                    fontWeight = FontWeight.Bold,
                )
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    QuantityStepper(
                        quantity = item.quantity,
                        enabled = !isUpdating,
                        canDecrease = item.quantity > 1,
                        onIncrease = onIncrease,
                        onDecrease = onDecrease,
                    )
                    Spacer(modifier = Modifier.weight(1f))
                    if (item.quantity > 1) {
                        Text(
                            text = "小计 ¥${formatPrice(item.lineTotal)}",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                            maxLines = 1,
                        )
                    }
                    TextButton(
                        onClick = onRemove,
                        enabled = !isUpdating,
                        contentPadding = PaddingValues(horizontal = 8.dp),
                    ) {
                        Text(
                            text = "删除",
                            color = MaterialTheme.colorScheme.error,
                            maxLines = 1,
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun QuantityStepper(
    quantity: Int,
    enabled: Boolean,
    canDecrease: Boolean,
    onIncrease: () -> Unit,
    onDecrease: () -> Unit,
) {
    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        StepperButton(text = "-", enabled = enabled && canDecrease, onClick = onDecrease)
        Text(
            text = quantity.toString(),
            style = MaterialTheme.typography.titleSmall,
            fontWeight = FontWeight.Bold,
            maxLines = 1,
        )
        StepperButton(text = "+", enabled = enabled, onClick = onIncrease)
    }
}

@Composable
private fun StepperButton(
    text: String,
    enabled: Boolean,
    onClick: () -> Unit,
) {
    Surface(
        onClick = onClick,
        enabled = enabled,
        shape = CircleShape,
        color = if (enabled) {
            MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.75f)
        } else {
            MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.55f)
        },
        modifier = Modifier.size(40.dp),
    ) {
        Box(contentAlignment = Alignment.Center) {
            Text(
                text = text,
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Bold,
                color = if (enabled) {
                    MaterialTheme.colorScheme.onPrimaryContainer
                } else {
                    MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.6f)
                },
            )
        }
    }
}

@Composable
private fun CartBottomBar(
    allSelected: Boolean,
    selectedQuantity: Int,
    selectedTotal: Double,
    onToggleSelectAll: () -> Unit,
    onCheckoutClick: () -> Unit,
) {
    Surface(
        color = MaterialTheme.colorScheme.surface,
        shadowElevation = 8.dp,
        modifier = Modifier.navigationBarsPadding(),
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 12.dp, vertical = 10.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                modifier = Modifier.clickable(onClick = onToggleSelectAll),
            ) {
                Checkbox(
                    checked = allSelected,
                    onCheckedChange = { onToggleSelectAll() },
                )
                Text(
                    text = "全选",
                    style = MaterialTheme.typography.bodyMedium,
                    maxLines = 1,
                )
            }
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = "合计 ¥${formatPrice(selectedTotal)}",
                    style = MaterialTheme.typography.titleMedium,
                    color = MaterialTheme.colorScheme.primary,
                    fontWeight = FontWeight.Bold,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
                Text(
                    text = "不含运费",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    maxLines = 1,
                )
            }
            Button(
                onClick = onCheckoutClick,
                enabled = selectedQuantity > 0,
                modifier = Modifier
                    .width(128.dp)
                    .heightIn(min = 48.dp),
                shape = RoundedCornerShape(999.dp),
                colors = ButtonDefaults.buttonColors(
                    containerColor = MaterialTheme.colorScheme.primary,
                ),
            ) {
                Text(
                    text = "去结算（$selectedQuantity）",
                    maxLines = 1,
                    softWrap = false,
                )
            }
        }
    }
}

@Composable
private fun EmptyCart(
    modifier: Modifier = Modifier,
    onBack: () -> Unit,
) {
    Box(
        modifier = modifier
            .fillMaxSize()
            .padding(28.dp),
        contentAlignment = Alignment.Center,
    ) {
        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(14.dp),
        ) {
            Text(
                text = "购物车还是空的",
                style = MaterialTheme.typography.titleLarge,
                fontWeight = FontWeight.Bold,
            )
            Button(
                onClick = onBack,
                shape = RoundedCornerShape(999.dp),
            ) {
                Text("去智能导购看看")
            }
        }
    }
}
