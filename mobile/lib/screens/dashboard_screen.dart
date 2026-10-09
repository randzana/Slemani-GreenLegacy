import 'package:flutter/material.dart';

import '../api.dart';
import '../notification_service.dart';
import '../strings.dart';
import '../theme.dart';
import 'daily_tasks_card.dart';
import 'rewards_screen.dart';
import 'spot_detail_screen.dart';

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({
    super.key,
    required this.onOpenMap,
    required this.onOpenReport,
    required this.onOpenLeague,
    required this.onOpenGarden,
    required this.refresh,
  });

  final VoidCallback onOpenMap;
  final VoidCallback onOpenReport;
  final VoidCallback onOpenLeague;
  final VoidCallback onOpenGarden;
  final ValueNotifier<int> refresh;

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  Map<String, dynamic>? _user;
  List<Map<String, dynamic>> _reports = [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
    widget.refresh.addListener(_load);
  }

  @override
  void dispose() {
    widget.refresh.removeListener(_load);
    super.dispose();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final me = await Api.instance.me();
      final reports = await Api.instance.reports();
      NotificationService.instance.refresh();
      if (mounted) {
        setState(() {
          _user = me;
          _reports = reports;
          _loading = false;
        });
      }
    } catch (_) {
      if (mounted) setState(() => _loading = false);
    }
  }

  void _showNotifications() {
    NotificationService.instance.refresh();
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
      builder: (ctx) => ValueListenableBuilder<List<Map<String, dynamic>>>(
        valueListenable: NotificationService.instance.notifications,
        builder: (ctx, notifs, _) => DraggableScrollableSheet(
          expand: false,
          initialChildSize: 0.65,
          maxChildSize: 0.9,
          minChildSize: 0.4,
          builder: (ctx, scroll) => Padding(
            padding: const EdgeInsets.fromLTRB(20, 16, 20, 20),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Center(
                  child: Container(width: 40, height: 4, decoration: BoxDecoration(color: Colors.grey.shade300, borderRadius: BorderRadius.circular(2))),
                ),
                const SizedBox(height: 16),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    const Text(S.notifications, style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                    Text('${S.digits(notifs.length)} ${S.notifications}', style: TextStyle(color: Colors.grey.shade600, fontSize: 13)),
                  ],
                ),
                const SizedBox(height: 14),
                Expanded(
                  child: notifs.isEmpty
                      ? Center(
                          child: Column(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Icon(Icons.notifications_none_rounded, size: 54, color: Colors.grey.shade400),
                              const SizedBox(height: 10),
                              Text(S.notificationsEmpty, style: TextStyle(color: Colors.grey.shade600)),
                            ],
                          ),
                        )
                      : ListView.separated(
                          controller: scroll,
                          itemCount: notifs.length,
                          separatorBuilder: (_, __) => const SizedBox(height: 10),
                          itemBuilder: (_, i) {
                            final n = notifs[i];
                            final isUnread = n['is_read'] != true;
                            final cat = n['category']?.toString() ?? '';
                            final isTree = cat == 'tree_planting';
                            final isWater = cat == 'watering_point';
                            final icon = isTree ? Icons.park_rounded : (isWater ? Icons.water_drop_rounded : Icons.warning_amber_rounded);
                            final iconColor = isTree ? kPrimaryGreen : (isWater ? Colors.blue : Colors.orange.shade800);
                            return Card(
                              elevation: 0,
                              color: isUnread ? iconColor.withValues(alpha: 0.06) : null,
                              shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(14),
                                side: BorderSide(
                                  color: isUnread ? iconColor.withValues(alpha: 0.4) : Colors.grey.shade200,
                                  width: isUnread ? 1.5 : 1.0,
                                ),
                              ),
                              child: ListTile(
                                onTap: () {
                                  if (n['id'] != null) {
                                    NotificationService.instance.markRead(n['id'] as int);
                                  }
                                  if (n['lat'] != null) {
                                    Navigator.pop(ctx);
                                    widget.onOpenMap();
                                  }
                                },
                                leading: Stack(
                                  clipBehavior: Clip.none,
                                  children: [
                                    CircleAvatar(backgroundColor: iconColor.withValues(alpha: 0.15), child: Icon(icon, color: iconColor)),
                                    if (isUnread)
                                      Positioned(
                                        top: -2,
                                        right: -2,
                                        child: Container(
                                          width: 10,
                                          height: 10,
                                          decoration: BoxDecoration(
                                            color: Colors.red,
                                            shape: BoxShape.circle,
                                            border: Border.all(color: Colors.white, width: 2),
                                          ),
                                        ),
                                      ),
                                  ],
                                ),
                                title: Text(n['title']?.toString() ?? '', style: TextStyle(fontWeight: isUnread ? FontWeight.bold : FontWeight.w600, fontSize: 14)),
                                subtitle: Text(n['message']?.toString() ?? '', style: TextStyle(color: Colors.grey.shade700, fontSize: 12)),
                                trailing: n['lat'] != null
                                    ? IconButton(
                                        icon: const Icon(Icons.map_rounded, color: kPrimaryGreen),
                                        onPressed: () {
                                          if (n['id'] != null) {
                                            NotificationService.instance.markRead(n['id'] as int);
                                          }
                                          Navigator.pop(ctx);
                                          widget.onOpenMap();
                                        },
                                      )
                                    : null,
                              ),
                            );
                          },
                        ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }



  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final textColor = isDark ? kTextDark : kTextLight;
    final cardColor = Theme.of(context).cardColor;

    final name = _user?['name']?.toString() ?? S.citizen;
    final points = ((_user?['earned'] ?? _user?['released']) as num?)?.toInt() ?? 0;
    final pending = (_user?['pending'] as num?)?.toInt() ?? 0;
    final totalPoints = points + pending;

    double progress = (totalPoints / 200).clamp(0.0, 1.0);
    int nextGoal = 200;
    if (totalPoints >= 1000) {
      progress = 1.0;
      nextGoal = 1000;
    } else if (totalPoints >= 500) {
      progress = ((totalPoints - 500) / 500).clamp(0.0, 1.0);
      nextGoal = 1000;
    } else if (totalPoints >= 200) {
      progress = ((totalPoints - 200) / 300).clamp(0.0, 1.0);
      nextGoal = 500;
    }

    return RefreshIndicator(
      onRefresh: _load,
      child: SingleChildScrollView(
        physics: const AlwaysScrollableScrollPhysics(),
        child: Column(
          children: [
            // Top Header Container
            Container(
              padding: const EdgeInsets.fromLTRB(20, 20, 20, 26),
              decoration: BoxDecoration(
                color: cardColor,
                borderRadius: const BorderRadius.vertical(bottom: Radius.circular(28)),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withValues(alpha: isDark ? 0.4 : 0.06),
                    blurRadius: 12,
                    offset: const Offset(0, 4),
                  ),
                ],
              ),
              child: Column(
                children: [
                  // Greeting & Streak & Notification Bell
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            S.hello(name),
                            style: TextStyle(color: Colors.grey.shade600, fontSize: 15),
                          ),
                          const SizedBox(height: 2),
                          Text(
                            S.letsGoGreen,
                            style: TextStyle(
                              color: textColor,
                              fontSize: 22,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ],
                      ),
                      Row(
                        children: [
                          ValueListenableBuilder<int>(
                            valueListenable: NotificationService.instance.unreadCount,
                            builder: (context, unread, _) {
                              return Stack(
                                children: [
                                  IconButton(
                                    icon: const Icon(Icons.notifications_none_rounded, size: 26),
                                    color: kPrimaryGreen,
                                    onPressed: _showNotifications,
                                  ),
                                  if (unread > 0)
                                    Positioned(
                                      right: 6,
                                      top: 6,
                                      child: Container(
                                        padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 2),
                                        decoration: BoxDecoration(
                                          color: Colors.red,
                                          borderRadius: BorderRadius.circular(10),
                                        ),
                                        constraints: const BoxConstraints(minWidth: 16, minHeight: 16),
                                        child: Text(
                                          unread > 9 ? '9+' : '$unread',
                                          style: const TextStyle(
                                            color: Colors.white,
                                            fontSize: 9,
                                            fontWeight: FontWeight.bold,
                                          ),
                                          textAlign: TextAlign.center,
                                        ),
                                      ),
                                    ),
                                ],
                              );
                            },
                          ),
                          const SizedBox(width: 4),
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                            decoration: BoxDecoration(
                              color: Colors.orange.withValues(alpha: 0.12),
                              borderRadius: BorderRadius.circular(16),
                            ),
                            child: Row(
                              children: [
                                const Icon(Icons.local_fire_department_rounded, color: Colors.orange, size: 22),
                                const SizedBox(width: 4),
                                Text(
                                  S.digits(_reports.where((r) => r['status'] == 'clean').length),
                                  style: const TextStyle(fontWeight: FontWeight.bold, color: Colors.deepOrange, fontSize: 15),
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                  const SizedBox(height: 20),

                  // Eco-Points Card (Emerald Gradient)
                  Container(
                    width: double.infinity,
                    padding: const EdgeInsets.all(20),
                    decoration: BoxDecoration(
                      gradient: const LinearGradient(
                        colors: [kPrimaryGreen, kAccentTeal],
                        begin: Alignment.topLeft,
                        end: Alignment.bottomRight,
                      ),
                      borderRadius: BorderRadius.circular(20),
                      boxShadow: [
                        BoxShadow(
                          color: kPrimaryGreen.withValues(alpha: 0.38),
                          blurRadius: 14,
                          spreadRadius: 1,
                          offset: const Offset(0, 8),
                        ),
                      ],
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Text(
                              S.totalGreenPoints,
                              style: TextStyle(color: Colors.white70, fontSize: 14, fontWeight: FontWeight.w600),
                            ),
                            Icon(Icons.eco_rounded, color: Colors.white70, size: 24),
                          ],
                        ),
                        const SizedBox(height: 8),
                        Text(
                          '${S.digits(totalPoints)} ${S.points}',
                          style: const TextStyle(
                            color: Colors.white,
                            fontSize: 32,
                            fontWeight: FontWeight.w900,
                            letterSpacing: -0.5,
                          ),
                        ),
                        const SizedBox(height: 14),
                        Align(
                          alignment: AlignmentDirectional.centerEnd,
                          child: Text(
                            '${S.digits(totalPoints)} / ${S.digits(nextGoal)}',
                            style: const TextStyle(color: Colors.white70, fontSize: 12),
                          ),
                        ),
                        const SizedBox(height: 8),
                        ClipRRect(
                          borderRadius: BorderRadius.circular(8),
                          child: LinearProgressIndicator(
                            value: progress,
                            minHeight: 8,
                            backgroundColor: Colors.white.withValues(alpha: 0.25),
                            valueColor: const AlwaysStoppedAnimation<Color>(Colors.white),
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 20),

            // Quick Actions & Live Highlights
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 18),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Live Map Action Banner
                  GestureDetector(
                    onTap: widget.onOpenMap,
                    child: Container(
                      width: double.infinity,
                      padding: const EdgeInsets.all(18),
                      decoration: BoxDecoration(
                        gradient: const LinearGradient(
                          colors: [Color(0xFF1E88E5), Color(0xFF42A5F5)],
                          begin: Alignment.topLeft,
                          end: Alignment.bottomRight,
                        ),
                        borderRadius: BorderRadius.circular(18),
                        boxShadow: [
                          BoxShadow(
                            color: const Color(0xFF1E88E5).withValues(alpha: 0.32),
                            blurRadius: 10,
                            offset: const Offset(0, 6),
                          ),
                        ],
                      ),
                      child: Row(
                        children: [
                          Container(
                            padding: const EdgeInsets.all(10),
                            decoration: BoxDecoration(
                              color: Colors.white.withValues(alpha: 0.2),
                              borderRadius: BorderRadius.circular(12),
                            ),
                            child: const Icon(Icons.map_rounded, color: Colors.white, size: 28),
                          ),
                          const SizedBox(width: 14),
                          const Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  S.liveMap,
                                  style: TextStyle(color: Colors.white, fontSize: 17, fontWeight: FontWeight.bold),
                                ),
                                SizedBox(height: 2),
                                Text(
                                  S.liveMapHint,
                                  style: TextStyle(color: Colors.white70, fontSize: 12),
                                ),
                              ],
                            ),
                          ),
                          const Icon(Icons.arrow_forward_ios_rounded, color: Colors.white70, size: 18),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 16),

                  // Neighbourhood Rankings Banner (ڕیزبەندی گەڕەکەکان)
                  GestureDetector(
                    onTap: widget.onOpenLeague,
                    child: Container(
                      width: double.infinity,
                      padding: const EdgeInsets.all(16),
                      decoration: BoxDecoration(
                        gradient: const LinearGradient(
                          colors: [Color(0xFFD97706), Color(0xFFF59E0B)],
                          begin: Alignment.topLeft,
                          end: Alignment.bottomRight,
                        ),
                        borderRadius: BorderRadius.circular(18),
                        boxShadow: [
                          BoxShadow(
                            color: const Color(0xFFD97706).withValues(alpha: 0.32),
                            blurRadius: 10,
                            offset: const Offset(0, 6),
                          ),
                        ],
                      ),
                      child: Row(
                        children: [
                          Container(
                            padding: const EdgeInsets.all(10),
                            decoration: BoxDecoration(
                              color: Colors.white.withValues(alpha: 0.2),
                              borderRadius: BorderRadius.circular(12),
                            ),
                            child: const Icon(Icons.emoji_events_rounded, color: Colors.white, size: 28),
                          ),
                          const SizedBox(width: 14),
                          const Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  'ڕیزبەندی گەڕەکەکان',
                                  style: TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.bold),
                                ),
                                SizedBox(height: 2),
                                Text(
                                  'کێبڕکێی گەڕەکە سەوزەکان و خاوێنترین شوێنەکانی سلێمانی',
                                  style: TextStyle(color: Colors.white70, fontSize: 12),
                                ),
                              ],
                            ),
                          ),
                          const Icon(Icons.arrow_forward_ios_rounded, color: Colors.white70, size: 18),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 16),

                  // Quick Stats 2x2 Grid
                  Row(
                    children: [
                      Expanded(
                        child: _StatCard(
                          title: S.openReports,
                          value: S.digits(_reports.where((r) => r['status'] == 'open').length),
                          icon: Icons.delete_outline_rounded,
                          color: kStatusOpen,
                          onTap: widget.onOpenMap,
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: _StatCard(
                          title: S.cleanedSpots,
                          value: S.digits(_reports.where((r) => r['status'] == 'clean').length),
                          icon: Icons.check_circle_outline_rounded,
                          color: kPrimaryGreen,
                          onTap: widget.onOpenMap,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      Expanded(
                        child: _StatCard(
                          title: S.league,
                          value: S.ranking,
                          icon: Icons.emoji_events_rounded,
                          color: Colors.amber.shade800,
                          onTap: widget.onOpenLeague,
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: _StatCard(
                          title: S.pendingTotal,
                          value: S.digits(pending),
                          icon: Icons.hourglass_top_rounded,
                          color: Colors.deepPurpleAccent,
                          onTap: () => Navigator.of(context)
                              .push(MaterialPageRoute(builder: (_) => const RewardsScreen()))
                              .then((_) => widget.refresh.value++),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 24),
                  DailyTasksCard(refresh: widget.refresh),



                  // Recent Reports Header
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      const Text(
                        S.recentReports,
                        style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                      ),
                      TextButton(
                        onPressed: widget.onOpenMap,
                        child: const Text(S.wholeMap, style: TextStyle(color: kPrimaryGreen)),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),

                  if (_loading)
                    const Center(child: Padding(padding: EdgeInsets.all(24), child: CircularProgressIndicator()))
                  else if (_reports.isEmpty)
                    Card(
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                      child: const Padding(
                        padding: EdgeInsets.all(24),
                        child: Center(
                          child: Column(
                            children: [
                              Icon(Icons.park_rounded, size: 48, color: kPrimaryGreen),
                              SizedBox(height: 8),
                              Text(S.allClean),
                            ],
                          ),
                        ),
                      ),
                    )
                  else
                    for (final spot in _reports.take(5))
                      Padding(
                        padding: const EdgeInsets.only(bottom: 10),
                        child: Card(
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                          child: ListTile(
                            contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
                            leading: Container(
                              width: 44,
                              height: 44,
                              decoration: BoxDecoration(
                                color: statusColour(spot['status']?.toString() ?? '').withValues(alpha: 0.12),
                                borderRadius: BorderRadius.circular(12),
                              ),
                              child: Icon(
                                Icons.location_on_rounded,
                                color: statusColour(spot['status']?.toString() ?? ''),
                              ),
                            ),
                            title: Text(
                              S.reportNo(spot['id']),
                              style: const TextStyle(fontWeight: FontWeight.bold),
                            ),
                            subtitle: Text(
                              S.spotSummary(spot['litter_count'], spot['dirtiness']),
                              style: TextStyle(color: Colors.grey.shade600, fontSize: 13),
                            ),
                            trailing: Container(
                              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                              decoration: BoxDecoration(
                                color: statusColour(spot['status']?.toString() ?? '').withValues(alpha: 0.12),
                                borderRadius: BorderRadius.circular(10),
                              ),
                              child: Text(
                                S.reportStatuses[spot['status']] ?? spot['status']?.toString() ?? '',
                                style: TextStyle(
                                  color: statusColour(spot['status']?.toString() ?? ''),
                                  fontWeight: FontWeight.bold,
                                  fontSize: 12,
                                ),
                              ),
                            ),
                            onTap: () async {
                              await Navigator.of(context).push(
                                MaterialPageRoute(
                                  builder: (_) => SpotDetailScreen(reportId: spot['id'] as int),
                                ),
                              );
                              widget.refresh.value++; // a cleanup may have changed points and spots
                            },
                          ),
                        ),
                      ),
                  const SizedBox(height: 80),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _StatCard extends StatelessWidget {
  const _StatCard({
    required this.title,
    required this.value,
    required this.icon,
    required this.color,
    required this.onTap,
  });

  final String title;
  final String value;
  final IconData icon;
  final Color color;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Card(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: color.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Icon(icon, color: color, size: 22),
              ),
              const SizedBox(height: 12),
              Text(
                value,
                style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold, color: color),
              ),
              const SizedBox(height: 2),
              Text(
                title,
                style: TextStyle(color: Colors.grey.shade600, fontSize: 12),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
