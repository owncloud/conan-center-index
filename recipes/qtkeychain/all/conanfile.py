from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run, check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, mkdir, replace_in_file, rmdir
from conan.tools.gnu import PkgConfigDeps
import glob
import os


required_conan_version = ">=2.0.9"
class PackageConan(ConanFile):
    name = "qtkeychain"
    description = "Platform-independent Qt API for storing passwords securely."
    topics = ("qt", "keychain")
    license = "BSD-3-Clause"
    homepage = "https://github.com/frankosterfeld/qtkeychain"
    url = "https://github.com/conan-io/conan-center-index"

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_translations": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
        "with_translations": False,
    }

    implements = ["auto_shared_fpic"]

    def layout(self):
        cmake_layout(self, src_folder="src")

    def validate(self):
        check_min_cppstd(self, 17)
        qt_options = self.dependencies["qt"].options
        if self.settings.os in ("Linux", "FreeBSD") and not qt_options.with_dbus:
            raise ConanInvalidConfiguration(f'{self.ref} requires -o="qt/*:with_dbus=True" in {self.settings.os}')
        if self.options.with_translations:
            if not qt_options.qttools:
                raise ConanInvalidConfiguration(f'{self.ref} with_translations=True requires -o="qt/*:qttools=True"')
            if not can_run(self):
                # lrelease comes from the host Qt package
                raise ConanInvalidConfiguration(f'{self.ref} with_translations=True is not supported when cross-building')

    def requirements(self):
        self.requires("qt/[>=6.7 <7]", transitive_headers=True, transitive_libs=True)
        if self.settings.os == "Linux":
            self.requires("libsecret/0.21.7")

    def build_requirements(self):
        # CMakeLists.txt finds libsecret with pkg_check_modules.
        if self.settings.os == "Linux" and not self.conf.get("tools.gnu:pkg_config", check_type=str):
            self.tool_requires("pkgconf/[>=2.2 <3]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        replace_in_file(self, os.path.join(self.source_folder, "CMakeLists.txt"),
                        "SET(CMAKE_CXX_STANDARD 11)", "")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["BUILD_WITH_QT6"] = True
        # Settings this to True would need LinguistTools, which requires qttools, gui and widgets
        # qttools is not built by default in qt package, so we would need to add a check in validate()
        tc.cache_variables["BUILD_TRANSLATIONS"] = False
        tc.generate()

        deps = CMakeDeps(self)
        # CMakeLists expects us to have created Qt6Core specific variables, but we don't have them
        # So make the whole target generate them, this overlinks uneeded stuff though
        deps.set_property("qt", "cmake_additional_variables_prefixes", ["Qt6Core"])
        deps.generate()
        if self.settings.os == "Linux":
            # libsecret-1.pc and its Requires for pkg_check_modules, from the Conan packages. They
            # come first on PKG_CONFIG_PATH; pkg-config's system path still applies after them.
            PkgConfigDeps(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        self._build_translations()

    def _build_translations(self):
        # BUILD_TRANSLATIONS stays off: it needs Qt's LinguistTools CMake package and also runs
        # lupdate on the sources. Calling lrelease from the Qt package is enough to get the .qm files.
        if not self.options.with_translations:
            return
        lrelease = os.path.join(self.dependencies["qt"].package_folder, "bin", "lrelease")
        qm_folder = os.path.join(self.build_folder, "translations")
        mkdir(self, qm_folder)
        for ts in sorted(glob.glob(os.path.join(self.source_folder, "translations", "*.ts"))):
            qm = os.path.join(qm_folder, os.path.splitext(os.path.basename(ts))[0] + ".qm")
            self.run(f'"{lrelease}" "{ts}" -qm "{qm}"', env="conanrun")

    def package(self):
        copy(self, "COPYING", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        copy(self, "*.qm", os.path.join(self.build_folder, "translations"),
             os.path.join(self.package_folder, "res", "translations"))

    def package_info(self):
        self.cpp_info.libs = ["qt6keychain"]
        if self.options.with_translations:
            # qtkeychain_<lang>.qm
            self.cpp_info.resdirs = ["res"]
        self.cpp_info.set_property("cmake_file_name", "Qt6Keychain")
        self.cpp_info.set_property("cmake_target_name", "Qt6Keychain::Qt6Keychain")
