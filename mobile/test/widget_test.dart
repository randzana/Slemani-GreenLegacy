import 'package:flutter_test/flutter_test.dart';

import 'package:slemani_green_legacy/main.dart';
import 'package:slemani_green_legacy/strings.dart';

void main() {
  testWidgets('with no saved login the app opens on the login screen', (tester) async {
    await tester.pumpWidget(const GreenLegacyApp());
    expect(find.text(S.welcomeBack), findsOneWidget);
    expect(find.text(S.server), findsOneWidget);
  });
}
