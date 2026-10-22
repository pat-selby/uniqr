FetchContent_Declare(
  doctest
  GIT_REPOSITORY https://github.com/doctest/doctest.git
  GIT_TAG v2.4.12
  GIT_SHALLOW TRUE
)
FetchContent_MakeAvailable(doctest)

add_executable(uniqr_tests
  main.cpp
  test_link.cpp
  test_hotkeys.cpp
  test_report.cpp
  test_removal.cpp
  test_image.cpp
  test_scanner.cpp
  test_fixtures.cpp
  draw.cpp
)
target_link_libraries(uniqr_tests PRIVATE uniqr_core doctest::doctest)
uniqr_warnings(uniqr_tests)
# The real photos and the poster code live in the Python project's folders.
get_filename_component(UNIQR_REPO_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/../.." ABSOLUTE)
target_compile_definitions(uniqr_tests PRIVATE UNIQR_REPO_ROOT="${UNIQR_REPO_ROOT}")
add_test(NAME uniqr_tests COMMAND uniqr_tests)
