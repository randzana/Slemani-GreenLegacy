import 'package:flutter/material.dart';

import '../strings.dart';
import '../theme.dart';

/// Result: verified, sent to review, or rejected — with the reason and the points.
class ResultScreen extends StatelessWidget {
  const ResultScreen({super.key, required this.result});
  final Map<String, dynamic> result;

  @override
  Widget build(BuildContext context) {
    final verdict = result['verdict'];
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final (icon, colour, bgColour, title) = switch (verdict) {
      'verified' => (
        Icons.check_circle_rounded,
        kPrimaryGreen,
        kPrimaryGreen.withValues(alpha: 0.15),
        S.verified
      ),
      'review' => (
        Icons.hourglass_top_rounded,
        const Color(0xFFFFB300),
        const Color(0xFFFFB300).withValues(alpha: 0.15),
        S.review
      ),
      _ => (
        Icons.cancel_rounded,
        const Color(0xFFFF5252),
        const Color(0xFFFF5252).withValues(alpha: 0.15),
        S.rejected
      ),
    };

    return Scaffold(
      backgroundColor: isDark ? kDarkSurface : kBackgroundLight,
      appBar: AppBar(
        title: Text(title, style: const TextStyle(fontWeight: FontWeight.bold)),
        elevation: 0,
        backgroundColor: Colors.transparent,
      ),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
          child: Column(
            children: [
              Expanded(
                child: ListView(
                  children: [
                    const SizedBox(height: 20),
                    Center(
                      child: Container(
                        width: 120,
                        height: 120,
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          color: bgColour,
                          boxShadow: [
                            BoxShadow(
                              color: colour.withValues(alpha: 0.25),
                              blurRadius: 30,
                              spreadRadius: 6,
                            ),
                          ],
                        ),
                        child: Icon(icon, size: 68, color: colour),
                      ),
                    ),
                    const SizedBox(height: 24),
                    Text(
                      title,
                      textAlign: TextAlign.center,
                      style: TextStyle(
                        fontSize: 26,
                        fontWeight: FontWeight.w800,
                        color: colour,
                      ),
                    ),
                    const SizedBox(height: 8),
                    if (result['message'] != null)
                      Text(
                        result['message'].toString(),
                        textAlign: TextAlign.center,
                        style: TextStyle(
                          fontSize: 16,
                          color: isDark ? Colors.white70 : kTextSecondary,
                        ),
                      ),
                    const SizedBox(height: 28),
                    Container(
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
                      padding: const EdgeInsets.all(20),
                      child: Column(
                        children: [
                          if (result['litter_before'] != null) ...[
                            _MetricRow(
                              title: S.litterFound,
                              value: S.litterChange(result['litter_before'], result['litter_after']),
                              icon: Icons.delete_outline_rounded,
                              iconColor: Colors.blueGrey,
                            ),
                            Divider(color: Colors.grey.withValues(alpha: 0.2), height: 24),
                          ],
                          _MetricRow(
                            title: S.pointsNow,
                            value: '+${S.digits(result['points_now'] ?? 0)}',
                            icon: Icons.stars_rounded,
                            iconColor: kPrimaryGreen,
                            valueColor: kPrimaryGreen,
                          ),
                          Divider(color: Colors.grey.withValues(alpha: 0.2), height: 24),
                          _MetricRow(
                            title: S.pointsLater,
                            value: '+${S.digits(result['points_pending'] ?? 0)}',
                            icon: Icons.hourglass_bottom_rounded,
                            iconColor: const Color(0xFFFFB300),
                            valueColor: const Color(0xFFFFB300),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
              FilledButton(
                onPressed: () => Navigator.of(context).popUntil((route) => route.isFirst),
                style: FilledButton.styleFrom(
                  backgroundColor: kPrimaryGreen,
                  foregroundColor: Colors.white,
                  minimumSize: const Size.fromHeight(56),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                  elevation: 2,
                ),
                child: const Text(
                  S.backToMap,
                  style: TextStyle(fontSize: 17, fontWeight: FontWeight.bold),
                ),
              ),
              const SizedBox(height: 12),
            ],
          ),
        ),
      ),
    );
  }
}

class _MetricRow extends StatelessWidget {
  const _MetricRow({
    required this.title,
    required this.value,
    required this.icon,
    required this.iconColor,
    this.valueColor,
  });

  final String title;
  final String value;
  final IconData icon;
  final Color iconColor;
  final Color? valueColor;

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Row(
      children: [
        Container(
          padding: const EdgeInsets.all(8),
          decoration: BoxDecoration(
            color: iconColor.withValues(alpha: 0.12),
            borderRadius: BorderRadius.circular(10),
          ),
          child: Icon(icon, color: iconColor, size: 20),
        ),
        const SizedBox(width: 14),
        Expanded(
          child: Text(
            title,
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
            color: valueColor ?? (isDark ? Colors.white : kTextPrimary),
          ),
        ),
      ],
    );
  }
}
