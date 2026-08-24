# Embedded Firmware Profile

最小 CI 通常包含可重現的交叉建置（cross-build）、編譯器警告與靜態分析、單元測試（unit test），以及可取得時的模擬器（emulator）或硬體迴路測試（Hardware-in-the-Loop, HIL）結果。以 SSD PCIe 韌體（firmware）為例，發行證據（release evidence）還須記錄目標控制器（controller）、工具鏈版本、映像檔 SHA-256、供應商／安全啟動簽章驗證及支援的硬體與協定版本；不得臆測未公開規格。平台的 keyless attestation 或組織核准簽章是通用供應鏈來源關卡，不取代產品原生簽章。

平台驗收範例位於 `examples/ssd-pcie-fw/`。它只驗證可攜式 C11 流程，不代表真實控制器或 NVMe 實作。
