#include <stdio.h>

#include "fw_core.h"

int main(void) {
    const fw_read_request_t request = {
        .namespace_id = 1,
        .start_lba = 0,
        .sector_count = 8,
    };
    const fw_status_t status = fw_validate_read(&request, 1024);

    printf("ssd-pcie-fw sample status=%d\n", (int)status);
    return status == FW_STATUS_OK ? 0 : 1;
}
