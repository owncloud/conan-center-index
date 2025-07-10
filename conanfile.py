from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, replace_in_file, rmdir
from conan.tools.scm import Git
import os

class LibCrashReporterQtConan(ConanFile):
    name = "libcrashreporter-qt"
    version = "0.0.1"
    license = "LGPL-2.1-only"  # DrKonqi integration is GPL
    author = "ownCloud GmbH (dev@owncloud.com)"
    url = "https://github.com/owncloud/libcrashreporter-qt"
    description = "Library to provide an easy integration of Google Breakpad crash reporting into a Qt application"
    topics = ("crash-reporting", "qt", "breakpad")
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    # The breakpad commit used by libcrashreporter-qt v0.0.1
    breakpad_commit = "9735a19a5560636399a1392f59bd6ad93c008903"
    breakpad_url_template = "https://github.com/google/breakpad/archive/{commit}.tar.gz"

    # SHA256 values
    libcrashreporter_sha256 = "b2e9a40a2a1bb5af8179597193967717262f0c63618f01cb937418c305807795"
    breakpad_sha256 = "db65c99592c16401d70164f57b30fbe0ce6a4ab0200f798a570750f097c47766"


    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self)

    def requirements(self):
        self.requires("qt/5.15.10")
        self.tool_requires("cmake/[>=3.16]")

    def source(self):
        get(self,
            url=f"https://github.com/owncloud/libcrashreporter-qt/archive/refs/tags/v{self.version}.tar.gz",
            sha256=self.libcrashreporter_sha256,
            strip_root=True)

        breakpad_src_folder = os.path.join(self.source_folder, "3rdparty", "breakpad_src_temp")
        get(self,
            url=self.breakpad_url_template.format(commit=self.breakpad_commit),
            sha256=self.breakpad_sha256,
            destination=breakpad_src_folder,
            strip_root=True)

        breakpad_target_dir = os.path.join(self.source_folder, "3rdparty", "breakpad")
        if os.path.exists(breakpad_target_dir):
            rmdir(self, breakpad_target_dir)

        os.rename(breakpad_src_folder, breakpad_target_dir)

        exception_handler_cc = os.path.join(self.source_folder, "3rdparty", "breakpad", "src", "client", "linux", "handler", "exception_handler.cc")
        if os.path.exists(exception_handler_cc):
            replace_in_file(self, exception_handler_cc, "std::is_pod<CrashContext>", "std::is_trivial<CrashContext>", output=self.output)
            replace_in_file(self, exception_handler_cc, "std::is_pod<SignalContext>", "std::is_trivial<SignalContext>", output=self.output)
            replace_in_file(self, exception_handler_cc, "is_pod<google_breakpad::ExceptionHandler::CrashContext>", "is_trivial<google_breakpad::ExceptionHandler::CrashContext>", output=self.output)
            replace_in_file(self, exception_handler_cc, "is_pod<google_breakpad::ExceptionHandler::SignalContext>", "is_trivial<google_breakpad::ExceptionHandler::SignalContext>", output=self.output)

        microdump_writer_cc = os.path.join(self.source_folder, "3rdparty", "breakpad", "src", "client", "linux", "microdump_writer", "microdump_writer.cc")
        if self.settings.os == "Linux" and os.path.exists(microdump_writer_cc):
             replace_in_file(self, microdump_writer_cc,
                             '#include "client/linux/microdump_writer/microdump_writer.h"',
                             '#include <sys/types.h>\n#include "client/linux/microdump_writer/microdump_writer.h"',
                             output=self.output)

        stackwalker_x86_cc = os.path.join(self.source_folder, "3rdparty", "breakpad", "src", "processor", "stackwalker_x86.cc")
        if os.path.exists(stackwalker_x86_cc):
            replace_in_file(self, stackwalker_x86_cc,
                            '#include "processor/stackwalker_x86.h"',
                            '#include <limits.h>\n#include "processor/stackwalker_x86.h"',
                            output=self.output)

        breakpad_git_dir = os.path.join(self.source_folder, "3rdparty", "breakpad", ".git")
        if os.path.exists(breakpad_git_dir):
            rmdir(self, breakpad_git_dir)

    def generate(self):
        tc = CMakeToolchain(self)
        if self.options.shared:
            tc.variables["CRASHR REPORTER_STATIC_LIB"] = "OFF"
        else:
            tc.variables["CRASHR REPORTER_STATIC_LIB"] = "ON"
        tc.generate()
        # For CMakeDeps (implicitly handled by CMakeToolchain for requires)
        # deps = CMakeDeps(self)
        # deps.generate()


    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE.LGPL2.1", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "share"))


    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "libcrashreporter-qt")
        self.cpp_info.set_property("cmake_target_name", "CrashReporter::crashreporter")

        lib_name = "crashreporter"
        self.cpp_info.libs = [lib_name]

        if not self.options.shared:
            self.cpp_info.defines = ["CRASHR REPORTER_STATIC_DEFINE"]

        if self.settings.os == "Linux":
            self.cpp_info.system_libs.extend(["pthread"])

        self.cpp_info.requires = ["qt::qtCore", "qt::qtGui", "qt::qtWidgets"]

        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]

        self.cpp_info.filenames["cmake_find_package"] = "libcrashreporter-qt"
        self.cpp_info.filenames["cmake_find_package_multi"] = "libcrashreporter-qt"
        self.cpp_info.names["cmake_find_package"] = "CrashReporter"
        self.cpp_info.names["cmake_find_package_multi"] = "CrashReporter"

        # Component setup
        component = self.cpp_info.components["libcrashreporter"]
        component.names["cmake_find_package"] = "crashreporter"
        component.names["cmake_find_package_multi"] = "crashreporter"
        component.set_property("cmake_target_name", "CrashReporter::crashreporter")
        component.libs = [lib_name]
        component.requires = ["qt::qtCore", "qt::qtGui", "qt::qtWidgets"]
        if self.settings.os == "Linux":
            component.system_libs.extend(["pthread"])
        if not self.options.shared:
            component.defines = ["CRASHR REPORTER_STATIC_DEFINE"]
        component.includedirs = ["include"] # Redundant if global self.cpp_info.includedirs is set and component uses it
        component.libdirs = ["lib"]       # Redundant
        component.bindirs = ["bin"]       # Redundant
