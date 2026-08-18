package dev.aiplatform.sample

import org.junit.Assert.assertEquals
import org.junit.Test

class GreetingTest {
    @Test
    fun returnsStableSampleText() {
        assertEquals("ai-dev-platform Android sample", Greeting.text())
    }
}
