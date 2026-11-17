cmake_minimum_required(VERSION 3.15)
project(PackageTest OBJCXX)

find_package(sparkle CONFIG REQUIRED)

add_executable(example example.mm)
# Foundation: the Objective-C runtime that [SUUpdater class] calls into.
target_link_libraries(example sparkle::sparkle "-framework Foundation")
