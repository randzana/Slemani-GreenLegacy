// The sign-up and sign-in flows on a real device or simulator, against a running server whose email
// codes go to its log (OTP_SENDER=console), the way the demo laptop runs. From mobile/:
//
//   cd ../backend && OTP_SENDER=console PORT=5055 python run.py 2> /tmp/gl_server.log   # another terminal
//   flutter test integration_test/flows_test.dart -d <simulator> \
//       --dart-define=SERVER_URL=http://localhost:5055 --dart-define=SERVER_LOG=/tmp/gl_server.log
//
// Use a test database: each run makes a new account (a new email and phone). localhost is the laptop
// itself for the iOS Simulator. The app's saved login and server address are replaced.
import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:integration_test/integration_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:slemani_green_legacy/main.dart' as app;
import 'package:slemani_green_legacy/strings.dart';

const serverUrl = String.fromEnvironment('SERVER_URL');
const serverLog = String.fromEnvironment('SERVER_LOG');

/// Real time passes (the app talks to a real server), then a frame.
Future<void> wait(WidgetTester t, [int ms = 600]) async {
  await Future<void>.delayed(Duration(milliseconds: ms));
  await t.pump();
}

bool shows(Finder f) {
  try {
    return f.evaluate().isNotEmpty;
  } on StateError {
    return false;                                       // .first / .last of nothing
  }
}

Future<void> until(WidgetTester t, Finder f, {int seconds = 20}) async {
  for (var i = 0; i < seconds * 5; i++) {
    await t.pump();
    if (shows(f)) return;
    await Future<void>.delayed(const Duration(milliseconds: 200));
  }
  // what is on screen instead, so a failure says where the app actually is
  final shown = find.byType(Text).evaluate().map((e) => (e.widget as Text).data).whereType<String>().toSet();
  String described;
  try {
    described = '$f';
  } on StateError {
    described = 'a .first/.last of nothing';
  }
  fail('did not appear within $seconds s: $described\non screen: ${shown.join(' | ')}');
}

Future<void> untilGone(WidgetTester t, Finder f, {int seconds = 10}) async {
  for (var i = 0; i < seconds * 5; i++) {
    await t.pump();
    if (!shows(f)) return;
    await Future<void>.delayed(const Duration(milliseconds: 200));
  }
  fail('still on screen after $seconds s');
}

Future<void> tapOn(WidgetTester t, Finder f) async {
  await until(t, f);
  await wait(t, 700);                                   // a page may still be sliding in
  // to the middle of the screen: at the bottom edge the round report button covers it
  await Scrollable.ensureVisible(t.element(f.first), alignment: 0.5);
  await wait(t, 300);
  await t.tap(f.first);
  await wait(t);
}

Future<void> type(WidgetTester t, String label, String text) async {
  final field = find.widgetWithText(TextField, label);
  await until(t, field);
  await t.ensureVisible(field.first);
  await t.enterText(field.first, text);
  await t.pump();
}

/// The newest code the server wrote to its log after [before] lines.
Future<String> codeFromLog(int before) async {
  for (var i = 0; i < 50; i++) {
    final lines = File(serverLog).readAsLinesSync().skip(before);
    final found = lines.map(RegExp(r'EMAIL CODE for \S+: (\d+)').firstMatch).whereType<RegExpMatch>();
    if (found.isNotEmpty) return found.last.group(1)!;
    await Future<void>.delayed(const Duration(milliseconds: 200));
  }
  throw StateError('no email code in $serverLog');
}

/// The bottom bar's tab, not another text that happens to say the same.
Finder tab(String label) => find.descendant(of: find.byType(BottomAppBar), matching: find.text(label));

/// What the municipality does on its dashboard: reject this person's household, with a reason.
/// The staff login is seed.py's practice default (a test database).
Future<void> staffRejectsHome(String ownerPhone, String reason) async {
  Future<dynamic> call(String method, String path, [Map<String, dynamic>? body, String? token]) async {
    final headers = {'Content-Type': 'application/json', if (token != null) 'Authorization': 'Bearer $token'};
    final uri = Uri.parse('$serverUrl$path');
    final res = method == 'GET'
        ? await http.get(uri, headers: headers)
        : await http.post(uri, headers: headers, body: jsonEncode(body ?? {}));
    return jsonDecode(utf8.decode(res.bodyBytes));
  }

  final staff = (await call('POST', '/auth/login', {'login': '07500000000', 'password': 'staff1234'}))['token'];
  final queue = List<Map<String, dynamic>>.from(await call('GET', '/admin/places', null, staff));
  final home = queue.firstWhere((p) => p['owner_phone'] == '+964${ownerPhone.substring(1)}');
  final answer = await call('POST', '/admin/places/${home['id']}/review',
      {'decision': 'reject', 'reason': reason, 'updated_at': home['updated_at']}, staff);
  expect(answer['verification_status'], 'rejected');
}

Future<void> signOut(WidgetTester t) async {
  await untilGone(t, find.byType(SnackBar));            // a snackbar lifts the report button over the page
  await tapOn(t, tab(S.profile));
  await tapOn(t, find.text(S.logoutOfAccount));
  await until(t, find.text(S.welcomeBack));
}

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('A: sign up with a household and an email code; the municipality rejects it and the '
      'person fixes it; C/D: sign in with the email or the phone',
      (t) async {
    expect(serverUrl, isNotEmpty, reason: 'pass --dart-define=SERVER_URL=<the test server>');
    expect(serverLog, isNotEmpty, reason: 'pass --dart-define=SERVER_LOG=<its log>');
    final run = DateTime.now().millisecondsSinceEpoch;
    final email = 'flow$run@example.com';
    final phone = '0770${(run % 10000000).toString().padLeft(7, '0')}';
    final prefs = await SharedPreferences.getInstance();
    await prefs.clear();                                // no saved login
    await prefs.setString('baseUrl', serverUrl);        // what the server field would hold

    await app.main();
    await until(t, find.text(S.welcomeBack));

    // A1: what is registered
    await tapOn(t, find.text(S.signUp));
    await tapOn(t, find.byKey(const Key('type-household')));
    await tapOn(t, find.text(S.next));

    // A2: the form, and the home's pin on the map
    await type(t, S.name, 'ڕەند');
    await type(t, S.phone, phone);
    await type(t, S.password, 'secret123');
    // the neighbourhood list arrives from the server: open the menu until it has them
    final hoods = find.widgetWithText(DropdownButtonFormField<int>, S.neighbourhood);
    for (var i = 0; i < 10 && !shows(find.text('بەختیاری')); i++) {
      await tapOn(t, hoods);
      await wait(t, 500);
    }
    await tapOn(t, find.text('بەختیاری').last);
    await type(t, S.householdName, 'ماڵی ڕەند');
    await tapOn(t, find.byIcon(Icons.add_circle_outline));          // two residents
    await tapOn(t, find.text(S.chooseOnMap));
    await until(t, find.byType(FlutterMap));
    await wait(t, 1500);
    await t.tap(find.byType(FlutterMap));                           // the map opens on Slemani
    await wait(t);
    await tapOn(t, find.text(S.confirmLocation));
    await until(t, find.text(S.locationChosen));
    await tapOn(t, find.widgetWithText(ElevatedButton, S.next));

    // A3: the email code, read from the server's log like the demo operator does
    await until(t, find.text(S.emailTitle));
    await t.enterText(find.byKey(const Key('email')), email);
    final before = File(serverLog).readAsLinesSync().length;
    await tapOn(t, find.byKey(const Key('send')));
    await until(t, find.byKey(const Key('code')));
    expect(find.text(S.resendIn(60)), findsOneWidget);
    await t.enterText(find.byKey(const Key('code')), await codeFromLog(before));
    await tapOn(t, find.byKey(const Key('verify')));

    // A4: signed in; the home waits for the municipality
    await until(t, tab(S.home));
    await tapOn(t, tab(S.profile));
    await until(t, find.text(S.myPlaces));
    await t.ensureVisible(find.text(S.myPlaces));
    expect(find.text('ماڵی ڕەند'), findsOneWidget);
    expect(find.text(S.placeStatuses['pending']!), findsOneWidget);
    expect(find.text(email), findsOneWidget);
    await signOut(t);

    // the municipality rejects the home, with a reason
    const reason = 'ناونیشانەکە ناتەواوە';
    await staffRejectsHome(phone, reason);

    // C: sign in with the email, in another spelling; the reason is on the profile
    await type(t, S.loginField, email.toUpperCase());
    await type(t, S.password, 'secret123');
    await tapOn(t, find.widgetWithText(ElevatedButton, S.signIn));
    await until(t, tab(S.home));
    await tapOn(t, tab(S.profile));
    await until(t, find.text(S.rejectedBecause(reason)));
    expect(find.text(S.placeStatuses['rejected']!), findsOneWidget);

    // fixing it resubmits it: the edit screen shows the reason, saving puts it back in the queue
    await tapOn(t, find.text('ماڵی ڕەند'));
    await until(t, find.text(S.fixAndResend));
    await type(t, S.address, 'سەرچنار، کۆڵانی ٧');
    await tapOn(t, find.widgetWithText(ElevatedButton, S.save));
    await untilGone(t, find.text(S.fixAndResend));             // the edit screen has closed
    await until(t, find.text(S.placeStatuses['pending']!));
    expect(find.text(S.rejectedBecause(reason)), findsNothing);
    await signOut(t);

    // D: sign in with the phone, written the international way (old accounts only have a phone)
    await type(t, S.loginField, '+964${phone.substring(1)}');
    await type(t, S.password, 'secret123');
    await tapOn(t, find.widgetWithText(ElevatedButton, S.signIn));
    await until(t, tab(S.home));
  });
}
