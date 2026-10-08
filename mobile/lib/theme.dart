import 'package:flutter/material.dart';

// Zanko GreenLegacy Design Palette
const Color kPrimaryGreen = Color(0xFF00C853); // Emerald vibrant leaf green
const Color kDarkGreen = Color(0xFF1B5E20);    // Deep rich green
const Color kAccentTeal = Color(0xFF00BFA5);   // Modern cyan teal
const Color kBackgroundLight = Color(0xFFF5F7FA); // Modern crisp off-white
const Color kCardLight = Colors.white;         // Clean white card
const Color kTextLight = Color(0xFF263238);    // Slate charcoal
const Color kBackgroundDark = Color(0xFF121212);
const Color kCardDark = Color(0xFF1E1E1E);
const Color kTextDark = Color(0xFFE0E0E0);

// Status colors
const Color kStatusClean = Color(0xFF00C853);
const Color kStatusInProgress = Color(0xFFFFA000);
const Color kStatusReview = Color(0xFFFF9100);
const Color kStatusOpen = Color(0xFFE53935);

// Compatibility aliases
const forest = kDarkGreen;
const green = kPrimaryGreen;
const paper = kBackgroundLight;
const card = kCardLight;
const amber = kStatusInProgress;
const red = kStatusOpen;
const soft = Color(0xFF546E7A);

const Color kDarkSurface = kBackgroundDark;
const Color kDarkCard = kCardDark;
const Color kTextPrimary = kTextLight;
const Color kTextSecondary = soft;

/// Pin colours from the build plan: red open, orange in progress / in review, green clean.
Color statusColour(String status) {
  switch (status) {
    case 'clean':
      return kStatusClean;
    case 'in_progress':
    case 'needs_review':
      return kStatusInProgress;
    default:
      return kStatusOpen;
  }
}

ThemeData appTheme({Brightness brightness = Brightness.light}) {
  final isDark = brightness == Brightness.dark;
  final bg = isDark ? kBackgroundDark : kBackgroundLight;
  final cardBg = isDark ? kCardDark : kCardLight;
  final textColor = isDark ? kTextDark : kTextLight;

  return ThemeData(
    useMaterial3: true,
    brightness: brightness,
    scaffoldBackgroundColor: bg,
    cardColor: cardBg,
    colorScheme: ColorScheme.fromSeed(
      seedColor: kPrimaryGreen,
      primary: kPrimaryGreen,
      secondary: kAccentTeal,
      surface: cardBg,
      brightness: brightness,
    ),
    appBarTheme: AppBarTheme(
      backgroundColor: cardBg,
      foregroundColor: textColor,
      elevation: 0,
      centerTitle: true,
      titleTextStyle: TextStyle(
        color: textColor,
        fontSize: 20,
        fontWeight: FontWeight.bold,
      ),
      iconTheme: IconThemeData(color: textColor),
    ),
    cardTheme: CardThemeData(
      color: cardBg,
      elevation: 2,
      shadowColor: Colors.black.withValues(alpha: 0.06),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
    ),
    elevatedButtonTheme: ElevatedButtonThemeData(
      style: ElevatedButton.styleFrom(
        backgroundColor: kPrimaryGreen,
        foregroundColor: Colors.white,
        elevation: 3,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
        minimumSize: const Size.fromHeight(52),
        textStyle: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
      ),
    ),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(
        backgroundColor: kPrimaryGreen,
        foregroundColor: Colors.white,
        elevation: 2,
        minimumSize: const Size.fromHeight(52),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
        textStyle: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
      ),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: isDark ? const Color(0xFF2A2A2A) : Colors.white,
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(14),
        borderSide: BorderSide(color: Colors.grey.shade300),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(14),
        borderSide: BorderSide(color: Colors.grey.shade300),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(14),
        borderSide: const BorderSide(color: kPrimaryGreen, width: 2),
      ),
      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
    ),
  );
}
