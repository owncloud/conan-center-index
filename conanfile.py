from conan import ConanFile

class GlobalDependencyMirror(ConanFile):
    settings = "os", "compiler", "arch", "build_type"
    options = {"shared": [True, False]}
    default_options = {
        "*:fPIC": True,
        "qt/*:gui": True,
        "qt/*:qtdeclarative": True,
        "qt/*:qtimageformats": True,
        "qt/*:qtquickcontrols2": True,
        "qt/*:qtshadertools": True,
        "qt/*:qtsvg": True,
        "qt/*:qttools": True,
        "qt/*:qttranslations": True,
        "qt/*:shared": True,
        "qt/*:widgets": True,
        "qt/*:with_egl": True,
        "qt/*:with_libjpeg": "libjpeg",
        "qt/*:with_odbc": False,
        "qt/*:with_pq": False,
        "shared": True,
    }

    def configure(self):
        if self.settings.os == "Linux":
            self.options['qt/*'].with_dbus = True
            self.options['qt/*'].qtwayland = True

    def requirements(self):
        self.requires("extra-cmake-modules/6.8.0")
        self.requires("kdsingleapplication/1.2.0")
        self.requires("libregraphapi/1.0.4")
        self.requires("nlohmann_json/3.11.3")
        self.requires("openssl/3.4.2")
        self.requires("qt/6.8.3")
        self.requires("qtkeychain/0.15.0")
        self.requires("sqlite3/3.49.1")
        self.requires("zlib/1.3.1")

        if self.settings.os == "Macos":
            self.requires("sparkle/2.7.0")

    def build_requirements(self):
        self.tool_requires("cmake/3.30.0")

    def build(self):
        pass
