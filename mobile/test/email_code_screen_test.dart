import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:slemani_green_legacy/api.dart';
import 'package:slemani_green_legacy/screens/registration/email_code_screen.dart';
import 'package:slemani_green_legacy/strings.dart';

Widget rtl(Widget child) =>
    MaterialApp(home: Directionality(textDirection: TextDirection.rtl, child: child));

bool enabled(WidgetTester tester, Key key) {
  final button = tester.widget<ButtonStyleButton>(find.byKey(key));
  return button.onPressed != null;
}

/// Plays the server: each call answers with the next item (a map, or an ApiException to throw).
class FakeServer {
  FakeServer({this.sends = const [], this.checks = const []});
  final List<Object> sends;
  final List<Object> checks;
  int sent = 0;
  int checked = 0;

  Future<Map<String, dynamic>> send(String email) async => _answer(sends[sent++]);
  Future<Map<String, dynamic>> check(String email, String code) async => _answer(checks[checked++]);

  Map<String, dynamic> _answer(Object a) => a is ApiException ? throw a : a as Map<String, dynamic>;
}

Future<void> sendCode(WidgetTester tester) async {
  await tester.enterText(find.byKey(const Key('email')), 'rand@example.com');
  await tester.tap(find.byKey(const Key('send')));
  await tester.pump();
}

void main() {
  testWidgets('the resend button waits as long as the server says', (tester) async {
    final server = FakeServer(sends: [
      {'sent': true, 'expires_in': 300, 'resend_in': 60},
      {'sent': true, 'expires_in': 300, 'resend_in': 60},
    ]);
    await tester.pumpWidget(rtl(EmailCodeScreen(requestCode: server.send, verifyCode: server.check)));
    await sendCode(tester);

    expect(find.text(S.codeSent('rand@example.com', 6)), findsOneWidget);
    expect(find.text(S.resendIn(60)), findsOneWidget);
    expect(enabled(tester, const Key('resend')), isFalse);

    await tester.pump(const Duration(seconds: 30));
    expect(find.text(S.resendIn(30)), findsOneWidget);
    expect(enabled(tester, const Key('resend')), isFalse);

    await tester.pump(const Duration(seconds: 31));
    expect(enabled(tester, const Key('resend')), isTrue);
    await tester.tap(find.byKey(const Key('resend')));
    await tester.pump();
    expect(server.sent, 2);

    await tester.pumpWidget(const SizedBox());     // the countdown's timer goes with the screen
  });

  testWidgets('a wait the server asks for (too soon) still lets the person type the code', (tester) async {
    final server = FakeServer(sends: [
      ApiException('تکایە چەند چرکەیەک چاوەڕێ بکە', 'otp_too_soon', {'retry_after': 42}),
    ]);
    await tester.pumpWidget(rtl(EmailCodeScreen(requestCode: server.send, verifyCode: server.check)));
    await sendCode(tester);
    expect(find.byKey(const Key('code')), findsOneWidget);
    expect(find.text(S.resendIn(42)), findsOneWidget);
    expect(find.text('تکایە چەند چرکەیەک چاوەڕێ بکە'), findsOneWidget);
    await tester.pumpWidget(const SizedBox());
  });

  testWidgets('wrong codes show the tries left; a dead code asks for a new one', (tester) async {
    final server = FakeServer(sends: [
      {'sent': true, 'expires_in': 300, 'resend_in': 0},
    ], checks: [
      ApiException('کۆدەکە هەڵەیە', 'otp_invalid', {'attempts_left': 2}),
      ApiException('هەوڵی زۆر درا؛ کۆدێکی نوێ داوا بکە', 'otp_locked'),
    ]);
    await tester.pumpWidget(rtl(EmailCodeScreen(requestCode: server.send, verifyCode: server.check)));
    await sendCode(tester);

    await tester.enterText(find.byKey(const Key('code')), '111111');
    await tester.tap(find.byKey(const Key('verify')));
    await tester.pump();
    expect(find.text(S.attemptsLeft(2)), findsOneWidget);
    expect(find.text('کۆدەکە هەڵەیە'), findsOneWidget);
    expect(tester.widget<TextField>(find.byKey(const Key('code'))).controller!.text, isEmpty);

    await tester.enterText(find.byKey(const Key('code')), '222222');
    await tester.tap(find.byKey(const Key('verify')));
    await tester.pump();
    expect(find.text('هەوڵی زۆر درا؛ کۆدێکی نوێ داوا بکە'), findsOneWidget);
    expect(enabled(tester, const Key('verify')), isFalse);
    expect(find.text(S.requestNewCode), findsOneWidget);
    expect(enabled(tester, const Key('resend')), isTrue);
  });

  testWidgets('a short code is not sent; the right one hands back the token', (tester) async {
    String? token;
    String? email;
    final server = FakeServer(sends: [
      {'sent': true, 'expires_in': 300, 'resend_in': 0},
    ], checks: [
      {'email_verification_token': 'step-token', 'expires_in': 600, 'email_has_account': false},
    ]);
    await tester.pumpWidget(rtl(EmailCodeScreen(
        requestCode: server.send, verifyCode: server.check, onVerified: (t, e) => (token, email) = (t, e))));
    await sendCode(tester);

    await tester.enterText(find.byKey(const Key('code')), '123');
    await tester.tap(find.byKey(const Key('verify')));
    await tester.pump();
    expect(server.checked, 0);

    await tester.enterText(find.byKey(const Key('code')), '123456');
    await tester.tap(find.byKey(const Key('verify')));
    await tester.pump();
    expect(token, 'step-token');
    expect(email, 'rand@example.com');
  });
}
