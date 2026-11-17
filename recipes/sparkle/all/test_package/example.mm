#import <Sparkle/Sparkle.h>

int main()
{
    // The class the client's updater uses; referencing it links and loads the framework.
    return [SUUpdater class] ? 0 : 1;
}
