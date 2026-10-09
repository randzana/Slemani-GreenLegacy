import 'package:flutter/services.dart';
import 'package:google_sign_in/google_sign_in.dart';

import 'api.dart';
import 'strings.dart';

/// Sign in with Google (google_sign_in 7). The phone only gets Google's ID token; the server checks it
/// and decides who the person is. The Web client ID comes from the server (/auth/config), because the
/// server address is chosen at runtime; on Android it makes Google issue the token for that server.
class GoogleAuth {
  GoogleAuth._();

  /// google_sign_in can be set up once per app run, so the client ID it was set up with is kept.
  static String? _setUpWith;

  /// The ID token of the Google account the person picks, or null when they close the chooser.
  static Future<String?> idToken(String serverClientId) async {
    final google = GoogleSignIn.instance;
    if (_setUpWith == null) {
      try {
        await google.initialize(serverClientId: serverClientId);
      } catch (_) {
        // e.g. iOS without GIDClientID in Info.plist (setup_ios.py adds it from GOOGLE_IOS_CLIENT_ID)
        throw ApiException(S.googleNotSetUp, 'google_not_set_up');
      }
      _setUpWith = serverClientId;
    } else if (_setUpWith != serverClientId) {
      throw ApiException(S.googleRestartApp, 'google_restart');   // another server, another Google client
    }
    if (!google.supportsAuthenticate()) throw ApiException(S.googleNotSetUp, 'google_not_set_up');
    try {
      final account = await google.authenticate();
      final token = account.authentication.idToken;
      if (token == null) throw ApiException(S.googleFailed, 'google_failed');
      return token;
    } on GoogleSignInException catch (e) {
      if (e.code == GoogleSignInExceptionCode.canceled) return null;
      // Android: no OAuth client for this package and signing key (setup_android.py says how)
      final notSetUp = e.code == GoogleSignInExceptionCode.clientConfigurationError ||
          e.code == GoogleSignInExceptionCode.providerConfigurationError;
      throw notSetUp ? ApiException(S.googleNotSetUp, 'google_not_set_up') : ApiException(S.googleFailed, 'google_failed');
    } on PlatformException catch (e) {
      // iOS without GIDClientID in Info.plist: "No active configuration. Make sure GIDClientID is set"
      final notSetUp = '${e.message}'.contains('GIDClientID') || '${e.message}'.contains('configuration');
      throw notSetUp ? ApiException(S.googleNotSetUp, 'google_not_set_up') : ApiException(S.googleFailed, 'google_failed');
    }
  }

  /// Leaving the app's account also leaves the Google account picked for it.
  static Future<void> signOut() async {
    if (_setUpWith == null) return;
    try {
      await GoogleSignIn.instance.signOut();
    } catch (_) {
      // signing out of the app must not fail because Google could not be told
    }
  }
}
