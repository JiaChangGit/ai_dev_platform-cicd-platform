package dev.aiplatform.sample

import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Test

class BuildStatusTest {
    @Test
    fun rendersChecksInInputOrder() {
        val text = BuildStatus.render(
            version = "1.0.0",
            checks = listOf(
                BuildCheck("單元測試", CheckState.PASSED),
                BuildCheck("簽章", CheckState.BLOCKED),
            ),
        )

        assertEquals("版本 1.0.0\n通過｜單元測試\n待處理｜簽章", text)
    }

    @Test
    fun explainsEmptyCheckList() {
        assertEquals(
            "版本 1.0.0\n待處理｜尚無檢查結果",
            BuildStatus.render("1.0.0", emptyList()),
        )
    }

    @Test
    fun rejectsBlankVersion() {
        assertThrows(IllegalArgumentException::class.java) {
            BuildStatus.render(" ", emptyList())
        }
    }
}
