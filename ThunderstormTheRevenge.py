# API client
client_name = "xxx"
client_redirectURL = "xxx"
client_ID = 000
client_Secret = "xxx"

##################### METHOD: CHECK LIMIT RATE - if the number of remaining requests is equal to 1 or less, than wait 60 seconds
# to avoid incurring in any penalities (https://anilist.gitbook.io/anilist-apiv2-docs/overview/rate-limiting)
# PARAMETERS: response - response to a message that includes the rate limit fields among the headers
def checkRateLimit(response) :
    if int(response.headers["X-RateLimit-Remaining"]) <= 1 :
        import time
        print("oh shit, taking a pause cause I've almost finished the requests for this minute")
        time.sleep(60)


##################### METHOD: GETTING A PAGE (actually a post message)
# PARAMETERS: getNumber, number of the page to be retrieved; token, necessary to identify the client
# RETURNS: list of activities, 50 by default; empty list of the page retrieval was not successful
def getPage(pageNumber, token) :
    import requests
    uri = 'https://graphql.anilist.co'

    headerzzPage = {
        'Authorization': 'Bearer ' + token,
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    }

    query = '''
    query($isFollowing:Boolean = true, $hasReplies:Boolean = false, $activityType:ActivityType, $page:Int ){
        Page(page:$page, perPage:50 ){
            pageInfo{total perPage currentPage lastPage hasNextPage}
            activities(isFollowing:$isFollowing type:$activityType hasRepliesOrTypeText:$hasReplies type_in:[TEXT,ANIME_LIST,MANGA_LIST]sort:ID_DESC){
                ... on TextActivity{id userId type replyCount text isLocked isSubscribed isLiked likeCount createdAt user{id name donatorTier donatorBadge moderatorRoles avatar{large}}}
                ... on ListActivity{id userId type status progress replyCount isLocked isSubscribed isLiked likeCount createdAt user{id name donatorTier donatorBadge avatar{large}}media{id type status isAdult title{userPreferred}bannerImage coverImage{large}}}}
        }
    }
    '''

    variables = {
        'page': pageNumber, 
        'type': "following", 
        'filter': "all"
    }

    pageResponse = requests.post(uri, json={'query': query, 'variables': variables}, headers=headerzzPage)
    if pageResponse.status_code == 200:
        print("Page response : ", pageResponse)
    else :
        print(pageResponse.text)

    #Rate Limiting check!
    checkRateLimit(pageResponse)

    import json
    activities = pageResponse.json()
    if ('data' not in activities
        or 'Page' not in activities['data'] 
        or 'activities' not in activities['data']['Page']):
        return []
    else :
        return activities['data']['Page']['activities']


##################### METHOD: MAKE THE ACTIVITY POST REQUEST
# PARAMETERS: activityNumber, which uniquely identifies the activity, and the token code, necessary for the post request to be identified
# RETURN: True if the post is successful; False if the post is unsuccessful
def postLike(activityNumber, token) :
    import requests
    uri = 'https://graphql.anilist.co'

    headerzz = {
        'Authorization': 'Bearer ' + token,
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    }

    query = '''
    mutation ($id : Int, $type : LikeableType) { 
        ToggleLike : ToggleLikeV2( id : $id, type : $type ) { 
            ... on ListActivity {id likeCount isLiked}
            ... on MessageActivity {id likeCount isLiked}
            ... on TextActivity{id likeCount isLiked}
            ... on ActivityReply{id likeCount isLiked}
            ... on Thread{id likeCount isLiked}
            ... on ThreadComment{id likeCount isLiked}
        }
    }
    '''

    variables = {
        'id': activityNumber,
        'type' : "ACTIVITY"
    }

    response = requests.post(uri, json={'query': query, 'variables': variables}, headers=headerzz)
    
    #Rate limiting check!
    checkRateLimit(response)
    if response.status_code == 200:
        print("response : ", response)
        return True
    else :
        print(response.text)
        return False
    #just to check: webbrowser.open_new_tab("https://anilist.co/activity/" + str(activityNumber))


##################### METHOD: GET THE PAGE CODE
def getAuthorizationCode() :
    import sqlite3
    con = sqlite3.connect('C:\\Users\\andre\\AppData\\Local\\Google\\Chrome\\User Data\\Default\\History')
    cursor = con.cursor()
    cursor.execute("SELECT url FROM urls ORDER BY last_visit_time DESC LIMIT 10")
    urls = cursor.fetchall()
    #print to check
    #for i in range(0, len(urls)) :
    #    print(urls[i])
    #    print()

    found = False
    i = 0
    substring = client_redirectURL + "?code="
    while i < len(urls) and not(found):
        if substring in urls[i][0] :
            code = urls[i][0].replace(substring, "")
            found = True
    print(code)
    return code


##################### METHOD: GETTING THE STUPID ACCESS TOKEN
def getAccessToken(code) :
    import requests
    uri = 'https://anilist.co/api/v2/oauth/token'

    data = { 
        "grant_type" : "authorization_code", 
        "client_id" : client_ID, 
        "client_secret" : client_Secret, 
        "redirect_uri" : client_redirectURL, 
        "code": code
    }

    headerz = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    access_token = requests.post(url=uri, json=data, headers=headerz)
    print(access_token)
    print(access_token.json()["access_token"])
    token = access_token.json()["access_token"]

    return token


############### METHOD: TIME TO ITERATE! 
def postActivities(token) :
    import time
    pageCounter = 1
    likeCounter = 0 #count how many likes; maximum of 30 before 1minute time out
    listCounter = 0 #count the activity of the list that was reached (0 up to 49)
    continueFlag = True
    likes = 0

    with open('lastDate.txt', 'r') as file: # extracting the activity epoch up to which the algorithm has run
        data = file.read().rstrip()
    epochToReach = int(data) # and converting it to integer

    activities = getPage(pageCounter, token)
    while (len(activities) == 0) :
        activities = getPage(pageCounter, token)
    pageCounter += 1
    startingEpoch = activities[0].get('createdAt') #getting epoch of the most recent activity

    while (continueFlag and pageCounter < 100) :
        while (listCounter < 50 and continueFlag) :
            activity = activities[listCounter]
            if (activity.get('createdAt') < epochToReach) :
                continueFlag = False
            elif (likeCounter < 30) :
                if (not(activity.get('isLiked'))) :
                    successful = postLike(int(activity.get('id')), token)
                    if (successful) :
                        likeCounter += 1
                        likes += 1
                    else : 
                        time.sleep(60)
                        listCounter -= 1
                listCounter += 1
            else :
                time.sleep(60)
                likeCounter = 0
        if (continueFlag) : 
            listCounter = 0
            activities = getPage(pageCounter, token)
            while (len(activities) == 0) :
                activities = getPage(pageCounter, token)
            pageCounter += 1

    with open('lastDate.txt', "w") as file:
        file.write(str(startingEpoch))
    
    print(likes)


############### MAIN -> ffs I don't like the __main__
code = getAuthorizationCode()
token = getAccessToken(code)
postActivities(token)
print("My job is done!")


"""
import requests
url = 'https://graphql.anilist.co'

query = '''
mutation ($id : Int, $type : LikeableType) { 
    ToggleLike : ToggleLikeV2( id : $id, type : $type ) { 
        ... on ListActivity {id likeCount isLiked}
        ... on MessageActivity {id likeCount isLiked}
        ... on TextActivity{id likeCount isLiked}
        ... on ActivityReply{id likeCount isLiked}
        ... on Thread{id likeCount isLiked}
        ... on ThreadComment{id likeCount isLiked}
    }
}
'''

variables = {
    'id': 425783137,
    'type' : "ACTIVITY"
}

response = requests.post(url, json={'query': query, 'variables': variables})
if response.status_code == 200:
    print("response : ", response)
else :
    print(response.text)


"""