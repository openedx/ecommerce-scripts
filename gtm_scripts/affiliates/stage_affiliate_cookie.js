<script type="text/javascript">
    var iCookieLength = 30; // Cookie length in days
    var sCookieName = "stage_affiliate_id"; // Name of the first party cookie to utilise for last click referrer de-duplication
    var sSourceParameterName = "utm_source"; // The parameter used by networks and other marketing channels to tell you who drove the traffic
    var sMediumParameterName = "utm_medium"; // The parameter to identify the type of referrer
    var sPartnerValue = "affiliate_partner"; // We only set a cookie if `sMediumParameterName` is set to this value
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

    var _setCookie = function (sCookieName, sCookieContents, iCookieLength) {
        var dCookieExpires = new Date();
        dCookieExpires.setTime(dCookieExpires.getTime() + (iCookieLength * 24 * 60 * 60 * 1000));
        document.cookie = sCookieName + "=" + sCookieContents + "; expires=" + dCookieExpires.toGMTString() + "; path=/; domain=." + sCookieDomain + ";";
    };

    if (_getQueryStringValue(sSourceParameterName) && _getQueryStringValue(sMediumParameterName) === sPartnerValue) {
        _setCookie(sCookieName, _getQueryStringValue(sSourceParameterName), iCookieLength);
    }
</script>
