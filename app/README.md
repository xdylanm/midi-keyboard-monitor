# MIDI Keyboard Monitor — Flutter Client (scaffold)

This folder contains a minimal Flutter app scaffold for the MIDI Keyboard Monitor project.

Supported platforms

- Android: Supported and tested. Use a physical Android device for BLE-related features; the emulator has limited BLE capabilities.
- iOS: Not implemented in this scaffold (can be added later).
- Web / Windows / macOS / Linux: Not supported and removed from the project by default.

Quick start (Android)

```bash
cd app
flutter pub get
# Launch an emulator or connect a device, then:
flutter run -d <deviceId>
```

Notes

- The BLE service is currently a stub (`lib/ble_service.dart`) with test hooks (`simulateNote`, `mockConnect`).
- The app uses `flutter_reactive_ble` in `pubspec.yaml` for BLE functionality.
- For BLE testing use a real Android device whenever possible; emulators often lack full BLE support.
- If you removed platform folders (macos/windows/linux/web), you can regenerate them with `flutter create .` if needed in future.

Android permissions

- BLE-related permissions are included in `android/app/src/main/AndroidManifest.xml`. Android 12+ requires runtime permissions (`BLUETOOTH_SCAN`, `BLUETOOTH_CONNECT`) and location permission for scanning; the app must request these at runtime.
