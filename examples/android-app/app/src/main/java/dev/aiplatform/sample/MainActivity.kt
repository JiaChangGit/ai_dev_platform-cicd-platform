package dev.aiplatform.sample

import android.app.Activity
import android.os.Bundle
import android.widget.TextView

class MainActivity : Activity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val checks = listOf(
            BuildCheck("需求已確認", CheckState.PASSED),
            BuildCheck("單元測試", CheckState.PASSED),
            BuildCheck("正式簽章", CheckState.BLOCKED),
        )
        setContentView(TextView(this).apply {
            text = BuildStatus.render("1.0.0", checks)
            setPadding(32, 32, 32, 32)
        })
    }
}
