// Offscreen only: prove the native automatic read and the read-only guard.
// Uses a synthetic clipboard provider; never connects to a desktop clipboard.
#include <QClipboard>
#include <QGuiApplication>
#include <QMimeData>
#include <QQmlComponent>
#include <QQmlEngine>
#include <QVariant>
#include <cstdio>
#include <memory>

struct Provider final : QMimeData {
    int* calls;
    int* reads;
    explicit Provider(int& count, int& payloadReads) : calls(&count), reads(&payloadReads) {}
    QStringList formats() const override { ++*calls; return {"text/plain"}; }
    bool hasFormat(const QString& name) const override { ++*calls; return name == "text/plain"; }
    QVariant retrieveData(const QString&, QMetaType) const override { ++*calls; ++*reads; return QStringLiteral("synthetic"); }
};

int main(int argc, char** argv) {
    qputenv("QT_QPA_PLATFORM", "offscreen");
    qputenv("QT_QUICK_BACKEND", "software");
    qunsetenv("WAYLAND_DISPLAY");
    qunsetenv("DISPLAY");
    QGuiApplication app(argc, argv);
    QQmlEngine engine;
    QQmlComponent component(&engine);
    component.setData("import QtQuick\nimport QtQuick.Controls\nTextField { readOnly: true }", QUrl());
    std::unique_ptr<QObject> field(component.create());
    if (!field) { std::fprintf(stderr, "%s\n", qPrintable(component.errorString())); return 1; }
    int baseline = 0, guarded = 0, unsafe = 0, baselinePayload = 0, guardedPayload = 0, unsafePayload = 0;
    app.clipboard()->setMimeData(new Provider(baseline, baselinePayload));
    // The field remains read-only; even querying canPaste must not probe data.
    if (field->property("canPaste").toBool() || baseline != 0) return 2;
    app.clipboard()->setMimeData(new Provider(guarded, guardedPayload));
    app.processEvents();
    if (guarded != 0) return 3;
    const int guardedReads = guarded;
    field->setProperty("readOnly", false);
    app.clipboard()->setMimeData(new Provider(unsafe, unsafePayload));
    app.processEvents();
    if (unsafe == 0) return 4;
    field->setProperty("readOnly", true);
    int protectedAgain = 0, protectedPayload = 0;
    app.clipboard()->setMimeData(new Provider(protectedAgain, protectedPayload));
    app.processEvents();
    if (protectedAgain != 0) return 5;
    std::printf("{\"qt\":\"%s\",\"automatic_unfocused_probes\":%d,\"automatic_payload_reads\":%d,\"guarded_probes\":%d,\"guarded_again_probes\":%d}\n", qVersion(), unsafe, unsafePayload, guardedReads, protectedAgain);
    app.clipboard()->clear();
    return 0;
}
