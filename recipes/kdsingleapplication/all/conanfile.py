from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, rmdir, rm
from conan.tools.scm import Version
import os

required_conan_version = ">=2.0.9"


class KDSingleApplicationConan(ConanFile):
    name = "kdsingleapplication"
    description = "A library for single-instance application control, allowing applications to detect and communicate with existing instances of themselves."
    license = "MIT"
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://github.com/KDAB/KDSingleApplication"
    topics = ("qt", "single-instance", "application", "ipc", "kdab")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "qt_major_version": [None, "5", "6"],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "qt_major_version": None,
    }

    @property
    def _qt_version_suffix(self):
        # KDSingleApplication_LIBRARY_QTID from CMakeLists.txt
        # "" for Qt5, "-qt6" for Qt6
        qt_major = self._get_effective_qt_major_version()
        return "-qt6" if qt_major == "6" else ""

    def export_sources(self):
        # This recipe does not export any local sources or patches.
        # Sources are fetched from conandata.yml.
        pass

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        # C++ library, cppstd is validated in validate().
        # libcxx is not directly managed by this library's build options.
        self.settings.rm_safe("compiler.libcxx")

    def layout(self):
        # Source files from the tarball are in the root after strip_root=True.
        # We specify src_folder="src" to align with the common Conan practice of having a dedicated 'src' subdirectory
        # within the source folder for clarity, even if the actual build scripts are in the root of self.source_folder.
        # The `get()` command will place sources in `self.source_folder`.
        # CMake will be configured from `self.source_folder`.
        cmake_layout(self, src_folder="src")


    def _get_effective_qt_major_version(self):
        if self.options.qt_major_version:
            return str(self.options.qt_major_version)
        # Try to get from existing 'qt' dependency if available (e.g., from profile)
        qt_dep = self.dependencies.host.get("qt")
        if qt_dep:
            return Version(qt_dep.ref.version).major
        # Default to 5 if not specified and qt not found (should ideally be caught in validate if qt is missing)
        self.output.warning("qt_major_version not set and Qt dependency not found. Defaulting to Qt 5. This might lead to issues if Qt is not properly configured.")
        return "5"

    def requirements(self):
        effective_qt_major = self._get_effective_qt_major_version()
        
        # Use existing Qt dependency if present and version matches, otherwise require a default for that major.
        qt_dep = self.dependencies.host.get("qt")
        if qt_dep:
            if Version(qt_dep.ref.version).major != effective_qt_major:
                raise ConanInvalidConfiguration(
                    f"Detected Qt version {qt_dep.ref.version} conflicts with effective Qt major version {effective_qt_major} (derived from qt_major_version option or default)."
                )
            self.requires(str(qt_dep.ref), transitive_headers=True, transitive_libs=True)
        else:
            if effective_qt_major == "6":
                self.requires("qt/6.5.3", transitive_headers=True, transitive_libs=True) # A common recent Qt6
            elif effective_qt_major == "5":
                self.requires("qt/5.15.10", transitive_headers=True, transitive_libs=True) # A common recent Qt5
            else:
                raise ConanInvalidConfiguration(f"Unsupported effective Qt major version: {effective_qt_major}")


    def validate(self):
        check_min_cppstd(self, "14")
        if not self.dependencies.host.get("qt"):
            raise ConanInvalidConfiguration(f"{self.ref} requires Qt, but it's not found in dependencies.")

        # Further check consistency if qt_major_version option was explicitly set
        if self.options.qt_major_version:
            qt_dep_major = Version(self.dependencies.host["qt"].ref.version).major
            if str(self.options.qt_major_version) != qt_dep_major:
                raise ConanInvalidConfiguration(
                    f"Option qt_major_version='{self.options.qt_major_version}' conflicts with detected Qt version {qt_dep_major} from dependencies."
                )

    def build_requirements(self):
        # KDSingleApplication uses ECM. Version from upstream's FindECM.cmake is 1.7.0.
        # Using a more recent, commonly available ECM version.
        self.tool_requires("extra-cmake-modules/5.110.0")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["KDSingleApplication_STATIC"] = not self.options.shared
        
        effective_qt_major = self._get_effective_qt_major_version()
        tc.variables["KDSingleApplication_QT6"] = (effective_qt_major == "6")
        
        tc.variables["KDSingleApplication_TESTS"] = False
        tc.variables["KDSingleApplication_EXAMPLES"] = False
        # KDSingleApplication_DEVELOPER_MODE is OFF by default in CMakeLists.txt
        tc.generate()

        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        cmake = CMake(self)
        # Configure from the root of the source folder where CMakeLists.txt is located
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE.txt", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()

        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "share"))
        rm(self, "*.pdb", os.path.join(self.package_folder, "bin"), recursive=True, ignore_case=True)
        rm(self, "*.pdb", os.path.join(self.package_folder, "lib"), recursive=True, ignore_case=True)

    def package_info(self):
        self.cpp_info.libs = [f"KDSingleApplication{self._qt_version_suffix}"]
        
        self.cpp_info.set_property("cmake_file_name", "KDSingleApplication")
        # Upstream provides KDSingleApplication::KDSingleApplication target
        # The library name itself doesn't change with Qt6, but include path and .pri file do.
        self.cpp_info.set_property("cmake_target_name", "KDSingleApplication::KDSingleApplication")

        self.cpp_info.requires = ["qt::Core", "qt::Network", "qt::Widgets"]

        # KDSINGLEAPPLICATION_INCLUDEDIR = ${INSTALL_INCLUDE_DIR}/kdsingleapplication${KDSingleApplication_LIBRARY_QTID}
        # KDSingleApplication_LIBRARY_QTID is "" for Qt5 and "-qt6" for Qt6.
        # Conan package structure is <prefix>/include/kdsingleapplication[-qt6]
        self.cpp_info.includedirs = [os.path.join("include", f"kdsingleapplication{self._qt_version_suffix}")]

        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs.extend(["m", "pthread", "dl"])
        
        # For find_package in module mode (less common for this library)
        self.cpp_info.filenames["cmake_find_package"] = "KDSingleApplication"
        self.cpp_info.filenames["cmake_find_package_multi"] = "KDSingleApplication"
        self.cpp_info.names["cmake_find_package"] = "KDSingleApplication"
        self.cpp_info.names["cmake_find_package_multi"] = "KDSingleApplication"
        # self.cpp_info.components["libkdsingleapplication"].names["cmake_find_package"] = f"KDSingleApplication{self._qt_version_suffix.upper()}"
        # self.cpp_info.components["libkdsingleapplication"].names["cmake_find_package_multi"] = f"KDSingleApplication{self._qt_version_suffix.upper()}"
        # self.cpp_info.components["libkdsingleapplication"].set_property("cmake_target_name", f"KDSingleApplication::KDSingleApplication{self._qt_version_suffix.upper()}")
        # self.cpp_info.components["libkdsingleapplication"].libs = [f"KDSingleApplication{self._qt_version_suffix}"]
        # self.cpp_info.components["libkdsingleapplication"].requires = ["qt::Core", "qt::Network", "qt::Widgets"]
