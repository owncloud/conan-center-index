cmake_minimum_required(VERSION 3.15)
project(test_package LANGUAGES CXX)

find_package(PkgConfig REQUIRED)
pkg_check_modules(Cgl REQUIRED IMPORTED_TARGET cgl)

add_executable(${PROJECT_NAME} test_package.cpp)
target_link_libraries(${PROJECT_NAME} PRIVATE PkgConfig::Cgl)
