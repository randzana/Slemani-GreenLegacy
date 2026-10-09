import 'package:flutter/material.dart';

import '../../strings.dart';
import '../../theme.dart';
import 'profile_form_screen.dart';
import 'registration_draft.dart';

/// The first sign-up step: what is being registered. Everyone is a citizen; a household and a business
/// are optional additions, each checked by the municipality.
class AccountTypeScreen extends StatefulWidget {
  const AccountTypeScreen({super.key, required this.draft, this.onContinue});

  final RegistrationDraft draft;

  /// What "next" does; by default the form. Tests replace it.
  final void Function(BuildContext context, RegistrationDraft draft)? onContinue;

  @override
  State<AccountTypeScreen> createState() => _AccountTypeScreenState();
}

class _AccountTypeScreenState extends State<AccountTypeScreen> {
  RegistrationDraft get draft => widget.draft;

  void _next() {
    final go = widget.onContinue ??
        (context, draft) => Navigator.of(context)
            .push(MaterialPageRoute(builder: (_) => ProfileFormScreen(draft: draft)));
    go(context, draft);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text(S.signUp)),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(20),
          children: [
            const Text(S.whatToRegister, style: TextStyle(fontSize: 22, fontWeight: FontWeight.w800)),
            const SizedBox(height: 6),
            Text(S.whatToRegisterHint, style: TextStyle(color: Colors.grey.shade600)),
            const SizedBox(height: 20),
            const TypeCard(
              key: Key('type-citizen'),
              icon: Icons.person_rounded,
              title: S.typeCitizen,
              about: S.typeCitizenAbout,
              selected: true,
              locked: true,
            ),
            TypeCard(
              key: const Key('type-household'),
              icon: Icons.home_rounded,
              title: S.typeHousehold,
              about: S.typeHouseholdAbout,
              selected: draft.withHousehold,
              onTap: () => setState(() => draft.withHousehold = !draft.withHousehold),
            ),
            TypeCard(
              key: const Key('type-business'),
              icon: Icons.storefront_rounded,
              title: S.typeBusiness,
              about: S.typeBusinessAbout,
              selected: draft.withBusiness,
              onTap: () => setState(() => draft.withBusiness = !draft.withBusiness),
            ),
            const SizedBox(height: 20),
            ElevatedButton(
              onPressed: _next,
              style: ElevatedButton.styleFrom(
                backgroundColor: kPrimaryGreen,
                foregroundColor: Colors.white,
                minimumSize: const Size.fromHeight(54),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
              ),
              child: const Text(S.next, style: TextStyle(fontSize: 17, fontWeight: FontWeight.bold)),
            ),
          ],
        ),
      ),
    );
  }
}

/// One large card: icon, title, one line, and whether it is chosen.
class TypeCard extends StatelessWidget {
  const TypeCard({
    super.key,
    required this.icon,
    required this.title,
    required this.about,
    required this.selected,
    this.locked = false,
    this.onTap,
  });

  final IconData icon;
  final String title;
  final String about;
  final bool selected;
  final bool locked;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final border = selected ? kPrimaryGreen : Theme.of(context).dividerColor;
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Semantics(
        selected: selected,
        button: !locked,
        child: InkWell(
          onTap: locked ? null : onTap,
          borderRadius: BorderRadius.circular(18),
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 150),
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(18),
              border: Border.all(color: border, width: selected ? 2 : 1),
              color: selected ? kPrimaryGreen.withValues(alpha: 0.08) : null,
            ),
            child: Row(
              children: [
                CircleAvatar(
                  radius: 26,
                  backgroundColor: kPrimaryGreen.withValues(alpha: 0.15),
                  child: Icon(icon, color: kDarkGreen, size: 28),
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(title, style: const TextStyle(fontSize: 17, fontWeight: FontWeight.bold)),
                      const SizedBox(height: 4),
                      Text(about, style: TextStyle(color: Colors.grey.shade600, fontSize: 13)),
                    ],
                  ),
                ),
                const SizedBox(width: 8),
                locked
                    ? const Chip(label: Text(S.alwaysIncluded), visualDensity: VisualDensity.compact)
                    : Icon(selected ? Icons.check_circle_rounded : Icons.radio_button_unchecked_rounded,
                        color: selected ? kPrimaryGreen : Colors.grey),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
