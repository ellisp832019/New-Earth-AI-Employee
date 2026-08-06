import 'package:flutter/material.dart';

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
        final color = controller.connectionState == GaiaDashboardConnectionState.connected
            ? Colors.green
            : controller.connectionState == GaiaDashboardConnectionState.degraded
                ? Colors.orange
                : controller.connectionState == GaiaDashboardConnectionState.incompatible
                    ? Colors.red
                    : Colors.blueGrey;
        return FocusTraversalGroup(
          child: ListView(
            padding: const EdgeInsets.all(24),
            children: [
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  GaiaStatusPill(
                    label: controller.connectionState.name,
                    color: color,
                    icon: Icons.link,
                  ),
                  if (compatibility != null)
                    GaiaStatusPill(
                      label: compatibility.status,
                      color: color,
                      icon: Icons.verified_outlined,
                    ),
                  if ((compatibility?.degradedFeatures.isNotEmpty ?? false))
                    const GaiaStatusPill(label: 'Degraded features', color: Colors.orange, icon: Icons.warning_amber),
                  if (controller.latestReceipt?.chainId != null)
                    const GaiaStatusPill(label: 'Receipt chains', color: Colors.teal, icon: Icons.receipt_long),
                ],
              ),
              const SizedBox(height: 16),
              if (controller.errorMessage != null)
                GaiaSectionCard(
                  title: 'Backend Unavailable',
                  subtitle: 'The dashboard failed closed and kept the host responsive.',
                  child: Text(controller.errorMessage!),
                ),
              const SizedBox(height: 16),
              LayoutBuilder(
                builder: (context, constraints) {
                  final cardWidth = constraints.maxWidth > 1100
                      ? (constraints.maxWidth - 32) / 3
                      : constraints.maxWidth > 750
                          ? (constraints.maxWidth - 16) / 2
                          : constraints.maxWidth;
                  return Wrap(
                    spacing: 16,
                    runSpacing: 16,
                    children: [
                      SizedBox(
                        width: cardWidth,
                        child: GaiaSectionCard(
                          title: 'Compatibility',
                          subtitle: compatibility == null ? 'Unavailable' : compatibility.integrationContractVersion,
                          child: GaiaKeyValueGrid(
                            rows: [
                              ('Backend', compatibility?.backendVersion ?? 'unknown'),
                              ('Client', compatibility?.clientPackageVersion ?? 'unknown'),
                              ('Contract', compatibility?.integrationContractVersion ?? 'unknown'),
                              ('Minimum API', compatibility?.minimumSupportedApiVersion ?? 'unknown'),
                              ('Maximum API', compatibility?.maximumTestedApiVersion ?? 'unknown'),
                            ],
                          ),
                        ),
                      ),
                      SizedBox(
                        width: cardWidth,
                        child: GaiaSectionCard(
                          title: 'Project Summary',
                          subtitle: '${controller.projects.length} registered projects',
                          child: GaiaKeyValueGrid(
                            rows: [
                              ('Tasks', controller.taskSummary?.total.toString() ?? '0'),
                              ('Approvals', controller.approvalSummary?.total.toString() ?? '0'),
                              ('Actions', controller.actionSummary?.total.toString() ?? '0'),
                              ('Brief', controller.latestBrief?.title ?? 'None'),
                            ],
                          ),
                        ),
                      ),
                      SizedBox(
                        width: cardWidth,
                        child: GaiaSectionCard(
                          title: 'Trust',
                          subtitle: 'Read-only boundary and verification',
                          child: GaiaKeyValueGrid(
                            rows: [
                              ('Templates', controller.actionTemplates.length.toString()),
                              ('Policies', controller.retentionPolicies.length.toString()),
                              ('Receipt hash', controller.latestReceipt?.receiptContentHash ?? 'None'),
                              ('Chain', controller.latestReceipt?.chainId ?? 'None'),
                            ],
                          ),
                        ),
                      ),
                    ],
                  );
                },
              ),
            ],
          ),
        );
      },
    );
  }
}
