import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gaia_dashboard_module/gaia_dashboard_module.dart';
import 'package:gaia_integration_client/gaia_integration_client.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

void main() {
  testWidgets('renders compatibility and trust state', (tester) async {
    final client = MockClient((request) async {
      final path = request.url.path;
      if (path == '/integration/v1/compatibility') {
        return http.Response(
          jsonEncode({
            'backend_product_version': '0.6.0',
            'minimum_supported_api_version': '0.6.0',
            'maximum_tested_api_version': '0.6.0',
            'integration_contract_version': 'gaia-v2',
            'client_package_version': '0.6.0',
            'backend_version': '0.6.0',
            'status': 'compatible',
            'loopback_only': true,
            'capabilities': ['actions', 'receipts'],
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
        return http.Response(jsonEncode({'project_id': 'demo', 'total': 0, 'active': 0, 'pending': 0, 'completed': 0}), 200);
      }
      if (path == '/integration/v1/approvals/summary') {
        return http.Response(jsonEncode({'project_id': 'demo', 'total': 0, 'active': 0, 'pending': 0, 'completed': 0}), 200);
      }
      if (path == '/integration/v1/actions/summary') {
        return http.Response(jsonEncode({'project_id': 'demo', 'total': 0, 'proposed': 0, 'awaiting_approval': 0, 'approved': 0, 'completed': 0, 'failed': 0, 'invalidated': 0, 'rolled_back': 0}), 200);
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
        return http.Response(jsonEncode({'policies': [], 'plans': [], 'receipts': []}), 200);
      }
      return http.Response('{}', 404);
    });

    final controller = GaiaDashboardController(
      client: GaiaIntegrationClient(baseUri: Uri.parse('http://127.0.0.1:8765'), client: client),
    );

    await tester.pumpWidget(MaterialApp(home: Scaffold(body: GaiaDashboardView(controller: controller))));
    await tester.pump();
    await tester.runAsync(controller.refresh);
    await tester.pumpAndSettle();

    expect(find.text('Compatibility'), findsWidgets);
    expect(find.text('Trust'), findsWidgets);
    expect(find.text('compatible'), findsOneWidget);
  });
}
