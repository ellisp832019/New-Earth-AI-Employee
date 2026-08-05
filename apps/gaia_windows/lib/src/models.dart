import 'dart:convert';

enum BackendConnectionState {
  disconnected,
  connecting,
  connected,
  starting,
  failed,
}

enum BackendCompatibilityState {
  compatible,
  unknown,
  incompatible,
  unreachable,
}

enum ThemePreference { system, light, dark }

enum BackendLaunchPreference { connectExisting, startLocal }

enum ReportFormatPreference { markdown, json }

class HealthResponse {
  HealthResponse({
    required this.status,
    required this.version,
    required this.databasePath,
    required this.fts5Available,
  });

  factory HealthResponse.fromJson(Map<String, dynamic> json) => HealthResponse(
        status: json['status'] as String? ?? 'unknown',
        version: json['version'] as String? ?? 'unknown',
        databasePath: json['database_path'] as String? ?? '',
        fts5Available: json['fts5_available'] as bool? ?? false,
      );

  final String status;
  final String version;
  final String databasePath;
  final bool fts5Available;
}

class ProjectConfig {
  ProjectConfig({
    required this.projectId,
    required this.name,
    required this.root,
    required this.access,
    required this.approvedExtensions,
    required this.excludedDirectories,
    required this.excludedFilenames,
    required this.importantPaths,
  });

  factory ProjectConfig.fromJson(Map<String, dynamic> json) => ProjectConfig(
        projectId: json['project_id'] as String? ?? '',
        name: json['name'] as String? ?? '',
        root: json['root'] as String? ?? '',
        access: json['access'] as String? ?? 'read_only',
        approvedExtensions: _stringList(json['approved_extensions']),
        excludedDirectories: _stringList(json['excluded_directories']),
        excludedFilenames: _stringList(json['excluded_filenames']),
        importantPaths: _stringList(json['important_paths']),
      );

  final String projectId;
  final String name;
  final String root;
  final String access;
  final List<String> approvedExtensions;
  final List<String> excludedDirectories;
  final List<String> excludedFilenames;
  final List<String> importantPaths;
}

class GitState {
  GitState({
    required this.repositoryRoot,
    required this.branch,
    required this.commitSha,
    required this.isClean,
    required this.statusPorcelain,
    required this.recentCommits,
    required this.branches,
    required this.tags,
    required this.remotes,
    required this.ahead,
    required this.behind,
    required this.trackedFileCount,
    required this.untrackedFiles,
    required this.changedFiles,
    required this.warnings,
  });

  factory GitState.fromJson(Map<String, dynamic> json) => GitState(
        repositoryRoot: json['repository_root'] as String? ?? '',
        branch: json['branch'] as String?,
        commitSha: json['commit_sha'] as String?,
        isClean: json['is_clean'] as bool? ?? false,
        statusPorcelain: _stringList(json['status_porcelain']),
        recentCommits: _stringList(json['recent_commits']),
        branches: _stringList(json['branches']),
        tags: _stringList(json['tags']),
        remotes: _stringList(json['remotes']),
        ahead: json['ahead'] as int?,
        behind: json['behind'] as int?,
        trackedFileCount: json['tracked_file_count'] as int? ?? 0,
        untrackedFiles: _stringList(json['untracked_files']),
        changedFiles: _stringList(json['changed_files']),
        warnings: _stringList(json['warnings']),
      );

  final String repositoryRoot;
  final String? branch;
  final String? commitSha;
  final bool isClean;
  final List<String> statusPorcelain;
  final List<String> recentCommits;
  final List<String> branches;
  final List<String> tags;
  final List<String> remotes;
  final int? ahead;
  final int? behind;
  final int trackedFileCount;
  final List<String> untrackedFiles;
  final List<String> changedFiles;
  final List<String> warnings;
}

class RepositorySnapshot {
  RepositorySnapshot({
    required this.snapshotId,
    required this.projectId,
    required this.projectName,
    required this.projectRoot,
    required this.createdAt,
    required this.git,
    required this.documentCount,
    required this.indexedCount,
    required this.skippedCount,
    required this.failedCount,
    required this.countsByExtension,
    required this.scanWarnings,
    required this.importantPaths,
  });

  factory RepositorySnapshot.fromJson(Map<String, dynamic> json) => RepositorySnapshot(
        snapshotId: json['snapshot_id'] as String? ?? '',
        projectId: json['project_id'] as String? ?? '',
        projectName: json['project_name'] as String? ?? '',
        projectRoot: json['project_root'] as String? ?? '',
        createdAt: DateTime.parse(json['created_at'] as String? ?? DateTime.now().toIso8601String()),
        git: GitState.fromJson((json['git'] as Map?)?.cast<String, dynamic>() ?? const <String, dynamic>{}),
        documentCount: json['document_count'] as int? ?? 0,
        indexedCount: json['indexed_count'] as int? ?? 0,
        skippedCount: json['skipped_count'] as int? ?? 0,
        failedCount: json['failed_count'] as int? ?? 0,
        countsByExtension: _mapOfInt(json['counts_by_extension']),
        scanWarnings: _stringList(json['scan_warnings']),
        importantPaths: _mapOfBool(json['important_paths']),
      );

  final String snapshotId;
  final String projectId;
  final String projectName;
  final String projectRoot;
  final DateTime createdAt;
  final GitState git;
  final int documentCount;
  final int indexedCount;
  final int skippedCount;
  final int failedCount;
  final Map<String, int> countsByExtension;
  final List<String> scanWarnings;
  final Map<String, bool> importantPaths;
}

class DocumentRecord {
  DocumentRecord({
    required this.projectId,
    required this.relativePath,
    required this.extension,
    required this.sizeBytes,
    required this.modifiedUtc,
    required this.sha256,
    required this.indexingStatus,
    required this.warning,
  });

  factory DocumentRecord.fromJson(Map<String, dynamic> json) => DocumentRecord(
        projectId: json['project_id'] as String? ?? '',
        relativePath: json['relative_path'] as String? ?? '',
        extension: json['extension'] as String? ?? '',
        sizeBytes: json['size_bytes'] as int? ?? 0,
        modifiedUtc: DateTime.parse(json['modified_utc'] as String? ?? DateTime.now().toIso8601String()),
        sha256: json['sha256'] as String? ?? '',
        indexingStatus: json['indexing_status'] as String? ?? '',
        warning: json['warning'] as String?,
      );

  final String projectId;
  final String relativePath;
  final String extension;
  final int sizeBytes;
  final DateTime modifiedUtc;
  final String sha256;
  final String indexingStatus;
  final String? warning;
}

class SearchResult {
  SearchResult({
    required this.relativePath,
    required this.extension,
    required this.snippet,
    required this.score,
  });

  factory SearchResult.fromJson(Map<String, dynamic> json) => SearchResult(
        relativePath: json['relative_path'] as String? ?? '',
        extension: json['extension'] as String? ?? '',
        snippet: json['snippet'] as String? ?? '',
        score: (json['score'] as num?)?.toDouble(),
      );

  final String relativePath;
  final String extension;
  final String snippet;
  final double? score;
}

class ModelStatus {
  ModelStatus({
    required this.provider,
    required this.available,
    required this.modelName,
    required this.endpointIdentity,
    required this.details,
  });

  factory ModelStatus.fromJson(Map<String, dynamic> json) => ModelStatus(
        provider: json['provider'] as String? ?? '',
        available: json['available'] as bool? ?? false,
        modelName: json['model_name'] as String?,
        endpointIdentity: json['endpoint_identity'] as String?,
        details: json['details'] as String?,
      );

  final String provider;
  final bool available;
  final String? modelName;
  final String? endpointIdentity;
  final String? details;
}

class EvidenceItem {
  EvidenceItem({
    required this.evidenceId,
    required this.sourceKind,
    required this.projectId,
    required this.sourcePath,
    required this.title,
    required this.snippet,
    required this.score,
    required this.citations,
    required this.warning,
  });

  factory EvidenceItem.fromJson(Map<String, dynamic> json) => EvidenceItem(
        evidenceId: json['evidence_id'] as String? ?? '',
        sourceKind: json['source_kind'] as String? ?? '',
        projectId: json['project_id'] as String? ?? '',
        sourcePath: json['source_path'] as String? ?? '',
        title: json['title'] as String? ?? '',
        snippet: json['snippet'] as String? ?? '',
        score: (json['score'] as num?)?.toDouble() ?? 0,
        citations: _stringList(json['citations']),
        warning: json['warning'] as String?,
      );

  final String evidenceId;
  final String sourceKind;
  final String projectId;
  final String sourcePath;
  final String title;
  final String snippet;
  final double score;
  final List<String> citations;
  final String? warning;
}

class AskResponse {
  AskResponse({
    required this.runId,
    required this.projectId,
    required this.question,
    required this.questionCategory,
    required this.snapshotId,
    required this.provider,
    required this.modelName,
    required this.answer,
    required this.evidence,
    required this.confidence,
    required this.warnings,
    required this.promptInjectionWarnings,
    required this.deterministicOnly,
    required this.structured,
    required this.startedAt,
    required this.finishedAt,
  });

  factory AskResponse.fromJson(Map<String, dynamic> json) => AskResponse(
        runId: json['run_id'] as String? ?? '',
        projectId: json['project_id'] as String? ?? '',
        question: json['question'] as String? ?? '',
        questionCategory: json['question_category'] as String? ?? '',
        snapshotId: json['snapshot_id'] as String?,
        provider: json['provider'] as String? ?? '',
        modelName: json['model_name'] as String?,
        answer: json['answer'] as String? ?? '',
        evidence: _listOfMap(json['evidence']).map(EvidenceItem.fromJson).toList(),
        confidence: json['confidence'] as String? ?? 'low',
        warnings: _stringList(json['warnings']),
        promptInjectionWarnings: _stringList(json['prompt_injection_warnings']),
        deterministicOnly: json['deterministic_only'] as bool? ?? false,
        structured: json['structured'] as bool? ?? false,
        startedAt: DateTime.parse(json['started_at'] as String? ?? DateTime.now().toIso8601String()),
        finishedAt: DateTime.parse(json['finished_at'] as String? ?? DateTime.now().toIso8601String()),
      );

  final String runId;
  final String projectId;
  final String question;
  final String questionCategory;
  final String? snapshotId;
  final String provider;
  final String? modelName;
  final String answer;
  final List<EvidenceItem> evidence;
  final String confidence;
  final List<String> warnings;
  final List<String> promptInjectionWarnings;
  final bool deterministicOnly;
  final bool structured;
  final DateTime startedAt;
  final DateTime finishedAt;
}

class AgentRunRecord {
  AgentRunRecord({
    required this.runId,
    required this.projectId,
    required this.question,
    required this.questionCategory,
    required this.snapshotId,
    required this.provider,
    required this.modelName,
    required this.status,
    required this.confidence,
    required this.startTimestamp,
    required this.finishTimestamp,
    required this.warnings,
    required this.promptInjectionWarnings,
    required this.structuredAnswer,
  });

  factory AgentRunRecord.fromJson(Map<String, dynamic> json) => AgentRunRecord(
        runId: json['run_id'] as String? ?? '',
        projectId: json['project_id'] as String? ?? '',
        question: json['question'] as String? ?? '',
        questionCategory: json['question_category'] as String? ?? '',
        snapshotId: json['snapshot_id'] as String?,
        provider: json['provider'] as String? ?? '',
        modelName: json['model_name'] as String?,
        status: json['status'] as String? ?? '',
        confidence: json['confidence'] as String? ?? '',
        startTimestamp: DateTime.parse(json['start_timestamp'] as String? ?? DateTime.now().toIso8601String()),
        finishTimestamp: DateTime.parse(json['finish_timestamp'] as String? ?? DateTime.now().toIso8601String()),
        warnings: _stringList(json['warnings']),
        promptInjectionWarnings: _stringList(json['prompt_injection_warnings']),
        structuredAnswer: (json['structured_answer'] as Map?)?.cast<String, dynamic>() ?? const <String, dynamic>{},
      );

  final String runId;
  final String projectId;
  final String question;
  final String questionCategory;
  final String? snapshotId;
  final String provider;
  final String? modelName;
  final String status;
  final String confidence;
  final DateTime startTimestamp;
  final DateTime finishTimestamp;
  final List<String> warnings;
  final List<String> promptInjectionWarnings;
  final Map<String, dynamic> structuredAnswer;
}

class AuditEvent {
  AuditEvent({
    required this.eventId,
    required this.timestamp,
    required this.category,
    required this.operation,
    required this.projectId,
    required this.outcome,
    required this.metadata,
    required this.errorClassification,
  });

  factory AuditEvent.fromJson(Map<String, dynamic> json) => AuditEvent(
        eventId: json['event_id'] as String? ?? '',
        timestamp: DateTime.parse(json['timestamp'] as String? ?? DateTime.now().toIso8601String()),
        category: json['category'] as String? ?? '',
        operation: json['operation'] as String? ?? '',
        projectId: json['project_id'] as String?,
        outcome: json['outcome'] as String? ?? '',
        metadata: (json['metadata'] as Map?)?.cast<String, dynamic>() ?? const <String, dynamic>{},
        errorClassification: json['error_classification'] as String?,
      );

  final String eventId;
  final DateTime timestamp;
  final String category;
  final String operation;
  final String? projectId;
  final String outcome;
  final Map<String, dynamic> metadata;
  final String? errorClassification;
}

class AskRequestBody {
  AskRequestBody({
    required this.projectId,
    required this.question,
    this.provider,
    this.model,
    this.evidenceLimit = 8,
    this.refreshSnapshot = false,
    this.deterministicOnly = false,
  });

  final String projectId;
  final String question;
  final String? provider;
  final String? model;
  final int evidenceLimit;
  final bool refreshSnapshot;
  final bool deterministicOnly;

  Map<String, dynamic> toJson() => <String, dynamic>{
        'project_id': projectId,
        'question': question,
        'provider': provider,
        'model': model,
        'evidence_limit': evidenceLimit,
        'refresh_snapshot': refreshSnapshot,
        'deterministic_only': deterministicOnly,
      }..removeWhere((key, value) => value == null);
}

List<String> _stringList(dynamic value) {
  if (value is List) {
    return value.map((item) => item.toString()).toList();
  }
  return <String>[];
}

Map<String, int> _mapOfInt(dynamic value) {
  if (value is Map) {
    return value.map((key, item) => MapEntry(key.toString(), (item as num).toInt()));
  }
  return <String, int>{};
}

Map<String, bool> _mapOfBool(dynamic value) {
  if (value is Map) {
    return value.map((key, item) => MapEntry(key.toString(), item is bool ? item : item.toString() == 'true'));
  }
  return <String, bool>{};
}

List<Map<String, dynamic>> _listOfMap(dynamic value) {
  if (value is List) {
    return value
        .whereType<Map>()
        .map((item) => item.cast<String, dynamic>())
        .toList();
  }
  return <Map<String, dynamic>>[];
}

String encodeJsonPretty(Object? value) => const JsonEncoder.withIndent('  ').convert(value);
