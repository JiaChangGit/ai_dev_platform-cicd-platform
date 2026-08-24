#include <assert.h>
#include <stdint.h>

#include "fw_core.h"

int main(void) {
    const fw_read_request_t valid = {1, 8, 4};
    const fw_read_request_t zero_namespace = {0, 8, 4};
    const fw_read_request_t out_of_range = {1, 1023, 2};
    const fw_read_request_t overflow = {1, UINT64_MAX, 2};
    fw_trace_buffer_t trace;
    fw_trace_record_t record;
    uint32_t index;

    assert(fw_validate_read(&valid, 1024) == FW_STATUS_OK);
    assert(fw_validate_read(&zero_namespace, 1024) == FW_STATUS_INVALID_ARGUMENT);
    assert(fw_validate_read(&out_of_range, 1024) == FW_STATUS_OUT_OF_RANGE);
    assert(fw_validate_read(&overflow, UINT64_MAX) == FW_STATUS_OUT_OF_RANGE);
    assert(fw_validate_read(0, 1024) == FW_STATUS_INVALID_ARGUMENT);

    fw_trace_init(&trace);
    assert(fw_validate_read_traced(&valid, 1024, &trace) == FW_STATUS_OK);
    assert(trace.count == 2U);
    assert(fw_trace_get(&trace, 0U, &record));
    assert(record.sequence == 0U);
    assert(record.event == FW_TRACE_READ_RECEIVED);
    assert(record.namespace_id == 1U);
    assert(fw_trace_get(&trace, 1U, &record));
    assert(record.event == FW_TRACE_READ_ACCEPTED);
    assert(record.status == FW_STATUS_OK);

    for (index = 0U; index < 5U; index++) {
        assert(
            fw_validate_read_traced(&out_of_range, 1024, &trace) ==
            FW_STATUS_OUT_OF_RANGE
        );
    }
    assert(trace.count == FW_TRACE_CAPACITY);
    assert(trace.next_sequence == 12U);
    assert(fw_trace_get(&trace, 0U, &record));
    assert(record.sequence == 4U);
    assert(fw_trace_get(&trace, FW_TRACE_CAPACITY - 1U, &record));
    assert(record.sequence == 11U);
    assert(record.event == FW_TRACE_READ_REJECTED);
    assert(record.status == FW_STATUS_OUT_OF_RANGE);
    assert(!fw_trace_get(&trace, FW_TRACE_CAPACITY, &record));
    assert(!fw_trace_get(0, 0U, &record));
    return 0;
}
