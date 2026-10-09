import 'package:flutter/material.dart';

import '../../api.dart';
import '../../main.dart';
import '../../strings.dart';
import '../../theme.dart';
import '../home_screen.dart';
import 'email_code_screen.dart';
import 'link_dialog.dart';
import 'place_fields.dart';
import 'registration_draft.dart';

/// The sign-up form: the person, then the household and the business they chose. With a password the
/// email is verified next and the account made; with Google (whose email is verified already) the
/// account is made straight away. The server's field problems come back next to their fields.
class ProfileFormScreen extends StatefulWidget {
  const ProfileFormScreen({super.key, required this.draft});

  final RegistrationDraft draft;

  @override
  State<ProfileFormScreen> createState() => _ProfileFormScreenState();
}

class _ProfileFormScreenState extends State<ProfileFormScreen> {
  RegistrationDraft get draft => widget.draft;
  late final _name = TextEditingController(text: draft.name);
  late final _phone = TextEditingController(text: draft.phone);
  late final _password = TextEditingController(text: draft.password);
  List<Map<String, dynamic>> _hoods = [];
  Map<String, String> _errors = {};
  bool _busy = false;
  bool _obscure = true;

  @override
  void initState() {
    super.initState();
    Api.instance.neighbourhoods().then((h) {
      if (mounted) setState(() => _hoods = h);
    }).catchError((Object e) {
      if (mounted) showError(context, e);
    });
  }

  @override
  void dispose() {
    _name.dispose();
    _phone.dispose();
    _password.dispose();
    super.dispose();
  }

  /// The obvious gaps, before asking the server (which checks everything again).
  Map<String, String> _gaps() => {
        if (draft.name.trim().isEmpty) 'name': 'required',
        if (draft.phone.trim().isEmpty) 'phone': 'required',
        if (!draft.viaGoogle && draft.password.length < 6) 'password': 'too_short',
        for (final p in draft.places) ...{
          if (p.name.trim().length < 2) '${p.kind}.name': p.name.trim().isEmpty ? 'required' : 'too_short',
          if (p.pin == null) '${p.kind}.location': 'required',
          if (!p.isHousehold && p.category == null) '${p.kind}.category': 'required',
        },
      };

  Future<void> _submit() async {
    final gaps = _gaps();
    setState(() => _errors = gaps);
    if (gaps.isNotEmpty) {
      showError(context, S.fillAllFields);
      return;
    }
    setState(() => _busy = true);
    try {
      final household = draft.withHousehold ? draft.household.toJson() : null;
      final business = draft.withBusiness ? draft.business.toJson() : null;
      if (draft.viaGoogle) {
        await Api.instance.googleRegister(
            signupToken: draft.googleSignupToken!,
            name: draft.name.trim(),
            phone: draft.phone.trim(),
            neighbourhoodId: draft.neighbourhoodId,
            household: household,
            business: business);
      } else {
        if (draft.emailToken == null) {
          final length = (Api.instance.config?['otp']?['length'] as num?)?.toInt() ?? 6;
          final token = await Navigator.of(context).push<String>(MaterialPageRoute(
              builder: (_) => EmailCodeScreen(
                    initialEmail: draft.email,
                    codeLength: length,
                    onVerified: (token, email) {
                      draft.email = email;
                      Navigator.of(context).pop(token);
                    },
                  )));
          if (token == null || !mounted) return;     // went back from the email step
          draft.emailToken = token;
        }
        await Api.instance.signup(
            name: draft.name.trim(),
            phone: draft.phone.trim(),
            password: draft.password,
            neighbourhoodId: draft.neighbourhoodId,
            emailToken: draft.emailToken,
            household: household,
            business: business);
      }
      if (!mounted) return;
      Navigator.of(context).pushAndRemoveUntil(MaterialPageRoute(builder: (_) => const HomeScreen()), (_) => false);
    } on ApiException catch (e) {
      if (mounted) await _failed(e);
    } catch (e) {
      if (mounted) showError(context, e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _failed(ApiException e) async {
    switch (e.code) {
      case 'invalid_profile':
        setState(() => _errors = e.fields);
      case 'invalid_phone' || 'phone_not_allowed':
        setState(() => _errors = {'phone': e.code!});
      case ('phone_taken' || 'email_taken') when e.details['can_link'] == true && draft.viaGoogle:
        // Google sign-up: the phone or email has an account already, so offer to link Google to it
        final viaPhone = e.code == 'phone_taken';
        final linked = await showLinkDialog(context,
            signupToken: draft.googleSignupToken!,
            login: viaPhone ? draft.phone.trim() : (draft.googleEmail ?? ''),
            message: viaPhone ? S.linkPhoneHasAccount : S.linkEmailHasAccount);
        if (linked && mounted) {
          Navigator.of(context).pushAndRemoveUntil(MaterialPageRoute(builder: (_) => const HomeScreen()), (_) => false);
        }
      case 'phone_taken':
        setState(() => _errors = {'phone': 'phone_taken'});
      case 'email_not_verified' || 'email_taken':
        draft.emailToken = null;     // the next try asks for the email again (a new code, or another email)
        showError(context, e);
      case 'google_signup_expired':
        showError(context, e);
        Navigator.of(context).popUntil((route) => route.isFirst);
      default:
        showError(context, e);
    }
  }

  Widget _section(String title, Widget child) => Card(
        margin: const EdgeInsets.only(bottom: 16),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text(title, style: const TextStyle(fontSize: 17, fontWeight: FontWeight.bold)),
              const SizedBox(height: 12),
              child,
            ],
          ),
        ),
      );

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text(S.signUp)),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            if (draft.googleEmail != null)
              Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: Row(children: [
                  const Icon(Icons.verified_rounded, color: kPrimaryGreen, size: 18),
                  const SizedBox(width: 6),
                  Expanded(child: Text(S.googleAccount(draft.googleEmail!))),
                ]),
              ),
            _section(
              S.yourDetails,
              Column(children: [
                TextField(
                  controller: _name,
                  onChanged: (v) => draft.name = v,
                  decoration: InputDecoration(
                    labelText: S.name,
                    prefixIcon: const Icon(Icons.person_outline_rounded, color: kPrimaryGreen),
                    errorText: S.fieldError(_errors['name']),
                  ),
                ),
                const SizedBox(height: 14),
                TextField(
                  controller: _phone,
                  onChanged: (v) => draft.phone = v,
                  keyboardType: TextInputType.phone,
                  autofillHints: const [AutofillHints.telephoneNumber],
                  textDirection: TextDirection.ltr,
                  decoration: InputDecoration(
                    labelText: S.phone,
                    prefixIcon: const Icon(Icons.phone_outlined, color: kPrimaryGreen),
                    errorText: S.fieldError(_errors['phone']),
                  ),
                ),
                if (!draft.viaGoogle) ...[
                  const SizedBox(height: 14),
                  TextField(
                    controller: _password,
                    onChanged: (v) => draft.password = v,
                    obscureText: _obscure,
                    autofillHints: const [AutofillHints.newPassword],
                    textDirection: TextDirection.ltr,
                    decoration: InputDecoration(
                      labelText: S.password,
                      prefixIcon: const Icon(Icons.lock_outline_rounded, color: kPrimaryGreen),
                      errorText: S.fieldError(_errors['password']),
                      suffixIcon: IconButton(
                        icon: Icon(_obscure ? Icons.visibility_outlined : Icons.visibility_off_outlined),
                        onPressed: () => setState(() => _obscure = !_obscure),
                      ),
                    ),
                  ),
                ],
                const SizedBox(height: 14),
                DropdownButtonFormField<int>(
                  initialValue: _hoods.any((h) => h['id'] == draft.neighbourhoodId) ? draft.neighbourhoodId : null,
                  items: [
                    for (final h in _hoods) DropdownMenuItem(value: h['id'] as int, child: Text('${h['name']}')),
                  ],
                  onChanged: (v) => setState(() => draft.neighbourhoodId = v),
                  decoration: InputDecoration(
                    labelText: S.neighbourhood,
                    prefixIcon: const Icon(Icons.location_city_outlined, color: kPrimaryGreen),
                    errorText: S.fieldError(_errors['neighbourhood_id']),
                  ),
                ),
              ]),
            ),
            if (draft.withHousehold)
              _section(S.householdSection,
                  PlaceFields(place: draft.household, errors: _errors, onChanged: () => setState(() {}))),
            if (draft.withBusiness)
              _section(S.businessSection,
                  PlaceFields(place: draft.business, errors: _errors, onChanged: () => setState(() {}))),
            ElevatedButton(
              onPressed: _busy ? null : _submit,
              style: ElevatedButton.styleFrom(
                backgroundColor: kPrimaryGreen,
                foregroundColor: Colors.white,
                minimumSize: const Size.fromHeight(54),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
              ),
              child: _busy
                  ? const SizedBox(
                      width: 24, height: 24, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2.5))
                  : Text(draft.viaGoogle ? S.createAccount : S.next,
                      style: const TextStyle(fontSize: 17, fontWeight: FontWeight.bold)),
            ),
          ],
        ),
      ),
    );
  }
}
