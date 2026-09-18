if(PASSPORT_DESKTOP_TEMPLATE)
    set(course_sources "desktop_bundle.c" "desktop_font.c" "${CMAKE_BINARY_DIR}/desktop_blob.c")
elseif(NOT EXISTS "${CMAKE_CURRENT_LIST_DIR}/timetable_data.c")
    message(FATAL_ERROR "Run python tools/prepare_timetable.py examples/timetable.ics before building")
else()
    set(course_sources "timetable_data.c" "../assets/fonts/course_font_14.c"
        "../assets/fonts/course_font_16.c" "../assets/fonts/course_font_20.c")
endif()

idf_component_register(
    SRCS "course_app.c"
         "timetable.c"
         ${course_sources}
         "demo_navigation.c"
         "ui_pixel.c"
         "ui_pixel_math.c"
         "demo_display.c"
         "demo_button.c"
         "demo_audio.c"
         "demo_battery.c"
         "demo_radio.c"
         "demo_wifi.c"
         "demo_ble.c"
         "demo_low_power.c"
    INCLUDE_DIRS "."
    REQUIRES bsp bt esp_event esp_hw_support esp_netif esp_timer esp_wifi nvs_flash json esp_driver_usb_serial_jtag app_update
)
if(PASSPORT_DESKTOP_TEMPLATE)
    target_compile_definitions(${COMPONENT_LIB} PUBLIC PASSPORT_DESKTOP_TEMPLATE=1)
endif()
