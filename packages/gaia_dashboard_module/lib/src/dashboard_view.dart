import 'package:flutter/material.dart';
import 'package:gaia_integration_client/gaia_integration_client.dart';

import 'controller.dart';
import 'widgets.dart';

class GaiaDashboardView extends StatelessWidget {
  const GaiaDashboardView({super.key, required this.controller});

  final GaiaDashboardController controller;

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: controller,
      builder: (context, _) {
        final compatibility = controller.compatibility;
        final connectionColor = switch (controller.connectionState) {
          GaiaDashboardConnectionState.connected => Colors.green,
          GaiaDashboardConnectionState.degraded => Colors.orange,
          GaiaDashboardConnectionState.incompatible => Colors.red,
          GaiaDashboardConnectionState.unavailable => Colors.blueGrey,
          GaiaDashboardConnectionState.connecting => Colors.blue,
          GaiaDashboardConnectionState.disconnected => Colors.blueGrey,
        };
        final projectOfficerColor = _projectOfficerColor(
          controller.projectOfficerState,
        );
        final freshness = controller.dataStale
            ? 'Stale data'
            : controller.lastSuccessfulRefreshAt == null
            ? 'No successful refresh yet'
            : 'Fresh as of ${_format(controller.lastSuccessfulRefreshAt!)}';
        return DefaultTabController(
          length: 6,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(24, 24, 24, 12),
                child: Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  crossAxisAlignment: WrapCrossAlignment.center,
                  children: [
                    GaiaStatusPill(
                      label: controller.connectionState.name,
                      color: connectionColor,
                      icon: Icons.link,
                    ),
                    if (compatibility != null)
                      GaiaStatusPill(
                        label: compatibility.status,
                        color: connectionColor,
                        icon: Icons.verified_outlined,
                      ),
                    if (controller.projectOfficerCapabilitiesPayload != null ||
                        controller.projectOfficerError != null)
                      GaiaStatusPill(
                        label:
                            'Project Officer ${controller.projectOfficerStateLabel}',
                        color: projectOfficerColor,
                        icon: Icons.dashboard_outlined,
                      ),
                    if (controller.projectOfficerStale)
                      const GaiaStatusPill(
                        label: 'Project Officer stale',
                        color: Colors.orange,
                        icon: Icons.history,
                      ),
                    if (controller.dataStale)
                      const GaiaStatusPill(
                        label: 'Stale cache',
                        color: Colors.orange,
                        icon: Icons.history,
                      ),
                    GaiaStatusPill(
                      label: freshness,
                      color: Colors.teal,
                      icon: Icons.schedule,
                    ),
                    if ((compatibility?.degradedFeatures.isNotEmpty ?? false))
                      const GaiaStatusPill(
                        label: 'Degraded features',
                        color: Colors.orange,
                        icon: Icons.warning_amber,
                      ),
                  ],
                ),
              ),
              if (controller.errorMessage != null)
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 24),
                  child: GaiaSectionCard(
                    title: 'Connection issue',
                    subtitle:
                        'The module preserved stale data and failed closed.',
                    child: Text(controller.errorMessage!),
                  ),
                ),
              const SizedBox(height: 8),
              const TabBar(
                isScrollable: true,
                tabs: [
                  Tab(text: 'Overview'),
                  Tab(text: 'Capabilities'),
                  Tab(text: 'Project Officer'),
                  Tab(text: 'Provenance'),
                  Tab(text: 'Trust'),
                  Tab(text: 'Retention'),
                ],
              ),
              Expanded(
                child: TabBarView(
                  children: [
                    _OverviewTab(controller: controller),
                    _CapabilitiesTab(controller: controller),
                    _ProjectOfficerTab(controller: controller),
                    _ProvenanceTab(controller: controller),
                    _TrustTab(controller: controller),
                    _RetentionTab(controller: controller),
                  ],
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}

class _OverviewTab extends StatelessWidget {
  const _OverviewTab({required this.controller});

  final GaiaDashboardController controller;

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(24),
      children: [
        Wrap(
          spacing: 16,
          runSpacing: 16,
          children: [
            _SummaryCard(
              title: 'Projects',
              value: '${controller.projects.length}',
              icon: Icons.folder,
            ),
            _SummaryCard(
              title: 'Tasks',
              value: '${controller.taskSummary?.total ?? 0}',
              icon: Icons.task_alt,
            ),
            _SummaryCard(
              title: 'Approvals',
              value: '${controller.approvalSummary?.total ?? 0}',
              icon: Icons.verified,
            ),
            _SummaryCard(
              title: 'Actions',
              value: '${controller.actionSummary?.total ?? 0}',
              icon: Icons.play_circle,
            ),
          ],
        ),
        const SizedBox(height: 16),
        GaiaSectionCard(
          title: 'Workspace status',
          subtitle: 'Read-only embedded operations workspace',
          child: GaiaKeyValueGrid(
            rows: [
              (
                'Backend',
                controller.compatibility?.backendVersion ?? 'unknown',
              ),
              (
                'Contract',
                controller.compatibility?.integrationContractVersion ??
                    'unknown',
              ),
              (
                'Client',
                controller.compatibility?.clientPackageVersion ?? 'unknown',
              ),
              (
                'Capabilities',
                controller.capabilityPayload?['capability_version']
                        ?.toString() ??
                    'unknown',
              ),
              (
                'Last refresh',
                controller.lastSuccessfulRefreshAt == null
                    ? 'Never'
                    : _format(controller.lastSuccessfulRefreshAt!),
              ),
              ('Data stale', controller.dataStale ? 'Yes' : 'No'),
            ],
          ),
        ),
        const SizedBox(height: 16),
        GaiaSectionCard(
          title: 'Latest summary',
          subtitle: controller.latestBrief?.title ?? 'No daily brief',
          child: GaiaKeyValueGrid(
            rows: [
              ('Latest receipt', controller.latestReceipt?.receiptId ?? 'None'),
              ('Receipt chain', controller.latestReceipt?.chainId ?? 'None'),
              (
                'Receipt verification',
                controller.latestReceipt?.verificationStatus ?? 'unknown',
              ),
              ('Trust alerts', controller.trustAlerts.length.toString()),
            ],
          ),
        ),
      ],
    );
  }
}

class _CapabilitiesTab extends StatelessWidget {
  const _CapabilitiesTab({required this.controller});

  final GaiaDashboardController controller;

  @override
  Widget build(BuildContext context) {
    final capabilities =
        controller.compatibility?.capabilityCatalog ??
        const <GaiaCapabilityDescriptor>[];
    return ListView(
      padding: const EdgeInsets.all(24),
      children: [
        GaiaSectionCard(
          title: 'Capability discovery',
          subtitle:
              controller.compatibility?.capabilityVersion ?? 'Unavailable',
          child: Column(
            children: [
              for (final capability in capabilities)
                ListTile(
                  leading: Icon(
                    capability.enabled
                        ? Icons.check_circle
                        : Icons.info_outline,
                    color: capability.enabled ? Colors.green : Colors.orange,
                  ),
                  title: Text(capability.capabilityId),
                  subtitle: Text(capability.summary),
                  trailing: Text('${capability.version} | ${capability.state}'),
                ),
            ],
          ),
        ),
      ],
    );
  }
}

class _ProjectOfficerTab extends StatelessWidget {
  const _ProjectOfficerTab({required this.controller});

  final GaiaDashboardController controller;

  @override
  Widget build(BuildContext context) {
    final portfolioProjects = controller.projectOfficerPortfolioProjects;
    final countsByStatus = controller.projectOfficerPortfolioCountsByStatus;
    final latestPortfolioTimestamp = _mapDateTime(
      controller.projectOfficerPortfolioPayload,
      'generated_at',
    );
    final recommendations = controller.projectOfficerTopRecommendations;
    final blockedProjects = controller.projectOfficerBlockedProjects;
    final staleEvidenceItems = controller.projectOfficerStaleEvidenceItems;
    final pendingApprovals = controller.projectOfficerPendingApprovalPackages;
    final recentCompletedWork = controller.projectOfficerRecentCompletedWork;
    final trustAlerts = controller.projectOfficerTrustAlerts;

    return ListView(
      padding: const EdgeInsets.all(24),
      children: [
        GaiaSectionCard(
          title: 'Project Officer summary',
          subtitle:
              controller.projectOfficerError ??
              (controller.projectOfficerState ==
                      GaiaProjectOfficerSummaryState.unavailable
                  ? 'Project Officer summaries unavailable on this GAIA backend.'
                  : controller.projectOfficerStateLabel),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  GaiaStatusPill(
                    label: controller.projectOfficerStateLabel,
                    color: _projectOfficerColor(controller.projectOfficerState),
                    icon: Icons.dashboard_outlined,
                  ),
                  if (controller.projectOfficerStale)
                    const GaiaStatusPill(
                      label: 'Stale',
                      color: Colors.orange,
                      icon: Icons.history,
                    ),
                  GaiaStatusPill(
                    label: controller.lastProjectOfficerRefreshAt == null
                        ? 'Never refreshed'
                        : 'Refreshed ${_format(controller.lastProjectOfficerRefreshAt!)}',
                    color: Colors.teal,
                    icon: Icons.schedule,
                  ),
                  GaiaStatusPill(
                    label: controller.projectOfficerSupported
                        ? 'Capability available'
                        : 'Capability unavailable',
                    color: controller.projectOfficerSupported
                        ? Colors.green
                        : Colors.orange,
                    icon: Icons.verified_outlined,
                  ),
                ],
              ),
              if (controller.projectOfficerState ==
                      GaiaProjectOfficerSummaryState.unavailable ||
                  controller.projectOfficerState ==
                      GaiaProjectOfficerSummaryState.incompatible ||
                  controller.projectOfficerState ==
                      GaiaProjectOfficerSummaryState.error ||
                  controller.projectOfficerState ==
                      GaiaProjectOfficerSummaryState.partial)
                Padding(
                  padding: const EdgeInsets.only(top: 12),
                  child: Text(
                    controller.projectOfficerError ??
                        'Project Officer summaries are not fully available. The dashboard is preserving read-only state.',
                  ),
                ),
            ],
          ),
        ),
        const SizedBox(height: 16),
        Wrap(
          spacing: 16,
          runSpacing: 16,
          children: [
            _SummaryCard(
              title: 'Enabled',
              value:
                  _statusCount(countsByStatus, 'healthy') +
                  _statusCount(countsByStatus, 'attention') +
                  _statusCount(countsByStatus, 'blocked') +
                  _statusCount(countsByStatus, 'unknown'),
              icon: Icons.folder_copy,
            ),
            _SummaryCard(
              title: 'Healthy',
              value: _statusCount(countsByStatus, 'healthy'),
              icon: Icons.verified,
            ),
            _SummaryCard(
              title: 'Attention',
              value: _statusCount(countsByStatus, 'attention'),
              icon: Icons.warning_amber,
            ),
            _SummaryCard(
              title: 'Blocked',
              value: _statusCount(countsByStatus, 'blocked'),
              icon: Icons.block,
            ),
            _SummaryCard(
              title: 'Unknown',
              value: _statusCount(countsByStatus, 'unknown'),
              icon: Icons.help_outline,
            ),
            _SummaryCard(
              title: 'Latest evidence',
              value: latestPortfolioTimestamp == null
                  ? 'Unknown'
                  : _format(latestPortfolioTimestamp),
              icon: Icons.schedule,
            ),
          ],
        ),
        const SizedBox(height: 16),
        GaiaSectionCard(
          title: 'Portfolio health',
          subtitle:
              '${controller.projectOfficerPortfolioPayload?['enabled_project_count']?.toString() ?? '0'} enabled projects',
          child: Column(
            children: [
              if (portfolioProjects.isEmpty)
                const ListTile(
                  title: Text('No project portfolio data available'),
                  subtitle: Text(
                    'Project Officer summaries will appear here once the backend provides them.',
                  ),
                ),
              for (final project in portfolioProjects)
                _projectHealthTile(context, project),
            ],
          ),
        ),
        const SizedBox(height: 16),
        GaiaSectionCard(
          title: 'Highest-priority recommendations',
          subtitle: 'Top backend-ranked items',
          child: Column(
            children: [
              if (recommendations.isEmpty)
                const ListTile(
                  title: Text('No recommendations available'),
                  subtitle: Text(
                    'The backend did not return ranked recommendations for this view.',
                  ),
                ),
              for (final recommendation in recommendations)
                _recommendationTile(recommendation),
            ],
          ),
        ),
        const SizedBox(height: 16),
        GaiaSectionCard(
          title: 'Blocked projects',
          subtitle: 'Canonical blocked state from GAIA recommendations',
          child: Column(
            children: [
              if (blockedProjects.isEmpty)
                const ListTile(
                  title: Text('No blocked projects'),
                  subtitle: Text(
                    'The backend did not report any blocked project summaries.',
                  ),
                ),
              for (final project in blockedProjects)
                _blockedProjectTile(project),
            ],
          ),
        ),
        const SizedBox(height: 16),
        GaiaSectionCard(
          title: 'Pending approvals',
          subtitle: 'Display only - review in GAIA Control Centre',
          child: Column(
            children: [
              if (pendingApprovals.isEmpty)
                const ListTile(
                  title: Text('No pending approvals'),
                  subtitle: Text(
                    'There are no work packages waiting for human review right now.',
                  ),
                ),
              for (final workPackage in pendingApprovals)
                _pendingApprovalTile(workPackage),
            ],
          ),
        ),
        const SizedBox(height: 16),
        GaiaSectionCard(
          title: 'Stale evidence',
          subtitle: 'Canonical stale-evidence warnings from Project Officer',
          child: Column(
            children: [
              if (staleEvidenceItems.isEmpty)
                const ListTile(
                  title: Text('No stale evidence warnings'),
                  subtitle: Text(
                    'The backend did not report any stale evidence for this portfolio refresh.',
                  ),
                ),
              for (final project in staleEvidenceItems)
                _staleEvidenceTile(project),
            ],
          ),
        ),
        const SizedBox(height: 16),
        GaiaSectionCard(
          title: 'Recent completed work',
          subtitle: 'Read-only outcome history',
          child: Column(
            children: [
              if (recentCompletedWork.isEmpty)
                const ListTile(
                  title: Text('No completed work yet'),
                  subtitle: Text(
                    'Completed work will appear here when the backend records outcomes.',
                  ),
                ),
              for (final outcome in recentCompletedWork)
                _completedWorkTile(outcome),
            ],
          ),
        ),
        const SizedBox(height: 16),
        GaiaSectionCard(
          title: 'Trust alerts',
          subtitle:
              '${trustAlerts.length} active alerts in the GAIA trust subsystem',
          child: Column(
            children: [
              if (trustAlerts.isEmpty)
                const ListTile(
                  title: Text('No trust alerts'),
                  subtitle: Text('The trust subsystem is currently quiet.'),
                ),
              for (final alert in trustAlerts.take(5)) _trustAlertTile(alert),
            ],
          ),
        ),
      ],
    );
  }
}

class _ProvenanceTab extends StatelessWidget {
  const _ProvenanceTab({required this.controller});

  final GaiaDashboardController controller;

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(24),
      children: [
        GaiaSectionCard(
          title: 'Signing keys',
          subtitle: '${controller.signingKeys.length} stored locally',
          child: Column(
            children: [
              for (final key in controller.signingKeys)
                ListTile(
                  leading: Icon(
                    key.status == 'active' ? Icons.key : Icons.key_off,
                    color: key.status == 'active'
                        ? Colors.green
                        : Colors.orange,
                  ),
                  title: Text(key.keyName),
                  subtitle: Text(key.publicKey),
                  trailing: Text(key.status),
                ),
            ],
          ),
        ),
        const SizedBox(height: 16),
        GaiaSectionCard(
          title: 'Provenance manifests',
          subtitle:
              '${controller.provenanceManifests.length} deterministic records',
          child: Column(
            children: [
              for (final manifest in controller.provenanceManifests.take(8))
                ListTile(
                  leading: Icon(
                    manifest.signatureStatus == 'cryptographically_signed'
                        ? Icons.verified
                        : manifest.signatureStatus == 'signing_key_revoked'
                        ? Icons.verified_user_outlined
                        : Icons.description_outlined,
                    color: manifest.signatureStatus == 'signature_invalid'
                        ? Colors.red
                        : manifest.signatureStatus == 'signing_key_revoked'
                        ? Colors.orange
                        : Colors.green,
                  ),
                  title: Text(
                    '${manifest.subjectKind} - ${manifest.subjectId}',
                  ),
                  subtitle: Text(manifest.contentHash),
                  trailing: Text(manifest.signatureStatus),
                ),
            ],
          ),
        ),
      ],
    );
  }
}

class _TrustTab extends StatelessWidget {
  const _TrustTab({required this.controller});

  final GaiaDashboardController controller;

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(24),
      children: [
        GaiaSectionCard(
          title: 'Trust alerts',
          subtitle: '${controller.trustAlerts.length} active alerts',
          child: Column(
            children: [
              for (final alert in controller.trustAlerts)
                ListTile(
                  leading: Icon(
                    alert.severity == 'critical'
                        ? Icons.error
                        : Icons.warning_amber,
                    color: alert.severity == 'critical'
                        ? Colors.red
                        : Colors.orange,
                  ),
                  title: Text(alert.title),
                  subtitle: Text(alert.message),
                  trailing: Text(alert.status),
                ),
            ],
          ),
        ),
        const SizedBox(height: 16),
        GaiaSectionCard(
          title: 'Latest receipt chain',
          subtitle: controller.latestReceipt?.chainId ?? 'No chain yet',
          child: controller.latestReceipt == null
              ? const Text(
                  'Create and execute a local action to populate the receipt chain.',
                )
              : GaiaKeyValueGrid(
                  rows: [
                    ('Receipt', controller.latestReceipt!.receiptId),
                    ('Chain', controller.latestReceipt!.chainId ?? 'None'),
                    (
                      'Sequence',
                      controller.latestReceipt!.chainSequence?.toString() ??
                          'None',
                    ),
                    (
                      'Verification',
                      controller.latestReceipt!.verificationStatus,
                    ),
                  ],
                ),
        ),
      ],
    );
  }
}

class _RetentionTab extends StatelessWidget {
  const _RetentionTab({required this.controller});

  final GaiaDashboardController controller;

  @override
  Widget build(BuildContext context) {
    final report = controller.retentionReport;
    return ListView(
      padding: const EdgeInsets.all(24),
      children: [
        GaiaSectionCard(
          title: 'Retention report',
          subtitle: report == null
              ? 'Unavailable'
              : _format(report.generatedAt),
          child: report == null
              ? const Text(
                  'Retention reporting will appear once the backend is reachable.',
                )
              : GaiaKeyValueGrid(
                  rows: [
                    ('Policies', report.policyCount.toString()),
                    ('Enabled', report.enabledPolicyCount.toString()),
                    ('Plans', report.planCount.toString()),
                    ('Receipts', report.receiptCount.toString()),
                    (
                      'Issues',
                      report.issues.isEmpty ? 'None' : report.issues.join('; '),
                    ),
                  ],
                ),
        ),
        const SizedBox(height: 16),
        GaiaSectionCard(
          title: 'Retention policies',
          subtitle: '${controller.retentionPolicies.length} policies',
          child: Column(
            children: [
              for (final policy in controller.retentionPolicies)
                ListTile(
                  leading: Icon(
                    policy.enabled
                        ? Icons.inventory_2
                        : Icons.inventory_2_outlined,
                  ),
                  title: Text(policy.policyId),
                  subtitle: Text(
                    '${policy.retentionClass} - maximum age ${policy.maximumAgeDays?.toString() ?? "none"}',
                  ),
                ),
            ],
          ),
        ),
      ],
    );
  }
}

class _SummaryCard extends StatelessWidget {
  const _SummaryCard({
    required this.title,
    required this.value,
    required this.icon,
  });

  final String title;
  final Object value;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 220,
      child: Card(
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Icon(icon, color: Theme.of(context).colorScheme.primary),
              const SizedBox(height: 12),
              Text(title, style: Theme.of(context).textTheme.bodySmall),
              const SizedBox(height: 4),
              Text(
                value.toString(),
                style: Theme.of(context).textTheme.headlineSmall,
              ),
            ],
          ),
        ),
      ),
    );
  }
}

Widget _projectHealthTile(BuildContext context, Map<String, dynamic> project) {
  final latestSnapshot = _mapValue(project['latest_snapshot']);
  final gitState = _mapValue(
    _mapValue(latestSnapshot['normalized_payload'])['git_state'],
  );
  final status = _stringValue(
    project,
    'normalized_status',
    fallback: 'unknown',
  );
  final freshness = _stringValue(
    project,
    'evidence_freshness',
    fallback: 'unknown',
  );
  final branch = _stringValue(gitState, 'branch', fallback: 'unknown');
  final commitSha = _stringValue(gitState, 'commit_sha', fallback: '');
  final shortSha = _shortSha(commitSha);
  final isClean = _boolValue(gitState['is_clean']);
  final reasonSummary = _stringList(project['reason_codes']).join(', ');
  return Card(
    margin: const EdgeInsets.symmetric(vertical: 6),
    child: Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      _stringValue(
                        project,
                        'project_name',
                        fallback: 'Unknown project',
                      ),
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                    const SizedBox(height: 4),
                    Text(
                      _stringValue(project, 'project_id', fallback: 'unknown'),
                    ),
                  ],
                ),
              ),
              GaiaStatusPill(
                label: status,
                color: _projectStatusColor(status),
                icon: Icons.folder,
              ),
            ],
          ),
          const SizedBox(height: 12),
          GaiaKeyValueGrid(
            rows: [
              ('Reason', reasonSummary.isEmpty ? 'None' : reasonSummary),
              ('Branch', branch),
              ('Short SHA', shortSha),
              ('Clean', isClean ? 'clean' : 'dirty'),
              ('Freshness', freshness),
            ],
          ),
        ],
      ),
    ),
  );
}

Widget _recommendationTile(Map<String, dynamic> recommendation) {
  final isBlocked =
      _stringValue(recommendation, 'lifecycle_state') == 'blocked' ||
      _mapList(recommendation['blockers']).isNotEmpty;
  final blockers = _mapList(recommendation['blockers']);
  final conciseSummary = _stringValue(recommendation, 'concise_summary').isEmpty
      ? _stringValue(recommendation, 'why_it_matters')
      : _stringValue(recommendation, 'concise_summary');
  return Card(
    margin: const EdgeInsets.symmetric(vertical: 6),
    child: ListTile(
      leading: GaiaStatusPill(
        label: _stringValue(recommendation, 'priority_tier', fallback: 'P4'),
        color: _priorityColor(
          _stringValue(recommendation, 'priority_tier', fallback: 'P4'),
        ),
        icon: Icons.flag,
      ),
      title: Text(
        _stringValue(
          recommendation,
          'title',
          fallback: 'Untitled recommendation',
        ),
      ),
      subtitle: Text(
        [
          'Score ${_stringValue(recommendation, 'deterministic_score', fallback: '0')}',
          _stringValue(
            recommendation,
            'project_id',
            fallback: 'unknown project',
          ),
          conciseSummary.isEmpty ? 'No rationale available' : conciseSummary,
          'Freshness: ${_stringValue(recommendation, 'evidence_freshness', fallback: 'unknown')}',
          if (isBlocked)
            'Blocked: ${blockers.isEmpty ? 'yes' : _stringValue(blockers.first, 'blocker_description', fallback: 'yes')}',
        ].join(' | '),
      ),
    ),
  );
}

Widget _blockedProjectTile(Map<String, dynamic> project) {
  final latestRecommendations = _mapList(project['latest_recommendations']);
  final blockerReason =
      latestRecommendations.isNotEmpty &&
          _mapList(latestRecommendations.first['blockers']).isNotEmpty
      ? _stringValue(
          _mapList(latestRecommendations.first['blockers']).first,
          'blocker_description',
          fallback: 'Blocked by backend recommendation state',
        )
      : 'Blocked by backend recommendation state';
  final blockedCount = _intValue(project['blocked_recommendation_count']);
  final freshness = _stringValue(
    project,
    'latest_lifecycle_state',
    fallback: 'unknown',
  );
  return Card(
    margin: const EdgeInsets.symmetric(vertical: 6),
    child: ListTile(
      leading: const Icon(Icons.block, color: Colors.red),
      title: Text(
        _stringValue(project, 'project_name', fallback: 'Unknown project'),
      ),
      subtitle: Text(
        [
          'Project: ${_stringValue(project, 'project_id', fallback: 'unknown')}',
          'Reason: $blockerReason',
          'Recommendations: $blockedCount',
          'Freshness: $freshness',
        ].join(' | '),
      ),
    ),
  );
}

Widget _pendingApprovalTile(Map<String, dynamic> workPackage) {
  return Card(
    margin: const EdgeInsets.symmetric(vertical: 6),
    child: ListTile(
      leading: const Icon(Icons.hourglass_bottom, color: Colors.orange),
      title: Text(
        _stringValue(workPackage, 'title', fallback: 'Pending work package'),
      ),
      subtitle: Text(
        [
          'Project: ${_stringValue(workPackage, 'project_id', fallback: 'unknown')}',
          'Package: ${_stringValue(workPackage, 'work_package_id', fallback: 'unknown')}',
          'Revision: ${_stringValue(workPackage, 'current_revision_number', fallback: '1')}',
          'Risk: ${_stringValue(workPackage, 'risk_classification', fallback: 'unknown')}',
          'State: ${_stringValue(workPackage, 'approval_state', fallback: 'unknown')}',
          'Freshness: ${_stringValue(workPackage, 'staleness_state', fallback: 'unknown')}',
        ].join(' | '),
      ),
    ),
  );
}

Widget _staleEvidenceTile(Map<String, dynamic> project) {
  return Card(
    margin: const EdgeInsets.symmetric(vertical: 6),
    child: ListTile(
      leading: const Icon(Icons.history, color: Colors.orange),
      title: Text(
        _stringValue(project, 'project_name', fallback: 'Unknown project'),
      ),
      subtitle: Text(
        [
          'Project: ${_stringValue(project, 'project_id', fallback: 'unknown')}',
          'Health: ${_stringValue(project, 'latest_health_status', fallback: 'unknown')}',
          'Comparison: ${_stringValue(project, 'latest_comparison_id', fallback: 'none')}',
          'Freshness: ${_stringValue(project, 'latest_comparison_freshness', fallback: 'unknown')}',
        ].join(' | '),
      ),
    ),
  );
}

Widget _completedWorkTile(Map<String, dynamic> outcome) {
  return Card(
    margin: const EdgeInsets.symmetric(vertical: 6),
    child: ListTile(
      leading: const Icon(Icons.check_circle, color: Colors.green),
      title: Text(_stringValue(outcome, 'outcome', fallback: 'completed')),
      subtitle: Text(
        [
          'Project: ${_stringValue(outcome, 'project_id', fallback: 'unknown')}',
          'Package: ${_stringValue(outcome, 'work_package_id', fallback: 'unknown')}',
          'Revision: ${_stringValue(outcome, 'revision_number', fallback: 'unknown')}',
          'Completed: ${_stringValue(outcome, 'recorded_at', fallback: 'unknown')}',
          'Evidence: ${_stringValue(outcome, 'evidence_fingerprint', fallback: 'none')}',
        ].join(' | '),
      ),
    ),
  );
}

Widget _trustAlertTile(GaiaTrustAlert alert) {
  return Card(
    margin: const EdgeInsets.symmetric(vertical: 6),
    child: ListTile(
      leading: Icon(
        alert.severity == 'critical' ? Icons.error : Icons.warning_amber,
        color: alert.severity == 'critical' ? Colors.red : Colors.orange,
      ),
      title: Text(alert.title),
      subtitle: Text(alert.message),
      trailing: Text(alert.status),
    ),
  );
}

Color _projectOfficerColor(GaiaProjectOfficerSummaryState state) {
  return switch (state) {
    GaiaProjectOfficerSummaryState.ready => Colors.green,
    GaiaProjectOfficerSummaryState.empty => Colors.teal,
    GaiaProjectOfficerSummaryState.stale => Colors.orange,
    GaiaProjectOfficerSummaryState.partial => Colors.amber,
    GaiaProjectOfficerSummaryState.unavailable => Colors.blueGrey,
    GaiaProjectOfficerSummaryState.incompatible => Colors.red,
    GaiaProjectOfficerSummaryState.loading => Colors.blue,
    GaiaProjectOfficerSummaryState.error => Colors.red,
  };
}

Color _projectStatusColor(String status) {
  return switch (status) {
    'healthy' => Colors.green,
    'attention' => Colors.orange,
    'blocked' => Colors.red,
    _ => Colors.blueGrey,
  };
}

Color _priorityColor(String tier) {
  return switch (tier) {
    'P0' => Colors.red,
    'P1' => Colors.deepOrange,
    'P2' => Colors.orange,
    'P3' => Colors.amber,
    _ => Colors.blueGrey,
  };
}

int _statusCount(Map<String, dynamic> counts, String key) =>
    _intValue(counts[key]);

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

int _intValue(Object? value) {
  if (value is int) {
    return value;
  }
  return int.tryParse(value?.toString() ?? '') ?? 0;
}

bool _boolValue(Object? value) => value is bool ? value : false;

DateTime? _mapDateTime(Map<String, dynamic>? map, String key) {
  if (map == null) {
    return null;
  }
  final value = map[key];
  if (value == null) {
    return null;
  }
  return DateTime.tryParse(value.toString());
}

String _format(DateTime value) {
  return value.toIso8601String().replaceFirst('T', ' ').split('.').first;
}

String _shortSha(String commitSha) {
  if (commitSha.length <= 8) {
    return commitSha;
  }
  return commitSha.substring(0, 8);
}
