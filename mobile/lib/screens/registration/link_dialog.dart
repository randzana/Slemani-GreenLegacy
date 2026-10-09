import 'package:flutter/material.dart';

import '../../api.dart';
import '../../strings.dart';

/// Offers to add Google to the account that already has this email or phone. The account's password
/// is asked for: Google proves who the person is, the password proves the account is theirs.
/// True once linked (and signed in).
Future<bool> showLinkDialog(BuildContext context,
    {required String signupToken, required String login, required String message}) async {
  final who = TextEditingController(text: login);
  final password = TextEditingController();
  String? error;
  var busy = false;
  final linked = await showDialog<bool>(
    context: context,
    builder: (context) => StatefulBuilder(
      builder: (context, setState) => AlertDialog(
        title: const Text(S.linkTitle),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(message),
              const SizedBox(height: 12),
              TextField(
                controller: who,
                textDirection: TextDirection.ltr,
                decoration: const InputDecoration(labelText: S.loginField),
              ),
              TextField(
                controller: password,
                obscureText: true,
                textDirection: TextDirection.ltr,
                decoration: const InputDecoration(labelText: S.passwordOnly),
              ),
              if (error != null)
                Padding(
                  padding: const EdgeInsets.only(top: 10),
                  child: Text(error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
                ),
            ],
          ),
        ),
        actions: [
          TextButton(onPressed: busy ? null : () => Navigator.of(context).pop(false), child: const Text(S.cancel)),
          FilledButton(
            onPressed: busy
                ? null
                : () async {
                    setState(() {
                      busy = true;
                      error = null;
                    });
                    try {
                      await Api.instance.googleLink(signupToken, who.text.trim(), password.text);
                      if (context.mounted) Navigator.of(context).pop(true);
                    } on ApiException catch (e) {
                      setState(() {
                        error = e.message;
                        busy = false;
                      });
                    }
                  },
            child: const Text(S.link),
          ),
        ],
      ),
    ),
  );
  who.dispose();
  password.dispose();
  return linked ?? false;
}
