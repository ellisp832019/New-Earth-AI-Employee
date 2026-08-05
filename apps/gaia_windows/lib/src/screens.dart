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
    _Destination('Tasks', Icons.task_alt_outlined, Icons.task_alt),
    _Destination('Drafts', Icons.note_alt_outlined, Icons.note_alt),
    _Destination('Approvals', Icons.verified_outlined, Icons.verified),
    _Destination('Permissions', Icons.shield_outlined, Icons.shield),
    _Destination('Action Centre', Icons.play_circle_outline, Icons.play_circle),
    _Destination('Receipts', Icons.receipt_long_outlined, Icons.receipt_long),
    _Destination('Daily Brief', Icons.event_note_outlined, Icons.event_note),
    _Destination('VS Code Ops', Icons.code_outlined, Icons.code),
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
        TasksScreen(controller: controller),
        DraftsScreen(controller: controller),
        ApprovalsScreen(controller: controller),
        PermissionsScreen(controller: controller),
        ActionsScreen(controller: controller),
        ReceiptsScreen(controller: controller),
        DailyBriefScreen(controller: controller),
        VscodeOpsScreen(controller: controller),
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
        const StatusChip(
          label: 'GAIA-owned output only',
          color: Colors.deepOrange,
          icon: Icons.folder_special,
        ),
        const StatusChip(
          label: 'MicroGrow read-only',
          color: Colors.teal,
          icon: Icons.visibility,
        ),
        const StatusChip(
          label: 'No auto Git',
          color: Colors.indigo,
          icon: Icons.do_not_disturb,
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
        'Backend version ${controller.health?.version ?? 'unknown'} is incompatible with the v0.5 desktop client.',
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

class TasksScreen extends StatefulWidget {
  const TasksScreen({super.key, required this.controller});

  final GaiaAppController controller;

  @override
  State<TasksScreen> createState() => _TasksScreenState();
}

class _TasksScreenState extends State<TasksScreen> {
  String statusFilter = 'all';
  String priorityFilter = 'all';

  @override
  Widget build(BuildContext context) {
    final controller = widget.controller;
    final tasks = controller.tasks.where((task) {
      final statusOk = statusFilter == 'all' || task.status == statusFilter;
      final priorityOk = priorityFilter == 'all' || task.priority == priorityFilter;
      return statusOk && priorityOk;
    }).toList();
    final selectedTask = controller.selectedTask ?? (tasks.isNotEmpty ? tasks.first : null);
    if (selectedTask != null) {
      controller.selectTask(selectedTask.taskId);
    }
    return _ScreenScaffold(
      title: 'Task Centre',
      subtitle: 'Proposals, backlog items and local task transitions',
      child: Column(
        children: [
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: [
              _filterBox(
                label: 'Status',
                value: statusFilter,
                values: const ['all', 'proposed', 'backlog', 'ready', 'in_progress', 'blocked', 'awaiting_approval', 'completed', 'cancelled'],
                onChanged: (value) => setState(() => statusFilter = value ?? 'all'),
              ),
              _filterBox(
                label: 'Priority',
                value: priorityFilter,
                values: const ['all', 'low', 'normal', 'high', 'critical'],
                onChanged: (value) => setState(() => priorityFilter = value ?? 'all'),
              ),
              FilledButton(
                onPressed: () => _createTask(context),
                child: const Text('Create task'),
              ),
              OutlinedButton(
                onPressed: controller.selectedTask == null
                    ? null
                    : () async {
                        await controller.createTaskFromRun(controller.selectedTask!.sourceAgentRunId ?? controller.agentRuns.first.runId);
                        if (mounted) {
                          setState(() {});
                        }
                      },
                child: const Text('Create from run'),
              ),
            ],
          ),
          const SizedBox(height: 16),
          Expanded(
            child: Row(
              children: [
                Expanded(
                  flex: 2,
                  child: SectionCard(
                    title: 'Tasks',
                    child: ListView(
                      children: [
                        for (final task in tasks)
                          Card(
                            child: ListTile(
                              selected: task.taskId == controller.selectedTaskId,
                              onTap: () => controller.selectTask(task.taskId),
                              title: Text(task.title),
                              subtitle: Text('${task.projectId} • ${task.status} • ${task.priority}'),
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
                    title: 'Task Detail',
                    subtitle: selectedTask?.taskId ?? 'No task selected',
                    child: selectedTask == null ? const Text('Select a task to inspect it.') : _TaskDetail(controller: controller, task: selectedTask),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _createTask(BuildContext context) async {
    final titleController = TextEditingController();
    final descriptionController = TextEditingController();
    final criteriaController = TextEditingController();
    String projectId = widget.controller.selectedProjectId ?? widget.controller.projects.first.projectId;
    await showDialog<void>(
      context: context,
      builder: (dialogContext) {
        return AlertDialog(
          title: const Text('Create task'),
          content: StatefulBuilder(
            builder: (context, setState) {
              return SizedBox(
                width: 520,
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    DropdownButtonFormField<String>(
                      initialValue: projectId,
                      items: [
                        for (final project in widget.controller.projects)
                          DropdownMenuItem(value: project.projectId, child: Text(project.name)),
                      ],
                      onChanged: (value) => setState(() => projectId = value ?? projectId),
                      decoration: const InputDecoration(labelText: 'Project'),
                    ),
                    TextField(controller: titleController, decoration: const InputDecoration(labelText: 'Title')),
                    TextField(controller: descriptionController, decoration: const InputDecoration(labelText: 'Description')),
                    TextField(controller: criteriaController, decoration: const InputDecoration(labelText: 'Completion criteria')),
                  ],
                ),
              );
            },
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(dialogContext), child: const Text('Cancel')),
            FilledButton(
              onPressed: () async {
                await widget.controller.createTask(
                  title: titleController.text.trim(),
                  projectId: projectId,
                  description: descriptionController.text.trim(),
                  completionCriteria: criteriaController.text.trim(),
                );
                if (dialogContext.mounted) {
                  Navigator.pop(dialogContext);
                }
                if (mounted) {
                  setState(() {});
                }
              },
              child: const Text('Create'),
            ),
          ],
        );
      },
    );
  }
}

class _TaskDetail extends StatelessWidget {
  const _TaskDetail({required this.controller, required this.task});

  final GaiaAppController controller;
  final TaskRecord task;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _keyValueGrid([
          ('Task ID', task.taskId),
          ('Project', task.projectId),
          ('Status', task.status),
          ('Priority', task.priority),
          ('Category', task.category),
          ('Source', task.sourceType),
          ('Version', task.version.toString()),
        ]),
        const SizedBox(height: 12),
        Text(task.description.isEmpty ? 'No description.' : task.description),
        const SizedBox(height: 12),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: [
            FilledButton(onPressed: () => controller.acceptTask(task.taskId), child: const Text('Accept')),
            OutlinedButton(onPressed: () => controller.transitionTask(task.taskId, 'ready'), child: const Text('Ready')),
            OutlinedButton(onPressed: () => controller.transitionTask(task.taskId, 'in_progress'), child: const Text('In Progress')),
            OutlinedButton(onPressed: () => controller.transitionTask(task.taskId, 'blocked', reason: 'blocked'), child: const Text('Blocked')),
            OutlinedButton(onPressed: () => controller.transitionTask(task.taskId, 'awaiting_approval', reason: 'ready for review'), child: const Text('Awaiting approval')),
            OutlinedButton(onPressed: () => controller.transitionTask(task.taskId, 'completed', completionEvidence: const ['manual verification'], manualOverrideReason: 'manual completion'), child: const Text('Complete')),
            OutlinedButton(onPressed: () => controller.acceptTask(task.taskId), child: const Text('Backlog')),
          ],
        ),
        const SizedBox(height: 12),
        Text('Evidence: ${task.evidenceReferences.join(', ')}'),
        Text('Dependencies: ${task.dependencyTaskIds.join(', ')}'),
        Text('Tags: ${task.tags.join(', ')}'),
      ],
    );
  }
}

class DraftsScreen extends StatefulWidget {
  const DraftsScreen({super.key, required this.controller});

  final GaiaAppController controller;

  @override
  State<DraftsScreen> createState() => _DraftsScreenState();
}

class _DraftsScreenState extends State<DraftsScreen> {
  @override
  Widget build(BuildContext context) {
    final controller = widget.controller;
    final selectedDraft = controller.selectedDraft ?? (controller.drafts.isNotEmpty ? controller.drafts.first : null);
    if (selectedDraft != null) {
      controller.selectDraft(selectedDraft.draftId);
    }
    return _ScreenScaffold(
      title: 'Draft Centre',
      subtitle: 'Local draft records and revisions',
      child: Row(
        children: [
          Expanded(
            flex: 2,
            child: SectionCard(
              title: 'Drafts',
              trailing: FilledButton(
                onPressed: () => _createDraft(context),
                child: const Text('Create draft'),
              ),
              child: ListView(
                children: [
                  for (final draft in controller.drafts)
                    Card(
                      child: ListTile(
                        selected: draft.draftId == controller.selectedDraftId,
                        onTap: () => controller.selectDraft(draft.draftId),
                        title: Text(draft.title),
                        subtitle: Text('${draft.projectId} • ${draft.draftType} • ${draft.status}'),
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
              title: 'Draft Detail',
              subtitle: selectedDraft?.draftId ?? 'No draft selected',
              child: selectedDraft == null ? const Text('Select a draft to review it.') : _DraftDetail(controller: controller, draft: selectedDraft),
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _createDraft(BuildContext context) async {
    final titleController = TextEditingController();
    final contentController = TextEditingController();
    final taskController = TextEditingController();
    String projectId = widget.controller.selectedProjectId ?? widget.controller.projects.first.projectId;
    await showDialog<void>(
      context: context,
      builder: (dialogContext) {
        return AlertDialog(
          title: const Text('Create draft'),
          content: SizedBox(
            width: 520,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                DropdownButtonFormField<String>(
                  initialValue: projectId,
                  items: [
                    for (final project in widget.controller.projects)
                      DropdownMenuItem(value: project.projectId, child: Text(project.name)),
                  ],
                  onChanged: (value) => projectId = value ?? projectId,
                  decoration: const InputDecoration(labelText: 'Project'),
                ),
                TextField(controller: titleController, decoration: const InputDecoration(labelText: 'Title')),
                TextField(controller: taskController, decoration: const InputDecoration(labelText: 'Source task ID')),
                TextField(controller: contentController, maxLines: 4, decoration: const InputDecoration(labelText: 'Content')),
              ],
            ),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(dialogContext), child: const Text('Cancel')),
            FilledButton(
              onPressed: () async {
                await widget.controller.createDraft(
                  title: titleController.text.trim(),
                  projectId: projectId,
                  content: contentController.text,
                  sourceTaskId: taskController.text.trim().isEmpty ? null : taskController.text.trim(),
                  draftType: 'codex_prompt',
                );
                if (dialogContext.mounted) {
                  Navigator.pop(dialogContext);
                }
                if (mounted) {
                  setState(() {});
                }
              },
              child: const Text('Create'),
            ),
          ],
        );
      },
    );
  }
}

class _DraftDetail extends StatelessWidget {
  const _DraftDetail({required this.controller, required this.draft});

  final GaiaAppController controller;
  final DraftRecord draft;

  @override
  Widget build(BuildContext context) {
    final revisions = controller.drafts.where((entry) => entry.draftId == draft.draftId).toList();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _keyValueGrid([
          ('Draft ID', draft.draftId),
          ('Project', draft.projectId),
          ('Type', draft.draftType),
          ('Status', draft.status),
          ('Revision', draft.currentRevision.toString()),
          ('Hash', draft.currentContentHash),
        ]),
        const SizedBox(height: 12),
        Row(
          children: [
            CopyButton(text: draft.currentContentHash, label: 'Copy hash'),
            const SizedBox(width: 8),
            FilledButton(onPressed: () => controller.submitDraft(draft.draftId), child: const Text('Submit for review')),
            const SizedBox(width: 8),
            OutlinedButton(onPressed: () => controller.reviseDraft(draft.draftId, 'Revision based on local review.'), child: const Text('Revise')),
          ],
        ),
        const SizedBox(height: 12),
        MarkdownView(data: '### Current Draft\n\n```markdown\n${draft.currentContentHash}\n```'),
        const SizedBox(height: 12),
        Text('Evidence: ${draft.evidenceReferences.join(', ')}'),
        Text('Warnings: ${draft.warnings.join(', ')}'),
        Text('Revisions available in backend: ${revisions.length}'),
      ],
    );
  }
}

class ApprovalsScreen extends StatefulWidget {
  const ApprovalsScreen({super.key, required this.controller});

  final GaiaAppController controller;

  @override
  State<ApprovalsScreen> createState() => _ApprovalsScreenState();
}

class _ApprovalsScreenState extends State<ApprovalsScreen> {
  @override
  Widget build(BuildContext context) {
    final controller = widget.controller;
    final selectedApproval = controller.selectedApproval ?? (controller.approvals.isNotEmpty ? controller.approvals.first : null);
    if (selectedApproval != null) {
      controller.selectApproval(selectedApproval.approvalId);
    }
    return _ScreenScaffold(
      title: 'Approval Centre',
      subtitle: 'Manual-use decisions and risk review',
      child: Row(
        children: [
          Expanded(
            flex: 2,
            child: SectionCard(
              title: 'Approvals',
              trailing: FilledButton(onPressed: () => _createApproval(context), child: const Text('Create approval')),
              child: ListView(
                children: [
                  for (final approval in controller.approvals)
                    Card(
                      child: ListTile(
                        selected: approval.approvalId == controller.selectedApprovalId,
                        onTap: () => controller.selectApproval(approval.approvalId),
                        title: Text(approval.title),
                        subtitle: Text('${approval.projectId} • ${approval.riskLevel} • ${approval.status}'),
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
              title: 'Approval Detail',
              subtitle: selectedApproval?.approvalId ?? 'No approval selected',
              child: selectedApproval == null ? const Text('Select an approval to review it.') : _ApprovalDetail(controller: controller, approval: selectedApproval),
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _createApproval(BuildContext context) async {
    final titleController = TextEditingController();
    final summaryController = TextEditingController();
    final draftController = TextEditingController();
    final taskController = TextEditingController();
    String projectId = widget.controller.selectedProjectId ?? widget.controller.projects.first.projectId;
    await showDialog<void>(
      context: context,
      builder: (dialogContext) {
        return AlertDialog(
          title: const Text('Create approval'),
          content: SizedBox(
            width: 520,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                DropdownButtonFormField<String>(
                  initialValue: projectId,
                  items: [for (final project in widget.controller.projects) DropdownMenuItem(value: project.projectId, child: Text(project.name))],
                  onChanged: (value) => projectId = value ?? projectId,
                  decoration: const InputDecoration(labelText: 'Project'),
                ),
                TextField(controller: titleController, decoration: const InputDecoration(labelText: 'Title')),
                TextField(controller: draftController, decoration: const InputDecoration(labelText: 'Source draft ID')),
                TextField(controller: taskController, decoration: const InputDecoration(labelText: 'Source task ID')),
                TextField(controller: summaryController, decoration: const InputDecoration(labelText: 'Preview summary')),
              ],
            ),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(dialogContext), child: const Text('Cancel')),
            FilledButton(
              onPressed: () async {
                await widget.controller.createApproval(
                  title: titleController.text.trim(),
                  projectId: projectId,
                  sourceDraftId: draftController.text.trim().isEmpty ? null : draftController.text.trim(),
                  sourceTaskId: taskController.text.trim().isEmpty ? null : taskController.text.trim(),
                  previewSummary: summaryController.text.trim(),
                  proposedAction: 'Manual use review',
                  exactTargetDescription: 'GAIA draft and task review',
                  riskLevel: 'medium',
                );
                if (dialogContext.mounted) {
                  Navigator.pop(dialogContext);
                }
                if (mounted) {
                  setState(() {});
                }
              },
              child: const Text('Create'),
            ),
          ],
        );
      },
    );
  }
}

class _ApprovalDetail extends StatelessWidget {
  const _ApprovalDetail({required this.controller, required this.approval});

  final GaiaAppController controller;
  final ApprovalRecord approval;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _keyValueGrid([
          ('Approval ID', approval.approvalId),
          ('Project', approval.projectId),
          ('Risk', approval.riskLevel),
          ('Status', approval.status),
          ('Preview', approval.previewSummary),
          ('Hash', approval.approvedContentHash),
        ]),
        const SizedBox(height: 12),
        Text(approval.description),
        const SizedBox(height: 12),
        Wrap(
          spacing: 8,
          children: [
            FilledButton(
              onPressed: () => controller.approveRequest(approval.approvalId, version: approval.version, reviewer: 'manual', decisionReason: 'Approved for manual use'),
              child: const Text('Approve'),
            ),
            OutlinedButton(
              onPressed: () => controller.rejectRequest(approval.approvalId, version: approval.version, reviewer: 'manual', decisionReason: 'Rejected'),
              child: const Text('Reject'),
            ),
            OutlinedButton(
              onPressed: () => controller.refreshApprovalValidation(approval.approvalId),
              child: const Text('Refresh validation'),
            ),
          ],
        ),
        const SizedBox(height: 12),
        Text('Write boundary: ${approval.writeBoundary}'),
        Text('Requesting source: ${approval.requestingSource}'),
        Text('Decision: ${approval.decisionReason ?? 'pending'}'),
      ],
    );
  }
}

class DailyBriefScreen extends StatelessWidget {
  const DailyBriefScreen({super.key, required this.controller});

  final GaiaAppController controller;

  @override
  Widget build(BuildContext context) {
    final brief = controller.selectedBrief ?? (controller.briefs.isNotEmpty ? controller.briefs.first : null);
    if (brief != null) {
      controller.selectBrief(brief.briefId);
    }
    return _ScreenScaffold(
      title: 'Daily Operations Brief',
      subtitle: 'Deterministic summary of tasks, approvals and repo state',
      child: Column(
        children: [
          Align(
            alignment: Alignment.centerLeft,
            child: FilledButton(
              onPressed: controller.selectedProjectId == null ? null : () => controller.createDailyBrief(controller.selectedProjectId!),
              child: const Text('Generate brief'),
            ),
          ),
          const SizedBox(height: 16),
          Expanded(
            child: Row(
              children: [
                Expanded(
                  flex: 2,
                  child: SectionCard(
                    title: 'Briefs',
                    child: ListView(
                      children: [
                        for (final item in controller.briefs)
                          ListTile(
                            selected: item.briefId == controller.selectedBriefId,
                            onTap: () => controller.selectBrief(item.briefId),
                            title: Text(item.title),
                            subtitle: Text(item.projectId),
                          ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(width: 16),
                Expanded(
                  flex: 3,
                  child: SectionCard(
                    title: 'Brief detail',
                    subtitle: brief?.briefId ?? 'No brief selected',
                    child: brief == null ? const Text('Generate a brief to review it here.') : MarkdownView(data: brief.markdown),
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

class VscodeOpsScreen extends StatelessWidget {
  const VscodeOpsScreen({super.key, required this.controller});

  final GaiaAppController controller;

  @override
  Widget build(BuildContext context) {
    return _ScreenScaffold(
      title: 'VS Code Operations',
      subtitle: 'Workspace tasks and validation shortcuts',
      child: ListView(
        children: [
          SectionCard(
            title: 'Live tasks',
            child: const Text(
              'Use the GAIA workspace to run list/create/approve workflow commands, validation scripts and backend health checks from the repo root.',
            ),
          ),
          const SizedBox(height: 16),
          SectionCard(
            title: 'Recommended checks',
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                for (final line in const [
                  'GAIA: List Tasks',
                  'GAIA: List Drafts',
                  'GAIA: List Pending Approvals',
                  'GAIA: Generate Daily Brief',
                  'GAIA: Full Repository Validation',
                  'GAIA: Complete v0.4 Validation',
                  'GAIA: Release Readiness',
                ])
                  ListTile(leading: const Icon(Icons.checklist), title: Text(line)),
              ],
            ),
          ),
        ],
      ),
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
        title: 'GAIA v0.5.0',
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('GAIA Windows is the desktop control centre for the permissioned GAIA backend.'),
            const SizedBox(height: 12),
            _keyValueGrid([
              ('Backend', controller.settings.backendUrl),
              ('Version', controller.health?.version ?? 'Unknown'),
              ('Read-only', 'Yes'),
              ('Current project', controller.selectedProject?.projectId ?? 'None'),
            ]),
            const SizedBox(height: 12),
            const Text('Approval, task, draft and output-execution workflows are tracked locally and require explicit confirmation.'),
          ],
        ),
      ),
    );
  }
}

class PermissionsScreen extends StatefulWidget {
  const PermissionsScreen({super.key, required this.controller});

  final GaiaAppController controller;

  @override
  State<PermissionsScreen> createState() => _PermissionsScreenState();
}

class _PermissionsScreenState extends State<PermissionsScreen> {
  @override
  Widget build(BuildContext context) {
    final controller = widget.controller;
    final selected = controller.permissionManifests.isNotEmpty
        ? controller.permissionManifests.firstWhere(
            (entry) => entry['manifest_id'] == controller.selectedManifestId,
            orElse: () => controller.permissionManifests.first,
          )
        : null;
    if (selected != null) {
      controller.selectManifest(selected['manifest_id'] as String?);
    }
    return _ScreenScaffold(
      title: 'Permissions',
      subtitle: 'Permission manifests and allowlisted GAIA-owned output roots',
      child: Row(
        children: [
          Expanded(
            flex: 2,
            child: SectionCard(
              title: 'Manifests',
              trailing: FilledButton(
                onPressed: () => _createManifest(context),
                child: const Text('Create manifest'),
              ),
              child: ListView(
                children: [
                  for (final manifest in controller.permissionManifests)
                    Card(
                      child: ListTile(
                        selected: manifest['manifest_id'] == controller.selectedManifestId,
                        onTap: () => controller.selectManifest(manifest['manifest_id'] as String?),
                        title: Text(manifest['name']?.toString() ?? 'Unnamed manifest'),
                        subtitle: Text(
                          '${manifest['manifest_id']} • ${manifest['enabled'] == true ? 'enabled' : 'disabled'} • ${manifest['overwrite_policy'] ?? 'deny'}',
                        ),
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
              title: 'Manifest Detail',
              subtitle: selected?['manifest_id']?.toString() ?? 'No manifest selected',
              child: selected == null
                  ? const Text('Create or select a manifest to inspect it.')
                  : Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        _keyValueGrid([
                          ('Manifest ID', selected['manifest_id']?.toString() ?? ''),
                          ('Version', selected['manifest_version']?.toString() ?? ''),
                          ('Enabled', selected['enabled'] == true ? 'Yes' : 'No'),
                          ('Risk ceiling', selected['risk_ceiling']?.toString() ?? ''),
                          ('Overwrite policy', selected['overwrite_policy']?.toString() ?? ''),
                        ]),
                        const SizedBox(height: 12),
                        Text('Allowed roots: ${(selected['allowed_target_roots'] as List?)?.join(', ') ?? ''}'),
                        Text('Allowed actions: ${(selected['allowed_action_types'] as List?)?.join(', ') ?? ''}'),
                        Text('Allowed extensions: ${(selected['allowed_file_extensions'] as List?)?.join(', ') ?? ''}'),
                        const SizedBox(height: 12),
                        Wrap(
                          spacing: 8,
                          children: [
                            FilledButton(
                              onPressed: () async {
                                final result = await controller.validatePermissionManifest(selected['manifest_id'] as String);
                                if (context.mounted) {
                                  ScaffoldMessenger.of(context).showSnackBar(
                                    SnackBar(content: Text(result['valid'] == true ? 'Manifest valid' : 'Manifest has issues')),
                                  );
                                }
                              },
                              child: const Text('Validate'),
                            ),
                            OutlinedButton(
                              onPressed: () => controller.reviewPermissionManifest(
                                selected['manifest_id'] as String,
                                version: selected['manifest_version'] as int? ?? 1,
                                enabled: !(selected['enabled'] as bool? ?? false),
                                reviewNotes: 'Manual review from Control Centre',
                              ),
                              child: Text(selected['enabled'] == true ? 'Disable' : 'Enable'),
                            ),
                          ],
                        ),
                      ],
                    ),
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _createManifest(BuildContext context) async {
    final nameController = TextEditingController(text: 'Approved outputs');
    final rootController = TextEditingController(text: 'workspace/approved_outputs');
    await showDialog<void>(
      context: context,
      builder: (dialogContext) {
        return AlertDialog(
          title: const Text('Create permission manifest'),
          content: SizedBox(
            width: 480,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                TextField(controller: nameController, decoration: const InputDecoration(labelText: 'Name')),
                TextField(controller: rootController, decoration: const InputDecoration(labelText: 'Allowed root')),
              ],
            ),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(dialogContext), child: const Text('Cancel')),
            FilledButton(
              onPressed: () async {
                await widget.controller.createPermissionManifest(
                  name: nameController.text.trim(),
                  allowedActionTypes: const <String>['create_output_file', 'update_output_file', 'rollback_output_file'],
                  allowedTargetRoots: <String>[rootController.text.trim()],
                  allowedFileExtensions: const <String>['.md', '.txt'],
                  enabled: false,
                );
                if (dialogContext.mounted) {
                  Navigator.pop(dialogContext);
                }
              },
              child: const Text('Create'),
            ),
          ],
        );
      },
    );
  }
}

class ActionsScreen extends StatefulWidget {
  const ActionsScreen({super.key, required this.controller});

  final GaiaAppController controller;

  @override
  State<ActionsScreen> createState() => _ActionsScreenState();
}

class _ActionsScreenState extends State<ActionsScreen> {
  @override
  Widget build(BuildContext context) {
    final controller = widget.controller;
    final selected = controller.outputActions.isNotEmpty
        ? controller.outputActions.firstWhere(
            (entry) => entry['action_id'] == controller.selectedActionId,
            orElse: () => controller.outputActions.first,
          )
        : null;
    if (selected != null) {
      controller.selectAction(selected['action_id'] as String?);
    }
    final selectedDetail = controller.selectedActionDetail ?? selected;
    return _ScreenScaffold(
      title: 'Action Centre',
      subtitle: 'Proposed actions, exact targets, hashes, approvals and receipts',
      child: Row(
        children: [
          Expanded(
            flex: 2,
            child: SectionCard(
              title: 'Actions',
              trailing: FilledButton(
                onPressed: () => _createAction(context),
                child: const Text('Create action'),
              ),
              child: ListView(
                children: [
                  for (final action in controller.outputActions)
                    Card(
                      child: ListTile(
                        selected: action['action_id'] == controller.selectedActionId,
                        onTap: () => controller.selectAction(action['action_id'] as String?),
                        title: Text(action['title']?.toString() ?? 'Untitled action'),
                        subtitle: Text(
                          '${action['action_type'] ?? ''} • ${action['status'] ?? ''} • ${action['risk'] ?? ''}',
                        ),
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
              title: 'Action Detail',
              subtitle: selectedDetail?['action_id']?.toString() ?? 'No action selected',
              child: selectedDetail == null
                  ? const Text('Create or select an action to review it.')
                  : ListView(
                      children: [
                        _keyValueGrid([
                          ('Action ID', selectedDetail['action_id']?.toString() ?? ''),
                          ('Type', selectedDetail['action_type']?.toString() ?? ''),
                          ('Status', selectedDetail['status']?.toString() ?? ''),
                          ('Risk', selectedDetail['risk']?.toString() ?? ''),
                          ('Manifest', selectedDetail['manifest_id']?.toString() ?? ''),
                          ('Target', selectedDetail['canonical_target']?.toString() ?? ''),
                          ('Proposed hash', selectedDetail['proposed_content_hash']?.toString() ?? ''),
                          ('Previous hash', selectedDetail['previous_content_hash']?.toString() ?? 'None'),
                          ('Receipt', selectedDetail['execution_receipt_id']?.toString() ?? 'None'),
                        ]),
                        const SizedBox(height: 12),
                        Text('Preview'),
                        SelectableText(selectedDetail['preview']?.toString() ?? ''),
                        const SizedBox(height: 12),
                        Text('Diff'),
                        SelectableText(selectedDetail['diff']?.toString() ?? ''),
                        const SizedBox(height: 12),
                        Wrap(
                          spacing: 8,
                          runSpacing: 8,
                          children: [
                            FilledButton(
                              onPressed: () => controller.requestActionApproval(selectedDetail['action_id'] as String),
                              child: const Text('Request approval'),
                            ),
                            OutlinedButton(
                              onPressed: () => controller.approveAction(selectedDetail['action_id'] as String),
                              child: const Text('Approve'),
                            ),
                            OutlinedButton(
                              onPressed: () => controller.executeAction(selectedDetail['action_id'] as String, confirm: true, operator: 'manual'),
                              child: const Text('Execute'),
                            ),
                            OutlinedButton(
                              onPressed: () => controller.rollbackAction(selectedDetail['action_id'] as String, confirm: true, operator: 'manual'),
                              child: const Text('Rollback'),
                            ),
                            OutlinedButton(
                              onPressed: () => controller.cancelAction(selectedDetail['action_id'] as String),
                              child: const Text('Cancel'),
                            ),
                          ],
                        ),
                        const SizedBox(height: 12),
                        Text('Approval binding: ${selectedDetail['approval_binding_hash'] ?? 'None'}'),
                        Text('Approval status: ${selectedDetail['approval_status'] ?? 'None'}'),
                        Text('Backup path: ${selectedDetail['backup_path'] ?? 'None'}'),
                        Text('Selected previews: ${controller.selectedActionPreviews.length}'),
                        for (final preview in controller.selectedActionPreviews)
                          Padding(
                            padding: const EdgeInsets.only(top: 12),
                            child: Card(
                              child: Padding(
                                padding: const EdgeInsets.all(12),
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(preview['target_path']?.toString() ?? ''),
                                    const SizedBox(height: 8),
                                    SelectableText(preview['preview']?.toString() ?? ''),
                                  ],
                                ),
                              ),
                            ),
                          ),
                      ],
                    ),
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _createAction(BuildContext context) async {
    final titleController = TextEditingController(text: 'Export approved output');
    final contentController = TextEditingController(text: 'Hello from GAIA v0.5');
    final targetController = TextEditingController(text: 'workspace/approved_outputs/demo.md');
    String manifestId = widget.controller.selectedManifestId ?? (widget.controller.permissionManifests.isNotEmpty ? widget.controller.permissionManifests.first['manifest_id'] as String : '');
    await showDialog<void>(
      context: context,
      builder: (dialogContext) {
        return AlertDialog(
          title: const Text('Create action'),
          content: SizedBox(
            width: 520,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                DropdownButtonFormField<String>(
                  initialValue: manifestId.isEmpty ? null : manifestId,
                  items: [
                    for (final manifest in widget.controller.permissionManifests)
                      DropdownMenuItem(value: manifest['manifest_id'] as String?, child: Text(manifest['name']?.toString() ?? 'Manifest')),
                  ],
                  onChanged: (value) => manifestId = value ?? manifestId,
                  decoration: const InputDecoration(labelText: 'Manifest'),
                ),
                TextField(controller: titleController, decoration: const InputDecoration(labelText: 'Title')),
                TextField(controller: targetController, decoration: const InputDecoration(labelText: 'Target path')),
                TextField(controller: contentController, maxLines: 4, decoration: const InputDecoration(labelText: 'Content')),
              ],
            ),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(dialogContext), child: const Text('Cancel')),
            FilledButton(
              onPressed: () async {
                await widget.controller.createOutputAction(
                  title: titleController.text.trim(),
                  projectId: widget.controller.selectedProjectId ?? 'sample',
                  manifestId: manifestId,
                  targetPath: targetController.text.trim(),
                  actionType: 'create_output_file',
                  content: contentController.text,
                );
                if (dialogContext.mounted) {
                  Navigator.pop(dialogContext);
                }
              },
              child: const Text('Create'),
            ),
          ],
        );
      },
    );
  }
}

class ReceiptsScreen extends StatelessWidget {
  const ReceiptsScreen({super.key, required this.controller});

  final GaiaAppController controller;

  @override
  Widget build(BuildContext context) {
    final selected = controller.executionReceipts.isNotEmpty
        ? controller.executionReceipts.firstWhere(
            (entry) => entry['receipt_id'] == controller.selectedReceiptId,
            orElse: () => controller.executionReceipts.first,
          )
        : null;
    if (selected != null) {
      controller.selectReceipt(selected['receipt_id'] as String?);
    }
    return _ScreenScaffold(
      title: 'Receipts',
      subtitle: 'Execution receipts and rollback records',
      child: Row(
        children: [
          Expanded(
            flex: 2,
            child: SectionCard(
              title: 'Receipts',
              child: ListView(
                children: [
                  for (final receipt in controller.executionReceipts)
                    Card(
                      child: ListTile(
                        selected: receipt['receipt_id'] == controller.selectedReceiptId,
                        onTap: () => controller.selectReceipt(receipt['receipt_id'] as String?),
                        title: Text(receipt['receipt_id']?.toString() ?? 'Receipt'),
                        subtitle: Text('${receipt['action_id'] ?? ''} • ${receipt['result'] ?? ''}'),
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
              title: 'Receipt Detail',
              subtitle: selected?['receipt_id']?.toString() ?? 'No receipt selected',
              child: selected == null
                  ? const Text('Select a receipt to inspect it.')
                  : _keyValueGrid([
                      ('Receipt ID', selected['receipt_id']?.toString() ?? ''),
                      ('Action ID', selected['action_id']?.toString() ?? ''),
                      ('Manifest', selected['manifest_id']?.toString() ?? ''),
                      ('Target', selected['target_path']?.toString() ?? ''),
                      ('Previous hash', selected['previous_hash']?.toString() ?? 'None'),
                      ('Resulting hash', selected['resulting_hash']?.toString() ?? ''),
                      ('Backup path', selected['backup_path']?.toString() ?? 'None'),
                      ('Rollback available', selected['rollback_available'] == true ? 'Yes' : 'No'),
                    ]),
            ),
          ),
        ],
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

Widget _filterBox({
  required String label,
  required String value,
  required List<String> values,
  required ValueChanged<String?> onChanged,
}) {
  return SizedBox(
    width: 220,
    child: DropdownButtonFormField<String>(
      initialValue: value,
      items: [
        for (final entry in values) DropdownMenuItem(value: entry, child: Text(entry)),
      ],
      onChanged: onChanged,
      decoration: InputDecoration(labelText: label),
    ),
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
