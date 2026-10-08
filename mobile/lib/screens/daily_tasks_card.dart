import 'package:flutter/material.dart';

import '../api.dart';
import '../main.dart';
import '../strings.dart';
import '../theme.dart';

/// Today's three small goals (report, confirm, clean). A finished one can be claimed once for a
/// small bonus, which is held 24 hours like the other points.
class DailyTasksCard extends StatefulWidget {
  const DailyTasksCard({super.key, required this.refresh});
  final ValueNotifier<int> refresh;

  @override
  State<DailyTasksCard> createState() => _DailyTasksCardState();
}

class _DailyTasksCardState extends State<DailyTasksCard> {
  List<Map<String, dynamic>> _tasks = [];
  String? _busy;

  @override
  void initState() {
    super.initState();
    _load();
    widget.refresh.addListener(_load);
  }

  @override
  void dispose() {
    widget.refresh.removeListener(_load);
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final data = await Api.instance.tasks();
      if (mounted) setState(() => _tasks = List<Map<String, dynamic>>.from(data['tasks']));
    } catch (_) {
      // the home screen already shows connection problems; the card just stays as it was
    }
  }

  Future<void> _claim(String code) async {
    setState(() => _busy = code);
    try {
      final result = await Api.instance.claimTask(code);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(result['message'].toString())));
      widget.refresh.value++;
    } catch (e) {
      if (mounted) showError(context, e);
    } finally {
      if (mounted) setState(() => _busy = null);
    }
  }

  IconData _icon(String code) => switch (code) {
        'report' => Icons.add_a_photo_rounded,
        'confirm' => Icons.verified_rounded,
        _ => Icons.cleaning_services_rounded,
      };

  @override
  Widget build(BuildContext context) {
    if (_tasks.isEmpty) return const SizedBox.shrink();
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Container(
      margin: const EdgeInsets.only(bottom: 24),
      padding: const EdgeInsets.fromLTRB(16, 14, 16, 6),
      decoration: BoxDecoration(
        color: isDark ? kDarkCard : Colors.white,
        borderRadius: BorderRadius.circular(18),
        boxShadow: [
          BoxShadow(color: Colors.black.withValues(alpha: isDark ? 0.3 : 0.05), blurRadius: 12, offset: const Offset(0, 4)),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(S.dailyTasks, style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
          const SizedBox(height: 6),
          for (final t in _tasks)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 6),
              child: Row(
                children: [
                  CircleAvatar(
                    radius: 18,
                    backgroundColor: (t['complete'] == true ? kPrimaryGreen : Colors.blueGrey).withValues(alpha: 0.12),
                    child: Icon(_icon(t['code'].toString()),
                        size: 18, color: t['complete'] == true ? kPrimaryGreen : Colors.blueGrey),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(t['title'].toString(), style: const TextStyle(fontWeight: FontWeight.w600)),
                        const SizedBox(height: 4),
                        ClipRRect(
                          borderRadius: BorderRadius.circular(6),
                          child: LinearProgressIndicator(
                            value: (t['done'] as num) / (t['target'] as num),
                            minHeight: 6,
                            color: kPrimaryGreen,
                            backgroundColor: Colors.grey.withValues(alpha: 0.2),
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(width: 12),
                  if (t['claimed'] == true)
                    const Chip(label: Text(S.bonusClaimed), visualDensity: VisualDensity.compact)
                  else
                    FilledButton(
                      onPressed: t['complete'] == true && _busy == null ? () => _claim(t['code'].toString()) : null,
                      style: FilledButton.styleFrom(
                        minimumSize: const Size(0, 36),
                        padding: const EdgeInsets.symmetric(horizontal: 12),
                        textStyle: const TextStyle(fontSize: 13, fontWeight: FontWeight.bold),
                      ),
                      child: Text(S.bonus(t['bonus'])),
                    ),
                ],
              ),
            ),
        ],
      ),
    );
  }
}
