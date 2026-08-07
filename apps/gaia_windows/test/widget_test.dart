// This is a basic Flutter widget test.
//
// To perform an interaction with a widget in your test, use the WidgetTester
// utility in the flutter_test package. For example, you can send tap and scroll
// gestures. You can also use WidgetTester to find child widgets in the widget
// tree, read text, and verify that the values of widget properties are correct.

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:gaia_windows/src/controller.dart';
import 'package:gaia_windows/src/screens.dart';
import 'package:gaia_windows/src/widgets.dart';

void main() {
  testWidgets('renders the GAIA status chip', (WidgetTester tester) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: StatusChip(label: 'Connected', color: Color(0xFF00AA88)),
        ),
      ),
    );
    await tester.pump();

    expect(find.text('Connected'), findsOneWidget);
  });

  testWidgets('renders the project officer workspace shell', (WidgetTester tester) async {
    final controller = GaiaAppController();

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: ProjectOfficerWorkspaceScreen(controller: controller),
        ),
      ),
    );
    await tester.pump();

    expect(find.text('Project Officer Workspace'), findsOneWidget);
    expect(find.text('Planning Portfolio'), findsOneWidget);
  });
}
