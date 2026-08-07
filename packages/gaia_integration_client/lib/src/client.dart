import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:http/http.dart' as http;

import 'models.dart';

class GaiaIntegrationClient {
  GaiaIntegrationClient({
    required Uri baseUri,
    http.Client? client,
    Duration timeout = const Duration(seconds: 10),
    this.responseLimitBytes = 2 * 1024 * 1024,
  }) : baseUri = baseUri,
       _client = client ?? http.Client(),
       timeout = timeout;

  final Uri baseUri;
  final http.Client _client;
  final Duration timeout;
  final int responseLimitBytes;
  final Map<String, _CachedJson> _cache = <String, _CachedJson>{};

  Uri _resolve(String path) => baseUri.resolve(path);

  Future<dynamic> _getJson(
    String path, {
    Map<String, String>? queryParameters,
    bool allowStaleCache = true,
  }) async {
    final uri = _resolve(path).replace(queryParameters: queryParameters);
    final cacheKey = _cacheKey(uri);
    return _fetchJson(
      cacheKey,
      () => _client.get(uri).timeout(timeout),
      allowStale: allowStaleCache,
    );
  }

  Future<dynamic> _postJson(
    String path, {
    Object? body,
    Map<String, String>? queryParameters,
  }) async {
    final uri = _resolve(path).replace(queryParameters: queryParameters);
    return _fetchJson(
      _cacheKey(uri),
      () => _client
          .post(
            uri,
            headers: const {'content-type': 'application/json'},
            body: body == null ? null : jsonEncode(body),
          )
          .timeout(timeout),
      allowStale: false,
    );
  }

  Future<dynamic> _fetchJson(
    String cacheKey,
    Future<http.Response> Function() request, {
    required bool allowStale,
  }) async {
    Object? lastError;
    for (var attempt = 0; attempt < 3; attempt++) {
      try {
        final response = await request();
        final decoded = _decode(response);
        if (decoded != null) {
          _cache[cacheKey] = _CachedJson(decoded, DateTime.now());
        }
        return decoded;
      } on TimeoutException catch (error) {
        lastError = error;
      } on SocketException catch (error) {
        lastError = error;
      } on http.ClientException catch (error) {
        lastError = error;
      }
      if (attempt < 2) {
        await Future<void>.delayed(Duration(milliseconds: 150 * (attempt + 1)));
      }
    }
    if (allowStale && _cache.containsKey(cacheKey)) {
      return _cache[cacheKey]!.value;
    }
    if (lastError != null) {
      throw GaiaClientError(lastError.toString());
    }
    throw GaiaClientError('Request failed.');
  }

  dynamic _decode(http.Response response) {
    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw GaiaClientError(
        _message(response.body),
        statusCode: response.statusCode,
      );
    }
    if (response.bodyBytes.length > responseLimitBytes) {
      throw GaiaClientError('Response exceeded the configured size limit.');
    }
    if (response.body.isEmpty) {
      return null;
    }
    return jsonDecode(utf8.decode(response.bodyBytes));
  }

  String _cacheKey(Uri uri) => uri.toString();

  String _message(String body) {
    try {
      final decoded = jsonDecode(body);
      if (decoded is Map && decoded['detail'] != null) {
        final detail = decoded['detail'];
        if (detail is Map && detail['message'] != null) {
          return detail['message'].toString();
        }
        return detail.toString();
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
    final json =
        await _getJson('/integration/v1/compatibility') as Map<String, dynamic>;
    return GaiaCompatibility.fromJson(json);
  }

  Future<Map<String, dynamic>> capabilityPayload() async {
    final json =
        await _getJson('/integration/v1/capabilities') as Map<String, dynamic>;
    return json;
  }

  Future<Map<String, dynamic>> projectOfficerCapabilities({
    bool allowStaleCache = true,
  }) async {
    return (await _getJson(
          '/integration/v1/project-officer/capabilities',
          allowStaleCache: allowStaleCache,
        ))
        as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> projectOfficerPortfolio({
    bool allowStaleCache = true,
  }) async {
    return (await _getJson(
          '/integration/v1/project-officer/portfolio',
          allowStaleCache: allowStaleCache,
        ))
        as Map<String, dynamic>;
  }

  Future<List<Map<String, dynamic>>> projectOfficerProjects() async {
    final json =
        await _getJson('/integration/v1/project-officer/projects')
            as List<dynamic>;
    return json
        .whereType<Map>()
        .map((item) => item.cast<String, dynamic>())
        .toList();
  }

  Future<Map<String, dynamic>> projectOfficerProjectHealth(
    String projectId, {
    bool allowStaleCache = true,
  }) async {
    return (await _getJson(
          '/integration/v1/project-officer/projects/$projectId/health',
          allowStaleCache: allowStaleCache,
        ))
        as Map<String, dynamic>;
  }

  Future<List<Map<String, dynamic>>> projectOfficerProjectHealthSnapshots(
    String projectId, {
    int limit = 100,
    int offset = 0,
    bool allowStaleCache = true,
  }) async {
    final json =
        await _getJson(
              '/integration/v1/project-officer/projects/$projectId/health/snapshots',
              queryParameters: stringQuery({'limit': limit, 'offset': offset}),
              allowStaleCache: allowStaleCache,
            )
            as List<dynamic>;
    return json
        .whereType<Map>()
        .map((item) => item.cast<String, dynamic>())
        .toList();
  }

  Future<Map<String, dynamic>> projectOfficerHealthSnapshot(
    String snapshotId, {
    bool allowStaleCache = true,
  }) async {
    return (await _getJson(
          '/integration/v1/project-officer/health-snapshots/$snapshotId',
          allowStaleCache: allowStaleCache,
        ))
        as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> projectOfficerChangePortfolio({
    bool allowStaleCache = true,
  }) async {
    return (await _getJson(
          '/integration/v1/project-officer/changes/portfolio',
          allowStaleCache: allowStaleCache,
        ))
        as Map<String, dynamic>;
  }

  Future<List<Map<String, dynamic>>> projectOfficerChangeFindings(
    String projectId, {
    String? severity,
    String? direction,
    String? changeType,
    String? status,
    int limit = 100,
    int offset = 0,
    bool allowStaleCache = true,
  }) async {
    final json =
        await _getJson(
              '/integration/v1/project-officer/projects/$projectId/changes/findings',
              queryParameters: stringQuery({
                'severity': severity,
                'direction': direction,
                'change_type': changeType,
                'status': status,
                'limit': limit,
                'offset': offset,
              }),
              allowStaleCache: allowStaleCache,
            )
            as List<dynamic>;
    return json
        .whereType<Map>()
        .map((item) => item.cast<String, dynamic>())
        .toList();
  }

  Future<Map<String, dynamic>> projectOfficerChangeFinding(
    String findingId, {
    bool allowStaleCache = true,
  }) async {
    return (await _getJson(
          '/integration/v1/project-officer/change-findings/$findingId',
          allowStaleCache: allowStaleCache,
        ))
        as Map<String, dynamic>;
  }

  Future<List<Map<String, dynamic>>> projectOfficerRecentChangeFindings({
    String? projectId,
    int limit = 100,
    bool allowStaleCache = true,
  }) async {
    final json =
        await _getJson(
              '/integration/v1/project-officer/changes/recent',
              queryParameters: stringQuery({
                'project_id': projectId,
                'limit': limit,
              }),
              allowStaleCache: allowStaleCache,
            )
            as List<dynamic>;
    return json
        .whereType<Map>()
        .map((item) => item.cast<String, dynamic>())
        .toList();
  }

  Future<Map<String, dynamic>> projectOfficerRecommendationPortfolio({
    bool allowStaleCache = true,
  }) async {
    return (await _getJson(
          '/integration/v1/project-officer/recommendations/portfolio',
          allowStaleCache: allowStaleCache,
        ))
        as Map<String, dynamic>;
  }

  Future<List<Map<String, dynamic>>> projectOfficerRecommendations({
    String? projectId,
    String? priorityTier,
    String? lifecycleState,
    bool blockedOnly = false,
    int limit = 100,
    int offset = 0,
    bool allowStaleCache = true,
  }) async {
    final json =
        await _getJson(
              '/integration/v1/project-officer/recommendations',
              queryParameters: stringQuery({
                'project_id': projectId,
                'priority_tier': priorityTier,
                'lifecycle_state': lifecycleState,
                'blocked_only': blockedOnly,
                'limit': limit,
                'offset': offset,
              }),
              allowStaleCache: allowStaleCache,
            )
            as List<dynamic>;
    return json
        .whereType<Map>()
        .map((item) => item.cast<String, dynamic>())
        .toList();
  }

  Future<Map<String, dynamic>> projectOfficerRecommendation(
    String recommendationId, {
    bool allowStaleCache = true,
  }) async {
    return (await _getJson(
          '/integration/v1/project-officer/recommendations/$recommendationId',
          allowStaleCache: allowStaleCache,
        ))
        as Map<String, dynamic>;
  }

  Future<List<Map<String, dynamic>>> projectOfficerWorkPackages({
    String? projectId,
    String? approvalState,
    String? stalenessState,
    String? riskClassification,
    int limit = 100,
    int offset = 0,
    bool allowStaleCache = true,
  }) async {
    final json =
        await _getJson(
              '/integration/v1/project-officer/work-packages',
              queryParameters: stringQuery({
                'project_id': projectId,
                'approval_state': approvalState,
                'staleness_state': stalenessState,
                'risk_classification': riskClassification,
                'limit': limit,
                'offset': offset,
              }),
              allowStaleCache: allowStaleCache,
            )
            as List<dynamic>;
    return json
        .whereType<Map>()
        .map((item) => item.cast<String, dynamic>())
        .toList();
  }

  Future<Map<String, dynamic>> projectOfficerWorkPackage(
    String workPackageId, {
    bool allowStaleCache = true,
  }) async {
    return (await _getJson(
          '/integration/v1/project-officer/work-packages/$workPackageId',
          allowStaleCache: allowStaleCache,
        ))
        as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> projectOfficerWorkPackageSummary(
    String workPackageId, {
    bool allowStaleCache = true,
  }) async {
    return (await _getJson(
          '/integration/v1/project-officer/work-packages/$workPackageId/summary',
          allowStaleCache: allowStaleCache,
        ))
        as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> projectOfficerWorkPackagePrompt(
    String workPackageId, {
    int? revisionNumber,
    bool allowStaleCache = true,
  }) async {
    return (await _getJson(
          '/integration/v1/project-officer/work-packages/$workPackageId/prompt',
          queryParameters: stringQuery({'revision_number': revisionNumber}),
          allowStaleCache: allowStaleCache,
        ))
        as Map<String, dynamic>;
  }

  Future<List<Map<String, dynamic>>> projectOfficerWorkPackageRevisions(
    String workPackageId, {
    bool allowStaleCache = true,
  }) async {
    final json =
        await _getJson(
              '/integration/v1/project-officer/work-packages/$workPackageId/revisions',
              allowStaleCache: allowStaleCache,
            )
            as List<dynamic>;
    return json
        .whereType<Map>()
        .map((item) => item.cast<String, dynamic>())
        .toList();
  }

  Future<Map<String, dynamic>> projectOfficerWorkPackageRevision(
    String revisionId, {
    bool allowStaleCache = true,
  }) async {
    return (await _getJson(
          '/integration/v1/project-officer/work-package-revisions/$revisionId',
          allowStaleCache: allowStaleCache,
        ))
        as Map<String, dynamic>;
  }

  Future<List<Map<String, dynamic>>> projectOfficerWorkPackageApprovalDecisions(
    String workPackageId, {
    bool allowStaleCache = true,
  }) async {
    final json =
        await _getJson(
              '/integration/v1/project-officer/work-packages/$workPackageId/approval-decisions',
              allowStaleCache: allowStaleCache,
            )
            as List<dynamic>;
    return json
        .whereType<Map>()
        .map((item) => item.cast<String, dynamic>())
        .toList();
  }

  Future<List<Map<String, dynamic>>> projectOfficerWorkPackageHandoffs(
    String workPackageId, {
    bool allowStaleCache = true,
  }) async {
    final json =
        await _getJson(
              '/integration/v1/project-officer/work-packages/$workPackageId/handoffs',
              allowStaleCache: allowStaleCache,
            )
            as List<dynamic>;
    return json
        .whereType<Map>()
        .map((item) => item.cast<String, dynamic>())
        .toList();
  }

  Future<List<Map<String, dynamic>>> projectOfficerWorkPackageOutcomes(
    String workPackageId, {
    bool allowStaleCache = true,
  }) async {
    final json =
        await _getJson(
              '/integration/v1/project-officer/work-packages/$workPackageId/outcomes',
              allowStaleCache: allowStaleCache,
            )
            as List<dynamic>;
    return json
        .whereType<Map>()
        .map((item) => item.cast<String, dynamic>())
        .toList();
  }

  Future<Map<String, dynamic>> projectOfficerSubmitForReview(
    String workPackageId, {
    required int revisionNumber,
    String actor = 'manual',
    String? humanNote,
  }) async {
    return (await _postJson(
          '/integration/v1/project-officer/work-packages/$workPackageId/submit-for-review',
          body: {
            'revision_number': revisionNumber,
            'actor': actor,
            'human_note': humanNote,
          },
        ))
        as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> projectOfficerApprove(
    String workPackageId, {
    required int revisionNumber,
    String actor = 'manual',
    String? humanNote,
  }) async {
    return (await _postJson(
          '/integration/v1/project-officer/work-packages/$workPackageId/approve',
          body: {
            'revision_number': revisionNumber,
            'actor': actor,
            'human_note': humanNote,
          },
        ))
        as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> projectOfficerReject(
    String workPackageId, {
    required int revisionNumber,
    String actor = 'manual',
    String? humanNote,
  }) async {
    return (await _postJson(
          '/integration/v1/project-officer/work-packages/$workPackageId/reject',
          body: {
            'revision_number': revisionNumber,
            'actor': actor,
            'human_note': humanNote,
          },
        ))
        as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> projectOfficerExpire(
    String workPackageId, {
    String reason = 'manual expiry',
  }) async {
    return (await _postJson(
          '/integration/v1/project-officer/work-packages/$workPackageId/expire',
          body: reason,
        ))
        as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> projectOfficerHandoff(
    String workPackageId, {
    required int revisionNumber,
    String approvedBy = 'manual',
    String nextManualAction = 'Copy the approved Codex prompt into Codex.',
    String rollbackReference =
        'Return to the recorded baseline commit or last approved revision.',
  }) async {
    return (await _postJson(
          '/integration/v1/project-officer/work-packages/$workPackageId/handoff',
          body: {
            'revision_number': revisionNumber,
            'approved_by': approvedBy,
            'next_manual_action': nextManualAction,
            'rollback_reference': rollbackReference,
          },
        ))
        as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> projectOfficerOutcome(
    String workPackageId, {
    required int revisionNumber,
    required String outcome,
    String actor = 'manual',
    String? note,
  }) async {
    return (await _postJson(
          '/integration/v1/project-officer/work-packages/$workPackageId/outcome',
          body: {
            'revision_number': revisionNumber,
            'outcome': outcome,
            'actor': actor,
            'note': note,
          },
        ))
        as Map<String, dynamic>;
  }

  Future<List<GaiaProjectSummary>> projects() async {
    final json = await _getJson('/integration/v1/projects') as List<dynamic>;
    return json
        .whereType<Map>()
        .map(
          (item) => GaiaProjectSummary.fromJson(item.cast<String, dynamic>()),
        )
        .toList();
  }

  Future<GaiaSummary> taskSummary({String? projectId}) async {
    final json =
        await _getJson(
              '/integration/v1/tasks/summary',
              queryParameters: stringQuery({'project_id': projectId}),
            )
            as Map<String, dynamic>;
    return GaiaSummary.fromJson(json);
  }

  Future<GaiaSummary> approvalSummary({String? projectId}) async {
    final json =
        await _getJson(
              '/integration/v1/approvals/summary',
              queryParameters: stringQuery({'project_id': projectId}),
            )
            as Map<String, dynamic>;
    return GaiaSummary.fromJson(json);
  }

  Future<GaiaActionSummary> actionSummary({String? projectId}) async {
    final json =
        await _getJson(
              '/integration/v1/actions/summary',
              queryParameters: stringQuery({'project_id': projectId}),
            )
            as Map<String, dynamic>;
    return GaiaActionSummary.fromJson(json);
  }

  Future<GaiaDailyBrief?> latestBrief({String? projectId}) async {
    final json = await _getJson(
      '/integration/v1/briefs/latest',
      queryParameters: stringQuery({'project_id': projectId}),
    );
    if (json == null) {
      return null;
    }
    return GaiaDailyBrief.fromJson((json as Map).cast<String, dynamic>());
  }

  Future<List<GaiaExecutionReceipt>> receipts() async {
    final json = await _getJson('/receipts') as List<dynamic>;
    return json
        .whereType<Map>()
        .map(
          (item) => GaiaExecutionReceipt.fromJson(item.cast<String, dynamic>()),
        )
        .toList();
  }

  Future<GaiaExecutionReceipt?> latestReceipt() async {
    final json = await _getJson('/integration/v1/receipts/latest');
    if (json == null) {
      return null;
    }
    return GaiaExecutionReceipt.fromJson((json as Map).cast<String, dynamic>());
  }

  Future<Map<String, dynamic>> status() async {
    final json =
        await _getJson('/integration/v1/status') as Map<String, dynamic>;
    return json;
  }

  Future<Map<String, dynamic>> createAction(Map<String, dynamic> body) async {
    return (await _postJson('/actions', body: body)) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> requestApproval(String actionId) async {
    return (await _postJson('/actions/$actionId/request-approval'))
        as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> approveAction(String actionId) async {
    return (await _postJson('/actions/$actionId/approve'))
        as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> executeAction(
    String actionId, {
    required bool confirm,
  }) async {
    return (await _postJson(
          '/actions/$actionId/execute',
          queryParameters: {'confirm': confirm.toString()},
        ))
        as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> rollbackAction(
    String actionId, {
    required bool confirm,
  }) async {
    return (await _postJson(
          '/actions/$actionId/rollback',
          queryParameters: {'confirm': confirm.toString()},
        ))
        as Map<String, dynamic>;
  }

  Future<List<GaiaActionTemplate>> listActionTemplates() async {
    final json = await _getJson('/action-templates') as List<dynamic>;
    return json
        .whereType<Map>()
        .map(
          (item) => GaiaActionTemplate.fromJson(item.cast<String, dynamic>()),
        )
        .toList();
  }

  Future<GaiaActionTemplate> getActionTemplate(String templateId) async {
    final json =
        await _getJson('/action-templates/$templateId') as Map<String, dynamic>;
    return GaiaActionTemplate.fromJson(json);
  }

  Future<Map<String, dynamic>> proposeActionTemplate(
    String templateId,
    Map<String, dynamic> body,
  ) async {
    return (await _postJson(
          '/action-templates/$templateId/propose',
          body: body,
        ))
        as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> previewActionTemplate(
    String templateId,
    Map<String, dynamic> body,
  ) async {
    return (await _postJson(
          '/action-templates/$templateId/preview',
          body: body,
        ))
        as Map<String, dynamic>;
  }

  Future<GaiaReceiptVerification> verifyReceipt(String receiptId) async {
    final json =
        await _getJson('/receipts/$receiptId/verify') as Map<String, dynamic>;
    return GaiaReceiptVerification.fromJson(json);
  }

  Future<Map<String, dynamic>> verifyReceiptChain(String chainId) async {
    return (await _postJson(
          '/receipts/verify-chain',
          body: {'chain_id': chainId},
        ))
        as Map<String, dynamic>;
  }

  Future<List<Map<String, dynamic>>> listReceiptChains() async {
    final json = await _getJson('/receipts/chains') as List<dynamic>;
    return json
        .whereType<Map>()
        .map((item) => item.cast<String, dynamic>())
        .toList();
  }

  Future<Map<String, dynamic>> getReceiptChain(String chainId) async {
    return (await _getJson('/receipts/chains/$chainId'))
        as Map<String, dynamic>;
  }

  Future<List<GaiaRetentionPolicy>> listRetentionPolicies() async {
    final json = await _getJson('/retention/policies') as List<dynamic>;
    return json
        .whereType<Map>()
        .map(
          (item) => GaiaRetentionPolicy.fromJson(item.cast<String, dynamic>()),
        )
        .toList();
  }

  Future<Map<String, dynamic>> retentionStatus() async {
    return (await _getJson('/retention/status')) as Map<String, dynamic>;
  }

  Future<GaiaRetentionReport> retentionReport() async {
    final json = await _getJson('/retention/report') as Map<String, dynamic>;
    return GaiaRetentionReport.fromJson(json);
  }

  Future<GaiaRetentionPlan> retentionPlan(String policyId) async {
    final json =
        await _postJson('/retention/plan', body: {'policy_id': policyId})
            as Map<String, dynamic>;
    return GaiaRetentionPlan.fromJson(json);
  }

  Future<GaiaReviewPackageResult> verifyReviewPackage(
    String packagePath,
  ) async {
    final json =
        await _postJson(
              '/review-packages/verify',
              body: {'package_path': packagePath},
            )
            as Map<String, dynamic>;
    return GaiaReviewPackageResult.fromJson(json);
  }

  Future<List<GaiaSigningKeySummary>> listSigningKeys() async {
    final json = await _getJson('/signing/keys') as List<dynamic>;
    return json
        .whereType<Map>()
        .map(
          (item) =>
              GaiaSigningKeySummary.fromJson(item.cast<String, dynamic>()),
        )
        .toList();
  }

  Future<GaiaSigningKeySummary> createSigningKey(
    String keyName, {
    bool activate = true,
  }) async {
    final json =
        await _postJson(
              '/signing/keys',
              body: {'key_name': keyName, 'activate': activate},
            )
            as Map<String, dynamic>;
    return GaiaSigningKeySummary.fromJson(json);
  }

  Future<Map<String, dynamic>> rotateSigningKey(
    String keyId, {
    String? nextKeyName,
  }) async {
    return (await _postJson(
          '/signing/keys/$keyId/rotate',
          body: {'next_key_name': nextKeyName},
        ))
        as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> revokeSigningKey(
    String keyId, {
    String reason = 'revoked',
  }) async {
    return (await _postJson(
          '/signing/keys/$keyId/revoke',
          body: {'reason': reason},
        ))
        as Map<String, dynamic>;
  }

  Future<List<GaiaProvenanceManifest>> listProvenanceManifests() async {
    final json = await _getJson('/provenance/manifests') as List<dynamic>;
    return json
        .whereType<Map>()
        .map(
          (item) =>
              GaiaProvenanceManifest.fromJson(item.cast<String, dynamic>()),
        )
        .toList();
  }

  Future<GaiaProvenanceManifest> createProvenanceManifest(
    Map<String, dynamic> body,
  ) async {
    final json =
        await _postJson('/provenance/manifests', body: body)
            as Map<String, dynamic>;
    return GaiaProvenanceManifest.fromJson(json);
  }

  Future<GaiaProvenanceManifest> getProvenanceManifest(
    String manifestId,
  ) async {
    final json =
        await _getJson('/provenance/manifests/$manifestId')
            as Map<String, dynamic>;
    return GaiaProvenanceManifest.fromJson(json);
  }

  Future<Map<String, dynamic>> verifyProvenanceManifest(
    String manifestId,
  ) async {
    return (await _postJson('/provenance/manifests/$manifestId/verify'))
        as Map<String, dynamic>;
  }

  Future<List<GaiaTrustAlert>> trustAlerts() async {
    final json = await _getJson('/trust/alerts') as List<dynamic>;
    return json
        .whereType<Map>()
        .map((item) => GaiaTrustAlert.fromJson(item.cast<String, dynamic>()))
        .toList();
  }

  Future<List<GaiaTrustAlert>> refreshTrustAlerts() async {
    final json = await _postJson('/trust/alerts/refresh') as List<dynamic>;
    return json
        .whereType<Map>()
        .map((item) => GaiaTrustAlert.fromJson(item.cast<String, dynamic>()))
        .toList();
  }

  Future<Map<String, dynamic>> acknowledgeTrustAlert(
    String alertId, {
    String reviewer = 'manual',
    String reason = '',
  }) async {
    return (await _postJson(
          '/trust/alerts/$alertId/acknowledge',
          body: {'reviewer': reviewer, 'reason': reason},
        ))
        as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> inspectReceiptChain(String chainId) async {
    return (await _getJson('/receipts/chains/$chainId/inspect'))
        as Map<String, dynamic>;
  }
}

class _CachedJson {
  _CachedJson(this.value, this.createdAt);

  final dynamic value;
  final DateTime createdAt;
}
