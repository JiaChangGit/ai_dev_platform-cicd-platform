package dev.aiplatform.sample

enum class CheckState(val label: String) {
    PASSED("通過"),
    FAILED("失敗"),
    BLOCKED("待處理"),
}

data class BuildCheck(val name: String, val state: CheckState)

object BuildStatus {
    fun render(version: String, checks: List<BuildCheck>): String {
        require(version.isNotBlank()) { "version 不可為空" }
        val rows = checks.ifEmpty {
            listOf(BuildCheck("尚無檢查結果", CheckState.BLOCKED))
        }
        return buildString {
            appendLine("版本 $version")
            rows.forEach { appendLine("${it.state.label}｜${it.name}") }
        }.trimEnd()
    }
}
