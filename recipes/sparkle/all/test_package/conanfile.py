import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.build import can_run


class sparkleTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build_requirements(self):
        self.tool_requires("cmake/[>=3.21 <4]")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def layout(self):
        cmake_layout(self)

    def _can_run(self):
        # can_run() compares arch as a whole string, so a universal arch=armv8|x86_64 would never
        # run, although its fat binary runs on either build arch. An explicit conf still decides.
        if self.conf.get("tools.build.cross_building:can_run", check_type=bool) is not None or can_run(self):
            return can_run(self)
        return (self.settings_build.os == self.settings.os
                and str(self.settings_build.arch) in str(self.settings.arch).split("|"))

    def test(self):
        if self._can_run():
            cmd = os.path.join(self.cpp.build.bindir, "example")
            self.run(cmd, env="conanrun")
