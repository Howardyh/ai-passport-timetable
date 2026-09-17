#include "timetable.h"

size_t timetable_day_range(const timetable_event_t *events, size_t count, int32_t day, size_t *first) {
    size_t lo = 0, hi = count;
    while (lo < hi) {
        size_t mid = lo + (hi - lo) / 2;
        if (events[mid].day < day) lo = mid + 1;
        else hi = mid;
    }
    *first = lo;
    while (lo < count && events[lo].day == day) ++lo;
    return lo - *first;
}

int timetable_phase(const timetable_event_t *event, int32_t day, int minute) {
    if (day < event->day || (day == event->day && minute < event->start)) return -1;
    if (day > event->day || minute >= event->end) return 1;
    return 0;
}

int32_t timetable_local_day(int64_t utc) {
    int64_t local = utc + 28800;
    return (int32_t)(local >= 0 ? local / 86400 : (local - 86399) / 86400);
}

int timetable_local_minute(int64_t utc) {
    int64_t local = (utc + 28800) % 86400;
    if (local < 0) local += 86400;
    return (int)(local / 60);
}

int timetable_days_in_month(int year, int month) {
    static const int days[] = {31,28,31,30,31,30,31,31,30,31,30,31};
    if (month < 1 || month > 12) return 0;
    return days[month - 1] + (month == 2 && year % 4 == 0 && (year % 100 != 0 || year % 400 == 0));
}
