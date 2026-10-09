import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';

import 'package:camera/camera.dart' show XFile;
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

import 'google_auth.dart';
import 'strings.dart';

class ApiException implements Exception {
  ApiException(this.message, [this.code, this.details = const {}]);
  final String message;
  final String? code;

  /// The rest of the server's error body: retry_after, attempts_left, fields (one problem per form
  /// field, e.g. {"household.location": "outside_service_area"}) or can_link.
  final Map<String, dynamic> details;

  Map<String, String> get fields =>
      {for (final e in Map<String, dynamic>.from(details['fields'] ?? {}).entries) e.key: '${e.value}'};

  @override
  String toString() => message;
}

/// Talks to the Flask API on the laptop. One shared instance for the whole app.
class Api {
  Api._();
  static final Api instance = Api._();

  String baseUrl = S.serverHint;
  String? token;
  Map<String, dynamic>? user;

  /// What this server offers at sign-up (GET /auth/config), asked again whenever the address changes.
  Map<String, dynamic>? config;

  /// Set by main.dart: the server no longer accepts the saved token (expired, or the database was
  /// re-seeded), so the person goes back to the login screen with the server's message.
  void Function(String message)? onSignedOut;

  Future<void> load() async {
    final prefs = await SharedPreferences.getInstance();
    baseUrl = prefs.getString('baseUrl') ?? S.serverHint;
    // Only the first build's hotspot default is replaced. Anything else was typed and worked,
    // including the old localhost:5001 default, which is right on a Mac where AirPlay holds 5000.
    if (baseUrl == 'http://192.168.43.1:5000' || baseUrl == 'http://localhost:5000') {
      baseUrl = S.serverHint;
      await prefs.setString('baseUrl', baseUrl);
    }
    token = prefs.getString('token');
  }

  Future<void> setBaseUrl(String url) async {
    baseUrl = url.trim().replaceAll(RegExp(r'/+$'), '');
    if (!baseUrl.contains('://')) baseUrl = 'http://$baseUrl';
    (await SharedPreferences.getInstance()).setString('baseUrl', baseUrl);
  }

  Future<void> _saveToken(String? value) async {
    token = value;
    final prefs = await SharedPreferences.getInstance();
    value == null ? prefs.remove('token') : prefs.setString('token', value);
  }

  String fileUrl(String path) => '$baseUrl$path';

  Map<String, String> get _headers => {
        'Content-Type': 'application/json',
        if (token != null) 'Authorization': 'Bearer $token',
      };

  Uri _uri(String path) => Uri.parse('$baseUrl$path');

  dynamic _decode(http.Response res, {bool allowError = false}) {
    dynamic body;
    try {
      body = res.body.isEmpty ? null : jsonDecode(utf8.decode(res.bodyBytes));
    } catch (_) {
      body = null;
    }
    if (res.statusCode >= 400 && !(allowError && body is Map && body.containsKey('verdict'))) {
      final message = (body is Map ? (body['message'] ?? S.genericError) : S.genericError).toString();
      final code = body is Map ? body['error']?.toString() : null;
      final details = body is Map ? Map<String, dynamic>.from(body) : <String, dynamic>{};
      // Sign out once, and only for the token this request carried: the screens loading together
      // all get the same 401, and a slow answer for an old token must not log out a fresh login.
      if (res.statusCode == 401 &&
          code == 'unauthorized' &&
          token != null &&
          res.request?.headers['Authorization'] == 'Bearer $token') {
        _saveToken(null);
        user = null;
        onSignedOut?.call(message);
      }
      throw ApiException(message, code, details);
    }
    return body;
  }

  Future<T> _guard<T>(Future<T> Function() call) async {
    try {
      return await call().timeout(const Duration(seconds: 60));
    } on ApiException {
      rethrow;
    } on TimeoutException {
      throw ApiException(S.noServer);
    } catch (_) {
      throw ApiException(S.noServer);
    }
  }

  Future<dynamic> _get(String path) =>
      _guard(() async => _decode(await http.get(_uri(path), headers: _headers)));

  Future<dynamic> _post(String path, [Map<String, dynamic>? body]) => _guard(() async =>
      _decode(await http.post(_uri(path), headers: _headers, body: jsonEncode(body ?? {}))));

  // ---- auth
  Future<void> _signedIn(dynamic data) async {
    user = Map<String, dynamic>.from(data['user']);
    await _saveToken(data['token']);
  }

  Future<Map<String, dynamic>> authConfig() async {
    config = Map<String, dynamic>.from(await _get('/auth/config'));
    return config!;
  }

  /// [who] is an email or a phone number. Servers from before email accounts only read 'phone'.
  Future<void> login(String who, String password) async =>
      _signedIn(await _post('/auth/login', {'login': who, 'phone': who, 'password': password}));

  /// A new account. [emailToken] comes from [verifyEmailCode]; [household] and [business] are the
  /// optional places, as the server's field names.
  Future<void> signup({
    required String name,
    required String phone,
    required String password,
    required int? neighbourhoodId,
    String? emailToken,
    Map<String, dynamic>? household,
    Map<String, dynamic>? business,
  }) async =>
      _signedIn(await _post('/auth/signup', {
        'name': name,
        'phone': phone,
        'password': password,
        'neighbourhood_id': neighbourhoodId,
        if (emailToken != null) 'email_verification_token': emailToken,
        if (household != null) 'household': household,
        if (business != null) 'business': business,
      }));

  /// Sends a code to [email]: {expires_in, resend_in}. 429s carry retry_after.
  Future<Map<String, dynamic>> requestEmailCode(String email) async =>
      Map<String, dynamic>.from(await _post('/auth/otp/request', {'email': email}));

  /// {email_verification_token, expires_in, email_has_account}. otp_invalid carries attempts_left.
  Future<Map<String, dynamic>> verifyEmailCode(String email, String code) async =>
      Map<String, dynamic>.from(await _post('/auth/otp/verify', {'email': email, 'code': code}));

  /// Google's ID token to the server: {status: signed_in} (and the person is signed in), or
  /// {status: registration_required, google_signup_token, profile, email_has_account}.
  Future<Map<String, dynamic>> googleSignIn(String idToken) async {
    final data = Map<String, dynamic>.from(await _post('/auth/google', {'id_token': idToken}));
    if (data['status'] == 'signed_in') await _signedIn(data);
    return data;
  }

  Future<void> googleRegister({
    required String signupToken,
    required String name,
    required String phone,
    required int? neighbourhoodId,
    Map<String, dynamic>? household,
    Map<String, dynamic>? business,
  }) async =>
      _signedIn(await _post('/auth/google/register', {
        'google_signup_token': signupToken,
        'name': name,
        'phone': phone,
        'neighbourhood_id': neighbourhoodId,
        if (household != null) 'household': household,
        if (business != null) 'business': business,
      }));

  /// Adds Google to an existing account: its email or phone and its password.
  Future<void> googleLink(String signupToken, String who, String password) async => _signedIn(
      await _post('/auth/google/link', {'google_signup_token': signupToken, 'login': who, 'password': password}));

  /// Adds or changes the person's household or business ([kind]); returns it as saved.
  Future<Map<String, dynamic>> savePlace(String kind, Map<String, dynamic> fields) async =>
      Map<String, dynamic>.from(await _post('/me/places', {'kind': kind, ...fields}));

  Future<void> logout() async {
    await GoogleAuth.signOut();
    await _saveToken(null);
  }

  Future<List<Map<String, dynamic>>> neighbourhoods() async =>
      List<Map<String, dynamic>>.from(await _get('/neighbourhoods'));

  // ---- reports
  Future<List<Map<String, dynamic>>> reports() async =>
      List<Map<String, dynamic>>.from(await _get('/reports'));

  Future<Map<String, dynamic>> report(int id) async =>
      Map<String, dynamic>.from(await _get('/reports/$id'));

  static Future<http.MultipartFile> _upload(String field, XFile file, String name) async =>
      http.MultipartFile.fromBytes(field, await file.readAsBytes(), filename: name);

  /// A synthetic picture from the rehearsal server, for simulators without a camera.
  Future<Uint8List> simulatedPhoto(String path) => _guard(() async {
        final res = await http.get(_uri(path));
        if (res.statusCode != 200) throw ApiException(S.simulatorOff);
        return res.bodyBytes;
      });

  Future<Map<String, dynamic>> createReport(XFile photo, double lat, double lon) =>
      _guard(() async {
        final req = http.MultipartRequest('POST', _uri('/reports'))
          ..headers['Authorization'] = 'Bearer $token'
          ..fields['lat'] = '$lat'
          ..fields['lon'] = '$lon'
          ..files.add(await _upload('photo', photo, 'photo.jpg'));
        final res = await http.Response.fromStream(await req.send());
        return Map<String, dynamic>.from(_decode(res));
      });

  Future<Map<String, dynamic>> claim(int reportId) async =>
      Map<String, dynamic>.from(await _post('/reports/$reportId/claim'));

  Future<Map<String, dynamic>> cleanup(
          int reportId, int challengeId, List<XFile> frames, double lat, double lon) =>
      _guard(() async {
        final req = http.MultipartRequest('POST', _uri('/reports/$reportId/cleanup'))
          ..headers['Authorization'] = 'Bearer $token'
          ..fields['lat'] = '$lat'
          ..fields['lon'] = '$lon'
          ..fields['challenge_id'] = '$challengeId';
        for (var i = 0; i < frames.length; i++) {
          req.files.add(await _upload('frames', frames[i], 'frame$i.jpg'));
        }
        final res = await http.Response.fromStream(await req.send());
        return Map<String, dynamic>.from(_decode(res, allowError: true));
      });

  // ---- points shop + daily tasks
  Future<Map<String, dynamic>> rewards() async => Map<String, dynamic>.from(await _get('/rewards'));

  Future<Map<String, dynamic>> redeem(String code) async =>
      Map<String, dynamic>.from(await _post('/rewards/$code/redeem'));

  Future<Map<String, dynamic>> tasks() async => Map<String, dynamic>.from(await _get('/tasks'));

  Future<Map<String, dynamic>> claimTask(String code) async =>
      Map<String, dynamic>.from(await _post('/tasks/$code/claim'));

  // ---- people
  Future<Map<String, dynamic>> leaderboard() async =>
      Map<String, dynamic>.from(await _get('/leaderboard'));

  Future<Map<String, dynamic>> me() async {
    final data = Map<String, dynamic>.from(await _get('/me'));
    user = data;
    return data;
  }

  // ---- municipality pins & notifications
  Future<List<Map<String, dynamic>>> pins([String? category]) async {
    final query = category != null ? '?category=$category' : '';
    return List<Map<String, dynamic>>.from(await _get('/pins$query'));
  }

  Future<Map<String, dynamic>> pin(int id) async =>
      Map<String, dynamic>.from(await _get('/pins/$id'));

  Future<Map<String, dynamic>> registerPin(int id, {String? notes}) async =>
      Map<String, dynamic>.from(await _post('/pins/$id/register', {'notes': notes}));

  Future<Map<String, dynamic>> unregisterPin(int id) async =>
      Map<String, dynamic>.from(await _post('/pins/$id/unregister'));

  Future<List<Map<String, dynamic>>> notifications() async =>
      List<Map<String, dynamic>>.from(await _get('/notifications'));

  Future<void> markNotificationRead(int id) async =>
      await _post('/notifications/$id/read');

  // ---- trash bins & disposal verification
  Future<List<Map<String, dynamic>>> trashBins() async =>
      List<Map<String, dynamic>>.from(await _get('/bins'));

  Future<Map<String, dynamic>> verifyDisposal({
    XFile? photo,
    String? qrCode,
    double? lat,
    double? lon,
    String? notes,
  }) async {
    if (photo != null) {
      final req = http.MultipartRequest('POST', _uri('/bins/verify-disposal'))
        ..headers['Authorization'] = 'Bearer $token';
      if (lat != null) req.fields['lat'] = '$lat';
      if (lon != null) req.fields['lon'] = '$lon';
      if (qrCode != null && qrCode.isNotEmpty) req.fields['qr_code'] = qrCode;
      if (notes != null) req.fields['notes'] = notes;
      req.files.add(await _upload('photo', photo, 'photo.jpg'));
      final res = await http.Response.fromStream(await req.send());
      return Map<String, dynamic>.from(_decode(res));
    }
    return Map<String, dynamic>.from(await _post('/bins/verify-disposal', {
      if (qrCode != null && qrCode.isNotEmpty) 'qr_code': qrCode,
      if (lat != null) 'lat': lat,
      if (lon != null) 'lon': lon,
      if (notes != null) 'notes': notes,
    }));
  }
}

