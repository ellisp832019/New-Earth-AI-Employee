import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

import 'package:gaia_windows/src/controller.dart';
import 'package:gaia_windows/src/backend_api.dart';
import 'package:gaia_windows/src/models.dart';
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

  testWidgets('renders the project officer workspace shell', (
    WidgetTester tester,
  ) async {
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

  testWidgets('gaia shell fits a 1280x720 window without overflow', (
    WidgetTester tester,
  ) async {
    final controller = GaiaAppController();
    controller.initialized = true;
    controller.firstRunMode = false;
    controller.backendState = BackendConnectionState.connected;
    controller.backendCompatibilityState = BackendCompatibilityState.compatible;
    controller.health = HealthResponse(
      status: 'ok',
      version: '0.8.0',
      databasePath: 'data/gaia.db',
      fts5Available: true,
    );
    controller.projects = [
      ProjectConfig(
        projectId: 'microgrow-v1',
        name: 'MicroGrow V1',
        root: r'D:\Dev\Projects\MicroGrow V1',
        access: 'read_only',
        approvedExtensions: const [],
        excludedDirectories: const [],
        excludedFilenames: const [],
        importantPaths: const [],
      ),
    ];
    controller.selectedProjectId = 'microgrow-v1';

    await tester.binding.setSurfaceSize(const Size(1280, 720));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      MaterialApp(home: GaiaShell(controller: controller)),
    );
    await tester.pumpAndSettle();

    expect(find.text('GAIA - Windows Control Centre'), findsOneWidget);
    expect(find.text('Project Officer'), findsWidgets);
    expect(find.text('Settings'), findsWidgets);
    expect(tester.takeException(), isNull);
  });

  testWidgets('gaia shell fits a 1366x768 window without overflow', (
    WidgetTester tester,
  ) async {
    final controller = GaiaAppController();
    controller.initialized = true;
    controller.firstRunMode = false;
    controller.backendState = BackendConnectionState.connected;
    controller.backendCompatibilityState = BackendCompatibilityState.compatible;
    controller.health = HealthResponse(
      status: 'ok',
      version: '0.8.0',
      databasePath: 'data/gaia.db',
      fts5Available: true,
    );
    controller.projects = [
      ProjectConfig(
        projectId: 'microgrow-v1',
        name: 'MicroGrow V1',
        root: r'D:\Dev\Projects\MicroGrow V1',
        access: 'read_only',
        approvedExtensions: const [],
        excludedDirectories: const [],
        excludedFilenames: const [],
        importantPaths: const [],
      ),
    ];
    controller.selectedProjectId = 'microgrow-v1';

    await tester.binding.setSurfaceSize(const Size(1366, 768));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      MaterialApp(home: GaiaShell(controller: controller)),
    );
    await tester.pumpAndSettle();

    expect(find.text('GAIA - Windows Control Centre'), findsOneWidget);
    expect(find.text('About'), findsWidgets);
    expect(tester.takeException(), isNull);
  });

  testWidgets('gaia shell fits a 1600x900 window without overflow', (
    WidgetTester tester,
  ) async {
    final controller = GaiaAppController();
    controller.initialized = true;
    controller.firstRunMode = false;
    controller.backendState = BackendConnectionState.connected;
    controller.backendCompatibilityState = BackendCompatibilityState.compatible;
    controller.health = HealthResponse(
      status: 'ok',
      version: '0.9.0',
      databasePath: 'data/gaia.db',
      fts5Available: true,
    );
    controller.projects = [
      ProjectConfig(
        projectId: 'microgrow-v1',
        name: 'MicroGrow V1',
        root: r'D:\Dev\Projects\MicroGrow V1',
        access: 'read_only',
        approvedExtensions: const [],
        excludedDirectories: const [],
        excludedFilenames: const [],
        importantPaths: const [],
      ),
    ];
    controller.selectedProjectId = 'microgrow-v1';

    await tester.binding.setSurfaceSize(const Size(1600, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      MaterialApp(home: GaiaShell(controller: controller)),
    );
    await tester.pumpAndSettle();

    expect(find.text('GAIA - Windows Control Centre'), findsOneWidget);
    expect(find.text('Settings'), findsWidgets);
    expect(tester.takeException(), isNull);
  });

  testWidgets('gaia shell fits a 1920x1080 window without overflow', (
    WidgetTester tester,
  ) async {
    final controller = GaiaAppController();
    controller.initialized = true;
    controller.firstRunMode = false;
    controller.backendState = BackendConnectionState.connected;
    controller.backendCompatibilityState = BackendCompatibilityState.compatible;
    controller.health = HealthResponse(
      status: 'ok',
      version: '0.9.0',
      databasePath: 'data/gaia.db',
      fts5Available: true,
    );
    controller.projects = [
      ProjectConfig(
        projectId: 'microgrow-v1',
        name: 'MicroGrow V1',
        root: r'D:\Dev\Projects\MicroGrow V1',
        access: 'read_only',
        approvedExtensions: const [],
        excludedDirectories: const [],
        excludedFilenames: const [],
        importantPaths: const [],
      ),
    ];
    controller.selectedProjectId = 'microgrow-v1';

    await tester.binding.setSurfaceSize(const Size(1920, 1080));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      MaterialApp(home: GaiaShell(controller: controller)),
    );
    await tester.pumpAndSettle();

    expect(find.text('GAIA - Windows Control Centre'), findsOneWidget);
    expect(find.text('Project Officer'), findsWidgets);
    expect(tester.takeException(), isNull);
  });

  test('refreshBackend uses the explicit compatibility contract', () async {
    final controller = GaiaAppController(
      backendApi: GaiaApiClient(
        baseUri: Uri.parse('http://127.0.0.1:8000'),
        client: MockClient((request) async {
          switch (request.url.path) {
            case '/health':
              return http.Response(
                jsonEncode({
                  'status': 'ok',
                  'version': '0.8.0',
                  'database_path': 'data/gaia.db',
                  'fts5_available': true,
                }),
                200,
              );
            case '/integration/v1/compatibility':
              return http.Response(
                jsonEncode({
                  'status': 'compatible',
                  'backend_version': '0.8.0',
                  'integration_contract_version': 'gaia-v3',
                  'capability_version': '0.9.0',
                }),
                200,
              );
            default:
              return http.Response('{}', 404);
          }
        }),
      ),
    );

    await controller.refreshBackend();

    expect(controller.backendState, BackendConnectionState.connected);
    expect(
      controller.backendCompatibilityState,
      BackendCompatibilityState.compatible,
    );
    expect(controller.lastError, isNull);
    expect(controller.integrationCompatibility, isNotNull);
  });

  test(
    'refreshBackend surfaces contract mismatches without stale v0.5 text',
    () async {
      final controller = GaiaAppController(
        backendApi: GaiaApiClient(
          baseUri: Uri.parse('http://127.0.0.1:8000'),
          client: MockClient((request) async {
            switch (request.url.path) {
              case '/health':
                return http.Response(
                  jsonEncode({
                    'status': 'ok',
                    'version': '0.8.0',
                    'database_path': 'data/gaia.db',
                    'fts5_available': true,
                  }),
                  200,
                );
              case '/integration/v1/compatibility':
                return http.Response(
                  jsonEncode({
                    'status': 'contract_mismatch',
                    'backend_version': '0.8.0',
                    'integration_contract_version': 'gaia-v2',
                    'capability_version': '0.8.0',
                  }),
                  200,
                );
              default:
                return http.Response('{}', 404);
            }
          }),
        ),
      );

      await controller.refreshBackend();

      expect(controller.backendState, BackendConnectionState.connected);
      expect(
        controller.backendCompatibilityState,
        BackendCompatibilityState.incompatible,
      );
      expect(controller.lastError, isNotNull);
      expect(controller.lastError, isNot(contains('v0.5 desktop client')));
      expect(controller.lastError, contains('contract_mismatch'));
    },
  );
}
