import 'dart:async';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

import 'backend_api.dart';
import 'backend_process.dart';
import 'models.dart';
import 'settings_store.dart';

class FirstRunCheck {
  FirstRunCheck({required this.label, required this.passed, required this.details});

  final String label;
  final bool passed;
  final String details;
}

class GaiaAppController extends ChangeNotifier {
  GaiaAppController({
    GaiaSettingsStore? settingsStore,
    BackendProcessManager? backendProcessManager,
    GaiaBackendApi? backendApi,
  })  : _settingsStoreFuture = settingsStore == null ? GaiaSettingsStore.open() : Future.value(settingsStore),
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
  AskResponse? lastAskResponse;
  Map<String, String> reports = <String, String>{};
  String? selectedProjectId;
  List<FirstRunCheck> firstRunChecks = <FirstRunCheck>[];
  final List<String> backendLogs = <String>[];
  http.Client? _activeAskClient;
  bool _loading = false;
  BackendCompatibilityState backendCompatibilityState = BackendCompatibilityState.unreachable;

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
      selectedProjectId = settings.defaultProjectId.isEmpty ? null : settings.defaultProjectId;
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
      backendCompatibilityState = _compatibilityFromVersion(health!.version);
      if (backendCompatibilityState == BackendCompatibilityState.incompatible) {
        lastError = 'Backend version ${health!.version} is incompatible with the v0.3 desktop client.';
      } else {
        lastError = null;
      }
    } catch (error) {
      backendState = BackendConnectionState.disconnected;
      backendCompatibilityState = BackendCompatibilityState.unreachable;
      health = null;
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
      await _backendProcessManager.pruneLogs(retentionDays: settings.logRetentionDays);
      final session = await _backendProcessManager.start(
        onStdout: _recordBackendLog,
        onStderr: _recordBackendLog,
      );
      _recordBackendLog('Started backend process pid=${session.process.pid}');
      await _pollBackendHealth();
      settings = settings.copyWith(backendLaunchPreference: BackendLaunchPreference.startLocal);
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
    selectedProjectId ??= settings.defaultProjectId.isNotEmpty ? settings.defaultProjectId : (projects.isEmpty ? null : projects.first.projectId);
    if (selectedProjectId != null && projects.every((project) => project.projectId != selectedProjectId)) {
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
      snapshots = <RepositorySnapshot>[snapshot, ...snapshots.where((entry) => entry.projectId != projectId)].take(20).toList();
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
      auditEvents = (await _client.listAuditEvents(limit: 100)).map(AuditEvent.fromJson).toList();
    } catch (_) {
      auditEvents = <AuditEvent>[];
    }
    notifyListeners();
  }

  Future<void> refreshReport(String projectId, {ReportFormatPreference format = ReportFormatPreference.markdown}) async {
    reports[projectId] = await _client.foundationReport(projectId, format: format.name);
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
    checks.add(FirstRunCheck(
      label: 'Locate GAIA installation',
      passed: repoRoot.existsSync() && _hasBackendProjectFiles(repoRoot),
      details: repoRoot.path,
    ));
    checks.add(FirstRunCheck(
      label: 'Python virtual environment',
      passed: File(defaultPythonPath(repoRoot.path)).existsSync(),
      details: defaultPythonPath(repoRoot.path),
    ));
    checks.add(FirstRunCheck(
      label: 'Backend availability',
      passed: await _canReachBackend(),
      details: settings.backendUrl,
    ));
    checks.add(FirstRunCheck(
      label: 'Configured projects',
      passed: projects.isNotEmpty,
      details: '${projects.length} projects',
    ));
    checks.add(FirstRunCheck(
      label: 'MicroGrow access',
      passed: projects.any((project) => project.projectId == 'microgrow-v1'),
      details: 'microgrow-v1',
    ));
    checks.add(FirstRunCheck(
      label: 'Ollama availability',
      passed: models.any((status) => status.provider == 'ollama'),
      details: models
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
    ));
    checks.add(FirstRunCheck(
      label: 'Read-only operating mode',
      passed: projects.every((project) => project.access == 'read_only'),
      details: 'No writable project endpoints are exposed.',
    ));
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

  void selectProject(String? projectId) {
    if (selectedProjectId == projectId) {
      return;
    }
    selectedProjectId = projectId;
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
      BackendCompatibilityState.unknown => 'Unknown',
      BackendCompatibilityState.incompatible => 'Incompatible',
      BackendCompatibilityState.unreachable => 'Unreachable',
    };
  }

  Color get backendCompatibilityColor {
    return switch (backendCompatibilityState) {
      BackendCompatibilityState.compatible => const Color(0xFF2E7D32),
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
    return File('${root.path}${Platform.pathSeparator}pyproject.toml').existsSync() &&
        File('${root.path}${Platform.pathSeparator}config${Platform.pathSeparator}projects.yaml').existsSync();
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
    final parts = path.replaceAll('\\', '/').split('/').where((part) => part.isNotEmpty).toList();
    if (parts.isEmpty) {
      return path;
    }
    if (parts.length <= 2) {
      return parts.join('/');
    }
    return '.../${parts.sublist(parts.length - 2).join('/')}';
  }

  BackendCompatibilityState _compatibilityFromVersion(String version) {
    final parts = version.split('.');
    if (parts.length < 2) {
      return BackendCompatibilityState.unknown;
    }
    final major = int.tryParse(parts[0]);
    final minor = int.tryParse(parts[1]);
    if (major == null || minor == null) {
      return BackendCompatibilityState.unknown;
    }
    if (major == 0 && minor == 3) {
      return BackendCompatibilityState.compatible;
    }
    return BackendCompatibilityState.incompatible;
  }
}
