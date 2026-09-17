cmake_minimum_required(VERSION 3.16)
include($ENV{IDF_PATH}/tools/cmake/project.cmake)

project(FoloToy-AI-Passport)

# ESP-IDF otherwise flashes its application over the original factory program.
# Point every generated flashing descriptor to our separate OTA slot instead.
partition_table_get_partition_info(course_offset "--partition-name courses" "offset")
if(NOT course_offset STREQUAL "0x500000")
    message(FATAL_ERROR "Expected courses OTA partition at 0x500000")
endif()
foreach(flash_target flash app-flash)
    foreach(prop FLASH_FILE FLASH_ENTRY IMAGES)
        get_property(entries TARGET ${flash_target} PROPERTY ${prop})
        set(updated "")
        foreach(entry IN LISTS entries)
            string(REPLACE "0x10000" "${course_offset}" entry "${entry}")
            list(APPEND updated "${entry}")
        endforeach()
        set_property(TARGET ${flash_target} PROPERTY ${prop} "${updated}")
    endforeach()
endforeach()
