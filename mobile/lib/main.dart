import 'package:flutter/material.dart';

import 'api.dart';
import 'screens/auth_screen.dart';
import 'screens/home_screen.dart';
import 'strings.dart';
import 'theme.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await Api.instance.load();
  runApp(const GreenLegacyApp());
}

class GreenLegacyApp extends StatelessWidget {
  const GreenLegacyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: S.appName,
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
