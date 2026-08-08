import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';

import 'src/app.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  FlutterError.onError = (details) {
    FlutterError.presentError(details);
    debugPrint('GAIA Flutter error: ${details.exceptionAsString()}');
    if (details.stack != null) {
      debugPrint(details.stack.toString());
    }
  };
  PlatformDispatcher.instance.onError = (error, stack) {
    debugPrint('GAIA uncaught async error: $error');
    debugPrint(stack.toString());
    return false;
  };
  runApp(const GaiaWindowsApp());
}
