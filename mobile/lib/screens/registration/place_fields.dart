import 'package:flutter/material.dart';

import '../../api.dart';
import '../../strings.dart';
import '../../theme.dart';
import 'location_picker_screen.dart';
import 'registration_draft.dart';

/// The fields of a household or a business. [errors] holds one problem code per field, keyed as the
/// server names them ("household.name", "business.location", ...).
class PlaceFields extends StatefulWidget {
  const PlaceFields({super.key, required this.place, required this.errors, required this.onChanged});

  final PlaceDraft place;
  final Map<String, String> errors;
  final VoidCallback onChanged;

  @override
  State<PlaceFields> createState() => _PlaceFieldsState();
}

class _PlaceFieldsState extends State<PlaceFields> {
  late final _name = TextEditingController(text: widget.place.name);
  late final _address = TextEditingController(text: widget.place.address);
  late final _license = TextEditingController(text: widget.place.license);

  PlaceDraft get place => widget.place;
  String? _error(String field) => S.fieldError(widget.errors['${place.kind}.$field']);

  @override
  void dispose() {
    _name.dispose();
    _address.dispose();
    _license.dispose();
    super.dispose();
  }

  void _changed(VoidCallback update) {
    setState(update);
    widget.onChanged();
  }

  Future<void> _pickLocation() async {
    final pin = await Navigator.of(context).push(MaterialPageRoute(
      builder: (_) => LocationPickerScreen(
        initial: place.pin,
        note: place.isHousehold ? S.householdPrivacyNote : S.businessLocationNote,
      ),
    ));
    if (pin != null) _changed(() => place.pin = pin);
  }

  @override
  Widget build(BuildContext context) {
    final categories = List<Map<String, dynamic>>.from(Api.instance.config?['business_categories'] ?? const []);
    final locationError = _error('location');
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        TextField(
          controller: _name,
          onChanged: (v) => _changed(() => place.name = v),
          decoration: InputDecoration(
            labelText: place.isHousehold ? S.householdName : S.businessName,
            prefixIcon: Icon(place.isHousehold ? Icons.home_outlined : Icons.storefront_outlined, color: kPrimaryGreen),
            errorText: _error('name'),
          ),
        ),
        const SizedBox(height: 14),
        if (place.isHousehold)
          InputDecorator(
            decoration: InputDecoration(
              labelText: S.residents,
              prefixIcon: const Icon(Icons.groups_outlined, color: kPrimaryGreen),
              errorText: _error('residents_count'),
            ),
            child: Row(
              children: [
                IconButton(
                  icon: const Icon(Icons.remove_circle_outline),
                  onPressed: place.residents > 1 ? () => _changed(() => place.residents--) : null,
                ),
                Text(S.digits(place.residents), style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                IconButton(
                  icon: const Icon(Icons.add_circle_outline),
                  onPressed: place.residents < 30 ? () => _changed(() => place.residents++) : null,
                ),
              ],
            ),
          )
        else ...[
          DropdownButtonFormField<String>(
            initialValue: categories.any((c) => c['code'] == place.category) ? place.category : null,
            items: [
              for (final c in categories)
                DropdownMenuItem(value: c['code'] as String, child: Text('${c['name']}')),
            ],
            onChanged: (v) => _changed(() => place.category = v),
            decoration: InputDecoration(
              labelText: S.category,
              prefixIcon: const Icon(Icons.category_outlined, color: kPrimaryGreen),
              errorText: _error('category'),
            ),
          ),
          const SizedBox(height: 14),
          TextField(
            controller: _license,
            textDirection: TextDirection.ltr,
            onChanged: (v) => _changed(() => place.license = v),
            decoration: InputDecoration(
              labelText: S.license,
              prefixIcon: const Icon(Icons.badge_outlined, color: kPrimaryGreen),
              errorText: _error('license_number'),
            ),
          ),
        ],
        const SizedBox(height: 14),
        TextField(
          controller: _address,
          onChanged: (v) => _changed(() => place.address = v),
          decoration: InputDecoration(
            labelText: S.address,
            prefixIcon: const Icon(Icons.signpost_outlined, color: kPrimaryGreen),
            errorText: _error('address'),
          ),
        ),
        const SizedBox(height: 14),
        OutlinedButton.icon(
          onPressed: _pickLocation,
          icon: Icon(place.pin == null ? Icons.add_location_alt_outlined : Icons.where_to_vote_rounded,
              color: locationError != null ? Theme.of(context).colorScheme.error : kPrimaryGreen),
          label: Text(place.pin == null ? S.chooseOnMap : S.locationChosen),
          style: OutlinedButton.styleFrom(
            minimumSize: const Size.fromHeight(48),
            side: BorderSide(color: locationError != null ? Theme.of(context).colorScheme.error : kPrimaryGreen),
          ),
        ),
        if (locationError != null)
          Padding(
            padding: const EdgeInsets.only(top: 6, right: 12),
            child: Text(locationError,
                style: TextStyle(color: Theme.of(context).colorScheme.error, fontSize: 12)),
          ),
        const SizedBox(height: 8),
        Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(place.isHousehold ? Icons.lock_outline_rounded : Icons.info_outline_rounded,
                size: 16, color: Colors.grey.shade600),
            const SizedBox(width: 6),
            Expanded(
              child: Text(place.isHousehold ? S.householdPrivacyNote : S.businessLocationNote,
                  style: TextStyle(color: Colors.grey.shade600, fontSize: 12)),
            ),
          ],
        ),
      ],
    );
  }
}
