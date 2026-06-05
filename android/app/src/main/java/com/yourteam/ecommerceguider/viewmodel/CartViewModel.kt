package com.yourteam.ecommerceguider.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
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

    fun loadCart() {
        viewModelScope.launch {
            _isLoading.value = true
            runCatching { repository.getCart() }
                .onSuccess {
                    _cart.value = it
                    _errorMessage.value = null
                }
                .onFailure { _errorMessage.value = "购物车加载失败，请检查后端服务。" }
            _isLoading.value = false
        }
    }

    fun increase(skuId: String) {
        val item = _cart.value.items.firstOrNull { it.skuId == skuId } ?: return
        updateQuantity(skuId, item.quantity + 1)
    }

    fun decrease(skuId: String) {
        val item = _cart.value.items.firstOrNull { it.skuId == skuId } ?: return
        if (item.quantity <= 1) {
            remove(skuId)
        } else {
            updateQuantity(skuId, item.quantity - 1)
        }
    }

    fun updateQuantity(skuId: String, quantity: Int) {
        viewModelScope.launch {
            runCatching { repository.updateCartQuantity(skuId, quantity) }
                .onSuccess {
                    _cart.value = it
                    _errorMessage.value = null
                    _operationMessage.value = "数量已更新"
                }
                .onFailure { _errorMessage.value = "数量修改失败，请稍后重试。" }
        }
    }

    fun remove(skuId: String) {
        viewModelScope.launch {
            runCatching { repository.removeFromCart(skuId) }
                .onSuccess {
                    _cart.value = it
                    _errorMessage.value = null
                    _operationMessage.value = "商品已删除"
                }
                .onFailure { _errorMessage.value = "删除失败，请稍后重试。" }
        }
    }

    fun clearCart() {
        viewModelScope.launch {
            runCatching { repository.clearCart() }
                .onSuccess {
                    _cart.value = it
                    _errorMessage.value = null
                    _operationMessage.value = "购物车已清空"
                }
                .onFailure { _errorMessage.value = "清空失败，请稍后重试。" }
        }
    }

    fun clearOperationMessage() {
        _operationMessage.value = null
    }
}
