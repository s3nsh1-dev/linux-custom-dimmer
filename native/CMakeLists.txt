cmake_minimum_required(VERSION 3.22)
project(dimmer_bridge VERSION 0.1.0 LANGUAGES CXX)
set(DIMMER_HEADER_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/../.local/sysroot" CACHE PATH
    "Ubuntu development packages extracted without installing system packages")
# This bridge needs public headers and three existing runtime libraries only.
# Avoid the distro Qt CMake package, whose broad dependency checks require
# unrelated OpenGL/Vulkan/qmake development packages. No Qt runtime is copied.
set(QT_HEADERS "${DIMMER_HEADER_ROOT}/usr/include/${CMAKE_LIBRARY_ARCHITECTURE}/qt6")
if(NOT EXISTS "${QT_HEADERS}/QtCore/qglobal.h")
    message(FATAL_ERROR "Matching Qt headers missing. Run scripts/setup-dev.")
endif()
find_library(QT_CORE NAMES libQt6Core.so.6 REQUIRED
    PATHS "/usr/lib/${CMAKE_LIBRARY_ARCHITECTURE}" NO_DEFAULT_PATH)
find_library(QT_GUI NAMES libQt6Gui.so.6 REQUIRED
    PATHS "/usr/lib/${CMAKE_LIBRARY_ARCHITECTURE}" NO_DEFAULT_PATH)
find_library(LAYER_SHELL NAMES libLayerShellQtInterface.so.6 REQUIRED
    PATHS "/usr/lib/${CMAKE_LIBRARY_ARCHITECTURE}" NO_DEFAULT_PATH)
add_library(dimmer_layer_shell SHARED layer_shell_bridge.cpp)
target_compile_features(dimmer_layer_shell PRIVATE cxx_std_17)
target_compile_options(dimmer_layer_shell PRIVATE -Wall -Wextra -Wpedantic -Werror)
target_include_directories(dimmer_layer_shell SYSTEM PRIVATE
    "${QT_HEADERS}" "${QT_HEADERS}/QtCore" "${QT_HEADERS}/QtGui"
    "${DIMMER_HEADER_ROOT}/usr/include")
target_link_libraries(dimmer_layer_shell PRIVATE "${QT_CORE}" "${QT_GUI}" "${LAYER_SHELL}")
set_target_properties(dimmer_layer_shell PROPERTIES CXX_VISIBILITY_PRESET hidden)
