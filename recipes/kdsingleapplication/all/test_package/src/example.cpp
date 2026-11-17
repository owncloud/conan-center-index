#include "kdsingleapplication-qt6/kdsingleapplication_version.h"
// The desktop client includes the headers unprefixed
#include <kdsingleapplication.h>
#include <iostream>

int main()
{
    std::cout << KDSINGLEAPPLICATION_VERSION_STRING << std::endl;
}
