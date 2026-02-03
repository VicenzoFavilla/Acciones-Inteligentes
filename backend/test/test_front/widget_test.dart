// This is a basic Flutter widget test.
//
// To run this test, it is best placed inside the `frontend/test` directory
// because it depends on the `frontend` pubspec dependencies.
//
// If you want to keep this file here for reference, you can copy its content
// to `frontend/test/widget_test.dart`.

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:frontend/main.dart'; // Ensure this import matches your package name in pubspec.yaml

void main() {
  testWidgets('Counter increments smoke test', (WidgetTester tester) async {
    // Build our app and trigger a frame.
    await tester.pumpWidget(const MyApp());

    // Verify that our counter starts at 0.
    expect(find.text('0'), findsOneWidget);
    expect(find.text('1'), findsNothing);

    // Tap the '+' icon and trigger a frame.
    await tester.tap(find.byIcon(Icons.add));
    await tester.pump();

    // Verify that our counter has incremented.
    expect(find.text('0'), findsNothing);
    expect(find.text('1'), findsOneWidget);
  });
}
