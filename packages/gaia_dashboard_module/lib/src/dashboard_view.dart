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
        final freshness = controller.dataStale
            ? 'Stale data'
            : controller.lastSuccessfulRefreshAt == null
                ? 'No successful refresh yet'
                : 'Fresh as of ${_format(controller.lastSuccessfulRefreshAt!)}';
        return DefaultTabController(
          length: 5,
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
                    subtitle: 'The module preserved stale data and failed closed.',
                    child: Text(controller.errorMessage!),
                  ),
                ),
              const SizedBox(height: 8),
              const TabBar(
                isScrollable: true,
                tabs: [
                  Tab(text: 'Overview'),
                  Tab(text: 'Capabilities'),
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
            _SummaryCard(title: 'Projects', value: '${controller.projects.length}', icon: Icons.folder),
            _SummaryCard(title: 'Tasks', value: '${controller.taskSummary?.total ?? 0}', icon: Icons.task_alt),
            _SummaryCard(title: 'Approvals', value: '${controller.approvalSummary?.total ?? 0}', icon: Icons.verified),
            _SummaryCard(title: 'Actions', value: '${controller.actionSummary?.total ?? 0}', icon: Icons.play_circle),
          ],
        ),
        const SizedBox(height: 16),
        GaiaSectionCard(
          title: 'Workspace status',
          subtitle: 'Read-only embedded operations workspace',
          child: GaiaKeyValueGrid(
            rows: [
              ('Backend', controller.compatibility?.backendVersion ?? 'unknown'),
              ('Contract', controller.compatibility?.integrationContractVersion ?? 'unknown'),
              ('Client', controller.compatibility?.clientPackageVersion ?? 'unknown'),
              ('Capabilities', controller.capabilityPayload?['capability_version']?.toString() ?? 'unknown'),
              ('Last refresh', controller.lastSuccessfulRefreshAt == null ? 'Never' : _format(controller.lastSuccessfulRefreshAt!)),
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
              ('Receipt verification', controller.latestReceipt?.verificationStatus ?? 'unknown'),
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
    final capabilities = controller.compatibility?.capabilityCatalog ?? const <GaiaCapabilityDescriptor>[];
    return ListView(
      padding: const EdgeInsets.all(24),
      children: [
        GaiaSectionCard(
          title: 'Capability discovery',
          subtitle: controller.compatibility?.capabilityVersion ?? 'Unavailable',
          child: Column(
            children: [
              for (final capability in capabilities)
                ListTile(
                  leading: Icon(
                    capability.enabled ? Icons.check_circle : Icons.info_outline,
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
                    color: key.status == 'active' ? Colors.green : Colors.orange,
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
          subtitle: '${controller.provenanceManifests.length} deterministic records',
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
                  title: Text('${manifest.subjectKind} - ${manifest.subjectId}'),
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
                    alert.severity == 'critical' ? Icons.error : Icons.warning_amber,
                    color: alert.severity == 'critical' ? Colors.red : Colors.orange,
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
              ? const Text('Create and execute a local action to populate the receipt chain.')
              : GaiaKeyValueGrid(
                  rows: [
                    ('Receipt', controller.latestReceipt!.receiptId),
                    ('Chain', controller.latestReceipt!.chainId ?? 'None'),
                    ('Sequence', controller.latestReceipt!.chainSequence?.toString() ?? 'None'),
                    ('Verification', controller.latestReceipt!.verificationStatus),
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
          subtitle: report == null ? 'Unavailable' : _format(report.generatedAt),
          child: report == null
              ? const Text('Retention reporting will appear once the backend is reachable.')
              : GaiaKeyValueGrid(
                  rows: [
                    ('Policies', report.policyCount.toString()),
                    ('Enabled', report.enabledPolicyCount.toString()),
                    ('Plans', report.planCount.toString()),
                    ('Receipts', report.receiptCount.toString()),
                    ('Issues', report.issues.isEmpty ? 'None' : report.issues.join('; ')),
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
                  leading: Icon(policy.enabled ? Icons.inventory_2 : Icons.inventory_2_outlined),
                  title: Text(policy.policyId),
                  subtitle: Text('${policy.retentionClass} - maximum age ${policy.maximumAgeDays?.toString() ?? "none"}'),
                ),
            ],
          ),
        ),
      ],
    );
  }
}

class _SummaryCard extends StatelessWidget {
  const _SummaryCard({required this.title, required this.value, required this.icon});

  final String title;
  final String value;
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
              Text(value, style: Theme.of(context).textTheme.headlineSmall),
            ],
          ),
        ),
      ),
    );
  }
}

String _format(DateTime value) {
  return value.toIso8601String().replaceFirst('T', ' ').split('.').first;
}
