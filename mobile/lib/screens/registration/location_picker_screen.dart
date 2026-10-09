import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';

import '../../api.dart';
import '../../location.dart';
import '../../strings.dart';
import '../../theme.dart';

/// Pick where a household or business is: tap the map. Starts at the pin already chosen, else at the
/// phone's position when it is inside the service area, else at the server's map centre (a simulator
/// sits in Cupertino). Returns the LatLng, or null when the person goes back.
class LocationPickerScreen extends StatefulWidget {
  const LocationPickerScreen({super.key, this.initial, required this.note});

  final LatLng? initial;
  final String note;

  @override
  State<LocationPickerScreen> createState() => _LocationPickerScreenState();
}

class _LocationPickerScreenState extends State<LocationPickerScreen> {
  final _map = MapController();
  late LatLng? _pin = widget.initial;

  static LatLng get _centre {
    final c = Api.instance.config?['map_center'];
    return c is List && c.length == 2 ? LatLng((c[0] as num).toDouble(), (c[1] as num).toDouble())
        : const LatLng(35.5613, 45.4373);
  }

  /// Inside the server's service area (min_lat, min_lon, max_lat, max_lon); true when it is not known.
  static bool inArea(LatLng p) {
    final a = Api.instance.config?['service_area'];
    if (a is! List || a.length != 4) return true;
    final box = a.map((v) => (v as num).toDouble()).toList();
    return p.latitude >= box[0] && p.longitude >= box[1] && p.latitude <= box[2] && p.longitude <= box[3];
  }

  @override
  void initState() {
    super.initState();
    if (_pin == null) _goToMe(quiet: true);
  }

  Future<void> _goToMe({bool quiet = false}) async {
    try {
      final here = await currentPosition();
      final point = LatLng(here.latitude, here.longitude);
      if (!mounted || !inArea(point)) return;
      setState(() => _pin ??= point);
      _map.move(point, 17);
    } catch (e) {
      if (!quiet && mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final outside = _pin != null && !inArea(_pin!);
    return Scaffold(
      appBar: AppBar(title: const Text(S.pickLocationTitle)),
      floatingActionButton: FloatingActionButton.small(
        tooltip: S.myLocation,
        onPressed: _goToMe,
        child: const Icon(Icons.my_location_rounded),
      ),
      body: Column(
        children: [
          Expanded(
            child: FlutterMap(
              mapController: _map,
              options: MapOptions(
                initialCenter: _pin ?? _centre,
                initialZoom: _pin == null ? 13 : 17,
                onTap: (_, point) => setState(() => _pin = point),
              ),
              children: [
                TileLayer(
                  urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
                  userAgentPackageName: 'krd.greenlegacy.slemani',
                ),
                if (_pin != null)
                  MarkerLayer(markers: [
                    Marker(
                      point: _pin!,
                      width: 44,
                      height: 44,
                      alignment: Alignment.topCenter,
                      child: Icon(Icons.location_on_rounded, size: 44, color: outside ? red : kDarkGreen),
                    ),
                  ]),
              ],
            ),
          ),
          SafeArea(
            top: false,
            child: Padding(
              padding: const EdgeInsets.fromLTRB(16, 12, 16, 12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Text(outside ? S.outsideServiceArea : (_pin == null ? S.pickLocationHint : widget.note),
                      style: TextStyle(color: outside ? red : Colors.grey.shade700, fontSize: 13)),
                  const SizedBox(height: 10),
                  ElevatedButton.icon(
                    onPressed: _pin == null || outside ? null : () => Navigator.of(context).pop(_pin),
                    icon: const Icon(Icons.check_rounded),
                    label: const Text(S.confirmLocation),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: kPrimaryGreen,
                      foregroundColor: Colors.white,
                      minimumSize: const Size.fromHeight(50),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
