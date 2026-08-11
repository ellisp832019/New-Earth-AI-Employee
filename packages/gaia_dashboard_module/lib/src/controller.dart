import 'dart:async';

import 'package:flutter/foundation.dart';

import 'package:gaia_integration_client/gaia_integration_client.dart';

enum GaiaDashboardConnectionState {
  disconnected,
  connecting,
  connected,
  degraded,
  incompatible,
  unavailable,
}

enum GaiaProjectOfficerSummaryState {
  loading,
  ready,
  empty,
  stale,
  unavailable,
  incompatible,
  partial,
  error,
}

enum GaiaProgrammeSummaryState {
  loading,
  ready,
  empty,
  stale,
  unavailable,
  incompatible,
  partial,
  error,
}

class GaiaDashboardController extends ChangeNotifier {
  GaiaDashboardController({required GaiaIntegrationClient client})
    : _client = client;

  final GaiaIntegrationClient _client;

  GaiaDashboardConnectionState connectionState =
      GaiaDashboardConnectionState.disconnected;
  GaiaCompatibility? compatibility;
  Map<String, dynamic>? capabilityPayload;
  Map<String, dynamic>? backendStatus;
  List<GaiaProjectSummary> projects = <GaiaProjectSummary>[];
  GaiaSummary? taskSummary;
  GaiaSummary? approvalSummary;
  GaiaActionSummary? actionSummary;
  GaiaDailyBrief? latestBrief;
  GaiaExecutionReceipt? latestReceipt;
  List<GaiaActionTemplate> actionTemplates = <GaiaActionTemplate>[];
  List<GaiaRetentionPolicy> retentionPolicies = <GaiaRetentionPolicy>[];
  Map<String, dynamic>? retentionStatus;
  GaiaRetentionReport? retentionReport;
  List<GaiaSigningKeySummary> signingKeys = <GaiaSigningKeySummary>[];
  List<GaiaProvenanceManifest> provenanceManifests = <GaiaProvenanceManifest>[];
  List<GaiaTrustAlert> trustAlerts = <GaiaTrustAlert>[];
  DateTime? lastRefreshAttemptAt;
  DateTime? lastSuccessfulRefreshAt;
  bool dataStale = false;
  String? errorMessage;
  String? statusMessage;

  GaiaProgrammeSummary? programmeSummary;
  DateTime? lastProgrammeSummaryRefreshAt;
  bool programmeSummaryStale = false;
  GaiaProgrammeSummaryState programmeSummaryState =
      GaiaProgrammeSummaryState.unavailable;
  String? programmeSummaryError;

  Map<String, dynamic>? projectOfficerCapabilitiesPayload;
  Map<String, dynamic>? projectOfficerPortfolioPayload;
  Map<String, dynamic>? projectOfficerRecommendationPortfolioPayload;
  Map<String, dynamic>? projectOfficerChangePortfolioPayload;
  List<Map<String, dynamic>> projectOfficerPendingApprovalPackages =
      <Map<String, dynamic>>[];
  List<Map<String, dynamic>> projectOfficerRecentCompletedWork =
      <Map<String, dynamic>>[];
  DateTime? lastProjectOfficerRefreshAt;
  bool projectOfficerStale = false;
  GaiaProjectOfficerSummaryState projectOfficerState =
      GaiaProjectOfficerSummaryState.unavailable;
  String? projectOfficerError;

  bool get projectOfficerSupported => _projectOfficerSupportsSummary(
    projectOfficerCapabilitiesPayload ?? const <String, dynamic>{},
  );

  List<Map<String, dynamic>> get projectOfficerPortfolioProjects =>
      _mapList(projectOfficerPortfolioPayload?['projects']);

  Map<String, dynamic> get projectOfficerPortfolioCountsByStatus =>
      _mapValue(projectOfficerPortfolioPayload?['counts_by_status']);

  List<Map<String, dynamic>> get projectOfficerTopRecommendations => _mapList(
    projectOfficerRecommendationPortfolioPayload?['recommendation_queue'],
  ).take(5).toList();

  List<Map<String, dynamic>> get projectOfficerBlockedProjects => _mapList(
    projectOfficerRecommendationPortfolioPayload?['projects'],
  ).where(_isBlockedProject).toList();

  List<Map<String, dynamic>> get projectOfficerStaleEvidenceItems => _mapList(
    projectOfficerChangePortfolioPayload?['projects'],
  ).where((item) => _boolValue(item['stale_evidence'])).toList();

  List<GaiaTrustAlert> get projectOfficerTrustAlerts => trustAlerts;

  String get projectOfficerStateLabel =>
      projectOfficerState.name.replaceAll('_', ' ');

  Future<void> refresh({String? projectId}) async {
    connectionState = GaiaDashboardConnectionState.connecting;
    errorMessage = null;
    lastRefreshAttemptAt = DateTime.now();
    notifyListeners();

    await Future.wait<void>([
      _refreshLegacySurface(projectId: projectId),
      _refreshProgrammeSummary(projectId: projectId),
      _refreshProjectOfficerSurface(projectId: projectId),
    ]);

    statusMessage = 'GAIA dashboard refreshed';
    notifyListeners();
  }

  Future<void> _refreshProgrammeSummary({String? projectId}) async {
    programmeSummaryError = null;
    programmeSummaryState = GaiaProgrammeSummaryState.loading;
    programmeSummaryStale = false;
    notifyListeners();

    try {
      final summary = await _client.programmeSummary(
        projectId: projectId,
        allowStaleCache: false,
      );
      programmeSummary = summary;
      final counts = summary.summary;
      final hasAnyContent =
          counts.projectCount > 0 ||
          counts.architectureEntityCount > 0 ||
          counts.architectureRelationshipCount > 0 ||
          counts.cycleCount > 0 ||
          counts.unresolvedDependencyCount > 0 ||
          counts.sharedDependencyCount > 0 ||
          counts.orphanCount > 0 ||
          counts.trustAlertCount > 0 ||
          counts.provenanceManifestCount > 0 ||
          counts.staleEvidenceProjects.isNotEmpty;
      final hasStaleContent =
          counts.staleEvidenceProjects.isNotEmpty ||
          counts.unresolvedDependencyCount > 0 ||
          counts.cycleCount > 0 ||
          counts.orphanCount > 0;

      if (!hasAnyContent) {
        programmeSummaryState = GaiaProgrammeSummaryState.empty;
      } else if (hasStaleContent) {
        programmeSummaryState = GaiaProgrammeSummaryState.stale;
        programmeSummaryStale = true;
      } else {
        programmeSummaryState = GaiaProgrammeSummaryState.ready;
      }
      lastProgrammeSummaryRefreshAt = DateTime.now();
    } on GaiaClientError catch (error) {
      if (error.statusCode == 404) {
        programmeSummaryState = GaiaProgrammeSummaryState.unavailable;
        programmeSummaryError =
            'Programme summary unavailable on this GAIA backend.';
      } else if (error.statusCode == 400 || error.statusCode == 409) {
        programmeSummaryState = GaiaProgrammeSummaryState.incompatible;
        programmeSummaryError = error.message;
      } else {
        programmeSummaryState = GaiaProgrammeSummaryState.error;
        programmeSummaryError = error.toString();
      }
      programmeSummaryStale = true;
    } catch (error) {
      programmeSummaryState = GaiaProgrammeSummaryState.error;
      programmeSummaryError = error.toString();
      programmeSummaryStale = true;
    } finally {
      notifyListeners();
    }
  }

  Future<void> _refreshLegacySurface({String? projectId}) async {
    try {
      final results = await Future.wait<Object?>([
        _client.compatibility(),
        _client.capabilityPayload(),
        _client.status(),
        _client.projects(),
        _client.taskSummary(projectId: projectId),
        _client.approvalSummary(projectId: projectId),
        _client.actionSummary(projectId: projectId),
        _client.latestBrief(projectId: projectId),
        _client.latestReceipt(),
        _client.listActionTemplates(),
        _client.listRetentionPolicies(),
        _client.retentionStatus(),
        _client.retentionReport(),
        _client.listSigningKeys(),
        _client.listProvenanceManifests(),
        _client.trustAlerts(),
      ]);
      compatibility = results[0] as GaiaCompatibility;
      capabilityPayload = results[1] as Map<String, dynamic>;
      backendStatus = results[2] as Map<String, dynamic>;
      projects = results[3] as List<GaiaProjectSummary>;
      taskSummary = results[4] as GaiaSummary;
      approvalSummary = results[5] as GaiaSummary;
      actionSummary = results[6] as GaiaActionSummary;
      latestBrief = results[7] as GaiaDailyBrief?;
      latestReceipt = results[8] as GaiaExecutionReceipt?;
      actionTemplates = results[9] as List<GaiaActionTemplate>;
      retentionPolicies = results[10] as List<GaiaRetentionPolicy>;
      retentionStatus = results[11] as Map<String, dynamic>;
      retentionReport = results[12] as GaiaRetentionReport;
      signingKeys = results[13] as List<GaiaSigningKeySummary>;
      provenanceManifests = results[14] as List<GaiaProvenanceManifest>;
      trustAlerts = results[15] as List<GaiaTrustAlert>;
      connectionState = _connectionStateFromCompatibility(compatibility);
      dataStale = false;
      lastSuccessfulRefreshAt = DateTime.now();
    } catch (error) {
      connectionState = compatibility == null
          ? GaiaDashboardConnectionState.unavailable
          : GaiaDashboardConnectionState.degraded;
      dataStale = true;
      errorMessage = error.toString();
    } finally {
      notifyListeners();
    }
  }

  Future<void> _refreshProjectOfficerSurface({String? projectId}) async {
    projectOfficerError = null;
    projectOfficerState = GaiaProjectOfficerSummaryState.loading;
    projectOfficerStale = false;
    notifyListeners();

    try {
      final capabilities = await _client.projectOfficerCapabilities(
        allowStaleCache: false,
      );
      projectOfficerCapabilitiesPayload = capabilities;

      if (!_projectOfficerSupportsSummary(capabilities)) {
        projectOfficerState = GaiaProjectOfficerSummaryState.unavailable;
        projectOfficerError =
            'Project Officer summaries unavailable on this GAIA backend.';
        return;
      }

      final errors = <String>[];
      final portfolioFuture = _loadProjectOfficer(
        errors,
        'project officer portfolio',
        () => _client.projectOfficerPortfolio(allowStaleCache: false),
      );
      final recommendationPortfolioFuture = _loadProjectOfficer(
        errors,
        'project officer recommendation portfolio',
        () => _client.projectOfficerRecommendationPortfolio(
          allowStaleCache: false,
        ),
      );
      final changePortfolioFuture = _loadProjectOfficer(
        errors,
        'project officer change portfolio',
        () => _client.projectOfficerChangePortfolio(allowStaleCache: false),
      );
      final pendingApprovalsFuture = _loadProjectOfficer(
        errors,
        'project officer pending approvals',
        () => _client.projectOfficerWorkPackages(
          approvalState: 'under_review',
          limit: 10,
          allowStaleCache: false,
        ),
      );
      final completedPackagesFuture = _loadProjectOfficer(
        errors,
        'project officer completed packages',
        () => _client.projectOfficerWorkPackages(
          approvalState: 'completed',
          limit: 10,
          allowStaleCache: false,
        ),
      );

      final results = await Future.wait<Object?>([
        portfolioFuture,
        recommendationPortfolioFuture,
        changePortfolioFuture,
        pendingApprovalsFuture,
        completedPackagesFuture,
      ]);

      projectOfficerPortfolioPayload = results[0] as Map<String, dynamic>?;
      projectOfficerRecommendationPortfolioPayload =
          results[1] as Map<String, dynamic>?;
      projectOfficerChangePortfolioPayload =
          results[2] as Map<String, dynamic>?;
      projectOfficerPendingApprovalPackages = _mapList(results[3]);

      final completedPackages = _mapList(results[4]);
      projectOfficerRecentCompletedWork = [];
      for (final package in completedPackages) {
        final outcomes = await _loadProjectOfficer(
          errors,
          'project officer work package outcomes',
          () => _client.projectOfficerWorkPackageOutcomes(
            _stringValue(package, 'work_package_id'),
            allowStaleCache: false,
          ),
        );
        final latestOutcome = _latestOutcome(_mapList(outcomes));
        if (latestOutcome != null) {
          projectOfficerRecentCompletedWork.add(latestOutcome);
        }
      }

      final hasAnyContent =
          projectOfficerPortfolioProjects.isNotEmpty ||
          projectOfficerTopRecommendations.isNotEmpty ||
          projectOfficerBlockedProjects.isNotEmpty ||
          projectOfficerPendingApprovalPackages.isNotEmpty ||
          projectOfficerStaleEvidenceItems.isNotEmpty ||
          projectOfficerRecentCompletedWork.isNotEmpty ||
          projectOfficerTrustAlerts.isNotEmpty;

      final hasStaleContent =
          _hasStalePortfolioEvidence(projectOfficerPortfolioPayload) ||
          _hasStalePortfolioEvidence(
            projectOfficerRecommendationPortfolioPayload,
          ) ||
          _hasStalePortfolioEvidence(projectOfficerChangePortfolioPayload);

      if (errors.isNotEmpty) {
        projectOfficerStale = true;
        projectOfficerState = hasAnyContent
            ? GaiaProjectOfficerSummaryState.partial
            : GaiaProjectOfficerSummaryState.error;
        projectOfficerError = errors.join(' | ');
      } else if (!hasAnyContent) {
        projectOfficerState = GaiaProjectOfficerSummaryState.empty;
      } else if (hasStaleContent) {
        projectOfficerState = GaiaProjectOfficerSummaryState.stale;
        projectOfficerStale = true;
      } else {
        projectOfficerState = GaiaProjectOfficerSummaryState.ready;
      }

      lastProjectOfficerRefreshAt = DateTime.now();
    } on GaiaClientError catch (error) {
      if (error.statusCode == 404) {
        projectOfficerState = GaiaProjectOfficerSummaryState.unavailable;
        projectOfficerError =
            'Project Officer summaries unavailable on this GAIA backend.';
      } else if (error.statusCode == 400 || error.statusCode == 409) {
        projectOfficerState = GaiaProjectOfficerSummaryState.incompatible;
        projectOfficerError = error.message;
      } else {
        projectOfficerState = GaiaProjectOfficerSummaryState.error;
        projectOfficerError = error.toString();
      }
      projectOfficerStale = true;
    } catch (error) {
      projectOfficerState = GaiaProjectOfficerSummaryState.error;
      projectOfficerError = error.toString();
      projectOfficerStale = true;
    } finally {
      notifyListeners();
    }
  }

  Future<T?> _loadProjectOfficer<T>(
    List<String> errors,
    String label,
    Future<T> Function() action,
  ) async {
    try {
      return await action();
    } catch (error) {
      errors.add('$label: ${error.toString()}');
      return null;
    }
  }

  bool _projectOfficerSupportsSummary(Map<String, dynamic> payload) {
    final capabilities = _stringList(payload['capabilities']);
    return capabilities.contains('project_officer_portfolio') ||
        capabilities.contains('project_officer_work_packages');
  }

  bool _hasStalePortfolioEvidence(Map<String, dynamic>? payload) {
    if (payload == null) {
      return false;
    }
    final projects = _mapList(payload['projects']);
    for (final project in projects) {
      if (_stringValue(project, 'evidence_freshness') == 'stale') {
        return true;
      }
      if (_boolValue(project['stale_evidence'])) {
        return true;
      }
      if (_stringValue(project, 'latest_comparison_freshness') == 'stale') {
        return true;
      }
      final latestSnapshot = _mapValue(project['latest_snapshot']);
      final freshness = _nestedString(latestSnapshot, [
        'normalized_payload',
        'configured_evidence',
        'evidence_freshness',
        'state',
      ]);
      if (freshness == 'stale') {
        return true;
      }
    }
    return false;
  }

  Map<String, dynamic> _mapValue(Object? value) =>
      value is Map ? value.cast<String, dynamic>() : <String, dynamic>{};

  List<Map<String, dynamic>> _mapList(Object? value) {
    if (value is! List) {
      return <Map<String, dynamic>>[];
    }
    return value
        .whereType<Map>()
        .map((item) => item.cast<String, dynamic>())
        .toList();
  }

  List<String> _stringList(Object? value) {
    if (value is! List) {
      return <String>[];
    }
    return value.whereType<String>().toList();
  }

  String _stringValue(
    Map<String, dynamic> map,
    String key, {
    String fallback = '',
  }) {
    final value = map[key];
    return value == null ? fallback : value.toString();
  }

  bool _boolValue(Object? value) => value is bool ? value : false;

  String _nestedString(
    Map<String, dynamic>? map,
    List<String> path, {
    String fallback = '',
  }) {
    if (map == null) {
      return fallback;
    }
    Object? current = map;
    for (final segment in path) {
      if (current is Map && current.containsKey(segment)) {
        current = current[segment];
      } else {
        return fallback;
      }
    }
    return current?.toString() ?? fallback;
  }

  Map<String, dynamic>? _latestOutcome(List<Map<String, dynamic>> outcomes) {
    if (outcomes.isEmpty) {
      return null;
    }
    outcomes.sort((a, b) {
      final aTime = DateTime.tryParse(_stringValue(a, 'recorded_at'));
      final bTime = DateTime.tryParse(_stringValue(b, 'recorded_at'));
      if (aTime == null && bTime == null) {
        return 0;
      }
      if (aTime == null) {
        return -1;
      }
      if (bTime == null) {
        return 1;
      }
      return aTime.compareTo(bTime);
    });
    return outcomes.last;
  }

  bool _isBlockedProject(Map<String, dynamic> project) {
    final state = _stringValue(project, 'latest_lifecycle_state');
    final blockedCount = project['blocked_recommendation_count'] as int? ?? 0;
    return state == 'blocked' || blockedCount > 0;
  }

  GaiaDashboardConnectionState _connectionStateFromCompatibility(
    GaiaCompatibility? compatibility,
  ) {
    if (compatibility == null) {
      return GaiaDashboardConnectionState.unavailable;
    }
    if (compatibility.status == 'compatible') {
      return GaiaDashboardConnectionState.connected;
    }
    if (compatibility.status == 'compatible_with_warnings') {
      return GaiaDashboardConnectionState.degraded;
    }
    if (compatibility.status == 'client_too_old' ||
        compatibility.status == 'backend_too_old' ||
        compatibility.status == 'contract_mismatch') {
      return GaiaDashboardConnectionState.incompatible;
    }
    if (compatibility.status == 'unavailable' ||
        compatibility.status == 'timeout' ||
        compatibility.status == 'malformed_response') {
      return GaiaDashboardConnectionState.unavailable;
    }
    return GaiaDashboardConnectionState.degraded;
  }
}
