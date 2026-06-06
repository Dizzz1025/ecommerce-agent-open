package com.yourteam.ecommerceguider.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.yourteam.ecommerceguider.data.model.CartItemUiModel
import com.yourteam.ecommerceguider.data.model.CartSnapshotUiModel
import com.yourteam.ecommerceguider.data.repository.ShoppingRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
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

    fun loadCart() {
        viewModelScope.launch {
            _isLoading.value = true
            runCatching { repository.getCart() }
                .onSuccess {
                    _cart.value = it
                    _selectedItemIds.value = it.items.map { item -> item.cartItemId }.toSet()
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
            _operationMessage.value = "至少保留 1 件，如需移除请点击删除"
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
                    syncSelectionWithCart(it)
                    _errorMessage.value = null
                    _operationMessage.value = "数量已更新"
                }
                .onFailure { _errorMessage.value = "数量修改失败，请稍后重试。" }
            markUpdating(item.cartItemId, updating = false)
        }
    }

    fun remove(item: CartItemUiModel) {
        if (_updatingItemIds.value.contains(item.cartItemId)) {
            return
        }
        viewModelScope.launch {
            markUpdating(item.cartItemId, updating = true)
            runCatching { repository.removeFromCart(skuId = item.skuId, cartItemId = item.cartItemId) }
                .onSuccess {
                    _cart.value = it
                    syncSelectionWithCart(it)
                    _errorMessage.value = null
                    _operationMessage.value = "商品已删除"
                }
                .onFailure { _errorMessage.value = "删除失败，请稍后重试。" }
            markUpdating(item.cartItemId, updating = false)
        }
    }

    fun clearCart() {
        viewModelScope.launch {
            runCatching { repository.clearCart() }
                .onSuccess {
                    _cart.value = it
                    _selectedItemIds.value = emptySet()
                    _errorMessage.value = null
                    _operationMessage.value = "购物车已清空"
                }
                .onFailure { _errorMessage.value = "清空失败，请稍后重试。" }
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

    private fun syncSelectionWithCart(snapshot: CartSnapshotUiModel) {
        val currentItemIds = snapshot.items.map { it.cartItemId }.toSet()
        _selectedItemIds.value = _selectedItemIds.value.intersect(currentItemIds)
    }

    private fun markUpdating(itemId: String, updating: Boolean) {
        _updatingItemIds.value = if (updating) {
            _updatingItemIds.value + itemId
        } else {
            _updatingItemIds.value - itemId
        }
    }
}
