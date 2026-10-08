import 'package:camera/camera.dart';
import 'package:flutter/material.dart';

import '../api.dart';
import '../strings.dart';

/// Opens the back camera in the app. There is deliberately no gallery button anywhere:
/// photos and cleanup frames must be taken live.
///
/// The iOS Simulator (and an emulator without a webcam) has no camera at all. Then, and only then,
/// each shot is a synthetic picture from the rehearsal server (`simulatorPath`, see
/// backend/app/simulator.py), so the whole loop can be practised without a phone.
class CameraHolder {
  CameraHolder({this.simulatorPath});

  /// Server path that stands in for shot number `shot` when there is no camera.
  final String Function(int shot)? simulatorPath;
  CameraController? controller;
  bool simulated = false;

  Future<void> open() async {
    final cameras = await availableCameras();
    if (cameras.isEmpty) {
      if (simulatorPath == null) throw CameraException('noCamera', null);
      simulated = true;
      return;
    }
    final back = cameras.firstWhere((c) => c.lensDirection == CameraLensDirection.back,
        orElse: () => cameras.first);
    final c = CameraController(back, ResolutionPreset.medium, enableAudio: false);
    await c.initialize();
    controller = c;
  }

  bool get ready => simulated || (controller?.value.isInitialized ?? false);

  Future<XFile> shoot({int shot = 0}) async {
    if (simulated) return XFile.fromData(await Api.instance.simulatedPhoto(simulatorPath!(shot)));
    return controller!.takePicture();
  }

  void dispose() => controller?.dispose();
}

class CameraBox extends StatelessWidget {
  const CameraBox({super.key, required this.holder, this.error});
  final CameraHolder holder;
  final String? error;

  @override
  Widget build(BuildContext context) {
    if (error != null) {
      return Center(child: Text(error!, style: const TextStyle(color: Colors.white)));
    }
    if (holder.simulated) {
      return const Center(
        child: Padding(
          padding: EdgeInsets.all(32),
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            Icon(Icons.phone_iphone, size: 64, color: Colors.white54),
            SizedBox(height: 12),
            Text(S.simulatedCamera, textAlign: TextAlign.center, style: TextStyle(color: Colors.white, fontSize: 16)),
          ]),
        ),
      );
    }
    if (!holder.ready) {
      return const Center(child: CircularProgressIndicator(color: Colors.white));
    }
    return Center(child: CameraPreview(holder.controller!));
  }
}

String cameraErrorText(Object e) => e is CameraException ? '${S.cameraError}: ${e.code}' : S.cameraError;
