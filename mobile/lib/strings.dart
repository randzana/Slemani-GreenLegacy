/// Every Kurdish (Sorani) string in the app, in one file so it is easy to fix on day two.
class S {
  static const appName = 'GreenLegacy سلێمانی';

  // auth
  static const server = 'ناونیشانی سێرڤەر';
  // run.py listens on 5000 and moves to 5001 only when 5000 is taken (macOS AirPlay)
  static const serverHint = 'http://localhost:5000';
  // one hint per line: a narrow phone otherwise breaks the addresses after "http://"
  static const serverHelp = 'مۆبایل: IP ی لاپتۆپ\n'
      'سیمولەیتەری iOS: http://localhost:5000\n'
      'ئیمولەیتەری ئەندرۆید: http://10.0.2.2:5000\n'
      'پۆرتی 5000 گیرابوو (macOS)؟ 5001 بەکاربهێنە';
  static const name = 'ناو';
  static const phone = 'ژمارەی مۆبایل';
  static const password = 'وشەی نهێنی (لانیکەم ٦ پیت)';
  static const neighbourhood = 'گەڕەک';
  static const signIn = 'چوونەژوورەوە';
  static const signUp = 'هەژماری نوێ';
  static const haveAccount = 'هەژمارم هەیە';
  static const noAccount = 'هەژمارم نییە';
  static const welcomeBack = 'بەخێربێیتەوە بۆ گەشتی پاراستنی ژینگە';
  static const joinUs = 'بەشداربە لە سەوزکردنی سلێمانی';
  static const fillAllFields = 'تکایە هەموو خانەکان پڕبکەرەوە';

  // tabs
  static const map = 'نەخشە';
  static const league = 'لیگی گەڕەکەکان';
  static const profile = 'پرۆفایل';
  static const report = 'ڕاپۆرتی پاشماوە';

  // home: app bar titles, bottom bar and the round report button
  static const home = 'سەرەکی';
  static const garden = 'باخچە';
  static const gardenTitle = 'باخچەی دیجیتاڵی 🌱';
  static const leagueTitle = 'لیگی گەڕەکەکان 🏆';
  static const refreshMap = 'نوێکردنەوەی نەخشە';
  static const reportButton = 'ڕاپۆرت';

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
  // map filter chips (the open chip uses [open])
  static const filterAll = 'هەموو';
  static const filterInProgress = 'لەسەریەتی';
  static const filterClean = 'پاک';
  static String withCount(String label, Object n) => '$label (${digits(n)})';

  // dashboard (home tab)
  static const citizen = 'هاوڵاتی'; // shown when the server sends no name
  static String hello(String name) => 'سڵاو، $name 👋';
  static const letsGoGreen = 'با سلێمانی سەوز بکەین!';
  static const totalGreenPoints = 'کۆی خاڵە سەوزەکان';
  static String levelOf(String level) => 'ئاست: $level';
  // eco levels by total points: under 200, 200+, 500+, 1000+
  static const levelSeed = 'شینەوار (تۆو)';
  static const levelGreenWarrior = 'شەڕڤانی سەوز 🌲';
  static const levelEcoTeacher = 'مامۆستای ژینگە 🌿';
  static const levelEarthGuardian = 'پارێزەری زەوی 🌍';
  static const liveMap = 'نەخشەی ڕاستەوخۆی شار';
  static const liveMapHint = 'شوێنە پیسەکان و پاککردنەوە ببینە';
  static const openReports = 'ڕاپۆرتە کراوەکان';
  static const cleanedSpots = 'پاککراوەکان';
  static const ranking = 'پلەبەندی';
  static const pendingTotal = 'خاڵی چاوەڕوانکراو';
  static const myGarden = 'باخچەی دیجیتاڵیی من 🌱';
  static String plantCount(Object n) => '${digits(n)} ڕووەک';
  static const seeGarden = 'بینینی باخچە';
  static const gardenEmpty = 'باخچەکەت بەتاڵە! دەست بکە بە ناشتنی یەکەم درەخت.';
  static const plantFirst = 'ناشتن 🌱';
  static const recentReports = 'دواین ڕاپۆرتەکانی پاشماوە';
  static const wholeMap = 'هەموو نەخشە';
  static const allClean = 'سلێمانی خاوێنە! هیچ پاشماوەیەک نییە.';
  static String reportNo(Object id) => 'ڕاپۆرتی #${digits(id)}';
  static String spotSummary(Object litter, Object dirtiness) =>
      'پاشماوە: ${digits(litter)} دەنک • پیسی: ${digits(dirtiness)}/${digits(5)}';

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
  static const pleaseWait = 'تکایە چاوەڕێبە...';
  static const noValue = '—'; // distance or count not known yet
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
  // litter before ← after; the arrow points left because the screen reads right to left
  static String litterChange(Object before, Object? after) =>
      '${digits(before)} ← ${after == null ? noValue : digits(after)}';

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

  // profile tab
  static const slemani = 'سلێمانی'; // shown when the person has no neighbourhood
  static const approvedPoints = 'پەسەندکراو';
  static const waitingPoints = 'چاوەڕوانکراو';
  static const records = 'تۆمارەکان';
  static String hoodAndPhone(String hood, String phone) => '$hood • $phone';
  static const badges = 'نیشانە بەدەستهاتووەکان 🎖️';
  static const badgeReporter = 'ڕاپۆرتکەر';
  static const badgeCleaner = 'پاککەرەوە';
  static const badgeEcoWarrior = 'شەڕڤانی ژینگە';
  static const badgeCityGuardian = 'پارێزەری شار';
  static const pointsHistory = 'مێژووی خاڵەکان';
  static String activities(Object n) => '${digits(n)} چالاکی';
  static const noHistory = 'هیچ تۆمارێکی خاڵ بەردەست نییە';
  static const logoutOfAccount = 'چوونەدەرەوە لە هەژمار';

  // league tab
  static const hoodsTab = 'گەڕەکەکان 🏘️';
  static const citizensTab = 'هاوڵاتیانی نموونەیی 🌟';
  static const noData = 'هیچ داتایەک بەردەست نییە';
  // podium fallbacks when a name is missing
  static const first = 'یەکەم';
  static const second = 'دووەم';
  static const third = 'سێیەم';
  static const allHoods = 'هەموو گەڕەکەکانی سلێمانی';
  static const overallRanking = 'ڕیزبەندیی گشتی چالاکوانان';

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
  static const voucherUsed = 'بەکارهاتووە'; // the municipality or partner already honoured it
  static const cancel = 'پاشگەزبوونەوە';
  static String confirmRedeem(String name, Object cost) => '«$name» بە ${digits(cost)} خاڵ وەردەگریت؟';
  static const statuses = {'pending': 'چاوەڕوان', 'released': 'ئازاد', 'revoked': 'هەڵوەشێنرایەوە'};

  // digital garden tab (counts here use Western digits, as the screen always has)
  static const gardenHeader = 'باخچەی سەوزی سلێمانی';
  static String gardenPlants(int n) => '$n درەخت و ڕووەک';
  static const newSeedling = 'نەمامی نوێ';
  static String thirstyPlants(int n) => '$n ڕووەک پێویستیان بە ئاوپڕژێنە! ئاویان بدە بۆ بەدەستهێنانی خاڵ.';
  static const yourPlants = 'درەختە چێنراوەکانی تۆ 🌱';
  static String plantsAvailable(int n) => '$n بەردەستە';
  static const plant = 'ڕووەک'; // fallback name of a saved plant
  static const plantLevelFallback = 'ئاستی ١';
  static const thirsty = 'تینووە';
  static const waterIt = 'ئاو بدە 💧';
  static const healthyBadge = 'تەندروستە 🌱';
  static const plantNew = 'ڕوواندنی ڕووەکی نوێ';
  static const ecoPoints = '+ خاڵی ژینگەیی';
  static String watered(String name) => '$name بە سەرکەوتوویی ئاو درا! 💧 (+10 خاڵ بەدەستهات)';
  static String alreadyWatered(String name) => '$name پێشتر ئاو دراوە و تەندروستە! 🌱';
  static const removePlant = 'لابردنی ڕووەک';
  static String confirmRemovePlant(String name) => 'ئایا دڵنیایت لە لابردنی $name لە باخچەکەتدا؟';
  static const yesRemove = 'بەڵێ، لایببە';
  static String plantRemoved(String name) => '$name لە باخچەکەت لابرا';

  // plant selection
  static const choosePlant = 'هەڵبژاردنی نەمام و ڕووەک 🌳';
  static const allKinds = 'هەموو جۆرەکان 🌱';
  static const bigTrees = 'درەختە گەورەکان 🌳';
  static const fruitTrees = 'میوەدارەکان 🍎';
  static const flowersAndHerbs = 'گوڵ و دەرمانەکان 🌸';
  static String waterNeed(String need) => '💧 $need';
  static const plantIt = 'بڕوێنە 🌱';
  static String planted(String name, int points) => '$name بە سەرکەوتوویی ڕوواندرا! 🌱 (+$points خاڵ)';

  // garden plant states. These exact values are saved on the phone (SharedPreferences) and compared
  // when the garden loads again: changing one strands every plant saved with the old text.
  static const plantHealthy = 'تەندروستە';
  static const plantThirsty = 'پێویستی بە ئاوە';
  static const plantLevel1 = 'ئاستی ١ (چەکەرەکردن)';
  static const plantLevel2 = 'ئاستی ٢ (لە گەشەدایە)';
  static const plantLevel3 = 'ئاستی ٣ (پێگەیشتوو)';

  // plant catalogue (data/plant_data.dart): names, one-line descriptions, difficulty, water need
  static const difficultyEasy = 'ئاسان';
  static const difficultyMedium = 'مامناوەند';
  static const difficultyHard = 'قورس';
  static const waterLow = 'کەمئاو';
  static const waterMedium = 'مامناوەند';
  static const waterHigh = 'ئاوی زۆر';
  static const plantOak = 'بەڕوو (Oak Tree)';
  static const plantOakAbout = 'درەختی ڕەسەنی دارستانەکانی ئەزمەڕ و گۆیژە. بەرگەی گەرما و وشکەساڵی دەگرێت.';
  static const plantPine = 'سنەوبەر (Pine Tree)';
  static const plantPineAbout = 'هەمیشە سەوز و خێرا لە گەشەکردندا. هەوای سلێمانی پاک و سازگار دەکات.';
  static const plantPlane = 'چنار (Plane Tree)';
  static const plantPlaneAbout = 'درەختی هێمای سەرچناری سلێمانی. سێبەرێکی فراوان و بەهەیبەت دروست دەکات.';
  static const plantOlive = 'زەیتوون (Olive Tree)';
  static const plantOliveAbout = 'هێمای ئاشتی و بەرەکەت. زۆر کەمئاوە و تەمەندرێژترین درەختی ناوچەکەیە.';
  static const plantPomegranate = 'هەنار (Pomegranate)';
  static const plantPomegranateAbout = 'میوەدار و گوڵدار بە گوڵی سووری گەش. گونجاوە بۆ باخچەی ماڵان و گەڕەکەکان.';
  static const plantFig = 'هەنجیر (Fig Tree)';
  static const plantFigAbout = 'درەختی شیرین و پڕسێبەر. لە خاکە شاخاوییەکان زۆر بە باشی گەشە دەکات.';
  static const plantRose = 'گوڵەباخ (Rose Bush)';
  static const plantRoseAbout = 'گوڵێکی بۆنخۆشی ڕەسەن کە جوانییەکی تایبەت دەبەخشێتە کۆڵان و گەڕەکەکان.';
  static const plantLavender = 'لاڤێندەر (Lavender)';
  static const plantLavenderAbout = 'بۆنخۆش و سەرنجڕاکێش بۆ پەپوولە و هەنگ. زۆر کەمئاوە و سەوز دەمێنێتەوە.';
  static const plantHerbs = 'نەعنا و ڕێحانە (Herbs)';
  static const plantHerbsAbout = 'ڕووەکی سەوزی بەکەڵک و بۆندار. زوو گەشە دەکات و دەڕوێت.';

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
