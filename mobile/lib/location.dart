import 'package:geolocator/geolocator.dart';

import 'api.dart';
import 'strings.dart';

/// The phone's current position, asking for permission when needed.
Future<Position> currentPosition() async {
  if (!await Geolocator.isLocationServiceEnabled()) {
    throw ApiException(S.locationDenied);
  }
  var permission = await Geolocator.checkPermission();
  if (permission == LocationPermission.denied) {
    permission = await Geolocator.requestPermission();
  }
  if (permission == LocationPermission.denied || permission == LocationPermission.deniedForever) {
    throw ApiException(S.locationDenied);
  }
  try {
    return await Geolocator.getCurrentPosition(
      locationSettings: const LocationSettings(accuracy: LocationAccuracy.high, timeLimit: Duration(seconds: 20)),
    );
  } catch (_) {
    // e.g. the iOS Simulator with Features > Location set to None
    throw ApiException(S.locationUnavailable);
  }
}
