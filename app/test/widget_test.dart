import 'package:flutter_test/flutter_test.dart';
import 'package:flutter/material.dart';
import 'package:midi_keyboard_monitor_app/main.dart' as app;

void main() {
  testWidgets('App builds', (WidgetTester tester) async {
    await tester.pumpWidget(app.MyApp());
    expect(find.text('MIDI Keyboard Monitor'), findsOneWidget);
  });
}
