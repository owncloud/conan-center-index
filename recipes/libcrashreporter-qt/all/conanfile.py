from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, replace_in_file, rmdir
import os


required_conan_version = ">=2.0.9"
class CrashReporterQTConan(ConanFile):
    name = "libcrashreporter-qt"
    description = "libcrashreporter-qt is supposed to provide an easy integration of Google Breakpad crash reporting into a Qt application"
    topics = ("qt")
    homepage = "https://github.com/owncloud/libcrashreporter-qt"
    url = "https://github.com/conan-io/conan-center-index"

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
    }

    implements = ["auto_shared_fpic"]

    def layout(self):
        cmake_layout(self)

    def validate(self):
        check_min_cppstd(self, 17)

    def requirements(self):
        self.requires("qt/[>=6.7 <7]", transitive_headers=True, transitive_libs=True)
        self.requires("breakpad/cci.20210521")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        #replace_in_file(self, os.path.join(self.source_folder, "client", "CMakeLists.txt"), "CXX_STANDARD 14", "")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["LibreGraphAPI"]
        self.cpp_info.set_property("cmake_file_name", "LibreGraphAPI")
        self.cpp_info.set_property("cmake_target_name", "OpenAPI::LibreGraphAPI")
