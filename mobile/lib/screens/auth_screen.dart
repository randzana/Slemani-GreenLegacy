import 'package:flutter/material.dart';

import '../api.dart';
import '../google_auth.dart';
import '../main.dart';
import '../strings.dart';
import '../theme.dart';
import 'home_screen.dart';
import 'registration/account_type_screen.dart';
import 'registration/link_dialog.dart';
import 'registration/registration_draft.dart';

class AuthScreen extends StatefulWidget {
  const AuthScreen({super.key, this.notice});

  /// Why the person was sent back here (the server's message when a saved login stopped working).
  final String? notice;

  @override
  State<AuthScreen> createState() => _AuthScreenState();
}

class _AuthScreenState extends State<AuthScreen> {
  final _server = TextEditingController(text: Api.instance.baseUrl);
  final _serverFocus = FocusNode();
  final _login = TextEditingController();
  final _password = TextEditingController();
  bool _busy = false;
  bool _obscurePassword = true;
  String? _configUrl; // the address the sign-up settings were last asked from
  late String? _notice = widget.notice;

  /// This server offers Google sign-in (its /auth/config says so). Hidden when it is off or unknown.
  bool get _googleOn => Api.instance.config?['google']?['enabled'] == true;

  @override
  void initState() {
    super.initState();
    if (_server.text.isEmpty) {
      _server.text = S.serverHint;
    }
    // The server's settings load when the person leaves the address field (submitting it does that
    // too), not on every keystroke: half a typed address is one failed request per character.
    _serverFocus.addListener(() {
      if (!_serverFocus.hasFocus && _server.text != _configUrl) _loadConfig();
    });
    _loadConfig();
  }

  @override
  void dispose() {
    _server.dispose();
    _serverFocus.dispose();
    _login.dispose();
    _password.dispose();
    super.dispose();
  }

  /// Quietly: a server from before accounts had settings, or one not started yet, just has no Google
  /// button; signing in still says what is wrong.
  Future<void> _loadConfig() async {
    final url = _server.text;
    _configUrl = url;
    try {
      await Api.instance.setBaseUrl(url);
      await Api.instance.authConfig();
    } catch (_) {
      Api.instance.config = null;
      _configUrl = null; // leaving the field again retries, e.g. once the server is started
    }
    if (mounted && _server.text == url) setState(() {});
  }

  Future<T?> _working<T>(Future<T> Function() job) async {
    setState(() {
      _busy = true;
      _notice = null;
    });
    try {
      await Api.instance.setBaseUrl(_server.text);
      return await job();
    } catch (e) {
      if (mounted) showError(context, e);
      return null;
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  void _goHome() =>
      Navigator.of(context).pushAndRemoveUntil(MaterialPageRoute(builder: (_) => const HomeScreen()), (_) => false);

  Future<void> _submit() async {
    final who = _login.text.trim();
    if (who.isEmpty || _password.text.isEmpty) {
      showError(context, S.fillAllFields);
      return;
    }
    final ok = await _working(() async {
      await Api.instance.login(who, _password.text);
      return true;
    });
    if (ok == true && mounted) _goHome();
  }

  /// A new account: what is registered, the form, then the email code (app/registration/).
  Future<void> _signUp([RegistrationDraft? draft]) async {
    await Api.instance.setBaseUrl(_server.text);
    if (!mounted) return;
    if (Api.instance.config == null) {
      Api.instance.authConfig().catchError((_) => <String, dynamic>{});
    }
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => AccountTypeScreen(draft: draft ?? RegistrationDraft()),
      ),
    );
  }

  /// Google: a known account signs straight in; a new one either links to the account its email
  /// already has (with that account's password), or signs up with Google's verified email.
  Future<void> _google() async {
    final answer = await _working(() async {
      final config = await Api.instance.authConfig();
      final clientId = config['google']?['server_client_id'] as String?;
      if (clientId == null) throw ApiException(S.googleNotSetUp, 'google_not_set_up');
      final idToken = await GoogleAuth.idToken(clientId);
      return idToken == null ? null : Api.instance.googleSignIn(idToken);
    });
    if (answer == null || !mounted) return;
    if (answer['status'] == 'signed_in') return _goHome();
    final profile = Map<String, dynamic>.from(answer['profile'] ?? {});
    final token = answer['google_signup_token'] as String;
    if (answer['email_has_account'] == true) {
      final linked = await showLinkDialog(context,
          signupToken: token, login: '${profile['email'] ?? ''}', message: S.linkEmailHasAccount);
      if (linked && mounted) _goHome();
      return;
    }
    Navigator.of(context).push(MaterialPageRoute(
        builder: (_) => AccountTypeScreen(
            draft: RegistrationDraft()
              ..googleSignupToken = token
              ..googleEmail = profile['email'] as String?
              ..name = '${profile['name'] ?? ''}')));
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final textColor = isDark ? kTextDark : kTextLight;

    return Scaffold(
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.symmetric(horizontal: 28, vertical: 24),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                // Top Brand Icon with glowing aura
                Container(
                  padding: const EdgeInsets.all(20),
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: kPrimaryGreen.withValues(alpha: 0.12),
                    boxShadow: [
                      BoxShadow(
                        color: kPrimaryGreen.withValues(alpha: 0.2),
                        blurRadius: 24,
                        spreadRadius: 2,
                        offset: const Offset(0, 8),
                      ),
                    ],
                  ),
                  child: const Icon(Icons.eco_rounded, size: 68, color: kPrimaryGreen),
                ),
                const SizedBox(height: 20),
                Text(
                  S.appName,
                  style: TextStyle(
                    fontSize: 26,
                    fontWeight: FontWeight.w800,
                    color: textColor,
                    letterSpacing: -0.5,
                  ),
                ),
                const SizedBox(height: 6),
                Text(
                  S.welcomeBack,
                  textAlign: TextAlign.center,
                  style: TextStyle(color: Colors.grey.shade600, fontSize: 14),
                ),
                const SizedBox(height: 32),

                // Why the person is here again (their saved login stopped working)
                if (_notice != null) ...[
                  Container(
                    width: double.infinity,
                    padding: const EdgeInsets.all(14),
                    decoration: BoxDecoration(
                      color: Colors.orange.withValues(alpha: 0.12),
                      borderRadius: BorderRadius.circular(14),
                      border: Border.all(color: Colors.orange.withValues(alpha: 0.5)),
                    ),
                    child: Row(
                      children: [
                        const Icon(Icons.info_outline_rounded, color: Colors.orange),
                        const SizedBox(width: 10),
                        Expanded(
                          child: Text(_notice!, style: TextStyle(color: textColor, fontSize: 14)),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 16),
                ],

                // Form Fields Card Container
                Card(
                  elevation: 3,
                  shadowColor: Colors.black.withValues(alpha: isDark ? 0.4 : 0.08),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
                  child: Padding(
                    padding: const EdgeInsets.all(20),
                    child: Column(
                      children: [
                        // Server URL
                        TextField(
                          controller: _server,
                          focusNode: _serverFocus,
                          keyboardType: TextInputType.url,
                          textDirection: TextDirection.ltr,
                          decoration: InputDecoration(
                            labelText: S.server,
                            helperText: S.serverHelp,
                            helperMaxLines: 4,
                            prefixIcon: const Icon(Icons.dns_outlined, color: kPrimaryGreen),
                            suffixIcon: IconButton(
                              icon: const Icon(Icons.refresh_rounded, color: kPrimaryGreen),
                              tooltip: S.serverHint,
                              onPressed: () {
                                _server.text = S.serverHint;
                                _loadConfig();
                              },
                            ),
                          ),
                        ),
                        const SizedBox(height: 16),

                        // Email or phone (accounts from before emails log in with the phone)
                        TextField(
                          controller: _login,
                          keyboardType: TextInputType.emailAddress,
                          autofillHints: const [AutofillHints.email, AutofillHints.telephoneNumber],
                          textDirection: TextDirection.ltr,
                          decoration: const InputDecoration(
                            labelText: S.loginField,
                            prefixIcon: Icon(Icons.alternate_email_rounded, color: kPrimaryGreen),
                          ),
                        ),
                        const SizedBox(height: 16),

                        // Password
                        TextField(
                          controller: _password,
                          obscureText: _obscurePassword,
                          textDirection: TextDirection.ltr,
                          decoration: InputDecoration(
                            labelText: S.password,
                            prefixIcon: const Icon(Icons.lock_outline_rounded, color: kPrimaryGreen),
                            suffixIcon: IconButton(
                              icon: Icon(
                                _obscurePassword ? Icons.visibility_outlined : Icons.visibility_off_outlined,
                                color: Colors.grey.shade600,
                              ),
                              onPressed: () => setState(() => _obscurePassword = !_obscurePassword),
                            ),
                          ),
                        ),

                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 24),

                // Main Submit Button (ElevatedButton styled like Zanko-GreenLegacy)
                SizedBox(
                  width: double.infinity,
                  height: 54,
                  child: ElevatedButton(
                    onPressed: _busy ? null : _submit,
                    style: ElevatedButton.styleFrom(
                      backgroundColor: kPrimaryGreen,
                      foregroundColor: Colors.white,
                      elevation: 4,
                      shadowColor: kPrimaryGreen.withValues(alpha: 0.5),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                    ),
                    child: _busy
                        ? const SizedBox(
                            width: 24,
                            height: 24,
                            child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2.5),
                          )
                        : const Text(
                            S.signIn,
                            style: TextStyle(fontSize: 17, fontWeight: FontWeight.bold),
                          ),
                  ),
                ),

                // Google, when this server offers it
                if (_googleOn) ...[
                  const SizedBox(height: 16),
                  Row(children: [
                    const Expanded(child: Divider()),
                    Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 12),
                      child: Text(S.or, style: TextStyle(color: Colors.grey.shade600)),
                    ),
                    const Expanded(child: Divider()),
                  ]),
                  const SizedBox(height: 16),
                  SizedBox(
                    width: double.infinity,
                    height: 52,
                    child: OutlinedButton.icon(
                      key: const Key('google'),
                      onPressed: _busy ? null : _google,
                      icon: const Icon(Icons.g_mobiledata_rounded, size: 32),
                      label: const Text(S.continueWithGoogle, style: TextStyle(fontSize: 16)),
                      style: OutlinedButton.styleFrom(
                        foregroundColor: textColor,
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                      ),
                    ),
                  ),
                ],
                const SizedBox(height: 20),

                // Switch between Login and Sign up
                Center(
                  child: InkWell(
                    key: const Key('switch-to-signup'),
                    onTap: _busy ? null : () => _signUp(),
                    borderRadius: BorderRadius.circular(12),
                    child: Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Text(
                            S.noAccount,
                            style: TextStyle(color: isDark ? Colors.grey : Colors.black54, fontSize: 15),
                          ),
                          const SizedBox(width: 8),
                          const Text(
                            S.signUp,
                            style: TextStyle(
                              color: kPrimaryGreen,
                              fontWeight: FontWeight.bold,
                              fontSize: 15,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
