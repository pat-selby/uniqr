cmake_minimum_required(VERSION 3.24)

# The C++ version of UniQR. See README.md in this folder.
project(uniqr_cpp VERSION 0.2.9 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)
if(NOT CMAKE_BUILD_TYPE AND NOT CMAKE_CONFIGURATION_TYPES)
  set(CMAKE_BUILD_TYPE Release CACHE STRING "" FORCE)
endif()

if(MSVC)
  # One self-contained exe: link the C++ runtime statically, so a friend's PC
  # needs no Visual C++ redistributable.
  set(CMAKE_MSVC_RUNTIME_LIBRARY "MultiThreaded$<$<CONFIG:Debug>:Debug>")
endif()

option(UNIQR_BUILD_TESTS "Build the unit tests" ON)
option(UNIQR_BUILD_APP "Build the Windows desktop app (Windows only)" ON)

include(FetchContent)
set(FETCHCONTENT_QUIET ON)

# zxing-cpp: the barcode reader. The same version the Python UniQR uses, so the
# two can be compared like for like. Writers are on so the tests can draw codes.
set(ZXING_READERS ON CACHE BOOL "" FORCE)
set(ZXING_WRITERS NEW CACHE STRING "" FORCE)
set(ZXING_C_API OFF CACHE BOOL "" FORCE)
set(ZXING_EXAMPLES OFF CACHE BOOL "" FORCE)
set(ZXING_BLACKBOX_TESTS OFF CACHE BOOL "" FORCE)
set(ZXING_UNIT_TESTS OFF CACHE BOOL "" FORCE)
set(ZXING_PYTHON_MODULE OFF CACHE BOOL "" FORCE)
set(ZXING_DEPENDENCIES LOCAL CACHE STRING "" FORCE)
set(BUILD_SHARED_LIBS OFF CACHE BOOL "" FORCE)
FetchContent_Declare(
  zxing
  GIT_REPOSITORY https://github.com/zxing-cpp/zxing-cpp.git
  GIT_TAG v3.1.1
  GIT_SHALLOW TRUE
)

# stb: single-file PNG and JPEG reading and PNG writing. Pinned to a commit.
FetchContent_Declare(
  stb
  GIT_REPOSITORY https://github.com/nothings/stb.git
  GIT_TAG 2c980bb59875b0d32144a71867fbdebb2f77cd20
)
FetchContent_MakeAvailable(zxing stb)

# Our own code gets strict warnings; the libraries keep their own settings.
function(uniqr_warnings target)
  if(MSVC)
    target_compile_options(${target} PRIVATE /W4 /permissive- /utf-8 /wd4244 /wd4267)
  else()
    target_compile_options(${target} PRIVATE -Wall -Wextra -Wpedantic)
  endif()
endfunction()

configure_file(src/core/version.hpp.in ${CMAKE_CURRENT_BINARY_DIR}/generated/version.hpp @ONLY)

# -- the core: scanning and the safety rules, no OS code ----------------------
add_library(uniqr_core STATIC
  src/core/image.cpp
  src/core/image_io.cpp
  src/core/scanner.cpp
  src/core/link.cpp
  src/core/hotkeys.cpp
  src/core/report.cpp
  src/core/removal.cpp
)
target_include_directories(uniqr_core PUBLIC src/core ${CMAKE_CURRENT_BINARY_DIR}/generated)
target_include_directories(uniqr_core SYSTEM PRIVATE ${stb_SOURCE_DIR})
target_link_libraries(uniqr_core PUBLIC ZXing::ZXing)
uniqr_warnings(uniqr_core)
find_package(Threads REQUIRED)
target_link_libraries(uniqr_core PUBLIC Threads::Threads)
# stb's implementation lives in image_io.cpp only; its own code is not ours to warn about.
if(MSVC)
  set_source_files_properties(src/core/image_io.cpp PROPERTIES COMPILE_OPTIONS "/W0")
else()
  set_source_files_properties(src/core/image_io.cpp PROPERTIES COMPILE_OPTIONS "-w")
endif()

# -- uniqr-scan: the command-line scanner ----------------------------------------
add_executable(uniqr-scan src/cli/main.cpp)
target_link_libraries(uniqr-scan PRIVATE uniqr_core)
uniqr_warnings(uniqr-scan)
if(WIN32)
  target_link_libraries(uniqr-scan PRIVATE shell32)
endif()

# -- the Windows desktop app ------------------------------------------------------
if(WIN32 AND UNIQR_BUILD_APP)
  add_subdirectory(src/win)
endif()

# -- tests ---------------------------------------------------------------------------
if(UNIQR_BUILD_TESTS)
  enable_testing()
  add_subdirectory(tests)
endif()
