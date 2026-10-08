import 'package:flutter/material.dart';

import '../data/plant_data.dart';
import '../theme.dart';
import 'plant_selection_screen.dart';

class GardenScreen extends StatefulWidget {
  const GardenScreen({super.key});

  @override
  State<GardenScreen> createState() => _GardenScreenState();
}

class _GardenScreenState extends State<GardenScreen> {
  @override
  void initState() {
    super.initState();
    GardenManager.instance.init();
  }

  void _water(int index, String name) async {
    final earned = await GardenManager.instance.waterPlant(index);
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(
          earned
              ? '$name بە سەرکەوتوویی ئاو درا! 💧 (+10 خاڵ بەدەستهات)'
              : '$name پێشتر ئاو دراوە و تەندروستە! 🌱',
        ),
        backgroundColor: earned ? kPrimaryGreen : Colors.teal,
        duration: const Duration(seconds: 2),
      ),
    );
  }

  void _remove(int index, String name) {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('لابردنی ڕووەک', style: TextStyle(fontWeight: FontWeight.bold)),
        content: Text('ئایا دڵنیایت لە لابردنی $name لە باخچەکەتدا؟'),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(),
            child: const Text('پاشگەزبوونەوە', style: TextStyle(color: Colors.grey)),
          ),
          ElevatedButton(
            onPressed: () {
              GardenManager.instance.removePlant(index);
              Navigator.of(ctx).pop();
              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(
                  content: Text('$name لە باخچەکەت لابرا'),
                  backgroundColor: Colors.redAccent,
                  duration: const Duration(seconds: 2),
                ),
              );
            },
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.redAccent,
              foregroundColor: Colors.white,
              elevation: 0,
            ),
            child: const Text('بەڵێ، لایببە'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return AnimatedBuilder(
      animation: GardenManager.instance,
      builder: (context, _) {
        final plants = GardenManager.instance.myPlants;
        final thirstyCount = plants.where((p) => p['status'] == 'پێویستی بە ئاوە').length;

        return Scaffold(
          backgroundColor: isDark ? kDarkSurface : kBackgroundLight,
          body: ListView(
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 90),
            children: [
              // Header Summary Card
              Container(
                padding: const EdgeInsets.all(20),
                decoration: BoxDecoration(
                  gradient: const LinearGradient(
                    colors: [Color(0xFF00C853), Color(0xFF1B5E20)],
                    begin: Alignment.topRight,
                    end: Alignment.bottomLeft,
                  ),
                  borderRadius: BorderRadius.circular(24),
                  boxShadow: [
                    BoxShadow(
                      color: kPrimaryGreen.withValues(alpha: 0.35),
                      blurRadius: 18,
                      offset: const Offset(0, 6),
                    ),
                  ],
                ),
                child: Column(
                  children: [
                    Row(
                      children: [
                        Container(
                          width: 58,
                          height: 58,
                          decoration: BoxDecoration(
                            shape: BoxShape.circle,
                            color: Colors.white.withValues(alpha: 0.2),
                          ),
                          child: const Icon(Icons.forest_rounded, color: Colors.white, size: 34),
                        ),
                        const SizedBox(width: 16),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              const Text(
                                'باخچەی سەوزی سلێمانی',
                                style: TextStyle(
                                  color: Colors.white70,
                                  fontSize: 13,
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                              const SizedBox(height: 2),
                              Text(
                                '${plants.length} درەخت و ڕووەک',
                                style: const TextStyle(
                                  color: Colors.white,
                                  fontSize: 22,
                                  fontWeight: FontWeight.w800,
                                ),
                              ),
                            ],
                          ),
                        ),
                        ElevatedButton.icon(
                          onPressed: () {
                            Navigator.of(context).push(
                              MaterialPageRoute(builder: (_) => const PlantSelectionScreen()),
                            );
                          },
                          icon: const Icon(Icons.add_rounded, size: 18),
                          label: const Text('نەمامی نوێ', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
                          style: ElevatedButton.styleFrom(
                            backgroundColor: Colors.white,
                            foregroundColor: kDarkGreen,
                            elevation: 0,
                            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                            minimumSize: Size.zero,
                          ),
                        ),
                      ],
                    ),
                    if (thirstyCount > 0) ...[
                      const SizedBox(height: 14),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                        decoration: BoxDecoration(
                          color: Colors.orange.withValues(alpha: 0.25),
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(color: Colors.orange.withValues(alpha: 0.4)),
                        ),
                        child: Row(
                          children: [
                            const Icon(Icons.water_drop_rounded, color: Colors.amberAccent, size: 18),
                            const SizedBox(width: 8),
                            Expanded(
                              child: Text(
                                '$thirstyCount ڕووەک پێویستیان بە ئاوپڕژێنە! ئاویان بدە بۆ بەدەستهێنانی خاڵ.',
                                style: const TextStyle(color: Colors.white, fontSize: 12, fontWeight: FontWeight.bold),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ],
                ),
              ),

              const SizedBox(height: 22),

              // Title Row
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(
                    'درەختە چێنراوەکانی تۆ 🌱',
                    style: TextStyle(
                      fontSize: 17,
                      fontWeight: FontWeight.bold,
                      color: isDark ? Colors.white : kTextPrimary,
                    ),
                  ),
                  Text(
                    '${plants.length} بەردەستە',
                    style: TextStyle(
                      fontSize: 13,
                      color: isDark ? Colors.white60 : kTextSecondary,
                    ),
                  ),
                ],
              ),

              const SizedBox(height: 14),

              // Grid of Plants
              GridView.builder(
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                  crossAxisCount: 2,
                  crossAxisSpacing: 14,
                  mainAxisSpacing: 14,
                  childAspectRatio: 0.76,
                ),
                itemCount: plants.length + 1,
                itemBuilder: (context, index) {
                  if (index == plants.length) {
                    return _buildAddPlantCard(context, isDark);
                  }
                  final plant = plants[index];
                  return _buildPlantCard(context, index, plant, isDark);
                },
              ),
            ],
          ),
        );
      },
    );
  }

  Widget _buildPlantCard(
    BuildContext context,
    int index,
    Map<String, dynamic> plant,
    bool isDark,
  ) {
    final name = plant['name']?.toString() ?? 'ڕووەک';
    final level = plant['level']?.toString() ?? 'ئاستی ١';
    final status = plant['status']?.toString() ?? 'تەندروستە';
    final needsWater = status == 'پێویستی بە ئاوە';
    final iconData = plantIcon(plant['iconCode']);
    final color = Color(plant['colorValue'] as int? ?? kPrimaryGreen.toARGB32());

    return Container(
      decoration: BoxDecoration(
        color: isDark ? kDarkCard : Colors.white,
        borderRadius: BorderRadius.circular(20),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: isDark ? 0.3 : 0.05),
            blurRadius: 10,
            offset: const Offset(0, 3),
          ),
        ],
        border: needsWater
            ? Border.all(color: Colors.orange.withValues(alpha: 0.6), width: 1.5)
            : null,
      ),
      padding: const EdgeInsets.all(12),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          // Top row: Water drop and Delete button
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              GestureDetector(
                onTap: () => _remove(index, name),
                child: Container(
                  padding: const EdgeInsets.all(4),
                  decoration: BoxDecoration(
                    color: Colors.grey.withValues(alpha: 0.15),
                    shape: BoxShape.circle,
                  ),
                  child: const Icon(Icons.close_rounded, size: 14, color: Colors.grey),
                ),
              ),
              if (needsWater)
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                  decoration: BoxDecoration(
                    color: Colors.orange.withValues(alpha: 0.15),
                    borderRadius: BorderRadius.circular(6),
                  ),
                  child: const Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(Icons.water_drop_rounded, size: 12, color: Colors.orange),
                      SizedBox(width: 2),
                      Text('تینووە', style: TextStyle(color: Colors.orange, fontSize: 10, fontWeight: FontWeight.bold)),
                    ],
                  ),
                ),
            ],
          ),

          // Center Icon
          Container(
            width: 60,
            height: 60,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: color.withValues(alpha: 0.12),
            ),
            child: Icon(iconData, color: color, size: 34),
          ),

          // Names & Level
          Column(
            children: [
              Text(
                name,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                textAlign: TextAlign.center,
                style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14),
              ),
              const SizedBox(height: 2),
              Text(
                level,
                style: TextStyle(
                  color: isDark ? Colors.white60 : kTextSecondary,
                  fontSize: 11,
                  fontWeight: FontWeight.w500,
                ),
              ),
            ],
          ),

          // Water Button
          SizedBox(
            width: double.infinity,
            height: 34,
            child: ElevatedButton.icon(
              onPressed: () => _water(index, name),
              icon: Icon(
                needsWater ? Icons.water_drop_rounded : Icons.check_circle_outline_rounded,
                size: 14,
              ),
              label: Text(
                needsWater ? 'ئاو بدە 💧' : 'تەندروستە 🌱',
                style: const TextStyle(fontSize: 11, fontWeight: FontWeight.bold),
              ),
              style: ElevatedButton.styleFrom(
                backgroundColor: needsWater ? const Color(0xFF1E88E5) : kPrimaryGreen.withValues(alpha: 0.15),
                foregroundColor: needsWater ? Colors.white : kPrimaryGreen,
                elevation: needsWater ? 2 : 0,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                padding: EdgeInsets.zero,
                minimumSize: Size.zero,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildAddPlantCard(BuildContext context, bool isDark) {
    return GestureDetector(
      onTap: () {
        Navigator.of(context).push(
          MaterialPageRoute(builder: (_) => const PlantSelectionScreen()),
        );
      },
      child: Container(
        decoration: BoxDecoration(
          color: isDark ? kDarkCard.withValues(alpha: 0.5) : Colors.white.withValues(alpha: 0.7),
          borderRadius: BorderRadius.circular(20),
          border: Border.all(
            color: kPrimaryGreen.withValues(alpha: 0.4),
            width: 1.5,
          ),
        ),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: kPrimaryGreen.withValues(alpha: 0.12),
                shape: BoxShape.circle,
              ),
              child: const Icon(Icons.add_rounded, size: 30, color: kPrimaryGreen),
            ),
            const SizedBox(height: 10),
            const Text(
              'ڕوواندنی ڕووەکی نوێ',
              style: TextStyle(
                fontWeight: FontWeight.bold,
                fontSize: 13,
                color: kPrimaryGreen,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              '+ خاڵی ژینگەیی',
              style: TextStyle(
                fontSize: 11,
                color: Colors.grey.shade500,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
