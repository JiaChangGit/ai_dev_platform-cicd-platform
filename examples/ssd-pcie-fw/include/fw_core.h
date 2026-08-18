#ifndef AI_DEV_PLATFORM_FW_CORE_H
#define AI_DEV_PLATFORM_FW_CORE_H

#include <stdint.h>

typedef enum {
    FW_STATUS_OK = 0,
    FW_STATUS_INVALID_ARGUMENT = 1,
    FW_STATUS_OUT_OF_RANGE = 2
} fw_status_t;

typedef struct {
    uint32_t namespace_id;
    uint64_t start_lba;
    uint16_t sector_count;
} fw_read_request_t;

fw_status_t fw_validate_read(
    const fw_read_request_t *request,
    uint64_t namespace_sector_count
);

#endif
