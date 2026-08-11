import 'package:meta/meta.dart';

@immutable
class GaiaProgrammeSummaryCounts {
  const GaiaProgrammeSummaryCounts({
    required this.projectCount,
    required this.healthStatusCounts,
    required this.changeSeverityCounts,
    required this.recommendationStateCounts,
    required this.roadmapStateCounts,
    required this.releaseTrainReadinessCounts,
    required this.packageStateCounts,
    required this.architectureEntityCount,
    required this.architectureRelationshipCount,
    required this.cycleCount,
    required this.unresolvedDependencyCount,
    required this.sharedDependencyCount,
    required this.orphanCount,
    required this.trustAlertCount,
    required this.provenanceManifestCount,
    required this.staleEvidenceProjects,
  });

  factory GaiaProgrammeSummaryCounts.fromJson(Map<String, dynamic> json) {
    return GaiaProgrammeSummaryCounts(
      projectCount: _intValue(json['project_count']),
      healthStatusCounts: _intMap(json['health_status_counts']),
      changeSeverityCounts: _intMap(json['change_severity_counts']),
      recommendationStateCounts: _intMap(json['recommendation_state_counts']),
      roadmapStateCounts: _intMap(json['roadmap_state_counts']),
      releaseTrainReadinessCounts: _intMap(
        json['release_train_readiness_counts'],
      ),
      packageStateCounts: _intMap(json['package_state_counts']),
      architectureEntityCount: _intValue(json['architecture_entity_count']),
      architectureRelationshipCount: _intValue(
        json['architecture_relationship_count'],
      ),
      cycleCount: _intValue(json['cycle_count']),
      unresolvedDependencyCount: _intValue(json['unresolved_dependency_count']),
      sharedDependencyCount: _intValue(json['shared_dependency_count']),
      orphanCount: _intValue(json['orphan_count']),
      trustAlertCount: _intValue(json['trust_alert_count']),
      provenanceManifestCount: _intValue(json['provenance_manifest_count']),
      staleEvidenceProjects: _stringList(json['stale_evidence_projects']),
    );
  }

  final int projectCount;
  final Map<String, int> healthStatusCounts;
  final Map<String, int> changeSeverityCounts;
  final Map<String, int> recommendationStateCounts;
  final Map<String, int> roadmapStateCounts;
  final Map<String, int> releaseTrainReadinessCounts;
  final Map<String, int> packageStateCounts;
  final int architectureEntityCount;
  final int architectureRelationshipCount;
  final int cycleCount;
  final int unresolvedDependencyCount;
  final int sharedDependencyCount;
  final int orphanCount;
  final int trustAlertCount;
  final int provenanceManifestCount;
  final List<String> staleEvidenceProjects;
}

@immutable
class GaiaProgrammeSummary {
  const GaiaProgrammeSummary({
    required this.generatedAt,
    required this.selectedProjectId,
    required this.selectedProject,
    required this.summary,
    required this.portfolio,
    required this.architectureRegistry,
    required this.dependencyGraph,
    required this.impactAnalysis,
    required this.changeProposals,
    required this.roadmap,
    required this.releaseTrains,
    required this.programmePackages,
    required this.decisions,
    required this.crossProjectEvidence,
  });

  factory GaiaProgrammeSummary.fromJson(Map<String, dynamic> json) {
    return GaiaProgrammeSummary(
      generatedAt: DateTime.parse(
        json['generated_at'] as String? ?? DateTime.now().toIso8601String(),
      ),
      selectedProjectId: json['selected_project_id'] as String?,
      selectedProject: _mapValue(json['selected_project']),
      summary: GaiaProgrammeSummaryCounts.fromJson(_mapValue(json['summary'])),
      portfolio: _mapValue(json['portfolio']),
      architectureRegistry: _mapValue(json['architecture_registry']),
      dependencyGraph: _mapValue(json['dependency_graph']),
      impactAnalysis: _mapValue(json['impact_analysis']),
      changeProposals: _mapValue(json['change_proposals']),
      roadmap: _mapValue(json['roadmap']),
      releaseTrains: _mapValue(json['release_trains']),
      programmePackages: _mapValue(json['programme_packages']),
      decisions: _mapValue(json['decisions']),
      crossProjectEvidence: _mapValue(json['cross_project_evidence']),
    );
  }

  final DateTime generatedAt;
  final String? selectedProjectId;
  final Map<String, dynamic>? selectedProject;
  final GaiaProgrammeSummaryCounts summary;
  final Map<String, dynamic> portfolio;
  final Map<String, dynamic> architectureRegistry;
  final Map<String, dynamic> dependencyGraph;
  final Map<String, dynamic> impactAnalysis;
  final Map<String, dynamic> changeProposals;
  final Map<String, dynamic> roadmap;
  final Map<String, dynamic> releaseTrains;
  final Map<String, dynamic> programmePackages;
  final Map<String, dynamic> decisions;
  final Map<String, dynamic> crossProjectEvidence;
}

Map<String, dynamic> _mapValue(Object? value) {
  return value is Map ? value.cast<String, dynamic>() : <String, dynamic>{};
}

Map<String, int> _intMap(Object? value) {
  if (value is! Map) {
    return <String, int>{};
  }
  final result = <String, int>{};
  for (final entry in value.entries) {
    final key = entry.key.toString();
    final parsed = int.tryParse(entry.value.toString()) ?? 0;
    result[key] = parsed;
  }
  return result;
}

int _intValue(Object? value) {
  if (value is int) {
    return value;
  }
  return int.tryParse(value?.toString() ?? '') ?? 0;
}

List<String> _stringList(Object? value) {
  if (value is! List) {
    return <String>[];
  }
  return value.whereType<String>().toList();
}
