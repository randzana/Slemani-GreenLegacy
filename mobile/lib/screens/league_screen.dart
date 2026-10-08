import 'package:flutter/material.dart';

import '../api.dart';
import '../strings.dart';
import '../theme.dart';

/// Eco-League: Top 3 Podium and rankings for neighbourhoods and citizens.
class LeagueScreen extends StatefulWidget {
  const LeagueScreen({super.key, required this.refresh});
  final ValueNotifier<int> refresh;

  @override
  State<LeagueScreen> createState() => _LeagueScreenState();
}

class _LeagueScreenState extends State<LeagueScreen> with SingleTickerProviderStateMixin {
  late Future<Map<String, dynamic>> _data = Api.instance.leaderboard();
  late TabController _tabController;

  final List<Color> _podiumColors = [
    const Color(0xFFFFB300), // Gold
    const Color(0xFF90A4AE), // Silver
    const Color(0xFFB08D57), // Bronze
  ];

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
    widget.refresh.addListener(_reload);
  }

  @override
  void dispose() {
    widget.refresh.removeListener(_reload);
    _tabController.dispose();
    super.dispose();
  }

  Future<void> _reload() async {
    setState(() {
      _data = Api.instance.leaderboard();
    });
    await _data;
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return RefreshIndicator(
      onRefresh: _reload,
      child: FutureBuilder<Map<String, dynamic>>(
        future: _data,
        builder: (context, snap) {
          if (snap.hasError) {
            return Center(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Text(snap.error.toString(), textAlign: TextAlign.center),
              ),
            );
          }
          if (!snap.hasData) {
            return const Center(child: CircularProgressIndicator(color: kPrimaryGreen));
          }

          final hoods = List<Map<String, dynamic>>.from(snap.data!['neighbourhoods']);
          final people = List<Map<String, dynamic>>.from(snap.data!['citizens']);

          return Column(
            children: [
              // Top Tab Selector (Neighbourhoods vs Citizens)
              Container(
                margin: const EdgeInsets.fromLTRB(20, 12, 20, 8),
                padding: const EdgeInsets.all(4),
                decoration: BoxDecoration(
                  color: isDark ? kCardDark : Colors.grey.shade200,
                  borderRadius: BorderRadius.circular(16),
                ),
                child: TabBar(
                  controller: _tabController,
                  indicatorSize: TabBarIndicatorSize.tab,
                  indicator: BoxDecoration(
                    color: kPrimaryGreen,
                    borderRadius: BorderRadius.circular(12),
                    boxShadow: [
                      BoxShadow(
                        color: kPrimaryGreen.withValues(alpha: 0.35),
                        blurRadius: 8,
                        offset: const Offset(0, 3),
                      ),
                    ],
                  ),
                  labelColor: Colors.white,
                  unselectedLabelColor: isDark ? Colors.white60 : Colors.black54,
                  labelStyle: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14),
                  dividerColor: Colors.transparent,
                  tabs: const [
                    Tab(text: 'گەڕەکەکان 🏘️'),
                    Tab(text: 'هاوڵاتیانی نموونەیی 🌟'),
                  ],
                ),
              ),

              // Tab View Content
              Expanded(
                child: TabBarView(
                  controller: _tabController,
                  children: [
                    _buildLeaderboardView(context, hoods, isHood: true),
                    _buildLeaderboardView(context, people, isHood: false),
                  ],
                ),
              ),
            ],
          );
        },
      ),
    );
  }

  Widget _buildLeaderboardView(BuildContext context, List<Map<String, dynamic>> items, {required bool isHood}) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    if (items.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.emoji_events_outlined, size: 64, color: Colors.grey.shade400),
            const SizedBox(height: 12),
            Text('هیچ داتایەک بەردەست نییە', style: TextStyle(color: Colors.grey.shade600)),
          ],
        ),
      );
    }

    return SingleChildScrollView(
      physics: const AlwaysScrollableScrollPhysics(),
      child: Column(
        children: [
          const SizedBox(height: 12),
          // Top 3 Podium
          if (items.length >= 3)
            SizedBox(
              height: 220,
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  _buildPodium(items[1]['name']?.toString() ?? 'دووەم', S.digits(items[1]['points'] ?? 0), 2, _podiumColors[1]),
                  _buildPodium(items[0]['name']?.toString() ?? 'یەکەم', S.digits(items[0]['points'] ?? 0), 1, _podiumColors[0]),
                  _buildPodium(items[2]['name']?.toString() ?? 'سێیەم', S.digits(items[2]['points'] ?? 0), 3, _podiumColors[2]),
                ],
              ),
            ),
          const SizedBox(height: 16),

          // Remaining items card list
          Container(
            padding: const EdgeInsets.fromLTRB(18, 20, 18, 30),
            decoration: BoxDecoration(
              color: Theme.of(context).cardColor,
              borderRadius: const BorderRadius.vertical(top: Radius.circular(28)),
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withValues(alpha: isDark ? 0.4 : 0.05),
                  blurRadius: 10,
                  offset: const Offset(0, -4),
                ),
              ],
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  isHood ? 'هەموو گەڕەکەکانی سلێمانی' : 'ڕیزبەندیی گشتی چالاکوانان',
                  style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: 12),
                for (var i = 0; i < items.length; i++)
                  _buildRankRow(
                    context,
                    rank: i + 1,
                    name: items[i]['name']?.toString() ?? '',
                    subtitle: isHood ? null : items[i]['neighbourhood']?.toString(),
                    points: S.digits(items[i]['points'] ?? 0),
                    isTopThree: i < 3,
                  ),
                const SizedBox(height: 80),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildPodium(String name, String points, int rank, Color color) {
    final double height = rank == 1 ? 140 : (rank == 2 ? 110 : 85);
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 6.0),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.end,
        children: [
          CircleAvatar(
            backgroundColor: color.withValues(alpha: 0.18),
            radius: 22,
            child: Text(
              S.digits(rank),
              style: TextStyle(color: color, fontWeight: FontWeight.bold, fontSize: 18),
            ),
          ),
          const SizedBox(height: 6),
          Container(
            width: 96,
            height: height,
            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 8),
            decoration: BoxDecoration(
              gradient: LinearGradient(
                colors: [color.withValues(alpha: 0.85), color],
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
              ),
              borderRadius: const BorderRadius.vertical(top: Radius.circular(16)),
              boxShadow: [
                BoxShadow(
                  color: color.withValues(alpha: 0.3),
                  blurRadius: 8,
                  offset: const Offset(0, 4),
                ),
              ],
            ),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Text(
                  name,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  textAlign: TextAlign.center,
                  style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 13),
                ),
                const SizedBox(height: 2),
                Text(
                  '$points خاڵ',
                  style: const TextStyle(color: Colors.white70, fontSize: 11, fontWeight: FontWeight.w600),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildRankRow(
    BuildContext context, {
    required int rank,
    required String name,
    String? subtitle,
    required String points,
    required bool isTopThree,
  }) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    Color badgeColor = kPrimaryGreen;
    if (rank == 1) badgeColor = _podiumColors[0];
    if (rank == 2) badgeColor = _podiumColors[1];
    if (rank == 3) badgeColor = _podiumColors[2];

    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      decoration: BoxDecoration(
        color: isDark ? const Color(0xFF262626) : Colors.grey.shade50,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(
          color: isTopThree ? badgeColor.withValues(alpha: 0.3) : Colors.grey.shade200,
        ),
      ),
      child: Row(
        children: [
          CircleAvatar(
            backgroundColor: badgeColor.withValues(alpha: 0.12),
            radius: 16,
            child: Text(
              '#${S.digits(rank)}',
              style: TextStyle(color: badgeColor, fontWeight: FontWeight.bold, fontSize: 12),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  name,
                  style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 15),
                ),
                if (subtitle != null)
                  Text(
                    subtitle,
                    style: TextStyle(color: Colors.grey.shade600, fontSize: 12),
                  ),
              ],
            ),
          ),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
            decoration: BoxDecoration(
              color: kPrimaryGreen.withValues(alpha: 0.12),
              borderRadius: BorderRadius.circular(10),
            ),
            child: Text(
              '$points ${S.points}',
              style: const TextStyle(
                color: kPrimaryGreen,
                fontWeight: FontWeight.bold,
                fontSize: 13,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
