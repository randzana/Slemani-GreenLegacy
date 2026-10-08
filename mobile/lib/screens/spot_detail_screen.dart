import 'package:flutter/material.dart';
import 'package:geolocator/geolocator.dart';

import '../api.dart';
import '../location.dart';
import '../main.dart';
import '../strings.dart';
import '../theme.dart';
import 'cleanup_recorder_screen.dart';

/// Spot detail: the before photo, how dirty it is, how far away, and "I'll clean it".
class SpotDetailScreen extends StatefulWidget {
  const SpotDetailScreen({super.key, required this.reportId});
  final int reportId;

  @override
  State<SpotDetailScreen> createState() => _SpotDetailScreenState();
}

class _SpotDetailScreenState extends State<SpotDetailScreen> {
  Map<String, dynamic>? _spot;
  double? _metres;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final spot = await Api.instance.report(widget.reportId);
      if (mounted) setState(() => _spot = spot);
      final pos = await currentPosition();
      final metres = Geolocator.distanceBetween(
        pos.latitude,
        pos.longitude,
        (spot['lat'] as num).toDouble(),
        (spot['lon'] as num).toDouble(),
      );
      if (mounted) setState(() => _metres = metres);
    } catch (e) {
      if (mounted) showError(context, e);
    }
  }

  Future<void> _claim() async {
    setState(() => _busy = true);
    try {
      final challenge = await Api.instance.claim(widget.reportId);
      if (!mounted) return;
      await Navigator.of(context).push(
        MaterialPageRoute(
          builder: (_) => CleanupRecorderScreen(spot: _spot!, challenge: challenge),
        ),
      );
      _load();
    } catch (e) {
      if (mounted) showError(context, e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  String _status(String s) => S.reportStatuses[s] ?? s;

  @override
  Widget build(BuildContext context) {
    final spot = _spot;
    final color = spot == null ? kPrimaryGreen : statusColour(spot['status']?.toString() ?? '');

    return Scaffold(
      appBar: AppBar(
        title: Text(
          spot == null ? '' : 'ڕاپۆرتی #${S.digits(spot['id'])}',
          style: const TextStyle(fontWeight: FontWeight.bold),
        ),
      ),
      body: spot == null
          ? const Center(child: CircularProgressIndicator(color: kPrimaryGreen))
          : ListView(
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
              children: [
                // Spot Image with Badge Overlay
                Stack(
                  children: [
                    Container(
                      height: 260,
                      width: double.infinity,
                      decoration: BoxDecoration(
                        borderRadius: BorderRadius.circular(20),
                        boxShadow: [
                          BoxShadow(
                            color: Colors.black.withValues(alpha: 0.12),
                            blurRadius: 14,
                            offset: const Offset(0, 6),
                          ),
                        ],
                      ),
                      child: ClipRRect(
                        borderRadius: BorderRadius.circular(20),
                        child: Image.network(
                          Api.instance.fileUrl(spot['photo_url']),
                          fit: BoxFit.cover,
                          errorBuilder: (_, __, ___) => Container(
                            color: Colors.grey.shade300,
                            child: const Center(
                              child: Icon(Icons.broken_image_rounded, size: 48, color: Colors.grey),
                            ),
                          ),
                        ),
                      ),
                    ),
                    Positioned(
                      top: 14,
                      right: 14,
                      child: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
                        decoration: BoxDecoration(
                          color: color,
                          borderRadius: BorderRadius.circular(12),
                          boxShadow: [
                            BoxShadow(
                              color: color.withValues(alpha: 0.4),
                              blurRadius: 8,
                              offset: const Offset(0, 3),
                            ),
                          ],
                        ),
                        child: Text(
                          _status(spot['status']),
                          style: const TextStyle(
                            color: Colors.white,
                            fontWeight: FontWeight.bold,
                            fontSize: 13,
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 20),

                // Metrics Card
                Card(
                  elevation: 2,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
                  child: Padding(
                    padding: const EdgeInsets.symmetric(vertical: 8),
                    child: Column(
                      children: [
                        ListTile(
                          leading: CircleAvatar(
                            backgroundColor: kStatusOpen.withValues(alpha: 0.12),
                            child: const Icon(Icons.delete_outline_rounded, color: kStatusOpen),
                          ),
                          title: const Text(S.litterFound, style: TextStyle(fontWeight: FontWeight.w600)),
                          trailing: Text(
                            S.digits(spot['litter_count']),
                            style: const TextStyle(fontSize: 19, fontWeight: FontWeight.bold),
                          ),
                        ),
                        const Divider(indent: 16, endIndent: 16, height: 1),
                        ListTile(
                          leading: CircleAvatar(
                            backgroundColor: Colors.amber.withValues(alpha: 0.12),
                            child: const Icon(Icons.warning_amber_rounded, color: Colors.amber),
                          ),
                          title: const Text(S.dirtiness, style: TextStyle(fontWeight: FontWeight.w600)),
                          trailing: Text(
                            '${S.digits(spot['dirtiness'])} / ${S.digits(5)}',
                            style: const TextStyle(fontSize: 19, fontWeight: FontWeight.bold),
                          ),
                        ),
                        const Divider(indent: 16, endIndent: 16, height: 1),
                        ListTile(
                          leading: CircleAvatar(
                            backgroundColor: kPrimaryGreen.withValues(alpha: 0.12),
                            child: const Icon(Icons.near_me_rounded, color: kPrimaryGreen),
                          ),
                          title: const Text(S.distance, style: TextStyle(fontWeight: FontWeight.w600)),
                          trailing: Text(
                            _metres == null ? '—' : '${S.digits(_metres!.round())} ${S.metres}',
                            style: const TextStyle(fontSize: 19, fontWeight: FontWeight.bold),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 24),

                // Action Button
                if (spot['status'] == 'open' || spot['status'] == 'in_progress')
                  SizedBox(
                    height: 54,
                    child: ElevatedButton.icon(
                      onPressed: _busy ? null : _claim,
                      style: ElevatedButton.styleFrom(
                        backgroundColor: kPrimaryGreen,
                        foregroundColor: Colors.white,
                        elevation: 4,
                        shadowColor: kPrimaryGreen.withValues(alpha: 0.4),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                      ),
                      icon: const Icon(Icons.cleaning_services_rounded),
                      label: Text(
                        _busy ? 'تکایە چاوەڕێبە...' : S.illClean,
                        style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                      ),
                    ),
                  ),
              ],
            ),
    );
  }
}
