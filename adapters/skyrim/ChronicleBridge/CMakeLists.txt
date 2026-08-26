# ChronicleBridge -- the Chronicle project's SKSE plugin (adapters/skyrim/README.md's
# "only place in the repo allowed to know Skyrim exists"). Design: docs/design/
# chronicle-bridge-spatial-streamer.md (slice 1), docs/design/
# chronicle-bridge-death-extraction.md (slice 2). Built on Windows (native, no
# Proton/Wine) -- see README.md in this directory for the build setup.
#
# Slice 1: sample every actor currently outdoors in WhiterunWorld at ~1Hz and
# push their positions out to a Linux-side listener.
# Slice 2: sink RE::TESDeathEvent and push a discrete death event to the same
# listener. No hydration, no save/reload sync yet -- still real future work.

cmake_minimum_required(VERSION 3.21)

project(ChronicleBridge VERSION 0.0.1 LANGUAGES CXX)

# Same "drop the built DLL straight into a mod manager's mods folder" convenience
# the upstream CommonLibSSE-NG templates use -- set SKYRIM_MODS_FOLDER (MO2/Vortex
# mods dir) or SKYRIM_FOLDER (Data dir directly) as an environment variable.
if(DEFINED ENV{SKYRIM_FOLDER} AND IS_DIRECTORY "$ENV{SKYRIM_FOLDER}/Data")
    set(OUTPUT_FOLDER "$ENV{SKYRIM_FOLDER}/Data")
endif()

if(DEFINED ENV{SKYRIM_MODS_FOLDER} AND IS_DIRECTORY "$ENV{SKYRIM_MODS_FOLDER}")
    set(OUTPUT_FOLDER "$ENV{SKYRIM_MODS_FOLDER}/${PROJECT_NAME}")
endif()

find_package(CommonLibSSE CONFIG REQUIRED)
find_package(httplib CONFIG REQUIRED)

add_commonlibsse_plugin(${PROJECT_NAME} SOURCES
    src/plugin.cpp
    src/SpatialStreamer.cpp
    src/IdentityMap.cpp
    src/OutboundClient.cpp
    src/Config.cpp
    src/DeathEventSink.cpp
)
target_compile_features(${PROJECT_NAME} PRIVATE cxx_std_23)
target_precompile_headers(${PROJECT_NAME} PRIVATE src/PCH.h)
target_link_libraries(${PROJECT_NAME} PRIVATE httplib::httplib)

if(DEFINED OUTPUT_FOLDER)
    set(DLL_FOLDER "${OUTPUT_FOLDER}/SKSE/Plugins")
    message(STATUS "ChronicleBridge output folder: ${DLL_FOLDER}")

    add_custom_command(
        TARGET "${PROJECT_NAME}"
        POST_BUILD
        COMMAND "${CMAKE_COMMAND}" -E make_directory "${DLL_FOLDER}"
        COMMAND "${CMAKE_COMMAND}" -E copy_if_different "$<TARGET_FILE:${PROJECT_NAME}>" "${DLL_FOLDER}/$<TARGET_FILE_NAME:${PROJECT_NAME}>"
        VERBATIM
    )

    if(CMAKE_BUILD_TYPE STREQUAL "Debug")
        add_custom_command(
            TARGET "${PROJECT_NAME}"
            POST_BUILD
            COMMAND "${CMAKE_COMMAND}" -E copy_if_different "$<TARGET_PDB_FILE:${PROJECT_NAME}>" "${DLL_FOLDER}/$<TARGET_PDB_FILE_NAME:${PROJECT_NAME}>"
            VERBATIM
        )
    endif()
endif()
