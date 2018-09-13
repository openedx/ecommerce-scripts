addEventListener('fetch', event => {
  event.passThroughOnException()

  event.respondWith(fetchAndApply(event.request))
})

async function fetchAndApply(request) {
  const test_group_name = 'test'
  const control_group_name = 'control'
  const cookie_name = getCookieName(request)
  const control_cookie_pattern = `${cookie_name}=${control_group_name}`
  const test_cookie_pattern = `${cookie_name}=${test_group_name}`

  const percent_in_test_group = 0.5
  let group          // 'control' or 'test', set below
  let cookie_group   // How the assignment was made + which group was assigned
  let isNew = false  // is the group newly-assigned?

  let debugMsg = ''
  debugMsg += "CONTROL: "
  debugMsg += presortToControl(request, control_cookie_pattern, control_group_name)

  debugMsg += "; TEST: "
  debugMsg += presortToTest(request, test_cookie_pattern, test_group_name)



  // Determine which group this request is in.
  let controlAssignment = presortToControl(request, control_cookie_pattern, control_group_name)
  let testAssignment = presortToTest(request, test_cookie_pattern, test_group_name)
  if( controlAssignment ){
    group = control_group_name
    cookie_group = `${controlAssignment}_${group}`
  } else if ( testAssignment ){
    group = test_group_name
    cookie_group = `${testAssignment}_${group}`
  } else {
    group = Math.random() < percent_in_test_group ? test_group_name : control_group_name

    isNew = true
    debugMsg += `; ASSIGN => ${group};`
  }

  const modifiedHeaders = new Headers(request.headers)
  modifiedHeaders.set('x-rollout-group', group)

  const modifiedRequest = new Request(request.url, {
    method: request.method,
    headers: modifiedHeaders
  })

  const response = await fetch(modifiedRequest)

  const newHeaders = new Headers(response.headers)
  if (isNew) {
    newHeaders.append('Set-Cookie', `${cookie_name}=${group}`)
  }
  newHeaders.append('X-debug', debugMsg)
  return new Response(response.body, {
    status: response.status,
    statusText: response.statusText,
    headers: newHeaders
  })
}

function presortToControl(request, control_cookie_pattern, control_group){
  // Always sort search engines and other crawlers to control
  if( isSearchEngine(request)){
    return "crawler"
  }


  // If a user has a control cookie, keep them in the control group
  const cookie = request.headers.get('Cookie')
  return ( cookie && cookie.includes(control_cookie_pattern) )


  // if query string include control param
  const url = new URL(request.url)
  if(url.searchParams.has("rollout") && url.searchParams.get("rollout") === control_group){
    return "query"
  }

  return ''
}

function presortToTest(request, test_cookie_pattern, test_group){
  const url = new URL(request.url)
  if(url.searchParams.has("rollout")){
    return url.searchParams.get("rollout") === test_group
  }

  // If a user has a test cookie, keep them in the test group
  const cookie = request.headers.get('Cookie')
  return ( cookie && cookie.includes(test_cookie_pattern) )
}

function getCookieName(request) {
  const prodCookieName = 'prod-edx-rollout-group'
  const stageCookieName = 'stage-edx-rollout-group'
  const prodEdxUrlPattern = /www\.edx\.org/

  if(request.url.match(prodEdxUrlPattern)){
    debugMsg += 'prod'
    return prodCookieName
  }

  return stageCookieName
}

function isSearchEngine(request) {
  const ua = request.headers.get('user-agent')
  // From https://raw.githubusercontent.com/monperrus/crawler-user-agents/ff7991d57cff2c4889775e31added07d81d320bb/crawler-user-agents.json
  const botPatterns = [
  'Googlebot\\/',
  'Googlebot-Mobile',
  'Googlebot-Image',
  'Googlebot-News',
  'Googlebot-Video',
  'AdsBot-Google([^-]|$)',
  'AdsBot-Google-Mobile',
  'Feedfetcher-Google',
  'Mediapartners-Google',
  'Mediapartners \\(Googlebot\\)',
  'APIs-Google',
  'bingbot',
  'Slurp',
  '[wW]get',
  'curl',
  'LinkedInBot',
  'Python-urllib',
  'python-requests',
  'libwww',
  'httpunit',
  'nutch',
  'Go-http-client',
  'phpcrawl',
  'msnbot',
  'jyxobot',
  'FAST-WebCrawler',
  'FAST Enterprise Crawler',
  'BIGLOTRON',
  'Teoma',
  'convera',
  'seekbot',
  'Gigabot',
  'Gigablast',
  'exabot',
  'ia_archiver',
  'GingerCrawler',
  'webmon ',
  'HTTrack',
  'grub.org',
  'UsineNouvelleCrawler',
  'antibot',
  'netresearchserver',
  'speedy',
  'fluffy',
  'bibnum.bnf',
  'findlink',
  'msrbot',
  'panscient',
  'yacybot',
  'AISearchBot',
  'ips-agent',
  'tagoobot',
  'MJ12bot',
  'woriobot',
  'yanga',
  'buzzbot',
  'mlbot',
  'YandexBot',
  'yandex.com\\/bots',
  'purebot',
  'Linguee Bot',
  'CyberPatrol',
  'voilabot',
  'Baiduspider',
  'citeseerxbot',
  'spbot',
  'twengabot',
  'postrank',
  'turnitinbot',
  'scribdbot',
  'page2rss',
  'sitebot',
  'linkdex',
  'Adidxbot',
  'blekkobot',
  'ezooms',
  'dotbot',
  'Mail.RU_Bot',
  'discobot',
  'heritrix',
  'findthatfile',
  'europarchive.org',
  'NerdByNature.Bot',
  'sistrix crawler',
  'Ahrefs(Bot|SiteAudit)',
  'fuelbot',
  'CrunchBot',
  'centurybot9',
  'IndeedBot',
  'mappydata',
  'woobot',
  'ZoominfoBot',
  'PrivacyAwareBot',
  'Multiviewbot',
  'SWIMGBot',
  'Grobbot',
  'eright',
  'Apercite',
  'semanticbot',
  'Aboundex',
  'domaincrawler',
  'wbsearchbot',
  'summify',
  'CCBot',
  'edisterbot',
  'seznambot',
  'ec2linkfinder',
  'gslfbot',
  'aiHitBot',
  'intelium_bot',
  'facebookexternalhit',
  'Yeti',
  'RetrevoPageAnalyzer',
  'lb-spider',
  'Sogou',
  'lssbot',
  'careerbot',
  'wotbox',
  'wocbot',
  'ichiro',
  'DuckDuckBot',
  'lssrocketcrawler',
  'drupact',
  'webcompanycrawler',
  'acoonbot',
  'openindexspider',
  'gnam gnam spider',
  'web-archive-net.com.bot',
  'backlinkcrawler',
  'coccoc',
  'integromedb',
  'content crawler spider',
  'toplistbot',
  'it2media-domain-crawler',
  'ip-web-crawler.com',
  'siteexplorer.info',
  'elisabot',
  'proximic',
  'changedetection',
  'arabot',
  'WeSEE:Search',
  'niki-bot',
  'CrystalSemanticsBot',
  'rogerbot',
  '360Spider',
  'psbot',
  'InterfaxScanBot',
  'CC Metadata Scaper',
  'g00g1e.net',
  'GrapeshotCrawler',
  'urlappendbot',
  'brainobot',
  'fr-crawler',
  'binlar',
  'SimpleCrawler',
  'Twitterbot',
  'cXensebot',
  'smtbot',
  'bnf.fr_bot',
  'A6-Indexer',
  'ADmantX',
  'Facebot',
  'OrangeBot\\/',
  'memorybot',
  'AdvBot',
  'MegaIndex',
  'SemanticScholarBot',
  'ltx71',
  'nerdybot',
  'xovibot',
  'BUbiNG',
  'Qwantify',
  'archive.org_bot',
  'Applebot',
  'TweetmemeBot',
  'crawler4j',
  'findxbot',
  'S[eE][mM]rushBot',
  'yoozBot',
  'lipperhey',
  'Y!J',
  'Domain Re-Animator Bot',
  'AddThis',
  'Screaming Frog SEO Spider',
  'MetaURI',
  'Scrapy',
  'Livelap[bB]ot',
  'OpenHoseBot',
  'CapsuleChecker',
  'collection@infegy.com',
  'IstellaBot',
  'DeuSu\\/',
  'betaBot',
  'Cliqzbot\\/',
  'MojeekBot\\/',
  'netEstate NE Crawler',
  'SafeSearch microdata crawler',
  'Gluten Free Crawler\\/',
  'Sonic',
  'Sysomos',
  'Trove',
  'deadlinkchecker',
  'Slack-ImgProxy',
  'Embedly',
  'RankActiveLinkBot',
  'iskanie',
  'SafeDNSBot',
  'SkypeUriPreview',
  'Veoozbot',
  'Slackbot',
  'redditbot',
  'datagnionbot',
  'Google-Adwords-Instant',
  'adbeat_bot',
  'WhatsApp',
  'contxbot',
  'pinterest',
  'electricmonk',
  'GarlikCrawler',
  'BingPreview\\/',
  'vebidoobot',
  'FemtosearchBot',
  'Yahoo Link Preview',
  'MetaJobBot',
  'DomainStatsBot',
  'mindUpBot',
  'Daum\\/',
  'Jugendschutzprogramm-Crawler',
  'Xenu Link Sleuth',
  'Pcore-HTTP',
  'moatbot',
  'KosmioBot',
  'pingdom',
  'PhantomJS',
  'Gowikibot',
  'PiplBot',
  'Discordbot',
  'TelegramBot',
  'Jetslide',
  'newsharecounts',
  'James BOT',
  'Barkrowler',
  'TinEye',
  'SocialRankIOBot',
  'trendictionbot',
  'Ocarinabot',
  'epicbot',
  'Primalbot',
  'DuckDuckGo-Favicons-Bot',
  'GnowitNewsbot',
  'Leikibot',
  'LinkArchiver',
  'YaK\\/',
  'PaperLiBot',
  'Digg Deeper',
  'dcrawl',
  'Snacktory',
  'AndersPinkBot',
  'Fyrebot',
  'EveryoneSocialBot',
  'Mediatoolkitbot',
  'Luminator-robots',
  'ExtLinksBot',
  'SurveyBot',
  'NING\\/',
  'okhttp',
  'Nuzzel',
  'omgili',
  'PocketParser',
  'YisouSpider',
  'um-LN',
  'ToutiaoSpider',
  'MuckRack',
  'Jamie\'s Spider',
  'AHC\\/',
  'NetcraftSurveyAgent',
  'Laserlikebot',
  'Apache-HttpClient',
  'AppEngine-Google',
  'Jetty',
  'Upflow',
  'Thinklab',
  'Traackr.com',
  'Twurly',
  'Mastodon',
  'http_get',
  'DnyzBot',
  'botify',
  '007ac9 Crawler',
  'BehloolBot',
  'BrandVerity',
  'check_http',
  'BDCbot',
  'ZumBot',
  'EZID',
  'ICC-Crawler',
  'ArchiveBot',
  '^LCC ',
  'filterdb.iss.net\\/crawler',
  'BLP_bbot',
  'BomboraBot',
  'Buck\\/',
  'Companybook-Crawler',
  'Genieo',
  'magpie-crawler',
  'MeltwaterNews',
  'Moreover',
  'newspaper\\/',
  'ScoutJet',
  '(^| )sentry\\/',
  'StorygizeBot',
  'UptimeRobot',
  'OutclicksBot',
  'seoscanners',
  'Hatena',
  'Google Web Preview',
  'MauiBot',
  'AlphaBot',
  'SBL-BOT',
  'IAS crawler',
  'adscanner',
  'Netvibes',
  'acapbot',
  'Baidu-YunGuanCe',
  'bitlybot',
  'blogmuraBot',
  'Bot.AraTurka.com',
  'bot-pge.chlooe.com',
  'BoxcarBot',
  'BTWebClient',
  'ContextAd Bot',
  'Digincore bot',
  'Disqus',
  'Feedly',
  'Fetch\\/',
  'Fever',
  'Flamingo_SearchEngine',
  'FlipboardProxy',
  'g2reader-bot',
  'imrbot',
  'K7MLWCBot',
  'Kemvibot',
  'Landau-Media-Spider',
  'linkapediabot',
  'vkShare',
  'Siteimprove.com',
  'BLEXBot\\/',
  'DareBoost',
  'ZuperlistBot\\/',
  'Miniflux\\/',
  'Feedspotbot\\/',
  'Diffbot\\/',
  'SEOkicks',
  'tracemyfile',
  'Nimbostratus-Bot',
  'zgrab',
  'PR-CY.RU',
  'AdsTxtCrawler',
  'Datafeedwatch',
  'Zabbix',
  'TangibleeBot',
  'google-xrawler',
  'axios',
  'Amazon CloudFront'
  ]
  let botMatch = false

  botPatterns.forEach(function(pattern){
    if (RegExp(pattern).test(ua)) {
      botMatch = true
    }
  })
  return botMatch
}