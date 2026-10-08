import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';

import '../api.dart';
import '../main.dart';
import '../strings.dart';
import '../theme.dart';
import 'spot_detail_screen.dart';

class MapScreen extends StatefulWidget {
  const MapScreen({super.key, required this.refresh});
  final ValueNotifier<int> refresh;

  @override
  State<MapScreen> createState() => _MapScreenState();
}

class _MapScreenState extends State<MapScreen> {
  static const slemani = LatLng(35.5613, 45.4373);
  final MapController _mapController = MapController();
  List<Map<String, dynamic>> _spots = [];
  String _filter = 'all'; // 'all', 'open', 'in_progress' (also needs_review), 'clean'
  Timer? _timer;

  @override
  void initState() {
    super.initState();
    _load();
    widget.refresh.addListener(_load);
    _timer = Timer.periodic(const Duration(seconds: 15), (_) => _load());
  }

  @override
  void dispose() {
    _timer?.cancel();
    widget.refresh.removeListener(_load);
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final spots = await Api.instance.reports();
      if (mounted) setState(() => _spots = spots);
    } catch (e) {
      if (mounted) showError(context, e);
    }
  }

  Future<void> _open(Map<String, dynamic> spot) async {
    await Navigator.of(context).push(
      MaterialPageRoute(builder: (_) => SpotDetailScreen(reportId: spot['id'] as int)),
    );
    widget.refresh.value++;
  }

  // needs_review is drawn in the same amber as in_progress, so it shares that chip.
  static bool _matches(Map<String, dynamic> spot, String filter) =>
      filter == 'all' ||
      spot['status'] == filter ||
      (filter == 'in_progress' && spot['status'] == 'needs_review');

  int _count(String filter) => _spots.where((s) => _matches(s, filter)).length;

  List<Map<String, dynamic>> get _filteredSpots =>
      _spots.where((s) => _matches(s, _filter)).toList();

  @override
  Widget build(BuildContext context) {
    final spots = _filteredSpots;

    return Stack(
      children: [
        FlutterMap(
          mapController: _mapController,
          options: const MapOptions(initialCenter: slemani, initialZoom: 14),
          children: [
            TileLayer(
              urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
              userAgentPackageName: 'krd.greenlegacy.slemani',
            ),
            MarkerLayer(
              markers: [
                for (final s in spots)
                  Marker(
                    point: LatLng((s['lat'] as num).toDouble(), (s['lon'] as num).toDouble()),
                    width: 50,
                    height: 50,
                    child: GestureDetector(
                      onTap: () => _open(s),
                      child: Container(
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          color: statusColour(s['status']?.toString() ?? '').withValues(alpha: 0.2),
                        ),
                        child: Center(
                          child: Icon(
                            Icons.location_on_rounded,
                            size: 42,
                            color: statusColour(s['status']?.toString() ?? ''),
                          ),
                        ),
                      ),
                    ),
                  ),
              ],
            ),
          ],
        ),

        // Floating Filter & Legend Header
        Positioned(
          top: 12,
          right: 12,
          left: 12,
          child: Column(
            children: [
              Card(
                elevation: 4,
                shadowColor: Colors.black.withValues(alpha: 0.12),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceAround,
                    children: [
                      _buildFilterChip(S.withCount(S.filterAll, _count('all')), 'all', Colors.grey.shade700),
                      _buildFilterChip(
                        S.withCount(S.open, _count('open')),
                        'open',
                        kStatusOpen,
                      ),
                      _buildFilterChip(
                        S.withCount(S.filterInProgress, _count('in_progress')),
                        'in_progress',
                        kStatusInProgress,
                      ),
                      _buildFilterChip(
                        S.withCount(S.filterClean, _count('clean')),
                        'clean',
                        kStatusClean,
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),

        // Re-center Location Button
        Positioned(
          bottom: 24,
          left: 16,
          child: FloatingActionButton.small(
            heroTag: 'map_center_btn',
            backgroundColor: Colors.white,
            foregroundColor: kPrimaryGreen,
            elevation: 4,
            onPressed: () => _mapController.move(slemani, 14),
            child: const Icon(Icons.my_location_rounded),
          ),
        ),
      ],
    );
  }

  Widget _buildFilterChip(String label, String key, Color color) {
    final isSelected = _filter == key;
    return GestureDetector(
      onTap: () => setState(() => _filter = key),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
        decoration: BoxDecoration(
          color: isSelected ? color.withValues(alpha: 0.18) : Colors.transparent,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: isSelected ? color : Colors.transparent,
            width: 1.5,
          ),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.circle, size: 8, color: color),
            const SizedBox(width: 4),
            Text(
              label,
              style: TextStyle(
                fontSize: 12,
                fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
                color: isSelected ? color : Colors.grey.shade800,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
