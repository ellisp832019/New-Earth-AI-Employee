import 'package:flutter/material.dart';

import 'package:gaia_dashboard_module/gaia_dashboard_module.dart';
import 'package:gaia_integration_client/gaia_integration_client.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const GaiaDashboardHostApp());
}

class GaiaDashboardHostApp extends StatefulWidget {
  const GaiaDashboardHostApp({super.key});

  @override
  State<GaiaDashboardHostApp> createState() => _GaiaDashboardHostAppState();
}

class _GaiaDashboardHostAppState extends State<GaiaDashboardHostApp> {
  late final GaiaDashboardController controller;
  ThemeMode themeMode = ThemeMode.system;

  @override
  void initState() {
    super.initState();
    controller = GaiaDashboardController(
      client: GaiaIntegrationClient(
        baseUri: Uri.parse('http://127.0.0.1:8765'),
      ),
    );
    controller.refresh();
  }

  @override
  void dispose() {
    controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final lightTheme = ThemeData(
      colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFF0F766E), brightness: Brightness.light),
      useMaterial3: true,
    );
    final darkTheme = ThemeData(
      colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFF67E8F9), brightness: Brightness.dark),
      useMaterial3: true,
    );
    return MaterialApp(
      title: 'GAIA Dashboard Host',
      debugShowCheckedModeBanner: false,
      theme: lightTheme,
      darkTheme: darkTheme,
      themeMode: themeMode,
      home: Scaffold(
        appBar: AppBar(
          title: const Text('GAIA Dashboard Host'),
          actions: [
            IconButton(
              tooltip: 'Refresh',
              onPressed: () => controller.refresh(),
              icon: const Icon(Icons.refresh),
            ),
            PopupMenuButton<ThemeMode>(
              onSelected: (value) => setState(() => themeMode = value),
              itemBuilder: (context) => const [
                PopupMenuItem(value: ThemeMode.system, child: Text('System theme')),
                PopupMenuItem(value: ThemeMode.light, child: Text('Light theme')),
                PopupMenuItem(value: ThemeMode.dark, child: Text('Dark theme')),
              ],
            ),
          ],
        ),
        body: Column(
          children: [
            _BoundaryBanner(controller: controller),
            const Divider(height: 1),
            Expanded(
              child: DefaultTabController(
                length: 3,
                child: Column(
                  children: [
                    const TabBar(
                      tabs: [
                        Tab(text: 'Overview'),
                        Tab(text: 'Trust'),
                        Tab(text: 'Diagnostics'),
                      ],
                    ),
                    Expanded(
                      child: TabBarView(
                        children: [
                          GaiaDashboardView(controller: controller),
                          _TrustTab(controller: controller),
                          _DiagnosticsTab(controller: controller),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _BoundaryBanner extends StatelessWidget {
  const _BoundaryBanner({required this.controller});

  final GaiaDashboardController controller;

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: controller,
      builder: (context, _) {
        return MaterialBanner(
          content: Text(
            controller.connectionState == GaiaDashboardConnectionState.connected
                ? 'Connected to loopback GAIA backend. The module is read-mostly and will not execute actions.'
                : 'Dashboard module is operating in degraded or unavailable mode.',
          ),
          leading: const Icon(Icons.shield_outlined),
          actions: [
            TextButton(
              onPressed: controller.refresh,
              child: const Text('Refresh'),
            ),
          ],
        );
      },
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
          title: 'Trust Centre',
          subtitle: 'Read-only dashboard module boundary',
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('Action execution stays inside the Windows Control Centre or CLI.'),
              const SizedBox(height: 16),
              Wrap(
                spacing: 8,
                children: [
                  for (final template in controller.actionTemplates.take(4))
                    Chip(label: Text(template.templateId)),
                ],
              ),
            ],
          ),
        ),
        const SizedBox(height: 16),
        GaiaSectionCard(
          title: 'Retention',
          subtitle: 'Default-preserve policies',
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              for (final policy in controller.retentionPolicies)
                ListTile(
                  title: Text(policy.policyId),
                  subtitle: Text('${policy.retentionClass} · preserve=${policy.preserveAuditLinkedRecords}'),
                ),
            ],
          ),
        ),
      ],
    );
  }
}

class _DiagnosticsTab extends StatelessWidget {
  const _DiagnosticsTab({required this.controller});

  final GaiaDashboardController controller;

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(24),
      children: [
        GaiaSectionCard(
          title: 'Compatibility',
          subtitle: controller.compatibility?.status ?? 'Unavailable',
          child: GaiaKeyValueGrid(
            rows: [
              ('Backend', controller.compatibility?.backendVersion ?? 'unknown'),
              ('Contract', controller.compatibility?.integrationContractVersion ?? 'unknown'),
              ('Client', controller.compatibility?.clientPackageVersion ?? 'unknown'),
              ('Capabilities', controller.compatibility?.capabilities.join(', ') ?? 'none'),
            ],
          ),
        ),
        const SizedBox(height: 16),
        GaiaSectionCard(
          title: 'Backend Status',
          subtitle: controller.errorMessage ?? 'OK',
          child: Text(controller.backendStatus?.toString() ?? 'No backend status yet'),
        ),
      ],
    );
  }
}
