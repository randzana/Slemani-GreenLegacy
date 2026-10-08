import 'package:flutter/material.dart';

import '../api.dart';
import '../data/plant_data.dart';
import '../strings.dart';
import '../theme.dart';
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
    GardenManager.instance.init();
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

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final textColor = isDark ? kTextDark : kTextLight;
    final cardColor = Theme.of(context).cardColor;

    final name = _user?['name']?.toString() ?? 'هاوڵاتی';
    final points = (_user?['released'] as num?)?.toInt() ?? 0;
    final pending = (_user?['pending'] as num?)?.toInt() ?? 0;
    final totalPoints = points + pending;

    // Eco levels
    String levelName = 'شینەوار (تۆو)';
    double progress = (totalPoints / 200).clamp(0.0, 1.0);
    int nextGoal = 200;
    if (totalPoints >= 1000) {
      levelName = 'پارێزەری زەوی 🌍';
      progress = 1.0;
      nextGoal = 1000;
    } else if (totalPoints >= 500) {
      levelName = 'مامۆستای ژینگە 🌿';
      progress = ((totalPoints - 500) / 500).clamp(0.0, 1.0);
      nextGoal = 1000;
    } else if (totalPoints >= 200) {
      levelName = 'شەڕڤانی سەوز 🌲';
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
                  // Greeting & Streak
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'سڵاو، $name 👋',
                            style: TextStyle(color: Colors.grey.shade600, fontSize: 15),
                          ),
                          const SizedBox(height: 2),
                          Text(
                            'با سلێمانی سەوز بکەین!',
                            style: TextStyle(
                              color: textColor,
                              fontSize: 22,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ],
                      ),
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
                              'کۆی خاڵە سەوزەکان',
                              style: TextStyle(color: Colors.white70, fontSize: 14, fontWeight: FontWeight.w600),
                            ),
                            Icon(Icons.eco_rounded, color: Colors.white70, size: 24),
                          ],
                        ),
                        const SizedBox(height: 8),
                        Text(
                          '${S.digits(totalPoints)} خاڵ',
                          style: const TextStyle(
                            color: Colors.white,
                            fontSize: 32,
                            fontWeight: FontWeight.w900,
                            letterSpacing: -0.5,
                          ),
                        ),
                        const SizedBox(height: 14),
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Text(
                              'ئاست: $levelName',
                              style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 13),
                            ),
                            Text(
                              '${S.digits(totalPoints)} / ${S.digits(nextGoal)}',
                              style: const TextStyle(color: Colors.white70, fontSize: 12),
                            ),
                          ],
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
                                  'نەخشەی ڕاستەوخۆی شار',
                                  style: TextStyle(color: Colors.white, fontSize: 17, fontWeight: FontWeight.bold),
                                ),
                                SizedBox(height: 2),
                                Text(
                                  'شوێنە پیسەکان و پاککردنەوە ببینە',
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
                          title: 'ڕاپۆرتە کراوەکان',
                          value: S.digits(_reports.where((r) => r['status'] == 'open').length),
                          icon: Icons.delete_outline_rounded,
                          color: kStatusOpen,
                          onTap: widget.onOpenMap,
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: _StatCard(
                          title: 'پاککراوەکان',
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
                          title: 'لیگی گەڕەکەکان',
                          value: 'پلەبەندی',
                          icon: Icons.emoji_events_rounded,
                          color: Colors.amber.shade800,
                          onTap: widget.onOpenLeague,
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: _StatCard(
                          title: 'خاڵی چاوەڕوانکراو',
                          value: S.digits(pending),
                          icon: Icons.hourglass_top_rounded,
                          color: Colors.deepPurpleAccent,
                          onTap: () {},
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 24),

                  // Digital Garden Preview
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Row(
                        children: [
                          const Text(
                            'باخچەی دیجیتاڵیی من 🌱',
                            style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                          ),
                          const SizedBox(width: 8),
                          AnimatedBuilder(
                            animation: GardenManager.instance,
                            builder: (context, _) => Container(
                              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                              decoration: BoxDecoration(
                                color: kPrimaryGreen.withValues(alpha: 0.12),
                                borderRadius: BorderRadius.circular(8),
                              ),
                              child: Text(
                                '${S.digits(GardenManager.instance.myPlants.length)} ڕووەک',
                                style: const TextStyle(
                                  color: kPrimaryGreen,
                                  fontSize: 11,
                                  fontWeight: FontWeight.bold,
                                ),
                              ),
                            ),
                          ),
                        ],
                      ),
                      TextButton(
                        onPressed: widget.onOpenGarden,
                        child: const Text('بینینی باخچە', style: TextStyle(color: kPrimaryGreen, fontWeight: FontWeight.bold)),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  AnimatedBuilder(
                    animation: GardenManager.instance,
                    builder: (context, _) {
                      final plants = GardenManager.instance.myPlants;
                      if (plants.isEmpty) {
                        return Container(
                          padding: const EdgeInsets.all(16),
                          decoration: BoxDecoration(
                            color: isDark ? kDarkCard : Colors.white,
                            borderRadius: BorderRadius.circular(16),
                          ),
                          child: Row(
                            children: [
                              const Icon(Icons.eco_outlined, color: kPrimaryGreen, size: 28),
                              const SizedBox(width: 12),
                              const Expanded(
                                child: Text('باخچەکەت بەتاڵە! دەست بکە بە ناشتنی یەکەم درەخت.'),
                              ),
                              ElevatedButton(
                                onPressed: widget.onOpenGarden,
                                style: ElevatedButton.styleFrom(
                                  backgroundColor: kPrimaryGreen,
                                  foregroundColor: Colors.white,
                                  minimumSize: Size.zero,
                                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                                ),
                                child: const Text('ناشتن 🌱', style: TextStyle(fontSize: 12)),
                              ),
                            ],
                          ),
                        );
                      }
                      return SizedBox(
                        height: 128,
                        child: ListView.separated(
                          scrollDirection: Axis.horizontal,
                          itemCount: plants.length,
                          separatorBuilder: (_, __) => const SizedBox(width: 12),
                          itemBuilder: (context, index) {
                            final p = plants[index];
                            final color = Color(p['colorValue'] as int? ?? kPrimaryGreen.toARGB32());
                            final icon = plantIcon(p['iconCode']);
                            final needsWater = p['status'] == 'پێویستی بە ئاوە';

                            return GestureDetector(
                              onTap: widget.onOpenGarden,
                              child: Container(
                                width: 110,
                                padding: const EdgeInsets.all(10),
                                decoration: BoxDecoration(
                                  color: isDark ? kDarkCard : Colors.white,
                                  borderRadius: BorderRadius.circular(16),
                                  border: needsWater ? Border.all(color: Colors.orange.withValues(alpha: 0.6)) : null,
                                  boxShadow: [
                                    BoxShadow(
                                      color: Colors.black.withValues(alpha: isDark ? 0.3 : 0.05),
                                      blurRadius: 6,
                                      offset: const Offset(0, 2),
                                    ),
                                  ],
                                ),
                                child: Column(
                                  mainAxisAlignment: MainAxisAlignment.center,
                                  children: [
                                    Stack(
                                      clipBehavior: Clip.none,
                                      children: [
                                        CircleAvatar(
                                          radius: 24,
                                          backgroundColor: color.withValues(alpha: 0.12),
                                          child: Icon(icon, color: color, size: 26),
                                        ),
                                        if (needsWater)
                                          const Positioned(
                                            top: -2,
                                            right: -2,
                                            child: CircleAvatar(
                                              radius: 7,
                                              backgroundColor: Colors.orange,
                                              child: Icon(Icons.water_drop, size: 9, color: Colors.white),
                                            ),
                                          ),
                                      ],
                                    ),
                                    const SizedBox(height: 8),
                                    Text(
                                      p['name']?.toString() ?? '',
                                      maxLines: 1,
                                      overflow: TextOverflow.ellipsis,
                                      textAlign: TextAlign.center,
                                      style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 12),
                                    ),
                                    const SizedBox(height: 2),
                                    Text(
                                      p['level']?.toString() ?? '',
                                      maxLines: 1,
                                      overflow: TextOverflow.ellipsis,
                                      style: TextStyle(
                                        color: isDark ? Colors.white60 : kTextSecondary,
                                        fontSize: 10,
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                            );
                          },
                        ),
                      );
                    },
                  ),
                  const SizedBox(height: 24),

                  // Recent Reports Header
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      const Text(
                        'دواین ڕاپۆرتەکانی پاشماوە',
                        style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                      ),
                      TextButton(
                        onPressed: widget.onOpenMap,
                        child: const Text('هەموو نەخشە', style: TextStyle(color: kPrimaryGreen)),
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
                              Text('سلێمانی خاوێنە! هیچ پاشماوەیەک نییە.'),
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
                              'ڕاپۆرتی #${S.digits(spot['id'])}',
                              style: const TextStyle(fontWeight: FontWeight.bold),
                            ),
                            subtitle: Text(
                              'پاشماوە: ${S.digits(spot['litter_count'])} دەنک • پیسی: ${S.digits(spot['dirtiness'])}/${S.digits(5)}',
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
