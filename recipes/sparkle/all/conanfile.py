from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.apple import to_apple_arch
from conan.tools.files import get, copy
import glob
import os
import shlex
import shutil

class sparkleRecipe(ConanFile):
    name = "sparkle"
    # Sparkle.framework is always a dynamic framework.
    package_type = "shared-library"

    # Optional metadata
    license = "MIT"
    url = "https://github.com/sparkle-project/Sparkle"
    description = "A software update framework for macOS "
    topics = ("macos", "framework", "update", "software-update")

    # Binary configuration
    settings = "os", "compiler", "build_type", "arch"

    @property
    def _configuration(self):
        return "Debug" if self.settings.build_type == "Debug" else "Release"

    def validate(self):
        if self.settings.os != "Macos":
            raise ConanInvalidConfiguration("Sparkle is a macOS framework")
        # One macOS arch per package; a universal arch=armv8|x86_64 is built per arch instead.
        if str(self.settings.arch) not in ("armv8", "x86_64"):
            raise ConanInvalidConfiguration(f"Sparkle builds for macOS armv8 or x86_64, not arch={self.settings.arch}")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        # -derivedDataPath: without it the product lands in ~/Library/Developer/Xcode/DerivedData,
        # outside the build folder. Signing stays at Sparkle's ad-hoc default (CODE_SIGN_IDENTITY = -),
        # which needs no certificate and keeps the nested helpers signed until whoever bundles the
        # framework re-signs it with a Developer ID.
        args = [
            "-project Sparkle.xcodeproj",
            "-scheme Sparkle",
            f"-configuration {self._configuration}",
            f"-derivedDataPath {shlex.quote(os.path.join(self.build_folder, 'dd'))}",
            f"ARCHS={to_apple_arch(self)}",
            "ONLY_ACTIVE_ARCH=NO",
            # A dSYM for Debug too, whose default (dwarf) leaves the debug info in the object files.
            "DEBUG_INFORMATION_FORMAT=dwarf-with-dsym",
        ]
        if self.settings.get_safe("os.version"):
            args.append(f"MACOSX_DEPLOYMENT_TARGET={self.settings.os.version}")
        # The build phases are written for the system's BSD tools (link-tools.sh runs `ln -h`,
        # set-git-version-info.sh `which -s`): /usr/bin and /bin first, so GNU coreutils on PATH
        # (e.g. Homebrew's gnubin) don't shadow them.
        self.run("PATH=/usr/bin:/bin:$PATH xcodebuild " + " ".join(args) + " build")

    def package(self):
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        products = os.path.join(self.build_folder, "dd", "Build", "Products", self._configuration)
        # copytree with symlinks: a framework's Versions/Current and top-level entries are links.
        shutil.copytree(os.path.join(products, "Sparkle.framework"),
                        os.path.join(self.package_folder, "lib", "Sparkle.framework"), symlinks=True)
        # The framework's dSYM and those of the helpers inside it (Autoupdate, Updater.app, the XPC
        # services), so crashes in any of them can be symbolicated.
        for dsym in glob.glob(os.path.join(products, "*.dSYM")):
            shutil.copytree(dsym, os.path.join(self.package_folder, "lib", os.path.basename(dsym)), symlinks=True)

    def package_info(self):
        self.cpp_info.set_property("cmake_target_name", "sparkle::sparkle")
        # Headers and binary come from the framework itself.
        self.cpp_info.frameworkdirs = ["lib"]
        self.cpp_info.frameworks = ["Sparkle"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
