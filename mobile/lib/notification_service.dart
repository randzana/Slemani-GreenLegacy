import 'dart:async';
import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'api.dart';

/// Central background notification service that polls for municipality alerts
/// and broadcasts both native system notifications (Lock Screen / Notification Center)
/// and in-app events.
class NotificationService {
  NotificationService._();
  static final NotificationService instance = NotificationService._();

  final ValueNotifier<List<Map<String, dynamic>>> notifications =
      ValueNotifier<List<Map<String, dynamic>>>([]);
  final ValueNotifier<int> unreadCount = ValueNotifier<int>(0);

  final StreamController<Map<String, dynamic>> _newNotificationController =
      StreamController<Map<String, dynamic>>.broadcast();

  Stream<Map<String, dynamic>> get onNewNotification =>
      _newNotificationController.stream;

  final FlutterLocalNotificationsPlugin _localNotifs =
      FlutterLocalNotificationsPlugin();

  Timer? _timer;
  int? _lastSeenId;
  bool _initialized = false;

  Future<void> init() async {
    if (_initialized) return;
    _initialized = true;

    await _initLocalNotifications();

    final prefs = await SharedPreferences.getInstance();
    _lastSeenId = prefs.getInt('last_seen_notif_id');

    // Initial check
    await checkNotifications();

    // Poll every 5 seconds for real-time responsiveness
    _timer?.cancel();
    _timer = Timer.periodic(const Duration(seconds: 5), (_) => checkNotifications());
  }

  Future<void> _initLocalNotifications() async {
    try {
      const initializationSettingsDarwin = DarwinInitializationSettings(
        requestAlertPermission: true,
        requestBadgePermission: true,
        requestSoundPermission: true,
      );
      const initializationSettingsAndroid =
          AndroidInitializationSettings('@mipmap/ic_launcher');
      const initializationSettings = InitializationSettings(
        iOS: initializationSettingsDarwin,
        macOS: initializationSettingsDarwin,
        android: initializationSettingsAndroid,
      );

      await _localNotifs.initialize(
        settings: initializationSettings,
      );

      await _localNotifs
          .resolvePlatformSpecificImplementation<
              IOSFlutterLocalNotificationsPlugin>()
          ?.requestPermissions(
            alert: true,
            badge: true,
            sound: true,
          );
    } catch (e) {
      debugPrint('Local notifications init error: $e');
    }
  }

  Future<void> _showSystemNotification(Map<String, dynamic> notif) async {
    try {
      final id = (notif['id'] as int? ?? 1) % 100000;
      final title = notif['title']?.toString() ?? 'ئاگاداریی نوێ';
      final body = notif['message']?.toString() ?? '';

      const darwinDetails = DarwinNotificationDetails(
        presentAlert: true,
        presentBadge: true,
        presentSound: true,
        interruptionLevel: InterruptionLevel.active,
      );
      const androidDetails = AndroidNotificationDetails(
        'green_legacy_channel',
        'ئاگادارییەکانی شارەوانی',
        channelDescription: 'ئاگادارییەکانی پاراستنی ژینگە و نەمام ناشتن',
        importance: Importance.max,
        priority: Priority.high,
        showWhen: true,
      );
      const details = NotificationDetails(
        iOS: darwinDetails,
        android: androidDetails,
      );

      await _localNotifs.show(
        id: id,
        title: title,
        body: body,
        notificationDetails: details,
      );
    } catch (e) {
      debugPrint('Error showing system notification: $e');
    }
  }

  Future<void> checkNotifications() async {
    if (Api.instance.token == null) return;

    try {
      final list = await Api.instance.notifications();
      notifications.value = list;

      final unread = list.where((n) => n['is_read'] != true).length;
      unreadCount.value = unread;

      if (list.isNotEmpty) {
        final newest = list.first;
        final newestId = newest['id'] as int? ?? 0;

        if (_lastSeenId == null) {
          // First time tracking: remember newest id and alert if unread
          final prefs = await SharedPreferences.getInstance();
          await prefs.setInt('last_seen_notif_id', newestId);
          _lastSeenId = newestId;
          if (newest['is_read'] != true) {
            HapticFeedback.heavyImpact();
            _newNotificationController.add(newest);
            await _showSystemNotification(newest);
          }
        } else if (newestId > _lastSeenId!) {
          // New notification detected! Broadcast it for banner display and system notification
          debugPrint('🔔 [NotificationService] New notification: $newestId - ${newest['title']}');
          HapticFeedback.heavyImpact();
          _newNotificationController.add(newest);
          await _showSystemNotification(newest);

          final prefs = await SharedPreferences.getInstance();
          await prefs.setInt('last_seen_notif_id', newestId);
          _lastSeenId = newestId;
        }
      }
    } catch (_) {
      // Ignore network failures during poll
    }
  }

  /// Forces an immediate poll check
  Future<void> refresh() => checkNotifications();

  Future<void> markRead(int id) async {
    try {
      await Api.instance.markNotificationRead(id);
      final updated = notifications.value.map((n) {
        if (n['id'] == id) {
          final copy = Map<String, dynamic>.from(n);
          copy['is_read'] = true;
          return copy;
        }
        return n;
      }).toList();
      notifications.value = updated;
      unreadCount.value = updated.where((n) => n['is_read'] != true).length;
    } catch (_) {}
  }

  void dispose() {
    _timer?.cancel();
  }
}
