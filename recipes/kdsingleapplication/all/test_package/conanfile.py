from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.build import can_run
import os

class KDSingleApplicationTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualBuildEnv", "VirtualRunEnv"
    apply_env = False

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            # The executable is typically in a subfolder matching the build_type (e.g., Release, Debug)
            # For single-config generators like Ninja or Makefile, it's directly in build_folder/bin or similar.
            # For multi-config like MSVC, it's in build_folder/Release/test_package.exe
            # CMake.build_folder is the root build directory.
            # The layout places the executable in self.cpp.build.bindirs[0] after build.
            # A simpler way that often works for default CMake layouts:
            bin_path = os.path.join(self.cpp.build.bindirs[0], "test_package")
            self.run(bin_path, env="conanrun")
