#include "desktop_bundle.h"
#include <string.h>

uint32_t desktop_u32(const uint8_t *p) {
    return (uint32_t)p[0] | (uint32_t)p[1]<<8 | (uint32_t)p[2]<<16 | (uint32_t)p[3]<<24;
}
uint16_t desktop_u16(const uint8_t *p) { return (uint16_t)(p[0] | p[1]<<8); }
static bool range(uint32_t off, uint32_t size, uint32_t total) {
    return off >= 136 && off <= total && size <= total-off;
}
static bool text_ok(const uint8_t *d, uint32_t off, uint32_t total) {
    if (!range(off, 1, total)) return false;
    uint32_t n=total-off; if(n>385) n=385;
    return memchr(d+off, 0, n)!=NULL;
}
static uint32_t crc32(const uint8_t *p, size_t n) {
    uint32_t crc=0xffffffffu;
    while(n--) {
        crc^=*p++;
        for(int bit=0;bit<8;bit++) crc=(crc>>1)^((crc&1) ? 0xedb88320u : 0);
    }
    return crc^0xffffffffu;
}
bool desktop_bundle_parse(const uint8_t *d, size_t capacity,
                          timetable_event_t *events, size_t *count) {
    *count=0;
    if(capacity<136 || desktop_u32(d+32)!=1) return false;
    uint32_t total=desktop_u32(d+36), n=desktop_u32(d+44), records=desktop_u32(d+48);
    if(total<136 || total>capacity || n==0 || n>DESKTOP_MAX_EVENTS ||
       !range(records,n*20,total) || crc32(d+44,total-44)!=desktop_u32(d+40)) return false;
    for(uint32_t i=0;i<n;i++) {
        const uint8_t *e=d+records+i*20;
        uint16_t start=desktop_u16(e+4),end=desktop_u16(e+6);
        int32_t day=(int32_t)desktop_u32(e);
        if(start>=end || end>=1440 || (i && (day<events[i-1].day ||
           (day==events[i-1].day && start<events[i-1].start)))) return false;
        for(unsigned k=8;k<20;k+=4) if(!text_ok(d,desktop_u32(e+k),total)) return false;
        events[i]=(timetable_event_t){day,start,end,(const char *)d+desktop_u32(e+8),
                   (const char *)d+desktop_u32(e+12),(const char *)d+desktop_u32(e+16)};
        if(!events[i].name[0]) return false;
    }
    for(unsigned f=0;f<3;f++) {
        uint32_t off=desktop_u32(d+56+f*4);
        if(!range(off,16,total)) return false;
        uint32_t glyphs=desktop_u32(d+off),table=desktop_u32(d+off+4);
        if(!glyphs || glyphs>4096 || !range(table,glyphs*20,total) ||
           desktop_u32(d+off+8)!=(f==0?20u:f==1?22u:26u) || desktop_u32(d+off+12)!=6) return false;
        uint32_t prev=0;
        for(uint32_t i=0;i<glyphs;i++) {
            const uint8_t *g=d+table+i*20;
            uint32_t cp=desktop_u32(g),w=desktop_u16(g+8),h=desktop_u16(g+10);
            if(cp<=prev || cp>0x10ffff || w>64 || h>64 ||
               !range(desktop_u32(g+4),w*h,total)) return false;
            prev=cp;
        }
    }
    *count=n; return true;
}

#ifdef PASSPORT_DESKTOP_TEMPLATE
static timetable_event_t loaded_events[DESKTOP_MAX_EVENTS];
const timetable_event_t *timetable_events=loaded_events;
size_t timetable_count;
static char source_hash[65];
const char *timetable_source_hash=source_hash;
bool desktop_bundle_init(void) {
    if(!desktop_bundle_parse(desktop_blob,DESKTOP_CAPACITY,loaded_events,&timetable_count)) return false;
    memcpy(source_hash,desktop_blob+72,64); source_hash[64]=0;
    return true;
}
#endif
