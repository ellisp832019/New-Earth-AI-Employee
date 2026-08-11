import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gaia_dashboard_module/gaia_dashboard_module.dart';
import 'package:gaia_integration_client/gaia_integration_client.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

void main() {
  test('dashboard module source stays read only', () {
    final controllerSource = File('lib/src/controller.dart').readAsStringSync();
    final viewSource = File('lib/src/dashboard_view.dart').readAsStringSync();
    for (final forbidden in <String>[
      'approveRevision(',
      'rejectRevision(',
      'submitForReview(',
      'recordHandoff(',
      'recordOutcome(',
    ]) {
      expect(controllerSource, isNot(contains(forbidden)));
      expect(viewSource, isNot(contains(forbidden)));
    }
  });

  test('controller preserves ordering and explicit summary states', () async {
    final seenRequests = <String>[];
    final controller = GaiaDashboardController(
      client: GaiaIntegrationClient(
        baseUri: Uri.parse('http://127.0.0.1:8765'),
        client: _dashboardMockClient(
          seenRequests: seenRequests,
          projectOfficerEnabled: true,
          changePortfolioStale: true,
        ),
      ),
    );

    await controller.refresh();

    expect(controller.connectionState, GaiaDashboardConnectionState.connected);
    expect(
      controller.projectOfficerState,
      GaiaProjectOfficerSummaryState.stale,
    );
    expect(controller.projectOfficerStale, isTrue);
    expect(controller.projectOfficerSupported, isTrue);
    expect(controller.projectOfficerPortfolioProjects.length, 1);
    expect(controller.projectOfficerPortfolioCountsByStatus['healthy'], 1);
    expect(
      controller.projectOfficerTopRecommendations
          .map((item) => item['title'])
          .toList(),
      <String>['First recommendation', 'Second recommendation'],
    );
    expect(controller.projectOfficerBlockedProjects.length, 1);
    expect(controller.projectOfficerPendingApprovalPackages.length, 1);
    expect(controller.projectOfficerRecentCompletedWork.length, 1);
    expect(
      controller.projectOfficerRecentCompletedWork.first['outcome'],
      'completed',
    );
    expect(seenRequests.any((request) => request.startsWith('POST ')), isFalse);
    expect(
      seenRequests.any(
        (request) =>
            request.contains('/approve') ||
            request.contains('/reject') ||
            request.contains('/handoff'),
      ),
      isFalse,
    );
    expect(
      seenRequests.where((request) => request.contains('/outcomes')).length,
      1,
    );
  });

  test(
    'controller fails closed when project officer capability is unavailable',
    () async {
      final seenRequests = <String>[];
      final controller = GaiaDashboardController(
        client: GaiaIntegrationClient(
          baseUri: Uri.parse('http://127.0.0.1:8765'),
          client: _dashboardMockClient(
            seenRequests: seenRequests,
            projectOfficerEnabled: false,
          ),
        ),
      );

      await controller.refresh();

      expect(
        controller.connectionState,
        GaiaDashboardConnectionState.connected,
      );
      expect(
        controller.projectOfficerState,
        GaiaProjectOfficerSummaryState.unavailable,
      );
      expect(controller.projectOfficerSupported, isFalse);
      expect(
        controller.projectOfficerError,
        contains('unavailable on this GAIA backend'),
      );
      expect(
        seenRequests.any(
          (request) => request.contains('/project-officer/portfolio'),
        ),
        isFalse,
      );
      expect(
        seenRequests.any(
          (request) =>
              request.contains('/project-officer/recommendations/portfolio'),
        ),
        isFalse,
      );
      expect(
        seenRequests.any(
          (request) => request.contains('/project-officer/work-packages'),
        ),
        isFalse,
      );
    },
  );

  test(
    'controller preserves legacy data when project officer capability lookup fails',
    () async {
      final seenRequests = <String>[];
      final controller = GaiaDashboardController(
        client: GaiaIntegrationClient(
          baseUri: Uri.parse('http://127.0.0.1:8765'),
          client: _dashboardMockClient(
            seenRequests: seenRequests,
            projectOfficerCapabilitiesStatusCode: 404,
          ),
        ),
      );

      await controller.refresh();

      expect(
        controller.connectionState,
        GaiaDashboardConnectionState.connected,
      );
      expect(
        controller.projectOfficerState,
        GaiaProjectOfficerSummaryState.unavailable,
      );
      expect(controller.projectOfficerStale, isTrue);
      expect(controller.errorMessage, isNull);
      expect(
        seenRequests.any(
          (request) => request.contains('/project-officer/portfolio'),
        ),
        isFalse,
      );
    },
  );

  testWidgets('renders the Project Officer summary surface read only', (
    tester,
  ) async {
    final controller = GaiaDashboardController(
      client: GaiaIntegrationClient(
        baseUri: Uri.parse('http://127.0.0.1:8765'),
        client: _dashboardMockClient(seenRequests: <String>[]),
      ),
    );

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(body: GaiaDashboardView(controller: controller)),
      ),
    );
    await tester.runAsync(controller.refresh);
    await tester.pumpAndSettle();

    await tester.tap(find.text('Project Officer').first);
    await tester.pumpAndSettle();

    expect(find.text('Project Officer summary'), findsOneWidget);
    expect(find.text('Capability available'), findsOneWidget);
    expect(find.text('Approve'), findsNothing);
    expect(find.text('Reject'), findsNothing);
    expect(find.text('Submit for review'), findsNothing);
    expect(find.text('Handoff'), findsNothing);
    expect(find.text('Execute'), findsNothing);
    expect(find.text('Rollback'), findsNothing);
    expect(find.text('Sign'), findsNothing);
  });

  testWidgets('renders unavailable project officer state explicitly', (
    tester,
  ) async {
    final controller = GaiaDashboardController(
      client: GaiaIntegrationClient(
        baseUri: Uri.parse('http://127.0.0.1:8765'),
        client: _dashboardMockClient(
          seenRequests: <String>[],
          projectOfficerEnabled: false,
        ),
      ),
    );

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(body: GaiaDashboardView(controller: controller)),
      ),
    );
    await tester.runAsync(controller.refresh);
    await tester.pumpAndSettle();

    await tester.tap(find.text('Project Officer').first);
    await tester.pumpAndSettle();

    expect(
      find.textContaining('unavailable on this GAIA backend'),
      findsAtLeastNWidgets(1),
    );
    expect(find.text('Capability unavailable'), findsOneWidget);
  });
}

MockClient _dashboardMockClient({
  required List<String> seenRequests,
  bool projectOfficerEnabled = true,
  int projectOfficerCapabilitiesStatusCode = 200,
  bool changePortfolioStale = false,
}) {
  return MockClient((request) async {
    seenRequests.add('${request.method} ${request.url.path}');
    switch (request.url.path) {
      case '/integration/v1/compatibility':
        return _jsonResponse({
          'backend_product_version': '0.8.0',
          'minimum_supported_api_version': '0.8.0',
          'maximum_tested_api_version': '0.10.0',
          'integration_contract_version': 'gaia-v2',
          'client_package_version': '0.8.0',
          'backend_version': '0.8.0',
          'status': 'compatible',
          'loopback_only': true,
          'capability_version': '0.8.0',
          'capabilities': ['embedded_operations_workspace'],
          'capability_catalog': [
            {
              'capability_id': 'embedded_operations_workspace',
              'version': '0.8.0',
              'state': 'enabled',
              'summary': 'Embedded operations workspace',
              'gated_by': const [],
              'requires_signing': false,
              'enabled': true,
            },
          ],
          'degraded_features': const [],
          'deprecation_warnings': const [],
        });
      case '/integration/v1/capabilities':
        return _jsonResponse({
          'capability_version': '0.8.0',
          'capabilities': ['embedded_operations_workspace'],
          'capability_catalog': const [],
          'degraded_features': const [],
          'signing_enabled': false,
          'signing_key_count': 0,
        });
      case '/integration/v1/status':
        return _jsonResponse({'backend': 'ok'});
      case '/integration/v1/projects':
        return _jsonResponse(const []);
      case '/integration/v1/tasks/summary':
        return _jsonResponse({
          'project_id': 'demo',
          'total': 1,
          'active': 1,
          'pending': 0,
          'completed': 0,
        });
      case '/integration/v1/approvals/summary':
        return _jsonResponse({
          'project_id': 'demo',
          'total': 1,
          'active': 1,
          'pending': 0,
          'completed': 0,
        });
      case '/integration/v1/actions/summary':
        return _jsonResponse({
          'project_id': 'demo',
          'total': 1,
          'proposed': 1,
          'awaiting_approval': 0,
          'approved': 0,
          'completed': 0,
          'failed': 0,
          'invalidated': 0,
          'rolled_back': 0,
        });
      case '/integration/v1/briefs/latest':
        return _jsonResponse(null);
      case '/integration/v1/receipts/latest':
        return _jsonResponse(null);
      case '/action-templates':
        return _jsonResponse(const []);
      case '/retention/policies':
        return _jsonResponse(const []);
      case '/retention/status':
        return _jsonResponse({
          'policies': const [],
          'plans': const [],
          'receipts': const [],
        });
      case '/retention/report':
        return _jsonResponse({
          'generated_at': '2026-08-06T00:00:00Z',
          'policy_count': 0,
          'plan_count': 0,
          'receipt_count': 0,
          'enabled_policy_count': 0,
          'issues': const [],
          'summary': const {},
        });
      case '/signing/keys':
        return _jsonResponse(const []);
      case '/provenance/manifests':
        return _jsonResponse(const []);
      case '/trust/alerts':
        return _jsonResponse([
          {
            'alert_id': 'alert-1',
            'alert_type': 'trust',
            'severity': 'warning',
            'status': 'open',
            'title': 'Trust alert',
            'message': 'Evidence needs review',
            'source_kind': 'project',
            'source_id': 'project-alpha',
            'created_at': '2026-08-06T08:00:00Z',
            'acknowledged_at': null,
            'metadata': const {},
          },
        ]);
      case '/integration/v1/project-officer/capabilities':
        if (projectOfficerCapabilitiesStatusCode != 200) {
          return http.Response(
            'not found',
            projectOfficerCapabilitiesStatusCode,
          );
        }
        return _jsonResponse({
          'capability_version': '0.10.0',
          'capabilities': projectOfficerEnabled
              ? ['project_officer_portfolio', 'project_officer_work_packages']
              : ['legacy_only'],
        });
      case '/integration/v1/project-officer/portfolio':
        return _jsonResponse({
          'generated_at': '2026-08-06T12:00:00Z',
          'enabled_project_count': 1,
          'counts_by_status': {
            'healthy': 1,
            'attention': 0,
            'blocked': 0,
            'unknown': 0,
          },
          'projects': [
            {
              'project_id': 'project-alpha',
              'project_name': 'Project Alpha',
              'normalized_status': 'healthy',
              'evidence_freshness': 'fresh',
              'reason_codes': ['fresh_evidence'],
              'latest_snapshot': {
                'normalized_payload': {
                  'git_state': {
                    'branch': 'main',
                    'commit_sha': '0123456789abcdef',
                    'is_clean': true,
                  },
                  'configured_evidence': {
                    'evidence_freshness': {'state': 'fresh'},
                  },
                },
              },
            },
          ],
        });
      case '/integration/v1/project-officer/recommendations/portfolio':
        return _jsonResponse({
          'recommendation_queue': [
            {
              'priority_tier': 'P1',
              'deterministic_score': '0.97',
              'project_id': 'project-alpha',
              'title': 'First recommendation',
              'concise_summary': 'Keep the latest evidence current.',
              'why_it_matters': 'Read-only command-centre summary.',
              'evidence_freshness': 'fresh',
              'lifecycle_state': 'active',
            },
            {
              'priority_tier': 'P2',
              'deterministic_score': '0.88',
              'project_id': 'project-beta',
              'title': 'Second recommendation',
              'concise_summary': 'A secondary backend-ranked item.',
              'why_it_matters': 'Keeps ranking visible.',
              'evidence_freshness': 'fresh',
              'lifecycle_state': 'active',
            },
          ],
          'projects': [
            {
              'project_id': 'project-alpha',
              'project_name': 'Project Alpha',
              'latest_lifecycle_state': 'blocked',
              'blocked_recommendation_count': 2,
              'latest_recommendations': [
                {
                  'blockers': [
                    {'blocker_description': 'Waiting on human review'},
                  ],
                },
              ],
            },
            {
              'project_id': 'project-beta',
              'project_name': 'Project Beta',
              'latest_lifecycle_state': 'active',
              'blocked_recommendation_count': 0,
              'latest_recommendations': const [
                {'blockers': const []},
              ],
            },
          ],
        });
      case '/integration/v1/project-officer/changes/portfolio':
        return _jsonResponse({
          'projects': [
            {
              'project_id': 'project-alpha',
              'project_name': 'Project Alpha',
              'latest_health_status': 'attention',
              'latest_comparison_id': 'cmp-1',
              'latest_comparison_freshness': changePortfolioStale
                  ? 'stale'
                  : 'fresh',
              'stale_evidence': changePortfolioStale,
            },
          ],
        });
      case '/integration/v1/project-officer/work-packages':
        if (request.url.query.contains('approval_state=under_review')) {
          return _jsonResponse([
            {
              'project_id': 'project-alpha',
              'work_package_id': 'package-1',
              'title': 'Pending approval package',
              'current_revision_number': 3,
              'risk_classification': 'moderate',
              'approval_state': 'under_review',
              'staleness_state': 'fresh',
            },
          ]);
        }
        if (request.url.query.contains('approval_state=completed')) {
          return _jsonResponse([
            {
              'project_id': 'project-alpha',
              'work_package_id': 'package-1',
              'title': 'Completed package',
              'current_revision_number': 3,
              'risk_classification': 'moderate',
              'approval_state': 'completed',
              'staleness_state': 'fresh',
            },
          ]);
        }
        return _jsonResponse(const []);
      case '/integration/v1/project-officer/work-packages/package-1/outcomes':
        return _jsonResponse([
          {
            'project_id': 'project-alpha',
            'work_package_id': 'package-1',
            'revision_number': 3,
            'outcome': 'completed',
            'recorded_at': '2026-08-06T12:10:00Z',
            'evidence_fingerprint': 'sha256:abcd',
          },
        ]);
      default:
        return http.Response('not found', 404);
    }
  });
}

http.Response _jsonResponse(Object? body, [int statusCode = 200]) {
  return http.Response(
    jsonEncode(body),
    statusCode,
    headers: const {'content-type': 'application/json'},
  );
}
