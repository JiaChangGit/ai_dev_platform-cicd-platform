# Android App 最小範例

此範例驗證 Kotlin Android App 的基本建置、單元測試與 lint 流程，不包含產品商業邏輯。

版本基準：

- Android Gradle Plugin 9.2.0
- Gradle 9.4.1
- JDK 17
- AGP 9.2 內建 Kotlin（built-in Kotlin）
- compileSdk／targetSdk 36

AGP 9 已預設啟用內建 Kotlin，因此範例不套用舊的 `org.jetbrains.kotlin.android` 外掛。CI 可使用 `gradle/actions/setup-gradle@v6` 安裝 Gradle 9.4.1，不需要在本範例保存 Gradle Wrapper JAR。
