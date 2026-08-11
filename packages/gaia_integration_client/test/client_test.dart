import 'dart:convert';

import 'package:gaia_integration_client/gaia_integration_client.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:test/test.dart';

void main() {
  test(
    'parses compatibility and summaries with stale cache fallback',
    () async {
      var healthCalls = 0;
      final client = MockClient((request) async {
        final path = request.url.path;
        if (path == '/health') {
          healthCalls += 1;
          if (healthCalls > 1) {
            throw http.ClientException('offline', request.url);
          }
          return http.Response(
            jsonEncode({
              'status': 'ok',
              'version': '0.5.0',
              'database_path': 'data/gaia.db',
              'fts5_available': true,
            }),
            200,
          );
        }
        if (path == '/integration/v1/compatibility') {
          return http.Response(
            jsonEncode({
              'backend_product_version': '0.7.0',
              'minimum_supported_api_version': '0.7.0',
              'maximum_tested_api_version': '0.7.0',
              'integration_contract_version': 'gaia-v2',
              'client_package_version': '0.7.0',
              'backend_version': '0.7.0',
              'status': 'compatible_with_warnings',
              'loopback_only': true,
              'capability_version': '0.7.0',
              'capabilities': ['actions', 'receipts', 'retention_policies'],
              'capability_catalog': [
                {
                  'capability_id': 'embedded_operations_workspace',
                  'version': '0.7.0',
                  'state': 'enabled',
                  'summary': 'Embedded operations workspace',
                  'gated_by': const [],
                  'requires_signing': false,
                  'enabled': true,
                },
              ],
              'degraded_features': ['offline_packages'],
              'deprecation_warnings': ['v1 contract is deprecated'],
            }),
            200,
          );
        }
        if (path == '/integration/v1/actions/summary') {
          return http.Response(
            jsonEncode({
              'project_id': 'sample',
              'total': 1,
              'proposed': 0,
              'awaiting_approval': 0,
              'approved': 0,
              'completed': 1,
              'failed': 0,
              'invalidated': 0,
              'rolled_back': 0,
            }),
            200,
          );
        }
        if (path == '/integration/v1/receipts/latest') {
          return http.Response(
            jsonEncode({
              'receipt_id': 'receipt-1',
              'action_id': 'action-1',
              'manifest_id': 'manifest-1',
              'manifest_version': 1,
              'target_path': 'workspace/approved_outputs/demo.md',
              'resulting_hash': 'abc',
              'timestamp': '2026-08-05T00:00:00Z',
              'chain_id': 'manifest-1',
              'chain_sequence': 1,
              'previous_receipt_hash': null,
              'receipt_content_hash': 'hash-1',
              'verification_status': 'valid',
            }),
            200,
          );
        }
        if (path == '/integration/v1/capabilities') {
          return http.Response(
            jsonEncode({
              'capability_version': '0.7.0',
              'capabilities': ['embedded_operations_workspace'],
              'capability_catalog': const [],
              'degraded_features': const [],
              'signing_enabled': false,
              'signing_key_count': 0,
            }),
            200,
          );
        }
        if (path == '/receipts/receipt-1/verify') {
          return http.Response(
            jsonEncode({
              'receipt_id': 'receipt-1',
              'chain_id': 'manifest-1',
              'chain_sequence': 1,
              'status': 'valid',
              'previous_receipt_hash': null,
              'receipt_content_hash': 'hash-1',
              'warnings': const [],
            }),
            200,
          );
        }
        return http.Response('{}', 404);
      });

      final gaia = GaiaIntegrationClient(
        baseUri: Uri.parse('http://127.0.0.1:8765'),
        client: client,
      );

      final health = await gaia.health();
      expect(health.version, '0.5.0');
      final cachedHealth = await gaia.health();
      expect(cachedHealth.status, 'ok');

      final compatibility = await gaia.compatibility();
      expect(compatibility.integrationContractVersion, 'gaia-v2');
      expect(compatibility.status, 'compatible_with_warnings');
      expect(compatibility.capabilities, contains('actions'));
      expect(compatibility.capabilityVersion, '0.7.0');
      expect(
        compatibility.capabilityCatalog.single.capabilityId,
        'embedded_operations_workspace',
      );

      final capabilityPayload = await gaia.capabilityPayload();
      expect(capabilityPayload['capability_version'], '0.7.0');

      final actionSummary = await gaia.actionSummary(projectId: 'sample');
      expect(actionSummary.completed, 1);

      final receipt = await gaia.latestReceipt();
      expect(receipt?.receiptId, 'receipt-1');

      final verification = await gaia.verifyReceipt('receipt-1');
      expect(verification.status, 'valid');
    },
  );

  test('supports project officer compatibility and lifecycle endpoints', () async {
    final client = MockClient((request) async {
      final path = request.url.path;
      if (path == '/integration/v1/project-officer/capabilities') {
        return http.Response(
          jsonEncode({
            'api_version': '0.10.0',
            'contract_version': 'gaia-v3',
            'capability_version': '0.10.0',
            'capabilities': [
              'project_officer_portfolio',
              'project_officer_work_packages',
            ],
            'capability_catalog': [
              {
                'capability_id': 'project_officer_portfolio',
                'version': '0.10.0',
                'state': 'enabled',
                'summary':
                    'Inspect the portfolio of project-health and planning evidence.',
                'authority_level': 'read_only',
                'gated_by': const [],
                'requires_signing': false,
                'enabled': true,
              },
            ],
            'degraded_features': const [],
          }),
          200,
        );
      }
      if (path == '/integration/v1/project-officer/projects/sample/health') {
        return http.Response(
          jsonEncode({
            'snapshot_id': 'snap-1',
            'project_id': 'sample',
            'project_name': 'Sample',
            'project_root': '/tmp/sample',
            'project_configuration_fingerprint': 'abc',
            'capture_timestamp': '2026-08-07T00:00:00Z',
            'normalized_status': 'healthy',
            'reason_codes': const [],
            'explanations': const [],
            'blocking_conditions': const [],
            'attention_conditions': const [],
            'unknown_fields': const [],
            'evidence_references': const [],
            'normalized_payload': const {},
            'provenance_reference': null,
            'audit_event_id': null,
            'content_fingerprint': 'fp',
          }),
          200,
        );
      }
      if (path ==
          '/integration/v1/project-officer/projects/sample/changes/findings') {
        expect(request.url.queryParameters['severity'], 'high');
        expect(request.url.queryParameters['limit'], '1');
        return http.Response(
          jsonEncode([
            {
              'finding_id': 'finding-1',
              'schema_version': 1,
              'comparison_id': 'cmp-1',
              'project_id': 'sample',
              'finding_type': 'documentation_drift',
              'change_class': 'documentation_drift',
              'severity': 'high',
              'direction': 'changed',
              'confidence': 'high',
              'status': 'active',
              'capture_timestamp': '2026-08-07T00:00:00Z',
              'previous_snapshot_id': 'snap-a',
              'current_snapshot_id': 'snap-b',
              'previous_snapshot_fingerprint': 'prev',
              'current_snapshot_fingerprint': 'curr',
              'reason_codes': const [],
              'explanation': 'Docs changed',
              'evidence_references': const [],
              'evidence': const {},
              'normalized_payload': const {},
              'detector_version': '1.0.0',
              'provenance_reference': null,
              'audit_event_id': null,
              'content_fingerprint': 'fp',
            },
          ]),
          200,
        );
      }
      if (path == '/integration/v1/project-officer/recommendations') {
        expect(request.url.queryParameters['priority_tier'], 'P1');
        return http.Response(
          jsonEncode([
            {
              'recommendation_id': 'rec-1',
              'schema_version': 1,
              'project_id': 'sample',
              'recommendation_type': 'review_project_configuration_change',
              'recommendation_policy_version': '1',
              'created_timestamp': '2026-08-07T00:00:00Z',
              'updated_timestamp': '2026-08-07T00:00:00Z',
              'lifecycle_state': 'active',
              'priority_tier': 'P1',
              'deterministic_score': 91,
              'score_breakdown': {'total_score': 91},
              'title': 'Review config',
              'concise_summary': 'Review config',
              'rationale': '',
              'why_it_matters': '',
              'why_it_received_this_score': '',
              'reasons_to_proceed': const [],
              'reasons_not_to_proceed': const [],
              'blockers': const [],
              'dependencies': const [],
              'uncertainty': 'low',
              'source_finding_ids': const [],
              'source_comparison_ids': const [],
              'source_snapshot_ids': const [],
              'evidence_fingerprints': const [],
              'evidence_freshness': 'fresh',
              'evidence_references': const [],
              'semantic_fingerprint': 'sem',
              'content_fingerprint': 'fp',
              'provenance_reference': null,
              'audit_event_id': null,
              'supersedes_recommendation_id': null,
              'superseded_by_recommendation_id': null,
              'normalized_payload': const {},
            },
          ]),
          200,
        );
      }
      if (path == '/integration/v1/project-officer/work-packages/wp-1/prompt') {
        expect(request.url.queryParameters['revision_number'], '2');
        return http.Response(
          jsonEncode({
            'work_package_id': 'wp-1',
            'revision_number': 2,
            'prompt': 'prompt text',
          }),
          200,
        );
      }
      if (path ==
          '/integration/v1/project-officer/work-packages/wp-1/submit-for-review') {
        final body = jsonDecode(request.body) as Map<String, dynamic>;
        expect(body['revision_number'], 2);
        expect(body['actor'], 'manual');
        return http.Response(
          jsonEncode({
            'work_package_id': 'wp-1',
            'project_id': 'sample',
            'revision_number': 2,
            'approval_state': 'under_review',
          }),
          200,
        );
      }
      return http.Response('{}', 404);
    });

    final gaia = GaiaIntegrationClient(
      baseUri: Uri.parse('http://127.0.0.1:8765'),
      client: client,
    );

    final capabilities = await gaia.projectOfficerCapabilities();
    expect(capabilities['contract_version'], 'gaia-v3');

    final health = await gaia.projectOfficerProjectHealth('sample');
    expect(health['normalized_status'], 'healthy');

    final findings = await gaia.projectOfficerChangeFindings(
      'sample',
      severity: 'high',
      limit: 1,
    );
    expect(findings.single['finding_id'], 'finding-1');

    final recommendations = await gaia.projectOfficerRecommendations(
      projectId: 'sample',
      priorityTier: 'P1',
    );
    expect(recommendations.single['recommendation_id'], 'rec-1');

    final prompt = await gaia.projectOfficerWorkPackagePrompt(
      'wp-1',
      revisionNumber: 2,
    );
    expect(prompt['prompt'], 'prompt text');

    final updated = await gaia.projectOfficerSubmitForReview(
      'wp-1',
      revisionNumber: 2,
    );
    expect(updated['approval_state'], 'under_review');
  });

  test(
    'supports public programme, dependency, and release-train read surfaces',
    () async {
      final client = MockClient((request) async {
        final path = request.url.path;
        if (path == '/integration/v1/programme/summary') {
          return http.Response(
            jsonEncode({
              'generated_at': '2026-08-08T00:00:00Z',
              'selected_project_id': 'sample',
              'selected_project': {
                'project_id': 'sample',
                'project_name': 'Sample',
              },
              'summary': {
                'project_count': 1,
                'health_status_counts': {'healthy': 1},
                'change_severity_counts': {'high': 1},
                'recommendation_state_counts': {'active': 1},
                'roadmap_state_counts': {'NOW': 1},
                'release_train_readiness_counts': {'READY': 1},
                'package_state_counts': {'approved': 1},
                'architecture_entity_count': 1,
                'architecture_relationship_count': 1,
                'cycle_count': 0,
                'unresolved_dependency_count': 0,
                'shared_dependency_count': 0,
                'orphan_count': 0,
                'trust_alert_count': 1,
                'provenance_manifest_count': 1,
                'stale_evidence_projects': ['sample'],
              },
              'portfolio': {
                'health_portfolio': {
                  'counts_by_status': {'healthy': 1},
                },
                'change_portfolio': {
                  'counts_by_severity': {'high': 1},
                },
                'recommendation_portfolio': {
                  'counts_by_state': {'active': 1},
                },
                'roadmap_portfolio': {
                  'counts_by_state': {'NOW': 1},
                },
                'release_portfolio': {
                  'counts_by_readiness': {'READY': 1},
                },
                'package_portfolio': {
                  'counts_by_state': {'approved': 1},
                },
              },
              'architecture_registry': {
                'entities': [
                  {
                    'entity_id': 'entity-1',
                    'kind': 'package',
                    'name': 'Shared Library',
                  },
                ],
                'relationships': [
                  {
                    'relationship_id': 'rel-1',
                    'source_entity_id': 'entity-1',
                    'target_entity_id': 'entity-2',
                  },
                ],
              },
              'dependency_graph': {
                'snapshot': {'node_count': 1, 'edge_count': 1},
                'cycles': const [],
                'shared_dependencies': const [],
                'orphans': const [],
                'unresolved_findings': const [],
              },
              'impact_analysis': {
                'analyses': [
                  {
                    'analysis_id': 'analysis-1',
                    'proposal': {'title': 'Demo impact'},
                    'risk': {'risk_level': 'medium'},
                    'freshness_state': 'fresh',
                  },
                ],
                'selected_analysis': {
                  'analysis_id': 'analysis-1',
                  'proposal': {'title': 'Demo impact'},
                  'risk': {'risk_level': 'medium'},
                  'freshness_state': 'fresh',
                },
                'selected_change_findings': const [],
              },
              'change_proposals': {
                'recommendations': [
                  {'recommendation_id': 'rec-1'},
                ],
              },
              'roadmap': {
                'roadmap_items': [
                  {
                    'title': 'Demo roadmap',
                    'project_id': 'sample',
                    'roadmap_state': 'NOW',
                    'freshness': 'fresh',
                  },
                ],
              },
              'release_trains': {
                'release_trains': [
                  {
                    'release_train_id': 'train-1',
                    'objective': 'Demo train',
                    'release_readiness': 'READY',
                    'human_approval_state': 'approved',
                  },
                ],
              },
              'programme_packages': {
                'programme_packages': [
                  {
                    'programme_package_id': 'package-1',
                    'objective': 'Demo package',
                    'package_state': 'approved',
                    'human_approval': {'approval_state': 'approved'},
                  },
                ],
              },
              'decisions': {
                'selected_work_packages': [
                  {'work_package_id': 'wp-1'},
                ],
                'selected_contract': {'contract_id': 'contract-1'},
              },
              'cross_project_evidence': {
                'provenance_manifests': [
                  {'manifest_id': 'manifest-1'},
                ],
                'selected_project_dependencies': [
                  {'dependency_id': 'dep-1'},
                ],
                'selected_project_dependents': [
                  {'dependency_id': 'dep-2'},
                ],
              },
            }),
            200,
          );
        }
        if (path == '/integration/v1/architecture/entities') {
          return http.Response(
            jsonEncode([
              {
                'entity_id': 'entity-1',
                'kind': 'package',
                'name': 'Shared Library',
              },
            ]),
            200,
          );
        }
        if (path == '/integration/v1/architecture/entities/entity-1') {
          return http.Response(
            jsonEncode({'entity_id': 'entity-1', 'kind': 'package'}),
            200,
          );
        }
        if (path == '/integration/v1/architecture/relationships') {
          return http.Response(
            jsonEncode([
              {
                'relationship_id': 'rel-1',
                'source_entity_id': 'entity-1',
                'target_entity_id': 'entity-2',
              },
            ]),
            200,
          );
        }
        if (path == '/integration/v1/architecture/relationships/rel-1') {
          return http.Response(jsonEncode({'relationship_id': 'rel-1'}), 200);
        }
        if (path == '/integration/v1/dependencies/graph') {
          return http.Response(
            jsonEncode({
              'snapshot': {'node_count': 1, 'edge_count': 1},
            }),
            200,
          );
        }
        if (path == '/integration/v1/dependencies/findings') {
          return http.Response(
            jsonEncode([
              {'finding_id': 'finding-1'},
            ]),
            200,
          );
        }
        if (path == '/integration/v1/dependencies/cycles') {
          return http.Response(
            jsonEncode([
              {'cycle_id': 'cycle-1'},
            ]),
            200,
          );
        }
        if (path == '/integration/v1/dependencies/shared') {
          return http.Response(
            jsonEncode([
              {'shared_dependency_id': 'shared-1'},
            ]),
            200,
          );
        }
        if (path == '/integration/v1/dependencies/orphans') {
          return http.Response(
            jsonEncode([
              {'orphan_id': 'orphan-1'},
            ]),
            200,
          );
        }
        if (path == '/integration/v1/dependencies/projects/sample') {
          expect(request.url.queryParameters['transitive'], 'false');
          return http.Response(
            jsonEncode([
              {'dependency_id': 'dep-1'},
            ]),
            200,
          );
        }
        if (path == '/integration/v1/dependencies/projects/sample/dependents') {
          expect(request.url.queryParameters['transitive'], 'false');
          return http.Response(
            jsonEncode([
              {'dependency_id': 'dep-2'},
            ]),
            200,
          );
        }
        if (path == '/integration/v1/change-impact/summary') {
          return http.Response(
            jsonEncode({
              'generated_at': '2026-08-08T00:00:00Z',
              'selected_project_id': 'sample',
              'recommendation_portfolio': const {},
              'change_portfolio': const {},
              'recommendations': const [],
              'analyses': const [],
              'selected_analysis': null,
            }),
            200,
          );
        }
        if (path == '/integration/v1/change-impact/recommendations') {
          return http.Response(
            jsonEncode([
              {'recommendation_id': 'rec-1'},
            ]),
            200,
          );
        }
        if (path == '/integration/v1/change-impact/recommendations/rec-1') {
          return http.Response(jsonEncode({'recommendation_id': 'rec-1'}), 200);
        }
        if (path == '/integration/v1/programme/roadmap') {
          return http.Response(
            jsonEncode({
              'roadmap_items': [
                {'roadmap_item_id': 'item-1'},
              ],
            }),
            200,
          );
        }
        if (path == '/integration/v1/release-trains') {
          return http.Response(
            jsonEncode({
              'release_trains': [
                {'release_train_id': 'train-1'},
              ],
            }),
            200,
          );
        }
        if (path == '/integration/v1/programme-packages') {
          return http.Response(
            jsonEncode({
              'programme_packages': [
                {'programme_package_id': 'package-1'},
              ],
            }),
            200,
          );
        }
        if (path == '/integration/v1/programme-packages/package-1') {
          return http.Response(
            jsonEncode({'programme_package_id': 'package-1'}),
            200,
          );
        }
        return http.Response('{}', 404);
      });

      final gaia = GaiaIntegrationClient(
        baseUri: Uri.parse('http://127.0.0.1:8765'),
        client: client,
      );

      final summary = await gaia.programmeSummary(projectId: 'sample');
      expect(summary.selectedProjectId, 'sample');
      expect(summary.summary.trustAlertCount, 1);
      expect(summary.summary.provenanceManifestCount, 1);
      expect(summary.summary.staleEvidenceProjects, ['sample']);

      expect(
        (await gaia.architectureEntities()).single['entity_id'],
        'entity-1',
      );
      expect(
        (await gaia.architectureEntity('entity-1'))['entity_id'],
        'entity-1',
      );
      expect(
        (await gaia.architectureRelationships()).single['relationship_id'],
        'rel-1',
      );
      expect(
        (await gaia.architectureRelationship('rel-1'))['relationship_id'],
        'rel-1',
      );
      expect((await gaia.dependencyGraph())['snapshot']['node_count'], 1);
      expect(
        (await gaia.dependencyFindings()).single['finding_id'],
        'finding-1',
      );
      expect((await gaia.dependencyCycles()).single['cycle_id'], 'cycle-1');
      expect(
        (await gaia.dependencySharedDependencies())
            .single['shared_dependency_id'],
        'shared-1',
      );
      expect((await gaia.dependencyOrphans()).single['orphan_id'], 'orphan-1');
      expect(
        (await gaia.dependencyProjectDependencies(
          'sample',
        )).single['dependency_id'],
        'dep-1',
      );
      expect(
        (await gaia.dependencyProjectDependents(
          'sample',
        )).single['dependency_id'],
        'dep-2',
      );

      expect(
        (await gaia.changeImpactSummary(
          projectId: 'sample',
        ))['selected_project_id'],
        'sample',
      );
      expect(
        (await gaia.changeImpactRecommendations(
          projectId: 'sample',
        )).single['recommendation_id'],
        'rec-1',
      );
      expect(
        (await gaia.changeImpactRecommendation('rec-1'))['recommendation_id'],
        'rec-1',
      );

      expect((await gaia.programmeRoadmap())['roadmap_items'], isA<List>());
      expect((await gaia.releaseTrains())['release_trains'], isA<List>());
      expect(
        (await gaia.programmePackages())['programme_packages'],
        isA<List>(),
      );
      expect(
        (await gaia.programmePackage('package-1'))['programme_package_id'],
        'package-1',
      );
    },
  );
}
