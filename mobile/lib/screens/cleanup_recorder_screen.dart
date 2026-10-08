import 'dart:async';

import 'package:camera/camera.dart' show XFile;
import 'package:flutter/material.dart';

import '../api.dart';
import '../location.dart';
import '../main.dart';
import '../strings.dart';
import '../theme.dart';
import 'camera_box.dart';
import 'result_screen.dart';

/// Cleanup recorder: the random instruction sits on top of the live camera. "Recording" takes
/// 8 frames over about 6 seconds in the app (no gallery, no video file to fake), then sends them.
class CleanupRecorderScreen extends StatefulWidget {
  const CleanupRecorderScreen({super.key, required this.spot, required this.challenge});
  final Map<String, dynamic> spot;
  final Map<String, dynamic> challenge;

  @override
  State<CleanupRecorderScreen> createState() => _CleanupRecorderScreenState();
}

class _CleanupRecorderScreenState extends State<CleanupRecorderScreen> {
  static const frameCount = 8;
  static const frameGap = Duration(milliseconds: 650);

  late final _camera = CameraHolder(
      simulatorPath: (shot) => '/sim/cleanup-frame?report_id=${widget.spot['id']}'
          '&instruction=${widget.challenge['instruction']}&frame=$shot&count=$frameCount');
  String? _cameraError;
  int _taken = 0;
  bool _recording = false;
  bool _sending = false;
  late final DateTime _deadline = DateTime.now().add(const Duration(minutes: 5));
  Timer? _clock;

  @override
  void initState() {
    super.initState();
    _camera.open().then((_) {
      if (mounted) setState(() {});
    }).catchError((Object e) {
      if (mounted) setState(() => _cameraError = cameraErrorText(e));
    });
    _clock = Timer.periodic(const Duration(seconds: 1), (_) {
      if (mounted) setState(() {});
    });
  }

  @override
  void dispose() {
    _clock?.cancel();
    _camera.dispose();
    super.dispose();
  }

  Future<void> _record() async {
    setState(() {
      _recording = true;
      _taken = 0;
    });
    final frames = <XFile>[];
    try {
      for (var i = 0; i < frameCount; i++) {
        frames.add(await _camera.shoot(shot: i));
        if (mounted) setState(() => _taken = i + 1);
        await Future<void>.delayed(frameGap);
      }
      setState(() {
        _recording = false;
        _sending = true;
      });
      final pos = await currentPosition();
      final result = await Api.instance.cleanup(widget.spot['id'] as int,
          widget.challenge['id'] as int, frames, pos.latitude, pos.longitude);
      if (!mounted) return;
      Navigator.of(context).pushReplacement(
        MaterialPageRoute(builder: (_) => ResultScreen(result: result)),
      );
    } catch (e) {
      if (mounted) {
        showError(context, e);
        setState(() {
          _recording = false;
          _sending = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final left = _deadline.difference(DateTime.now());
    final expired = left.isNegative;
    final mm = S.digits(left.inMinutes.clamp(0, 99));
    final ss = S.digits((left.inSeconds % 60).clamp(0, 59).toString().padLeft(2, '0'));

    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(
        title: const Text(S.illClean, style: TextStyle(fontWeight: FontWeight.bold)),
        backgroundColor: Colors.black,
        foregroundColor: Colors.white,
        elevation: 0,
      ),
      body: Stack(
        children: [
          Positioned.fill(child: CameraBox(holder: _camera, error: _cameraError)),
          // The challenge instruction card over the camera view
          Positioned(
            top: 16,
            left: 16,
            right: 16,
            child: Container(
              padding: const EdgeInsets.all(18),
              decoration: BoxDecoration(
                color: kDarkCard.withValues(alpha: 0.92),
                borderRadius: BorderRadius.circular(20),
                border: Border.all(color: kPrimaryGreen.withValues(alpha: 0.4), width: 1.5),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withValues(alpha: 0.4),
                    blurRadius: 16,
                    offset: const Offset(0, 4),
                  ),
                ],
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                        decoration: BoxDecoration(
                          color: kPrimaryGreen.withValues(alpha: 0.2),
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: const Text(
                          S.instruction,
                          style: TextStyle(
                            color: kPrimaryGreen,
                            fontSize: 12,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ),
                      const Spacer(),
                      Row(
                        children: [
                          Icon(
                            Icons.timer_outlined,
                            size: 16,
                            color: expired ? const Color(0xFFFF5252) : Colors.white70,
                          ),
                          const SizedBox(width: 4),
                          Text(
                            '$mm:$ss',
                            style: TextStyle(
                              color: expired ? const Color(0xFFFF5252) : Colors.white,
                              fontWeight: FontWeight.w700,
                              fontSize: 14,
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                  const SizedBox(height: 10),
                  Text(
                    widget.challenge['instruction_text'].toString(),
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 18,
                      fontWeight: FontWeight.w700,
                      height: 1.3,
                    ),
                  ),
                ],
              ),
            ),
          ),
          if (_recording || _sending)
            Positioned(
              left: 32,
              right: 32,
              bottom: 120,
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
                decoration: BoxDecoration(
                  color: Colors.black.withValues(alpha: 0.8),
                  borderRadius: BorderRadius.circular(16),
                ),
                child: Column(
                  children: [
                    ClipRRect(
                      borderRadius: BorderRadius.circular(8),
                      child: LinearProgressIndicator(
                        value: _sending ? null : _taken / frameCount,
                        color: kPrimaryGreen,
                        backgroundColor: Colors.white24,
                        minHeight: 8,
                      ),
                    ),
                    const SizedBox(height: 10),
                    Text(
                      _sending ? S.verifying : '${S.recording} ($_taken/$frameCount)',
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 15,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          Positioned(
            left: 24,
            right: 24,
            bottom: 36,
            child: FilledButton.icon(
              onPressed: _recording || _sending || !_camera.ready || expired ? null : _record,
              style: FilledButton.styleFrom(
                backgroundColor: const Color(0xFFFF5252),
                foregroundColor: Colors.white,
                minimumSize: const Size.fromHeight(56),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                elevation: 4,
              ),
              icon: const Icon(Icons.fiber_manual_record, color: Colors.white),
              label: Text(
                _recording ? S.recording : S.record,
                style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
