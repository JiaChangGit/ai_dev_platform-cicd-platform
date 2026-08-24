#include "fw_core.h"

static void fw_trace_append(
    fw_trace_buffer_t *trace,
    fw_trace_event_t event,
    fw_status_t status,
    const fw_read_request_t *request
) {
    fw_trace_record_t *record;

    if (trace == 0) {
        return;
    }
    record = &trace->records[trace->next_sequence % FW_TRACE_CAPACITY];
    record->sequence = trace->next_sequence;
    record->event = event;
    record->status = status;
    record->namespace_id = request == 0 ? 0U : request->namespace_id;
    record->start_lba = request == 0 ? 0U : request->start_lba;
    record->sector_count = request == 0 ? 0U : request->sector_count;
    trace->next_sequence++;
    if (trace->count < FW_TRACE_CAPACITY) {
        trace->count++;
    }
}

void fw_trace_init(fw_trace_buffer_t *trace) {
    uint32_t index;

    if (trace == 0) {
        return;
    }
    trace->next_sequence = 0U;
    trace->count = 0U;
    for (index = 0U; index < FW_TRACE_CAPACITY; index++) {
        trace->records[index] = (fw_trace_record_t){0};
    }
}

int fw_trace_get(
    const fw_trace_buffer_t *trace,
    uint32_t oldest_index,
    fw_trace_record_t *record
) {
    uint32_t sequence;

    if (trace == 0 || record == 0 || oldest_index >= trace->count) {
        return 0;
    }
    sequence = trace->next_sequence - trace->count + oldest_index;
    *record = trace->records[sequence % FW_TRACE_CAPACITY];
    return record->sequence == sequence;
}

fw_status_t fw_validate_read(
    const fw_read_request_t *request,
    uint64_t namespace_sector_count
) {
    return fw_validate_read_traced(request, namespace_sector_count, 0);
}

fw_status_t fw_validate_read_traced(
    const fw_read_request_t *request,
    uint64_t namespace_sector_count,
    fw_trace_buffer_t *trace
) {
    uint64_t end_lba;
    fw_status_t status = FW_STATUS_OK;

    fw_trace_append(trace, FW_TRACE_READ_RECEIVED, FW_STATUS_OK, request);
    if (request == 0 || request->namespace_id == 0 || request->sector_count == 0) {
        status = FW_STATUS_INVALID_ARGUMENT;
    } else {
        end_lba = request->start_lba + (uint64_t)request->sector_count;
        if (end_lba < request->start_lba || end_lba > namespace_sector_count) {
            status = FW_STATUS_OUT_OF_RANGE;
        }
    }
    fw_trace_append(
        trace,
        status == FW_STATUS_OK ? FW_TRACE_READ_ACCEPTED : FW_TRACE_READ_REJECTED,
        status,
        request
    );
    return status;
}
