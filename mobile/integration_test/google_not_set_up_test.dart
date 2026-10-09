// A server with Google sign-in on, and an app build without the iOS Google client (setup_ios.py run
// without GOOGLE_IOS_CLIENT_ID): the Google button shows, and tapping it explains instead of crashing.
//
//   cd ../backend && GOOGLE_CLIENT_IDS=web.example GOOGLE_SERVER_CLIENT_ID=web.example PORT=5056 python run.py
//   flutter test integration_test/google_not_set_up_test.dart -d <iOS simulator> \
//       --dart-define=SERVER_URL=http://localhost:5056
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:slemani_green_legacy/main.dart' as app;
import 'package:slemani_green_legacy/strings.dart';

const serverUrl = String.fromEnvironment('SERVER_URL');

Future<void> until(WidgetTester t, Finder f, {int seconds = 20}) async {
  for (var i = 0; i < seconds * 5; i++) {
    await t.pump();
    if (f.evaluate().isNotEmpty) return;
    await Future<void>.delayed(const Duration(milliseconds: 200));
  }
  final shown = find.byType(Text).evaluate().map((e) => (e.widget as Text).data).whereType<String>().toSet();
  fail('did not appear within $seconds s: $f\non screen: ${shown.join(' | ')}');
}

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('Google on at the server, not set up in this build: a message, not a crash', (t) async {
    expect(serverUrl, isNotEmpty, reason: 'pass --dart-define=SERVER_URL=<a server with Google on>');
    final prefs = await SharedPreferences.getInstance();
    await prefs.clear();
    await prefs.setString('baseUrl', serverUrl);

    await app.main();
    await until(t, find.byKey(const Key('google')));        // the server said Google is on
    await Future<void>.delayed(const Duration(milliseconds: 700));
    await t.tap(find.byKey(const Key('google')));
    await until(t, find.text(S.googleNotSetUp));
    expect(find.text(S.welcomeBack), findsOneWidget);         // still on the login screen
  });
}
