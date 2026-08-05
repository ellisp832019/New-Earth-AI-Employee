import 'dart:convert';

import 'package:http/http.dart' as http;

import 'models.dart';

abstract class GaiaBackendApi {
  Future<HealthResponse> health();
  Future<List<ProjectConfig>> listProjects();
  Future<ProjectConfig> getProject(String projectId);
  Future<Map<String, dynamic>> scanProject(String projectId);
  Future<List<RepositorySnapshot>> listSnapshots(String projectId);
  Future<RepositorySnapshot> latestSnapshot(String projectId);
  Future<List<DocumentRecord>> listDocuments(String projectId);
  Future<List<SearchResult>> search(String projectId, String query, {int limit = 20});
  Future<String> foundationReport(String projectId, {String format = 'markdown'});
  Future<List<Map<String, dynamic>>> listAuditEvents({int limit = 100});
  Future<List<ModelStatus>> listModelStatus();
  Future<AskResponse> ask(AskRequestBody request, {http.Client? client});
  Future<List<AgentRunRecord>> listAgentRuns({int limit = 100});
  Future<AgentRunRecord> getAgentRun(String runId);
}

class GaiaApiError implements Exception {
  GaiaApiError(this.message, {this.statusCode});

  final String message;
  final int? statusCode;

  @override
  String toString() => statusCode == null ? message : '[$statusCode] $message';
}

class GaiaApiClient implements GaiaBackendApi {
  GaiaApiClient({
    required this.baseUri,
    http.Client? client,
    this.responseLimitBytes = 2 * 1024 * 1024,
  }) : _client = client ?? http.Client();

  final Uri baseUri;
  final http.Client _client;
  final int responseLimitBytes;

  Uri _resolve(String path) => baseUri.resolve(path);

  Future<dynamic> _getJson(String path, {Map<String, String>? queryParameters}) async {
    final uri = _resolve(path).replace(queryParameters: queryParameters);
    final response = await _client.get(uri).timeout(const Duration(seconds: 10));
    return _decodeJsonResponse(response);
  }

  Future<dynamic> _postJson(String path, {Object? body}) async {
    final response = await _client
        .post(
          _resolve(path),
          headers: const {'content-type': 'application/json'},
          body: body == null ? null : jsonEncode(body),
        )
        .timeout(const Duration(seconds: 20));
    return _decodeJsonResponse(response);
  }

  dynamic _decodeJsonResponse(http.Response response) {
    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw GaiaApiError(_safeMessage(response.body), statusCode: response.statusCode);
    }
    if (response.bodyBytes.length > responseLimitBytes) {
      throw GaiaApiError('Response exceeded the configured size limit.');
    }
    if (response.body.isEmpty) {
      return null;
    }
    return jsonDecode(utf8.decode(response.bodyBytes));
  }

  String _safeMessage(String body) {
    try {
      final decoded = jsonDecode(body);
      if (decoded is Map && decoded['detail'] != null) {
        return decoded['detail'].toString();
      }
    } catch (_) {
      // Fall back to the raw body below.
    }
    return body.isEmpty ? 'Backend request failed.' : body;
  }

  @override
  Future<HealthResponse> health() async {
    final json = await _getJson('/health') as Map<String, dynamic>;
    return HealthResponse.fromJson(json);
  }

  @override
  Future<List<ProjectConfig>> listProjects() async {
    final json = await _getJson('/projects') as List<dynamic>;
    return json.whereType<Map>().map((item) => ProjectConfig.fromJson(item.cast<String, dynamic>())).toList();
  }

  @override
  Future<ProjectConfig> getProject(String projectId) async {
    final json = await _getJson('/projects/$projectId') as Map<String, dynamic>;
    return ProjectConfig.fromJson(json);
  }

  @override
  Future<Map<String, dynamic>> scanProject(String projectId) async {
    final json = await _postJson('/projects/$projectId/scan') as Map<String, dynamic>;
    return json;
  }

  @override
  Future<List<RepositorySnapshot>> listSnapshots(String projectId) async {
    final json = await _getJson('/projects/$projectId/snapshots') as List<dynamic>;
    return json.whereType<Map>().map((item) => RepositorySnapshot.fromJson(item.cast<String, dynamic>())).toList();
  }

  @override
  Future<RepositorySnapshot> latestSnapshot(String projectId) async {
    final json = await _getJson('/projects/$projectId/snapshots/latest') as Map<String, dynamic>;
    return RepositorySnapshot.fromJson(json);
  }

  @override
  Future<List<DocumentRecord>> listDocuments(String projectId) async {
    final json = await _getJson('/projects/$projectId/documents') as List<dynamic>;
    return json.whereType<Map>().map((item) => DocumentRecord.fromJson(item.cast<String, dynamic>())).toList();
  }

  @override
  Future<List<SearchResult>> search(String projectId, String query, {int limit = 20}) async {
    final json = await _getJson(
      '/projects/$projectId/search',
      queryParameters: <String, String>{'q': query, 'limit': limit.toString()},
    ) as List<dynamic>;
    return json.whereType<Map>().map((item) => SearchResult.fromJson(item.cast<String, dynamic>())).toList();
  }

  @override
  Future<String> foundationReport(String projectId, {String format = 'markdown'}) async {
    final uri = _resolve('/projects/$projectId/reports/foundation').replace(queryParameters: <String, String>{'format': format});
    final response = await _client.post(uri).timeout(const Duration(seconds: 20));
    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw GaiaApiError(_safeMessage(response.body), statusCode: response.statusCode);
    }
    return utf8.decode(response.bodyBytes);
  }

  @override
  Future<List<Map<String, dynamic>>> listAuditEvents({int limit = 100}) async {
    final json = await _getJson('/audit/events', queryParameters: <String, String>{'limit': limit.toString()}) as List<dynamic>;
    return json.whereType<Map>().map((item) => item.cast<String, dynamic>()).toList();
  }

  @override
  Future<List<ModelStatus>> listModelStatus() async {
    final json = await _getJson('/models/status') as List<dynamic>;
    return json.whereType<Map>().map((item) => ModelStatus.fromJson(item.cast<String, dynamic>())).toList();
  }

  @override
  Future<AskResponse> ask(AskRequestBody request, {http.Client? client}) async {
    final activeClient = client ?? _client;
    final response = await activeClient
        .post(
          _resolve('/agent/ask'),
          headers: const {'content-type': 'application/json'},
          body: jsonEncode(request.toJson()),
        )
        .timeout(const Duration(seconds: 40));
    final json = _decodeJsonResponse(response) as Map<String, dynamic>;
    return AskResponse.fromJson(json);
  }

  @override
  Future<List<AgentRunRecord>> listAgentRuns({int limit = 100}) async {
    final json = await _getJson('/agent/runs', queryParameters: <String, String>{'limit': limit.toString()}) as List<dynamic>;
    return json.whereType<Map>().map((item) => AgentRunRecord.fromJson(item.cast<String, dynamic>())).toList();
  }

  @override
  Future<AgentRunRecord> getAgentRun(String runId) async {
    final json = await _getJson('/agent/runs/$runId') as Map<String, dynamic>;
    return AgentRunRecord.fromJson(json);
  }

  void close() {
    _client.close();
  }
}
