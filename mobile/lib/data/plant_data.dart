import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

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
    name: 'بەڕوو (Oak Tree)',
    description: 'درەختی ڕەسەنی دارستانەکانی ئەزمەڕ و گۆیژە. بەرگەی گەرما و وشکەساڵی دەگرێت.',
    points: 50,
    difficulty: 'مامناوەند',
    icon: Icons.park_rounded,
    color: Color(0xFF2E7D32),
    waterNeeded: 'کەمئاو',
  ),
  const PlantType(
    id: 'p2',
    name: 'سنەوبەر (Pine Tree)',
    description: 'هەمیشە سەوز و خێرا لە گەشەکردندا. هەوای سلێمانی پاک و سازگار دەکات.',
    points: 40,
    difficulty: 'ئاسان',
    icon: Icons.nature_rounded,
    color: Color(0xFF00796B),
    waterNeeded: 'مامناوەند',
  ),
  const PlantType(
    id: 'p3',
    name: 'چنار (Plane Tree)',
    description: 'درەختی هێمای سەرچناری سلێمانی. سێبەرێکی فراوان و بەهەیبەت دروست دەکات.',
    points: 45,
    difficulty: 'قورس',
    icon: Icons.forest_rounded,
    color: Color(0xFF1B5E20),
    waterNeeded: 'ئاوی زۆر',
  ),
  const PlantType(
    id: 'p4',
    name: 'زەیتوون (Olive Tree)',
    description: 'هێمای ئاشتی و بەرەکەت. زۆر کەمئاوە و تەمەندرێژترین درەختی ناوچەکەیە.',
    points: 45,
    difficulty: 'ئاسان',
    icon: Icons.eco_rounded,
    color: Color(0xFF558B2F),
    waterNeeded: 'کەمئاو',
  ),
  const PlantType(
    id: 'p5',
    name: 'هەنار (Pomegranate)',
    description: 'میوەدار و گوڵدار بە گوڵی سووری گەش. گونجاوە بۆ باخچەی ماڵان و گەڕەکەکان.',
    points: 35,
    difficulty: 'مامناوەند',
    icon: Icons.apple_rounded,
    color: Color(0xFFC62828),
    waterNeeded: 'مامناوەند',
  ),
  const PlantType(
    id: 'p6',
    name: 'هەنجیر (Fig Tree)',
    description: 'درەختی شیرین و پڕسێبەر. لە خاکە شاخاوییەکان زۆر بە باشی گەشە دەکات.',
    points: 30,
    difficulty: 'ئاسان',
    icon: Icons.spa_rounded,
    color: Color(0xFF43A047),
    waterNeeded: 'مامناوەند',
  ),
  const PlantType(
    id: 'p7',
    name: 'گوڵەباخ (Rose Bush)',
    description: 'گوڵێکی بۆنخۆشی ڕەسەن کە جوانییەکی تایبەت دەبەخشێتە کۆڵان و گەڕەکەکان.',
    points: 20,
    difficulty: 'مامناوەند',
    icon: Icons.local_florist_rounded,
    color: Color(0xFFD81B60),
    waterNeeded: 'ئاوی زۆر',
  ),
  const PlantType(
    id: 'p8',
    name: 'لاڤێندەر (Lavender)',
    description: 'بۆنخۆش و سەرنجڕاکێش بۆ پەپوولە و هەنگ. زۆر کەمئاوە و سەوز دەمێنێتەوە.',
    points: 25,
    difficulty: 'ئاسان',
    icon: Icons.grass_rounded,
    color: Color(0xFF8E24AA),
    waterNeeded: 'کەمئاو',
  ),
  const PlantType(
    id: 'p9',
    name: 'نەعنا و ڕێحانە (Herbs)',
    description: 'ڕووەکی سەوزی بەکەڵک و بۆندار. زوو گەشە دەکات و دەڕوێت.',
    points: 15,
    difficulty: 'ئاسان',
    icon: Icons.energy_savings_leaf_rounded,
    color: Color(0xFF00BFA5),
    waterNeeded: 'ئاوی زۆر',
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
        'name': 'بەڕوو (Oak Tree)',
        'typeId': 'p1',
        'level': 'ئاستی ٣ (پێگەیشتوو)',
        'status': 'تەندروستە',
        'iconCode': Icons.park_rounded.codePoint,
        'colorValue': const Color(0xFF2E7D32).toARGB32(),
        'plantedAt': DateTime.now().subtract(const Duration(days: 14)).toIso8601String(),
      },
      {
        'id': '2',
        'name': 'چنار (Plane Tree)',
        'typeId': 'p3',
        'level': 'ئاستی ٢ (لە گەشەدایە)',
        'status': 'پێویستی بە ئاوە',
        'iconCode': Icons.forest_rounded.codePoint,
        'colorValue': const Color(0xFF1B5E20).toARGB32(),
        'plantedAt': DateTime.now().subtract(const Duration(days: 6)).toIso8601String(),
      },
      {
        'id': '3',
        'name': 'گوڵەباخ (Rose Bush)',
        'typeId': 'p7',
        'level': 'ئاستی ١ (چەکەرەکردن)',
        'status': 'تەندروستە',
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
      'level': 'ئاستی ١ (چەکەرەکردن)',
      'status': 'تەندروستە',
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
    final wasThirsty = plant['status'] == 'پێویستی بە ئاوە';

    plant['status'] = 'تەندروستە';
    plant['lastWatered'] = DateTime.now().toIso8601String();

    // Small chance to level up when watered
    if (plant['level'] == 'ئاستی ١ (چەکەرەکردن)') {
      plant['level'] = 'ئاستی ٢ (لە گەشەدایە)';
    } else if (plant['level'] == 'ئاستی ٢ (لە گەشەدایە)' && wasThirsty) {
      plant['level'] = 'ئاستی ٣ (پێگەیشتوو)';
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
