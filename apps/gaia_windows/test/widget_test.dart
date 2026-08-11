import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

import 'package:gaia_windows/src/controller.dart';
import 'package:gaia_windows/src/backend_api.dart';
import 'package:gaia_windows/src/models.dart';
import 'package:gaia_windows/src/programme_workspace.dart';
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

  testWidgets('programme intelligence workspace fits desktop sizes', (
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
    controller.selectedProjectId = 'sample';
    controller.programmeWorkspace = _programmeWorkspaceFixture();

    for (final size in const [
      Size(1280, 720),
      Size(1366, 768),
      Size(1600, 900),
      Size(1920, 1080),
    ]) {
      await tester.binding.setSurfaceSize(size);
      addTearDown(() => tester.binding.setSurfaceSize(null));

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: ProgrammeIntelligenceWorkspaceScreen(controller: controller),
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(tester.takeException(), isNull);
    }
  });

  testWidgets('programme intelligence release trains surface renders', (
    WidgetTester tester,
  ) async {
    final controller = GaiaAppController();
    controller.initialized = true;
    controller.firstRunMode = false;
    controller.backendState = BackendConnectionState.connected;
    controller.backendCompatibilityState = BackendCompatibilityState.compatible;
    controller.programmeWorkspace = _programmeWorkspaceFixture();

    await tester.binding.setSurfaceSize(const Size(1600, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: ProgrammeIntelligenceWorkspaceScreen(
            controller: controller,
            initialIndex: 6,
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Release Train Detail'), findsOneWidget);
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

Map<String, dynamic> _programmeWorkspaceFixture() {
  return {
    'generated_at': '2026-08-10T12:00:00Z',
    'selected_project_id': 'sample',
    'selected_project': {'project_id': 'sample', 'name': 'Sample'},
    'summary': {
      'project_count': 1,
      'health_status_counts': {'healthy': 1},
      'change_severity_counts': {'low': 1},
      'recommendation_state_counts': {'active': 1},
      'roadmap_state_counts': {'NOW': 1},
      'release_train_readiness_counts': {'READY': 1},
      'package_state_counts': {'approved': 1},
      'architecture_entity_count': 1,
      'architecture_relationship_count': 1,
      'cycle_count': 0,
      'unresolved_dependency_count': 0,
      'shared_dependency_count': 0,
      'orphan_count': 0,
      'trust_alert_count': 1,
      'provenance_manifest_count': 1,
      'stale_evidence_projects': [],
    },
    'overview': {
      'health_portfolio': {
        'counts_by_status': {'healthy': 1},
        'projects_without_snapshots': [],
      },
      'change_portfolio': {
        'counts_by_severity': {'low': 1},
        'projects': [{}],
      },
      'recommendation_portfolio': {
        'counts_by_state': {'active': 1},
        'recommendation_queue': [{}],
      },
      'roadmap_portfolio': {
        'counts_by_state': {'NOW': 1},
        'roadmap_items': [{}],
      },
      'release_portfolio': {
        'counts_by_readiness': {'READY': 1},
        'release_trains': [{}],
      },
      'package_portfolio': {
        'counts_by_state': {'approved': 1},
        'programme_packages': [
          {
            'programme_package_id': 'pkg-1',
            'objective': 'Sample package',
            'package_state': 'approved',
            'current_revision_number': 1,
            'package_fingerprint': '1234567890abcdef',
            'human_approval': {'approval_state': 'approved'},
            'revision_history': [],
          },
        ],
      },
    },
    'architecture_registry': {
      'entities': [
        {
          'entity_id': 'entity-1',
          'identity_key': 'sample',
          'name': 'Sample',
          'kind': 'project',
          'status': 'approved',
          'freshness_state': 'fresh',
          'current_revision_number': 1,
        },
      ],
      'relationships': [
        {
          'relationship_id': 'rel-1',
          'relationship_type': 'DEPENDS_ON',
          'source_entity_id': 'entity-1',
          'target_entity_id': 'entity-1',
          'canonical_relationship_reference': 'ref-1',
        },
      ],
    },
    'dependency_graph': {
      'snapshot': {
        'graph_id': 'graph-1',
        'graph_fingerprint': 'graph-fingerprint',
        'node_count': 1,
        'edge_count': 1,
        'freshness_state': 'fresh',
        'trust_state': 'trusted',
      },
      'cycles': [],
      'shared_dependencies': [],
      'orphans': [],
      'unresolved_findings': [],
      'project_dependencies': [],
      'project_dependents': [],
    },
    'impact_analysis': {
      'analyses': [
        {
          'analysis_id': 'analysis-1',
          'proposal': {
            'proposal_id': 'proposal-1',
            'title': 'Sample analysis',
            'origin_project': 'sample',
          },
          'impact_fingerprint': 'impact-1',
          'risk': {'risk_level': 'LOW'},
          'freshness_state': 'fresh',
          'trust_state': 'trusted',
          'selected_change_findings': [],
        },
      ],
      'selected_change_findings': [],
    },
    'change_proposals': {
      'recommendations': [
        {
          'recommendation_id': 'rec-1',
          'title': 'Sample proposal',
          'recommendation_type': 'review_project_configuration_change',
          'priority_tier': 'P1',
          'lifecycle_state': 'active',
          'concise_summary': 'Summary',
          'why_it_matters': 'It matters',
        },
      ],
      'selected_recommendation': {},
    },
    'roadmap': {
      'roadmap_items': [
        {
          'roadmap_item_id': 'roadmap-1',
          'title': 'Sample roadmap item',
          'roadmap_state': 'NOW',
          'source_type': 'project',
          'project_id': 'sample',
          'rank': 1,
        },
      ],
    },
    'release_trains': {
      'release_trains': [
        {
          'release_train_id': 'train-1',
          'objective': 'Sample train',
          'release_readiness': 'READY',
          'human_approval_state': 'required',
          'trust': 'trusted',
          'train_fingerprint': 'train-fingerprint',
        },
      ],
    },
    'programme_packages': {
      'programme_packages': [
        {
          'programme_package_id': 'pkg-1',
          'objective': 'Sample package',
          'package_state': 'approved',
          'current_revision_number': 1,
          'package_fingerprint': '1234567890abcdef',
          'human_approval': {'approval_state': 'approved'},
          'revision_history': [],
        },
      ],
    },
    'decisions': {
      'selected_work_packages': [
        {
          'work_package_id': 'wp-1',
          'title': 'Sample work package',
          'approval_state': 'approved',
          'gate_state': 'open',
          'staleness_state': 'fresh',
          'risk_classification': 'low',
        },
      ],
      'selected_health_snapshots': [
        {'snapshot_id': 'snapshot-1'},
      ],
      'selected_contract': {'contract_id': 'contract-1'},
      'trust_alerts': [
        {'severity': 'warning', 'title': 'Sample alert', 'message': 'Example'},
      ],
    },
    'cross_project_evidence': {
      'provenance_manifests': [
        {'manifest_id': 'manifest-1', 'name': 'Sample manifest'},
      ],
      'capabilities': ['windows_programme_workspace'],
      'selected_project_health': {'normalized_status': 'healthy'},
      'selected_project_change_findings': [],
      'selected_project_recommendations': [],
      'selected_project_work_packages': [],
      'selected_project_dependencies': [],
      'selected_project_dependents': [],
    },
  };
}
