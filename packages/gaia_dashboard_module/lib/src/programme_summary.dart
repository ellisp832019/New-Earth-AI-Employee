import 'package:flutter/material.dart';

import 'controller.dart';
import 'widgets.dart';

class GaiaProgrammeSummaryView extends StatelessWidget {
  const GaiaProgrammeSummaryView({super.key, required this.controller});

  final GaiaDashboardController controller;

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: controller,
      builder: (context, _) {
        final summary = controller.programmeSummary;
        return ListView(
          padding: const EdgeInsets.all(24),
          children: [
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                GaiaStatusPill(
                  label: controller.programmeSummaryState.name.replaceAll(
                    '_',
                    ' ',
                  ),
                  color: _programmeColor(controller.programmeSummaryState),
                  icon: Icons.timeline,
                ),
                if (controller.programmeSummaryStale)
                  const GaiaStatusPill(
                    label: 'Stale',
                    color: Colors.orange,
                    icon: Icons.history,
                  ),
                GaiaStatusPill(
                  label: controller.lastProgrammeSummaryRefreshAt == null
                      ? 'Never refreshed'
                      : 'Refreshed ${_format(controller.lastProgrammeSummaryRefreshAt!)}',
                  color: Colors.teal,
                  icon: Icons.schedule,
                ),
                if (summary != null)
                  GaiaStatusPill(
                    label: summary.selectedProjectId == null
                        ? 'All projects'
                        : 'Selected ${summary.selectedProjectId}',
                    color: Colors.blue,
                    icon: Icons.account_tree_outlined,
                  ),
              ],
            ),
            const SizedBox(height: 16),
            GaiaSectionCard(
              title: 'Programme summary',
              subtitle:
                  controller.programmeSummaryError ??
                  'Read-only backend summary for the GAIA programme surfaces.',
              child: summary == null
                  ? Text(
                      controller.programmeSummaryError ??
                          'No programme summary is available yet.',
                    )
                  : GaiaKeyValueGrid(
                      rows: [
                        ('Projects', summary.summary.projectCount.toString()),
                        (
                          'Architecture entities',
                          summary.summary.architectureEntityCount.toString(),
                        ),
                        (
                          'Architecture relationships',
                          summary.summary.architectureRelationshipCount
                              .toString(),
                        ),
                        ('Cycles', summary.summary.cycleCount.toString()),
                        (
                          'Unresolved deps',
                          summary.summary.unresolvedDependencyCount.toString(),
                        ),
                        (
                          'Shared deps',
                          summary.summary.sharedDependencyCount.toString(),
                        ),
                        ('Orphans', summary.summary.orphanCount.toString()),
                        (
                          'Trust alerts',
                          summary.summary.trustAlertCount.toString(),
                        ),
                        (
                          'Provenance manifests',
                          summary.summary.provenanceManifestCount.toString(),
                        ),
                        (
                          'Stale evidence',
                          summary.summary.staleEvidenceProjects.isEmpty
                              ? 'None'
                              : summary.summary.staleEvidenceProjects.join(
                                  ', ',
                                ),
                        ),
                      ],
                    ),
            ),
            if (summary != null) ...[
              const SizedBox(height: 16),
              GaiaSectionCard(
                title: 'Portfolio health',
                subtitle: 'Project health, change, and recommendation counts',
                child: GaiaKeyValueGrid(
                  rows: [
                    (
                      'Health states',
                      _summaryCountsText(
                        _mapValue(
                          summary.portfolio['health_portfolio'],
                        )['counts_by_status'],
                      ),
                    ),
                    (
                      'Change severities',
                      _summaryCountsText(
                        _mapValue(
                          summary.portfolio['change_portfolio'],
                        )['counts_by_severity'],
                      ),
                    ),
                    (
                      'Recommendation states',
                      _summaryCountsText(
                        _mapValue(
                          summary.portfolio['recommendation_portfolio'],
                        )['counts_by_state'],
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 16),
              GaiaSectionCard(
                title: 'Architecture and dependencies',
                subtitle:
                    'Registry, graph, cycles, shared dependencies, and orphans',
                child: GaiaKeyValueGrid(
                  rows: [
                    (
                      'Entities',
                      _mapList(
                        summary.architectureRegistry['entities'],
                      ).length.toString(),
                    ),
                    (
                      'Relationships',
                      _mapList(
                        summary.architectureRegistry['relationships'],
                      ).length.toString(),
                    ),
                    (
                      'Graph nodes',
                      _intValue(
                        _mapValue(
                          summary.dependencyGraph['snapshot'],
                        )['node_count'],
                      ).toString(),
                    ),
                    (
                      'Graph edges',
                      _intValue(
                        _mapValue(
                          summary.dependencyGraph['snapshot'],
                        )['edge_count'],
                      ).toString(),
                    ),
                    (
                      'Cycles',
                      _mapList(
                        summary.dependencyGraph['cycles'],
                      ).length.toString(),
                    ),
                    (
                      'Shared deps',
                      _mapList(
                        summary.dependencyGraph['shared_dependencies'],
                      ).length.toString(),
                    ),
                    (
                      'Orphans',
                      _mapList(
                        summary.dependencyGraph['orphans'],
                      ).length.toString(),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 16),
              GaiaSectionCard(
                title: 'Change impact',
                subtitle: 'Analyses, recommendations, and change findings',
                child: Column(
                  children: [
                    for (final analysis in _mapList(
                      summary.impactAnalysis['analyses'],
                    ).take(5))
                      ListTile(
                        leading: const Icon(Icons.insights, color: Colors.blue),
                        title: Text(
                          _stringValue(
                            analysis,
                            'analysis_id',
                            fallback: 'analysis',
                          ),
                        ),
                        subtitle: Text(
                          [
                            _stringValue(
                              _mapValue(analysis['risk']),
                              'risk_level',
                              fallback: 'unknown',
                            ),
                            _stringValue(
                              _mapValue(analysis['proposal']),
                              'title',
                              fallback: 'Untitled proposal',
                            ),
                            'Freshness: ${_stringValue(analysis, 'freshness_state', fallback: 'unknown')}',
                          ].join(' | '),
                        ),
                      ),
                  ],
                ),
              ),
              const SizedBox(height: 16),
              GaiaSectionCard(
                title: 'Roadmap',
                subtitle: 'Deterministic programme sequencing',
                child: Column(
                  children: [
                    for (final item in _mapList(
                      summary.roadmap['roadmap_items'],
                    ).take(5))
                      ListTile(
                        leading: const Icon(Icons.route, color: Colors.teal),
                        title: Text(
                          _stringValue(item, 'title', fallback: 'Roadmap item'),
                        ),
                        subtitle: Text(
                          [
                            _stringValue(
                              item,
                              'project_id',
                              fallback: 'unknown',
                            ),
                            _stringValue(
                              item,
                              'roadmap_state',
                              fallback: 'unknown',
                            ),
                            'Freshness: ${_stringValue(item, 'freshness', fallback: 'unknown')}',
                          ].join(' | '),
                        ),
                      ),
                  ],
                ),
              ),
              const SizedBox(height: 16),
              GaiaSectionCard(
                title: 'Release trains',
                subtitle: 'Read-only release coordination summary',
                child: Column(
                  children: [
                    for (final train in _mapList(
                      summary.releaseTrains['release_trains'],
                    ).take(5))
                      ListTile(
                        leading: const Icon(
                          Icons.alt_route,
                          color: Colors.indigo,
                        ),
                        title: Text(
                          _stringValue(
                            train,
                            'objective',
                            fallback: 'Release train',
                          ),
                        ),
                        subtitle: Text(
                          [
                            _stringValue(
                              train,
                              'release_train_id',
                              fallback: 'unknown',
                            ),
                            _stringValue(
                              train,
                              'release_readiness',
                              fallback: 'unknown',
                            ),
                            'Approval: ${_stringValue(train, 'human_approval_state', fallback: 'unknown')}',
                          ].join(' | '),
                        ),
                      ),
                  ],
                ),
              ),
              const SizedBox(height: 16),
              GaiaSectionCard(
                title: 'Programme packages',
                subtitle: 'Human-reviewable package bundles',
                child: Column(
                  children: [
                    for (final package in _mapList(
                      summary.programmePackages['programme_packages'],
                    ).take(5))
                      ListTile(
                        leading: const Icon(
                          Icons.inventory_2_outlined,
                          color: Colors.orange,
                        ),
                        title: Text(
                          _stringValue(
                            package,
                            'objective',
                            fallback: 'Programme package',
                          ),
                        ),
                        subtitle: Text(
                          [
                            _stringValue(
                              package,
                              'programme_package_id',
                              fallback: 'unknown',
                            ),
                            _stringValue(
                              package,
                              'package_state',
                              fallback: 'unknown',
                            ),
                            'Approval: ${_stringValue(_mapValue(package['human_approval']), 'approval_state', fallback: 'unknown')}',
                          ].join(' | '),
                        ),
                      ),
                  ],
                ),
              ),
              const SizedBox(height: 16),
              GaiaSectionCard(
                title: 'Decisions and evidence',
                subtitle:
                    'Human-review state, selected contract, and provenance',
                child: GaiaKeyValueGrid(
                  rows: [
                    (
                      'Pending reviews',
                      _mapList(
                        summary.decisions['selected_work_packages'],
                      ).length.toString(),
                    ),
                    (
                      'Selected contract',
                      _stringValue(
                        _mapValue(summary.decisions['selected_contract']),
                        'contract_id',
                        fallback: 'none',
                      ),
                    ),
                    (
                      'Provenance manifests',
                      _mapList(
                        summary.crossProjectEvidence['provenance_manifests'],
                      ).length.toString(),
                    ),
                    (
                      'Selected project deps',
                      _mapList(
                        summary
                            .crossProjectEvidence['selected_project_dependencies'],
                      ).length.toString(),
                    ),
                    (
                      'Selected project dependents',
                      _mapList(
                        summary
                            .crossProjectEvidence['selected_project_dependents'],
                      ).length.toString(),
                    ),
                  ],
                ),
              ),
            ],
          ],
        );
      },
    );
  }
}

Color _programmeColor(GaiaProgrammeSummaryState state) {
  return switch (state) {
    GaiaProgrammeSummaryState.ready => Colors.green,
    GaiaProgrammeSummaryState.empty => Colors.teal,
    GaiaProgrammeSummaryState.stale => Colors.orange,
    GaiaProgrammeSummaryState.partial => Colors.amber,
    GaiaProgrammeSummaryState.unavailable => Colors.blueGrey,
    GaiaProgrammeSummaryState.incompatible => Colors.red,
    GaiaProgrammeSummaryState.loading => Colors.blue,
    GaiaProgrammeSummaryState.error => Colors.red,
  };
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

String _stringValue(
  Map<String, dynamic> map,
  String key, {
  String fallback = '',
}) {
  final value = map[key];
  return value == null ? fallback : value.toString();
}

int _intValue(Object? value) {
  if (value is int) {
    return value;
  }
  return int.tryParse(value?.toString() ?? '') ?? 0;
}

String _format(DateTime value) {
  return value.toIso8601String().replaceFirst('T', ' ').split('.').first;
}

String _summaryCountsText(Object? value) {
  if (value is Map) {
    if (value.isEmpty) {
      return 'none';
    }
    return value
        .cast<Object?, Object?>()
        .entries
        .map((entry) => '${entry.key}: ${entry.value}')
        .join(', ');
  }
  if (value == null) {
    return 'none';
  }
  return value.toString();
}
