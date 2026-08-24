#include <stdio.h>

#include "fw_core.h"

int main(void) {
    const fw_read_request_t request = {
        .namespace_id = 1,
        .start_lba = 0,
        .sector_count = 8,
    };
    fw_trace_buffer_t trace;
    fw_trace_record_t record;
    fw_status_t status;
    uint32_t index;

    fw_trace_init(&trace);
    status = fw_validate_read_traced(&request, 1024, &trace);
    for (index = 0U; index < trace.count; index++) {
        if (fw_trace_get(&trace, index, &record)) {
            printf(
                "seq=%u event=%d status=%d nsid=%u lba=%llu count=%u\n",
                record.sequence,
                (int)record.event,
                (int)record.status,
                record.namespace_id,
                (unsigned long long)record.start_lba,
                (unsigned int)record.sector_count
            );
        }
    }
    return status == FW_STATUS_OK ? 0 : 1;
}
