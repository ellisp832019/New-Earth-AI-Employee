import 'dart:convert';

import 'package:http/http.dart' as http;

import 'models.dart';

class GaiaIntegrationClient {
  GaiaIntegrationClient({
    required Uri baseUri,
    http.Client? client,
    Duration timeout = const Duration(seconds: 10),
    this.responseLimitBytes = 2 * 1024 * 1024,
  })  : baseUri = baseUri,
        _client = client ?? http.Client(),
        timeout = timeout;

  final Uri baseUri;
  final http.Client _client;
  final Duration timeout;
  final int responseLimitBytes;

  Uri _resolve(String path) => baseUri.resolve(path);

  Future<dynamic> _getJson(String path, {Map<String, String>? queryParameters}) async {
    final uri = _resolve(path).replace(queryParameters: queryParameters);
    final response = await _client.get(uri).timeout(timeout);
    return _decode(response);
  }

  Future<dynamic> _postJson(String path, {Object? body, Map<String, String>? queryParameters}) async {
    final uri = _resolve(path).replace(queryParameters: queryParameters);
    final response = await _client
        .post(
          uri,
          headers: const {'content-type': 'application/json'},
          body: body == null ? null : jsonEncode(body),
        )
        .timeout(timeout);
    return _decode(response);
  }

  dynamic _decode(http.Response response) {
    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw GaiaClientError(_message(response.body), statusCode: response.statusCode);
    }
    if (response.bodyBytes.length > responseLimitBytes) {
      throw GaiaClientError('Response exceeded the configured size limit.');
    }
    if (response.body.isEmpty) {
      return null;
    }
    return jsonDecode(utf8.decode(response.bodyBytes));
  }

  String _message(String body) {
    try {
      final decoded = jsonDecode(body);
      if (decoded is Map && decoded['detail'] != null) {
        return decoded['detail'].toString();
      }
    } catch (_) {
      // Fall through to the raw body below.
    }
    return body.isEmpty ? 'Request failed.' : body;
  }

  Future<GaiaHealth> health() async {
    final json = await _getJson('/health') as Map<String, dynamic>;
    return GaiaHealth.fromJson(json);
  }

  Future<GaiaCompatibility> compatibility() async {
    final json = await _getJson('/integration/v1/compatibility') as Map<String, dynamic>;
    return GaiaCompatibility.fromJson(json);
  }

  Future<List<GaiaProjectSummary>> projects() async {
    final json = await _getJson('/integration/v1/projects') as List<dynamic>;
    return json.whereType<Map>().map((item) => GaiaProjectSummary.fromJson(item.cast<String, dynamic>())).toList();
  }

  Future<GaiaSummary> taskSummary({String? projectId}) async {
    final json = await _getJson('/integration/v1/tasks/summary', queryParameters: stringQuery({'project_id': projectId})) as Map<String, dynamic>;
    return GaiaSummary.fromJson(json);
  }

  Future<GaiaSummary> approvalSummary({String? projectId}) async {
    final json = await _getJson('/integration/v1/approvals/summary', queryParameters: stringQuery({'project_id': projectId})) as Map<String, dynamic>;
    return GaiaSummary.fromJson(json);
  }

  Future<GaiaActionSummary> actionSummary({String? projectId}) async {
    final json = await _getJson('/integration/v1/actions/summary', queryParameters: stringQuery({'project_id': projectId})) as Map<String, dynamic>;
    return GaiaActionSummary.fromJson(json);
  }

  Future<GaiaDailyBrief?> latestBrief({String? projectId}) async {
    final json = await _getJson('/integration/v1/briefs/latest', queryParameters: stringQuery({'project_id': projectId}));
    if (json == null) {
      return null;
    }
    return GaiaDailyBrief.fromJson((json as Map).cast<String, dynamic>());
  }

  Future<List<GaiaExecutionReceipt>> receipts() async {
    final json = await _getJson('/receipts') as List<dynamic>;
    return json.whereType<Map>().map((item) => GaiaExecutionReceipt.fromJson(item.cast<String, dynamic>())).toList();
  }

  Future<GaiaExecutionReceipt?> latestReceipt() async {
    final json = await _getJson('/integration/v1/receipts/latest');
    if (json == null) {
      return null;
    }
    return GaiaExecutionReceipt.fromJson((json as Map).cast<String, dynamic>());
  }

  Future<Map<String, dynamic>> status() async {
    final json = await _getJson('/integration/v1/status') as Map<String, dynamic>;
    return json;
  }

  Future<Map<String, dynamic>> createAction(Map<String, dynamic> body) async {
    return (await _postJson('/actions', body: body)) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> requestApproval(String actionId) async {
    return (await _postJson('/actions/$actionId/request-approval')) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> approveAction(String actionId) async {
    return (await _postJson('/actions/$actionId/approve')) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> executeAction(String actionId, {required bool confirm}) async {
    return (await _postJson('/actions/$actionId/execute', queryParameters: {'confirm': confirm.toString()})) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> rollbackAction(String actionId, {required bool confirm}) async {
    return (await _postJson('/actions/$actionId/rollback', queryParameters: {'confirm': confirm.toString()})) as Map<String, dynamic>;
  }
}
