#include "timetable.h"
#include "bsp_i2c.h"
#include "bsp_display.h"
#include "bsp_button.h"
#include "bsp_battery.h"
#include "bsp_audio.h"
#include "lvgl.h"
#include "esp_log.h"
#include "esp_timer.h"
#include "esp_heap_caps.h"
#include "esp_sleep.h"
#include "esp_wifi.h"
#include "esp_netif.h"
#include "esp_netif_sntp.h"
#include "esp_event.h"
#include "esp_ota_ops.h"
#include "esp_system.h"
#include "driver/usb_serial_jtag.h"
#include "driver/usb_serial_jtag_vfs.h"
#include "nvs_flash.h"
#include "nvs.h"
#include "cJSON.h"
#include "freertos/FreeRTOS.h"
#include "freertos/queue.h"
#include "freertos/task.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <sys/time.h>
#ifdef PASSPORT_DESKTOP_TEMPLATE
#include "desktop_bundle.h"
#else
#include "../assets/fonts/course_glyphs.h"
#endif

LV_FONT_DECLARE(course_font_14);
LV_FONT_DECLARE(course_font_16);
LV_FONT_DECLARE(course_font_20);

#define BG 0x101923
#define CARD 0x1D2B39
#define WHITE 0xF0F4F8
#define MUTED 0x9BACBC
#define ACCENT 0x88E0BD
#define AMBER 0xFFC879
#define MIN_TIME 1704067200LL
#define MAX_TIME 4102444800LL

typedef enum { MSG_KEY, MSG_TIME, MSG_WIFI, MSG_STATUS, MSG_SCREEN } message_type_t;
typedef struct {
    message_type_t type;
    bsp_btn_t button;
    bsp_btn_ev_t event;
    int64_t epoch;
    char ssid[33];
    char password[65];
} message_t;
typedef enum { PAGE_DAY, PAGE_DETAIL, PAGE_MENU, PAGE_CLOCK, PAGE_ABOUT, PAGE_FACTORY } page_t;

static const char *TAG = "courses";
static QueueHandle_t s_queue;
static lv_obj_t *s_screen;
static page_t s_page;
static int32_t s_day;
static size_t s_first, s_count, s_selected;
static int s_menu, s_clock_field;
static struct tm s_edit;
static bool s_valid_time, s_follow_today = true, s_battery_ok;
static bool s_display_off;
static int s_brightness = 70, s_soc = -1;
static int64_t s_last_input, s_last_battery, s_last_save;
static nvs_handle_t s_nvs;
static bool s_nvs_ok;
static char s_ssid[33], s_password[65];
static bool s_wifi_initialized, s_wifi_running, s_sntp_started;
static volatile int s_wifi_status, s_wifi_retries;
static int64_t s_wifi_started_at;
static const char *WEEK[] = {"周日", "周一", "周二", "周三", "周四", "周五", "周六"};
static const char *MENU[] = {"回到今天", "前一天", "后一天", "设置日期时间", "联网校时", "屏幕亮度", "关闭屏幕", "使用说明", "原厂功能"};

static void serial_line(const char *line) {
    // Serial responses are small; app worker owns response ordering.
    usb_serial_jtag_write_bytes(line, strlen(line), pdMS_TO_TICKS(100));
    usb_serial_jtag_write_bytes("\n", 1, pdMS_TO_TICKS(100));
}

static void key_callback(bsp_btn_t button, bsp_btn_ev_t event, void *arg) {
    (void)arg;
    if (!s_queue || (event != BSP_BTN_CLICK && event != BSP_BTN_LONG)) return;
    message_t msg = {.type=MSG_KEY, .button=button, .event=event};
    (void)xQueueSend(s_queue, &msg, 0);
}

static void handle_json(char *line) {
    cJSON *json = cJSON_Parse(line);
    if (!json) { serial_line("COURSE ERROR invalid JSON"); return; }
    message_t msg = {0};
    bool send = false;
    const cJSON *cmd = cJSON_GetObjectItemCaseSensitive(json, "cmd");
    if (cJSON_IsString(cmd) && strcmp(cmd->valuestring, "time") == 0) {
        const cJSON *epoch = cJSON_GetObjectItemCaseSensitive(json, "epoch");
        if (cJSON_IsNumber(epoch) && epoch->valuedouble >= MIN_TIME && epoch->valuedouble < MAX_TIME) {
            msg.type = MSG_TIME; msg.epoch = (int64_t)epoch->valuedouble; send = true;
        }
    } else if (cJSON_IsString(cmd) && strcmp(cmd->valuestring, "wifi") == 0) {
        const cJSON *ssid = cJSON_GetObjectItemCaseSensitive(json, "ssid");
        const cJSON *pass = cJSON_GetObjectItemCaseSensitive(json, "password");
        if (cJSON_IsString(ssid) && cJSON_IsString(pass) && strlen(ssid->valuestring) <= 32 &&
            strlen(pass->valuestring) <= 64) {
            msg.type = MSG_WIFI;
            snprintf(msg.ssid, sizeof(msg.ssid), "%s", ssid->valuestring);
            snprintf(msg.password, sizeof(msg.password), "%s", pass->valuestring);
            send = true;
        }
    } else if (cJSON_IsString(cmd) && strcmp(cmd->valuestring, "status") == 0) {
        msg.type = MSG_STATUS; send = true;
    } else if (cJSON_IsString(cmd) && strcmp(cmd->valuestring, "screen") == 0) {
        msg.type = MSG_SCREEN; send = true;
    } else if (cJSON_IsString(cmd) && strcmp(cmd->valuestring, "key") == 0) {
        const cJSON *key = cJSON_GetObjectItemCaseSensitive(json, "key");
        const cJSON *hold = cJSON_GetObjectItemCaseSensitive(json, "long");
        if (cJSON_IsString(key)) {
            int button = strcmp(key->valuestring, "up") == 0 ? BSP_BTN_UP :
                         strcmp(key->valuestring, "down") == 0 ? BSP_BTN_DOWN :
                         strcmp(key->valuestring, "ok") == 0 ? BSP_BTN_OK : -1;
            if (button >= 0) {
                msg.type=MSG_KEY; msg.button=(bsp_btn_t)button;
                msg.event=cJSON_IsTrue(hold) ? BSP_BTN_LONG : BSP_BTN_CLICK;
                send=true;
            }
        }
    }
    if (send) {
        if (xQueueSend(s_queue, &msg, pdMS_TO_TICKS(50)) != pdTRUE) serial_line("COURSE ERROR busy");
    } else serial_line("COURSE ERROR unsupported command or value");
    cJSON_Delete(json);
}

static void serial_task(void *arg) {
    (void)arg;
    char line[512]; size_t used=0; bool overflow=false;
    for (;;) {
        char ch;
        if (usb_serial_jtag_read_bytes(&ch, 1, pdMS_TO_TICKS(100)) <= 0) continue;
        if (ch == '\n') {
            if (overflow) serial_line("COURSE ERROR line too long");
            else if (used) { line[used]='\0'; handle_json(line); }
            used=0; overflow=false;
        } else if (ch != '\r') {
            if (used < sizeof(line)-1 && !overflow) line[used++]=ch;
            else overflow=true;
        }
    }
}

static void on_sntp(struct timeval *tv) {
    message_t msg = {.type=MSG_TIME, .epoch=tv->tv_sec};
    (void)xQueueSend(s_queue, &msg, 0);
}

static void wifi_event(void *arg, esp_event_base_t base, int32_t id, void *data) {
    (void)arg; (void)data;
    if (base == WIFI_EVENT && id == WIFI_EVENT_STA_START) esp_wifi_connect();
    if (base == WIFI_EVENT && id == WIFI_EVENT_STA_DISCONNECTED) {
        if (s_wifi_status != 4 && s_wifi_retries++ < 3) esp_wifi_connect();
        else s_wifi_status=3;
    }
    if (base == IP_EVENT && id == IP_EVENT_STA_GOT_IP) {
        s_wifi_status=2;
        if (s_sntp_started) esp_netif_sntp_start();
    }
}

static void wifi_stop(void) {
    if (!s_wifi_running) return;
    s_wifi_status=4;
    if (s_sntp_started) esp_netif_sntp_deinit();
    s_sntp_started=false;
    esp_wifi_stop();
    s_wifi_running=false;
}

static void wifi_start(void) {
    if (!s_ssid[0] || s_wifi_running) return;
    if (!s_wifi_initialized) {
        if (esp_netif_init() != ESP_OK || esp_event_loop_create_default() != ESP_OK) return;
        if (!esp_netif_create_default_wifi_sta()) return;
        wifi_init_config_t init = WIFI_INIT_CONFIG_DEFAULT();
        if (esp_wifi_init(&init) != ESP_OK) return;
        ESP_ERROR_CHECK(esp_event_handler_register(WIFI_EVENT, ESP_EVENT_ANY_ID, wifi_event, NULL));
        ESP_ERROR_CHECK(esp_event_handler_register(IP_EVENT, IP_EVENT_STA_GOT_IP, wifi_event, NULL));
        ESP_ERROR_CHECK(esp_wifi_set_storage(WIFI_STORAGE_RAM));
        s_wifi_initialized=true;
    }
    wifi_config_t config = {0};
    memcpy(config.sta.ssid, s_ssid, strlen(s_ssid));
    memcpy(config.sta.password, s_password, strlen(s_password));
    esp_wifi_set_mode(WIFI_MODE_STA);
    esp_wifi_set_config(WIFI_IF_STA, &config);
    esp_sntp_config_t sntp = ESP_NETIF_SNTP_DEFAULT_CONFIG("ntp.aliyun.com");
    sntp.start=false; sntp.sync_cb=on_sntp;
    if (esp_netif_sntp_init(&sntp) != ESP_OK) { s_wifi_status=3; return; }
    s_sntp_started=true; s_wifi_status=1; s_wifi_retries=0;
    if (esp_wifi_start() != ESP_OK) { esp_netif_sntp_deinit(); s_sntp_started=false; s_wifi_status=3; return; }
    s_wifi_running=true; s_wifi_started_at=esp_timer_get_time();
}

static lv_obj_t *label(lv_obj_t *parent, int x, int y, int width, const char *text, int size, uint32_t color) {
    lv_obj_t *obj=lv_label_create(parent);
    lv_obj_set_pos(obj,x,y); lv_obj_set_width(obj,width);
    lv_obj_set_style_text_font(obj, size==20 ? &course_font_20 : size==14 ? &course_font_14 : &course_font_16,0);
    lv_obj_set_style_text_color(obj,lv_color_hex(color),0);
    lv_label_set_text(obj,text);
    return obj;
}

static lv_obj_t *panel(int x, int y, int width, int height, uint32_t color) {
    lv_obj_t *obj=lv_obj_create(s_screen);
    lv_obj_remove_style_all(obj);
    lv_obj_set_pos(obj,x,y); lv_obj_set_size(obj,width,height);
    lv_obj_set_style_bg_color(obj,lv_color_hex(color),0);
    lv_obj_set_style_bg_opa(obj,LV_OPA_COVER,0); lv_obj_set_style_radius(obj,10,0);
    lv_obj_remove_flag(obj,LV_OBJ_FLAG_SCROLLABLE);
    return obj;
}

static void update_range(bool reset) {
    s_count=timetable_day_range(timetable_events,timetable_count,s_day,&s_first);
    if (reset || s_selected >= s_count) s_selected=0;
    if (reset && s_valid_time && s_day == timetable_local_day(time(NULL))) {
        int minute=timetable_local_minute(time(NULL));
        for (size_t i=0; i<s_count; i++) {
            if (timetable_events[s_first+i].end > minute) { s_selected=i; break; }
        }
    }
}

static void day_text(int32_t day, char *out, size_t size) {
    time_t value=(int64_t)day*86400; struct tm date;
    gmtime_r(&value,&date);
    snprintf(out,size,"%02d/%02d  %s",date.tm_mon+1,date.tm_mday,WEEK[date.tm_wday]);
}

static void capture_flush(lv_event_t *event);
static void capture_done(lv_event_t *event);

static void render(void) {
    if (!bsp_lvgl_lock(500)) return;
    if (!s_screen) {
        s_screen=lv_obj_create(NULL); lv_obj_remove_style_all(s_screen);
        lv_obj_set_style_bg_color(s_screen,lv_color_hex(BG),0);
        lv_obj_set_style_bg_opa(s_screen,LV_OPA_COVER,0);
        lv_obj_remove_flag(s_screen,LV_OBJ_FLAG_SCROLLABLE);
        lv_screen_load(s_screen);
        lv_display_add_event_cb(lv_display_get_default(),capture_flush,LV_EVENT_FLUSH_START,NULL);
        lv_display_add_event_cb(lv_display_get_default(),capture_done,LV_EVENT_REFR_READY,NULL);
    }
    lv_obj_clean(s_screen);
    char buf[512];
    label(s_screen,20,10,158,"我的课程",16,ACCENT);
    if (s_soc >= 0) snprintf(buf,sizeof(buf),"%d%%",s_soc);
    else snprintf(buf,sizeof(buf),"--%%");
    lv_obj_t *battery=label(s_screen,179,12,42,buf,14,MUTED);
    lv_obj_set_style_text_align(battery,LV_TEXT_ALIGN_RIGHT,0);

    if (s_page == PAGE_DAY || s_page == PAGE_DETAIL) {
        day_text(s_day,buf,sizeof(buf)); label(s_screen,16,37,206,buf,20,WHITE);
        if (s_valid_time) {
            time_t now=time(NULL); struct tm current; localtime_r(&now,&current);
            snprintf(buf,sizeof(buf),"%02d:%02d   %s · %u节课",current.tm_hour,current.tm_min,
                     s_day==timetable_local_day(now) ? "今天" : "浏览",(unsigned)s_count);
        } else snprintf(buf,sizeof(buf),"时间待校准 · 长按确定设置");
        label(s_screen,16,66,212,buf,14,s_valid_time ? MUTED : AMBER);

        if (!s_count) {
            label(s_screen,26,129,190,"今天没有课程",20,WHITE);
            if (s_day<timetable_events[0].day || s_day>timetable_events[timetable_count-1].day)
                label(s_screen,26,173,190,"当前日期超出\n已导入课表范围",16,AMBER);
            else label(s_screen,26,173,190,"享受自己的时间",16,MUTED);
        } else if (s_page == PAGE_DETAIL) {
            const timetable_event_t *e=&timetable_events[s_first+s_selected];
            lv_obj_t *card=panel(12,92,216,188,CARD);
            label(card,12,10,192,e->name,20,WHITE);
            snprintf(buf,sizeof(buf),"%02d:%02d - %02d:%02d",e->start/60,e->start%60,e->end/60,e->end%60);
            label(card,12,67,194,buf,16,ACCENT);
            snprintf(buf,sizeof(buf),"教室: %s",e->location);
            label(card,12,91,194,buf,16,WHITE);
            label(card,12,133,194,e->description,14,MUTED);
        } else {
            size_t offset=(s_selected/3)*3;
            for (size_t row=0; row<3 && offset+row<s_count; row++) {
                size_t i=offset+row; const timetable_event_t *e=&timetable_events[s_first+i];
                bool selected=i==s_selected;
                lv_obj_t *card=panel(12,91+(int)row*63,216,58,selected ? 0x24493F : CARD);
                lv_obj_t *name=label(card,10,5,196,e->name,16,WHITE);
                lv_label_set_long_mode(name,LV_LABEL_LONG_DOT); lv_obj_set_height(name,23);
                snprintf(buf,sizeof(buf),"%02d:%02d  %s",e->start/60,e->start%60,e->location);
                lv_obj_t *meta=label(card,10,30,160,buf,14,selected ? ACCENT : MUTED);
                lv_label_set_long_mode(meta,LV_LABEL_LONG_DOT); lv_obj_set_height(meta,20);
                if (s_valid_time && s_day==timetable_local_day(time(NULL))) {
                    int phase=timetable_phase(e,s_day,timetable_local_minute(time(NULL)));
                    if(phase==0 || (phase<0 && selected)) label(card,175,31,32,phase==0 ? "现在" : "待上",14,ACCENT);
                }
            }
        }
        label(s_screen,16,278,212,s_page==PAGE_DETAIL ? "上下切课  确定返回" : "上下选课  确定详情",14,MUTED);
        label(s_screen,23,296,194,"长按上下换天 / 确定菜单",14,MUTED);
    } else if (s_page == PAGE_MENU) {
        label(s_screen,16,40,210,"课程工具",20,WHITE);
        int offset=(s_menu/5)*5;
        for (int i=offset; i<offset+5 && i<9; i++) {
            lv_obj_t *card=panel(12,76+(i-offset)*40,216,35,i==s_menu ? 0x24493F : CARD);
            if (i==5) snprintf(buf,sizeof(buf),"%s  %d%%",MENU[i],s_brightness);
            else snprintf(buf,sizeof(buf),"%s",MENU[i]);
            label(card,10,6,195,buf,16,i==s_menu ? ACCENT : WHITE);
        }
        label(s_screen,18,282,210,"上下选择  确定执行",14,MUTED);
        label(s_screen,30,296,190,"长按确定返回课程",14,MUTED);
    } else if (s_page == PAGE_CLOCK) {
        static const char *fields[]={"年","月","日","时","分"};
        label(s_screen,16,43,210,"设置日期时间",20,WHITE);
        snprintf(buf,sizeof(buf),"%04d-%02d-%02d\n\n%02d:%02d",s_edit.tm_year+1900,s_edit.tm_mon+1,s_edit.tm_mday,s_edit.tm_hour,s_edit.tm_min);
        label(s_screen,33,106,186,buf,20,WHITE);
        snprintf(buf,sizeof(buf),"正在设置: %s",fields[s_clock_field]);
        label(s_screen,26,219,190,buf,16,ACCENT);
        label(s_screen,15,276,214,"上下调整  确定下一项",14,MUTED);
        label(s_screen,26,296,190,"设置分后确定保存",14,MUTED);
    } else if(s_page == PAGE_FACTORY) {
        label(s_screen,16,43,210,"原厂功能",20,WHITE);
        label(s_screen,16,98,210,"确定后重启进入\n原厂程序\n\n回到课程表需要\n连接电脑运行\n切换工具",16,WHITE);
        label(s_screen,16,272,210,"确定进入原厂功能",14,ACCENT);
        label(s_screen,25,296,195,"长按确定取消",14,MUTED);
    } else {
        label(s_screen,16,43,210,"随身课程表 1.0",20,WHITE);
        snprintf(buf,sizeof(buf),"已导入 %u 次课程\n\n长按上下: 前后一天\n长按确定: 工具菜单\n熄屏后按任意键唤醒\n\n断电后需重新校时\nUSB连接电脑可校时\n也可在菜单手动设置",(unsigned)timetable_count);
        label(s_screen,16,88,212,buf,16,WHITE);
        const char *network=s_wifi_status==1 || s_wifi_status==2 ? "正在联网校时" : s_wifi_status==3 ? "联网失败，可离线使用" : s_ssid[0] ? "已保存无线网络" : "未配置无线网络";
        label(s_screen,16,266,210,network,14,ACCENT);
        label(s_screen,28,296,190,"确定返回课程",14,MUTED);
    }
    bsp_lvgl_unlock();
}

static void set_time(int64_t epoch) {
    if (epoch<MIN_TIME || epoch>=MAX_TIME) return;
    struct timeval tv={.tv_sec=epoch,.tv_usec=0}; settimeofday(&tv,NULL);
    s_valid_time=true;
    if (s_follow_today) { s_day=timetable_local_day(epoch); update_range(true); }
    if (s_nvs_ok) { nvs_set_i64(s_nvs,"last_time",epoch); nvs_commit(s_nvs); }
    s_last_save=esp_timer_get_time();
    serial_line("COURSE TIME OK");
}

static void change_day(int direction) {
    // Permit any real date around the imported semester without signed overflow.
    if (s_day+direction>=19723 && s_day+direction<47482) s_day+=direction;
    s_follow_today=false; s_page=PAGE_DAY; update_range(true);
}

static void clock_adjust(int direction) {
    if (s_clock_field==0) {
        int y=s_edit.tm_year+1900+direction;
        s_edit.tm_year=(y<2024 ? 2099 : y>2099 ? 2024 : y)-1900;
    } else if (s_clock_field==1) s_edit.tm_mon=(s_edit.tm_mon+12+direction)%12;
    else if (s_clock_field==2) {
        int max=timetable_days_in_month(s_edit.tm_year+1900,s_edit.tm_mon+1);
        s_edit.tm_mday=(s_edit.tm_mday-1+max+direction)%max+1;
    } else if (s_clock_field==3) s_edit.tm_hour=(s_edit.tm_hour+24+direction)%24;
    else s_edit.tm_min=(s_edit.tm_min+60+direction)%60;
    int max=timetable_days_in_month(s_edit.tm_year+1900,s_edit.tm_mon+1);
    if (s_edit.tm_mday>max) s_edit.tm_mday=max;
}

static void process_key(const message_t *msg) {
    s_last_input=esp_timer_get_time();
    if (s_display_off) { s_display_off=false; bsp_display_backlight(s_brightness); return; }
    bsp_display_backlight(s_brightness);
    if (msg->event==BSP_BTN_LONG) {
        if (msg->button==BSP_BTN_OK) {
            s_page=s_page==PAGE_DAY || s_page==PAGE_DETAIL ? PAGE_MENU : PAGE_DAY; s_menu=0;
        } else if (s_page==PAGE_DAY || s_page==PAGE_DETAIL) change_day(msg->button==BSP_BTN_UP ? -1 : 1);
        return;
    }
    int direction=msg->button==BSP_BTN_UP ? -1 : 1;
    if (s_page==PAGE_MENU) {
        if (msg->button!=BSP_BTN_OK) s_menu=(s_menu+9+direction)%9;
        else switch(s_menu) {
            case 0: s_follow_today=true; s_day=timetable_local_day(time(NULL)); update_range(true); s_page=PAGE_DAY; break;
            case 1: change_day(-1); break;
            case 2: change_day(1); break;
            case 3: { time_t now=time(NULL); localtime_r(&now,&s_edit); s_clock_field=0; s_page=PAGE_CLOCK; break; }
            case 4: wifi_start(); s_page=PAGE_ABOUT; break;
            case 5: s_brightness=s_brightness==40 ? 70 : s_brightness==70 ? 100 : 40; bsp_display_backlight(s_brightness); break;
            case 6: s_page=PAGE_DAY; s_display_off=true; bsp_display_backlight(0); break;
            case 7: s_page=PAGE_ABOUT; break;
            case 8: s_page=PAGE_FACTORY; break;
        }
    } else if (s_page==PAGE_CLOCK) {
        if (msg->button!=BSP_BTN_OK) clock_adjust(direction);
        else if (++s_clock_field==5) {
            s_edit.tm_sec=0; s_edit.tm_isdst=0; s_follow_today=true;
            set_time(mktime(&s_edit)); s_page=PAGE_DAY;
        }
    } else if (s_page==PAGE_FACTORY) {
        if(msg->button==BSP_BTN_OK) {
            const esp_partition_t *factory=esp_partition_find_first(ESP_PARTITION_TYPE_APP,ESP_PARTITION_SUBTYPE_APP_FACTORY,NULL);
            if(factory && esp_ota_set_boot_partition(factory)==ESP_OK) {
                serial_line("COURSE BOOT FACTORY"); vTaskDelay(pdMS_TO_TICKS(100)); esp_restart();
            } else serial_line("COURSE ERROR factory image unavailable");
        }
    } else if (s_page==PAGE_ABOUT) { if(msg->button==BSP_BTN_OK) s_page=PAGE_DAY; }
    else if (msg->button==BSP_BTN_OK) s_page=s_page==PAGE_DETAIL ? PAGE_DAY : s_count ? PAGE_DETAIL : PAGE_DAY;
    else if (s_count) s_selected=(s_selected+s_count+direction)%s_count;
}

static void status(void) {
    char buf[440];
    snprintf(buf,sizeof(buf),"COURSE STATUS {\"version\":\"1.0\",\"epoch\":%lld,\"time_valid\":%s,\"day\":%ld,\"lessons\":%u,\"selected\":%u,\"page\":%d,\"battery\":%d,\"wifi\":%d,\"free_heap\":%u,\"largest_block\":%u,\"total_events\":%u}",
        (long long)time(NULL),s_valid_time ? "true" : "false",(long)s_day,(unsigned)s_count,(unsigned)s_selected,s_page,s_soc,s_wifi_status,
        (unsigned)esp_get_free_heap_size(),(unsigned)heap_caps_get_largest_free_block(MALLOC_CAP_8BIT),(unsigned)timetable_count);
    size_t length=strlen(buf);
    if(length && buf[length-1]=='}')
        snprintf(buf+length-1,sizeof(buf)-length+1,",\"source\":\"%.64s\"}",timetable_source_hash);
    serial_line(buf);
}

static void font_check(void) {
    const lv_font_t *fonts[]={&course_font_14,&course_font_16,&course_font_20};
    int missing=0;
#ifdef PASSPORT_DESKTOP_TEMPLATE
    for(unsigned f=0;f<3;f++) {
        const uint8_t *header=desktop_blob+desktop_u32(desktop_blob+56+f*4);
        uint32_t count=desktop_u32(header),records=desktop_u32(header+4);
        for(uint32_t i=0;i<count;i++) {
            lv_font_glyph_dsc_t desc={0};
            if(!lv_font_get_glyph_dsc(fonts[f],&desc,desktop_u32(desktop_blob+records+i*20),0) || desc.is_placeholder) ++missing;
        }
    }
    ESP_LOGI(TAG,"Desktop font coverage: %s",missing ? "FAIL" : "PASS");
#else
    for (unsigned f=0; f<3; f++) {
        for (size_t i=0; i<sizeof(course_glyphs)/sizeof(course_glyphs[0]); i++) {
            lv_font_glyph_dsc_t desc={0};
            if (!lv_font_get_glyph_dsc(fonts[f],&desc,course_glyphs[i],0) || desc.is_placeholder) {
                ++missing; ESP_LOGE(TAG,"Missing font %u U+%04lx",f,(unsigned long)course_glyphs[i]);
            }
        }
        lv_font_glyph_dsc_t negative={0};
        if (lv_font_get_glyph_dsc(fonts[f],&negative,0x9F98,0) && !negative.is_placeholder) ++missing;
    }
    ESP_LOGI(TAG,"Font coverage: %s (%u glyphs, 3 sizes)",missing ? "FAIL" : "PASS",(unsigned)(sizeof(course_glyphs)/sizeof(course_glyphs[0])));
#endif
}

static bool s_capturing;

static void capture_flush(lv_event_t *event) {
    if(!s_capturing) return;
    lv_display_t *display=lv_event_get_target(event);
    const lv_area_t *area=lv_event_get_param(event);
    lv_draw_buf_t *buffer=lv_display_get_buf_active(display);
    if(!area || !buffer || area->x1!=0 || area->x2!=239) return;
    const char *hex="0123456789abcdef";
    char line[1000];
    for(int y=area->y1;y<=area->y2;y++) {
        const uint8_t *row=buffer->data+(y-area->y1)*buffer->header.stride;
        int length=snprintf(line,sizeof(line),"COURSE PIX %d ",y);
        for(int x=0;x<480;x++) {
            uint8_t value=row[x];
            line[length++]=hex[value>>4]; line[length++]=hex[value&15];
        }
        line[length++]='\n';
        if(usb_serial_jtag_write_bytes(line,length,pdMS_TO_TICKS(1000))!=length) {
            s_capturing=false; return;
        }
    }
}

static void capture_done(lv_event_t *event) {
    (void)event;
    if(s_capturing) { s_capturing=false; serial_line("COURSE SCREEN END"); }
}

static void screenshot(void) {
    // Stream the existing 20-row display buffer before byte swapping. No frame allocation.
    if(!bsp_lvgl_lock(1000)) { serial_line("COURSE ERROR display busy"); return; }
    serial_line("COURSE SCREEN 240 320 RGB565");
    s_capturing=true;
    lv_obj_invalidate(s_screen);
    bsp_lvgl_unlock();
}

void app_main(void) {
#ifdef PASSPORT_DESKTOP_TEMPLATE
    if(!desktop_bundle_init()) { ESP_LOGE(TAG,"Invalid desktop timetable bundle"); return; }
#endif
    setenv("TZ","CST-8",1); tzset();
    s_queue=xQueueCreate(12,sizeof(message_t));
    if (!s_queue) return;
    usb_serial_jtag_driver_config_t usb=USB_SERIAL_JTAG_DRIVER_CONFIG_DEFAULT();
    usb.rx_buffer_size=1024; usb.tx_buffer_size=1024;
    ESP_ERROR_CHECK(usb_serial_jtag_driver_install(&usb));
    usb_serial_jtag_vfs_use_driver();
    if (xTaskCreate(serial_task,"course_usb",4096,NULL,3,NULL)!=pdPASS) return;

    esp_err_t nvs_error=nvs_flash_init(); // Never erase unrelated settings on failure.
    s_nvs_ok=nvs_error==ESP_OK && nvs_open("courses",NVS_READWRITE,&s_nvs)==ESP_OK;
    int64_t last=(int64_t)timetable_events[0].day*86400-28800+8*3600;
    if(s_nvs_ok) {
        int64_t saved;
        if(nvs_get_i64(s_nvs,"last_time",&saved)==ESP_OK && saved>=MIN_TIME && saved<MAX_TIME) last=saved;
        size_t length=sizeof(s_ssid); nvs_get_str(s_nvs,"ssid",s_ssid,&length);
        length=sizeof(s_password); nvs_get_str(s_nvs,"password",s_password,&length);
    }
    if (time(NULL)<MIN_TIME) {
        struct timeval tv={.tv_sec=last}; settimeofday(&tv,NULL);
    }
    // A saved timestamp is only a browsing hint; it never proves elapsed power-off time.
    s_valid_time=false; s_day=timetable_local_day(time(NULL)); update_range(true);
    bsp_i2c_init();
    if(bsp_display_init()!=ESP_OK || !bsp_lvgl_init()) { ESP_LOGE(TAG,"Display initialization failed"); return; }
    if(bsp_lvgl_lock(1000)) { font_check(); bsp_lvgl_unlock(); }
    s_battery_ok=bsp_battery_init()==ESP_OK;
    if(s_battery_ok) s_soc=bsp_battery_soc();
    if (bsp_audio_init()==ESP_OK) bsp_audio_sleep();
    ESP_ERROR_CHECK(bsp_button_init(key_callback,NULL));
    bsp_display_backlight(s_brightness);
    s_last_input=esp_timer_get_time();
    render();
    if (s_nvs_ok) wifi_start();
    ESP_LOGI(TAG,"Course app ready: %u occurrences, source %.12s",(unsigned)timetable_count,timetable_source_hash);
    int64_t last_minute=-1;
    for (;;) {
        message_t msg;
        bool dirty=false;
        if (xQueueReceive(s_queue,&msg,pdMS_TO_TICKS(200))==pdTRUE) {
            if (msg.type==MSG_KEY) { process_key(&msg); dirty=true; }
            else if (msg.type==MSG_TIME) { set_time(msg.epoch); dirty=true; }
            else if (msg.type==MSG_STATUS) status();
            else if (msg.type==MSG_SCREEN) screenshot();
            else if (msg.type==MSG_WIFI) {
                wifi_stop();
                snprintf(s_ssid,sizeof(s_ssid),"%s",msg.ssid);
                snprintf(s_password,sizeof(s_password),"%s",msg.password);
                if(s_nvs_ok) {
                    esp_err_t a=nvs_set_str(s_nvs,"ssid",s_ssid);
                    esp_err_t b=nvs_set_str(s_nvs,"password",s_password);
                    esp_err_t c=nvs_commit(s_nvs);
                    serial_line(a==ESP_OK && b==ESP_OK && c==ESP_OK ? "COURSE WIFI SAVED" : "COURSE WIFI SAVE FAILED");
                    wifi_start();
                } else serial_line("COURSE ERROR storage unavailable");
                dirty=true;
            }
        }
        int64_t now_us=esp_timer_get_time(); time_t now=time(NULL);
        if(now/60!=last_minute) {
            last_minute=now/60;
            if(s_valid_time && s_follow_today && s_day!=timetable_local_day(now)) {
                s_day=timetable_local_day(now); update_range(true);
            }
            dirty=true;
        }
        if(now_us-s_last_battery>60000000) {
            s_last_battery=now_us; if(s_battery_ok) s_soc=bsp_battery_soc(); dirty=true;
        }
        if(s_valid_time && s_nvs_ok && now_us-s_last_save>900000000) {
            nvs_set_i64(s_nvs,"last_time",now); nvs_commit(s_nvs); s_last_save=now_us;
        }
        if(s_wifi_running && (s_wifi_status==3 || now_us-s_wifi_started_at>25000000)) {
            bool failed=s_wifi_status!=2; wifi_stop(); if(failed) s_wifi_status=3; dirty=true;
        }
        if(now_us-s_last_input>45000000 && !s_display_off) { s_display_off=true; bsp_display_backlight(0); }
        else if(now_us-s_last_input>20000000 && !s_display_off) bsp_display_backlight(15);
        if(dirty && !s_display_off) render();
    }
}
