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
  Future<List<TaskRecord>> listTasks({String? projectId, String? status, String? priority, int limit = 100, int offset = 0});
  Future<TaskRecord> createTask(Map<String, dynamic> body);
  Future<TaskRecord> getTask(String taskId);
  Future<TaskRecord> updateTask(String taskId, Map<String, dynamic> body);
  Future<List<TaskHistoryRecord>> listTaskHistory(String taskId);
  Future<TaskRecord> acceptTask(String taskId);
  Future<TaskRecord> transitionTask(String taskId, Map<String, dynamic> body);
  Future<TaskRecord> cancelTask(String taskId);
  Future<TaskRecord> createTaskFromRun(String runId);
  Future<List<DraftRecord>> listDrafts({String? projectId, String? status, int limit = 100, int offset = 0});
  Future<DraftRecord> createDraft(Map<String, dynamic> body);
  Future<DraftRecord> getDraft(String draftId);
  Future<DraftRecord> reviseDraft(String draftId, Map<String, dynamic> body);
  Future<List<DraftRevisionRecord>> listDraftRevisions(String draftId);
  Future<DraftRecord> submitDraft(String draftId);
  Future<DraftRecord> rejectDraft(String draftId);
  Future<DraftRecord> supersedeDraft(String draftId);
  Future<List<ApprovalRecord>> listApprovals({String? projectId, String? status, int limit = 100, int offset = 0});
  Future<ApprovalRecord> createApproval(Map<String, dynamic> body);
  Future<ApprovalRecord> getApproval(String approvalId);
  Future<ApprovalRecord> approveApproval(String approvalId, Map<String, dynamic> body);
  Future<ApprovalRecord> rejectApproval(String approvalId, Map<String, dynamic> body);
  Future<ApprovalRecord> cancelApproval(String approvalId, Map<String, dynamic> body);
  Future<ApprovalRecord> refreshApprovalValidation(String approvalId);
  Future<DailyBriefRecord> createDailyBrief(String projectId);
  Future<List<DailyBriefRecord>> listBriefs({String? projectId, int limit = 100, int offset = 0});
  Future<DailyBriefRecord> getBrief(String briefId);
  Future<Map<String, dynamic>> integrationStatus();
  Future<List<Map<String, dynamic>>> integrationProjects();
  Future<Map<String, dynamic>> taskSummary({String? projectId});
  Future<Map<String, dynamic>> approvalSummary({String? projectId});
  Future<DailyBriefRecord?> latestBrief({String? projectId});
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

  @override
  Future<List<TaskRecord>> listTasks({String? projectId, String? status, String? priority, int limit = 100, int offset = 0}) async {
    final query = <String, String>{'limit': limit.toString(), 'offset': offset.toString()};
    if (projectId != null) query['project_id'] = projectId;
    if (status != null) query['status'] = status;
    if (priority != null) query['priority'] = priority;
    final json = await _getJson('/tasks', queryParameters: query) as List<dynamic>;
    return json.whereType<Map>().map((item) => TaskRecord.fromJson(item.cast<String, dynamic>())).toList();
  }

  @override
  Future<TaskRecord> createTask(Map<String, dynamic> body) async {
    final json = await _postJson('/tasks', body: body) as Map<String, dynamic>;
    return TaskRecord.fromJson(json);
  }

  @override
  Future<TaskRecord> getTask(String taskId) async {
    final json = await _getJson('/tasks/$taskId') as Map<String, dynamic>;
    return TaskRecord.fromJson(json);
  }

  @override
  Future<TaskRecord> updateTask(String taskId, Map<String, dynamic> body) async {
    final response = await _client
        .patch(
          _resolve('/tasks/$taskId'),
          headers: const {'content-type': 'application/json'},
          body: jsonEncode(body),
        )
        .timeout(const Duration(seconds: 20));
    final json = _decodeJsonResponse(response) as Map<String, dynamic>;
    return TaskRecord.fromJson(json);
  }

  @override
  Future<List<TaskHistoryRecord>> listTaskHistory(String taskId) async {
    final json = await _getJson('/tasks/$taskId/history') as List<dynamic>;
    return json.whereType<Map>().map((item) => TaskHistoryRecord.fromJson(item.cast<String, dynamic>())).toList();
  }

  @override
  Future<TaskRecord> acceptTask(String taskId) async {
    final json = await _postJson('/tasks/$taskId/accept') as Map<String, dynamic>;
    return TaskRecord.fromJson(json);
  }

  @override
  Future<TaskRecord> transitionTask(String taskId, Map<String, dynamic> body) async {
    final response = await _client
        .post(
          _resolve('/tasks/$taskId/transition'),
          headers: const {'content-type': 'application/json'},
          body: jsonEncode(body),
        )
        .timeout(const Duration(seconds: 20));
    final json = _decodeJsonResponse(response) as Map<String, dynamic>;
    return TaskRecord.fromJson(json);
  }

  @override
  Future<TaskRecord> cancelTask(String taskId) async {
    final json = await _postJson('/tasks/$taskId/cancel') as Map<String, dynamic>;
    return TaskRecord.fromJson(json);
  }

  @override
  Future<TaskRecord> createTaskFromRun(String runId) async {
    final json = await _postJson('/tasks/from-agent-run/$runId') as Map<String, dynamic>;
    return TaskRecord.fromJson(json);
  }

  @override
  Future<List<DraftRecord>> listDrafts({String? projectId, String? status, int limit = 100, int offset = 0}) async {
    final query = <String, String>{'limit': limit.toString(), 'offset': offset.toString()};
    if (projectId != null) query['project_id'] = projectId;
    if (status != null) query['status'] = status;
    final json = await _getJson('/drafts', queryParameters: query) as List<dynamic>;
    return json.whereType<Map>().map((item) => DraftRecord.fromJson(item.cast<String, dynamic>())).toList();
  }

  @override
  Future<DraftRecord> createDraft(Map<String, dynamic> body) async {
    final json = await _postJson('/drafts', body: body) as Map<String, dynamic>;
    return DraftRecord.fromJson(json);
  }

  @override
  Future<DraftRecord> getDraft(String draftId) async {
    final json = await _getJson('/drafts/$draftId') as Map<String, dynamic>;
    return DraftRecord.fromJson(json);
  }

  @override
  Future<DraftRecord> reviseDraft(String draftId, Map<String, dynamic> body) async {
    final response = await _client
        .patch(
          _resolve('/drafts/$draftId'),
          headers: const {'content-type': 'application/json'},
          body: jsonEncode(body),
        )
        .timeout(const Duration(seconds: 20));
    final json = _decodeJsonResponse(response) as Map<String, dynamic>;
    return DraftRecord.fromJson(json);
  }

  @override
  Future<List<DraftRevisionRecord>> listDraftRevisions(String draftId) async {
    final json = await _getJson('/drafts/$draftId/revisions') as List<dynamic>;
    return json.whereType<Map>().map((item) => DraftRevisionRecord.fromJson(item.cast<String, dynamic>())).toList();
  }

  @override
  Future<DraftRecord> submitDraft(String draftId) async {
    final json = await _postJson('/drafts/$draftId/submit-for-review') as Map<String, dynamic>;
    return DraftRecord.fromJson(json);
  }

  @override
  Future<DraftRecord> rejectDraft(String draftId) async {
    final json = await _postJson('/drafts/$draftId/reject') as Map<String, dynamic>;
    return DraftRecord.fromJson(json);
  }

  @override
  Future<DraftRecord> supersedeDraft(String draftId) async {
    final json = await _postJson('/drafts/$draftId/supersede') as Map<String, dynamic>;
    return DraftRecord.fromJson(json);
  }

  @override
  Future<List<ApprovalRecord>> listApprovals({String? projectId, String? status, int limit = 100, int offset = 0}) async {
    final query = <String, String>{'limit': limit.toString(), 'offset': offset.toString()};
    if (projectId != null) query['project_id'] = projectId;
    if (status != null) query['status'] = status;
    final json = await _getJson('/approvals', queryParameters: query) as List<dynamic>;
    return json.whereType<Map>().map((item) => ApprovalRecord.fromJson(item.cast<String, dynamic>())).toList();
  }

  @override
  Future<ApprovalRecord> createApproval(Map<String, dynamic> body) async {
    final json = await _postJson('/approvals', body: body) as Map<String, dynamic>;
    return ApprovalRecord.fromJson(json);
  }

  @override
  Future<ApprovalRecord> getApproval(String approvalId) async {
    final json = await _getJson('/approvals/$approvalId') as Map<String, dynamic>;
    return ApprovalRecord.fromJson(json);
  }

  @override
  Future<ApprovalRecord> approveApproval(String approvalId, Map<String, dynamic> body) async {
    final json = await _postJson('/approvals/$approvalId/approve', body: body) as Map<String, dynamic>;
    return ApprovalRecord.fromJson(json);
  }

  @override
  Future<ApprovalRecord> rejectApproval(String approvalId, Map<String, dynamic> body) async {
    final json = await _postJson('/approvals/$approvalId/reject', body: body) as Map<String, dynamic>;
    return ApprovalRecord.fromJson(json);
  }

  @override
  Future<ApprovalRecord> cancelApproval(String approvalId, Map<String, dynamic> body) async {
    final json = await _postJson('/approvals/$approvalId/cancel', body: body) as Map<String, dynamic>;
    return ApprovalRecord.fromJson(json);
  }

  @override
  Future<ApprovalRecord> refreshApprovalValidation(String approvalId) async {
    final json = await _postJson('/approvals/$approvalId/refresh-validation') as Map<String, dynamic>;
    return ApprovalRecord.fromJson(json);
  }

  @override
  Future<DailyBriefRecord> createDailyBrief(String projectId) async {
    final json = await _postJson('/briefs/daily', body: {'project_id': projectId}) as Map<String, dynamic>;
    return DailyBriefRecord.fromJson(json);
  }

  @override
  Future<List<DailyBriefRecord>> listBriefs({String? projectId, int limit = 100, int offset = 0}) async {
    final query = <String, String>{'limit': limit.toString(), 'offset': offset.toString()};
    if (projectId != null) query['project_id'] = projectId;
    final json = await _getJson('/briefs', queryParameters: query) as List<dynamic>;
    return json.whereType<Map>().map((item) => DailyBriefRecord.fromJson(item.cast<String, dynamic>())).toList();
  }

  @override
  Future<DailyBriefRecord> getBrief(String briefId) async {
    final json = await _getJson('/briefs/$briefId') as Map<String, dynamic>;
    return DailyBriefRecord.fromJson(json);
  }

  @override
  Future<Map<String, dynamic>> integrationStatus() async {
    return (await _getJson('/integration/v1/status') as Map).cast<String, dynamic>();
  }

  @override
  Future<List<Map<String, dynamic>>> integrationProjects() async {
    final json = await _getJson('/integration/v1/projects') as List<dynamic>;
    return json.whereType<Map>().map((item) => item.cast<String, dynamic>()).toList();
  }

  @override
  Future<Map<String, dynamic>> taskSummary({String? projectId}) async {
    final json = await _getJson('/integration/v1/tasks/summary', queryParameters: projectId == null ? null : {'project_id': projectId}) as Map;
    return json.cast<String, dynamic>();
  }

  @override
  Future<Map<String, dynamic>> approvalSummary({String? projectId}) async {
    final json = await _getJson('/integration/v1/approvals/summary', queryParameters: projectId == null ? null : {'project_id': projectId}) as Map;
    return json.cast<String, dynamic>();
  }

  @override
  Future<DailyBriefRecord?> latestBrief({String? projectId}) async {
    final json = await _getJson('/integration/v1/briefs/latest', queryParameters: projectId == null ? null : {'project_id': projectId});
    if (json == null) {
      return null;
    }
    return DailyBriefRecord.fromJson((json as Map).cast<String, dynamic>());
  }

  void close() {
    _client.close();
  }
}
