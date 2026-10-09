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
  List<Map<String, dynamic>> _pins = [];
  List<Map<String, dynamic>> _trashBins = [];
  String _filter = 'all'; // 'all', 'open', 'in_progress', 'clean', 'tree_planting', 'cleanup_target', 'bins'
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
      final results = await Future.wait([
        Api.instance.reports(),
        Api.instance.pins().catchError((_) => <Map<String, dynamic>>[]),
        Api.instance.trashBins().catchError((_) => <Map<String, dynamic>>[]),
      ]);
      if (mounted) {
        setState(() {
          _spots = results[0];
          _pins = results[1];
          _trashBins = results[2];
        });
      }
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

  void _openPin(Map<String, dynamic> pin) {
    final cat = pin['category']?.toString() ?? 'tree_planting';
    final isTree = cat == 'tree_planting';
    final isWater = cat == 'watering_point';
    final color = isTree ? kPrimaryGreen : (isWater ? Colors.blue : Colors.orange.shade800);
    final icon = isTree ? Icons.park_rounded : (isWater ? Icons.water_drop_rounded : Icons.delete_sweep_rounded);
    final title = pin['title']?.toString() ?? '';
    final desc = pin['description']?.toString() ?? '';
    final reward = pin['reward_points'] ?? 50;
    final hood = pin['neighbourhood_name']?.toString() ?? '';
    final target = (pin['target_count'] as num?)?.toInt() ?? 1;

    int participantCount = (pin['participant_count'] as num?)?.toInt() ?? 0;
    bool isRegistered = pin['user_registered'] == true;
    bool loading = false;

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
      builder: (ctx) => StatefulBuilder(
        builder: (context, setSheetState) {
          final progress = target > 0 ? (participantCount / target).clamp(0.0, 1.0) : 0.0;

          return Padding(
            padding: EdgeInsets.only(
              left: 20,
              right: 20,
              top: 20,
              bottom: MediaQuery.of(context).viewInsets.bottom + 20,
            ),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    CircleAvatar(backgroundColor: color.withValues(alpha: 0.15), child: Icon(icon, color: color)),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            isTree ? S.pinTreePlanting : (isWater ? S.pinWateringPoint : S.pinCleanupTarget),
                            style: TextStyle(color: color, fontSize: 13, fontWeight: FontWeight.bold),
                          ),
                          Text(title, style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                        ],
                      ),
                    ),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                      decoration: BoxDecoration(color: Colors.amber.shade100, borderRadius: BorderRadius.circular(12)),
                      child: Text('+${S.digits(reward)} ${S.points}',
                          style: TextStyle(color: Colors.amber.shade900, fontWeight: FontWeight.bold)),
                    ),
                  ],
                ),
                const SizedBox(height: 14),
                Text(desc, style: TextStyle(color: Colors.grey.shade700, fontSize: 14, height: 1.4)),
                if (hood.isNotEmpty) ...[
                  const SizedBox(height: 10),
                  Text('${S.neighbourhood}: $hood', style: TextStyle(color: Colors.grey.shade600, fontSize: 13)),
                ],
                const SizedBox(height: 14),

                // Participant counter & progress card
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: Colors.grey.shade50,
                    borderRadius: BorderRadius.circular(14),
                    border: Border.all(color: Colors.grey.shade200),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Row(
                            children: [
                              Icon(Icons.people_alt_rounded, size: 18, color: color),
                              const SizedBox(width: 6),
                              Text(
                                '${S.participantsCount}: ${S.digits(participantCount)} کەس',
                                style: TextStyle(fontWeight: FontWeight.bold, fontSize: 14, color: Colors.grey.shade800),
                              ),
                            ],
                          ),
                          Text(
                            '${S.pinTarget}: ${S.digits(target)}',
                            style: TextStyle(fontSize: 13, color: Colors.grey.shade600),
                          ),
                        ],
                      ),
                      const SizedBox(height: 8),
                      ClipRRect(
                        borderRadius: BorderRadius.circular(6),
                        child: LinearProgressIndicator(
                          value: progress,
                          minHeight: 8,
                          backgroundColor: Colors.grey.shade200,
                          valueColor: AlwaysStoppedAnimation<Color>(color),
                        ),
                      ),
                    ],
                  ),
                ),

                if (isRegistered) ...[
                  const SizedBox(height: 12),
                  Container(
                    width: double.infinity,
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                    decoration: BoxDecoration(
                      color: kPrimaryGreen.withValues(alpha: 0.12),
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: const Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(Icons.check_circle_rounded, size: 18, color: kPrimaryGreen),
                        SizedBox(width: 6),
                        Text(
                          S.alreadyRegisteredBadge,
                          style: TextStyle(color: kPrimaryGreen, fontWeight: FontWeight.bold, fontSize: 13),
                        ),
                      ],
                    ),
                  ),
                ],

                const SizedBox(height: 18),
                if (loading)
                  const Center(child: CircularProgressIndicator())
                else if (isRegistered)
                  SizedBox(
                    width: double.infinity,
                    child: OutlinedButton.icon(
                      icon: const Icon(Icons.close_rounded, size: 18),
                      label: const Text(S.cancelRegistration),
                      style: OutlinedButton.styleFrom(
                        foregroundColor: Colors.red.shade700,
                        side: BorderSide(color: Colors.red.shade300),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                        padding: const EdgeInsets.symmetric(vertical: 12),
                      ),
                      onPressed: () async {
                        setSheetState(() => loading = true);
                        try {
                          final res = await Api.instance.unregisterPin(pin['id'] as int);
                          setSheetState(() {
                            isRegistered = false;
                            participantCount = (res['participant_count'] as num?)?.toInt() ?? (participantCount - 1).clamp(0, 9999);
                            loading = false;
                          });
                          setState(() {
                            pin['user_registered'] = false;
                            pin['participant_count'] = participantCount;
                          });
                          if (context.mounted) {
                            ScaffoldMessenger.of(context).showSnackBar(
                              const SnackBar(content: Text(S.unregisteredSuccess)),
                            );
                          }
                        } catch (e) {
                          setSheetState(() => loading = false);
                        }
                      },
                    ),
                  )
                else
                  SizedBox(
                    width: double.infinity,
                    child: ElevatedButton.icon(
                      icon: const Icon(Icons.how_to_reg_rounded),
                      label: Text(isTree ? S.registerParticipation : 'خۆتۆمارکردن بۆ بەشداریکردن'),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: color,
                        foregroundColor: Colors.white,
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                        padding: const EdgeInsets.symmetric(vertical: 12),
                      ),
                      onPressed: () async {
                        setSheetState(() => loading = true);
                        try {
                          final res = await Api.instance.registerPin(pin['id'] as int);
                          setSheetState(() {
                            isRegistered = true;
                            participantCount = (res['participant_count'] as num?)?.toInt() ?? (participantCount + 1);
                            loading = false;
                          });
                          setState(() {
                            pin['user_registered'] = true;
                            pin['participant_count'] = participantCount;
                          });
                          if (context.mounted) {
                            ScaffoldMessenger.of(context).showSnackBar(
                              const SnackBar(
                                content: Text(S.registeredSuccess),
                                backgroundColor: kPrimaryGreen,
                              ),
                            );
                          }
                        } catch (e) {
                          setSheetState(() => loading = false);
                        }
                      },
                    ),
                  ),
              ],
            ),
          );
        },
      ),
    );
  }


  void _openTrashBin(Map<String, dynamic> bin) {
    final name = bin['name']?.toString() ?? 'تەنەکەی خۆڵ';
    final code = bin['code']?.toString() ?? '';
    final typeLabel = bin['type_label']?.toString() ?? 'پاشماوەی گشتی';
    final capacity = bin['capacity_liters'] ?? 240;
    final hood = bin['neighbourhood_name']?.toString() ?? '';
    final isFull = bin['status'] == 'full';
    final disposals = (bin['disposal_count'] as num?)?.toInt() ?? 0;
    bool busy = false;

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
      builder: (ctx) => StatefulBuilder(
        builder: (context, setSheetState) => Padding(
          padding: EdgeInsets.only(
            left: 20,
            right: 20,
            top: 20,
            bottom: MediaQuery.of(context).viewInsets.bottom + 24,
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  CircleAvatar(
                    backgroundColor: (isFull ? Colors.red : const Color(0xFF10B981)).withValues(alpha: 0.15),
                    child: Icon(Icons.delete_rounded, color: isFull ? Colors.red : const Color(0xFF10B981)),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          isFull ? 'پڕبووە' : 'تەنەکەی خۆڵی شارەوانی',
                          style: TextStyle(
                            color: isFull ? Colors.red : const Color(0xFF10B981),
                            fontSize: 13,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        Text(name, style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                      ],
                    ),
                  ),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                    decoration: BoxDecoration(
                      color: const Color(0xFF10B981).withValues(alpha: 0.12),
                      borderRadius: BorderRadius.circular(10),
                      border: Border.all(color: const Color(0xFF10B981).withValues(alpha: 0.3)),
                    ),
                    child: Text(code,
                        style: const TextStyle(
                            fontFamily: 'Courier',
                            fontWeight: FontWeight.bold,
                            color: Color(0xFF065F46),
                            fontSize: 13)),
                  ),
                ],
              ),
              const SizedBox(height: 16),
              Container(
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: Colors.grey.shade50,
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(color: Colors.grey.shade200),
                ),
                child: Column(
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        const Text('جۆری پاشماوە:', style: TextStyle(color: Colors.grey, fontSize: 13)),
                        Text(typeLabel, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
                      ],
                    ),
                    const Divider(height: 16),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        const Text('قەبارە:', style: TextStyle(color: Colors.grey, fontSize: 13)),
                        Text('${S.digits(capacity)} لیتر', style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
                      ],
                    ),
                    if (hood.isNotEmpty) ...[
                      const Divider(height: 16),
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          const Text('گەڕەک:', style: TextStyle(color: Colors.grey, fontSize: 13)),
                          Text(hood, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
                        ],
                      ),
                    ],
                    const Divider(height: 16),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        const Text('کۆی فڕێدان:', style: TextStyle(color: Colors.grey, fontSize: 13)),
                        Text('${S.digits(disposals)} جار', style: const TextStyle(fontWeight: FontWeight.bold, color: Color(0xFF10B981), fontSize: 13)),
                      ],
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 18),
              SizedBox(
                width: double.infinity,
                child: ElevatedButton.icon(
                  icon: const Icon(Icons.qr_code_scanner_rounded),
                  label: busy
                      ? const SizedBox(
                          width: 20,
                          height: 20,
                          child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                      : const Text('🗑️ فڕێدانی پاشماوە و تۆمارکردن (+١٥ خاڵ)'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFF10B981),
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(vertical: 14),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                  ),
                  onPressed: busy || isFull
                      ? null
                      : () async {
                          final messenger = ScaffoldMessenger.of(context);
                          final navigator = Navigator.of(ctx);
                          setSheetState(() => busy = true);
                          try {
                            final res = await Api.instance.verifyDisposal(code, lat: (bin['lat'] as num).toDouble(), lon: (bin['lon'] as num).toDouble());
                            navigator.pop();
                            widget.refresh.value++;
                            _load();
                            messenger.showSnackBar(
                              SnackBar(
                                content: Text(res['message']?.toString() ?? 'فڕێدانی پاشماوە بە سەرکەوتوویی پشتڕاستکرایەوە!'),
                                backgroundColor: const Color(0xFF10B981),
                                duration: const Duration(seconds: 4),
                              ),
                            );
                          } catch (err) {
                            setSheetState(() => busy = false);
                            if (context.mounted) showError(context, err);
                          }
                        },
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  static bool _matches(Map<String, dynamic> spot, String filter) =>
      filter == 'all' ||
      spot['status'] == filter ||
      (filter == 'in_progress' && spot['status'] == 'needs_review');

  int _count(String filter) {
    if (filter == 'tree_planting' || filter == 'cleanup_target') {
      return _pins.where((p) => p['category'] == filter).length;
    }
    if (filter == 'bins') {
      return _trashBins.length;
    }
    return _spots.where((s) => _matches(s, filter)).length;
  }

  List<Map<String, dynamic>> get _filteredSpots =>
      (_filter == 'tree_planting' || _filter == 'cleanup_target' || _filter == 'bins')
          ? []
          : _spots.where((s) => _matches(s, _filter)).toList();

  List<Map<String, dynamic>> get _filteredPins =>
      _filter == 'bins' ? [] : _pins.where((p) => _filter == 'all' || _filter == p['category']).toList();

  List<Map<String, dynamic>> get _filteredBins =>
      _filter == 'all' || _filter == 'bins' ? _trashBins : [];

  @override
  Widget build(BuildContext context) {
    final spots = _filteredSpots;
    final pins = _filteredPins;
    final bins = _filteredBins;

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
                // Citizen litter reports
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

                // Municipality custom pins (Tree Planting & Cleanup Targets)
                for (final p in pins)
                  Marker(
                    point: LatLng((p['lat'] as num).toDouble(), (p['lon'] as num).toDouble()),
                    width: 52,
                    height: 52,
                    child: GestureDetector(
                      onTap: () => _openPin(p),
                      child: Container(
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          color: (p['category'] == 'tree_planting'
                                  ? kPrimaryGreen
                                  : (p['category'] == 'watering_point' ? Colors.blue : Colors.orange.shade800))
                              .withValues(alpha: 0.25),
                          border: Border.all(
                            color: p['category'] == 'tree_planting'
                                ? kPrimaryGreen
                                : (p['category'] == 'watering_point' ? Colors.blue : Colors.orange.shade800),
                            width: 2,
                          ),
                        ),
                        child: Center(
                          child: Icon(
                            p['category'] == 'tree_planting'
                                ? Icons.park_rounded
                                : (p['category'] == 'watering_point'
                                    ? Icons.water_drop_rounded
                                    : Icons.warning_amber_rounded),
                            size: 28,
                            color: p['category'] == 'tree_planting'
                                ? kPrimaryGreen
                                : (p['category'] == 'watering_point' ? Colors.blue : Colors.orange.shade800),
                          ),
                        ),
                      ),
                    ),
                  ),

                // Municipality Trash Bins
                for (final b in bins)
                  Marker(
                    point: LatLng((b['lat'] as num).toDouble(), (b['lon'] as num).toDouble()),
                    width: 48,
                    height: 48,
                    child: GestureDetector(
                      onTap: () => _openTrashBin(b),
                      child: Container(
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          color: (b['status'] == 'full' ? Colors.red : const Color(0xFF10B981)).withValues(alpha: 0.25),
                          border: Border.all(
                            color: b['status'] == 'full' ? Colors.red : const Color(0xFF10B981),
                            width: 2.2,
                          ),
                        ),
                        child: Center(
                          child: Icon(
                            Icons.delete_rounded,
                            size: 26,
                            color: b['status'] == 'full' ? Colors.red : const Color(0xFF10B981),
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
          child: Card(
            elevation: 4,
            shadowColor: Colors.black.withValues(alpha: 0.12),
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
            child: SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
              child: Row(
                children: [
                  _buildFilterChip(S.withCount(S.filterAll, _count('all')), 'all', Colors.grey.shade700),
                  const SizedBox(width: 4),
                  _buildFilterChip(S.withCount('🗑️ تەنەکەکان', _count('bins')), 'bins', const Color(0xFF10B981)),
                  const SizedBox(width: 4),
                  _buildFilterChip(S.withCount(S.open, _count('open')), 'open', kStatusOpen),
                  const SizedBox(width: 4),
                  _buildFilterChip(S.withCount(S.filterInProgress, _count('in_progress')), 'in_progress', kStatusInProgress),
                  const SizedBox(width: 4),
                  _buildFilterChip(S.withCount(S.filterClean, _count('clean')), 'clean', kStatusClean),
                  const SizedBox(width: 4),
                  _buildFilterChip(S.withCount(S.filterTreePlanting, _count('tree_planting')), 'tree_planting', kPrimaryGreen),
                  const SizedBox(width: 4),
                  _buildFilterChip(S.withCount(S.filterCleanupTarget, _count('cleanup_target')), 'cleanup_target', Colors.orange.shade800),
                ],
              ),
            ),
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
