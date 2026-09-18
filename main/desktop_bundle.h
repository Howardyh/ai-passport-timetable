#pragma once
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include "timetable.h"
#define DESKTOP_CAPACITY (1024u * 1024u)
#define DESKTOP_MAX_EVENTS 1024u
extern const uint8_t desktop_blob[DESKTOP_CAPACITY];
bool desktop_bundle_parse(const uint8_t *data, size_t capacity,
                          timetable_event_t *events, size_t *count);
bool desktop_bundle_init(void);
uint32_t desktop_u32(const uint8_t *p);
uint16_t desktop_u16(const uint8_t *p);
