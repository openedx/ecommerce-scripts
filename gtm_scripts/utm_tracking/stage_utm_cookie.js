<script type="text/javascript">
    var iCookieLengthDays = 90; // Cookie length in days
    var sCookieName = "stage.edx.utm"; // Name of the first party cookie to utilise for last click referrer de-duplication
    var sSourceParameterName = "utm_source"; // The parameter used by networks and other marketing channels to tell you who drove the traffic
    var sMediumParameterName = "utm_medium"; // The parameter to identify the type of referrer
    var sCampaignParameterName = "utm_campaign"; // The parameter to identify the specific effort which drove the traffic
    var sTermParameterName = "utm_term"; // The parameter to identify the specific keyword which drove the traffic
    var sContentParameterName = "utm_content"; // The parameter to identify the campaign content.  Useful for differentiating A/B tests
    var sCookieDomain = "edx.org";

    var _getQueryStringValue = function (sParameterName) {
        var aQueryStringPairs = document.location.search.substring(1).split("&");
        for (var i = 0; i < aQueryStringPairs.length; i++) {
            var aQueryStringParts = aQueryStringPairs[i].split("=");
            if (sParameterName.toLowerCase() == aQueryStringParts[0].toLowerCase()) {
                return aQueryStringParts[1];
            }
        }
    };

    var _setCookie = function (sCookieName, sCookieContents, iCookieLengthDays) {
        var dCookieExpires = new Date(),
            iCookieLengthMilliseconds = iCookieLengthDays * 24 * 60 * 60 * 1000;
        dCookieExpires.setTime(dCookieExpires.getTime() + iCookieLengthMilliseconds);
        document.cookie = sCookieName + "=" + sCookieContents + "; expires=" + dCookieExpires.toGMTString() + "; path=/; domain=." + sCookieDomain + ";";
    };

    var sSourceValue = _getQueryStringValue(sSourceParameterName),
        sMediumeValue = _getQueryStringValue(sMediumParameterName),
        sCampaignValue = _getQueryStringValue(sCampaignParameterName),
        sTermValue = _getQueryStringValue(sTermParameterName),
        sContentValue = _getQueryStringValue(sContentParameterName);

    if ( sSourceValue || sMediumeValue || sCampaignValue || sTermValue || sContentValue ) {
        var oCookieContent = {
            utm_source: sSourceValue,
            utm_medium: sMediumeValue,
            utm_campaign: sCampaignValue,
            utm_term: sTermValue,
            utm_content: sContentValue
        };
        _setCookie(sCookieName, JSON.stringify(oCookieContent), iCookieLengthDays);
    }
</script>
