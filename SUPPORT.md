# Support

For support with this project, please use the following channels:

- **Enterprise Support**: <https://owncloud.com/contact-us/>
- **Community discussions**: https://github.com/orgs/owncloud/discussions
- **Matrix Chat**: <https://app.element.io/#/room/#owncloud:matrix.org>
- **Documentation**: <https://doc.owncloud.com>

Please do not use GitHub issues for general support questions.

## Which tracker for a recipe problem?

This repository is a copy of [conan-io/conan-center-index](https://github.com/conan-io/conan-center-index),
and almost every recipe in it is upstream content.

- A problem with an upstream recipe belongs
  [upstream](https://github.com/conan-io/conan-center-index/issues). Fixes merged there are
  picked up here on the next resync.
- A problem with one of the ownCloud-only recipes (`kdsingleapplication`, `libregraphapi`,
  `qtkeychain`, `sparkle`), with the root `conanfile.py`, or with a published package in the
  ownCloud Artifactory belongs to the desktop maintainers - raise it in the desktop channels
  above.
