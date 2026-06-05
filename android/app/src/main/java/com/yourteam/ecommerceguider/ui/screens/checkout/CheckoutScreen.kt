package com.yourteam.ecommerceguider.ui.screens.checkout

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp

@Composable
fun CheckoutScreen(
    onBack: () -> Unit,
    onSubmitOrder: () -> Unit,
) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Text(text = "Checkout", style = MaterialTheme.typography.headlineSmall)
        Text(text = "Reserved for address, price summary, delivery method, and order confirmation.")
        Button(onClick = onSubmitOrder) {
            Text("Submit Placeholder Order")
        }
        Button(onClick = onBack) {
            Text("Back")
        }
    }
}

