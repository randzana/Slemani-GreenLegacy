import 'package:flutter/material.dart';

import '../api.dart';
import '../strings.dart';
import '../theme.dart';
import 'auth_screen.dart';
import 'place_edit_screen.dart';
import 'rewards_screen.dart';

/// Profile: user info, eco stat boxes, earned badges, points history, and logout.
class ProfileScreen extends StatefulWidget {
  const ProfileScreen({super.key, required this.refresh});
  final ValueNotifier<int> refresh;

  @override
  State<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> {
  late Future<Map<String, dynamic>> _me = Api.instance.me();

  @override
  void initState() {
    super.initState();
    widget.refresh.addListener(_reload);
  }

  @override
  void dispose() {
    widget.refresh.removeListener(_reload);
    super.dispose();
  }

  Future<void> _reload() async {
    setState(() {
      _me = Api.instance.me();
    });
    await _me;
  }

  Future<void> _logout() async {
    await Api.instance.logout();
    if (!mounted) return;
    Navigator.of(context).pushAndRemoveUntil(
      MaterialPageRoute(builder: (_) => const AuthScreen()),
      (_) => false,
    );
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final textColor = isDark ? kTextDark : kTextLight;

    return RefreshIndicator(
      onRefresh: _reload,
      child: FutureBuilder<Map<String, dynamic>>(
        future: _me,
        builder: (context, snap) {
          if (snap.hasError) {
            return ListView(
              padding: const EdgeInsets.all(24),
              children: [
                Text(snap.error.toString(), textAlign: TextAlign.center),
                const SizedBox(height: 16),
                ElevatedButton(
                  onPressed: _logout,
                  style: ElevatedButton.styleFrom(backgroundColor: Colors.redAccent),
                  child: const Text(S.logout),
                ),
              ],
            );
          }
          if (!snap.hasData) {
            return const Center(child: CircularProgressIndicator(color: kPrimaryGreen));
          }

          final me = snap.data!;
          final name = me['name']?.toString() ?? S.citizen;
          final phone = me['phone']?.toString() ?? '';
          final hood = me['neighbourhood']?.toString() ?? S.slemani;
          final released = (me['released'] as num?)?.toInt() ?? 0; // spendable in the shop
          // badges follow everything ever earned, so spending points never takes one away
          final earned = (me['earned'] as num?)?.toInt() ?? released;
          final pending = (me['pending'] as num?)?.toInt() ?? 0;
          final history = List<Map<String, dynamic>>.from(me['history'] ?? []);
          final rank = me['rank'];
          final hoodRank = me['neighbourhood_rank'];

          return SingleChildScrollView(
            physics: const AlwaysScrollableScrollPhysics(),
            padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
            child: Column(
              children: [
                // Avatar with glowing shadow
                Container(
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    boxShadow: [
                      BoxShadow(
                        color: kPrimaryGreen.withValues(alpha: 0.3),
                        blurRadius: 18,
                        spreadRadius: 2,
                        offset: const Offset(0, 6),
                      ),
                    ],
                  ),
                  child: const CircleAvatar(
                    radius: 46,
                    backgroundColor: kPrimaryGreen,
                    child: Icon(Icons.person_rounded, size: 52, color: Colors.white),
                  ),
                ),
                const SizedBox(height: 14),

                // Name & Details
                Text(
                  name,
                  style: TextStyle(
                    fontSize: 22,
                    fontWeight: FontWeight.bold,
                    color: textColor,
                  ),
                ),
                const SizedBox(height: 4),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                  decoration: BoxDecoration(
                    color: kPrimaryGreen.withValues(alpha: 0.12),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Text(
                    S.hoodAndPhone(hood, phone),
                    style: const TextStyle(
                      color: kPrimaryGreen,
                      fontSize: 13,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
                if (me['email'] != null) ...[
                  const SizedBox(height: 4),
                  Text('${me['email']}', textDirection: TextDirection.ltr,
                      style: TextStyle(color: Colors.grey.shade600, fontSize: 13)),
                ],
                const SizedBox(height: 24),

                // 3 Stat Boxes Row (Zanko-GreenLegacy style)
                Row(
                  children: [
                    Expanded(
                      child: _buildStatBox(
                        context,
                        title: S.approvedPoints,
                        value: S.digits(released),
                        icon: Icons.check_circle_outline_rounded,
                        color: kPrimaryGreen,
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: _buildStatBox(
                        context,
                        title: S.waitingPoints,
                        value: S.digits(pending),
                        icon: Icons.hourglass_top_rounded,
                        color: Colors.orange,
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: _buildStatBox(
                        context,
                        title: S.records,
                        value: S.digits(history.length),
                        icon: Icons.history_rounded,
                        color: const Color(0xFF1E88E5),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 12),

                // League place, trust and the points shop
                Card(
                  child: Column(
                    children: [
                      if (rank != null)
                        ListTile(
                          leading: const Icon(Icons.emoji_events_rounded, color: Color(0xFFFFB300)),
                          title: const Text(S.rank),
                          trailing: Text(S.rankOf(rank, me['citizens']),
                              style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 15)),
                        ),
                      if (hoodRank != null)
                        ListTile(
                          leading: const Icon(Icons.location_city_rounded, color: Color(0xFF1E88E5)),
                          title: Text('${S.hoodRank} ($hood)'),
                          trailing: Text(S.rankOf(hoodRank, me['neighbourhoods']),
                              style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 15)),
                        ),
                      ListTile(
                        leading: const Icon(Icons.verified_user_rounded, color: kPrimaryGreen),
                        title: const Text(S.trust),
                        trailing: Text(S.digits(me['trust_level'] ?? 0),
                            textDirection: TextDirection.ltr,
                            style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 15)),
                      ),
                      ListTile(
                        leading: const Icon(Icons.card_giftcard_rounded, color: kPrimaryGreen),
                        title: const Text(S.shop, style: TextStyle(fontWeight: FontWeight.bold)),
                        subtitle: const Text(S.shopHint),
                        // chevron_right is mirrored in right-to-left, so it points forward (left)
                        trailing: const Icon(Icons.chevron_right_rounded),
                        onTap: () => Navigator.of(context)
                            .push(MaterialPageRoute(builder: (_) => const RewardsScreen()))
                            .then((_) => _reload()),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 12),

                // The person's household and business: the municipality's answer, and the money
                _placesCard(context, me),
                const SizedBox(height: 26),

                // Earned Badges Section
                const Align(
                  alignment: Alignment.centerRight,
                  child: Text(
                    S.badges,
                    style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                  ),
                ),
                const SizedBox(height: 12),
                Wrap(
                  spacing: 12,
                  runSpacing: 12,
                  children: [
                    _buildBadge(S.badgeReporter, Icons.photo_camera_rounded, Colors.teal, active: history.isNotEmpty),
                    _buildBadge(S.badgeCleaner, Icons.cleaning_services_rounded, Colors.green, active: history.any((h) => h['kind'] == 'cleanup')),
                    _buildBadge(S.badgeEcoWarrior, Icons.eco_rounded, Colors.orange, active: earned >= 50),
                    _buildBadge(S.badgeCityGuardian, Icons.military_tech_rounded, Colors.purple, active: earned >= 200),
                  ],
                ),
                const SizedBox(height: 28),

                // Points History Section
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    const Text(
                      S.pointsHistory,
                      style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                    ),
                    Text(
                      S.activities(history.length),
                      style: TextStyle(color: Colors.grey.shade600, fontSize: 13),
                    ),
                  ],
                ),
                const SizedBox(height: 10),

                if (history.isEmpty)
                  Card(
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                    child: Padding(
                      padding: const EdgeInsets.all(20),
                      child: Center(
                        child: Text(
                          S.noHistory,
                          style: TextStyle(color: Colors.grey.shade500),
                        ),
                      ),
                    ),
                  )
                else
                  for (final h in history)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 8),
                      child: Card(
                        elevation: 1,
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                        child: ListTile(
                          contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
                          leading: CircleAvatar(
                            backgroundColor: (h['status'] == 'revoked' ? kStatusOpen : kPrimaryGreen).withValues(alpha: 0.12),
                            child: Icon(
                              switch (h['kind']) {
                                'cleanup' => Icons.cleaning_services_rounded,
                                'report' => Icons.add_a_photo_rounded,
                                'redeem' => Icons.card_giftcard_rounded,
                                _ => Icons.star_rounded,
                              },
                              color: h['status'] == 'revoked' ? kStatusOpen : kPrimaryGreen,
                              size: 20,
                            ),
                          ),
                          title: Text(
                            S.kinds[h['kind']] ?? h['kind'].toString(),
                            style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14),
                          ),
                          subtitle: Text(
                            S.statuses[h['status']] ?? h['status'].toString(),
                            style: TextStyle(color: Colors.grey.shade600, fontSize: 12),
                          ),
                          trailing: Text(
                            '${h['kind'] == 'redeem' ? '-' : '+'}${S.digits(h['amount'])} ${S.points}',
                            style: TextStyle(
                              fontWeight: FontWeight.bold,
                              fontSize: 15,
                              color: h['status'] == 'revoked' ? kStatusOpen : kPrimaryGreen,
                            ),
                          ),
                        ),
                      ),
                    ),
                const SizedBox(height: 28),

                // Logout Button
                SizedBox(
                  width: double.infinity,
                  height: 50,
                  child: ElevatedButton.icon(
                    onPressed: _logout,
                    icon: const Icon(Icons.logout_rounded),
                    label: const Text(
                      S.logoutOfAccount,
                      style: TextStyle(fontSize: 15, fontWeight: FontWeight.bold),
                    ),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.redAccent.shade400,
                      foregroundColor: Colors.white,
                      elevation: 2,
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                    ),
                  ),
                ),
                const SizedBox(height: 90),
              ],
            ),
          );
        },
      ),
    );
  }

  Future<void> _editPlace(String kind, Map<String, dynamic>? existing) async {
    final saved = await Navigator.of(context)
        .push<bool>(MaterialPageRoute(builder: (_) => PlaceEditScreen(kind: kind, existing: existing)));
    if (saved == true) _reload();
  }

  Widget _placesCard(BuildContext context, Map<String, dynamic> me) {
    final places = List<Map<String, dynamic>>.from(me['places'] ?? const []);
    final money = Map<String, dynamic>.from(me['money'] ?? const {});
    final payments = List<Map<String, dynamic>>.from(money['payments'] ?? const []);
    final has = {for (final p in places) p['kind']};
    const statusColours = {'pending': amber, 'verified': kPrimaryGreen, 'rejected': red};
    return Card(
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 8),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Padding(
              padding: EdgeInsets.fromLTRB(16, 8, 16, 4),
              child: Text(S.myPlaces, style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
            ),
            for (final p in places)
              ListTile(
                leading: Icon(p['kind'] == 'household' ? Icons.home_rounded : Icons.storefront_rounded,
                    color: kDarkGreen),
                title: Text('${p['name']}'),
                subtitle: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(S.placeKinds[p['kind']] ?? ''),
                    const SizedBox(height: 4),
                    Chip(
                      label: Text(S.placeStatuses[p['verification_status']] ?? '${p['verification_status']}'),
                      labelStyle: const TextStyle(color: Colors.white, fontSize: 12),
                      backgroundColor: statusColours[p['verification_status']] ?? soft,
                      visualDensity: VisualDensity.compact,
                    ),
                    if (p['rejection_reason'] != null)
                      Text(S.rejectedBecause('${p['rejection_reason']}'), style: const TextStyle(color: red)),
                  ],
                ),
                isThreeLine: true,
                trailing: const Icon(Icons.edit_outlined),
                onTap: () => _editPlace('${p['kind']}', p),
              ),
            if (!has.contains('household'))
              ListTile(
                leading: const Icon(Icons.add_home_outlined, color: kPrimaryGreen),
                title: const Text(S.addHousehold),
                onTap: () => _editPlace('household', null),
              ),
            if (!has.contains('business'))
              ListTile(
                leading: const Icon(Icons.add_business_outlined, color: kPrimaryGreen),
                title: const Text(S.addBusiness),
                onTap: () => _editPlace('business', null),
              ),
            if (places.isNotEmpty) ...[
              const Divider(),
              ListTile(
                leading: const Icon(Icons.account_balance_wallet_outlined, color: kDarkGreen),
                title: const Text(S.monthlyMoney, style: TextStyle(fontWeight: FontWeight.bold)),
                subtitle: const Text(S.moneyHint),
                trailing: Text(S.dinar((money['total_iqd'] as num?) ?? 0),
                    style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 15)),
              ),
              if (payments.isEmpty)
                Padding(
                  padding: const EdgeInsets.fromLTRB(16, 0, 16, 8),
                  child: Text(S.moneyNone, style: TextStyle(color: Colors.grey.shade600)),
                ),
              for (final pay in payments.take(6))
                ListTile(
                  dense: true,
                  leading: Text(S.month('${pay['month']}')),
                  title: Text(S.placeKinds[pay['kind']] ?? ''),
                  trailing: Text(S.dinar((pay['amount_iqd'] as num?) ?? 0)),
                ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildStatBox(
    BuildContext context, {
    required String title,
    required String value,
    required IconData icon,
    required Color color,
  }) {
    return Card(
      elevation: 2,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 16, horizontal: 10),
        child: Column(
          children: [
            Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: color.withValues(alpha: 0.12),
                shape: BoxShape.circle,
              ),
              child: Icon(icon, color: color, size: 22),
            ),
            const SizedBox(height: 8),
            Text(
              value,
              style: TextStyle(fontSize: 20, fontWeight: FontWeight.w900, color: color),
            ),
            const SizedBox(height: 2),
            Text(
              title,
              textAlign: TextAlign.center,
              style: TextStyle(color: Colors.grey.shade600, fontSize: 12),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildBadge(String name, IconData icon, Color color, {required bool active}) {
    return Container(
      width: 150,
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        color: active ? color.withValues(alpha: 0.12) : Colors.grey.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(
          color: active ? color.withValues(alpha: 0.4) : Colors.grey.shade300,
        ),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, color: active ? color : Colors.grey, size: 24),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              name,
              style: TextStyle(
                fontSize: 13,
                fontWeight: FontWeight.bold,
                color: active ? color : Colors.grey,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
