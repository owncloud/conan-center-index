cmake_minimum_required(VERSION 3.15)
project(test_package LANGUAGES C)

find_package(NEON_2_SSE REQUIRED CONFIG)

add_executable(${PROJECT_NAME} test_package.c)
target_link_libraries(${PROJECT_NAME} PRIVATE NEON_2_SSE::NEON_2_SSE)
