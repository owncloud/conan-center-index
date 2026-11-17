from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.apple import to_apple_arch
from conan.tools.files import get, copy
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
        if not to_apple_arch(self):
            # E.g. a universal arch=armv8|x86_64: build each arch on its own.
            raise ConanInvalidConfiguration(f"arch={self.settings.arch} has no single Xcode ARCHS value")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        # -derivedDataPath: without it the product lands in ~/Library/Developer/Xcode/DerivedData,
        # outside the build folder. Signing is the job of whoever bundles the framework.
        args = [
            "-project Sparkle.xcodeproj",
            "-scheme Sparkle",
            f"-configuration {self._configuration}",
            f"-derivedDataPath {shlex.quote(os.path.join(self.build_folder, 'dd'))}",
            f"ARCHS={to_apple_arch(self)}",
            "ONLY_ACTIVE_ARCH=NO",
            "CODE_SIGNING_ALLOWED=NO",
        ]
        if self.settings.get_safe("os.version"):
            args.append(f"MACOSX_DEPLOYMENT_TARGET={self.settings.os.version}")
        # link-tools.sh runs BSD `ln -h`: /bin first, so GNU coreutils on PATH (e.g. Homebrew's
        # gnubin) don't shadow it. Nothing a Conan build environment provides lives in /bin.
        self.run("PATH=/bin:$PATH xcodebuild " + " ".join(args) + " build")

    def package(self):
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        products = os.path.join(self.build_folder, "dd", "Build", "Products", self._configuration)
        # copytree with symlinks: a framework's Versions/Current and top-level entries are links.
        shutil.copytree(os.path.join(products, "Sparkle.framework"),
                        os.path.join(self.package_folder, "lib", "Sparkle.framework"), symlinks=True)
        dsym = os.path.join(products, "Sparkle.framework.dSYM")
        if os.path.isdir(dsym):
            shutil.copytree(dsym, os.path.join(self.package_folder, "lib", "Sparkle.framework.dSYM"))

    def package_info(self):
        self.cpp_info.set_property("cmake_target_name", "sparkle::sparkle")
        # Headers and binary come from the framework itself.
        self.cpp_info.frameworkdirs = ["lib"]
        self.cpp_info.frameworks = ["Sparkle"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
