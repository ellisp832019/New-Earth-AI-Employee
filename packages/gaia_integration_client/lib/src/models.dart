import 'dart:convert';

class GaiaClientError implements Exception {
  GaiaClientError(this.message, {this.statusCode});

  final String message;
  final int? statusCode;

  @override
  String toString() => statusCode == null ? message : '[$statusCode] $message';
}

class GaiaHealth {
  GaiaHealth({
    required this.status,
    required this.version,
    required this.databasePath,
    required this.fts5Available,
  });

  factory GaiaHealth.fromJson(Map<String, dynamic> json) => GaiaHealth(
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

class GaiaCompatibility {
  GaiaCompatibility({
    required this.backendVersion,
    required this.contractVersion,
    required this.status,
    required this.loopbackOnly,
    required this.capabilities,
  });

  factory GaiaCompatibility.fromJson(Map<String, dynamic> json) => GaiaCompatibility(
        backendVersion: json['backend_version'] as String? ?? 'unknown',
        contractVersion: json['contract_version'] as String? ?? 'unknown',
        status: json['status'] as String? ?? 'unknown',
        loopbackOnly: json['loopback_only'] as bool? ?? true,
        capabilities: (json['capabilities'] as List<dynamic>? ?? const <dynamic>[])
            .whereType<String>()
            .toList(),
      );

  final String backendVersion;
  final String contractVersion;
  final String status;
  final bool loopbackOnly;
  final List<String> capabilities;
}

class GaiaProjectSummary {
  GaiaProjectSummary({
    required this.projectId,
    required this.name,
    required this.root,
  });

  factory GaiaProjectSummary.fromJson(Map<String, dynamic> json) => GaiaProjectSummary(
        projectId: json['project_id'] as String? ?? '',
        name: json['name'] as String? ?? '',
        root: json['root'] as String? ?? '',
      );

  final String projectId;
  final String name;
  final String root;
}

class GaiaSummary {
  GaiaSummary({
    required this.projectId,
    required this.total,
    required this.activeCount,
    required this.pendingCount,
    required this.completedCount,
  });

  factory GaiaSummary.fromJson(Map<String, dynamic> json) => GaiaSummary(
        projectId: json['project_id'] as String? ?? '',
        total: json['total'] as int? ?? 0,
        activeCount: json['active'] as int? ?? 0,
        pendingCount: json['pending'] as int? ?? 0,
        completedCount: json['completed'] as int? ?? 0,
      );

  final String projectId;
  final int total;
  final int activeCount;
  final int pendingCount;
  final int completedCount;
}

class GaiaActionSummary {
  GaiaActionSummary({
    required this.projectId,
    required this.total,
    required this.proposed,
    required this.awaitingApproval,
    required this.approved,
    required this.completed,
    required this.failed,
    required this.invalidated,
    required this.rolledBack,
  });

  factory GaiaActionSummary.fromJson(Map<String, dynamic> json) => GaiaActionSummary(
        projectId: json['project_id'] as String? ?? '',
        total: json['total'] as int? ?? 0,
        proposed: json['proposed'] as int? ?? 0,
        awaitingApproval: json['awaiting_approval'] as int? ?? 0,
        approved: json['approved'] as int? ?? 0,
        completed: json['completed'] as int? ?? 0,
        failed: json['failed'] as int? ?? 0,
        invalidated: json['invalidated'] as int? ?? 0,
        rolledBack: json['rolled_back'] as int? ?? 0,
      );

  final String projectId;
  final int total;
  final int proposed;
  final int awaitingApproval;
  final int approved;
  final int completed;
  final int failed;
  final int invalidated;
  final int rolledBack;
}

class GaiaExecutionReceipt {
  GaiaExecutionReceipt({
    required this.receiptId,
    required this.actionId,
    required this.manifestId,
    required this.manifestVersion,
    required this.targetPath,
    required this.resultingHash,
    required this.timestamp,
  });

  factory GaiaExecutionReceipt.fromJson(Map<String, dynamic> json) => GaiaExecutionReceipt(
        receiptId: json['receipt_id'] as String? ?? '',
        actionId: json['action_id'] as String? ?? '',
        manifestId: json['manifest_id'] as String? ?? '',
        manifestVersion: json['manifest_version'] as int? ?? 0,
        targetPath: json['target_path'] as String? ?? '',
        resultingHash: json['resulting_hash'] as String? ?? '',
        timestamp: DateTime.parse(json['timestamp'] as String? ?? DateTime.now().toIso8601String()),
      );

  final String receiptId;
  final String actionId;
  final String manifestId;
  final int manifestVersion;
  final String targetPath;
  final String resultingHash;
  final DateTime timestamp;
}

class GaiaDailyBrief {
  GaiaDailyBrief({
    required this.briefId,
    required this.projectId,
    required this.title,
    required this.markdown,
  });

  factory GaiaDailyBrief.fromJson(Map<String, dynamic> json) => GaiaDailyBrief(
        briefId: json['brief_id'] as String? ?? '',
        projectId: json['project_id'] as String? ?? '',
        title: json['title'] as String? ?? '',
        markdown: json['markdown'] as String? ?? '',
      );

  final String briefId;
  final String projectId;
  final String title;
  final String markdown;
}

Map<String, String> stringQuery(Map<String, Object?> values) {
  return values.map(
    (key, value) => MapEntry(key, value == null ? '' : value.toString()),
  )..removeWhere((key, value) => value.isEmpty);
}

String jsonEncodeBody(Map<String, Object?> body) => jsonEncode(body);
