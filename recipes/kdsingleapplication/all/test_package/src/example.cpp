#include "kdsingleapplication-qt6/kdsingleapplication_version.h"
// The desktop client includes the headers unprefixed
#include <kdsingleapplication.h>
#include <iostream>

int main()
{
    // staticMetaObject is data in the library, so this links it (and, on Windows, checks the
    // static/shared import define; not yet built there); a member function pointer gets optimized away
    std::cout << KDSINGLEAPPLICATION_VERSION_STRING << " "
              << KDSingleApplication::staticMetaObject.className() << std::endl;
}
