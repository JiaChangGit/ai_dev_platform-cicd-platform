#include "fw_core.h"

fw_status_t fw_validate_read(
    const fw_read_request_t *request,
    uint64_t namespace_sector_count
) {
    uint64_t end_lba;

    if (request == 0 || request->namespace_id == 0 || request->sector_count == 0) {
        return FW_STATUS_INVALID_ARGUMENT;
    }
    end_lba = request->start_lba + (uint64_t)request->sector_count;
    if (end_lba < request->start_lba || end_lba > namespace_sector_count) {
        return FW_STATUS_OUT_OF_RANGE;
    }
    return FW_STATUS_OK;
}
