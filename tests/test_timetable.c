#include "timetable.h"
#include <assert.h>
#include <stdio.h>

int main(void) {
    timetable_event_t events[] = {{10,480,570,"A","",""},{10,600,690,"B","",""},{12,500,600,"C","",""}};
    size_t first = 99;
    assert(timetable_day_range(events, 3, 10, &first) == 2 && first == 0);
    assert(timetable_day_range(events, 3, 11, &first) == 0 && first == 2);
    assert(timetable_day_range(events, 3, 13, &first) == 0 && first == 3);
    assert(timetable_day_range(events, 0, 10, &first) == 0 && first == 0);
    assert(timetable_phase(&events[0], 10, 479) == -1);
    assert(timetable_phase(&events[0], 10, 480) == 0);
    assert(timetable_phase(&events[0], 10, 569) == 0);
    assert(timetable_phase(&events[0], 10, 570) == 1);
    assert(timetable_phase(&events[0], 9, 1000) == -1);
    assert(timetable_local_day(57599) == 0);
    assert(timetable_local_day(57600) == 1);
    assert(timetable_local_minute(57600) == 0);
    assert(timetable_local_minute(0) == 480);
    assert(timetable_days_in_month(2028, 2) == 29);
    assert(timetable_days_in_month(2100, 2) == 28);
    puts("Timetable logic: PASS");
    return 0;
}
