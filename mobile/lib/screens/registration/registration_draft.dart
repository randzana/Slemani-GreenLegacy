import 'package:latlong2/latlong.dart';

/// A household or a business as it is being filled in (sign-up, or changed later from the profile).
class PlaceDraft {
  PlaceDraft(this.kind);

  /// The place as /me returns it, to change it.
  factory PlaceDraft.fromServer(Map<String, dynamic> p) => PlaceDraft(p['kind'] as String)
    ..name = (p['name'] ?? '') as String
    ..address = (p['address'] ?? '') as String
    ..residents = (p['residents_count'] ?? 1) as int
    ..category = p['category'] as String?
    ..license = (p['license_number'] ?? '') as String
    ..pin = LatLng((p['lat'] as num).toDouble(), (p['lon'] as num).toDouble());

  final String kind;
  String name = '';
  String address = '';
  int residents = 1;
  String? category;
  String license = '';
  LatLng? pin;

  bool get isHousehold => kind == 'household';

  /// The server's field names. Its neighbourhood is worked out on the server, from the pin.
  Map<String, dynamic> toJson() => {
        'name': name.trim(),
        if (address.trim().isNotEmpty) 'address': address.trim(),
        if (isHousehold) 'residents_count': residents,
        if (!isHousehold) 'category': category,
        if (!isHousehold && license.trim().isNotEmpty) 'license_number': license.trim(),
        'lat': pin?.latitude,
        'lon': pin?.longitude,
      };
}

/// Everything the sign-up screens collect, handed from one to the next. Only in memory: it survives
/// switching to the mail app for the code, and nothing half-typed is left on the phone.
class RegistrationDraft {
  bool withHousehold = false;
  bool withBusiness = false;
  final household = PlaceDraft('household');
  final business = PlaceDraft('business');

  String name = '';
  String phone = '';
  String password = '';
  int? neighbourhoodId;

  /// Signing up with a password: the step token from the email code, and that email.
  String? emailToken;
  String email = '';

  /// Signing up with Google: the step token from /auth/google, and Google's (verified) email.
  String? googleSignupToken;
  String? googleEmail;

  bool get viaGoogle => googleSignupToken != null;
  List<PlaceDraft> get places => [if (withHousehold) household, if (withBusiness) business];
}
