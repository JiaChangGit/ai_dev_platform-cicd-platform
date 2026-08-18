# SSD PCIe 韌體最小範例

此範例只驗證通用 C11 韌體開發流程：編譯器警告、host 單元測試與成品打包。範例不實作 PCIe／NVMe 命令、不操作硬體暫存器，也不包含控制器供應商資料。

```bash
make all
make test
make lint
make package
```

產生的 `.elf` 只是 host 驗收成品，不是可燒錄到實際 SSD 控制器的韌體映像檔。
