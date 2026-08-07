import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gaia_dashboard_module/gaia_dashboard_module.dart';
import 'package:gaia_integration_client/gaia_integration_client.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

void main() {
  testWidgets('reference host shows read-mostly integration messaging', (
    tester,
  ) async {
    final client = MockClient((request) async {
      final path = request.url.path;
      if (path == '/integration/v1/compatibility') {
        return http.Response(
          jsonEncode({
            'backend_product_version': '0.7.0',
            'minimum_supported_api_version': '0.7.0',
            'maximum_tested_api_version': '0.7.0',
            'integration_contract_version': 'gaia-v2',
            'client_package_version': '0.7.0',
            'backend_version': '0.7.0',
            'status': 'compatible',
            'loopback_only': true,
            'capability_version': '0.7.0',
            'capabilities': ['actions', 'receipts'],
            'capability_catalog': [
              {
                'capability_id': 'embedded_operations_workspace',
                'version': '0.7.0',
                'state': 'enabled',
                'summary': 'Embedded operations workspace',
                'gated_by': const [],
                'requires_signing': false,
                'enabled': true,
              },
            ],
            'degraded_features': const [],
            'deprecation_warnings': const [],
          }),
          200,
        );
      }
      if (path == '/integration/v1/status') {
        return http.Response(jsonEncode({'backend': 'ok'}), 200);
      }
      if (path == '/integration/v1/projects') {
        return http.Response(jsonEncode([]), 200);
      }
      if (path == '/integration/v1/tasks/summary') {
        return http.Response(
          jsonEncode({
            'project_id': 'demo',
            'total': 0,
            'active': 0,
            'pending': 0,
            'completed': 0,
          }),
          200,
        );
      }
      if (path == '/integration/v1/approvals/summary') {
        return http.Response(
          jsonEncode({
            'project_id': 'demo',
            'total': 0,
            'active': 0,
            'pending': 0,
            'completed': 0,
          }),
          200,
        );
      }
      if (path == '/integration/v1/actions/summary') {
        return http.Response(
          jsonEncode({
            'project_id': 'demo',
            'total': 0,
            'proposed': 0,
            'awaiting_approval': 0,
            'approved': 0,
            'completed': 0,
            'failed': 0,
            'invalidated': 0,
            'rolled_back': 0,
          }),
          200,
        );
      }
      if (path == '/integration/v1/briefs/latest') {
        return http.Response('null', 200);
      }
      if (path == '/integration/v1/receipts/latest') {
        return http.Response('null', 200);
      }
      if (path == '/action-templates') {
        return http.Response(jsonEncode([]), 200);
      }
      if (path == '/retention/policies') {
        return http.Response(jsonEncode([]), 200);
      }
      if (path == '/retention/status') {
        return http.Response(
          jsonEncode({'policies': [], 'plans': [], 'receipts': []}),
          200,
        );
      }
      if (path == '/integration/v1/capabilities') {
        return http.Response(
          jsonEncode({
            'capability_version': '0.7.0',
            'capabilities': ['embedded_operations_workspace'],
            'capability_catalog': const [],
            'degraded_features': const [],
            'signing_enabled': false,
            'signing_key_count': 0,
          }),
          200,
        );
      }
      if (path == '/signing/keys') {
        return http.Response(jsonEncode([]), 200);
      }
      if (path == '/provenance/manifests') {
        return http.Response(jsonEncode([]), 200);
      }
      if (path == '/trust/alerts') {
        return http.Response(jsonEncode([]), 200);
      }
      if (path == '/retention/report') {
        return http.Response(
          jsonEncode({
            'generated_at': '2026-08-06T00:00:00Z',
            'policy_count': 0,
            'plan_count': 0,
            'receipt_count': 0,
            'enabled_policy_count': 0,
            'issues': const [],
            'summary': const {},
          }),
          200,
        );
      }
      return http.Response('{}', 404);
    });

    final controller = GaiaDashboardController(
      client: GaiaIntegrationClient(
        baseUri: Uri.parse('http://127.0.0.1:8765'),
        client: client,
      ),
    );
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: Column(
            children: [
              const Text('Reference integration host'),
              const Text('Not the New Earth Dashboard'),
              Expanded(child: GaiaDashboardView(controller: controller)),
            ],
          ),
        ),
      ),
    );
    await tester.runAsync(controller.refresh);
    await tester.pumpAndSettle();

    expect(find.text('Reference integration host'), findsOneWidget);
    expect(find.text('Not the New Earth Dashboard'), findsOneWidget);
    expect(find.text('compatible'), findsWidgets);
  });
}
