#ifndef AI_DEV_PLATFORM_FW_CORE_H
#define AI_DEV_PLATFORM_FW_CORE_H

#include <stdint.h>

#define FW_TRACE_CAPACITY 8U

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

typedef enum {
    FW_TRACE_READ_RECEIVED = 1,
    FW_TRACE_READ_ACCEPTED = 2,
    FW_TRACE_READ_REJECTED = 3
} fw_trace_event_t;

typedef struct {
    uint32_t sequence;
    fw_trace_event_t event;
    fw_status_t status;
    uint32_t namespace_id;
    uint64_t start_lba;
    uint16_t sector_count;
} fw_trace_record_t;

typedef struct {
    fw_trace_record_t records[FW_TRACE_CAPACITY];
    uint32_t next_sequence;
    uint32_t count;
} fw_trace_buffer_t;

void fw_trace_init(fw_trace_buffer_t *trace);

int fw_trace_get(
    const fw_trace_buffer_t *trace,
    uint32_t oldest_index,
    fw_trace_record_t *record
);

fw_status_t fw_validate_read(
    const fw_read_request_t *request,
    uint64_t namespace_sector_count
);

fw_status_t fw_validate_read_traced(
    const fw_read_request_t *request,
    uint64_t namespace_sector_count,
    fw_trace_buffer_t *trace
);

#endif
