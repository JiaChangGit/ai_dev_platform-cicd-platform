#include <assert.h>
#include <stdint.h>

#include "fw_core.h"

int main(void) {
    const fw_read_request_t valid = {1, 8, 4};
    const fw_read_request_t zero_namespace = {0, 8, 4};
    const fw_read_request_t out_of_range = {1, 1023, 2};
    const fw_read_request_t overflow = {1, UINT64_MAX, 2};

    assert(fw_validate_read(&valid, 1024) == FW_STATUS_OK);
    assert(fw_validate_read(&zero_namespace, 1024) == FW_STATUS_INVALID_ARGUMENT);
    assert(fw_validate_read(&out_of_range, 1024) == FW_STATUS_OUT_OF_RANGE);
    assert(fw_validate_read(&overflow, UINT64_MAX) == FW_STATUS_OUT_OF_RANGE);
    assert(fw_validate_read(0, 1024) == FW_STATUS_INVALID_ARGUMENT);
    return 0;
}
