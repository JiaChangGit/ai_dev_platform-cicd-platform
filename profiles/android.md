# Android Profile

最小 CI 通常包含 Gradle release build、unit test、Android lint、instrumentation test（可使用 emulator）及相依套件安全掃描。發行證據（release evidence）須記錄 `versionCode`／`versionName`、APK 或 AAB 的 SHA-256、Android App Signing 驗證結果與 Play 發布所需的核准資訊。平台的 keyless attestation 或組織核准簽章是供應鏈來源關卡，不取代 Android 原生簽章。

平台驗收範例位於 `examples/android-app/`。目前使用 AGP 9.2 內建 Kotlin、Gradle 9.4.1 與 JDK 17；產品採用前仍須依 Android 官方相容性表確認版本。
