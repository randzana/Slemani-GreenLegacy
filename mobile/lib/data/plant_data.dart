import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../strings.dart';

class PlantType {
  final String id;
  final String name;
  final String description;
  final int points;
  final String difficulty;
  final IconData icon;
  final Color color;
  final String waterNeeded;

  const PlantType({
    required this.id,
    required this.name,
    required this.description,
    required this.points,
    required this.difficulty,
    required this.icon,
    required this.color,
    required this.waterNeeded,
  });
}

final List<PlantType> kPlantTypes = [
  const PlantType(
    id: 'p1',
    name: S.plantOak,
    description: S.plantOakAbout,
    points: 50,
    difficulty: S.difficultyMedium,
    icon: Icons.park_rounded,
    color: Color(0xFF2E7D32),
    waterNeeded: S.waterLow,
  ),
  const PlantType(
    id: 'p2',
    name: S.plantPine,
    description: S.plantPineAbout,
    points: 40,
    difficulty: S.difficultyEasy,
    icon: Icons.nature_rounded,
    color: Color(0xFF00796B),
    waterNeeded: S.waterMedium,
  ),
  const PlantType(
    id: 'p3',
    name: S.plantPlane,
    description: S.plantPlaneAbout,
    points: 45,
    difficulty: S.difficultyHard,
    icon: Icons.forest_rounded,
    color: Color(0xFF1B5E20),
    waterNeeded: S.waterHigh,
  ),
  const PlantType(
    id: 'p4',
    name: S.plantOlive,
    description: S.plantOliveAbout,
    points: 45,
    difficulty: S.difficultyEasy,
    icon: Icons.eco_rounded,
    color: Color(0xFF558B2F),
    waterNeeded: S.waterLow,
  ),
  const PlantType(
    id: 'p5',
    name: S.plantPomegranate,
    description: S.plantPomegranateAbout,
    points: 35,
    difficulty: S.difficultyMedium,
    icon: Icons.apple_rounded,
    color: Color(0xFFC62828),
    waterNeeded: S.waterMedium,
  ),
  const PlantType(
    id: 'p6',
    name: S.plantFig,
    description: S.plantFigAbout,
    points: 30,
    difficulty: S.difficultyEasy,
    icon: Icons.spa_rounded,
    color: Color(0xFF43A047),
    waterNeeded: S.waterMedium,
  ),
  const PlantType(
    id: 'p7',
    name: S.plantRose,
    description: S.plantRoseAbout,
    points: 20,
    difficulty: S.difficultyMedium,
    icon: Icons.local_florist_rounded,
    color: Color(0xFFD81B60),
    waterNeeded: S.waterHigh,
  ),
  const PlantType(
    id: 'p8',
    name: S.plantLavender,
    description: S.plantLavenderAbout,
    points: 25,
    difficulty: S.difficultyEasy,
    icon: Icons.grass_rounded,
    color: Color(0xFF8E24AA),
    waterNeeded: S.waterLow,
  ),
  const PlantType(
    id: 'p9',
    name: S.plantHerbs,
    description: S.plantHerbsAbout,
    points: 15,
    difficulty: S.difficultyEasy,
    icon: Icons.energy_savings_leaf_rounded,
    color: Color(0xFF00BFA5),
    waterNeeded: S.waterHigh,
  ),
];

/// Saved plants keep their icon as a code point. A release build only works when every IconData is
/// a constant (icon tree shaking), so look the code point up among the plant icons instead of
/// building a new IconData from it.
IconData plantIcon(Object? codePoint) {
  for (final type in kPlantTypes) {
    if (type.icon.codePoint == codePoint) return type.icon;
  }
  return Icons.park_rounded;
}

/// The garden lives only on this phone. Each plant's 'status' and 'level' are saved as their
/// Kurdish text (S.plantHealthy, S.plantLevel1, ...) and compared on the next start, so those
/// values in strings.dart must stay exactly as they are.
class GardenManager extends ChangeNotifier {
  GardenManager._();
  static final GardenManager instance = GardenManager._();

  List<Map<String, dynamic>> _myPlants = [];
  List<Map<String, dynamic>> get myPlants => List.unmodifiable(_myPlants);

  bool _initialized = false;

  Future<void> init() async {
    if (_initialized) return;
    _initialized = true;
    final prefs = await SharedPreferences.getInstance();
    final jsonStr = prefs.getString('digital_garden_plants');
    if (jsonStr != null && jsonStr.isNotEmpty) {
      try {
        final List<dynamic> list = jsonDecode(jsonStr);
        _myPlants = list.map((e) => Map<String, dynamic>.from(e as Map)).toList();
      } catch (_) {
        _loadDefaultPlants();
      }
    } else {
      _loadDefaultPlants();
    }
    notifyListeners();
  }

  void _loadDefaultPlants() {
    _myPlants = [
      {
        'id': '1',
        'name': S.plantOak,
        'typeId': 'p1',
        'level': S.plantLevel3,
        'status': S.plantHealthy,
        'iconCode': Icons.park_rounded.codePoint,
        'colorValue': const Color(0xFF2E7D32).toARGB32(),
        'plantedAt': DateTime.now().subtract(const Duration(days: 14)).toIso8601String(),
      },
      {
        'id': '2',
        'name': S.plantPlane,
        'typeId': 'p3',
        'level': S.plantLevel2,
        'status': S.plantThirsty,
        'iconCode': Icons.forest_rounded.codePoint,
        'colorValue': const Color(0xFF1B5E20).toARGB32(),
        'plantedAt': DateTime.now().subtract(const Duration(days: 6)).toIso8601String(),
      },
      {
        'id': '3',
        'name': S.plantRose,
        'typeId': 'p7',
        'level': S.plantLevel1,
        'status': S.plantHealthy,
        'iconCode': Icons.local_florist_rounded.codePoint,
        'colorValue': const Color(0xFFD81B60).toARGB32(),
        'plantedAt': DateTime.now().subtract(const Duration(days: 2)).toIso8601String(),
      },
    ];
    _persist();
  }

  Future<void> _persist() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString('digital_garden_plants', jsonEncode(_myPlants));
    } catch (_) {}
  }

  Future<void> addPlant(PlantType type) async {
    _myPlants.add({
      'id': DateTime.now().millisecondsSinceEpoch.toString(),
      'name': type.name,
      'typeId': type.id,
      'level': S.plantLevel1,
      'status': S.plantHealthy,
      'iconCode': type.icon.codePoint,
      'colorValue': type.color.toARGB32(),
      'plantedAt': DateTime.now().toIso8601String(),
    });
    await _persist();
    notifyListeners();
  }

  Future<bool> waterPlant(int index) async {
    if (index < 0 || index >= _myPlants.length) return false;
    final plant = _myPlants[index];
    final wasThirsty = plant['status'] == S.plantThirsty;

    plant['status'] = S.plantHealthy;
    plant['lastWatered'] = DateTime.now().toIso8601String();

    // Small chance to level up when watered
    if (plant['level'] == S.plantLevel1) {
      plant['level'] = S.plantLevel2;
    } else if (plant['level'] == S.plantLevel2 && wasThirsty) {
      plant['level'] = S.plantLevel3;
    }

    await _persist();
    notifyListeners();
    return wasThirsty;
  }

  Future<void> removePlant(int index) async {
    if (index < 0 || index >= _myPlants.length) return;
    _myPlants.removeAt(index);
    await _persist();
    notifyListeners();
  }
}
