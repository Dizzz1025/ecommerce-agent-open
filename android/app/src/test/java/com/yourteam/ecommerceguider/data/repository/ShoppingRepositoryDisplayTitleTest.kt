package com.yourteam.ecommerceguider.data.repository

import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Test

class ShoppingRepositoryDisplayTitleTest {
    @Test
    fun productCardPayloadParsesDisplayTitleAndRecommendReason() {
        val displayTitle = "\u901a\u52e4\u4e0e\u6237\u5916\u517c\u987e\u7684\u9ad8\u500d\u9632\u6652"
        val recommendReason = "\u63a8\u8350\u7406\u7531\u6b63\u6587"
        val payload = JSONObject()
            .put("turn_id", "turn_1")
            .put("request_id", "turn_1")
            .put("section_index", 0)
            .put("sku_id", "sku_1")
            .put("product_id", "product_1")
            .put("display_title", displayTitle)
            .put("recommend_reason", recommendReason)

        val event = ShoppingRepository("http://127.0.0.1:8000")
            .parseChatStreamEventForTest("product_card", payload)

        assertNotNull(event)
        assertEquals("product_card", event?.event)
        assertEquals(displayTitle, event?.recommendationSection?.displayTitle)
        assertEquals(recommendReason, event?.recommendationSection?.recommendReason)
        assertEquals(0, event?.recommendationSection?.sectionIndex)
        assertEquals("sku_1", event?.recommendationSection?.skuId)
    }

    @Test
    fun productCardPayloadKeepsOwnTagsAndDoesNotDisplayMatchedReasonsAsTags() {
        val payload = JSONObject()
            .put("turn_id", "turn_1")
            .put("request_id", "turn_1")
            .put("section_index", 0)
            .put("sku_id", "p_food_003")
            .put(
                "product",
                productJson(
                    skuId = "p_food_003",
                    name = "\u519c\u592b\u5c71\u6cc9 \u4e1c\u65b9\u6811\u53f6 \u65e0\u7cd6\u4e4c\u9f99\u8336",
                    tags = listOf("\u65e0\u7cd6", "\u4f4e\u7cd6"),
                    matchedReasons = listOf("\u6e29\u548c", "\u62cd\u7167"),
                ),
            )

        val product = ShoppingRepository("http://127.0.0.1:8000")
            .parseChatStreamEventForTest("product_card", payload)
            ?.product

        assertNotNull(product)
        assertEquals(listOf("\u65e0\u7cd6", "\u4f4e\u7cd6"), product?.tags)
        assertEquals(listOf("\u6e29\u548c", "\u62cd\u7167"), product?.matchedReasons)
        assertEquals(listOf("\u65e0\u7cd6", "\u4f4e\u7cd6"), product?.displayTags)
        assertFalse(product?.displayTags.orEmpty().contains("\u6e29\u548c"))
        assertFalse(product?.displayTags.orEmpty().contains("\u62cd\u7167"))
    }

    @Test
    fun productCardPayloadWithEmptyTagsDoesNotInheritSectionOrMatchedTags() {
        val payload = JSONObject()
            .put("turn_id", "turn_1")
            .put("request_id", "turn_1")
            .put("section_index", 0)
            .put("sku_id", "p_food_026")
            .put("recommendation_tags", JSONArray(listOf("\u6e29\u548c", "\u62cd\u7167")))
            .put(
                "product",
                productJson(
                    skuId = "p_food_026",
                    name = "\u519c\u592b\u5c71\u6cc9\u5929\u7136\u996e\u7528\u6c34",
                    tags = emptyList(),
                    matchedReasons = listOf("\u6e29\u548c", "\u62cd\u7167"),
                ),
            )

        val product = ShoppingRepository("http://127.0.0.1:8000")
            .parseChatStreamEventForTest("product_card", payload)
            ?.product

        assertNotNull(product)
        assertEquals(emptyList<String>(), product?.tags)
        assertEquals(emptyList<String>(), product?.displayTags)
    }

    private fun productJson(
        skuId: String,
        name: String,
        tags: List<String>,
        matchedReasons: List<String>,
    ): JSONObject {
        return JSONObject()
            .put("sku_id", skuId)
            .put("product_id", skuId)
            .put("name", name)
            .put("category", "\u98df\u54c1\u996e\u6599")
            .put("brand", "\u519c\u592b\u5c71\u6cc9")
            .put("price", 9.9)
            .put("stock", 10)
            .put("tags", JSONArray(tags))
            .put("matched_reasons", JSONArray(matchedReasons))
    }
}
