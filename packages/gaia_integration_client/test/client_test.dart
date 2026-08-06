import 'dart:convert';

import 'package:gaia_integration_client/gaia_integration_client.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:test/test.dart';

void main() {
  test('parses compatibility and summaries', () async {
    final client = MockClient((request) async {
      final path = request.url.path;
      if (path == '/health') {
        return http.Response(
          jsonEncode({
            'status': 'ok',
            'version': '0.5.0',
            'database_path': 'data/gaia.db',
            'fts5_available': true,
          }),
          200,
        );
      }
      if (path == '/integration/v1/compatibility') {
        return http.Response(
          jsonEncode({
            'backend_product_version': '0.6.0',
            'minimum_supported_api_version': '0.6.0',
            'maximum_tested_api_version': '0.6.0',
            'integration_contract_version': 'gaia-v2',
            'client_package_version': '0.6.0',
            'backend_version': '0.6.0',
            'status': 'compatible_with_warnings',
            'loopback_only': true,
            'capabilities': ['actions', 'receipts', 'retention_policies'],
            'degraded_features': ['offline_packages'],
            'deprecation_warnings': ['v1 contract is deprecated'],
          }),
          200,
        );
      }
      if (path == '/integration/v1/actions/summary') {
        return http.Response(
          jsonEncode({
            'project_id': 'sample',
            'total': 1,
            'proposed': 0,
            'awaiting_approval': 0,
            'approved': 0,
            'completed': 1,
            'failed': 0,
            'invalidated': 0,
            'rolled_back': 0,
          }),
          200,
        );
      }
      if (path == '/integration/v1/receipts/latest') {
        return http.Response(
          jsonEncode({
            'receipt_id': 'receipt-1',
            'action_id': 'action-1',
            'manifest_id': 'manifest-1',
            'manifest_version': 1,
            'target_path': 'workspace/approved_outputs/demo.md',
            'resulting_hash': 'abc',
            'timestamp': '2026-08-05T00:00:00Z',
            'chain_id': 'manifest-1',
            'chain_sequence': 1,
            'previous_receipt_hash': null,
            'receipt_content_hash': 'hash-1',
            'verification_status': 'valid',
          }),
          200,
        );
      }
      if (path == '/receipts/receipt-1/verify') {
        return http.Response(
          jsonEncode({
            'receipt_id': 'receipt-1',
            'chain_id': 'manifest-1',
            'chain_sequence': 1,
            'status': 'valid',
            'previous_receipt_hash': null,
            'receipt_content_hash': 'hash-1',
            'warnings': const [],
          }),
          200,
        );
      }
      return http.Response('{}', 404);
    });

    final gaia = GaiaIntegrationClient(baseUri: Uri.parse('http://127.0.0.1:8765'), client: client);

    final health = await gaia.health();
    expect(health.version, '0.5.0');

    final compatibility = await gaia.compatibility();
    expect(compatibility.integrationContractVersion, 'gaia-v2');
    expect(compatibility.status, 'compatible_with_warnings');
    expect(compatibility.capabilities, contains('actions'));

    final actionSummary = await gaia.actionSummary(projectId: 'sample');
    expect(actionSummary.completed, 1);

    final receipt = await gaia.latestReceipt();
    expect(receipt?.receiptId, 'receipt-1');

    final verification = await gaia.verifyReceipt('receipt-1');
    expect(verification.status, 'valid');
  });
}
