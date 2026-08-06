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

class GaiaDashboardController extends ChangeNotifier {
  GaiaDashboardController({required GaiaIntegrationClient client}) : _client = client;

  final GaiaIntegrationClient _client;

  GaiaDashboardConnectionState connectionState = GaiaDashboardConnectionState.disconnected;
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

  Future<void> refresh({String? projectId}) async {
    connectionState = GaiaDashboardConnectionState.connecting;
    errorMessage = null;
    lastRefreshAttemptAt = DateTime.now();
    notifyListeners();
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
      statusMessage = 'GAIA dashboard refreshed';
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

  GaiaDashboardConnectionState _connectionStateFromCompatibility(GaiaCompatibility? compatibility) {
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
