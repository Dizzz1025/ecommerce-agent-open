package com.yourteam.ecommerceguider.navigation

import androidx.compose.runtime.Composable
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import com.yourteam.ecommerceguider.ui.screens.address.AddressScreen
import com.yourteam.ecommerceguider.ui.screens.cart.CartScreen
import com.yourteam.ecommerceguider.ui.screens.chat.ChatScreen
import com.yourteam.ecommerceguider.ui.screens.checkout.CheckoutScreen
import com.yourteam.ecommerceguider.ui.screens.image.ImageSearchScreen
import com.yourteam.ecommerceguider.ui.screens.order.OrderResultScreen
import com.yourteam.ecommerceguider.ui.screens.product.ProductDetailScreen
import com.yourteam.ecommerceguider.viewmodel.ChatViewModel
import com.yourteam.ecommerceguider.viewmodel.simpleViewModelFactory

@Composable
fun AppNavGraph() {
    val navController = rememberNavController()
    val chatViewModel: ChatViewModel = viewModel(
        factory = simpleViewModelFactory { ChatViewModel() },
    )

    NavHost(
        navController = navController,
        startDestination = Routes.Chat.route,
    ) {
        composable(Routes.Chat.route) {
            ChatScreen(
                onProductClick = { skuId -> navController.navigate(Routes.ProductDetail.create(skuId)) },
                onCartClick = { navController.navigate(Routes.Cart.route) },
                onCheckoutClick = { navController.navigate(Routes.Checkout.route) },
                onImageSearchClick = { navController.navigate(Routes.ImageSearch.route) },
                onAddressClick = { navController.navigate(Routes.Address.route) },
                viewModel = chatViewModel,
            )
        }
        composable(
            route = Routes.ProductDetail.route,
            arguments = listOf(navArgument("skuId") { type = NavType.StringType }),
        ) { backStackEntry ->
            ProductDetailScreen(
                skuId = backStackEntry.arguments?.getString("skuId").orEmpty(),
                onBack = { navController.popBackStack() },
                onCartClick = { navController.navigate(Routes.Cart.route) },
            )
        }
        composable(Routes.Cart.route) {
            CartScreen(
                onBack = { navController.popBackStack() },
                onCheckoutClick = { navController.navigate(Routes.Checkout.route) },
                onProductClick = { skuId -> navController.navigate(Routes.ProductDetail.create(skuId)) },
            )
        }
        composable(Routes.Checkout.route) {
            CheckoutScreen(
                onBack = { navController.popBackStack() },
                onSubmitOrder = { navController.navigate(Routes.OrderResult.route) },
            )
        }
        composable(Routes.OrderResult.route) {
            OrderResultScreen(onBackToChat = {
                navController.navigate(Routes.Chat.route) {
                    popUpTo(Routes.Chat.route) { inclusive = true }
                }
            })
        }
        composable(Routes.ImageSearch.route) {
            ImageSearchScreen(
                onBack = { navController.popBackStack() },
                onProductClick = { skuId -> navController.navigate(Routes.ProductDetail.create(skuId)) },
                onCartClick = { navController.navigate(Routes.Cart.route) },
                viewModel = chatViewModel,
            )
        }
        composable(Routes.Address.route) {
            AddressScreen(onBack = { navController.popBackStack() })
        }
    }
}
