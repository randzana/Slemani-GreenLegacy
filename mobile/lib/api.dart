import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';

import 'package:camera/camera.dart' show XFile;
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

import 'strings.dart';

class ApiException implements Exception {
  ApiException(this.message, [this.code]);
  final String message;
  final String? code;

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

  Future<void> load() async {
    final prefs = await SharedPreferences.getInstance();
    baseUrl = prefs.getString('baseUrl') ?? S.serverHint;
    if (baseUrl == 'http://192.168.43.1:5000') {
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
      final message = body is Map ? (body['message'] ?? S.genericError) : S.genericError;
      throw ApiException(message.toString(), body is Map ? body['error']?.toString() : null);
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
  Future<void> login(String phone, String password) async {
    final data = await _post('/auth/login', {'phone': phone, 'password': password});
    user = Map<String, dynamic>.from(data['user']);
    await _saveToken(data['token']);
  }

  Future<void> signup(String name, String phone, String password, int? neighbourhoodId) async {
    final data = await _post('/auth/signup', {
      'name': name,
      'phone': phone,
      'password': password,
      'neighbourhood_id': neighbourhoodId,
    });
    user = Map<String, dynamic>.from(data['user']);
    await _saveToken(data['token']);
  }

  Future<void> logout() => _saveToken(null);

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
}
