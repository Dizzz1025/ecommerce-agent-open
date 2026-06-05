package com.yourteam.ecommerceguider

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import com.yourteam.ecommerceguider.navigation.AppNavGraph
import com.yourteam.ecommerceguider.theme.EcommerceGuiderTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            EcommerceGuiderTheme {
                AppNavGraph()
            }
        }
    }
}

