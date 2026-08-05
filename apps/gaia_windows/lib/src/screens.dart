import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import 'controller.dart';
import 'models.dart';
import 'settings_store.dart';
import 'widgets.dart';

class GaiaShell extends StatefulWidget {
  const GaiaShell({super.key, required this.controller});

  final GaiaAppController controller;

  @override
  State<GaiaShell> createState() => _GaiaShellState();
}

class _GaiaShellState extends State<GaiaShell> {
  static const _destinations = <_Destination>[
    _Destination('Home', Icons.home_outlined, Icons.home),
    _Destination('Projects', Icons.folder_outlined, Icons.folder),
    _Destination('Ask GAIA', Icons.chat_bubble_outline, Icons.chat_bubble),
    _Destination('Evidence', Icons.fact_check_outlined, Icons.fact_check),
    _Destination('Snapshots', Icons.camera_alt_outlined, Icons.camera_alt),
    _Destination('Reports', Icons.description_outlined, Icons.description),
    _Destination('Agent Runs', Icons.timeline_outlined, Icons.timeline),
    _Destination('Audit', Icons.rule_folder_outlined, Icons.rule_folder),
    _Destination('Settings', Icons.settings_outlined, Icons.settings),
    _Destination('About', Icons.info_outline, Icons.info),
  ];

  int selectedIndex = 0;

  @override
  void initState() {
    super.initState();
    unawaited(widget.controller.refreshEverything());
  }

  @override
  Widget build(BuildContext context) {
    final controller = widget.controller;
    final body = IndexedStack(
      index: selectedIndex,
      children: [
        HomeScreen(controller: controller),
        ProjectsScreen(controller: controller),
        AskScreen(controller: controller),
        EvidenceScreen(controller: controller),
        SnapshotsScreen(controller: controller),
        ReportsScreen(controller: controller),
        AgentRunsScreen(controller: controller),
        AuditScreen(controller: controller),
        SettingsScreen(controller: controller),
        AboutScreen(controller: controller),
      ],
    );
    return Scaffold(
      appBar: AppBar(
        title: const Text('GAIA - Windows Control Centre'),
        actions: [
          _GlobalStatus(controller: controller),
          const SizedBox(width: 12),
        ],
      ),
      body: Column(
        children: [
          const ReadOnlyBanner(),
          Expanded(
            child: Row(
              children: [
                NavigationRail(
                  selectedIndex: selectedIndex,
                  onDestinationSelected: (index) => setState(() => selectedIndex = index),
                  labelType: NavigationRailLabelType.all,
                  leading: Padding(
                    padding: const EdgeInsets.only(top: 12),
                    child: Column(
                      children: [
                        Text('GAIA', style: Theme.of(context).textTheme.headlineSmall),
                        const SizedBox(height: 8),
                        Text(
                          controller.backendStatusLabel,
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
                  child: AnimatedBuilder(
                    animation: controller,
                    builder: (context, _) {
                      return body;
                    },
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _GlobalStatus extends StatelessWidget {
  const _GlobalStatus({required this.controller});

  final GaiaAppController controller;

  @override
  Widget build(BuildContext context) {
    final selectedProject = controller.selectedProject;
    final hasOllama = controller.models.any((model) => model.provider == 'ollama' && model.available);
    return Wrap(
      spacing: 8,
      runSpacing: 8,
      crossAxisAlignment: WrapCrossAlignment.center,
      children: [
        StatusChip(
          label: controller.backendStatusLabel,
          color: controller.backendState == BackendConnectionState.connected ? Colors.green : Colors.orange,
          icon: controller.backendState == BackendConnectionState.connected ? Icons.check_circle : Icons.cloud_off,
        ),
        StatusChip(
          label: controller.backendCompatibilityLabel,
          color: controller.backendCompatibilityColor,
          icon: Icons.verified_outlined,
        ),
        StatusChip(
          label: 'Read-only',
          color: Colors.blue,
          icon: Icons.lock,
        ),
        if (selectedProject != null)
          StatusChip(
            label: selectedProject.projectId,
            color: Colors.teal,
            icon: Icons.folder,
          ),
        StatusChip(
          label: hasOllama ? 'Ollama ready' : 'Deterministic',
          color: hasOllama ? Colors.purple : Colors.indigo,
          icon: hasOllama ? Icons.memory : Icons.auto_fix_high,
        ),
      ],
    );
  }
}

class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key, required this.controller});

  final GaiaAppController controller;

  @override
  Widget build(BuildContext context) {
    final project = controller.selectedProject;
    final snapshot = controller.snapshots.isNotEmpty ? controller.snapshots.first : null;
    final latestRun = controller.agentRuns.isNotEmpty ? controller.agentRuns.first : null;
    final latestReport = controller.reports[project?.projectId ?? ''];
    return _ScreenScaffold(
      title: 'Home',
      subtitle: 'Operational status and quick actions',
      child: ListView(
        children: [
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: [
              _statusCard(
                'GAIA Status',
                controller.health?.status ?? controller.backendStatusLabel,
                controller.backendState == BackendConnectionState.connected &&
                    controller.backendCompatibilityState == BackendCompatibilityState.compatible,
              ),
              _statusCard('Projects', '${controller.projects.length}', controller.projects.isNotEmpty),
              _statusCard('Selected Project', project?.name ?? 'None selected', project != null),
              _statusCard('Working Tree', snapshot?.git.isClean == true ? 'Clean' : 'Changed', snapshot?.git.isClean == true),
            ],
          ),
          const SizedBox(height: 16),
          Row(
            children: [
              Expanded(
                child: SectionCard(
                  title: 'Backend Health',
                  subtitle: controller.health?.version ?? controller.lastError ?? 'Not connected',
                  trailing: _quickActionButtons(context, controller),
                  child: _keyValueGrid([
                    ('Database', controller.health?.databasePath ?? 'Unknown'),
                    ('FTS5', controller.health?.fts5Available == true ? 'Available' : 'Unavailable'),
                    ('Port', Uri.parse(controller.settings.backendUrl).port.toString()),
                    ('Logs', '${controller.backendLogs.length} lines'),
                  ]),
                ),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: SectionCard(
                  title: 'Current Project',
                  subtitle: project?.projectId ?? 'No project selected',
                  child: _keyValueGrid([
                    ('Branch', snapshot?.git.branch ?? 'Unknown'),
                    ('Commit', snapshot?.git.commitSha ?? 'Unknown'),
                    ('Documents', snapshot?.documentCount.toString() ?? '0'),
                    ('Warnings', snapshot?.scanWarnings.length.toString() ?? '0'),
                  ]),
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          SectionCard(
            title: 'Recent Warnings',
            child: _warningList(controller),
          ),
          const SizedBox(height: 16),
          SectionCard(
            title: 'Latest Agent Run',
            subtitle: latestRun?.question ?? 'No runs yet',
            child: latestRun == null
                ? const Text('Ask a question to populate the run history.')
                : _runSummary(latestRun),
          ),
          const SizedBox(height: 16),
          SectionCard(
            title: 'Latest Report',
            subtitle: project?.projectId ?? 'No report generated yet',
            child: latestReport == null
                ? const Text('Generate a foundation report to view it here.')
                : MarkdownView(data: latestReport),
          ),
          const SizedBox(height: 16),
          if (snapshot != null)
            SectionCard(
              title: 'Latest Snapshot',
              subtitle: snapshot.snapshotId,
              child: _snapshotSummary(snapshot),
            ),
        ],
      ),
    );
  }

  Widget _quickActionButtons(BuildContext context, GaiaAppController controller) {
    final project = controller.selectedProject;
    if (project == null) {
      return const SizedBox.shrink();
    }
    return Wrap(
      spacing: 8,
      children: [
        FilledButton(
          onPressed: controller.busy ? null : () => controller.runScan(project.projectId),
          child: const Text('Scan'),
        ),
        FilledButton.tonal(
          onPressed: controller.busy ? null : () => controller.createSnapshot(project.projectId),
          child: const Text('Snapshot'),
        ),
        OutlinedButton(
          onPressed: controller.busy
              ? null
              : () => controller.askGaia(
                    projectId: project.projectId,
                    question: 'What was completed most recently?',
                    provider: controller.settings.preferredProvider,
                    modelName: controller.settings.preferredModelName,
                    evidenceLimit: controller.settings.defaultEvidenceLimit,
                    deterministicOnly: controller.settings.deterministicOnlyDefault,
                    refreshSnapshot: false,
                  ),
          child: const Text('Ask'),
        ),
      ],
    );
  }

  Widget _warningList(GaiaAppController controller) {
    final warnings = <String>[
      ...controller.backendLogs.takeLast(3),
      if (controller.lastError != null) controller.lastError!,
      if (controller.backendCompatibilityState == BackendCompatibilityState.incompatible)
        'Backend version ${controller.health?.version ?? 'unknown'} is incompatible with the v0.3 desktop client.',
    ].where((item) => item.trim().isNotEmpty).toList();
    if (warnings.isEmpty) {
      return const Text('No recent warnings.');
    }
    return Column(
      children: [
        for (final warning in warnings) ListTile(leading: const Icon(Icons.warning_amber), title: Text(warning)),
      ],
    );
  }

  Widget _runSummary(AgentRunRecord run) {
    return _keyValueGrid([
      ('Run ID', run.runId),
      ('Category', run.questionCategory),
      ('Provider', run.provider),
      ('Confidence', run.confidence),
      ('Snapshot', run.snapshotId ?? 'None'),
      ('Warnings', run.warnings.length.toString()),
    ]);
  }

  Widget _snapshotSummary(RepositorySnapshot snapshot) {
    return _keyValueGrid([
      ('Branch', snapshot.git.branch ?? 'Unknown'),
      ('Commit', snapshot.git.commitSha ?? 'Unknown'),
      ('Documents', snapshot.documentCount.toString()),
      ('Indexed', snapshot.indexedCount.toString()),
      ('Skipped', snapshot.skippedCount.toString()),
      ('Failed', snapshot.failedCount.toString()),
    ]);
  }
}

class ProjectsScreen extends StatelessWidget {
  const ProjectsScreen({super.key, required this.controller});

  final GaiaAppController controller;

  @override
  Widget build(BuildContext context) {
    return _ScreenScaffold(
      title: 'Projects',
      subtitle: 'Registered projects and read-only status',
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(
            flex: 2,
            child: SectionCard(
              title: 'Projects',
              child: Column(
                children: [
                  for (final project in controller.projects)
                    Card(
                      child: ListTile(
                        selected: project.projectId == controller.selectedProjectId,
                        onTap: () => controller.selectProject(project.projectId),
                        title: Text(project.name),
                        subtitle: Text('${project.projectId} • ${project.access} • ${controller.maskPath(project.root)}'),
                        trailing: project.projectId == 'microgrow-v1'
                            ? const Chip(label: Text('READ-ONLY EXTERNAL PROJECT'))
                            : null,
                      ),
                    ),
                ],
              ),
            ),
          ),
          const SizedBox(width: 16),
          Expanded(
            flex: 3,
            child: SectionCard(
              title: 'Project Detail',
              subtitle: controller.selectedProject?.name ?? 'No selection',
              child: _ProjectDetailView(controller: controller),
            ),
          ),
        ],
      ),
    );
  }
}

class _ProjectDetailView extends StatelessWidget {
  const _ProjectDetailView({required this.controller});

  final GaiaAppController controller;

  @override
  Widget build(BuildContext context) {
    final project = controller.selectedProject;
    final snapshot = controller.snapshots.where((item) => item.projectId == project?.projectId).isNotEmpty
        ? controller.snapshots.firstWhere((item) => item.projectId == project?.projectId)
        : null;
    if (project == null) {
      return const Text('Select a project to see detail.');
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (project.projectId == 'microgrow-v1')
          const Padding(
            padding: EdgeInsets.only(bottom: 12),
            child: Chip(label: Text('READ-ONLY EXTERNAL PROJECT')),
          ),
        _keyValueGrid([
          ('Project ID', project.projectId),
          ('Access', project.access),
          ('Root', controller.maskPath(project.root)),
          ('Current Branch', snapshot?.git.branch ?? 'Unknown'),
          ('Current SHA', snapshot?.git.commitSha ?? 'Unknown'),
          ('Clean', snapshot?.git.isClean == true ? 'Yes' : 'No'),
          ('Indexed docs', snapshot?.indexedCount.toString() ?? '0'),
          ('Warnings', snapshot?.scanWarnings.length.toString() ?? '0'),
        ]),
        const SizedBox(height: 12),
        Wrap(
          spacing: 8,
          children: [
            FilledButton(
              onPressed: () => controller.runScan(project.projectId),
              child: const Text('Scan'),
            ),
            FilledButton.tonal(
              onPressed: () => controller.createSnapshot(project.projectId),
              child: const Text('Snapshot'),
            ),
          ],
        ),
      ],
    );
  }
}

class AskScreen extends StatefulWidget {
  const AskScreen({super.key, required this.controller});

  final GaiaAppController controller;

  @override
  State<AskScreen> createState() => _AskScreenState();
}

class _AskScreenState extends State<AskScreen> {
  final TextEditingController questionController = TextEditingController(text: 'Where exactly is MicroGrow currently?');
  String provider = 'mock';
  String modelName = '';
  bool deterministicOnly = true;
  bool refreshSnapshot = false;
  int evidenceLimit = 8;
  bool pending = false;

  @override
  void initState() {
    super.initState();
    provider = widget.controller.settings.preferredProvider;
    modelName = widget.controller.settings.preferredModelName;
    deterministicOnly = widget.controller.settings.deterministicOnlyDefault;
    evidenceLimit = widget.controller.settings.defaultEvidenceLimit;
  }

  @override
  void dispose() {
    questionController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final controller = widget.controller;
    final response = controller.lastAskResponse;
    final selectedProject = controller.selectedProject;
    return _ScreenScaffold(
      title: 'Ask GAIA',
      subtitle: 'Evidence-backed conversational workflow',
      child: ListView(
        children: [
          SectionCard(
            title: 'Question',
            trailing: FilledButton(
              onPressed: pending || controller.busy || selectedProject == null
                  ? null
                  : () async {
                      setState(() => pending = true);
                      try {
                        await controller.askGaia(
                          projectId: selectedProject.projectId,
                          question: questionController.text,
                          provider: provider,
                          modelName: modelName,
                          evidenceLimit: evidenceLimit,
                          deterministicOnly: deterministicOnly,
                          refreshSnapshot: refreshSnapshot,
                        );
                      } finally {
                        if (mounted) {
                          setState(() => pending = false);
                        }
                      }
                    },
              child: const Text('Send'),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                DropdownButtonFormField<String>(
                  key: ValueKey(selectedProject?.projectId),
                  initialValue: selectedProject?.projectId,
                  items: [
                    for (final project in controller.projects) DropdownMenuItem(value: project.projectId, child: Text(project.name)),
                  ],
                  onChanged: (value) => setState(() => controller.selectProject(value)),
                  decoration: const InputDecoration(labelText: 'Project'),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: questionController,
                  maxLines: 4,
                  decoration: const InputDecoration(
                    labelText: 'Question',
                    hintText: 'Ask something about the selected project',
                    border: OutlineInputBorder(),
                  ),
                ),
                const SizedBox(height: 12),
                Wrap(
                  spacing: 12,
                  runSpacing: 12,
                  children: [
                    SizedBox(
                      width: 240,
                      child: DropdownButtonFormField<String>(
                        key: ValueKey(provider),
                        initialValue: provider,
                        items: const [
                          DropdownMenuItem(value: 'mock', child: Text('Mock (deterministic)')),
                          DropdownMenuItem(value: 'ollama', child: Text('Ollama (local)')),
                        ],
                        onChanged: (value) => setState(() => provider = value ?? 'mock'),
                        decoration: const InputDecoration(labelText: 'Provider'),
                      ),
                    ),
                    SizedBox(
                      width: 240,
                      child: TextField(
                        onChanged: (value) => modelName = value,
                        controller: TextEditingController(text: modelName),
                        decoration: const InputDecoration(labelText: 'Model name'),
                      ),
                    ),
                    SizedBox(
                      width: 180,
                      child: TextField(
                        keyboardType: TextInputType.number,
                        onChanged: (value) => evidenceLimit = int.tryParse(value) ?? evidenceLimit,
                        decoration: const InputDecoration(labelText: 'Evidence limit'),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                Wrap(
                  spacing: 12,
                  children: [
                    FilterChip(
                      label: const Text('Deterministic only'),
                      selected: deterministicOnly,
                      onSelected: (value) => setState(() => deterministicOnly = value),
                    ),
                    FilterChip(
                      label: const Text('Refresh snapshot'),
                      selected: refreshSnapshot,
                      onSelected: (value) => setState(() => refreshSnapshot = value),
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: [
                    for (final suggestion in _suggestedQuestions)
                      ActionChip(
                        label: Text(suggestion),
                        onPressed: () => setState(() => questionController.text = suggestion),
                      ),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),
          if (controller.busy) const LinearProgressIndicator(),
          if (controller.statusMessage != null) Padding(
            padding: const EdgeInsets.only(top: 8),
            child: Text(controller.statusMessage!),
          ),
          const SizedBox(height: 16),
          if (response != null) _AnswerPanel(response: response, controller: controller),
        ],
      ),
    );
  }
}

class _AnswerPanel extends StatelessWidget {
  const _AnswerPanel({required this.response, required this.controller});

  final AskResponse response;
  final GaiaAppController controller;

  @override
  Widget build(BuildContext context) {
    final isPromptDraft = response.answer.contains('DRAFT - NOT EXECUTED');
    return Column(
      children: [
        SectionCard(
          title: 'Answer',
          subtitle: 'Run ${response.runId} • Snapshot ${response.snapshotId ?? 'none'} • Confidence ${response.confidence}',
          trailing: Wrap(
            spacing: 8,
            children: [
              CopyButton(text: response.answer, label: 'Copy answer'),
              if (isPromptDraft) CopyButton(text: response.answer, label: 'Copy prompt'),
            ],
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _section('Verified current state', Text(_answerSectionText(response.answer, 'Facts:'))),
              _section('Findings', Text(_answerSectionText(response.answer, 'Findings:'))),
              _section(
                'Evidence',
                Column(
                  children: [
                    for (final item in response.evidence)
                      EvidenceCard(item: item, onCopy: (text) async => Clipboard.setData(ClipboardData(text: text))),
                  ],
                ),
              ),
              _section('Inference', Text(_answerSectionText(response.answer, 'Inference:'))),
              _section('Recommendations', Text(_answerSectionText(response.answer, 'Recommendation:'))),
              _section('Unknowns', Text(_answerSectionText(response.answer, 'Unknowns:'))),
              _section('Warnings', response.warnings.isEmpty ? const Text('None') : _warningChips(response.warnings)),
              if (response.promptInjectionWarnings.isNotEmpty)
                _section('Prompt-injection warnings', _warningChips(response.promptInjectionWarnings)),
            ],
          ),
        ),
        if (isPromptDraft) ...[
          const SizedBox(height: 16),
          SectionCard(
            title: 'Codex Prompt Draft',
            subtitle: 'DRAFT - NOT EXECUTED',
            child: MarkdownView(data: response.answer),
          ),
        ],
      ],
    );
  }

  Widget _section(String title, Widget child) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title, style: const TextStyle(fontWeight: FontWeight.w700)),
          const SizedBox(height: 8),
          child,
        ],
      ),
    );
  }

  Widget _warningChips(List<String> warnings) {
    return Wrap(
      spacing: 8,
      runSpacing: 8,
      children: [for (final warning in warnings) Chip(label: Text(warning))],
    );
  }
}

class EvidenceScreen extends StatelessWidget {
  const EvidenceScreen({super.key, required this.controller});

  final GaiaAppController controller;

  @override
  Widget build(BuildContext context) {
    return _ScreenScaffold(
      title: 'Evidence',
      subtitle: 'Repository search and supporting evidence',
      child: ListView(
        children: [
          SectionCard(
            title: 'Current Evidence',
            child: controller.lastAskResponse == null
                ? const Text('Ask GAIA to populate evidence, or inspect the selected project documents below.')
                : Column(
                    children: [for (final item in controller.lastAskResponse!.evidence) EvidenceCard(item: item, onCopy: (text) => Clipboard.setData(ClipboardData(text: text)))],
                  ),
          ),
          const SizedBox(height: 16),
          SectionCard(
            title: 'Selected Project Documents',
            child: Column(
              children: [
                for (final doc in controller.documents)
                  ListTile(
                    leading: const Icon(Icons.description),
                    title: Text(doc.relativePath),
                    subtitle: Text('${doc.extension} • ${doc.indexingStatus} • ${doc.sha256.substring(0, 12)}'),
                  ),
              ],
            ),
          ),
          const SizedBox(height: 16),
          SectionCard(
            title: 'Search Results',
            child: Column(
              children: [
                for (final result in controller.searchResults)
                  ListTile(
                    title: Text(result.relativePath),
                    subtitle: Text(result.snippet),
                    trailing: Text(result.score?.toStringAsFixed(2) ?? ''),
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class SnapshotsScreen extends StatelessWidget {
  const SnapshotsScreen({super.key, required this.controller});

  final GaiaAppController controller;

  @override
  Widget build(BuildContext context) {
    return _ScreenScaffold(
      title: 'Snapshots',
      subtitle: 'Read-only repository snapshots',
      child: Column(
        children: [
          for (final snapshot in controller.snapshots)
            SectionCard(
              title: snapshot.projectName,
              subtitle: snapshot.snapshotId,
              child: _keyValueGrid([
                ('Project', snapshot.projectId),
                ('Branch', snapshot.git.branch ?? 'Unknown'),
                ('Commit', snapshot.git.commitSha ?? 'Unknown'),
                ('Clean', snapshot.git.isClean ? 'Yes' : 'No'),
                ('Documents', snapshot.documentCount.toString()),
                ('Indexed', snapshot.indexedCount.toString()),
                ('Warnings', snapshot.scanWarnings.length.toString()),
              ]),
            ),
        ],
      ),
    );
  }
}

class ReportsScreen extends StatelessWidget {
  const ReportsScreen({super.key, required this.controller});

  final GaiaAppController controller;

  @override
  Widget build(BuildContext context) {
    final project = controller.selectedProject;
    final report = project == null ? null : controller.reports[project.projectId];
    return _ScreenScaffold(
      title: 'Reports',
      subtitle: 'Foundation reports and safe local exports',
      child: ListView(
        children: [
          SectionCard(
            title: 'Generate report',
            child: Wrap(
              spacing: 8,
              children: [
                if (project != null)
                  FilledButton(
                    onPressed: () => controller.refreshReport(project.projectId),
                    child: const Text('Refresh foundation report'),
                  ),
                if (project != null)
                  FilledButton.tonal(
                    onPressed: () => controller.refreshReport(
                      project.projectId,
                      format: ReportFormatPreference.json,
                    ),
                    child: const Text('Refresh JSON'),
                  ),
              ],
            ),
          ),
          const SizedBox(height: 16),
          if (report != null)
            SectionCard(
              title: 'Latest report',
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      CopyButton(text: report),
                      const SizedBox(width: 8),
                      Expanded(child: Text('Saved through GAIA backend report endpoints only.', style: Theme.of(context).textTheme.bodySmall)),
                    ],
                  ),
                  const SizedBox(height: 16),
                  MarkdownView(data: report),
                ],
              ),
            ),
        ],
      ),
    );
  }
}

class AgentRunsScreen extends StatelessWidget {
  const AgentRunsScreen({super.key, required this.controller});

  final GaiaAppController controller;

  @override
  Widget build(BuildContext context) {
    return _ScreenScaffold(
      title: 'Agent Runs',
      subtitle: 'Stored conversational history',
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(
            flex: 2,
            child: SectionCard(
              title: 'Runs',
              child: Column(
                children: [
                  for (final run in controller.agentRuns)
                    ListTile(
                      title: Text(run.question),
                      subtitle: Text('${run.projectId} • ${run.provider} • ${run.confidence}'),
                    ),
                ],
              ),
            ),
          ),
          const SizedBox(width: 16),
          Expanded(
            flex: 3,
            child: SectionCard(
              title: 'Latest run detail',
              child: controller.agentRuns.isEmpty
                  ? const Text('Ask a question to populate agent runs.')
                  : _RunDetail(run: controller.agentRuns.first),
            ),
          ),
        ],
      ),
    );
  }
}

class _RunDetail extends StatelessWidget {
  const _RunDetail({required this.run});

  final AgentRunRecord run;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _keyValueGrid([
          ('Run ID', run.runId),
          ('Project', run.projectId),
          ('Question', run.question),
          ('Category', run.questionCategory),
          ('Status', run.status),
          ('Confidence', run.confidence),
          ('Snapshot', run.snapshotId ?? 'None'),
        ]),
        const SizedBox(height: 16),
        MarkdownView(data: encodeJsonPretty(run.structuredAnswer)),
      ],
    );
  }
}

class AuditScreen extends StatelessWidget {
  const AuditScreen({super.key, required this.controller});

  final GaiaAppController controller;

  @override
  Widget build(BuildContext context) {
    return _ScreenScaffold(
      title: 'Audit',
      subtitle: 'Read-only event history',
      child: SectionCard(
        title: 'Events',
        child: Column(
          children: [
            for (final event in controller.auditEvents)
              ListTile(
                title: Text('${event.category} • ${event.operation}'),
                subtitle: Text(event.metadata.toString()),
                trailing: Text(event.outcome),
              ),
          ],
        ),
      ),
    );
  }
}

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key, required this.controller});

  final GaiaAppController controller;

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  late TextEditingController backendUrlController;
  late TextEditingController rootController;
  late TextEditingController modelController;
  late TextEditingController projectController;
  late TextEditingController evidenceController;
  late TextEditingController retentionController;
  late BackendLaunchPreference launchPreference;
  late ThemePreference themePreference;
  late ReportFormatPreference reportPreference;
  late bool deterministicOnly;

  @override
  void initState() {
    super.initState();
    final settings = widget.controller.settings;
    backendUrlController = TextEditingController(text: settings.backendUrl);
    rootController = TextEditingController(text: settings.repositoryRootPath);
    modelController = TextEditingController(text: settings.preferredModelName);
    projectController = TextEditingController(text: settings.defaultProjectId);
    evidenceController = TextEditingController(text: settings.defaultEvidenceLimit.toString());
    retentionController = TextEditingController(text: settings.logRetentionDays.toString());
    launchPreference = settings.backendLaunchPreference;
    themePreference = settings.themePreference;
    reportPreference = settings.reportFormatPreference;
    deterministicOnly = settings.deterministicOnlyDefault;
  }

  @override
  void dispose() {
    backendUrlController.dispose();
    rootController.dispose();
    modelController.dispose();
    projectController.dispose();
    evidenceController.dispose();
    retentionController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return _ScreenScaffold(
      title: 'Settings',
      subtitle: 'Local preferences and safe defaults',
      child: ListView(
        children: [
          SectionCard(
            title: 'Application Settings',
            child: Column(
              children: [
                TextField(controller: rootController, decoration: const InputDecoration(labelText: 'Repository root')),
                TextField(controller: backendUrlController, decoration: const InputDecoration(labelText: 'Backend URL')),
                const SizedBox(height: 8),
                DropdownButtonFormField<BackendLaunchPreference>(
                  key: ValueKey(launchPreference),
                  initialValue: launchPreference,
                  items: const [
                    DropdownMenuItem(value: BackendLaunchPreference.connectExisting, child: Text('Connect to existing backend')),
                    DropdownMenuItem(value: BackendLaunchPreference.startLocal, child: Text('Start local backend')),
                  ],
                  onChanged: (value) => setState(() => launchPreference = value ?? BackendLaunchPreference.startLocal),
                  decoration: const InputDecoration(labelText: 'Backend launch preference'),
                ),
                TextField(controller: projectController, decoration: const InputDecoration(labelText: 'Default project')),
                TextField(controller: modelController, decoration: const InputDecoration(labelText: 'Preferred model')),
                TextField(controller: evidenceController, decoration: const InputDecoration(labelText: 'Default evidence limit')),
                TextField(controller: retentionController, decoration: const InputDecoration(labelText: 'Log retention days')),
                const SizedBox(height: 8),
                DropdownButtonFormField<ThemePreference>(
                  key: ValueKey(themePreference),
                  initialValue: themePreference,
                  items: const [
                    DropdownMenuItem(value: ThemePreference.system, child: Text('System')),
                    DropdownMenuItem(value: ThemePreference.light, child: Text('Light')),
                    DropdownMenuItem(value: ThemePreference.dark, child: Text('Dark')),
                  ],
                  onChanged: (value) => setState(() => themePreference = value ?? ThemePreference.system),
                  decoration: const InputDecoration(labelText: 'Theme'),
                ),
                DropdownButtonFormField<ReportFormatPreference>(
                  key: ValueKey(reportPreference),
                  initialValue: reportPreference,
                  items: const [
                    DropdownMenuItem(value: ReportFormatPreference.markdown, child: Text('Markdown')),
                    DropdownMenuItem(value: ReportFormatPreference.json, child: Text('JSON')),
                  ],
                  onChanged: (value) => setState(() => reportPreference = value ?? ReportFormatPreference.markdown),
                  decoration: const InputDecoration(labelText: 'Report viewing preference'),
                ),
                SwitchListTile(
                  value: deterministicOnly,
                  onChanged: (value) => setState(() => deterministicOnly = value),
                  title: const Text('Deterministic-only default'),
                ),
                const SizedBox(height: 8),
                Wrap(
                  spacing: 8,
                  children: [
                    FilledButton(
                      onPressed: () async {
                        final next = widget.controller.settings.copyWith(
                          repositoryRootPath: rootController.text.trim(),
                          backendUrl: backendUrlController.text.trim(),
                          backendLaunchPreference: launchPreference,
                          defaultProjectId: projectController.text.trim(),
                          preferredModelName: modelController.text.trim(),
                          defaultEvidenceLimit: int.tryParse(evidenceController.text) ?? widget.controller.settings.defaultEvidenceLimit,
                          deterministicOnlyDefault: deterministicOnly,
                          reportFormatPreference: reportPreference,
                          themePreference: themePreference,
                          logRetentionDays: int.tryParse(retentionController.text) ?? widget.controller.settings.logRetentionDays,
                        );
                        await widget.controller.updateSettings(next);
                      },
                      child: const Text('Save'),
                    ),
                    OutlinedButton(
                      onPressed: () async {
                        await widget.controller.updateSettings(
                          GaiaAppSettings.defaults().copyWith(firstRunComplete: widget.controller.settings.firstRunComplete),
                        );
                        setState(() {
                          final settings = widget.controller.settings;
                          backendUrlController.text = settings.backendUrl;
                          rootController.text = settings.repositoryRootPath;
                          projectController.text = settings.defaultProjectId;
                          modelController.text = settings.preferredModelName;
                          evidenceController.text = settings.defaultEvidenceLimit.toString();
                          retentionController.text = settings.logRetentionDays.toString();
                          launchPreference = settings.backendLaunchPreference;
                          themePreference = settings.themePreference;
                          reportPreference = settings.reportFormatPreference;
                          deterministicOnly = settings.deterministicOnlyDefault;
                        });
                      },
                      child: const Text('Reset safe defaults'),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class AboutScreen extends StatelessWidget {
  const AboutScreen({super.key, required this.controller});

  final GaiaAppController controller;

  @override
  Widget build(BuildContext context) {
    return _ScreenScaffold(
      title: 'About',
      subtitle: 'Local-first, evidence-backed desktop control centre',
      child: SectionCard(
        title: 'GAIA v0.3.0',
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('GAIA Windows is a read-only client for the existing FastAPI backend.'),
            const SizedBox(height: 12),
            _keyValueGrid([
              ('Backend', controller.settings.backendUrl),
              ('Version', controller.health?.version ?? 'Unknown'),
              ('Read-only', 'Yes'),
              ('Current project', controller.selectedProject?.projectId ?? 'None'),
            ]),
            const SizedBox(height: 12),
            const Text('Future approval-centre functionality is intentionally not implemented in v0.3.'),
          ],
        ),
      ),
    );
  }
}

class FirstRunScreen extends StatefulWidget {
  const FirstRunScreen({super.key, required this.controller});

  final GaiaAppController controller;

  @override
  State<FirstRunScreen> createState() => _FirstRunScreenState();
}

class _FirstRunScreenState extends State<FirstRunScreen> {
  late final TextEditingController rootController;
  late final TextEditingController backendController;
  bool starting = false;

  @override
  void initState() {
    super.initState();
    rootController = TextEditingController(text: widget.controller.settings.repositoryRootPath);
    backendController = TextEditingController(text: widget.controller.settings.backendUrl);
  }

  @override
  void dispose() {
    rootController.dispose();
    backendController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final controller = widget.controller;
    return Scaffold(
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 1100),
          child: ListView(
            padding: const EdgeInsets.all(24),
            children: [
              const SizedBox(height: 24),
              Text('Welcome to GAIA', style: Theme.of(context).textTheme.displaySmall),
              const SizedBox(height: 8),
              const Text('Complete a short local setup before entering the desktop control centre.'),
              const SizedBox(height: 24),
              SectionCard(
                title: 'Setup Stages',
                child: Column(
                  children: [
                    for (final check in controller.firstRunChecks)
                      ListTile(
                        leading: Icon(check.passed ? Icons.check_circle : Icons.radio_button_unchecked, color: check.passed ? Colors.green : Colors.orange),
                        title: Text(check.label),
                        subtitle: Text(check.details),
                      ),
                  ],
                ),
              ),
              const SizedBox(height: 16),
              SectionCard(
                title: 'Locate Installation',
                child: Column(
                  children: [
                    TextField(controller: rootController, decoration: const InputDecoration(labelText: 'GAIA repository root')),
                    TextField(controller: backendController, decoration: const InputDecoration(labelText: 'Backend URL')),
                    const SizedBox(height: 12),
                    Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: [
                        FilledButton(
                          onPressed: starting
                              ? null
                              : () async {
                                  setState(() => starting = true);
                                  try {
                                    await controller.updateSettings(
                                      controller.settings.copyWith(
                                        repositoryRootPath: rootController.text.trim(),
                                        backendUrl: backendController.text.trim(),
                                      ),
                                    );
                                    await controller.connectToBackend();
                                    await controller.completeFirstRun();
                                  } finally {
                                    if (mounted) {
                                      setState(() => starting = false);
                                    }
                                  }
                                },
                          child: const Text('Finish setup'),
                        ),
                        OutlinedButton(
                          onPressed: starting ? null : controller.startLocalBackend,
                          child: const Text('Start local backend'),
                        ),
                        OutlinedButton(
                          onPressed: starting ? null : controller.connectToBackend,
                          child: const Text('Check backend'),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 16),
              if (controller.lastError != null)
                SectionCard(
                  title: 'Last error',
                  child: Text(controller.lastError!),
                ),
            ],
          ),
        ),
      ),
    );
  }
}

class _Destination {
  const _Destination(this.label, this.icon, this.activeIcon);
  final String label;
  final IconData icon;
  final IconData activeIcon;
}

class _ScreenScaffold extends StatelessWidget {
  const _ScreenScaffold({
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

Widget _statusCard(String label, String value, bool ok) {
  return SizedBox(
    width: 260,
    child: Card(
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(label),
            const SizedBox(height: 8),
            Text(value, style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w600)),
            const SizedBox(height: 8),
            Text(ok ? 'Operational' : 'Needs attention'),
          ],
        ),
      ),
    ),
  );
}

Widget _keyValueGrid(List<(String, String)> values) {
  return Wrap(
    spacing: 16,
    runSpacing: 16,
    children: [
      for (final entry in values)
        SizedBox(
          width: 280,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(entry.$1, style: const TextStyle(fontWeight: FontWeight.w700)),
              const SizedBox(height: 4),
              Text(entry.$2),
            ],
          ),
        ),
    ],
  );
}

String _answerSectionText(String text, String heading) {
  final lines = text.split('\n');
  final start = lines.indexWhere((line) => line.trim() == heading);
  if (start < 0) {
    return 'Not provided.';
  }
  final buffer = <String>[];
  for (var index = start + 1; index < lines.length; index++) {
    final line = lines[index];
    if (line.trim().endsWith(':') && !line.trim().startsWith('-')) {
      break;
    }
    if (line.trim().isNotEmpty) {
      buffer.add(line);
    }
  }
  return buffer.isEmpty ? 'Not provided.' : buffer.join('\n');
}

extension _TakeLast<T> on Iterable<T> {
  List<T> takeLast(int count) {
    final list = toList();
    return list.length <= count ? list : list.sublist(list.length - count);
  }
}

const _suggestedQuestions = <String>[
  'Where exactly is MicroGrow currently?',
  'What was completed most recently?',
  'What proves the PlatformIO build passed?',
  'Which features are production-ready?',
  'Which features are experimental?',
  'What is incomplete?',
  'What is planned for future versions?',
  'What documentation is missing?',
  'What are the current blockers?',
  'What should I build next?',
  'Create the next Codex prompt.',
];
