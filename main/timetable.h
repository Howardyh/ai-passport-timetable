#pragma once
#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>

typedef struct {
    int32_t day; // Shanghai civil days since 1970-01-01, not UTC days.
    uint16_t start;
    uint16_t end;
    const char *name;
    const char *location;
    const char *description;
} timetable_event_t;

#ifdef PASSPORT_DESKTOP_TEMPLATE
extern const timetable_event_t *timetable_events;
extern size_t timetable_count;
extern const char *timetable_source_hash;
#else
extern const timetable_event_t timetable_events[];
extern const size_t timetable_count;
extern const char timetable_source_hash[];
#endif
size_t timetable_day_range(const timetable_event_t *events, size_t count, int32_t day, size_t *first);
int timetable_phase(const timetable_event_t *event, int32_t day, int minute);
int32_t timetable_local_day(int64_t utc);
int timetable_local_minute(int64_t utc);
int timetable_days_in_month(int year, int month);
