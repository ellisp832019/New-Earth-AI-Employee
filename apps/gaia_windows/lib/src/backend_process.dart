import 'dart:async';
import 'dart:convert';
import 'dart:io';

class BackendProcessSession {
  BackendProcessSession({
    required this.process,
    required this.startedByApp,
    required this.logFile,
  });

  final Process process;
  final bool startedByApp;
  final File logFile;
  final List<String> recentOutput = <String>[];
  final List<String> recentError = <String>[];
  StreamSubscription<String>? _stdoutSubscription;
  StreamSubscription<String>? _stderrSubscription;

  void attachLogging({
    required void Function(String line) onStdout,
    required void Function(String line) onStderr,
  }) {
    _stdoutSubscription = process.stdout
        .transform(utf8.decoder)
        .transform(const LineSplitter())
        .listen((line) {
      _append(recentOutput, line);
      onStdout(line);
    });
    _stderrSubscription = process.stderr
        .transform(utf8.decoder)
        .transform(const LineSplitter())
        .listen((line) {
      _append(recentError, line);
      onStderr(line);
    });
  }

  Future<void> dispose() async {
    await _stdoutSubscription?.cancel();
    await _stderrSubscription?.cancel();
  }

  void _append(List<String> buffer, String line) {
    buffer.add(line);
    if (buffer.length > 200) {
      buffer.removeAt(0);
    }
    unawaited(logFile.writeAsString('$line${Platform.lineTerminator}', mode: FileMode.append));
  }
}

class BackendProcessManager {
  BackendProcessManager({
    required this.repositoryRoot,
    required this.pythonExecutable,
    required this.backendPort,
    required this.logDirectory,
  });

  final String repositoryRoot;
  final String pythonExecutable;
  final int backendPort;
  final Directory logDirectory;
  BackendProcessSession? _session;

  bool get hasRunningSession => _session != null;
  BackendProcessSession? get session => _session;

  Future<BackendProcessSession> start({
    required void Function(String line) onStdout,
    required void Function(String line) onStderr,
  }) async {
    if (_session != null) {
      return _session!;
    }
    final python = File(pythonExecutable);
    if (!python.existsSync()) {
      throw StateError('Python virtual environment is missing at $pythonExecutable');
    }
    logDirectory.createSync(recursive: true);
    final logFile = File('${logDirectory.path}${Platform.pathSeparator}backend-${DateTime.now().toIso8601String().replaceAll(':', '-')}.log');
    final process = await Process.start(
      pythonExecutable,
      <String>['-m', 'gaia', 'serve', '--host', '127.0.0.1', '--port', '$backendPort'],
      workingDirectory: repositoryRoot,
      mode: ProcessStartMode.normal,
    );
    final session = BackendProcessSession(process: process, startedByApp: true, logFile: logFile);
    session.attachLogging(onStdout: onStdout, onStderr: onStderr);
    _session = session;
    process.exitCode.then((_) async {
      await session.dispose();
      if (identical(_session, session)) {
        _session = null;
      }
    });
    return session;
  }

  Future<void> stop() async {
    final session = _session;
    if (session == null) {
      return;
    }
    if (session.startedByApp) {
      session.process.kill(ProcessSignal.sigterm);
    }
    await session.dispose();
    _session = null;
  }

  Future<void> pruneLogs({required int retentionDays}) async {
    if (!logDirectory.existsSync()) {
      return;
    }
    final cutoff = DateTime.now().subtract(Duration(days: retentionDays));
    for (final entity in logDirectory.listSync()) {
      if (entity is File) {
        try {
          final stat = await entity.stat();
          if (stat.modified.isBefore(cutoff)) {
            await entity.delete();
          }
        } catch (_) {
        }
      }
    }
  }
}

String defaultPythonPath(String repositoryRoot) {
  return '$repositoryRoot${Platform.pathSeparator}.venv${Platform.pathSeparator}Scripts${Platform.pathSeparator}python.exe';
}
