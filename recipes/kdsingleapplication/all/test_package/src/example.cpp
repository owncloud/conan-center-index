#include "kdsingleapplication-qt6/kdsingleapplication_version.h"
// The desktop client includes the headers unprefixed
#include <kdsingleapplication.h>
#include <iostream>

int main()
{
    // Referencing a member links the library, which also checks the static/shared defines
    bool (KDSingleApplication::*isPrimary)() const = &KDSingleApplication::isPrimaryInstance;
    std::cout << KDSINGLEAPPLICATION_VERSION_STRING << (isPrimary ? "" : "?") << std::endl;
}
