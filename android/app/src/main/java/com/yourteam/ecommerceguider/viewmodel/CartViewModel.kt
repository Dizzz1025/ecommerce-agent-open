package com.yourteam.ecommerceguider.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.yourteam.ecommerceguider.data.model.CartItemRestoreSnapshotUiModel
import com.yourteam.ecommerceguider.data.model.CartItemUiModel
import com.yourteam.ecommerceguider.data.model.CartSnapshotUiModel
import com.yourteam.ecommerceguider.data.model.toRestoreSnapshot
import com.yourteam.ecommerceguider.data.repository.ShoppingRepository
import com.yourteam.ecommerceguider.ui.screens.cart.CartUiEffect
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asSharedFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

class CartViewModel(
    private val repository: ShoppingRepository = ShoppingRepository(),
) : ViewModel() {
    private val _cart = MutableStateFlow(CartSnapshotUiModel())
    val cart: StateFlow<CartSnapshotUiModel> = _cart.asStateFlow()

    private val _isLoading = MutableStateFlow(false)
    val isLoading: StateFlow<Boolean> = _isLoading.asStateFlow()

    private val _errorMessage = MutableStateFlow<String?>(null)
    val errorMessage: StateFlow<String?> = _errorMessage.asStateFlow()

    private val _operationMessage = MutableStateFlow<String?>(null)
    val operationMessage: StateFlow<String?> = _operationMessage.asStateFlow()

    private val _selectedItemIds = MutableStateFlow<Set<String>>(emptySet())
    val selectedItemIds: StateFlow<Set<String>> = _selectedItemIds.asStateFlow()

    private val _updatingItemIds = MutableStateFlow<Set<String>>(emptySet())
    val updatingItemIds: StateFlow<Set<String>> = _updatingItemIds.asStateFlow()

    private val _effects = MutableSharedFlow<CartUiEffect>(extraBufferCapacity = 1)
    val effects: SharedFlow<CartUiEffect> = _effects.asSharedFlow()

    private var lastRemovedSnapshot: CartItemRestoreSnapshotUiModel? = null

    fun loadCart() {
        viewModelScope.launch {
            _isLoading.value = true
            runCatching { repository.getCart() }
                .onSuccess {
                    _cart.value = it
                    selectAllCurrentItems(it)
                    _errorMessage.value = null
                }
                .onFailure { _errorMessage.value = "购物车加载失败，请检查后端服务。" }
            _isLoading.value = false
        }
    }

    fun increase(cartItemId: String) {
        val item = _cart.value.items.firstOrNull { it.cartItemId == cartItemId } ?: return
        updateQuantity(item, item.quantity + 1)
    }

    fun decrease(cartItemId: String) {
        val item = _cart.value.items.firstOrNull { it.cartItemId == cartItemId } ?: return
        if (item.quantity <= 1) {
            _effects.tryEmit(CartUiEffect.ShowMessage("数量已是最小值，左滑可删除商品"))
        } else {
            updateQuantity(item, item.quantity - 1)
        }
    }

    fun updateQuantity(item: CartItemUiModel, quantity: Int) {
        if (_updatingItemIds.value.contains(item.cartItemId)) {
            return
        }
        viewModelScope.launch {
            markUpdating(item.cartItemId, updating = true)
            runCatching {
                repository.updateCartQuantity(
                    skuId = item.skuId,
                    quantity = quantity,
                    cartItemId = item.cartItemId,
                )
            }
                .onSuccess {
                    _cart.value = it
                    selectAllCurrentItems(it)
                    _errorMessage.value = null
                }
                .onFailure {
                    _effects.tryEmit(
                        CartUiEffect.ShowMessage(
                            message = "数量修改失败，请稍后重试。",
                            cartItemId = item.cartItemId,
                        ),
                    )
                }
            markUpdating(item.cartItemId, updating = false)
        }
    }

    fun remove(item: CartItemUiModel) {
        if (_updatingItemIds.value.contains(item.cartItemId)) {
            return
        }
        viewModelScope.launch {
            val restoreSnapshot = item.toRestoreSnapshot()
            markUpdating(item.cartItemId, updating = true)
            runCatching { repository.removeFromCart(skuId = item.skuId, cartItemId = item.cartItemId) }
                .onSuccess {
                    _cart.value = it
                    selectAllCurrentItems(it)
                    lastRemovedSnapshot = restoreSnapshot
                    _errorMessage.value = null
                    _effects.tryEmit(CartUiEffect.ItemRemoved(item.cartItemId))
                }
                .onFailure {
                    _effects.tryEmit(
                        CartUiEffect.ShowMessage(
                            message = "删除失败，请稍后重试。",
                            cartItemId = item.cartItemId,
                        ),
                    )
                }
            markUpdating(item.cartItemId, updating = false)
        }
    }

    fun undoLastRemove(cartItemId: String) {
        val snapshot = lastRemovedSnapshot ?: return
        if (snapshot.cartItemId != cartItemId || _updatingItemIds.value.contains(cartItemId)) {
            return
        }
        viewModelScope.launch {
            markUpdating(cartItemId, updating = true)
            runCatching { repository.restoreCartItem(snapshot) }
                .onSuccess {
                    _cart.value = it
                    selectAllCurrentItems(it)
                    lastRemovedSnapshot = null
                    _errorMessage.value = null
                    _effects.tryEmit(CartUiEffect.ShowMessage("已恢复商品"))
                }
                .onFailure {
                    _effects.tryEmit(CartUiEffect.ShowMessage("撤销失败，请稍后重试。"))
                }
            markUpdating(cartItemId, updating = false)
        }
    }

    fun discardLastRemoved(cartItemId: String) {
        if (lastRemovedSnapshot?.cartItemId == cartItemId) {
            lastRemovedSnapshot = null
        }
    }

    fun clearCart() {
        viewModelScope.launch {
            runCatching { repository.clearCart() }
                .onSuccess {
                    _cart.value = it
                    _selectedItemIds.value = emptySet()
                    _errorMessage.value = null
                    _effects.tryEmit(CartUiEffect.ShowMessage("购物车已清空"))
                }
                .onFailure {
                    _effects.tryEmit(CartUiEffect.ShowMessage("清空失败，请稍后重试。"))
                }
        }
    }

    fun toggleItemSelection(cartItemId: String) {
        _selectedItemIds.value = if (_selectedItemIds.value.contains(cartItemId)) {
            _selectedItemIds.value - cartItemId
        } else {
            _selectedItemIds.value + cartItemId
        }
    }

    fun toggleSelectAll() {
        val allItemIds = _cart.value.items.map { it.cartItemId }.toSet()
        _selectedItemIds.value = if (allItemIds.isNotEmpty() && _selectedItemIds.value.containsAll(allItemIds)) {
            emptySet()
        } else {
            allItemIds
        }
    }

    fun clearOperationMessage() {
        _operationMessage.value = null
    }

    private fun selectAllCurrentItems(snapshot: CartSnapshotUiModel) {
        _selectedItemIds.value = snapshot.items.map { it.cartItemId }.toSet()
    }

    private fun markUpdating(itemId: String, updating: Boolean) {
        _updatingItemIds.value = if (updating) {
            _updatingItemIds.value + itemId
        } else {
            _updatingItemIds.value - itemId
        }
    }
}
