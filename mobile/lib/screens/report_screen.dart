import 'package:flutter/material.dart';

import '../api.dart';
import '../location.dart';
import '../main.dart';
import '../strings.dart';
import '../theme.dart';
import 'camera_box.dart';
import 'spot_detail_screen.dart' show AiDescription;

/// Report: take a photo in the app, the AI counts the litter and scores the spot 1-5.
class ReportScreen extends StatefulWidget {
  const ReportScreen({super.key});

  @override
  State<ReportScreen> createState() => _ReportScreenState();
}

class _ReportScreenState extends State<ReportScreen> {
  final _camera = CameraHolder(simulatorPath: (_) => '/sim/report-photo');
  String? _cameraError;
  bool _busy = false;
  Map<String, dynamic>? _result;

  @override
  void initState() {
    super.initState();
    _camera.open().then((_) {
      if (mounted) setState(() {});
    }).catchError((Object e) {
      if (mounted) setState(() => _cameraError = cameraErrorText(e));
    });
  }

  @override
  void dispose() {
    _camera.dispose();
    super.dispose();
  }

  Future<void> _shoot() async {
    setState(() => _busy = true);
    try {
      final photo = await _camera.shoot();
      final pos = await currentPosition();
      final result = await Api.instance.createReport(photo, pos.latitude, pos.longitude);
      if (mounted) setState(() => _result = result);
    } catch (e) {
      if (mounted) showError(context, e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(
        title: const Text(S.report, style: TextStyle(fontWeight: FontWeight.bold)),
        backgroundColor: Colors.black,
        foregroundColor: Colors.white,
        elevation: 0,
      ),
      body: _result != null
          ? _ResultCard(result: _result!)
          : Stack(
              children: [
                Positioned.fill(child: CameraBox(holder: _camera, error: _cameraError)),
                if (_busy)
                  Container(
                    color: Colors.black87,
                    alignment: Alignment.center,
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Container(
                          padding: const EdgeInsets.all(20),
                          decoration: BoxDecoration(
                            color: kDarkCard,
                            borderRadius: BorderRadius.circular(20),
                            boxShadow: [
                              BoxShadow(
                                color: kPrimaryGreen.withValues(alpha: 0.3),
                                blurRadius: 20,
                              ),
                            ],
                          ),
                          child: const CircularProgressIndicator(
                            color: kPrimaryGreen,
                            strokeWidth: 3,
                          ),
                        ),
                        const SizedBox(height: 16),
                        const Text(
                          S.analysing,
                          style: TextStyle(
                            color: Colors.white,
                            fontSize: 16,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ],
                    ),
                  ),
                Positioned(
                  left: 0,
                  right: 0,
                  bottom: 36,
                  child: Center(
                    child: GestureDetector(
                      onTap: _busy || !_camera.ready ? null : _shoot,
                      child: Container(
                        width: 76,
                        height: 76,
                        padding: const EdgeInsets.all(4),
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          border: Border.all(color: Colors.white, width: 4),
                        ),
                        child: Container(
                          decoration: BoxDecoration(
                            shape: BoxShape.circle,
                            color: _busy || !_camera.ready ? Colors.grey : kPrimaryGreen,
                            boxShadow: [
                              BoxShadow(
                                color: kPrimaryGreen.withValues(alpha: 0.5),
                                blurRadius: 16,
                                spreadRadius: 2,
                              ),
                            ],
                          ),
                          child: const Icon(
                            Icons.camera_alt_rounded,
                            color: Colors.white,
                            size: 32,
                          ),
                        ),
                      ),
                    ),
                  ),
                ),
              ],
            ),
    );
  }
}

class _ResultCard extends StatelessWidget {
  const _ResultCard({required this.result});
  final Map<String, dynamic> result;

  @override
  Widget build(BuildContext context) {
    final report = Map<String, dynamic>.from(result['report']);
    final message = result['message'];
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Container(
      color: isDark ? kDarkSurface : kBackgroundLight,
      padding: const EdgeInsets.all(24),
      child: SafeArea(
        child: ListView(
          children: [
            Container(
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(20),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withValues(alpha: 0.1),
                    blurRadius: 16,
                    offset: const Offset(0, 4),
                  ),
                ],
              ),
              child: ClipRRect(
                borderRadius: BorderRadius.circular(20),
                child: Image.network(
                  Api.instance.fileUrl(report['photo_url']),
                  height: 240,
                  fit: BoxFit.cover,
                ),
              ),
            ),
            const SizedBox(height: 20),
            Container(
              padding: const EdgeInsets.all(20),
              decoration: BoxDecoration(
                color: isDark ? kDarkCard : Colors.white,
                borderRadius: BorderRadius.circular(20),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withValues(alpha: isDark ? 0.3 : 0.05),
                    blurRadius: 16,
                    offset: const Offset(0, 4),
                  ),
                ],
              ),
              child: Column(
                children: [
                  _Row(
                    S.litterFound,
                    S.digits(report['litter_count']),
                    icon: Icons.delete_outline_rounded,
                  ),
                  Divider(color: Colors.grey.withValues(alpha: 0.2), height: 24),
                  _Row(
                    S.dirtiness,
                    '${S.digits(report['dirtiness'])} / ${S.digits(5)}',
                    icon: Icons.speed_rounded,
                  ),
                  Divider(color: Colors.grey.withValues(alpha: 0.2), height: 24),
                  _Row(
                    S.pendingPoints,
                    '+${S.digits(result['points_pending'] ?? 0)}',
                    icon: Icons.stars_rounded,
                    highlight: true,
                  ),
                ],
              ),
            ),
            AiDescription(report['description']?.toString()),
            const SizedBox(height: 16),
            if (message != null) ...[
              Container(
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: kPrimaryGreen.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: kPrimaryGreen.withValues(alpha: 0.3)),
                ),
                child: Text(
                  message.toString(),
                  textAlign: TextAlign.center,
                  style: const TextStyle(
                    fontSize: 15,
                    fontWeight: FontWeight.w600,
                    color: kPrimaryGreen,
                  ),
                ),
              ),
              const SizedBox(height: 10),
            ],
            Text(
              S.pendingNote,
              textAlign: TextAlign.center,
              style: TextStyle(
                color: isDark ? Colors.white60 : kTextSecondary,
                fontSize: 13,
              ),
            ),
            const SizedBox(height: 28),
            FilledButton(
              onPressed: () => Navigator.of(context).pop(true),
              style: FilledButton.styleFrom(
                backgroundColor: kPrimaryGreen,
                foregroundColor: Colors.white,
                minimumSize: const Size.fromHeight(54),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                elevation: 2,
              ),
              child: const Text(
                S.done,
                style: TextStyle(fontSize: 17, fontWeight: FontWeight.bold),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _Row extends StatelessWidget {
  const _Row(this.label, this.value, {required this.icon, this.highlight = false});
  final String label;
  final String value;
  final IconData icon;
  final bool highlight;

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Row(
      children: [
        Container(
          padding: const EdgeInsets.all(8),
          decoration: BoxDecoration(
            color: (highlight ? kPrimaryGreen : Colors.blueGrey).withValues(alpha: 0.12),
            borderRadius: BorderRadius.circular(10),
          ),
          child: Icon(icon, color: highlight ? kPrimaryGreen : Colors.blueGrey, size: 20),
        ),
        const SizedBox(width: 14),
        Expanded(
          child: Text(
            label,
            style: TextStyle(
              fontSize: 15,
              fontWeight: FontWeight.w500,
              color: isDark ? Colors.white70 : kTextSecondary,
            ),
          ),
        ),
        Text(
          value,
          style: TextStyle(
            fontSize: 20,
            fontWeight: FontWeight.w800,
            color: highlight ? kPrimaryGreen : (isDark ? Colors.white : kTextPrimary),
          ),
        ),
      ],
    );
  }
}
