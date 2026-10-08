import 'package:flutter/material.dart';

import 'api.dart';
import 'screens/auth_screen.dart';
import 'screens/home_screen.dart';
import 'strings.dart';
import 'theme.dart';

/// Lets the API send the person to the login screen from wherever they are.
final navigatorKey = GlobalKey<NavigatorState>();

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await Api.instance.load();
  // A stored token can be stale (expired, or the database was re-seeded since): the first 401
  // replaces every screen with the login screen and the server's reason, instead of each tab
  // showing its own error.
  Api.instance.onSignedOut = (message) => navigatorKey.currentState?.pushAndRemoveUntil(
        MaterialPageRoute(builder: (_) => AuthScreen(notice: message)),
        (_) => false,
      );
  runApp(const GreenLegacyApp());
}

class GreenLegacyApp extends StatelessWidget {
  const GreenLegacyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: S.appName,
      navigatorKey: navigatorKey,
      debugShowCheckedModeBanner: false,
      theme: appTheme(brightness: Brightness.light),
      darkTheme: appTheme(brightness: Brightness.dark),
      themeMode: ThemeMode.system,
      // Flutter's Material translations do not include Sorani, so the whole app is wrapped
      // right-to-left by hand and every string lives in strings.dart.
      builder: (context, child) => Directionality(textDirection: TextDirection.rtl, child: child!),
      home: Api.instance.token == null ? const AuthScreen() : const HomeScreen(),
    );
  }
}

void showError(BuildContext context, Object error) {
  // The login screen already shows why the session ended; a snackbar per open tab would repeat it.
  if (error is ApiException && error.code == 'unauthorized') return;
  ScaffoldMessenger.of(context).showSnackBar(
    SnackBar(
      content: Text(error is ApiException
          ? error.message
          : error is String
              ? error
              : S.genericError),
    ),
  );
}
