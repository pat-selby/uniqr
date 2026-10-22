# uniqr-cpp.exe: the Windows desktop app.
configure_file(app.rc.in ${CMAKE_CURRENT_BINARY_DIR}/app.rc @ONLY)

add_executable(uniqr-cpp WIN32
  main.cpp
  app.cpp
  card.cpp
  card_paint.cpp
  picker.cpp
  capture.cpp
  system.cpp
  log.cpp
  win.cpp
  ${CMAKE_CURRENT_BINARY_DIR}/app.rc
)
target_include_directories(uniqr-cpp PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})
target_link_libraries(uniqr-cpp PRIVATE uniqr_core user32 gdi32 shell32 advapi32 dwmapi shcore)
target_compile_definitions(uniqr-cpp PRIVATE UNICODE _UNICODE)
uniqr_warnings(uniqr-cpp)
if(MSVC)
  # The manifest comes from app.rc, not from the linker's default one.
  target_link_options(uniqr-cpp PRIVATE /MANIFEST:NO)
endif()
