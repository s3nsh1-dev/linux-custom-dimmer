// Public Qt/LayerShellQt APIs only. Never changes the global shell integration.
#include <LayerShellQt/Window>
#include <QGuiApplication>
#include <QThread>
#include <QWindow>
#include <cstring>

#define DIMMER_API extern "C" __attribute__((visibility("default")))

DIMMER_API int dimmer_bridge_abi() { return 1; }
DIMMER_API const char *dimmer_build_qt() { return QT_VERSION_STR; }
DIMMER_API const char *dimmer_runtime_qt() { return qVersion(); }

// The caller must supply its own live QWindow and keep it alive throughout this
// call. A raw C pointer cannot prove lifetime. Python enforces type/lifetime/GIL.
// The adapter retains no pointer; LayerShellQt's attachment is parented to QWindow.
DIMMER_API int dimmer_configure(void *pointer, const char *caller_qt) noexcept
{
    if (!caller_qt || std::strcmp(caller_qt, QT_VERSION_STR) != 0
        || std::strcmp(caller_qt, qVersion()) != 0) {
        return 3;
    }
    auto *app = qobject_cast<QGuiApplication *>(QCoreApplication::instance());
    if (!app) return 1;
    if (QThread::currentThread() != app->thread()) return 2;
    if (!pointer) return 4;
    if (QGuiApplication::platformName() != QStringLiteral("wayland")) return 5;
    auto *window = static_cast<QWindow *>(pointer);
    if (window->thread() != app->thread()) return 2;
    if (window->handle() || window->isVisible()) return 6;
    try {
        window->setFlags(window->flags() | Qt::FramelessWindowHint
                         | Qt::WindowTransparentForInput | Qt::WindowDoesNotAcceptFocus);
        using Layer = LayerShellQt::Window;
        auto *layer = Layer::get(window);
        if (!layer) return 7;
        layer->setLayer(Layer::LayerOverlay);
        layer->setAnchors(Layer::Anchors(Layer::AnchorTop) | Layer::AnchorBottom
                          | Layer::AnchorLeft | Layer::AnchorRight);
        layer->setExclusiveZone(-1);
        layer->setKeyboardInteractivity(Layer::KeyboardInteractivityNone);
        layer->setActivateOnShow(false);
        layer->setScreen(window->screen());
        layer->setCloseOnDismissed(true);
        layer->setScope(QStringLiteral("linux-custom-dimmer"));
        return 0;
    } catch (...) {
        return 7;
    }
}
