addEventListener('fetch', event => {
  event.passThroughOnException()
  if (
    event.request.url.indexOf('/admin') === -1 &&
    event.request.url.indexOf('/user') === -1 &&
    event.request.url.indexOf('/api') === -1
  ) {
    event.respondWith(fetchAndApply(event.request))
  } else {
    event.respondWith(fetchAndApplyDefault(event.request))
  }
})

async function fetchAndApplyDefault(request) {
  const response = await fetch(request)
  return response
}

async function fetchAndApply(request) {
  //////////////////////////////////////////////////////////////////////
  // SWITCHING THIS TO TRUE WILL UNSET ALL COOKIES AND HEADERS TO BE CONTROL
  const killswitch = false
  //////////////////////////////////////////////////////////////////////
  const headers = rolloutGroupHeaders(request, killswitch)
  const modifiedRequest = updateRequest(request, headers.request_headers)

  const response = await fetch(modifiedRequest)
  const modifiedResponse = updateResponse(response, headers.response_headers)

  return modifiedResponse
}

function updateRequest(request, newHeaders){
  const newRequest = new Request(request)
  newHeaders.forEach(function(header){
    newRequest.headers.set(header.name, header.value)
  })

  return newRequest
}

function updateResponse(response, newHeaders){
  const newResponse = new Response(response.body, response)
  newHeaders.forEach(function(header){
    console.log(header.name, ": ", header.value)
    newResponse.headers.set(header.name, header.value)
  })
  return newResponse
}

function rolloutGroupHeaders(request, killswitch){
  //////////////////////////////////////////////////////////////////////
  //
  // THIS IS THE ONLY THING WE SHOULD BE EDITING DURING ROLLOUT
  //
  const percent_in_test_group = 1
  //
  //
  //
  //////////////////////////////////////////////////////////////////////

  const cookie_name = getCookieName(request)
  const test_group_name = 'test'
  const control_group_name = 'control'
  const control_cookie_pattern = `${cookie_name}=${control_group_name}`
  const test_cookie_pattern = `${cookie_name}=${test_group_name}`

  let group          // 'control' or 'test', set below
  let cookie_group   // How the assignment was made + which group was assigned
  let isNew = false  // is the group newly-assigned?

  // Determine which group this request is in.
  let controlAssignment = presortToControl(request, control_cookie_pattern, control_group_name, percent_in_test_group, killswitch)
  let testAssignment = presortToTest(request, test_cookie_pattern, test_group_name, percent_in_test_group)
  if( controlAssignment.assignment ){
    group = control_group_name
    cookie_group = `${group}_${controlAssignment.assignment}`
    isNew = controlAssignment.isNew
  } else if ( testAssignment.assignment ){
    group = test_group_name
    cookie_group = `${group}_${testAssignment.assignment}`
    isNew = testAssignment.isNew
  } else {
    group = Math.random() < percent_in_test_group ? test_group_name : control_group_name
    cookie_group = `${group}_random1`
    isNew = true
  }

  // Override for killswitch
  if (killswitch) {
    group = control_group_name
    cookie_group = `${group}_forced`
    isNew = controlAssignment.isNew
  }

  // Override the group to be test_rolledout
  if (percent_in_test_group >= 1 && group == control_group_name) {
    group = test_group_name;
    cookie_group = `${test_group_name}_rolledout`;
    isNew = true;
  }

  let headers = {
    request_headers: [
      {
        name: 'x-rollout-group',
        value: group
      }
    ],
    response_headers: [
    ]
  }

  if( isNew ){

    headers.response_headers.push(
      {
        name: 'Set-Cookie',
        value: `${cookie_name}=${cookie_group}; Path=/`
      }
    )
  }

  return headers
}

function presortToControl(request, control_cookie_pattern, control_group, rollout_percentage, killswitch){
  let responseObj = {
    assignment: '',
    isNew: false,
  }
  const cookie = request.headers.get('Cookie')
  // If the killswitch is on, a user has a control cookie, and that cookie is forced, don't set isNew
  if (killswitch) {
    if (cookie && cookie.includes('forced')) {
      return responseObj
    } else {
      responseObj.isNew = true
      return responseObj
    }
  }

  // if query string includes the control param at the start (index 0)
  const url = new URL(request.url)
  if(url.searchParams.has("rollout") && url.searchParams.get("rollout").indexOf(control_group) === 0){
    responseObj.assignment =  "query"
    responseObj.isNew = true
    return responseObj
  }

  // If a user has a control cookie, keep them in the control group, unless that cookie is forced
  if ( cookie && cookie.includes(control_cookie_pattern) && !cookie.includes('forced')){
    responseObj.assignment =  assignmentMethod(cookie, control_cookie_pattern)
    return responseObj
  }

  // Always sort search engines and other crawlers to control if the rollout is less than 100%
  if( isSearchEngine(request) && rollout_percentage < 1){
    responseObj.assignment = "crawler"
    responseObj.isNew = true
    return responseObj
  }

  return responseObj
}

function presortToTest(request, test_cookie_pattern, test_group, rollout_percentage){
  let responseObj = {
    assignment: '',
    isNew: false,
  }

  // if query string includes test param at the start (index 0)
  const url = new URL(request.url)
  if(url.searchParams.has("rollout") && url.searchParams.get("rollout").indexOf(test_group) === 0){
    responseObj.assignment = "query"
    responseObj.isNew = true
    return responseObj
  }

  // If a user has a test cookie, keep them in the test group
  const cookie = request.headers.get('Cookie')
  if ( cookie && cookie.includes(test_cookie_pattern) ){
    responseObj.assignment = assignmentMethod(cookie, test_cookie_pattern)
    return responseObj
  }

  // Always sort search engines and other crawlers to test if the rollout is at 100%
  if( isSearchEngine(request) && rollout_percentage >= 1){
    responseObj.assignment = "crawler"
    responseObj.isNew = true
    return responseObj
  }

  return responseObj
}

function assignmentMethod(cookie, pattern){
  const indexOfCookieStart = cookie.indexOf(pattern+'_')
  const indexOfCookieEnd = cookie.indexOf(';', indexOfCookieStart+1)
  return cookie.substring(indexOfCookieStart + pattern.length, indexOfCookieEnd)
}

function getCookieName(request) {
  const prodCookieName = 'prod-edx-rollout-group'
  const stageCookieName = 'stage-edx-rollout-group'
  const prodEdxUrlPattern = /www\.edx\.org/

  if(request.url.match(prodEdxUrlPattern)){
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
