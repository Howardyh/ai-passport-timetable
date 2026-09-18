#include "desktop_bundle.h"
#include "lvgl.h"
#include <string.h>

static const uint8_t *font_header(const lv_font_t *font) {
    unsigned index=(unsigned)(uintptr_t)font->dsc;
    return desktop_blob+desktop_u32(desktop_blob+56+index*4);
}
static bool glyph(const lv_font_t *font,lv_font_glyph_dsc_t *out,uint32_t cp,uint32_t next) {
    (void)next;
    const uint8_t *h=font_header(font);
    uint32_t lo=0,hi=desktop_u32(h),table=desktop_u32(h+4);
    while(lo<hi) {
        uint32_t mid=lo+(hi-lo)/2;
        if(desktop_u32(desktop_blob+table+mid*20)<cp) lo=mid+1; else hi=mid;
    }
    if(lo>=desktop_u32(h)) return false;
    const uint8_t *g=desktop_blob+table+lo*20;
    if(desktop_u32(g)!=cp) return false;
    out->adv_w=desktop_u16(g+12); out->box_w=desktop_u16(g+8); out->box_h=desktop_u16(g+10);
    out->ofs_x=(int16_t)desktop_u16(g+14); out->ofs_y=(int16_t)desktop_u16(g+16);
    out->format=LV_FONT_GLYPH_FORMAT_A8; out->stride=out->box_w;
    out->gid.index=table+lo*20; out->is_placeholder=false;
    return true;
}
static const void *bitmap(lv_font_glyph_dsc_t *g,lv_draw_buf_t *buf) {
    const uint8_t *p=desktop_blob+desktop_u32(desktop_blob+g->gid.index+4);
    if(g->req_raw_bitmap) return p;
    if(!buf || !g->box_w || !g->box_h) return NULL;
    uint32_t stride=lv_draw_buf_width_to_stride(g->box_w,LV_COLOR_FORMAT_A8);
    for(unsigned y=0;y<g->box_h;y++) memcpy(buf->data+y*stride,p+y*g->box_w,g->box_w);
    return buf;
}
#define DESKTOP_FONT(size,index) const lv_font_t course_font_##size={ \
    .get_glyph_dsc=glyph,.get_glyph_bitmap=bitmap,.line_height=size+6,.base_line=6, \
    .static_bitmap=1,.underline_position=-2,.underline_thickness=1,.dsc=(void *)(uintptr_t)index}
DESKTOP_FONT(14,0);
DESKTOP_FONT(16,1);
DESKTOP_FONT(20,2);
