package com.yourteam.ecommerceguider.data.repository

import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
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
    fun scenarioBundlePayloadParsesOverviewAndItems() {
        val planRole = "\u8d1f\u8d23\u624b\u81c2\u3001\u817f\u90e8\u7b49\u88f8\u9732\u76ae\u80a4\u7684\u65e5\u5e38\u9632\u6652\u548c\u5916\u51fa\u8865\u6d82"
        val payload = JSONObject()
            .put("turn_id", "turn_1")
            .put("recommendation_type", "scenario_bundle")
            .put(
                "bundle",
                JSONObject()
                    .put("title", "\u4e09\u4e9a\u6d77\u8fb9\u5ea6\u5047\u5168\u573a\u666f\u9632\u6652\u7a7f\u642d\u65b9\u6848")
                    .put("plan_title", "\u4e09\u4e9a\u6d77\u8fb9\u5ea6\u5047\u5168\u573a\u666f\u9632\u6652\u7a7f\u642d\u65b9\u6848")
                    .put("summary", "\u8986\u76d6\u9632\u6652\u548c\u6d89\u6c34\u7a7f\u642d")
                    .put("plan_summary", "\u8986\u76d6\u9632\u6652\u548c\u6d89\u6c34\u7a7f\u642d")
                    .put(
                        "plan_items",
                        JSONArray(
                            listOf(
                                JSONObject()
                                    .put("role_name", "\u8eab\u4f53\u9632\u6652")
                                    .put("category_name", "\u9632\u6652\u55b7\u96fe")
                                    .put("sku_id", "sku_sun")
                                    .put("plan_role", planRole),
                            )
                        ),
                    )
                    .put(
                        "items",
                        JSONArray(
                            listOf(
                                JSONObject()
                                    .put("role", "\u8eab\u4f53\u9632\u6652")
                                    .put("role_name", "\u8eab\u4f53\u9632\u6652")
                                    .put("category_name", "\u9632\u6652\u55b7\u96fe")
                                    .put("sku_id", "sku_sun")
                                    .put("plan_role", planRole)
                                    .put("short_reason", planRole)
                                    .put(
                                        "product",
                                        productJson(
                                            skuId = "sku_sun",
                                            name = "\u9632\u6652\u55b7\u96fe",
                                            tags = listOf("\u9632\u6652"),
                                            matchedReasons = listOf("\u8eab\u4f53\u9632\u6652"),
                                        )
                                            .put("plan_role", planRole)
                                            .put("scheme_role", planRole)
                                            .put("plan_role_name", "\u8eab\u4f53\u9632\u6652")
                                            .put("plan_category_name", "\u9632\u6652\u55b7\u96fe"),
                                    ),
                            )
                        ),
                    ),
            )

        val event = ShoppingRepository("http://127.0.0.1:8000")
            .parseChatStreamEventForTest("scenario_bundle", payload)

        assertNotNull(event)
        assertEquals("scenario_bundle", event?.event)
        assertEquals("turn_1", event?.scenarioBundle?.turnId)
        assertEquals("\u4e09\u4e9a\u6d77\u8fb9\u5ea6\u5047\u5168\u573a\u666f\u9632\u6652\u7a7f\u642d\u65b9\u6848", event?.scenarioBundle?.title)
        assertEquals(1, event?.scenarioBundle?.items?.size)
        assertEquals("\u8eab\u4f53\u9632\u6652", event?.scenarioBundle?.items?.firstOrNull()?.role)
        assertEquals("\u9632\u6652\u55b7\u96fe", event?.scenarioBundle?.items?.firstOrNull()?.categoryName)
        assertEquals(planRole, event?.scenarioBundle?.items?.firstOrNull()?.planRole)
        assertEquals(1, event?.scenarioBundle?.planItems?.size)
        assertEquals("\u9632\u6652\u55b7\u96fe", event?.scenarioBundle?.planItems?.firstOrNull()?.categoryName)
        assertEquals("sku_sun", event?.products?.firstOrNull()?.skuId)
        assertEquals(planRole, event?.products?.firstOrNull()?.displayPlanRole)
    }

    @Test
    fun planOverviewPayloadParsesWithoutProductDetails() {
        val payload = JSONObject()
            .put("turn_id", "turn_1")
            .put("recommendation_type", "scenario_bundle")
            .put("plan_title", "\u4e09\u4e9a\u6d77\u8fb9\u5ea6\u5047\u5168\u573a\u666f\u9632\u6652\u7a7f\u642d\u65b9\u6848")
            .put("plan_summary", "\u7edf\u4e00\u65b9\u6848\u8bf4\u660e")
            .put(
                "plan_items",
                JSONArray(
                    listOf(
                        JSONObject()
                            .put("role_name", "\u8eab\u4f53\u9632\u6652")
                            .put("category_name", "\u9632\u6652\u55b7\u96fe")
                            .put("sku_id", "sku_sun")
                            .put("plan_role", "\u8d1f\u8d23\u624b\u81c2\u3001\u817f\u90e8\u7b49\u88f8\u9732\u76ae\u80a4\u7684\u65e5\u5e38\u9632\u6652\u548c\u5916\u51fa\u8865\u6d82"),
                    )
                ),
            )

        val event = ShoppingRepository("http://127.0.0.1:8000")
            .parseChatStreamEventForTest("plan_overview", payload)

        assertNotNull(event)
        assertEquals("plan_overview", event?.event)
        assertEquals("\u4e09\u4e9a\u6d77\u8fb9\u5ea6\u5047\u5168\u573a\u666f\u9632\u6652\u7a7f\u642d\u65b9\u6848", event?.scenarioBundle?.title)
        assertEquals(1, event?.scenarioBundle?.planItems?.size)
        assertEquals(0, event?.scenarioBundle?.items?.size)
    }

    @Test
    fun scenarioBundleProductCardDoesNotCreateRecommendationSection() {
        val planRole = "\u8d1f\u8d23\u624b\u81c2\u3001\u817f\u90e8\u7b49\u88f8\u9732\u76ae\u80a4\u7684\u65e5\u5e38\u9632\u6652\u548c\u5916\u51fa\u8865\u6d82"
        val payload = JSONObject()
            .put("turn_id", "turn_1")
            .put("recommendation_type", "scenario_bundle")
            .put("sku_id", "sku_sun")
            .put("plan_role", planRole)
            .put("role_name", "\u8eab\u4f53\u9632\u6652")
            .put("category_name", "\u9632\u6652\u55b7\u96fe")
            .put(
                "product",
                productJson(
                    skuId = "sku_sun",
                    name = "\u9632\u6652\u55b7\u96fe",
                    tags = listOf("\u9632\u6652"),
                    matchedReasons = listOf("\u8eab\u4f53\u9632\u6652"),
                ),
            )

        val event = ShoppingRepository("http://127.0.0.1:8000")
            .parseChatStreamEventForTest("product_card", payload)

        assertNotNull(event)
        assertEquals("product_card", event?.event)
        assertNull(event?.recommendationSection)
        assertEquals(planRole, event?.product?.displayPlanRole)
        assertEquals("\u8eab\u4f53\u9632\u6652", event?.product?.displayPlanRoleName)
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
