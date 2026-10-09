import 'package:flutter/material.dart';

import '../api.dart';
import '../main.dart';
import '../strings.dart';
import '../theme.dart';
import 'registration/place_fields.dart';
import 'registration/registration_draft.dart';

/// Add the person's household or business after signing up, or change it. Changing what the
/// municipality checked sends it back to them; the server decides that and the screen says so.
/// Pops true once saved.
class PlaceEditScreen extends StatefulWidget {
  const PlaceEditScreen({super.key, required this.kind, this.existing});

  final String kind;
  final Map<String, dynamic>? existing;

  @override
  State<PlaceEditScreen> createState() => _PlaceEditScreenState();
}

class _PlaceEditScreenState extends State<PlaceEditScreen> {
  late final PlaceDraft _place =
      widget.existing != null ? PlaceDraft.fromServer(widget.existing!) : PlaceDraft(widget.kind);
  Map<String, String> _errors = {};
  bool _busy = false;

  Future<void> _save() async {
    setState(() {
      _busy = true;
      _errors = {};
    });
    try {
      // categories and the service area come from the server's sign-up settings
      if (Api.instance.config == null) await Api.instance.authConfig();
      final saved = await Api.instance.savePlace(widget.kind, _place.toJson());
      if (!mounted) return;
      final wasVerified = widget.existing?['verification_status'] == 'verified';
      final backToReview = wasVerified && saved['verification_status'] == 'pending';
      ScaffoldMessenger.of(context)
          .showSnackBar(SnackBar(content: Text(backToReview ? S.placeBackToReview : S.placeSaved)));
      Navigator.of(context).pop(true);
    } on ApiException catch (e) {
      if (!mounted) return;
      if (e.code == 'invalid_profile') setState(() => _errors = e.fields);
      showError(context, e);
    } catch (e) {
      if (mounted) showError(context, e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final reason = widget.existing?['rejection_reason'] as String?;
    return Scaffold(
      appBar: AppBar(title: Text(widget.kind == 'household' ? S.householdSection : S.businessSection)),
      body: SafeArea(
        child: FutureBuilder(
          // the category list needs the server's settings; they are usually loaded at sign-in
          future: Api.instance.config == null ? Api.instance.authConfig() : Future.value(Api.instance.config),
          builder: (context, snap) => ListView(
            padding: const EdgeInsets.all(16),
            children: [
              if (reason != null)
                Card(
                  color: red.withValues(alpha: 0.08),
                  child: ListTile(
                    leading: const Icon(Icons.info_outline_rounded, color: red),
                    title: Text(S.rejectedBecause(reason)),
                    subtitle: const Text(S.fixAndResend),
                  ),
                ),
              PlaceFields(place: _place, errors: _errors, onChanged: () => setState(() {})),
              const SizedBox(height: 20),
              ElevatedButton(
                onPressed: _busy ? null : _save,
                style: ElevatedButton.styleFrom(
                  backgroundColor: kPrimaryGreen,
                  foregroundColor: Colors.white,
                  minimumSize: const Size.fromHeight(52),
                ),
                child: const Text(S.save),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
