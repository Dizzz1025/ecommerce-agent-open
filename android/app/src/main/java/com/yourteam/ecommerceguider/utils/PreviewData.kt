package com.yourteam.ecommerceguider.utils

import com.yourteam.ecommerceguider.data.model.CartSnapshotUiModel
import com.yourteam.ecommerceguider.data.model.CartItemUiModel
import com.yourteam.ecommerceguider.data.model.ChatMessageUiModel
import com.yourteam.ecommerceguider.data.model.ProductUiModel
import com.yourteam.ecommerceguider.data.model.SpotlightUiModel

object PreviewData {
    val sampleProducts = listOf(
        ProductUiModel(
            skuId = "p001",
            name = "清爽控油氨基酸洗面奶",
            category = "护肤/洁面",
            brand = "示例品牌A",
            price = 89.0,
            stock = 120,
            imageUrl = "data/1_美妆护肤/images/p_beauty_001_live.jpg",
            spotlight = SpotlightUiModel(
                skinType = listOf("油皮", "混油皮"),
                features = listOf("控油", "温和", "氨基酸"),
                exclude = listOf("酒精", "皂基"),
                description = "适合油皮日常清洁",
            ),
            reviewsSummary = "多数用户反馈洗后不紧绷",
            reason = "适合油皮和混油皮，主打控油和温和清洁",
        ),
        ProductUiModel(
            skuId = "p002",
            name = "舒缓修护净润洗面奶",
            category = "护肤/洁面",
            brand = "示例品牌B",
            price = 99.0,
            stock = 86,
            imageUrl = "data/1_美妆护肤/images/p_beauty_002_live.jpg",
            spotlight = SpotlightUiModel(
                skinType = listOf("混油皮", "敏感肌"),
                features = listOf("温和清洁", "修护", "低刺激"),
                exclude = listOf("酒精", "重香精"),
                description = "适合想兼顾清洁和舒缓的人群",
            ),
            reviewsSummary = "多数评价认为泡沫细腻，洗后不拔干",
            reason = "适合偏温和需求的人群，可作为油皮洁面备选",
        ),
        ProductUiModel(
            skuId = "p101",
            name = "主动降噪真无线耳机",
            category = "数码/音频",
            brand = "SoundBeat",
            price = 459.0,
            stock = 18,
            imageUrl = "data/2_数码电子/images/p_digital_001_live.jpg",
            spotlight = SpotlightUiModel(
                features = listOf("主动降噪", "蓝牙 5.3", "28 小时续航"),
                description = "适合通勤和运动场景的日常耳机",
            ),
            reviewsSummary = "连接稳定，性价比不错",
        ),
    )

    val sampleMessages = listOf(
        ChatMessageUiModel(
            id = "m1",
            content = "推荐一款适合油皮的洗面奶",
            isUser = true,
        ),
        ChatMessageUiModel(
            id = "m2",
            content = "我先根据当前商品库给你找到了几款候选，可以先看商品卡片。",
            isUser = false,
        ),
    )

    val sampleCartItems = listOf(
        CartItemUiModel(
            cartItemId = "p001",
            skuId = "p001",
            name = "清爽控油氨基酸洗面奶",
            price = 89.0,
            quantity = 1,
            imageUrl = "data/1_美妆护肤/images/p_beauty_001_live.jpg",
        ),
    )

    val sampleCartSnapshot = CartSnapshotUiModel(
        items = sampleCartItems,
        totalPrice = 89.0,
    )
}
