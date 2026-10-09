import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:slemani_green_legacy/screens/registration/account_type_screen.dart';
import 'package:slemani_green_legacy/screens/registration/registration_draft.dart';
import 'package:slemani_green_legacy/strings.dart';

Widget rtl(Widget child) =>
    MaterialApp(home: Directionality(textDirection: TextDirection.rtl, child: child));

void main() {
  testWidgets('three cards: the citizen is always included, home and business are chosen freely', (tester) async {
    final draft = RegistrationDraft();
    RegistrationDraft? continued;
    await tester.pumpWidget(rtl(AccountTypeScreen(draft: draft, onContinue: (_, d) => continued = d)));

    expect(find.text(S.typeCitizen), findsOneWidget);
    expect(find.text(S.typeHousehold), findsOneWidget);
    expect(find.text(S.typeBusiness), findsOneWidget);
    expect(find.text(S.alwaysIncluded), findsOneWidget);

    await tester.tap(find.byKey(const Key('type-citizen')));      // locked: nothing changes
    await tester.tap(find.byKey(const Key('type-business')));
    await tester.pump();
    expect(draft.withBusiness, isTrue);
    expect(draft.withHousehold, isFalse);                          // a business without a home is fine

    await tester.tap(find.byKey(const Key('type-household')));
    await tester.tap(find.byKey(const Key('type-business')));
    await tester.pump();
    expect(draft.withHousehold, isTrue);
    expect(draft.withBusiness, isFalse);
    expect(draft.places.map((p) => p.kind), ['household']);

    await tester.tap(find.text(S.next));
    expect(continued, same(draft));
  });
}
