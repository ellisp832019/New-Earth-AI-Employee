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
    required this.backendProductVersion,
    required this.minimumSupportedApiVersion,
    required this.maximumTestedApiVersion,
    required this.integrationContractVersion,
    required this.clientPackageVersion,
    required this.backendVersion,
    required this.status,
    required this.loopbackOnly,
    required this.capabilityVersion,
    required this.capabilities,
    required this.capabilityCatalog,
    required this.degradedFeatures,
    required this.deprecationWarnings,
  });

  factory GaiaCompatibility.fromJson(Map<String, dynamic> json) => GaiaCompatibility(
        backendProductVersion: json['backend_product_version'] as String? ?? json['backend_version'] as String? ?? 'unknown',
        minimumSupportedApiVersion: json['minimum_supported_api_version'] as String? ?? 'unknown',
        maximumTestedApiVersion: json['maximum_tested_api_version'] as String? ?? 'unknown',
        integrationContractVersion: json['integration_contract_version'] as String? ?? json['contract_version'] as String? ?? 'unknown',
        clientPackageVersion: json['client_package_version'] as String? ?? 'unknown',
        backendVersion: json['backend_version'] as String? ?? json['backend_product_version'] as String? ?? 'unknown',
        status: json['status'] as String? ?? 'unknown',
        loopbackOnly: json['loopback_only'] as bool? ?? true,
        capabilityVersion: json['capability_version'] as String? ?? 'unknown',
        capabilities: (json['capabilities'] as List<dynamic>? ?? const <dynamic>[]).whereType<String>().toList(),
        capabilityCatalog: (json['capability_catalog'] as List<dynamic>? ?? const <dynamic>[])
            .whereType<Map>()
            .map((item) => GaiaCapabilityDescriptor.fromJson(item.cast<String, dynamic>()))
            .toList(),
        degradedFeatures: (json['degraded_features'] as List<dynamic>? ?? const <dynamic>[]).whereType<String>().toList(),
        deprecationWarnings: (json['deprecation_warnings'] as List<dynamic>? ?? const <dynamic>[]).whereType<String>().toList(),
      );

  final String backendProductVersion;
  final String minimumSupportedApiVersion;
  final String maximumTestedApiVersion;
  final String integrationContractVersion;
  final String clientPackageVersion;
  final String backendVersion;
  final String status;
  final bool loopbackOnly;
  final String capabilityVersion;
  final List<String> capabilities;
  final List<GaiaCapabilityDescriptor> capabilityCatalog;
  final List<String> degradedFeatures;
  final List<String> deprecationWarnings;
}

class GaiaCapabilityDescriptor {
  GaiaCapabilityDescriptor({
    required this.capabilityId,
    required this.version,
    required this.state,
    required this.summary,
    required this.authorityLevel,
    required this.gatedBy,
    required this.requiresSigning,
    required this.enabled,
  });

  factory GaiaCapabilityDescriptor.fromJson(Map<String, dynamic> json) => GaiaCapabilityDescriptor(
        capabilityId: json['capability_id'] as String? ?? '',
        version: json['version'] as String? ?? '',
        state: json['state'] as String? ?? 'disabled',
        summary: json['summary'] as String? ?? '',
        authorityLevel: json['authority_level'] as String? ?? 'read_only',
        gatedBy: (json['gated_by'] as List<dynamic>? ?? const <dynamic>[]).whereType<String>().toList(),
        requiresSigning: json['requires_signing'] as bool? ?? false,
        enabled: json['enabled'] as bool? ?? false,
      );

  final String capabilityId;
  final String version;
  final String state;
  final String summary;
  final String authorityLevel;
  final List<String> gatedBy;
  final bool requiresSigning;
  final bool enabled;
}

class GaiaSigningKeySummary {
  GaiaSigningKeySummary({
    required this.keyId,
    required this.keyName,
    required this.publicKey,
    required this.status,
    required this.createdAt,
    required this.revokedAt,
    required this.rotatedFromKeyId,
    required this.lastUsedAt,
    required this.signingEnabled,
  });

  factory GaiaSigningKeySummary.fromJson(Map<String, dynamic> json) => GaiaSigningKeySummary(
        keyId: json['key_id'] as String? ?? '',
        keyName: json['key_name'] as String? ?? '',
        publicKey: json['public_key'] as String? ?? '',
        status: json['status'] as String? ?? 'unknown',
        createdAt: DateTime.parse(json['created_at'] as String? ?? DateTime.now().toIso8601String()),
        revokedAt: json['revoked_at'] == null ? null : DateTime.parse(json['revoked_at'] as String),
        rotatedFromKeyId: json['rotated_from_key_id'] as String?,
        lastUsedAt: json['last_used_at'] == null ? null : DateTime.parse(json['last_used_at'] as String),
        signingEnabled: json['signing_enabled'] as bool? ?? false,
      );

  final String keyId;
  final String keyName;
  final String publicKey;
  final String status;
  final DateTime createdAt;
  final DateTime? revokedAt;
  final String? rotatedFromKeyId;
  final DateTime? lastUsedAt;
  final bool signingEnabled;
}

class GaiaProvenanceManifest {
  GaiaProvenanceManifest({
    required this.manifestId,
    required this.manifestVersion,
    required this.subjectKind,
    required this.subjectId,
    required this.subjectVersion,
    required this.contentHash,
    required this.canonicalJson,
    required this.createdAt,
    required this.signingKeyId,
    required this.signature,
    required this.signatureStatus,
    required this.keyStatus,
    required this.chainId,
    required this.chainSequence,
    required this.packagePath,
    required this.metadata,
  });

  factory GaiaProvenanceManifest.fromJson(Map<String, dynamic> json) => GaiaProvenanceManifest(
        manifestId: json['manifest_id'] as String? ?? '',
        manifestVersion: json['manifest_version'] as int? ?? 1,
        subjectKind: json['subject_kind'] as String? ?? '',
        subjectId: json['subject_id'] as String? ?? '',
        subjectVersion: json['subject_version'] as int? ?? 1,
        contentHash: json['content_hash'] as String? ?? '',
        canonicalJson: json['canonical_json'] as String? ?? '',
        createdAt: DateTime.parse(json['created_at'] as String? ?? DateTime.now().toIso8601String()),
        signingKeyId: json['signing_key_id'] as String?,
        signature: json['signature'] as String?,
        signatureStatus: json['signature_status'] as String? ?? 'unsigned',
        keyStatus: json['key_status'] as String? ?? 'unknown',
        chainId: json['chain_id'] as String?,
        chainSequence: json['chain_sequence'] as int?,
        packagePath: json['package_path'] as String?,
        metadata: (json['metadata'] as Map<String, dynamic>? ?? <String, dynamic>{}),
      );

  final String manifestId;
  final int manifestVersion;
  final String subjectKind;
  final String subjectId;
  final int subjectVersion;
  final String contentHash;
  final String canonicalJson;
  final DateTime createdAt;
  final String? signingKeyId;
  final String? signature;
  final String signatureStatus;
  final String keyStatus;
  final String? chainId;
  final int? chainSequence;
  final String? packagePath;
  final Map<String, dynamic> metadata;
}

class GaiaTrustAlert {
  GaiaTrustAlert({
    required this.alertId,
    required this.alertType,
    required this.severity,
    required this.status,
    required this.title,
    required this.message,
    required this.sourceKind,
    required this.sourceId,
    required this.createdAt,
    required this.acknowledgedAt,
    required this.metadata,
  });

  factory GaiaTrustAlert.fromJson(Map<String, dynamic> json) => GaiaTrustAlert(
        alertId: json['alert_id'] as String? ?? '',
        alertType: json['alert_type'] as String? ?? '',
        severity: json['severity'] as String? ?? 'info',
        status: json['status'] as String? ?? 'open',
        title: json['title'] as String? ?? '',
        message: json['message'] as String? ?? '',
        sourceKind: json['source_kind'] as String? ?? '',
        sourceId: json['source_id'] as String? ?? '',
        createdAt: DateTime.parse(json['created_at'] as String? ?? DateTime.now().toIso8601String()),
        acknowledgedAt: json['acknowledged_at'] == null ? null : DateTime.parse(json['acknowledged_at'] as String),
        metadata: (json['metadata'] as Map<String, dynamic>? ?? <String, dynamic>{}),
      );

  final String alertId;
  final String alertType;
  final String severity;
  final String status;
  final String title;
  final String message;
  final String sourceKind;
  final String sourceId;
  final DateTime createdAt;
  final DateTime? acknowledgedAt;
  final Map<String, dynamic> metadata;
}

class GaiaRetentionReport {
  GaiaRetentionReport({
    required this.generatedAt,
    required this.policyCount,
    required this.planCount,
    required this.receiptCount,
    required this.enabledPolicyCount,
    required this.issues,
    required this.summary,
  });

  factory GaiaRetentionReport.fromJson(Map<String, dynamic> json) => GaiaRetentionReport(
        generatedAt: DateTime.parse(json['generated_at'] as String? ?? DateTime.now().toIso8601String()),
        policyCount: json['policy_count'] as int? ?? 0,
        planCount: json['plan_count'] as int? ?? 0,
        receiptCount: json['receipt_count'] as int? ?? 0,
        enabledPolicyCount: json['enabled_policy_count'] as int? ?? 0,
        issues: (json['issues'] as List<dynamic>? ?? const <dynamic>[]).whereType<String>().toList(),
        summary: (json['summary'] as Map<String, dynamic>? ?? <String, dynamic>{}),
      );

  final DateTime generatedAt;
  final int policyCount;
  final int planCount;
  final int receiptCount;
  final int enabledPolicyCount;
  final List<String> issues;
  final Map<String, dynamic> summary;
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
    required this.chainId,
    required this.chainSequence,
    required this.previousReceiptHash,
    required this.receiptContentHash,
    required this.verificationStatus,
  });

  factory GaiaExecutionReceipt.fromJson(Map<String, dynamic> json) => GaiaExecutionReceipt(
        receiptId: json['receipt_id'] as String? ?? '',
        actionId: json['action_id'] as String? ?? '',
        manifestId: json['manifest_id'] as String? ?? '',
        manifestVersion: json['manifest_version'] as int? ?? 0,
        targetPath: json['target_path'] as String? ?? '',
        resultingHash: json['resulting_hash'] as String? ?? '',
        timestamp: DateTime.parse(json['timestamp'] as String? ?? DateTime.now().toIso8601String()),
        chainId: json['chain_id'] as String?,
        chainSequence: json['chain_sequence'] as int?,
        previousReceiptHash: json['previous_receipt_hash'] as String?,
        receiptContentHash: json['receipt_content_hash'] as String?,
        verificationStatus: json['verification_status'] as String? ?? 'unknown',
      );

  final String receiptId;
  final String actionId;
  final String manifestId;
  final int manifestVersion;
  final String targetPath;
  final String resultingHash;
  final DateTime timestamp;
  final String? chainId;
  final int? chainSequence;
  final String? previousReceiptHash;
  final String? receiptContentHash;
  final String verificationStatus;
}

class GaiaReceiptVerification {
  GaiaReceiptVerification({
    required this.receiptId,
    required this.chainId,
    required this.chainSequence,
    required this.status,
    required this.previousReceiptHash,
    required this.receiptContentHash,
    required this.warnings,
  });

  factory GaiaReceiptVerification.fromJson(Map<String, dynamic> json) => GaiaReceiptVerification(
        receiptId: json['receipt_id'] as String? ?? '',
        chainId: json['chain_id'] as String?,
        chainSequence: json['chain_sequence'] as int?,
        status: json['status'] as String? ?? 'unknown',
        previousReceiptHash: json['previous_receipt_hash'] as String?,
        receiptContentHash: json['receipt_content_hash'] as String?,
        warnings: (json['warnings'] as List<dynamic>? ?? const <dynamic>[]).whereType<String>().toList(),
      );

  final String receiptId;
  final String? chainId;
  final int? chainSequence;
  final String status;
  final String? previousReceiptHash;
  final String? receiptContentHash;
  final List<String> warnings;
}

class GaiaActionTemplate {
  GaiaActionTemplate({
    required this.templateId,
    required this.templateVersion,
    required this.title,
    required this.description,
    required this.permittedActionType,
    required this.requiredInputs,
    required this.optionalInputs,
    required this.targetPathPattern,
    required this.allowedExtension,
    required this.riskLevel,
    required this.approvalRequired,
    required this.previewRenderer,
    required this.retentionClass,
    required this.enabled,
  });

  factory GaiaActionTemplate.fromJson(Map<String, dynamic> json) => GaiaActionTemplate(
        templateId: json['template_id'] as String? ?? '',
        templateVersion: json['template_version'] as int? ?? 1,
        title: json['title'] as String? ?? '',
        description: json['description'] as String? ?? '',
        permittedActionType: json['permitted_action_type'] as String? ?? '',
        requiredInputs: (json['required_inputs'] as List<dynamic>? ?? const <dynamic>[]).whereType<String>().toList(),
        optionalInputs: (json['optional_inputs'] as List<dynamic>? ?? const <dynamic>[]).whereType<String>().toList(),
        targetPathPattern: json['target_path_pattern'] as String? ?? '',
        allowedExtension: json['allowed_extension'] as String? ?? '',
        riskLevel: json['risk_level'] as String? ?? 'low',
        approvalRequired: json['approval_required'] as bool? ?? true,
        previewRenderer: json['preview_renderer'] as String? ?? 'markdown',
        retentionClass: json['retention_class'] as String? ?? 'standard',
        enabled: json['enabled'] as bool? ?? true,
      );

  final String templateId;
  final int templateVersion;
  final String title;
  final String description;
  final String permittedActionType;
  final List<String> requiredInputs;
  final List<String> optionalInputs;
  final String targetPathPattern;
  final String allowedExtension;
  final String riskLevel;
  final bool approvalRequired;
  final String previewRenderer;
  final String retentionClass;
  final bool enabled;
}

class GaiaRetentionPolicy {
  GaiaRetentionPolicy({
    required this.policyId,
    required this.policyVersion,
    required this.retentionClass,
    required this.minimumCopies,
    required this.minimumAgeDays,
    required this.maximumAgeDays,
    required this.maximumCount,
    required this.preserveFailedActions,
    required this.preserveRollbacks,
    required this.preserveAuditLinkedRecords,
    required this.dryRunRequired,
    required this.approvalRequired,
    required this.enabled,
  });

  factory GaiaRetentionPolicy.fromJson(Map<String, dynamic> json) => GaiaRetentionPolicy(
        policyId: json['policy_id'] as String? ?? '',
        policyVersion: json['policy_version'] as int? ?? 1,
        retentionClass: json['retention_class'] as String? ?? 'default',
        minimumCopies: json['minimum_copies'] as int? ?? 1,
        minimumAgeDays: json['minimum_age_days'] as int? ?? 0,
        maximumAgeDays: json['maximum_age_days'] as int?,
        maximumCount: json['maximum_count'] as int?,
        preserveFailedActions: json['preserve_failed_actions'] as bool? ?? true,
        preserveRollbacks: json['preserve_rollbacks'] as bool? ?? true,
        preserveAuditLinkedRecords: json['preserve_audit_linked_records'] as bool? ?? true,
        dryRunRequired: json['dry_run_required'] as bool? ?? true,
        approvalRequired: json['approval_required'] as bool? ?? true,
        enabled: json['enabled'] as bool? ?? true,
      );

  final String policyId;
  final int policyVersion;
  final String retentionClass;
  final int minimumCopies;
  final int minimumAgeDays;
  final int? maximumAgeDays;
  final int? maximumCount;
  final bool preserveFailedActions;
  final bool preserveRollbacks;
  final bool preserveAuditLinkedRecords;
  final bool dryRunRequired;
  final bool approvalRequired;
  final bool enabled;
}

class GaiaRetentionPlan {
  GaiaRetentionPlan({
    required this.planId,
    required this.policyId,
    required this.planHash,
    required this.approvedHash,
    required this.createdAt,
    required this.status,
    required this.payload,
  });

  factory GaiaRetentionPlan.fromJson(Map<String, dynamic> json) => GaiaRetentionPlan(
        planId: json['plan_id'] as String? ?? '',
        policyId: json['policy_id'] as String? ?? '',
        planHash: json['plan_hash'] as String? ?? '',
        approvedHash: json['approved_hash'] as String?,
        createdAt: DateTime.parse(json['created_at'] as String? ?? DateTime.now().toIso8601String()),
        status: json['status'] as String? ?? 'dry_run',
        payload: (json['payload'] as Map<String, dynamic>? ?? <String, dynamic>{}),
      );

  final String planId;
  final String policyId;
  final String planHash;
  final String? approvedHash;
  final DateTime createdAt;
  final String status;
  final Map<String, dynamic> payload;
}

class GaiaReviewPackageResult {
  GaiaReviewPackageResult({required this.status, required this.reason});

  factory GaiaReviewPackageResult.fromJson(Map<String, dynamic> json) => GaiaReviewPackageResult(
        status: json['status'] as String? ?? 'unknown',
        reason: json['reason'] as String? ?? '',
      );

  final String status;
  final String reason;
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
