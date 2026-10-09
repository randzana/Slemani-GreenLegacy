import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../api.dart';
import '../../strings.dart';
import '../../theme.dart';

/// Proves the person reads the mailbox: an email, a code sent to it, the code typed back. Pops with
/// the server's email_verification_token (or calls [onVerified]).
///
/// The wait before another code comes from the server (resend_in, or retry_after on a 429), not from
/// a number in the app. The UI branches on error codes only, and shows the server's Kurdish message.
class EmailCodeScreen extends StatefulWidget {
  const EmailCodeScreen({
    super.key,
    this.initialEmail = '',
    this.codeLength = 6,
    this.requestCode,
    this.verifyCode,
    this.onVerified,
  });

  final String initialEmail;
  final int codeLength;

  /// Stand-ins for the API in tests; by default Api.instance.
  final Future<Map<String, dynamic>> Function(String email)? requestCode;
  final Future<Map<String, dynamic>> Function(String email, String code)? verifyCode;
  final void Function(String token, String email)? onVerified;

  @override
  State<EmailCodeScreen> createState() => _EmailCodeScreenState();
}

class _EmailCodeScreenState extends State<EmailCodeScreen> {
  late final _email = TextEditingController(text: widget.initialEmail);
  final _code = TextEditingController();
  Timer? _timer;
  bool _sent = false;
  bool _busy = false;
  bool _needNewCode = false;   // the code is used up (too many tries) or expired
  int _wait = 0;
  int? _attemptsLeft;
  String? _error;

  @override
  void dispose() {
    _timer?.cancel();
    _email.dispose();
    _code.dispose();
    super.dispose();
  }

  void _countDown(Object? seconds) {
    _timer?.cancel();
    setState(() => _wait = seconds is num ? seconds.ceil() : 0);
    if (_wait <= 0) return;
    _timer = Timer.periodic(const Duration(seconds: 1), (t) {
      if (!mounted) return;
      setState(() => _wait--);
      if (_wait <= 0) t.cancel();
    });
  }

  Future<void> _send() async {
    final email = _email.text.trim();
    if (email.isEmpty) return setState(() => _error = S.fieldError('required'));
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final answer = await (widget.requestCode ?? Api.instance.requestEmailCode)(email);
      if (!mounted) return;
      setState(() {
        _sent = true;
        _needNewCode = false;
        _attemptsLeft = null;
        _code.clear();
      });
      _countDown(answer['resend_in']);
    } on ApiException catch (e) {
      if (!mounted) return;
      setState(() => _error = e.message);
      if (e.code == 'otp_too_soon' || e.code == 'otp_rate_limited') {
        // a code went out a moment ago (another tap, or before going back): it can still be typed
        if (e.code == 'otp_too_soon') setState(() => _sent = true);
        _countDown(e.details['retry_after']);
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _verify() async {
    final email = _email.text.trim();
    final code = _code.text.trim();
    if (code.length != widget.codeLength) return setState(() => _error = S.fieldError('invalid'));
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final answer = await (widget.verifyCode ?? Api.instance.verifyEmailCode)(email, code);
      if (!mounted) return;
      final token = answer['email_verification_token'] as String;
      final done = widget.onVerified ?? (token, _) => Navigator.of(context).pop(token);
      done(token, email);
    } on ApiException catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e.message;
        _code.clear();
        if (e.code == 'otp_invalid') _attemptsLeft = (e.details['attempts_left'] as num?)?.toInt();
        if (e.code == 'otp_invalid' && _attemptsLeft == 0) _needNewCode = true;
        if (e.code == 'otp_locked' || e.code == 'otp_expired') _needNewCode = true;
      });
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final email = _email.text.trim();
    return Scaffold(
      appBar: AppBar(title: const Text(S.emailTitle)),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(20),
          children: [
            Text(S.emailWhy, style: TextStyle(color: Colors.grey.shade600)),
            const SizedBox(height: 16),
            TextField(
              key: const Key('email'),
              controller: _email,
              enabled: !_sent,
              keyboardType: TextInputType.emailAddress,
              autofillHints: const [AutofillHints.email],
              textDirection: TextDirection.ltr,
              decoration: const InputDecoration(
                labelText: S.email,
                prefixIcon: Icon(Icons.alternate_email_rounded, color: kPrimaryGreen),
              ),
            ),
            if (_sent)
              Align(
                alignment: AlignmentDirectional.centerStart,
                child: TextButton(
                  onPressed: _busy
                      ? null
                      : () => setState(() {
                            _sent = false;
                            _error = null;
                          }),
                  child: const Text(S.changeEmail),
                ),
              ),
            const SizedBox(height: 12),
            if (!_sent)
              ElevatedButton(
                key: const Key('send'),
                onPressed: _busy || _wait > 0 ? null : _send,
                style: ElevatedButton.styleFrom(
                    backgroundColor: kPrimaryGreen,
                    foregroundColor: Colors.white,
                    minimumSize: const Size.fromHeight(50)),
                child: const Text(S.sendCode),
              )
            else ...[
              Text(S.codeSent(email, widget.codeLength), style: const TextStyle(fontWeight: FontWeight.w600)),
              Text(S.checkSpam, style: TextStyle(color: Colors.grey.shade600, fontSize: 12)),
              const SizedBox(height: 14),
              TextField(
                key: const Key('code'),
                controller: _code,
                enabled: !_needNewCode,
                autofocus: true,
                keyboardType: TextInputType.number,
                autofillHints: const [AutofillHints.oneTimeCode],
                inputFormatters: [FilteringTextInputFormatter.digitsOnly],
                maxLength: widget.codeLength,
                textAlign: TextAlign.center,
                textDirection: TextDirection.ltr,
                style: const TextStyle(fontSize: 26, letterSpacing: 10, fontWeight: FontWeight.bold),
                decoration: const InputDecoration(labelText: S.code, counterText: ''),
                onSubmitted: (_) => _verify(),
              ),
              if (_attemptsLeft != null && !_needNewCode)
                Text(S.attemptsLeft(_attemptsLeft!), style: const TextStyle(color: amber)),
              const SizedBox(height: 12),
              ElevatedButton(
                key: const Key('verify'),
                onPressed: _busy || _needNewCode ? null : _verify,
                style: ElevatedButton.styleFrom(
                    backgroundColor: kPrimaryGreen,
                    foregroundColor: Colors.white,
                    minimumSize: const Size.fromHeight(50)),
                child: const Text(S.verify),
              ),
              const SizedBox(height: 8),
              TextButton(
                key: const Key('resend'),
                onPressed: _busy || _wait > 0 ? null : _send,
                child: Text(_needNewCode ? S.requestNewCode : S.resend),
              ),
            ],
            if (_wait > 0)
              Text(S.resendIn(_wait), textAlign: TextAlign.center, style: TextStyle(color: Colors.grey.shade600)),
            if (_error != null)
              Padding(
                padding: const EdgeInsets.only(top: 12),
                child: Text(_error!,
                    key: const Key('error'),
                    textAlign: TextAlign.center,
                    style: TextStyle(color: Theme.of(context).colorScheme.error, fontWeight: FontWeight.w600)),
              ),
          ],
        ),
      ),
    );
  }
}
