import 'package:flutter/material.dart';

import '../api.dart';
import '../main.dart';
import '../strings.dart';
import '../theme.dart';

/// Points shop: released points buy a reward; the server answers with a voucher code to show
/// at the municipality or the partner.
class RewardsScreen extends StatefulWidget {
  const RewardsScreen({super.key});

  @override
  State<RewardsScreen> createState() => _RewardsScreenState();
}

class _RewardsScreenState extends State<RewardsScreen> {
  late Future<Map<String, dynamic>> _data = Api.instance.rewards();
  bool _busy = false;

  Future<void> _reload() async {
    setState(() => _data = Api.instance.rewards());
    await _data;
  }

  Future<void> _redeem(Map<String, dynamic> reward) async {
    final sure = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        content: Text(S.confirmRedeem(reward['name'].toString(), reward['cost'])),
        actions: [
          TextButton(onPressed: () => Navigator.of(ctx).pop(false), child: const Text(S.cancel)),
          FilledButton(
            onPressed: () => Navigator.of(ctx).pop(true),
            style: FilledButton.styleFrom(minimumSize: const Size(0, 40)),
            child: const Text(S.redeem),
          ),
        ],
      ),
    );
    if (sure != true || !mounted) return;
    setState(() => _busy = true);
    try {
      final result = await Api.instance.redeem(reward['code'].toString());
      if (!mounted) return;
      await showDialog<void>(
        context: context,
        builder: (ctx) => AlertDialog(
          title: Text(result['name'].toString()),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              SelectableText(
                result['voucher'].toString(),
                textDirection: TextDirection.ltr,
                style: const TextStyle(fontSize: 30, fontWeight: FontWeight.w900, letterSpacing: 2),
              ),
              const SizedBox(height: 12),
              Text(result['message'].toString(), textAlign: TextAlign.center),
            ],
          ),
          actions: [TextButton(onPressed: () => Navigator.of(ctx).pop(), child: const Text(S.done))],
        ),
      );
      await _reload();
    } catch (e) {
      if (mounted) showError(context, e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text(S.shop)),
      body: RefreshIndicator(
        onRefresh: _reload,
        child: FutureBuilder<Map<String, dynamic>>(
          future: _data,
          builder: (context, snap) {
            if (snap.hasError) {
              return ListView(padding: const EdgeInsets.all(24), children: [
                Text(snap.error.toString(), textAlign: TextAlign.center),
              ]);
            }
            if (!snap.hasData) {
              return const Center(child: CircularProgressIndicator(color: kPrimaryGreen));
            }
            final balance = (snap.data!['balance'] as num).toInt();
            final rewards = List<Map<String, dynamic>>.from(snap.data!['rewards']);
            final vouchers = List<Map<String, dynamic>>.from(snap.data!['vouchers']);
            return ListView(
              padding: const EdgeInsets.all(20),
              children: [
                Container(
                  padding: const EdgeInsets.all(20),
                  decoration: BoxDecoration(
                    gradient: const LinearGradient(colors: [kPrimaryGreen, kAccentTeal]),
                    borderRadius: BorderRadius.circular(20),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(S.balance, style: TextStyle(color: Colors.white70, fontWeight: FontWeight.w600)),
                      const SizedBox(height: 6),
                      Text('${S.digits(balance)} ${S.points}',
                          style: const TextStyle(color: Colors.white, fontSize: 30, fontWeight: FontWeight.w900)),
                      const SizedBox(height: 4),
                      const Text(S.shopHint, style: TextStyle(color: Colors.white70, fontSize: 13)),
                    ],
                  ),
                ),
                const SizedBox(height: 20),
                for (final r in rewards)
                  Card(
                    margin: const EdgeInsets.only(bottom: 10),
                    child: ListTile(
                      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
                      leading: const CircleAvatar(
                        backgroundColor: Color(0x1F00C853),
                        child: Icon(Icons.card_giftcard_rounded, color: kPrimaryGreen),
                      ),
                      title: Text(r['name'].toString(), style: const TextStyle(fontWeight: FontWeight.bold)),
                      subtitle: Text(r['description'].toString()),
                      trailing: FilledButton(
                        onPressed: _busy || balance < (r['cost'] as num) ? null : () => _redeem(r),
                        style: FilledButton.styleFrom(
                          minimumSize: const Size(0, 38),
                          padding: const EdgeInsets.symmetric(horizontal: 12),
                          textStyle: const TextStyle(fontSize: 13, fontWeight: FontWeight.bold),
                        ),
                        child: Text('${S.digits(r['cost'])} ${S.points}'),
                      ),
                    ),
                  ),
                if (vouchers.isNotEmpty) ...[
                  const SizedBox(height: 16),
                  const Text(S.myVouchers, style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                  const SizedBox(height: 4),
                  const Text(S.voucherHint, style: TextStyle(color: kTextSecondary, fontSize: 13)),
                  const SizedBox(height: 8),
                  for (final v in vouchers)
                    Card(
                      margin: const EdgeInsets.only(bottom: 8),
                      child: ListTile(
                        title: Text(v['name'].toString()),
                        subtitle: Text('-${S.digits(v['cost'])} ${S.points}'),
                        trailing: SelectableText(
                          v['voucher'].toString(),
                          textDirection: TextDirection.ltr,
                          style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w800, letterSpacing: 1),
                        ),
                      ),
                    ),
                ],
              ],
            );
          },
        ),
      ),
    );
  }
}
