cmake_minimum_required(VERSION 3.15)
project(cmake_wrapper)

include(conanbuildinfo.cmake)
conan_basic_setup(KEEP_RPATHS)

add_subdirectory("source_subfolder")
