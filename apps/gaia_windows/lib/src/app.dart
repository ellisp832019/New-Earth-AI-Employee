import 'dart:async';
import 'dart:io';

import 'package:flutter/material.dart';

import 'backend_process.dart';
import 'controller.dart';
import 'screens.dart';
import 'settings_store.dart';

class GaiaWindowsApp extends StatefulWidget {
  const GaiaWindowsApp({super.key});

  @override
  State<GaiaWindowsApp> createState() => _GaiaWindowsAppState();
}

class _GaiaWindowsAppState extends State<GaiaWindowsApp> {
  late final GaiaAppController controller;

  @override
  void initState() {
    super.initState();
    final repositoryRoot = GaiaAppSettings.defaults().repositoryRootPath;
    controller = GaiaAppController(
      backendProcessManager: BackendProcessManager(
        repositoryRoot: repositoryRoot,
        pythonExecutable: defaultPythonPath(repositoryRoot),
        backendPort: 8000,
        logDirectory: _defaultLogDirectory(),
      ),
    );
    unawaited(controller.bootstrap());
  }

  @override
  void dispose() {
    controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return GaiaAppScope(
      controller: controller,
      child: AnimatedBuilder(
        animation: controller,
        builder: (context, _) {
          return MaterialApp(
            title: 'GAIA Windows Control Centre',
            debugShowCheckedModeBanner: false,
            themeMode: controller.settings.toThemeMode(),
            theme: _buildTheme(Brightness.light),
            darkTheme: _buildTheme(Brightness.dark),
            home: controller.initialized
                ? controller.firstRunMode
                      ? FirstRunScreen(controller: controller)
                      : GaiaShell(controller: controller)
                : const _LoadingScreen(),
          );
        },
      ),
    );
  }

  ThemeData _buildTheme(Brightness brightness) {
    final colorScheme = ColorScheme.fromSeed(
      seedColor: const Color(0xFF177B75),
      brightness: brightness,
    );
    return ThemeData(
      colorScheme: colorScheme,
      useMaterial3: true,
      scaffoldBackgroundColor: colorScheme.surface,
      appBarTheme: AppBarTheme(backgroundColor: colorScheme.surface),
      cardTheme: CardThemeData(
        color: colorScheme.surfaceContainerHighest.withValues(
          alpha: brightness == Brightness.dark ? 0.5 : 0.7,
        ),
        elevation: 0,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
      ),
      navigationRailTheme: NavigationRailThemeData(
        backgroundColor: colorScheme.surface,
        selectedIconTheme: IconThemeData(color: colorScheme.primary),
        selectedLabelTextStyle: TextStyle(
          color: colorScheme.primary,
          fontWeight: FontWeight.w600,
        ),
      ),
    );
  }

  Directory _defaultLogDirectory() {
    final localAppData =
        Platform.environment['LOCALAPPDATA'] ?? Directory.current.path;
    return Directory(
      '$localAppData${Platform.pathSeparator}NewEarthAIEmployee${Platform.pathSeparator}gaia_windows${Platform.pathSeparator}logs',
    );
  }
}

class _LoadingScreen extends StatelessWidget {
  const _LoadingScreen();

  @override
  Widget build(BuildContext context) {
    return const Scaffold(
      body: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            CircularProgressIndicator(),
            SizedBox(height: 16),
            Text('Starting GAIA...'),
          ],
        ),
      ),
    );
  }
}

class GaiaAppScope extends InheritedNotifier<GaiaAppController> {
  const GaiaAppScope({
    super.key,
    required GaiaAppController controller,
    required super.child,
  }) : super(notifier: controller);

  static GaiaAppController of(BuildContext context) {
    final scope = context.dependOnInheritedWidgetOfExactType<GaiaAppScope>();
    assert(scope != null, 'GaiaAppScope not found in widget tree');
    return scope!.notifier!;
  }
}
