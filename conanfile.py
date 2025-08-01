from conan import ConanFile

class GlobalDependencyMirror(ConanFile):
    settings = "os", "compiler", "arch", "build_type"
    options = {"shared": [True, False]}
    default_options = {
        "shared": 'True',
        "*:fPIC": True,
        'qt/*:shared': 'True',
        'qt/*:qtdeclarative': 'True',
        'qt/*:qtquickcontrols2': 'True',
        'qt/*:qtshadertools': 'True',
        'qt/*:qttools': 'True',
        'qt/*:gui': 'True',
        'qt/*:widgets': 'True',
        'qt/*:with_dbus': 'True',
    }

    def requirements(self):
        self.requires("extra-cmake-modules/6.2.0")
        self.requires("zlib/1.3.1")
        self.requires("sqlite3/3.49.1")
        self.requires("openssl/3.4.1")
        self.requires("nlohmann_json/3.11.3")
        self.requires("qt/6.8.3")
        self.requires("kdsingleapplication/1.2.0")
        self.requires("qtkeychain/0.15.0")
        self.requires("libregraphapi/1.0.4")
        if self.settings.os == "Macos":
            self.requires("sparkle/2.7.0")

    def build_requirements(self):
        self.tool_requires("cmake/3.30.0")

    def build(self):
        pass
