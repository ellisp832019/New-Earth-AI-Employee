import 'dart:async';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

import 'backend_api.dart';
import 'backend_process.dart';
import 'models.dart';
import 'settings_store.dart';

class FirstRunCheck {
  FirstRunCheck({
    required this.label,
    required this.passed,
    required this.details,
  });

  final String label;
  final bool passed;
  final String details;
}

class GaiaAppController extends ChangeNotifier {
  GaiaAppController({
    GaiaSettingsStore? settingsStore,
    BackendProcessManager? backendProcessManager,
    GaiaBackendApi? backendApi,
  }) : _settingsStoreFuture = settingsStore == null
           ? GaiaSettingsStore.open()
           : Future.value(settingsStore),
       _backendProcessManager = backendProcessManager,
       _backendApi = backendApi;

  final Future<GaiaSettingsStore> _settingsStoreFuture;
  final BackendProcessManager? _backendProcessManager;
  GaiaBackendApi? _backendApi;

  GaiaSettingsStore? _settingsStore;
  GaiaAppSettings settings = GaiaAppSettings.defaults();
  bool initialized = false;
  bool firstRunMode = false;
  bool busy = false;
  String? statusMessage;
  String? lastError;
  BackendConnectionState backendState = BackendConnectionState.disconnected;
  HealthResponse? health;
  List<ProjectConfig> projects = <ProjectConfig>[];
  List<ModelStatus> models = <ModelStatus>[];
  List<RepositorySnapshot> snapshots = <RepositorySnapshot>[];
  List<DocumentRecord> documents = <DocumentRecord>[];
  List<SearchResult> searchResults = <SearchResult>[];
  List<AgentRunRecord> agentRuns = <AgentRunRecord>[];
  List<AuditEvent> auditEvents = <AuditEvent>[];
  List<TaskRecord> tasks = <TaskRecord>[];
  List<DraftRecord> drafts = <DraftRecord>[];
  List<ApprovalRecord> approvals = <ApprovalRecord>[];
  List<DailyBriefRecord> briefs = <DailyBriefRecord>[];
  Map<String, dynamic>? healthPortfolio;
  Map<String, dynamic>? changePortfolio;
  Map<String, dynamic>? recommendationPortfolio;
  Map<String, dynamic>? programmeWorkspace;
  List<Map<String, dynamic>> projectHealthSnapshots = <Map<String, dynamic>>[];
  List<Map<String, dynamic>> projectChangeFindings = <Map<String, dynamic>>[];
  List<Map<String, dynamic>> projectRecommendations = <Map<String, dynamic>>[];
  List<Map<String, dynamic>> recommendationQueue = <Map<String, dynamic>>[];
  List<Map<String, dynamic>> workPackages = <Map<String, dynamic>>[];
  Map<String, dynamic>? selectedRecommendationDetail;
  Map<String, dynamic>? selectedWorkPackageDetail;
  Map<String, dynamic>? selectedWorkPackageSummary;
  List<Map<String, dynamic>> selectedWorkPackageRevisions =
      <Map<String, dynamic>>[];
  List<Map<String, dynamic>> selectedWorkPackageApprovalDecisions =
      <Map<String, dynamic>>[];
  List<Map<String, dynamic>> selectedWorkPackageHandoffs =
      <Map<String, dynamic>>[];
  List<Map<String, dynamic>> selectedWorkPackageOutcomes =
      <Map<String, dynamic>>[];
  List<Map<String, dynamic>> permissionManifests = <Map<String, dynamic>>[];
  List<Map<String, dynamic>> outputActions = <Map<String, dynamic>>[];
  List<Map<String, dynamic>> executionReceipts = <Map<String, dynamic>>[];
  AskResponse? lastAskResponse;
  Map<String, String> reports = <String, String>{};
  Map<String, dynamic>? integrationCompatibility;
  Map<String, dynamic>? selectedActionDetail;
  List<Map<String, dynamic>> selectedActionPreviews = <Map<String, dynamic>>[];
  String? selectedProjectId;
  String? selectedTaskId;
  String? selectedDraftId;
  String? selectedApprovalId;
  String? selectedBriefId;
  String? selectedRecommendationId;
  String? selectedWorkPackageId;
  String? selectedActionId;
  String? selectedManifestId;
  String? selectedReceiptId;
  List<FirstRunCheck> firstRunChecks = <FirstRunCheck>[];
  final List<String> backendLogs = <String>[];
  http.Client? _activeAskClient;
  bool _loading = false;
  bool _disposed = false;
  Future<void>? _refreshEverythingInFlight;
  BackendCompatibilityState backendCompatibilityState =
      BackendCompatibilityState.unreachable;

  GaiaBackendApi get _client {
    if (_backendApi != null) {
      return _backendApi!;
    }
    final backendUrl = Uri.parse(settings.backendUrl);
    return GaiaApiClient(baseUri: backendUrl);
  }

  Future<void> bootstrap() async {
    if (_loading) {
      return;
    }
    _loading = true;
    try {
      _settingsStore ??= await _settingsStoreFuture;
      settings = await _settingsStore!.load();
      _backendApi ??= GaiaApiClient(baseUri: settings.backendUri());
      selectedProjectId = settings.defaultProjectId.isEmpty
          ? null
          : settings.defaultProjectId;
      firstRunMode = !settings.firstRunComplete;
      initialized = true;
      notifyListeners();
      if (!firstRunMode) {
        await refreshEverything();
      } else {
        await runFirstRunChecks();
      }
    } finally {
      _loading = false;
    }
  }

  Future<void> refreshEverything() async {
    final inFlight = _refreshEverythingInFlight;
    if (inFlight != null) {
      await inFlight;
      return;
    }

    final future = _refreshEverythingImpl();
    _refreshEverythingInFlight = future;
    try {
      await future;
    } finally {
      if (identical(_refreshEverythingInFlight, future)) {
        _refreshEverythingInFlight = null;
      }
    }
  }

  Future<void> _refreshEverythingImpl() async {
    busy = true;
    lastError = null;
    notifyListeners();
    try {
      await Future.wait(<Future<void>>[
        refreshBackend(),
        refreshProjects(),
        refreshModels(),
        refreshRuns(),
        refreshAuditEvents(),
        refreshWorkflowRecords(),
        refreshOutputWorkspaceRecords(),
        refreshProgrammeWorkspace(),
      ]);
      if (selectedProjectId == null && projects.isNotEmpty) {
        selectedProjectId = projects.first.projectId;
      }
      if (selectedProjectId != null) {
        await refreshSelectedProject(selectedProjectId!);
      }
      await refreshFirstRunChecks();
      statusMessage = 'GAIA refreshed';
    } catch (error) {
      lastError = error.toString();
    } finally {
      busy = false;
      notifyListeners();
    }
  }

  Future<void> refreshBackend() async {
    backendState = BackendConnectionState.connecting;
    notifyListeners();
    try {
      health = await _client.health();
      backendState = BackendConnectionState.connected;
    } catch (error) {
      backendState = BackendConnectionState.disconnected;
      backendCompatibilityState = BackendCompatibilityState.unreachable;
      health = null;
      lastError = error.toString();
      notifyListeners();
      return;
    }

    try {
      await _refreshCompatibilityState();
    } catch (error) {
      backendCompatibilityState = BackendCompatibilityState.unknown;
      integrationCompatibility = null;
      lastError = error.toString();
    } finally {
      notifyListeners();
    }
  }

  Future<void> connectToBackend() async {
    await refreshBackend();
    if (backendState == BackendConnectionState.connected) {
      await refreshEverything();
    }
  }

  Future<void> startLocalBackend() async {
    if (_backendProcessManager == null) {
      lastError = 'Backend process management is unavailable in this build.';
      notifyListeners();
      return;
    }
    backendState = BackendConnectionState.starting;
    statusMessage = 'Starting local backend...';
    notifyListeners();
    try {
      await _backendProcessManager.pruneLogs(
        retentionDays: settings.logRetentionDays,
      );
      final session = await _backendProcessManager.start(
        onStdout: _recordBackendLog,
        onStderr: _recordBackendLog,
      );
      _recordBackendLog('Started backend process pid=${session.process.pid}');
      await _pollBackendHealth();
      settings = settings.copyWith(
        backendLaunchPreference: BackendLaunchPreference.startLocal,
      );
      await _saveSettings();
      await refreshEverything();
    } catch (error) {
      backendState = BackendConnectionState.failed;
      lastError = error.toString();
      notifyListeners();
    }
  }

  Future<void> stopBackendIfManaged() async {
    if (_backendProcessManager == null) {
      return;
    }
    await _backendProcessManager.stop();
    backendState = BackendConnectionState.disconnected;
    statusMessage = 'Backend stopped.';
    notifyListeners();
  }

  Future<void> _pollBackendHealth() async {
    for (var attempt = 0; attempt < 20; attempt++) {
      try {
        await refreshBackend();
        if (backendState == BackendConnectionState.connected) {
          return;
        }
      } catch (_) {
        // keep retrying until we hit the timeout budget
      }
      await Future<void>.delayed(const Duration(milliseconds: 500));
    }
    throw StateError('Backend did not become healthy within the retry budget.');
  }

  Future<void> refreshProjects() async {
    projects = await _client.listProjects();
    selectedProjectId ??= settings.defaultProjectId.isNotEmpty
        ? settings.defaultProjectId
        : (projects.isEmpty ? null : projects.first.projectId);
    if (selectedProjectId != null &&
        projects.every((project) => project.projectId != selectedProjectId)) {
      selectedProjectId = projects.isEmpty ? null : projects.first.projectId;
    }
    notifyListeners();
  }

  Future<void> refreshModels() async {
    models = await _client.listModelStatus();
    notifyListeners();
  }

  Future<void> refreshSelectedProject(String projectId) async {
    try {
      final snapshot = await _client.latestSnapshot(projectId);
      snapshots = <RepositorySnapshot>[
        snapshot,
        ...snapshots.where((entry) => entry.projectId != projectId),
      ].take(20).toList();
    } catch (_) {
      // No snapshot yet, which is fine during first run.
    }
    try {
      documents = await _client.listDocuments(projectId);
    } catch (_) {
      documents = <DocumentRecord>[];
    }
    try {
      searchResults = await _client.search(projectId, 'MicroGrow', limit: 10);
    } catch (_) {
      searchResults = <SearchResult>[];
    }
    await refreshWorkflowRecords(projectId: projectId);
    await refreshPlanningWorkspace(projectId: projectId);
    notifyListeners();
  }

  Future<void> refreshWorkflowRecords({String? projectId}) async {
    try {
      tasks = await _client.listTasks(
        projectId: projectId ?? selectedProjectId,
        limit: 100,
      );
    } catch (_) {
      tasks = <TaskRecord>[];
    }
    try {
      drafts = await _client.listDrafts(
        projectId: projectId ?? selectedProjectId,
        limit: 100,
      );
    } catch (_) {
      drafts = <DraftRecord>[];
    }
    try {
      approvals = await _client.listApprovals(
        projectId: projectId ?? selectedProjectId,
        limit: 100,
      );
    } catch (_) {
      approvals = <ApprovalRecord>[];
    }
    try {
      briefs = await _client.listBriefs(
        projectId: projectId ?? selectedProjectId,
        limit: 50,
      );
    } catch (_) {
      briefs = <DailyBriefRecord>[];
    }
    selectedTaskId ??= tasks.isEmpty ? null : tasks.first.taskId;
    selectedDraftId ??= drafts.isEmpty ? null : drafts.first.draftId;
    selectedApprovalId ??= approvals.isEmpty
        ? null
        : approvals.first.approvalId;
    selectedBriefId ??= briefs.isEmpty ? null : briefs.first.briefId;
    notifyListeners();
  }

  Future<void> refreshCompatibility() async {
    try {
      await _refreshCompatibilityState();
    } catch (error) {
      integrationCompatibility = null;
      backendCompatibilityState = BackendCompatibilityState.unknown;
      lastError = error.toString();
    }
    notifyListeners();
  }

  Future<void> refreshOutputWorkspaceRecords({String? projectId}) async {
    try {
      permissionManifests = await _client.listPermissionManifests();
    } catch (_) {
      permissionManifests = <Map<String, dynamic>>[];
    }
    try {
      outputActions = await _client.listActions(
        projectId: projectId ?? selectedProjectId,
        limit: 100,
      );
    } catch (_) {
      outputActions = <Map<String, dynamic>>[];
    }
    try {
      executionReceipts = await _client.listReceipts(limit: 100);
    } catch (_) {
      executionReceipts = <Map<String, dynamic>>[];
    }
    selectedManifestId ??= permissionManifests.isEmpty
        ? null
        : permissionManifests.first['manifest_id'] as String?;
    selectedActionId ??= outputActions.isEmpty
        ? null
        : outputActions.first['action_id'] as String?;
    selectedReceiptId ??= executionReceipts.isEmpty
        ? null
        : executionReceipts.first['receipt_id'] as String?;
    await refreshSelectedAction();
    notifyListeners();
  }

  Future<void> refreshPlanningWorkspace({String? projectId}) async {
    final activeProjectId = projectId ?? selectedProjectId;
    try {
      healthPortfolio = await _client.projectHealthPortfolio();
    } catch (_) {
      healthPortfolio = null;
    }
    try {
      changePortfolio = await _client.projectChangePortfolio();
    } catch (_) {
      changePortfolio = null;
    }
    try {
      recommendationPortfolio = await _client.projectRecommendationPortfolio();
    } catch (_) {
      recommendationPortfolio = null;
    }
    if (activeProjectId != null) {
      try {
        projectHealthSnapshots = await _client.projectHealthSnapshots(
          activeProjectId,
        );
      } catch (_) {
        projectHealthSnapshots = <Map<String, dynamic>>[];
      }
      try {
        projectChangeFindings = await _client.projectChangeFindings(
          activeProjectId,
        );
      } catch (_) {
        projectChangeFindings = <Map<String, dynamic>>[];
      }
      try {
        projectRecommendations = await _client.projectRecommendations(
          activeProjectId,
        );
        if (projectRecommendations.isEmpty) {
          projectRecommendations = await _client.generateProjectRecommendations(
            activeProjectId,
          );
        }
      } catch (_) {
        projectRecommendations = <Map<String, dynamic>>[];
      }
      try {
        recommendationQueue = await _client.recommendationQueue(
          projectId: activeProjectId,
        );
      } catch (_) {
        recommendationQueue = <Map<String, dynamic>>[];
      }
      try {
        workPackages = await _client.listWorkPackages(
          projectId: activeProjectId,
        );
      } catch (_) {
        workPackages = <Map<String, dynamic>>[];
      }
    } else {
      projectHealthSnapshots = <Map<String, dynamic>>[];
      projectChangeFindings = <Map<String, dynamic>>[];
      projectRecommendations = <Map<String, dynamic>>[];
      recommendationQueue = <Map<String, dynamic>>[];
      workPackages = <Map<String, dynamic>>[];
      selectedRecommendationId = null;
      selectedWorkPackageId = null;
      selectedRecommendationDetail = null;
      selectedWorkPackageDetail = null;
      selectedWorkPackageSummary = null;
      selectedWorkPackageRevisions = <Map<String, dynamic>>[];
      selectedWorkPackageApprovalDecisions = <Map<String, dynamic>>[];
      selectedWorkPackageHandoffs = <Map<String, dynamic>>[];
      selectedWorkPackageOutcomes = <Map<String, dynamic>>[];
    }
    final recommendationKnown =
        selectedRecommendationId != null &&
        projectRecommendations.any(
          (item) =>
              item['recommendation_id']?.toString() == selectedRecommendationId,
        );
    final workPackageKnown =
        selectedWorkPackageId != null &&
        workPackages.any(
          (item) =>
              item['work_package_id']?.toString() == selectedWorkPackageId,
        );
    if (!recommendationKnown) {
      selectedRecommendationId = projectRecommendations.isEmpty
          ? null
          : projectRecommendations.first['recommendation_id'] as String?;
    }
    if (!workPackageKnown) {
      selectedWorkPackageId = workPackages.isEmpty
          ? null
          : workPackages.first['work_package_id'] as String?;
    }
    await refreshSelectedRecommendation();
    await refreshSelectedWorkPackage();
    notifyListeners();
  }

  Future<void> refreshProgrammeWorkspace({String? projectId}) async {
    try {
      programmeWorkspace = await _client.programmeWorkspace(
        projectId: projectId ?? selectedProjectId,
      );
    } catch (_) {
      programmeWorkspace = null;
    }
    notifyListeners();
  }

  Future<void> refreshSelectedRecommendation() async {
    if (selectedRecommendationId == null) {
      selectedRecommendationDetail = null;
      return;
    }
    try {
      selectedRecommendationDetail = await _client.getRecommendation(
        selectedRecommendationId!,
      );
    } catch (_) {
      selectedRecommendationDetail = null;
    }
    notifyListeners();
  }

  Future<void> refreshSelectedWorkPackage() async {
    if (selectedWorkPackageId == null) {
      selectedWorkPackageDetail = null;
      selectedWorkPackageSummary = null;
      selectedWorkPackageRevisions = <Map<String, dynamic>>[];
      selectedWorkPackageApprovalDecisions = <Map<String, dynamic>>[];
      selectedWorkPackageHandoffs = <Map<String, dynamic>>[];
      selectedWorkPackageOutcomes = <Map<String, dynamic>>[];
      return;
    }
    try {
      selectedWorkPackageDetail = await _client.getWorkPackage(
        selectedWorkPackageId!,
      );
      selectedWorkPackageSummary = await _client.workPackageSummary(
        selectedWorkPackageId!,
      );
      selectedWorkPackageRevisions = await _client.workPackageRevisions(
        selectedWorkPackageId!,
      );
      selectedWorkPackageApprovalDecisions = await _client
          .workPackageApprovalDecisions(selectedWorkPackageId!);
      selectedWorkPackageHandoffs = await _client.workPackageHandoffs(
        selectedWorkPackageId!,
      );
      selectedWorkPackageOutcomes = await _client.workPackageOutcomes(
        selectedWorkPackageId!,
      );
    } catch (_) {
      selectedWorkPackageDetail = null;
      selectedWorkPackageSummary = null;
      selectedWorkPackageRevisions = <Map<String, dynamic>>[];
      selectedWorkPackageApprovalDecisions = <Map<String, dynamic>>[];
      selectedWorkPackageHandoffs = <Map<String, dynamic>>[];
      selectedWorkPackageOutcomes = <Map<String, dynamic>>[];
    }
    notifyListeners();
  }

  Future<void> refreshSelectedAction() async {
    if (selectedActionId == null) {
      selectedActionDetail = null;
      selectedActionPreviews = <Map<String, dynamic>>[];
      return;
    }
    try {
      selectedActionDetail = await _client.getAction(selectedActionId!);
      final preview = await _client.previewAction(selectedActionId!);
      selectedActionPreviews =
          (preview['previews'] as List<dynamic>? ?? const <dynamic>[])
              .whereType<Map>()
              .map((item) => item.cast<String, dynamic>())
              .toList();
    } catch (_) {
      selectedActionDetail = null;
      selectedActionPreviews = <Map<String, dynamic>>[];
    }
    notifyListeners();
  }

  Future<void> refreshRuns() async {
    try {
      agentRuns = await _client.listAgentRuns(limit: 50);
    } catch (_) {
      agentRuns = <AgentRunRecord>[];
    }
    notifyListeners();
  }

  Future<void> refreshAuditEvents() async {
    try {
      auditEvents = (await _client.listAuditEvents(
        limit: 100,
      )).map(AuditEvent.fromJson).toList();
    } catch (_) {
      auditEvents = <AuditEvent>[];
    }
    notifyListeners();
  }

  Future<void> refreshReport(
    String projectId, {
    ReportFormatPreference format = ReportFormatPreference.markdown,
  }) async {
    reports[projectId] = await _client.foundationReport(
      projectId,
      format: format.name,
    );
    notifyListeners();
  }

  Future<void> runScan(String projectId) async {
    await _client.scanProject(projectId);
    await refreshSelectedProject(projectId);
    await refreshProjects();
    await refreshRuns();
  }

  Future<void> createSnapshot(String projectId) async {
    await _client.scanProject(projectId);
    await refreshSelectedProject(projectId);
    await refreshRuns();
  }

  Future<void> createDailyBrief(String projectId) async {
    await _client.createDailyBrief(projectId);
    await refreshWorkflowRecords(projectId: projectId);
  }

  Future<void> createTaskFromRun(String runId) async {
    await _client.createTaskFromRun(runId);
    await refreshWorkflowRecords();
  }

  Future<void> acceptTask(String taskId) async {
    await _client.acceptTask(taskId);
    await refreshWorkflowRecords();
  }

  Future<void> transitionTask(
    String taskId,
    String status, {
    String? reason,
    List<String>? completionEvidence,
    String? manualOverrideReason,
    String actor = 'manual',
  }) async {
    final task = tasks.firstWhere((entry) => entry.taskId == taskId);
    await _client.transitionTask(
      taskId,
      <String, dynamic>{
        'version': task.version,
        'status': status,
        'reason': reason,
        'completion_evidence': completionEvidence,
        'manual_override_reason': manualOverrideReason,
        'actor': actor,
      }..removeWhere((key, value) => value == null),
    );
    await refreshWorkflowRecords();
  }

  Future<void> createTask({
    required String title,
    required String projectId,
    String description = '',
    String priority = 'normal',
    String category = 'general',
    String sourceType = 'manual',
    String? sourceIdentifier,
    String? sourceAgentRunId,
    List<String> evidenceReferences = const <String>[],
    List<String> dependencyTaskIds = const <String>[],
    String? blockerDescription,
    String? assignedTo,
    String completionCriteria = '',
    bool approvalRequirement = false,
    List<String> tags = const <String>[],
  }) async {
    await _client.createTask(
      <String, dynamic>{
        'title': title,
        'project_id': projectId,
        'description': description,
        'priority': priority,
        'category': category,
        'source_type': sourceType,
        'source_identifier': sourceIdentifier,
        'source_agent_run_id': sourceAgentRunId,
        'evidence_references': evidenceReferences,
        'dependency_task_ids': dependencyTaskIds,
        'blocker_description': blockerDescription,
        'assigned_to': assignedTo,
        'completion_criteria': completionCriteria,
        'approval_requirement': approvalRequirement,
        'tags': tags,
      }..removeWhere((key, value) => value == null),
    );
    await refreshWorkflowRecords(projectId: projectId);
  }

  Future<void> createDraft({
    required String title,
    required String projectId,
    String draftType = 'generic_markdown',
    String content = '',
    String? sourceTaskId,
    String? sourceAgentRunId,
    bool approvalRequirement = false,
  }) async {
    await _client.createDraft(
      <String, dynamic>{
        'title': title,
        'draft_type': draftType,
        'project_id': projectId,
        'content': content,
        'source_task_id': sourceTaskId,
        'source_agent_run_id': sourceAgentRunId,
        'approval_requirement': approvalRequirement,
      }..removeWhere((key, value) => value == null),
    );
    await refreshWorkflowRecords(projectId: projectId);
  }

  Future<void> reviseDraft(
    String draftId,
    String content, {
    String? author,
    String? changeReason,
  }) async {
    final draft = drafts.firstWhere((entry) => entry.draftId == draftId);
    await _client.reviseDraft(draftId, <String, dynamic>{
      'version': draft.currentRevision,
      'content': content,
      'author': author ?? 'manual',
      'change_reason': changeReason ?? 'revision',
    });
    await refreshWorkflowRecords(projectId: draft.projectId);
  }

  Future<void> createApproval({
    required String title,
    required String projectId,
    String description = '',
    String requestType = 'manual',
    String? sourceTaskId,
    String? sourceDraftId,
    String requestingSource = 'manual',
    String proposedAction = '',
    String exactTargetDescription = '',
    String writeBoundary = 'gaia-local',
    String riskLevel = 'low',
    String previewSummary = '',
    String approvedContentHash = '',
  }) async {
    await _client.createApproval(
      <String, dynamic>{
        'title': title,
        'project_id': projectId,
        'description': description,
        'request_type': requestType,
        'source_task_id': sourceTaskId,
        'source_draft_id': sourceDraftId,
        'requesting_source': requestingSource,
        'proposed_action': proposedAction,
        'exact_target_description': exactTargetDescription,
        'write_boundary': writeBoundary,
        'risk_level': riskLevel,
        'preview_summary': previewSummary,
        'approved_content_hash': approvedContentHash,
      }..removeWhere((key, value) => value == null),
    );
    await refreshWorkflowRecords(projectId: projectId);
  }

  Future<void> submitDraft(String draftId) async {
    await _client.submitDraft(draftId);
    await refreshWorkflowRecords();
  }

  Future<void> approveRequest(
    String approvalId, {
    required int version,
    String reviewer = 'manual',
    String decisionReason = 'approved for manual use',
  }) async {
    await _client.approveApproval(approvalId, <String, dynamic>{
      'version': version,
      'reviewer': reviewer,
      'decision_reason': decisionReason,
    });
    await refreshWorkflowRecords();
  }

  Future<void> rejectRequest(
    String approvalId, {
    required int version,
    String reviewer = 'manual',
    String decisionReason = 'rejected',
  }) async {
    await _client.rejectApproval(approvalId, <String, dynamic>{
      'version': version,
      'reviewer': reviewer,
      'decision_reason': decisionReason,
    });
    await refreshWorkflowRecords();
  }

  Future<void> refreshApprovalValidation(String approvalId) async {
    await _client.refreshApprovalValidation(approvalId);
    await refreshWorkflowRecords();
  }

  Future<void> createApprovalFromDraft({
    required String title,
    required String projectId,
    required String sourceDraftId,
    String description = '',
    String requestingSource = 'manual',
    String proposedAction = 'Manual use review',
    String exactTargetDescription = 'GAIA draft and task review',
    String writeBoundary = 'gaia-local',
    String riskLevel = 'medium',
    String previewSummary = '',
  }) async {
    final draft = drafts.firstWhere((entry) => entry.draftId == sourceDraftId);
    await createApproval(
      title: title,
      projectId: projectId,
      description: description,
      sourceDraftId: sourceDraftId,
      requestingSource: requestingSource,
      proposedAction: proposedAction,
      exactTargetDescription: exactTargetDescription,
      writeBoundary: writeBoundary,
      riskLevel: riskLevel,
      previewSummary: previewSummary,
      approvedContentHash: draft.currentContentHash,
    );
  }

  Future<void> refreshPlanningWorkspaceForProject(String projectId) async {
    await refreshPlanningWorkspace(projectId: projectId);
  }

  Future<void> generateRecommendations(String projectId) async {
    await _client.generateProjectRecommendations(projectId);
    await refreshPlanningWorkspace(projectId: projectId);
  }

  Future<void> captureProjectHealth(String projectId) async {
    await _client.captureProjectHealth(projectId);
    await refreshPlanningWorkspace(projectId: projectId);
  }

  Future<void> generateWorkPackage(String recommendationId) async {
    final package = await _client.generateWorkPackage(recommendationId);
    selectedWorkPackageId = package['work_package_id'] as String?;
    await refreshPlanningWorkspace(projectId: selectedProjectId);
  }

  Future<void> submitWorkPackageForReview(
    String workPackageId,
    int revisionNumber, {
    String actor = 'manual',
  }) async {
    await _client.submitWorkPackageForReview(
      workPackageId,
      revisionNumber: revisionNumber,
      actor: actor,
    );
    await refreshPlanningWorkspace(projectId: selectedProjectId);
  }

  Future<void> approveWorkPackage(
    String workPackageId,
    int revisionNumber, {
    String actor = 'manual',
    String? humanNote,
  }) async {
    await _client.approveWorkPackage(
      workPackageId,
      revisionNumber: revisionNumber,
      actor: actor,
      humanNote: humanNote,
    );
    await refreshPlanningWorkspace(projectId: selectedProjectId);
  }

  Future<void> rejectWorkPackage(
    String workPackageId,
    int revisionNumber, {
    String actor = 'manual',
    String? humanNote,
  }) async {
    await _client.rejectWorkPackage(
      workPackageId,
      revisionNumber: revisionNumber,
      actor: actor,
      humanNote: humanNote,
    );
    await refreshPlanningWorkspace(projectId: selectedProjectId);
  }

  Future<void> handoffWorkPackage(
    String workPackageId,
    int revisionNumber, {
    String approvedBy = 'manual',
    String nextManualAction = 'Copy the approved Codex prompt into Codex.',
    String rollbackReference =
        'Return to the recorded baseline commit or last approved revision.',
  }) async {
    await _client.handoffWorkPackage(
      workPackageId,
      revisionNumber: revisionNumber,
      approvedBy: approvedBy,
      nextManualAction: nextManualAction,
      rollbackReference: rollbackReference,
    );
    await refreshPlanningWorkspace(projectId: selectedProjectId);
  }

  Future<void> recordWorkPackageOutcome(
    String workPackageId,
    int revisionNumber, {
    required String outcome,
    String actor = 'manual',
    String? note,
  }) async {
    await _client.recordWorkPackageOutcome(
      workPackageId,
      revisionNumber: revisionNumber,
      outcome: outcome,
      actor: actor,
      note: note,
    );
    await refreshPlanningWorkspace(projectId: selectedProjectId);
  }

  Future<void> reviseWorkPackage(
    String workPackageId, {
    required String changeReason,
    Map<String, dynamic>? fieldUpdates,
    String actor = 'manual',
  }) async {
    await _client.reviseWorkPackage(
      workPackageId,
      changeReason: changeReason,
      fieldUpdates: fieldUpdates,
      actor: actor,
    );
    await refreshPlanningWorkspace(projectId: selectedProjectId);
  }

  Future<void> detectWorkPackageStaleness(String workPackageId) async {
    await _client.detectWorkPackageStaleness(workPackageId);
    await refreshPlanningWorkspace(projectId: selectedProjectId);
  }

  Future<void> expireWorkPackage(
    String workPackageId, {
    String reason = 'manual expiry',
  }) async {
    await _client.expireWorkPackage(workPackageId, reason: reason);
    await refreshPlanningWorkspace(projectId: selectedProjectId);
  }

  Future<void> createPermissionManifest({
    required String name,
    String description = '',
    List<String> allowedActionTypes = const <String>[],
    List<String> allowedTargetRoots = const <String>[],
    List<String> allowedFileExtensions = const <String>[],
    List<String> deniedPathPatterns = const <String>[],
    int maximumFileSize = 0,
    String overwritePolicy = 'deny',
    bool backupRequirement = true,
    bool rollbackRequirement = true,
    bool approvalRequirement = true,
    String riskCeiling = 'low',
    bool enabled = false,
  }) async {
    await _client.createPermissionManifest(<String, dynamic>{
      'name': name,
      'description': description,
      'allowed_action_types': allowedActionTypes,
      'allowed_target_roots': allowedTargetRoots,
      'allowed_file_extensions': allowedFileExtensions,
      'denied_path_patterns': deniedPathPatterns,
      'maximum_file_size': maximumFileSize,
      'overwrite_policy': overwritePolicy,
      'backup_requirement': backupRequirement,
      'rollback_requirement': rollbackRequirement,
      'approval_requirement': approvalRequirement,
      'risk_ceiling': riskCeiling,
      'enabled': enabled,
    });
    await refreshOutputWorkspaceRecords();
  }

  Future<void> reviewPermissionManifest(
    String manifestId, {
    required int version,
    String reviewer = 'manual',
    String reviewNotes = '',
    bool enabled = true,
  }) async {
    await _client.reviewPermissionManifest(manifestId, <String, dynamic>{
      'version': version,
      'reviewer': reviewer,
      'review_notes': reviewNotes,
      'enabled': enabled,
    });
    await refreshOutputWorkspaceRecords();
  }

  Future<Map<String, dynamic>> validatePermissionManifest(
    String manifestId,
  ) async {
    return await _client.validatePermissionManifest(manifestId);
  }

  Future<void> createOutputAction({
    required String title,
    required String projectId,
    required String manifestId,
    required String targetPath,
    required String actionType,
    String content = '',
    String contentSource = 'manual',
  }) async {
    await _client.createAction(<String, dynamic>{
      'title': title,
      'project_id': projectId,
      'manifest_id': manifestId,
      'target_path': targetPath,
      'action_type': actionType,
      'content': content,
      'content_source': contentSource,
    });
    await refreshOutputWorkspaceRecords(projectId: projectId);
  }

  Future<void> requestActionApproval(String actionId) async {
    await _client.requestActionApproval(actionId);
    await refreshOutputWorkspaceRecords();
  }

  Future<void> approveAction(String actionId) async {
    await _client.approveAction(actionId);
    await refreshOutputWorkspaceRecords();
  }

  Future<void> executeAction(
    String actionId, {
    bool confirm = false,
    String operator = 'manual',
  }) async {
    await _client.executeAction(actionId, confirm: confirm, operator: operator);
    await refreshOutputWorkspaceRecords();
  }

  Future<void> rollbackAction(
    String actionId, {
    bool confirm = false,
    String operator = 'manual',
  }) async {
    await _client.rollbackAction(
      actionId,
      confirm: confirm,
      operator: operator,
    );
    await refreshOutputWorkspaceRecords();
  }

  Future<void> cancelAction(
    String actionId, {
    String reason = 'cancelled',
  }) async {
    await _client.cancelAction(actionId, reason: reason);
    await refreshOutputWorkspaceRecords();
  }

  Future<void> askGaia({
    required String projectId,
    required String question,
    required String provider,
    required String modelName,
    required int evidenceLimit,
    required bool deterministicOnly,
    required bool refreshSnapshot,
  }) async {
    cancelCurrentAsk();
    busy = true;
    statusMessage = 'Thinking...';
    lastError = null;
    notifyListeners();
    final client = http.Client();
    _activeAskClient = client;
    try {
      final response = await _client.ask(
        AskRequestBody(
          projectId: projectId,
          question: question,
          provider: provider.isEmpty ? null : provider,
          model: modelName.isEmpty ? null : modelName,
          evidenceLimit: evidenceLimit,
          refreshSnapshot: refreshSnapshot,
          deterministicOnly: deterministicOnly,
        ),
        client: client,
      );
      lastAskResponse = response;
      if (response.snapshotId != null && response.snapshotId!.isNotEmpty) {
        statusMessage = 'Answer received from ${response.provider}.';
      }
      await refreshRuns();
    } catch (error) {
      lastError = error.toString();
      rethrow;
    } finally {
      busy = false;
      _activeAskClient = null;
      notifyListeners();
    }
  }

  void cancelCurrentAsk() {
    _activeAskClient?.close();
    _activeAskClient = null;
    statusMessage = 'Ask cancelled.';
    notifyListeners();
  }

  Future<void> updateSettings(GaiaAppSettings next) async {
    settings = next;
    _backendApi = GaiaApiClient(baseUri: settings.backendUri());
    await _saveSettings();
    await refreshFirstRunChecks();
    notifyListeners();
  }

  Future<void> completeFirstRun() async {
    settings = settings.copyWith(firstRunComplete: true);
    await _saveSettings();
    firstRunMode = false;
    await refreshEverything();
    notifyListeners();
  }

  Future<void> runFirstRunChecks() async {
    final checks = <FirstRunCheck>[];
    final repoRoot = Directory(settings.repositoryRootPath);
    checks.add(
      FirstRunCheck(
        label: 'Locate GAIA installation',
        passed: repoRoot.existsSync() && _hasBackendProjectFiles(repoRoot),
        details: repoRoot.path,
      ),
    );
    checks.add(
      FirstRunCheck(
        label: 'Python virtual environment',
        passed: File(defaultPythonPath(repoRoot.path)).existsSync(),
        details: defaultPythonPath(repoRoot.path),
      ),
    );
    checks.add(
      FirstRunCheck(
        label: 'Backend availability',
        passed: await _canReachBackend(),
        details: settings.backendUrl,
      ),
    );
    checks.add(
      FirstRunCheck(
        label: 'Configured projects',
        passed: projects.isNotEmpty,
        details: '${projects.length} projects',
      ),
    );
    checks.add(
      FirstRunCheck(
        label: 'MicroGrow access',
        passed: projects.any((project) => project.projectId == 'microgrow-v1'),
        details: 'microgrow-v1',
      ),
    );
    checks.add(
      FirstRunCheck(
        label: 'Ollama availability',
        passed: models.any((status) => status.provider == 'ollama'),
        details:
            models
                .firstWhere(
                  (status) => status.provider == 'ollama',
                  orElse: () => ModelStatus(
                    provider: 'ollama',
                    available: false,
                    modelName: null,
                    endpointIdentity: null,
                    details: 'Not checked',
                  ),
                )
                .details ??
            'Not checked',
      ),
    );
    checks.add(
      FirstRunCheck(
        label: 'Read-only operating mode',
        passed: projects.every((project) => project.access == 'read_only'),
        details: 'No writable project endpoints are exposed.',
      ),
    );
    firstRunChecks = checks;
    notifyListeners();
  }

  Future<void> refreshFirstRunChecks() async {
    if (!initialized) {
      return;
    }
    if (projects.isEmpty) {
      try {
        projects = await _client.listProjects();
      } catch (_) {
        projects = <ProjectConfig>[];
      }
    }
    try {
      models = await _client.listModelStatus();
    } catch (_) {
      models = <ModelStatus>[];
    }
    await runFirstRunChecks();
  }

  bool get isReady => initialized && !firstRunMode;

  ProjectConfig? get selectedProject {
    if (selectedProjectId == null) {
      return null;
    }
    for (final project in projects) {
      if (project.projectId == selectedProjectId) {
        return project;
      }
    }
    return null;
  }

  TaskRecord? get selectedTask {
    if (selectedTaskId == null) {
      return null;
    }
    for (final task in tasks) {
      if (task.taskId == selectedTaskId) {
        return task;
      }
    }
    return null;
  }

  DraftRecord? get selectedDraft {
    if (selectedDraftId == null) {
      return null;
    }
    for (final draft in drafts) {
      if (draft.draftId == selectedDraftId) {
        return draft;
      }
    }
    return null;
  }

  ApprovalRecord? get selectedApproval {
    if (selectedApprovalId == null) {
      return null;
    }
    for (final approval in approvals) {
      if (approval.approvalId == selectedApprovalId) {
        return approval;
      }
    }
    return null;
  }

  DailyBriefRecord? get selectedBrief {
    if (selectedBriefId == null) {
      return null;
    }
    for (final brief in briefs) {
      if (brief.briefId == selectedBriefId) {
        return brief;
      }
    }
    return null;
  }

  Map<String, dynamic>? get selectedRecommendation {
    if (selectedRecommendationId == null) {
      return null;
    }
    for (final recommendation in projectRecommendations) {
      if (recommendation['recommendation_id'] == selectedRecommendationId) {
        return recommendation;
      }
    }
    return selectedRecommendationDetail;
  }

  Map<String, dynamic>? get selectedWorkPackage {
    if (selectedWorkPackageId == null) {
      return null;
    }
    for (final workPackage in workPackages) {
      if (workPackage['work_package_id'] == selectedWorkPackageId) {
        return workPackage;
      }
    }
    return selectedWorkPackageDetail;
  }

  void selectProject(String? projectId) {
    if (selectedProjectId == projectId) {
      return;
    }
    selectedProjectId = projectId;
    unawaited(refreshProgrammeWorkspace(projectId: projectId));
    notifyListeners();
  }

  void selectTask(String? taskId) {
    if (selectedTaskId == taskId) {
      return;
    }
    selectedTaskId = taskId;
    notifyListeners();
  }

  void selectDraft(String? draftId) {
    if (selectedDraftId == draftId) {
      return;
    }
    selectedDraftId = draftId;
    notifyListeners();
  }

  void selectApproval(String? approvalId) {
    if (selectedApprovalId == approvalId) {
      return;
    }
    selectedApprovalId = approvalId;
    notifyListeners();
  }

  void selectBrief(String? briefId) {
    if (selectedBriefId == briefId) {
      return;
    }
    selectedBriefId = briefId;
    notifyListeners();
  }

  void selectRecommendation(String? recommendationId) {
    if (selectedRecommendationId == recommendationId) {
      return;
    }
    selectedRecommendationId = recommendationId;
    unawaited(refreshSelectedRecommendation());
    notifyListeners();
  }

  void selectWorkPackage(String? workPackageId) {
    if (selectedWorkPackageId == workPackageId) {
      return;
    }
    selectedWorkPackageId = workPackageId;
    unawaited(refreshSelectedWorkPackage());
    notifyListeners();
  }

  void selectAction(String? actionId) {
    if (selectedActionId == actionId) {
      return;
    }
    selectedActionId = actionId;
    unawaited(refreshSelectedAction());
    notifyListeners();
  }

  void selectManifest(String? manifestId) {
    if (selectedManifestId == manifestId) {
      return;
    }
    selectedManifestId = manifestId;
    notifyListeners();
  }

  void selectReceipt(String? receiptId) {
    if (selectedReceiptId == receiptId) {
      return;
    }
    selectedReceiptId = receiptId;
    notifyListeners();
  }

  String get backendStatusLabel {
    return switch (backendState) {
      BackendConnectionState.connected => 'Connected',
      BackendConnectionState.connecting => 'Checking',
      BackendConnectionState.starting => 'Starting',
      BackendConnectionState.failed => 'Failed',
      BackendConnectionState.disconnected => 'Disconnected',
    };
  }

  String get backendCompatibilityLabel {
    return switch (backendCompatibilityState) {
      BackendCompatibilityState.compatible => 'Compatible',
      BackendCompatibilityState.compatibleWithWarnings =>
        'Compatible with warnings',
      BackendCompatibilityState.unknown => 'Unknown',
      BackendCompatibilityState.incompatible => 'Incompatible',
      BackendCompatibilityState.unreachable => 'Unreachable',
    };
  }

  Color get backendCompatibilityColor {
    return switch (backendCompatibilityState) {
      BackendCompatibilityState.compatible => const Color(0xFF2E7D32),
      BackendCompatibilityState.compatibleWithWarnings => const Color(
        0xFFE65100,
      ),
      BackendCompatibilityState.unknown => const Color(0xFFEF6C00),
      BackendCompatibilityState.incompatible => const Color(0xFFC62828),
      BackendCompatibilityState.unreachable => const Color(0xFF616161),
    };
  }

  Future<void> _saveSettings() async {
    _settingsStore ??= await _settingsStoreFuture;
    await _settingsStore!.save(settings);
  }

  bool _hasBackendProjectFiles(Directory root) {
    return File(
          '${root.path}${Platform.pathSeparator}pyproject.toml',
        ).existsSync() &&
        File(
          '${root.path}${Platform.pathSeparator}config${Platform.pathSeparator}projects.yaml',
        ).existsSync();
  }

  Future<void> _refreshCompatibilityState() async {
    final compatibility = await _client.integrationCompatibility();
    integrationCompatibility = compatibility;

    final status = _stringValue(
      compatibility,
      'status',
      fallback: 'unknown',
    ).toLowerCase();

    switch (status) {
      case 'compatible':
        backendCompatibilityState = BackendCompatibilityState.compatible;
        lastError = null;
        break;
      case 'compatible_with_warnings':
        backendCompatibilityState =
            BackendCompatibilityState.compatibleWithWarnings;
        lastError = _compatibilitySummary(compatibility);
        break;
      case 'client_too_old':
      case 'backend_too_old':
      case 'contract_mismatch':
        backendCompatibilityState = BackendCompatibilityState.incompatible;
        lastError = _compatibilitySummary(compatibility);
        break;
      case 'unavailable':
      case 'timeout':
        backendCompatibilityState = BackendCompatibilityState.unreachable;
        lastError = _compatibilitySummary(compatibility);
        break;
      case 'malformed_response':
      default:
        backendCompatibilityState = BackendCompatibilityState.unknown;
        lastError = _compatibilitySummary(compatibility);
        break;
    }
  }

  Future<bool> _canReachBackend() async {
    try {
      await _client.health();
      return true;
    } catch (_) {
      return false;
    }
  }

  void _recordBackendLog(String line) {
    backendLogs.add(line);
    if (backendLogs.length > 200) {
      backendLogs.removeAt(0);
    }
    notifyListeners();
  }

  String maskPath(String path) {
    final parts = path
        .replaceAll('\\', '/')
        .split('/')
        .where((part) => part.isNotEmpty)
        .toList();
    if (parts.isEmpty) {
      return path;
    }
    if (parts.length <= 2) {
      return parts.join('/');
    }
    return '.../${parts.sublist(parts.length - 2).join('/')}';
  }

  String _stringValue(
    Map<String, dynamic> map,
    String key, {
    String fallback = '',
  }) {
    final value = map[key];
    return value == null ? fallback : value.toString();
  }

  String _compatibilitySummary(Map<String, dynamic> compatibility) {
    final status = _stringValue(compatibility, 'status', fallback: 'unknown');
    final backendVersion = _stringValue(
      compatibility,
      'backend_version',
      fallback: health?.version ?? 'unknown',
    );
    final contractVersion = _stringValue(
      compatibility,
      'integration_contract_version',
      fallback: _stringValue(
        compatibility,
        'contract_version',
        fallback: 'unknown',
      ),
    );
    final capabilityVersion = _stringValue(
      compatibility,
      'capability_version',
      fallback: 'unknown',
    );
    if (status == 'compatible') {
      return 'GAIA compatibility check passed for backend $backendVersion (contract $contractVersion, capabilities $capabilityVersion).';
    }
    if (status == 'compatible_with_warnings') {
      return 'GAIA compatibility check reported warnings for backend $backendVersion (contract $contractVersion, capabilities $capabilityVersion).';
    }
    return 'GAIA compatibility check reported $status for backend $backendVersion (contract $contractVersion, capabilities $capabilityVersion).';
  }

  @override
  void notifyListeners() {
    if (_disposed) {
      return;
    }
    super.notifyListeners();
  }

  @override
  void dispose() {
    _disposed = true;
    _activeAskClient?.close();
    _activeAskClient = null;
    super.dispose();
  }
}
