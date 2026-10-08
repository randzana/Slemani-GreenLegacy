import 'package:flutter/material.dart';

import '../strings.dart';
import '../theme.dart';
import 'dashboard_screen.dart';
import 'garden_screen.dart';
import 'league_screen.dart';
import 'map_screen.dart';
import 'profile_screen.dart';
import 'report_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key, this.initialTab = 0});
  final int initialTab;

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  late int _tab = widget.initialTab;
  final _refresh = ValueNotifier<int>(0); // bump to reload every tab (map, home, profile, league)

  @override
  void dispose() {
    _refresh.dispose();
    super.dispose();
  }

  Future<void> _report() async {
    final changed = await Navigator.of(context).push<bool>(
      MaterialPageRoute(builder: (_) => const ReportScreen()),
    );
    if (changed == true) _refresh.value++;
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    final pages = [
      DashboardScreen(
        onOpenMap: () => setState(() => _tab = 1),
        onOpenGarden: () => setState(() => _tab = 2),
        onOpenLeague: () => setState(() => _tab = 4),
        onOpenReport: _report,
        refresh: _refresh,
      ),
      MapScreen(refresh: _refresh),
      const GardenScreen(),
      ProfileScreen(refresh: _refresh),
      LeagueScreen(refresh: _refresh),
    ];

    final titles = [
      S.appName,
      S.map,
      S.gardenTitle,
      S.profile,
      S.leagueTitle,
    ];

    return Scaffold(
      appBar: AppBar(
        title: Text(
          titles[_tab],
          style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 19),
        ),
        leading: _tab == 4
            ? IconButton(
                icon: const Icon(Icons.arrow_back_rounded),
                onPressed: () => setState(() => _tab = 0),
              )
            : null,
        actions: [
          if (_tab == 1)
            IconButton(
              icon: const Icon(Icons.refresh_rounded),
              tooltip: S.refreshMap,
              onPressed: () => _refresh.value++,
            )
          else if (_tab != 4)
            IconButton(
              icon: const Icon(Icons.emoji_events_rounded, color: Color(0xFFFFB300)),
              tooltip: S.league,
              onPressed: () => setState(() => _tab = 4),
            ),
        ],
      ),
      body: IndexedStack(index: _tab, children: pages),
      floatingActionButton: Container(
        height: 70,
        width: 70,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          boxShadow: [
            BoxShadow(
              color: kPrimaryGreen.withValues(alpha: 0.42),
              blurRadius: 16,
              spreadRadius: 2,
              offset: const Offset(0, 6),
            ),
          ],
        ),
        child: FloatingActionButton(
          onPressed: _report,
          backgroundColor: kPrimaryGreen,
          elevation: 0,
          shape: const CircleBorder(),
          child: const Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(Icons.qr_code_scanner_rounded, size: 28, color: Colors.white),
              Text(
                S.reportButton,
                style: TextStyle(
                  fontSize: 10,
                  color: Colors.white,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ],
          ),
        ),
      ),
      floatingActionButtonLocation: FloatingActionButtonLocation.centerDocked,
      bottomNavigationBar: BottomAppBar(
        shape: const CircularNotchedRectangle(),
        notchMargin: 8,
        color: isDark ? kCardDark : Colors.white,
        elevation: 8,
        child: SizedBox(
          height: 60,
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceAround,
            children: [
              _buildNavItem(0, Icons.dashboard_rounded, S.home),
              _buildNavItem(1, Icons.map_rounded, S.map),
              const SizedBox(width: 44), // space for center docked FAB
              _buildNavItem(2, Icons.eco_rounded, S.garden),
              _buildNavItem(3, Icons.person_rounded, S.profile),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildNavItem(int index, IconData icon, String label) {
    final isSelected = _tab == index;
    final color = isSelected ? kPrimaryGreen : Colors.grey.shade500;

    return InkWell(
      borderRadius: BorderRadius.circular(12),
      onTap: () => setState(() => _tab = index),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, color: color, size: 24),
            const SizedBox(height: 2),
            Text(
              label,
              style: TextStyle(
                color: color,
                fontSize: 11,
                fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
