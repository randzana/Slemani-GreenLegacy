import 'package:flutter/material.dart';

import '../data/plant_data.dart';
import '../strings.dart';
import '../theme.dart';

class PlantSelectionScreen extends StatefulWidget {
  const PlantSelectionScreen({super.key});

  @override
  State<PlantSelectionScreen> createState() => _PlantSelectionScreenState();
}

class _PlantSelectionScreenState extends State<PlantSelectionScreen> {
  String _selectedCategory = 'all';

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    final categories = [
      {'id': 'all', 'label': S.allKinds},
      {'id': 'tree', 'label': S.bigTrees},
      {'id': 'fruit', 'label': S.fruitTrees},
      {'id': 'flower', 'label': S.flowersAndHerbs},
    ];

    final filteredPlants = kPlantTypes.where((p) {
      if (_selectedCategory == 'tree') {
        return p.id == 'p1' || p.id == 'p2' || p.id == 'p3' || p.id == 'p4';
      } else if (_selectedCategory == 'fruit') {
        return p.id == 'p5' || p.id == 'p6';
      } else if (_selectedCategory == 'flower') {
        return p.id == 'p7' || p.id == 'p8' || p.id == 'p9';
      }
      return true;
    }).toList();

    return Scaffold(
      backgroundColor: isDark ? kDarkSurface : kBackgroundLight,
      appBar: AppBar(
        title: const Text(S.choosePlant, style: TextStyle(fontWeight: FontWeight.bold)),
        elevation: 0,
      ),
      body: Column(
        children: [
          // Category filter row
          Container(
            height: 52,
            margin: const EdgeInsets.symmetric(vertical: 8),
            child: ListView.separated(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              scrollDirection: Axis.horizontal,
              itemCount: categories.length,
              separatorBuilder: (_, __) => const SizedBox(width: 8),
              itemBuilder: (context, index) {
                final cat = categories[index];
                final isSelected = _selectedCategory == cat['id'];
                return ChoiceChip(
                  label: Text(
                    cat['label']!,
                    style: TextStyle(
                      color: isSelected ? Colors.white : (isDark ? Colors.white70 : kTextPrimary),
                      fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
                      fontSize: 13,
                    ),
                  ),
                  selected: isSelected,
                  selectedColor: kPrimaryGreen,
                  backgroundColor: isDark ? kDarkCard : Colors.white,
                  showCheckmark: false,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                  side: BorderSide(
                    color: isSelected ? kPrimaryGreen : Colors.grey.withValues(alpha: 0.2),
                  ),
                  onSelected: (val) {
                    if (val) setState(() => _selectedCategory = cat['id']!);
                  },
                );
              },
            ),
          ),

          // Plant types list
          Expanded(
            child: ListView.builder(
              padding: const EdgeInsets.fromLTRB(16, 4, 16, 24),
              itemCount: filteredPlants.length,
              itemBuilder: (context, index) {
                final plant = filteredPlants[index];
                return Container(
                  margin: const EdgeInsets.only(bottom: 12),
                  decoration: BoxDecoration(
                    color: isDark ? kDarkCard : Colors.white,
                    borderRadius: BorderRadius.circular(18),
                    boxShadow: [
                      BoxShadow(
                        color: Colors.black.withValues(alpha: isDark ? 0.3 : 0.04),
                        blurRadius: 10,
                        offset: const Offset(0, 3),
                      ),
                    ],
                  ),
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Container(
                              width: 54,
                              height: 54,
                              decoration: BoxDecoration(
                                color: plant.color.withValues(alpha: 0.15),
                                borderRadius: BorderRadius.circular(14),
                              ),
                              child: Icon(plant.icon, color: plant.color, size: 30),
                            ),
                            const SizedBox(width: 14),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    plant.name,
                                    style: const TextStyle(
                                      fontWeight: FontWeight.bold,
                                      fontSize: 16,
                                    ),
                                  ),
                                  const SizedBox(height: 4),
                                  Text(
                                    plant.description,
                                    style: TextStyle(
                                      color: isDark ? Colors.white60 : kTextSecondary,
                                      fontSize: 13,
                                      height: 1.3,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 14),
                        Row(
                          children: [
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                              decoration: BoxDecoration(
                                color: kPrimaryGreen.withValues(alpha: 0.12),
                                borderRadius: BorderRadius.circular(8),
                              ),
                              child: Text(
                                '+${plant.points} ${S.points}',
                                style: const TextStyle(
                                  color: kPrimaryGreen,
                                  fontWeight: FontWeight.bold,
                                  fontSize: 12,
                                ),
                              ),
                            ),
                            const SizedBox(width: 8),
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                              decoration: BoxDecoration(
                                color: Colors.blue.withValues(alpha: 0.12),
                                borderRadius: BorderRadius.circular(8),
                              ),
                              child: Text(
                                S.waterNeed(plant.waterNeeded),
                                style: const TextStyle(
                                  color: Colors.blue,
                                  fontWeight: FontWeight.w600,
                                  fontSize: 12,
                                ),
                              ),
                            ),
                            const SizedBox(width: 8),
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                              decoration: BoxDecoration(
                                color: Colors.amber.withValues(alpha: 0.12),
                                borderRadius: BorderRadius.circular(8),
                              ),
                              child: Text(
                                plant.difficulty,
                                style: const TextStyle(
                                  color: Colors.amber,
                                  fontWeight: FontWeight.w600,
                                  fontSize: 12,
                                ),
                              ),
                            ),
                            const Spacer(),
                            ElevatedButton(
                              onPressed: () async {
                                await GardenManager.instance.addPlant(plant);
                                if (!context.mounted) return;
                                ScaffoldMessenger.of(context).showSnackBar(
                                  SnackBar(
                                    content: Text(S.planted(plant.name, plant.points)),
                                    backgroundColor: kPrimaryGreen,
                                    duration: const Duration(seconds: 2),
                                  ),
                                );
                                Navigator.of(context).pop();
                              },
                              style: ElevatedButton.styleFrom(
                                backgroundColor: kPrimaryGreen,
                                foregroundColor: Colors.white,
                                elevation: 0,
                                padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 8),
                                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                                minimumSize: Size.zero,
                              ),
                              child: const Text(S.plantIt, style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}
