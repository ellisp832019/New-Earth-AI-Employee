import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_markdown/flutter_markdown.dart';

import 'models.dart';

class StatusChip extends StatelessWidget {
  const StatusChip({
    super.key,
    required this.label,
    required this.color,
    this.icon,
  });

  final String label;
  final Color color;
  final IconData? icon;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Chip(
      avatar: icon == null ? null : Icon(icon, size: 16, color: color),
      label: Text(label),
      side: BorderSide(color: color.withValues(alpha: 0.5)),
      backgroundColor: color.withValues(
        alpha: scheme.brightness == Brightness.dark ? 0.15 : 0.08,
      ),
    );
  }
}

class SectionCard extends StatelessWidget {
  const SectionCard({
    super.key,
    required this.title,
    required this.child,
    this.trailing,
    this.subtitle,
  });

  final String title;
  final Widget child;
  final Widget? trailing;
  final String? subtitle;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final body = child is ScrollView
        ? SizedBox(
            height: MediaQuery.sizeOf(context).height * 0.42,
            child: child,
          )
        : child;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
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
                      Text(title, style: theme.textTheme.titleLarge),
                      ...(subtitle == null
                          ? const <Widget>[]
                          : <Widget>[
                              const SizedBox(height: 4),
                              Text(subtitle!, style: theme.textTheme.bodySmall),
                            ]),
                    ],
                  ),
                ),
                if (trailing != null)
                  Flexible(
                    child: Align(
                      alignment: Alignment.topRight,
                      child: trailing!,
                    ),
                  ),
              ],
            ),
            const SizedBox(height: 16),
            body,
          ],
        ),
      ),
    );
  }
}

class ReadOnlyBanner extends StatelessWidget {
  const ReadOnlyBanner({super.key, this.message = 'Read-only mode active'});

  final String message;

  @override
  Widget build(BuildContext context) {
    return MaterialBanner(
      content: Row(
        children: [
          Icon(Icons.lock, color: Theme.of(context).colorScheme.primary),
          const SizedBox(width: 12),
          Expanded(child: Text(message)),
        ],
      ),
      actions: const [SizedBox.shrink()],
      backgroundColor: Theme.of(
        context,
      ).colorScheme.primaryContainer.withValues(alpha: 0.4),
    );
  }
}

class MarkdownView extends StatelessWidget {
  const MarkdownView({super.key, required this.data});

  final String data;

  @override
  Widget build(BuildContext context) {
    return SelectionArea(
      child: MarkdownBody(
        data: data,
        selectable: true,
        onTapLink: (text, href, title) {
          if (href != null) {
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(
                content: Text('External links are disabled by default: $href'),
              ),
            );
          }
        },
      ),
    );
  }
}

class CopyButton extends StatelessWidget {
  const CopyButton({super.key, required this.text, this.label = 'Copy'});

  final String text;
  final String label;

  @override
  Widget build(BuildContext context) {
    return OutlinedButton.icon(
      onPressed: () async {
        await Clipboard.setData(ClipboardData(text: text));
        if (context.mounted) {
          ScaffoldMessenger.of(
            context,
          ).showSnackBar(const SnackBar(content: Text('Copied to clipboard')));
        }
      },
      icon: const Icon(Icons.copy),
      label: Text(label),
    );
  }
}

class EvidenceCard extends StatelessWidget {
  const EvidenceCard({super.key, required this.item, required this.onCopy});

  final EvidenceItem item;
  final void Function(String text) onCopy;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Chip(label: Text(item.sourceKind.toUpperCase())),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    item.title,
                    style: Theme.of(context).textTheme.titleMedium,
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
                IconButton(
                  tooltip: 'Copy evidence',
                  onPressed: () =>
                      onCopy('${item.sourcePath}\n${item.snippet}'),
                  icon: const Icon(Icons.copy),
                ),
              ],
            ),
            const SizedBox(height: 6),
            Text(item.sourcePath, style: Theme.of(context).textTheme.bodySmall),
            const SizedBox(height: 8),
            Text(item.snippet),
            const SizedBox(height: 12),
            Row(
              children: [
                _Meta(label: 'Score', value: item.score.toStringAsFixed(2)),
                const SizedBox(width: 12),
                _Meta(label: 'ID', value: item.evidenceId),
                const SizedBox(width: 12),
                if (item.warning != null)
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 10,
                      vertical: 6,
                    ),
                    decoration: BoxDecoration(
                      color: scheme.errorContainer.withValues(alpha: 0.5),
                      borderRadius: BorderRadius.circular(999),
                    ),
                    child: Text(
                      item.warning!,
                      style: TextStyle(color: scheme.onErrorContainer),
                    ),
                  ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _Meta extends StatelessWidget {
  const _Meta({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Text('$label: $value', style: Theme.of(context).textTheme.bodySmall);
  }
}
