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
  const headers = rolloutGroupHeaders(request)
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

function rolloutGroupHeaders(request){
  //////////////////////////////////////////////////////////////////////
  //
  // THIS IS THE ONLY THING WE SHOULD BE EDITING DURING ROLLOUT
  //
  const cs_test_factor = 0.5;
  const bz_test_factor = 0.5;
  //
  //
  //
  //////////////////////////////////////////////////////////////////////

  const cookie_name = getCookieName(request)

  let group
  let isNew = false  // is the group newly-assigned?

  // Determine which group this request is in.
  let queryGroup = getQueryStringRolloutGroup(request);
  let cookieGroup = getCookieRolloutGroup(request, cookie_name);

  if (queryGroup) {
    group = `cs_${queryGroup}:bz_${queryGroup}:forced`;
    isNew = true;
  } else if (cookieGroup) {
    group = cookieGroup;
  } else {
    cs_group = Math.random() < cs_test_factor ? "cs_test" : "cs_control";
    bz_group = Math.random() < bz_test_factor ? "bz_test" : "bz_control";

    group = cs_group + ":" + bz_group + ":random";
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
        value: `${cookie_name}=${group}; Path=/`
      }
    )
  }

  return headers
}

function getQueryStringRolloutGroup(request){

  const url = new URL(request.url);
  if(url.searchParams.has("rollout")){
    let rollout_group = url.searchParams.get("rollout");
    if(rollout_group == "control" || rollout_group == "test"){
      return rollout_group;
    }
  }
}

function getCookieRolloutGroup(request, cookieName){
  const cookie = request.headers.get('Cookie')

  const indexOfCookieStart = cookie.indexOf(cookieName+'=')
  if( indexOfCookieStart > -1){
    const indexOfCookieEnd = cookie.indexOf(';', indexOfCookieStart+1)
    return cookie.substring(indexOfCookieStart + cookieName.length + 1, indexOfCookieEnd)
  }
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
