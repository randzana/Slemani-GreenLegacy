import 'package:flutter/material.dart';

import '../api.dart';
import '../main.dart';
import '../strings.dart';
import '../theme.dart';
import 'home_screen.dart';

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
  final _name = TextEditingController();
  final _phone = TextEditingController();
  final _password = TextEditingController();
  bool _signUp = false;
  bool _busy = false;
  bool _obscurePassword = true;
  List<Map<String, dynamic>> _hoods = [];
  String? _hoodsUrl; // the address the neighbourhood list was last asked from
  int? _hood;
  late String? _notice = widget.notice;

  @override
  void initState() {
    super.initState();
    if (_server.text.isEmpty) {
      _server.text = S.serverHint;
    }
    // Neighbourhoods load when the person leaves the address field (submitting it does that too),
    // not on every keystroke: half a typed address is one failed request and error per character.
    _serverFocus.addListener(() {
      if (!_serverFocus.hasFocus && _signUp && _server.text != _hoodsUrl) _loadHoods();
    });
  }

  @override
  void dispose() {
    _server.dispose();
    _serverFocus.dispose();
    _name.dispose();
    _phone.dispose();
    _password.dispose();
    super.dispose();
  }

  Future<void> _loadHoods() async {
    final url = _server.text;
    _hoodsUrl = url;
    try {
      await Api.instance.setBaseUrl(url);
      final hoods = await Api.instance.neighbourhoods();
      // The address changed while this was loading: the answer (or the error) is for an old one.
      if (!mounted || _server.text != url) return;
      setState(() {
        _hoods = hoods;
        // another server can have other neighbourhoods; the dropdown needs its value in the list
        if (!hoods.any((h) => h['id'] == _hood)) _hood = null;
      });
    } catch (e) {
      if (!mounted || _server.text != url) return;
      _hoodsUrl = null; // leaving the field again retries, e.g. once the server is started
      showError(context, e);
    }
  }

  Future<void> _submit() async {
    final phone = _phone.text.trim();
    final pass = _password.text;
    if (phone.isEmpty || pass.isEmpty || (_signUp && _name.text.trim().isEmpty)) {
      showError(context, S.fillAllFields);
      return;
    }

    setState(() {
      _busy = true;
      _notice = null;
    });
    try {
      await Api.instance.setBaseUrl(_server.text);
      if (_signUp) {
        await Api.instance.signup(_name.text.trim(), phone, pass, _hood);
      } else {
        await Api.instance.login(phone, pass);
      }
      if (!mounted) return;
      Navigator.of(context).pushReplacement(MaterialPageRoute(builder: (_) => const HomeScreen()));
    } catch (e) {
      if (mounted) showError(context, e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
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
                  _signUp ? S.signUp : S.appName,
                  style: TextStyle(
                    fontSize: 26,
                    fontWeight: FontWeight.w800,
                    color: textColor,
                    letterSpacing: -0.5,
                  ),
                ),
                const SizedBox(height: 6),
                Text(
                  _signUp ? S.joinUs : S.welcomeBack,
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
                                if (_signUp) _loadHoods();
                              },
                            ),
                          ),
                        ),
                        const SizedBox(height: 16),

                        // Name (if sign up)
                        if (_signUp) ...[
                          TextField(
                            controller: _name,
                            decoration: const InputDecoration(
                              labelText: S.name,
                              prefixIcon: Icon(Icons.person_outline_rounded, color: kPrimaryGreen),
                            ),
                          ),
                          const SizedBox(height: 16),
                        ],

                        // Phone Number
                        TextField(
                          controller: _phone,
                          keyboardType: TextInputType.phone,
                          textDirection: TextDirection.ltr,
                          decoration: const InputDecoration(
                            labelText: S.phone,
                            prefixIcon: Icon(Icons.phone_outlined, color: kPrimaryGreen),
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

                        // Neighbourhood dropdown (if sign up)
                        if (_signUp) ...[
                          const SizedBox(height: 16),
                          DropdownButtonFormField<int>(
                            initialValue: _hood,
                            items: [
                              for (final h in _hoods)
                                DropdownMenuItem(value: h['id'] as int, child: Text(h['name'].toString())),
                            ],
                            onChanged: (v) => setState(() => _hood = v),
                            onTap: _hoods.isEmpty ? _loadHoods : null,
                            decoration: const InputDecoration(
                              labelText: S.neighbourhood,
                              prefixIcon: Icon(Icons.location_city_outlined, color: kPrimaryGreen),
                            ),
                          ),
                        ],
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
                        : Text(
                            _signUp ? S.signUp : S.signIn,
                            style: const TextStyle(fontSize: 17, fontWeight: FontWeight.bold),
                          ),
                  ),
                ),
                const SizedBox(height: 20),

                // Switch between Login and Sign up
                Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Text(
                      _signUp ? S.haveAccount : S.noAccount,
                      style: TextStyle(color: isDark ? Colors.grey : Colors.black54),
                    ),
                    const SizedBox(width: 8),
                    GestureDetector(
                      onTap: () {
                        setState(() => _signUp = !_signUp);
                        if (_signUp && _hoods.isEmpty) _loadHoods();
                      },
                      child: Text(
                        _signUp ? S.signIn : S.signUp,
                        style: const TextStyle(
                          color: kPrimaryGreen,
                          fontWeight: FontWeight.bold,
                          fontSize: 15,
                        ),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
