/// Every Kurdish (Sorani) string in the app, in one file so it is easy to fix on day two.
class S {
  static const appName = 'GreenLegacy سلێمانی';

  // auth
  static const server = 'ناونیشانی سێرڤەر';
  static const serverHint = 'http://localhost:5001';
  static const serverHelp =
      'مۆبایل: IP ی لاپتۆپ · سیمولەیتەری iOS: http://localhost:5001 · ئیمولەیتەری ئەندرۆید: http://10.0.2.2:5001';
  static const name = 'ناو';
  static const phone = 'ژمارەی مۆبایل';
  static const password = 'وشەی نهێنی (لانیکەم ٦ پیت)';
  static const neighbourhood = 'گەڕەک';
  static const signIn = 'چوونەژوورەوە';
  static const signUp = 'هەژماری نوێ';
  static const haveAccount = 'هەژمارم هەیە';
  static const noAccount = 'هەژمارم نییە';

  // tabs
  static const map = 'نەخشە';
  static const league = 'لیگی گەڕەکەکان';
  static const profile = 'پرۆفایل';
  static const report = 'ڕاپۆرتی پاشماوە';

  // map
  static const open = 'کراوە';
  static const inProgress = 'لە پاککردنەوەدایە';
  static const needsReview = 'چاوەڕوانی پشکنین';
  static const clean = 'پاککراوە';
  static const reportStatuses = {
    'open': open,
    'in_progress': inProgress,
    'needs_review': needsReview,
    'clean': clean,
  };

  // report
  static const takePhoto = 'وێنە بگرە';
  static const analysing = 'زیرەکیی دەستکرد وێنەکە شی دەکاتەوە...';
  static const litterFound = 'پاشماوەی دۆزراوە';
  static const dirtiness = 'پلەی پیسی';
  static const pendingPoints = 'خاڵی چاوەڕوان';
  static const pendingNote = 'خاڵەکان ئازاد دەبن کاتێک کەسێکی تر پشتڕاستی بکاتەوە یان شوێنەکە پاک بکرێتەوە';
  static const done = 'باشە';

  // spot detail + cleanup
  static const distance = 'دووری';
  static const metres = 'مەتر';
  static const illClean = 'من پاکی دەکەمەوە';
  static const instruction = 'ڕێنمایی';
  static const record = 'تۆمارکردن (٦ چرکە)';
  static const recording = 'تۆمار دەکرێت... ڕێنماییەکە جێبەجێ بکە';
  static const verifying = 'پاککردنەوەکە دەسەلمێنرێت...';
  static const timeLeft = 'کاتی ماوە';

  // result
  static const verified = 'سەلمێنرا';
  static const review = 'نێردرا بۆ پشکنین';
  static const rejected = 'ڕەتکرایەوە';
  static const pointsNow = 'خاڵی ئێستا';
  static const pointsLater = 'خاڵ دوای ٢٤ کاتژمێر';
  static const backToMap = 'گەڕانەوە بۆ نەخشە';

  // league + profile
  static const neighbourhoods = 'گەڕەکەکان';
  static const topCitizens = 'باشترین هاوڵاتیان';
  static const points = 'خاڵ';
  static const released = 'خاڵی ئازاد';
  static const pending = 'خاڵی چاوەڕوان';
  static const history = 'مێژوو';
  static const logout = 'چوونەدەرەوە';
  static const kinds = {
    'report': 'ڕاپۆرت',
    'confirmation': 'پشتڕاستکردنەوە',
    'cleanup': 'پاککردنەوە',
    'task': 'ئەرکی ڕۆژانە',
    'redeem': 'گۆڕینەوە بە خەڵات',
  };
  static const rank = 'ڕیزبەندیت';
  static const hoodRank = 'ڕیزی گەڕەکەکەت';
  static const trust = 'متمانە';
  static String rankOf(Object rank, Object total) => '${digits(rank)} لە ${digits(total)}';

  // AI description of the spot
  static const aiDescription = 'وەسفی زیرەکیی دەستکرد';

  // daily tasks
  static const dailyTasks = 'ئەرکەکانی ئەمڕۆ';
  static const claimBonus = 'وەرگرتنی خاڵ';
  static const bonusClaimed = 'وەرگیرا';
  static String bonus(Object n) => '+${digits(n)} خاڵ';

  // points shop
  static const shop = 'فرۆشگای خاڵ';
  static const shopHint = 'خاڵە ئازادەکانت بگۆڕەوە بە خەڵات';
  static const balance = 'خاڵی ئازادت';
  static const redeem = 'گۆڕینەوە';
  static const notEnough = 'خاڵت بەس نییە';
  static const myVouchers = 'کۆدەکانم';
  static const voucherHint = 'ئەم کۆدە بە شارەوانی یان هاوبەشەکە پیشان بدە';
  static const cancel = 'پاشگەزبوونەوە';
  static String confirmRedeem(String name, Object cost) => '«$name» بە ${digits(cost)} خاڵ وەردەگریت؟';
  static const statuses = {'pending': 'چاوەڕوان', 'released': 'ئازاد', 'revoked': 'هەڵوەشێنرایەوە'};

  // errors
  static const genericError = 'هەڵەیەک ڕوویدا؛ دووبارە هەوڵ بدەرەوە';
  static const noServer = 'پەیوەندی بە سێرڤەرەوە نییە؛ ناونیشانەکە و ئینتەرنێت بپشکنە';
  static const locationDenied = 'ڕێگەی شوێن (GPS) پێویستە';
  static const cameraError = 'کامێرا کار ناکات';
  static const locationUnavailable = 'شوێنەکەت نەدۆزرایەوە؛ لە سیمولەیتەر شوێنێک دیاری بکە';
  static const simulatedCamera = 'سیمولەیتەر: کامێرا نییە، وێنەی دروستکراو لە سێرڤەرەوە دێت';
  static const simulatorOff = 'سێرڤەر وێنەی سیمولەیتەر نادات؛ بە DETECTOR_KIND=colorblob دەستی پێبکە';

  static String digits(Object n) {
    const ku = '٠١٢٣٤٥٦٧٨٩';
    return n.toString().replaceAllMapped(RegExp(r'\d'), (m) => ku[int.parse(m[0]!)]);
  }
}
