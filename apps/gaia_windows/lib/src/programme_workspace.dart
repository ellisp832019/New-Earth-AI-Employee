import 'dart:async';

import 'package:flutter/material.dart';

import 'controller.dart';
import 'models.dart';
import 'widgets.dart';

class ProgrammeIntelligenceWorkspaceScreen extends StatefulWidget {
  const ProgrammeIntelligenceWorkspaceScreen({
    super.key,
    required this.controller,
    this.initialIndex = 0,
  });

  final GaiaAppController controller;
  final int initialIndex;

  @override
  State<ProgrammeIntelligenceWorkspaceScreen> createState() =>
      _ProgrammeIntelligenceWorkspaceScreenState();
}

class _ProgrammeIntelligenceWorkspaceScreenState
    extends State<ProgrammeIntelligenceWorkspaceScreen> {
  static const _destinations = <_ProgrammeDestination>[
    _ProgrammeDestination(
      'Overview',
      Icons.space_dashboard_outlined,
      Icons.space_dashboard,
    ),
    _ProgrammeDestination(
      'Architecture',
      Icons.account_tree_outlined,
      Icons.account_tree,
    ),
    _ProgrammeDestination(
      'Dependencies',
      Icons.device_hub_outlined,
      Icons.device_hub,
    ),
    _ProgrammeDestination('Impact', Icons.track_changes_outlined, Icons.track_changes),
    _ProgrammeDestination('Change Proposals', Icons.draw_outlined, Icons.draw),
    _ProgrammeDestination('Roadmap', Icons.route_outlined, Icons.route),
    _ProgrammeDestination('Release Trains', Icons.train_outlined, Icons.train),
    _ProgrammeDestination(
      'Programme Packages',
      Icons.inventory_2_outlined,
      Icons.inventory_2,
    ),
    _ProgrammeDestination('Decisions', Icons.rule_outlined, Icons.rule),
    _ProgrammeDestination(
      'Evidence',
      Icons.fact_check_outlined,
      Icons.fact_check,
    ),
  ];

  int selectedIndex = 0;
  String? selectedEntityId;
  String? selectedAnalysisId;
  String? selectedProposalId;
  String? selectedTrainId;
  String? selectedPackageId;
  String? selectedDecisionWorkPackageId;
  String roadmapFilter = 'ALL';

  @override
  void initState() {
    super.initState();
    selectedIndex = widget.initialIndex.clamp(0, _destinations.length - 1);
    unawaited(widget.controller.refreshProgrammeWorkspace());
  }

  @override
  Widget build(BuildContext context) {
    final controller = widget.controller;
    final workspace = controller.programmeWorkspace;
    if (workspace == null) {
      return _buildUnavailable(controller);
    }

    final selectedProjectId = workspace['selected_project_id']?.toString() ??
        controller.selectedProjectId ??
        'unknown';
    final selectedProject =
        workspace['selected_project'] as Map<String, dynamic>? ?? <String, dynamic>{};
    final summary = _map(workspace['summary']);
    final overview = _map(workspace['overview']);
    final architecture = _map(workspace['architecture_registry']);
    final dependencyGraph = _map(workspace['dependency_graph']);
    final impactAnalysis = _map(workspace['impact_analysis']);
    final changeProposals = _map(workspace['change_proposals']);
    final roadmap = _map(workspace['roadmap']);
    final releaseTrains = _map(workspace['release_trains']);
    final packages = _map(workspace['programme_packages']);
    final decisions = _map(workspace['decisions']);
    final evidence = _map(workspace['cross_project_evidence']);

    final entities = _list(architecture['entities']);
    final relationships = _list(architecture['relationships']);
    final analyses = _list(impactAnalysis['analyses']);
    final recommendations = _list(changeProposals['recommendations']);
    final roadmapItems = _list(roadmap['roadmap_items']);
    final trains = _list(releaseTrains['release_trains']);
    final programmePackages = _list(packages['programme_packages']);
    final selectedWorkPackages = _list(decisions['selected_work_packages']);
    final trustAlerts = _list(decisions['trust_alerts']);
    final provenanceManifests = _list(evidence['provenance_manifests']);

    selectedEntityId ??= entities.isEmpty ? null : entities.first['entity_id']?.toString();
    selectedAnalysisId ??= analyses.isEmpty ? null : analyses.first['analysis_id']?.toString();
    selectedProposalId ??= recommendations.isEmpty
        ? null
        : recommendations.first['recommendation_id']?.toString();
    selectedTrainId ??= trains.isEmpty ? null : trains.first['release_train_id']?.toString();
    selectedPackageId ??= programmePackages.isEmpty
        ? null
        : programmePackages.first['programme_package_id']?.toString();
    selectedDecisionWorkPackageId ??= selectedWorkPackages.isEmpty
        ? null
        : selectedWorkPackages.first['work_package_id']?.toString();

    return Column(
      children: [
        MaterialBanner(
          leading: const Icon(Icons.lock_outline),
          content: const Text(
            'Programme Intelligence is read only. Refresh to load canonical backend data, but do not expect any execution or repository mutation here.',
          ),
          actions: [
            TextButton(
              onPressed: controller.busy
                  ? null
                  : () => unawaited(
                      controller.refreshProgrammeWorkspace(
                        projectId: selectedProjectId,
                      ),
                    ),
              child: const Text('Refresh'),
            ),
          ],
        ),
        const Divider(height: 1),
        Expanded(
          child: Row(
            children: [
              NavigationRail(
                selectedIndex: selectedIndex,
                onDestinationSelected: (index) => setState(() => selectedIndex = index),
                labelType: NavigationRailLabelType.all,
                scrollable: true,
                leading: Padding(
                  padding: const EdgeInsets.only(top: 12),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Programme Intelligence',
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                      const SizedBox(height: 4),
                      Text(
                        selectedProject['name']?.toString() ?? selectedProjectId,
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                    ],
                  ),
                ),
                destinations: [
                  for (final destination in _destinations)
                    NavigationRailDestination(
                      icon: Icon(destination.icon),
                      selectedIcon: Icon(destination.activeIcon),
                      label: Text(destination.label),
                    ),
                ],
              ),
              const VerticalDivider(width: 1),
              Expanded(
                child: _ProgrammeScreenScaffold(
                  title: _destinations[selectedIndex].label,
                  subtitle: _subtitle(selectedIndex),
                  child: ListView(
                    children: [
                      _headerChips(
                        context,
                        controller: controller,
                        selectedProjectId: selectedProjectId,
                        summary: summary,
                      ),
                      const SizedBox(height: 16),
                      _buildPage(
                        context,
                        controller,
                        workspace: workspace,
                        summary: summary,
                        overview: overview,
                        architecture: architecture,
                        dependencyGraph: dependencyGraph,
                        impactAnalysis: impactAnalysis,
                        changeProposals: changeProposals,
                        roadmap: roadmap,
                        releaseTrains: releaseTrains,
                        packages: packages,
                        decisions: decisions,
                        evidence: evidence,
                        entities: entities,
                        relationships: relationships,
                        analyses: analyses,
                        recommendations: recommendations,
                        roadmapItems: roadmapItems,
                        trains: trains,
                        programmePackages: programmePackages,
                        selectedWorkPackages: selectedWorkPackages,
                        trustAlerts: trustAlerts,
                        provenanceManifests: provenanceManifests,
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildUnavailable(GaiaAppController controller) {
    return Column(
      children: [
        MaterialBanner(
          leading: const Icon(Icons.lock_outline),
          content: const Text(
            'Programme workspace data is unavailable. Refresh after the backend is ready.',
          ),
          actions: [
            TextButton(
              onPressed: controller.busy
                  ? null
                  : () => unawaited(controller.refreshProgrammeWorkspace()),
              child: const Text('Retry'),
            ),
          ],
        ),
        const Divider(height: 1),
        Expanded(
          child: Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 560),
              child: Card(
                child: Padding(
                  padding: const EdgeInsets.all(24),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Programme workspace unavailable',
                        style: Theme.of(context).textTheme.titleLarge,
                      ),
                      const SizedBox(height: 8),
                      Text(controller.lastError ?? 'No backend response was loaded.'),
                      const SizedBox(height: 16),
                      FilledButton(
                        onPressed: controller.busy
                            ? null
                            : () => unawaited(controller.refreshProgrammeWorkspace()),
                        child: const Text('Retry'),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ),
      ],
    );
  }

  Widget _headerChips(
    BuildContext context, {
    required GaiaAppController controller,
    required String selectedProjectId,
    required Map<String, dynamic> summary,
  }) {
    final healthStates = _map(summary['health_status_counts']);
    final roadmapStates = _map(summary['roadmap_state_counts']);
    final trainStates = _map(summary['release_train_readiness_counts']);
    final packageStates = _map(summary['package_state_counts']);
    return Wrap(
      spacing: 8,
      runSpacing: 8,
      children: [
        StatusChip(
          label: controller.backendStatusLabel,
          color: controller.backendState == BackendConnectionState.connected
              ? Colors.green
              : Colors.orange,
          icon: controller.backendState == BackendConnectionState.connected
              ? Icons.check_circle
              : Icons.cloud_off,
        ),
        StatusChip(
          label: controller.backendCompatibilityLabel,
          color: controller.backendCompatibilityColor,
          icon: Icons.verified_outlined,
        ),
        StatusChip(label: selectedProjectId, color: Colors.teal, icon: Icons.folder),
        StatusChip(
          label: 'Projects ${summary['project_count'] ?? 0}',
          color: Colors.indigo,
          icon: Icons.groups_outlined,
        ),
        StatusChip(
          label: 'Roadmap ${_countStates(roadmapStates)}',
          color: Colors.deepPurple,
          icon: Icons.route_outlined,
        ),
        StatusChip(
          label: 'Trains ${_countStates(trainStates)}',
          color: Colors.cyan,
          icon: Icons.train_outlined,
        ),
        StatusChip(
          label: 'Packages ${_countStates(packageStates)}',
          color: Colors.orange,
          icon: Icons.inventory_2_outlined,
        ),
        StatusChip(
          label: 'Health ${_countStates(healthStates)}',
          color: Colors.green,
          icon: Icons.health_and_safety_outlined,
        ),
      ],
    );
  }

  Widget _buildPage(
    BuildContext context,
    GaiaAppController controller, {
    required Map<String, dynamic> workspace,
    required Map<String, dynamic> summary,
    required Map<String, dynamic> overview,
    required Map<String, dynamic> architecture,
    required Map<String, dynamic> dependencyGraph,
    required Map<String, dynamic> impactAnalysis,
    required Map<String, dynamic> changeProposals,
    required Map<String, dynamic> roadmap,
    required Map<String, dynamic> releaseTrains,
    required Map<String, dynamic> packages,
    required Map<String, dynamic> decisions,
    required Map<String, dynamic> evidence,
    required List<Map<String, dynamic>> entities,
    required List<Map<String, dynamic>> relationships,
    required List<Map<String, dynamic>> analyses,
    required List<Map<String, dynamic>> recommendations,
    required List<Map<String, dynamic>> roadmapItems,
    required List<Map<String, dynamic>> trains,
    required List<Map<String, dynamic>> programmePackages,
    required List<Map<String, dynamic>> selectedWorkPackages,
    required List<Map<String, dynamic>> trustAlerts,
    required List<Map<String, dynamic>> provenanceManifests,
  }) {
    switch (selectedIndex) {
      case 0:
        return _overviewPage(summary, overview);
      case 1:
        return _architecturePage(entities, relationships);
      case 2:
        return _dependenciesPage(dependencyGraph);
      case 3:
        return _impactPage(analyses, impactAnalysis);
      case 4:
        return _proposalsPage(recommendations, changeProposals);
      case 5:
        return _roadmapPage(roadmapItems);
      case 6:
        return _releaseTrainsPage(trains);
      case 7:
        return _packagesPage(programmePackages);
      case 8:
        return _decisionsPage(selectedWorkPackages, trustAlerts, decisions);
      case 9:
        return _evidencePage(evidence, provenanceManifests, workspace);
      default:
        return _overviewPage(summary, overview);
    }
  }

  Widget _overviewPage(
    Map<String, dynamic> summary,
    Map<String, dynamic> overview,
  ) {
    final healthPortfolio = _map(overview['health_portfolio']);
    final changePortfolio = _map(overview['change_portfolio']);
    final recommendationPortfolio = _map(overview['recommendation_portfolio']);
    final roadmapPortfolio = _map(overview['roadmap_portfolio']);
    final releasePortfolio = _map(overview['release_portfolio']);
    final packagePortfolio = _map(overview['package_portfolio']);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _statGrid([
          ('Projects', '${summary['project_count'] ?? 0}', Icons.groups_outlined),
          (
            'Entities',
            '${summary['architecture_entity_count'] ?? 0}',
            Icons.account_tree_outlined,
          ),
          ('Cycles', '${summary['cycle_count'] ?? 0}', Icons.sync_problem_outlined),
          (
            'Unresolved',
            '${summary['unresolved_dependency_count'] ?? 0}',
            Icons.link_off_outlined,
          ),
          ('Alerts', '${summary['trust_alert_count'] ?? 0}', Icons.verified_user_outlined),
          (
            'Packages',
            '${_listCount(packagePortfolio, 'programme_packages')}',
            Icons.inventory_2_outlined,
          ),
        ]),
        const SizedBox(height: 16),
        Wrap(
          spacing: 16,
          runSpacing: 16,
          children: [
            _summaryCard(
              'Health summary',
              Text(_simpleText([
                'Counts: ${_map(healthPortfolio['counts_by_status'])}',
                'Missing snapshots: ${_listCount(healthPortfolio, 'projects_without_snapshots')}',
              ])),
            ),
            _summaryCard(
              'Change summary',
              Text(_simpleText([
                'Counts: ${_map(changePortfolio['counts_by_severity'])}',
                'Projects: ${_listCount(changePortfolio, 'projects')}',
              ])),
            ),
            _summaryCard(
              'Recommendation summary',
              Text(_simpleText([
                'Counts: ${_map(recommendationPortfolio['counts_by_state'])}',
                'Queue: ${_listCount(recommendationPortfolio, 'recommendation_queue')}',
              ])),
            ),
            _summaryCard(
              'Roadmap summary',
              Text(_simpleText([
                'Counts: ${_map(roadmapPortfolio['counts_by_state'])}',
                'Items: ${_listCount(roadmapPortfolio, 'roadmap_items')}',
              ])),
            ),
            _summaryCard(
              'Release trains',
              Text(_simpleText([
                'Counts: ${_map(releasePortfolio['counts_by_readiness'])}',
                'Trains: ${_listCount(releasePortfolio, 'release_trains')}',
              ])),
            ),
          ],
        ),
      ],
    );
  }

  Widget _architecturePage(
    List<Map<String, dynamic>> entities,
    List<Map<String, dynamic>> relationships,
  ) {
    final selectedEntity = entities.firstWhere(
      (entity) => entity['entity_id']?.toString() == selectedEntityId,
      orElse: () => entities.isNotEmpty ? entities.first : <String, dynamic>{},
    );
    selectedEntityId ??= selectedEntity['entity_id']?.toString();
    final selectedRelationships = relationships
        .where(
          (relationship) =>
              relationship['source_entity_id']?.toString() ==
                  selectedEntity['entity_id']?.toString() ||
              relationship['target_entity_id']?.toString() ==
                  selectedEntity['entity_id']?.toString(),
        )
        .toList();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _statGrid([
          ('Entities', '${entities.length}', Icons.account_tree_outlined),
          ('Relationships', '${relationships.length}', Icons.device_hub_outlined),
          (
            'Approved',
            '${entities.where((entity) => entity['status']?.toString() == 'approved').length}',
            Icons.verified_outlined,
          ),
          (
            'Fresh',
            '${entities.where((entity) => entity['freshness_state']?.toString() == 'fresh').length}',
            Icons.fiber_new_outlined,
          ),
        ]),
        const SizedBox(height: 16),
        SectionCard(
          title: 'Architecture Registry',
          subtitle: 'Review current entities and revisions',
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  for (final entity in entities.take(10))
                    ChoiceChip(
                      label: Text(
                        '${entity['name']?.toString() ?? entity['identity_key']?.toString() ?? 'Entity'} | ${entity['kind']?.toString() ?? 'unknown'}',
                      ),
                      selected: entity['entity_id']?.toString() == selectedEntityId,
                      onSelected: (_) => setState(
                        () => selectedEntityId = entity['entity_id']?.toString(),
                      ),
                    ),
                ],
              ),
              const SizedBox(height: 12),
              SizedBox(
                height: 260,
                child: ListView.builder(
                  itemCount: entities.length,
                  itemBuilder: (context, index) {
                    final entity = entities[index];
                    return ListTile(
                      selected: entity['entity_id']?.toString() == selectedEntityId,
                      title: Text(entity['name']?.toString() ?? 'Entity'),
                      subtitle: Text(
                        '${entity['kind']?.toString() ?? 'unknown'} | ${entity['status']?.toString() ?? 'unknown'} | ${entity['freshness_state']?.toString() ?? 'unknown'}',
                      ),
                      trailing: Text(
                        entity['current_revision_number']?.toString() ?? '0',
                      ),
                      onTap: () => setState(
                        () => selectedEntityId = entity['entity_id']?.toString(),
                      ),
                    );
                  },
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 16),
        _detailCard(
          title: 'Entity Detail',
          subtitle:
              selectedEntity['name']?.toString() ?? selectedEntity['entity_id']?.toString() ?? 'Unknown entity',
          child: _keyValueText([
            ('Entity ID', selectedEntity['entity_id']?.toString() ?? 'unknown'),
            ('Identity', selectedEntity['identity_key']?.toString() ?? 'unknown'),
            ('Kind', selectedEntity['kind']?.toString() ?? 'unknown'),
            ('Status', selectedEntity['status']?.toString() ?? 'unknown'),
            ('Freshness', selectedEntity['freshness_state']?.toString() ?? 'unknown'),
            ('Revision', selectedEntity['current_revision_number']?.toString() ?? '0'),
          ]),
        ),
        const SizedBox(height: 12),
        _detailListCard(
          title: 'Relationships',
          subtitle: 'Edges touching the selected entity',
          items: selectedRelationships,
          labelField: 'relationship_type',
          detailField: 'canonical_relationship_reference',
        ),
      ],
    );
  }

  Widget _dependenciesPage(Map<String, dynamic> dependencyGraph) {
    final snapshot = _map(dependencyGraph['snapshot']);
    final cycles = _list(dependencyGraph['cycles']);
    final unresolved = _list(dependencyGraph['unresolved_findings']);
    final projectDependencies = _list(dependencyGraph['project_dependencies']);
    final projectDependents = _list(dependencyGraph['project_dependents']);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _statGrid([
          ('Nodes', '${snapshot['node_count'] ?? 0}', Icons.circle_outlined),
          ('Edges', '${snapshot['edge_count'] ?? 0}', Icons.linear_scale_outlined),
          ('Cycles', '${cycles.length}', Icons.sync_problem_outlined),
          ('Findings', '${unresolved.length}', Icons.warning_amber_outlined),
        ]),
        const SizedBox(height: 16),
        _detailCard(
          title: 'Dependency Graph',
          subtitle: 'Graph fingerprint and project-level dependencies',
          child: _keyValueText([
            ('Graph ID', snapshot['graph_id']?.toString() ?? 'unknown'),
            ('Fingerprint', snapshot['graph_fingerprint']?.toString() ?? 'unknown'),
            ('Freshness', snapshot['freshness_state']?.toString() ?? 'unknown'),
            ('Trust', snapshot['trust_state']?.toString() ?? 'unknown'),
          ]),
        ),
        const SizedBox(height: 12),
        Wrap(
          spacing: 16,
          runSpacing: 16,
          children: [
            _detailListCard(
              title: 'Cycles',
              subtitle: 'Canonical dependency cycles',
              items: cycles,
              labelField: 'cycle_id',
              detailField: 'project_ids',
            ),
            _detailListCard(
              title: 'Unresolved findings',
              subtitle: 'Stale or unresolved dependency issues',
              items: unresolved,
              labelField: 'finding_type',
              detailField: 'summary',
            ),
          ],
        ),
        const SizedBox(height: 12),
        _detailListCard(
          title: 'Selected project dependencies',
          subtitle: 'Project dependency projections from the backend',
          items: projectDependencies,
          labelField: 'target_project_id',
          detailField: 'freshness_state',
        ),
        const SizedBox(height: 12),
        _detailListCard(
          title: 'Selected project dependents',
          subtitle: 'Reverse dependency projections from the backend',
          items: projectDependents,
          labelField: 'source_project_id',
          detailField: 'freshness_state',
        ),
      ],
    );
  }

  Widget _impactPage(
    List<Map<String, dynamic>> analyses,
    Map<String, dynamic> impactAnalysis,
  ) {
    final selected = analyses.firstWhere(
      (analysis) => analysis['analysis_id']?.toString() == selectedAnalysisId,
      orElse: () => analyses.isNotEmpty ? analyses.first : <String, dynamic>{},
    );
    selectedAnalysisId ??= selected['analysis_id']?.toString();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _statGrid([
          ('Analyses', '${analyses.length}', Icons.track_changes_outlined),
          (
            'Findings',
            '${_list(impactAnalysis['selected_change_findings']).length}',
            Icons.warning_amber_outlined,
          ),
          (
            'Risk',
            _map(selected['risk'])['risk_level']?.toString() ??
                selected['risk_level']?.toString() ??
                'unknown',
            Icons.shield_outlined,
          ),
          (
            'Freshness',
            selected['freshness_state']?.toString() ?? 'unknown',
            Icons.fiber_new_outlined,
          ),
        ]),
        const SizedBox(height: 16),
        _detailListCard(
          title: 'Impact analyses',
          subtitle: 'Canonical change-impact results derived from current recommendations',
          items: analyses,
          labelField: 'analysis_id',
          detailField: 'impact_fingerprint',
          onTap: (analysis) =>
              setState(() => selectedAnalysisId = analysis['analysis_id']?.toString()),
          selectedValue: selectedAnalysisId,
        ),
        const SizedBox(height: 12),
        _detailCard(
          title: 'Impact Detail',
          subtitle:
              _map(selected['proposal'])['title']?.toString() ?? 'Selected analysis',
          child: _keyValueText([
            ('Analysis ID', selected['analysis_id']?.toString() ?? 'unknown'),
            (
              'Proposal',
              _map(selected['proposal'])['proposal_id']?.toString() ??
                  selected['proposal_id']?.toString() ??
                  'unknown',
            ),
            (
              'Origin project',
              _map(selected['proposal'])['origin_project']?.toString() ??
                  'unknown',
            ),
            (
              'Impact fingerprint',
              selected['impact_fingerprint']?.toString() ?? 'unknown',
            ),
            ('Trust', selected['trust_state']?.toString() ?? 'unknown'),
          ]),
        ),
      ],
    );
  }

  Widget _proposalsPage(
    List<Map<String, dynamic>> recommendations,
    Map<String, dynamic> changeProposals,
  ) {
    final selected = recommendations.firstWhere(
      (recommendation) =>
          recommendation['recommendation_id']?.toString() == selectedProposalId,
      orElse: () =>
          recommendations.isNotEmpty ? recommendations.first : <String, dynamic>{},
    );
    selectedProposalId ??= selected['recommendation_id']?.toString();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _statGrid([
          ('Proposals', '${recommendations.length}', Icons.draw_outlined),
          (
            'Active',
            '${recommendations.where((item) => item['lifecycle_state']?.toString() == 'active').length}',
            Icons.check_circle_outline,
          ),
          (
            'Blocked',
            '${recommendations.where((item) => item['lifecycle_state']?.toString() == 'blocked').length}',
            Icons.block_outlined,
          ),
          ('Priority', selected['priority_tier']?.toString() ?? 'unknown', Icons.flag_outlined),
        ]),
        const SizedBox(height: 16),
        _detailListCard(
          title: 'Change proposals',
          subtitle: 'Recommendation-backed proposal review',
          items: recommendations,
          labelField: 'title',
          detailField: 'priority_tier',
          selectedValue: selectedProposalId,
          onTap: (proposal) =>
              setState(() => selectedProposalId = proposal['recommendation_id']?.toString()),
        ),
        const SizedBox(height: 12),
        _detailCard(
          title: 'Proposal Detail',
          subtitle: selected['title']?.toString() ?? 'Selected proposal',
          child: _keyValueText([
            ('Recommendation ID', selected['recommendation_id']?.toString() ?? 'unknown'),
            ('Type', selected['recommendation_type']?.toString() ?? 'unknown'),
            ('Lifecycle', selected['lifecycle_state']?.toString() ?? 'unknown'),
            ('Priority', selected['priority_tier']?.toString() ?? 'unknown'),
            ('Summary', selected['concise_summary']?.toString() ?? 'unknown'),
            ('Why', selected['why_it_matters']?.toString() ?? 'unknown'),
          ]),
        ),
      ],
    );
  }

  Widget _roadmapPage(List<Map<String, dynamic>> roadmapItems) {
    final states = <String>{'ALL', ...roadmapItems.map((item) => item['roadmap_state']?.toString() ?? 'unknown')}.toList()
      ..sort();
    final filtered = roadmapFilter == 'ALL'
        ? roadmapItems
        : roadmapItems.where((item) => item['roadmap_state']?.toString() == roadmapFilter).toList();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _statGrid([
          ('Items', '${roadmapItems.length}', Icons.route_outlined),
          ('NOW', '${_countBy(roadmapItems, 'roadmap_state', 'NOW')}', Icons.flash_on_outlined),
          ('BLOCKED', '${_countBy(roadmapItems, 'roadmap_state', 'BLOCKED')}', Icons.block_outlined),
          (
            'RC',
            '${_countBy(roadmapItems, 'roadmap_state', 'RELEASE_CANDIDATE')}',
            Icons.rocket_outlined,
          ),
        ]),
        const SizedBox(height: 16),
        Row(
          children: [
            SizedBox(
              width: 260,
              child: DropdownButtonFormField<String>(
                initialValue: roadmapFilter,
                items: [
                  for (final state in states)
                    DropdownMenuItem(value: state, child: Text(state)),
                ],
                onChanged: (value) =>
                    setState(() => roadmapFilter = value ?? 'ALL'),
                decoration: const InputDecoration(labelText: 'Roadmap state'),
              ),
            ),
          ],
        ),
        const SizedBox(height: 12),
        _detailListCard(
          title: 'Programme roadmap',
          subtitle: 'Canonical roadmap items with reasons and blockers',
          items: filtered,
          labelField: 'title',
          detailField: 'roadmap_state',
        ),
      ],
    );
  }

  Widget _releaseTrainsPage(List<Map<String, dynamic>> trains) {
    final selected = trains.firstWhere(
      (train) => train['release_train_id']?.toString() == selectedTrainId,
      orElse: () => trains.isNotEmpty ? trains.first : <String, dynamic>{},
    );
    selectedTrainId ??= selected['release_train_id']?.toString();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _statGrid([
          ('Trains', '${trains.length}', Icons.train_outlined),
          ('Ready', '${_countBy(trains, 'release_readiness', 'READY')}', Icons.check_circle_outline),
          ('Blocked', '${_countBy(trains, 'release_readiness', 'BLOCKED')}', Icons.block_outlined),
          (
            'Warnings',
            '${_countBy(trains, 'release_readiness', 'PARTIAL')}',
            Icons.warning_amber_outlined,
          ),
        ]),
        const SizedBox(height: 16),
        _detailListCard(
          title: 'Release trains',
          subtitle: 'Dependency order, constraints and readiness',
          items: trains,
          labelField: 'objective',
          detailField: 'release_readiness',
          selectedValue: selectedTrainId,
          onTap: (train) =>
              setState(() => selectedTrainId = train['release_train_id']?.toString()),
        ),
        const SizedBox(height: 12),
        _detailCard(
          title: 'Release Train Detail',
          subtitle: selected['objective']?.toString() ?? 'Selected train',
          child: _keyValueText([
            ('Train ID', selected['release_train_id']?.toString() ?? 'unknown'),
            ('Fingerprint', selected['train_fingerprint']?.toString() ?? 'unknown'),
            ('Readiness', selected['release_readiness']?.toString() ?? 'unknown'),
            ('Human approval', selected['human_approval_state']?.toString() ?? 'unknown'),
            ('Trust', selected['trust']?.toString() ?? 'unknown'),
          ]),
        ),
      ],
    );
  }

  Widget _packagesPage(List<Map<String, dynamic>> programmePackages) {
    final selected = programmePackages.firstWhere(
      (package) => package['programme_package_id']?.toString() == selectedPackageId,
      orElse: () =>
          programmePackages.isNotEmpty ? programmePackages.first : <String, dynamic>{},
    );
    selectedPackageId ??= selected['programme_package_id']?.toString();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _statGrid([
          ('Packages', '${programmePackages.length}', Icons.inventory_2_outlined),
          (
            'Approved',
            '${_countBy(programmePackages, 'package_state', 'approved')}',
            Icons.verified_outlined,
          ),
          (
            'Proposed',
            '${_countBy(programmePackages, 'package_state', 'proposed')}',
            Icons.pending_outlined,
          ),
          (
            'Handed off',
            '${_countBy(programmePackages, 'package_state', 'handed_off')}',
            Icons.forward_outlined,
          ),
        ]),
        const SizedBox(height: 16),
        _detailListCard(
          title: 'Programme packages',
          subtitle: 'Exact package identity, revisions and fingerprints',
          items: programmePackages,
          labelField: 'objective',
          detailField: 'package_state',
          selectedValue: selectedPackageId,
          onTap: (package) =>
              setState(() => selectedPackageId = package['programme_package_id']?.toString()),
        ),
        const SizedBox(height: 12),
        _detailCard(
          title: 'Programme Package Detail',
          subtitle: selected['objective']?.toString() ?? 'Selected package',
          child: _keyValueText([
            ('Package ID', selected['programme_package_id']?.toString() ?? 'unknown'),
            ('Revision', selected['current_revision_number']?.toString() ?? '1'),
            ('Fingerprint', selected['package_fingerprint']?.toString() ?? 'unknown'),
            ('State', selected['package_state']?.toString() ?? 'unknown'),
            (
              'Approval',
              _map(selected['human_approval'])['approval_state']?.toString() ??
                  'unknown',
            ),
          ]),
        ),
        const SizedBox(height: 12),
        _detailListCard(
          title: 'Revision history',
          subtitle: 'Human reviewers must not assume approval carries forward',
          items: _list(selected['revision_history']),
          labelField: 'revision_number',
          detailField: 'change_reason',
        ),
      ],
    );
  }

  Widget _decisionsPage(
    List<Map<String, dynamic>> selectedWorkPackages,
    List<Map<String, dynamic>> trustAlerts,
    Map<String, dynamic> decisions,
  ) {
    final selected = selectedWorkPackages.firstWhere(
      (item) => item['work_package_id']?.toString() == selectedDecisionWorkPackageId,
      orElse: () => selectedWorkPackages.isNotEmpty
          ? selectedWorkPackages.first
          : <String, dynamic>{},
    );
    selectedDecisionWorkPackageId ??= selected['work_package_id']?.toString();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _statGrid([
          ('Work packages', '${selectedWorkPackages.length}', Icons.view_list_outlined),
          ('Alerts', '${trustAlerts.length}', Icons.verified_user_outlined),
          ('Handoffs', '${_listCount(decisions, 'selected_work_packages')}', Icons.forward_outlined),
          (
            'Snapshots',
            '${_listCount(decisions, 'selected_health_snapshots')}',
            Icons.camera_alt_outlined,
          ),
        ]),
        const SizedBox(height: 16),
        _detailListCard(
          title: 'Human decisions',
          subtitle: 'Approval, handoff and outcome evidence',
          items: selectedWorkPackages,
          labelField: 'title',
          detailField: 'approval_state',
          selectedValue: selectedDecisionWorkPackageId,
          onTap: (workPackage) => setState(
            () => selectedDecisionWorkPackageId = workPackage['work_package_id']?.toString(),
          ),
        ),
        const SizedBox(height: 12),
        _detailCard(
          title: 'Decision Detail',
          subtitle: selected['title']?.toString() ?? 'Selected work package',
          child: _keyValueText([
            ('Work package ID', selected['work_package_id']?.toString() ?? 'unknown'),
            ('Revision', selected['current_revision_number']?.toString() ?? '1'),
            ('Approval', selected['approval_state']?.toString() ?? 'unknown'),
            ('Gate', selected['gate_state']?.toString() ?? 'unknown'),
            ('Staleness', selected['staleness_state']?.toString() ?? 'unknown'),
          ]),
        ),
        const SizedBox(height: 12),
        _detailListCard(
          title: 'Trust alerts',
          subtitle: 'Cross-project trust and provenance warnings',
          items: trustAlerts,
          labelField: 'title',
          detailField: 'severity',
        ),
      ],
    );
  }

  Widget _evidencePage(
    Map<String, dynamic> evidence,
    List<Map<String, dynamic>> provenanceManifests,
    Map<String, dynamic> workspace,
  ) {
    final selectedProjectEvidence = _map(evidence['selected_project_health']);
    final selectedProjectDependencies = _list(evidence['selected_project_dependencies']);
    final selectedProjectRecommendations =
        _list(evidence['selected_project_recommendations']);
    final selectedProjectWorkPackages =
        _list(evidence['selected_project_work_packages']);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _statGrid([
          (
            'Provenance',
            '${provenanceManifests.length}',
            Icons.note_outlined,
          ),
          ('Capabilities', '${_listCount(evidence, 'capabilities')}', Icons.shield_outlined),
          (
            'Recommendations',
            '${selectedProjectRecommendations.length}',
            Icons.draw_outlined,
          ),
          (
            'Dependencies',
            '${selectedProjectDependencies.length}',
            Icons.device_hub_outlined,
          ),
        ]),
        const SizedBox(height: 16),
        Wrap(
          spacing: 16,
          runSpacing: 16,
          children: [
            _summaryCard(
              'Selected project evidence',
              _keyValueText([
                (
                  'Status',
                  selectedProjectEvidence['normalized_status']?.toString() ??
                      'unknown',
                ),
                (
                  'Snapshot',
                  selectedProjectEvidence['snapshot_id']?.toString() ??
                      selectedProjectEvidence['latest_snapshot_id']?.toString() ??
                      'unknown',
                ),
                (
                  'Freshness',
                  selectedProjectEvidence['evidence_freshness']?.toString() ??
                      'unknown',
                ),
              ]),
            ),
            _detailListCard(
              title: 'Provenance manifests',
              subtitle: 'Cross-project evidence records',
              items: provenanceManifests,
              labelField: 'manifest_id',
              detailField: 'name',
            ),
            _detailListCard(
              title: 'Selected project recommendations',
              subtitle: 'Recommendation provenance stays visible',
              items: selectedProjectRecommendations,
              labelField: 'recommendation_id',
              detailField: 'title',
            ),
            _detailListCard(
              title: 'Selected project work packages',
              subtitle: 'Child work package revisions remain exact',
              items: selectedProjectWorkPackages,
              labelField: 'work_package_id',
              detailField: 'title',
            ),
          ],
        ),
        const SizedBox(height: 12),
        _detailCard(
          title: 'Workspace metadata',
          subtitle: 'Backend-generated and read only',
          child: _keyValueText([
            ('Generated at', workspace['generated_at']?.toString() ?? 'unknown'),
            (
              'Selected project id',
              workspace['selected_project_id']?.toString() ?? 'unknown',
            ),
          ]),
        ),
      ],
    );
  }

  Widget _detailCard({
    required String title,
    required String subtitle,
    required Widget child,
  }) {
    return SectionCard(
      title: title,
      subtitle: subtitle,
      child: child,
    );
  }

  Widget _summaryCard(String title, Widget child) {
    return SizedBox(
      width: 320,
      child: SectionCard(title: title, child: child),
    );
  }

  Widget _detailListCard({
    required String title,
    required String subtitle,
    required List<Map<String, dynamic>> items,
    required String labelField,
    required String detailField,
    String? selectedValue,
    void Function(Map<String, dynamic>)? onTap,
  }) {
    return SizedBox(
      width: 360,
      child: SectionCard(
        title: title,
        subtitle: subtitle,
        child: SizedBox(
          height: 280,
          child: ListView.builder(
            itemCount: items.length,
            itemBuilder: (context, index) {
              final item = items[index];
              final value = item[labelField]?.toString() ?? 'unknown';
              final detail = item[detailField];
              final selected = selectedValue != null &&
                  (item.values.any((entry) => entry?.toString() == selectedValue));
              return ListTile(
                selected: selected,
                dense: true,
                title: Text(value),
                subtitle: Text(_display(detail)),
                onTap: onTap == null ? null : () => onTap(item),
              );
            },
          ),
        ),
      ),
    );
  }

  Widget _statGrid(List<(String, String, IconData)> values) {
    return Wrap(
      spacing: 16,
      runSpacing: 16,
      children: [
        for (final entry in values)
          SizedBox(
            width: 230,
            child: Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Icon(entry.$3, size: 18),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Text(
                            entry.$1,
                            style: Theme.of(context).textTheme.titleSmall,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Text(entry.$2, style: Theme.of(context).textTheme.headlineSmall),
                  ],
                ),
              ),
            ),
          ),
      ],
    );
  }

  String _subtitle(int index) {
    return switch (index) {
      0 => 'Programme-level overview and counts',
      1 => 'Architecture entities, relationships and revisions',
      2 => 'Dependency graph, cycles and unresolved findings',
      3 => 'Canonical change-impact analyses',
      4 => 'Recommendation-backed change proposals',
      5 => 'Roadmap states and reasons',
      6 => 'Release train readiness and constraints',
      7 => 'Programme package revision history',
      8 => 'Human decisions, handoffs and outcomes',
      9 => 'Cross-project provenance and trust evidence',
      _ => 'Programme intelligence',
    };
  }
}

class _ProgrammeDestination {
  const _ProgrammeDestination(this.label, this.icon, this.activeIcon);

  final String label;
  final IconData icon;
  final IconData activeIcon;
}

class _ProgrammeScreenScaffold extends StatelessWidget {
  const _ProgrammeScreenScaffold({
    required this.title,
    required this.subtitle,
    required this.child,
  });

  final String title;
  final String subtitle;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title, style: Theme.of(context).textTheme.headlineMedium),
          const SizedBox(height: 6),
          Text(subtitle, style: Theme.of(context).textTheme.bodyMedium),
          const SizedBox(height: 18),
          Expanded(child: child),
        ],
      ),
    );
  }
}

Map<String, dynamic> _map(dynamic value) {
  if (value is Map) {
    return value.cast<String, dynamic>();
  }
  return <String, dynamic>{};
}

List<Map<String, dynamic>> _list(dynamic value) {
  if (value is List) {
    return value
        .whereType<Map>()
        .map((item) => item.cast<String, dynamic>())
        .toList();
  }
  return <Map<String, dynamic>>[];
}

int _listCount(Map<String, dynamic> map, String key) {
  return _list(map[key]).length;
}

int _countBy(List<Map<String, dynamic>> items, String field, String expected) {
  return items.where((item) => item[field]?.toString() == expected).length;
}

int _countStates(Map<String, dynamic> map) {
  return map.values.where((value) => value is int && value > 0).length;
}

String _display(dynamic value) {
  if (value == null) {
    return 'unknown';
  }
  if (value is List) {
    return value.map(_display).join(', ');
  }
  if (value is Map) {
    return value.entries
        .map((entry) => '${entry.key}: ${_display(entry.value)}')
        .join(', ');
  }
  return value.toString();
}

String _simpleText(List<String> lines) {
  return lines.join('\n');
}

Widget _keyValueText(List<(String, String)> values) {
  return Wrap(
    spacing: 16,
    runSpacing: 16,
    children: [
      for (final entry in values)
        SizedBox(
          width: 300,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                entry.$1,
                style: const TextStyle(fontWeight: FontWeight.w700),
              ),
              const SizedBox(height: 4),
              SelectableText(entry.$2),
            ],
          ),
        ),
    ],
  );
}
