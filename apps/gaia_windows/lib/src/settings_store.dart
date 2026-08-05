import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'models.dart';

class GaiaAppSettings {
  GaiaAppSettings({
    required this.repositoryRootPath,
    required this.backendUrl,
    required this.backendLaunchPreference,
    required this.defaultProjectId,
    required this.preferredProvider,
    required this.preferredModelName,
    required this.defaultEvidenceLimit,
    required this.deterministicOnlyDefault,
    required this.reportFormatPreference,
    required this.themePreference,
    required this.logRetentionDays,
    required this.firstRunComplete,
    required this.windowWidth,
    required this.windowHeight,
  });

  factory GaiaAppSettings.defaults() {
    return GaiaAppSettings(
      repositoryRootPath: _discoverRepositoryRoot()?.path ?? Directory.current.path,
      backendUrl: 'http://127.0.0.1:8000',
      backendLaunchPreference: BackendLaunchPreference.startLocal,
      defaultProjectId: 'microgrow-v1',
      preferredProvider: 'mock',
      preferredModelName: '',
      defaultEvidenceLimit: 8,
      deterministicOnlyDefault: true,
      reportFormatPreference: ReportFormatPreference.markdown,
      themePreference: ThemePreference.system,
      logRetentionDays: 14,
      firstRunComplete: false,
      windowWidth: 1440,
      windowHeight: 960,
    );
  }

  factory GaiaAppSettings.fromMap(Map<String, dynamic> map) {
    return GaiaAppSettings(
      repositoryRootPath: map['repository_root_path'] as String? ?? _discoverRepositoryRoot()?.path ?? Directory.current.path,
      backendUrl: map['backend_url'] as String? ?? 'http://127.0.0.1:8000',
      backendLaunchPreference: _launchPreferenceFromString(map['backend_launch_preference'] as String?),
      defaultProjectId: map['default_project_id'] as String? ?? 'microgrow-v1',
      preferredProvider: map['preferred_provider'] as String? ?? 'mock',
      preferredModelName: map['preferred_model_name'] as String? ?? '',
      defaultEvidenceLimit: map['default_evidence_limit'] as int? ?? 8,
      deterministicOnlyDefault: map['deterministic_only_default'] as bool? ?? true,
      reportFormatPreference: _reportFormatFromString(map['report_format_preference'] as String?),
      themePreference: _themeFromString(map['theme_preference'] as String?),
      logRetentionDays: map['log_retention_days'] as int? ?? 14,
      firstRunComplete: map['first_run_complete'] as bool? ?? false,
      windowWidth: (map['window_width'] as num?)?.toDouble() ?? 1440,
      windowHeight: (map['window_height'] as num?)?.toDouble() ?? 960,
    );
  }

  final String repositoryRootPath;
  final String backendUrl;
  final BackendLaunchPreference backendLaunchPreference;
  final String defaultProjectId;
  final String preferredProvider;
  final String preferredModelName;
  final int defaultEvidenceLimit;
  final bool deterministicOnlyDefault;
  final ReportFormatPreference reportFormatPreference;
  final ThemePreference themePreference;
  final int logRetentionDays;
  final bool firstRunComplete;
  final double windowWidth;
  final double windowHeight;

  GaiaAppSettings copyWith({
    String? repositoryRootPath,
    String? backendUrl,
    BackendLaunchPreference? backendLaunchPreference,
    String? defaultProjectId,
    String? preferredProvider,
    String? preferredModelName,
    int? defaultEvidenceLimit,
    bool? deterministicOnlyDefault,
    ReportFormatPreference? reportFormatPreference,
    ThemePreference? themePreference,
    int? logRetentionDays,
    bool? firstRunComplete,
    double? windowWidth,
    double? windowHeight,
  }) {
    return GaiaAppSettings(
      repositoryRootPath: repositoryRootPath ?? this.repositoryRootPath,
      backendUrl: backendUrl ?? this.backendUrl,
      backendLaunchPreference: backendLaunchPreference ?? this.backendLaunchPreference,
      defaultProjectId: defaultProjectId ?? this.defaultProjectId,
      preferredProvider: preferredProvider ?? this.preferredProvider,
      preferredModelName: preferredModelName ?? this.preferredModelName,
      defaultEvidenceLimit: defaultEvidenceLimit ?? this.defaultEvidenceLimit,
      deterministicOnlyDefault: deterministicOnlyDefault ?? this.deterministicOnlyDefault,
      reportFormatPreference: reportFormatPreference ?? this.reportFormatPreference,
      themePreference: themePreference ?? this.themePreference,
      logRetentionDays: logRetentionDays ?? this.logRetentionDays,
      firstRunComplete: firstRunComplete ?? this.firstRunComplete,
      windowWidth: windowWidth ?? this.windowWidth,
      windowHeight: windowHeight ?? this.windowHeight,
    );
  }

  Map<String, dynamic> toMap() {
    return <String, dynamic>{
      'repository_root_path': repositoryRootPath,
      'backend_url': backendUrl,
      'backend_launch_preference': backendLaunchPreference.name,
      'default_project_id': defaultProjectId,
      'preferred_provider': preferredProvider,
      'preferred_model_name': preferredModelName,
      'default_evidence_limit': defaultEvidenceLimit,
      'deterministic_only_default': deterministicOnlyDefault,
      'report_format_preference': reportFormatPreference.name,
      'theme_preference': themePreference.name,
      'log_retention_days': logRetentionDays,
      'first_run_complete': firstRunComplete,
      'window_width': windowWidth,
      'window_height': windowHeight,
    };
  }

  ThemeMode toThemeMode() {
    return switch (themePreference) {
      ThemePreference.system => ThemeMode.system,
      ThemePreference.light => ThemeMode.light,
      ThemePreference.dark => ThemeMode.dark,
    };
  }

  Uri backendUri() => Uri.parse(backendUrl);
}

class GaiaSettingsStore {
  GaiaSettingsStore(this._prefs);

  static const String _storageKey = 'gaia_windows_settings_v1';
  final SharedPreferences _prefs;

  static Future<GaiaSettingsStore> open() async {
    final prefs = await SharedPreferences.getInstance();
    return GaiaSettingsStore(prefs);
  }

  Future<GaiaAppSettings> load() async {
    final raw = _prefs.getString(_storageKey);
    if (raw == null || raw.isEmpty) {
      return GaiaAppSettings.defaults();
    }
    final decoded = jsonDecode(raw);
    if (decoded is Map<String, dynamic>) {
      return GaiaAppSettings.fromMap(decoded);
    }
    if (decoded is Map) {
      return GaiaAppSettings.fromMap(decoded.cast<String, dynamic>());
    }
    return GaiaAppSettings.defaults();
  }

  Future<void> save(GaiaAppSettings settings) async {
    await _prefs.setString(_storageKey, jsonEncode(settings.toMap()));
  }
}

BackendLaunchPreference _launchPreferenceFromString(String? value) {
  return BackendLaunchPreference.values.firstWhere(
    (entry) => entry.name == value,
    orElse: () => BackendLaunchPreference.startLocal,
  );
}

ReportFormatPreference _reportFormatFromString(String? value) {
  return ReportFormatPreference.values.firstWhere(
    (entry) => entry.name == value,
    orElse: () => ReportFormatPreference.markdown,
  );
}

ThemePreference _themeFromString(String? value) {
  return ThemePreference.values.firstWhere(
    (entry) => entry.name == value,
    orElse: () => ThemePreference.system,
  );
}

Directory? _discoverRepositoryRoot() {
  final candidates = <Directory>[
    Directory.current,
    Directory(Directory.current.parent.path),
    if (Directory.current.parent.parent.path.isNotEmpty) Directory(Directory.current.parent.parent.path),
  ];
  for (final directory in candidates) {
    if (_looksLikeRepositoryRoot(directory)) {
      return directory;
    }
  }
  return null;
}

bool _looksLikeRepositoryRoot(Directory directory) {
  return File('${directory.path}${Platform.pathSeparator}pyproject.toml').existsSync() &&
      Directory('${directory.path}${Platform.pathSeparator}src${Platform.pathSeparator}gaia').existsSync() &&
      Directory('${directory.path}${Platform.pathSeparator}config').existsSync();
}
