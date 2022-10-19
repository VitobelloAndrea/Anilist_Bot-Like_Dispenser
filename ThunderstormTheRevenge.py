import json
client = open("client.json")
variables = json.load(client)

client_name = variables["client_name"]
client_redirectURL = variables["client_redirectURL"]
client_ID = int(variables["client_ID"])
client_Secret = variables["client_Secret"]



##################### METHOD: CHECK LIMIT RATE - if the number of remaining requests is equal to 1 or less, than wait 60 seconds
# to avoid incurring in any penalities (https://anilist.gitbook.io/anilist-apiv2-docs/overview/rate-limiting)
# PARAMETERS: response - response to a message that includes the rate limit fields among the headers
def checkRateLimit(response) :
    if int(response.headers["X-RateLimit-Remaining"]) <= 1 :
        import time
        print("oh shit, taking a pause cause I've almost finished the requests for this minute")
        time.sleep(60)


##################### METHOD: GET USER ID - since the site only retrieves it after submitting the username
# PARAMS: targetUser = username; token
# RETURNS: userID if the username is found; 0 if the username is not found; -1 if other errors have occurred
def getUserID(targetUser, token, toFollow=False) :
    import requests
    uri = 'https://graphql.anilist.co'

    headerzzPage = {
        'Authorization': 'Bearer ' + token,
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    }

    #step 1: get the user ID
    query = '''
    query ( $id:Int, $name:String ) { 
        User(id:$id, name:$name ) { 
            id name previousNames{name updatedAt} avatar{large}
            bannerImage about isFollowing isFollower donatorTier 
            donatorBadge createdAt moderatorRoles isBlocked bans 
            options{profileColor restrictMessagesToFollowing}
            mediaListOptions{scoreFormat}
            statistics { 
                anime{count meanScore standardDeviation minutesWatched episodesWatched genrePreview:genres(limit:10,sort:COUNT_DESC){genre count}}
                manga{count meanScore standardDeviation chaptersRead volumesRead genrePreview:genres(limit:10,sort:COUNT_DESC){genre count}}
            }
            stats{activityHistory{date amount level}}
            favourites { 
                anime{edges{favouriteOrder node{id type status(version:2)format isAdult bannerImage title{userPreferred}coverImage{large}startDate{year}}}}
                manga{edges{favouriteOrder node{id type status(version:2)format isAdult bannerImage title{userPreferred}coverImage{large}startDate{year}}}}
                characters{edges{favouriteOrder node{id name{userPreferred}image{large}}}}staff{edges{favouriteOrder node{id name{userPreferred}image{large}}}}
                studios{edges{favouriteOrder node{id name}}}
            }
        }
    }'''

    variables = {
        'name': targetUser
    }
            
    pageResponse = requests.post(uri, json={'query': query, 'variables': variables}, headers=headerzzPage)
    if pageResponse.status_code == 200:
        print("Page response : ", pageResponse)
        userID = pageResponse.json()['data']['User']['id']
        isFollowing = pageResponse.json()['data']['User']['isFollowing']
    elif pageResponse.status_code == 404: #INVALID USERNAME - gotta ask for a new one
        print("Page response : ", pageResponse)
        userID = -1
    else:
        userID = 0 #the request didn't go through

    if toFollow:
        return (userID, isFollowing)
    return userID


##################### METHOD: GETTING A PAGE (actually a post message)
# PARAMETERS: getNumber, number of the page to be retrieved; token, necessary to identify the client
# RETURNS: list of activities, 50 by default; empty list of the page retrieval was not successful
# NOTICE: the page can either be a default followed page or a global list page (maybe a user page too in the near future)
# mode: tells the operation mode;
# mode = 0 -> followed list mode; likes are posted until a certain time epoch is reached.
# mode = 1 -> global list mode; a predetermined quantity of likes is posted.
# mode = 2 -> a predetermined quantity of likes is posted to a certain user.
def getPage(pageNumber, token, mode, userID) :
    import requests
    uri = 'https://graphql.anilist.co'

    headerzzPage = {
        'Authorization': 'Bearer ' + token,
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    }

    if mode == 0 or mode == 1 :
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
    elif mode == 2 :
        query = '''
        query ( $id:Int, $type:ActivityType, $page:Int ) {
            Page( page:$page, perPage:50 ) { 
                pageInfo{total perPage currentPage lastPage hasNextPage}
                activities( userId:$id, type:$type, sort:[PINNED,ID_DESC] ) {
                    ... on ListActivity{id type replyCount status progress isLocked isSubscribed isLiked isPinned likeCount createdAt user{id name avatar{large}}media{id type status(version:2)isAdult bannerImage title{userPreferred}coverImage{large}}}
                    ... on TextActivity{id type text replyCount isLocked isSubscribed isLiked isPinned likeCount createdAt user{id name avatar{large}}}
                    ... on MessageActivity{id type message replyCount isPrivate isLocked isSubscribed isLiked likeCount createdAt user:recipient{id}messenger{id name donatorTier donatorBadge moderatorRoles avatar{large}}}
                }
            }
        }'''
        
    #selecting variables depending on the mode the algorithm is running on
    if mode == 0: #mode = 0 -> default
        variables = {
            'page': pageNumber, 
            'type': "following", 
            'filter': "all"
        }
    elif mode == 1: #mode = 1 -> global
        variables = {
            'page': 1, 
            'type': 'global', 
            'filter': 'all', 
            'isFollowing': False, 
            'hasReplies': True
        }
    elif mode == 2 : #mode = 2 -> target user
        variables = {
            'id': userID, 
            'page': pageNumber
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
    if response.status_code == 200 or response.status_code == 404 or response.status_code == 400 and "This user cannot currently receive likes" in response.text: #if everything was alright or the activity was deleted
        print("response : ", response)
        return True
    else :
        print(response.text)
        print(response)
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
    #print(code)
    print("Authorization Code obtained")
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
    #print(access_token)
    #print(access_token.json()["access_token"])
    print("Token obtained\n")
    token = access_token.json()["access_token"]

    return token


"""DEPRECATED, SOON TO BE DELETED"""
def postActivities(token, mode, targetUser) :
    import time
    pageCounter = 1
    likeCounter = 0 #count how many likes; maximum of 30 before 1minute time out
    listCounter = 0 #count the activity of the list that was reached (0 up to 49)
    likes = 0
    
    if mode == 3 :
        mode = 2
        userToFollow = targetUser

    if mode == 0 :
        continueFlag = True #MODE 0 variable necessary to determine for how long to continue
        with open('lastDate.txt', 'r') as file: # extracting the activity epoch up to which the algorithm has run
            data = file.read().rstrip()
        epochToReach = int(data) # and converting it to integer
    elif mode == 1 or mode == 2:
        continueFlag = input("Enter the number of activities to like (max50): ") #MODE 1/2 variable
        try :
            continueFlag = int(continueFlag)
        except ValueError:
            print("wrong input")
            return
        if continueFlag > 50 :
            continueFlag = 50

    activities = getPage(pageCounter, token, mode, userID=None)
    while (len(activities) == 0) : #when errors occur and I get a 0 len page, I try again
        activities = getPage(pageCounter, token, mode, userID=None)
    while (len(activities) == 1 and activities[0] == 0) : #(mode 2) when the targetUser is not valid I ask for another one
        targetUser = input("The inserted username is not valid. Enter another one: ")
        activities = getPage(pageCounter, token, mode, userID=None)
    pageCounter += 1

    if mode == 0 :
        startingEpoch = activities[0].get('createdAt') #getting epoch of the most recent activity
    elif mode == 1:
        pageCounter = 1

    while (continueFlag and pageCounter < 100) :
        while (listCounter < len(activities) and continueFlag) :
            activity = activities[listCounter]
            if ((mode == 0 and activity.get('createdAt') < epochToReach)) : #or (mode == 1 and not(continueFlag))
                continueFlag = False
            elif (likeCounter < 30) :
                if (not(activity.get('isLiked'))) :
                    successful = postLike(int(activity.get('id')), token)
                    if (successful) :
                        likeCounter += 1
                        likes += 1
                        if mode == 1 or mode == 2:
                            continueFlag -= 1
                    else : 
                        time.sleep(60)
                        listCounter -= 1
                listCounter += 1
            else :
                time.sleep(60)
                likeCounter = 0
        if (continueFlag) : 
            listCounter = 0
            activities = getPage(pageCounter, token, mode, userID=None)
            while (len(activities) == 0) :
                activities = getPage(pageCounter, token, mode, userID=None)
            if mode == 1 or mode == 2:
                pageCounter += 1
            elif mode == 1:
                pageCounter = 1 #becuse global activities refresh so fast page 1 becomes page 2 in the meanwhile, so just go on with page 0
                time.sleep(15) #so I just wait 15 seconds and ask for the same first page again

    if mode == 0 :
        with open('lastDate.txt', "w") as file:
            file.write(str(startingEpoch))
    
    print("posted likes: " + str(likes))

    if userToFollow :
        #TODO: IMPLEMENT followUser method
        if 1==1:
            print(True)

"""DEPRECATED, SOON TO BE DELETED"""
def callGlobal(token) :
    import requests
    uri = 'https://graphql.anilist.co'

    headerzzPage = {
        'Authorization': 'Bearer ' + token,
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    }

    query = '''
    query ( $isFollowing:Boolean = true, $hasReplies:Boolean = false, $activityType:ActivityType, $page:Int ) { 
        Page ( page:$page, perPage:50 ) {
            pageInfo { total perPage currentPage lastPage hasNextPage }
            activities ( isFollowing:$isFollowing type:$activityType hasRepliesOrTypeText:$hasReplies type_in:[TEXT,ANIME_LIST,MANGA_LIST]sort:ID_DESC) {
                ... on TextActivity{id userId type replyCount text isLocked isSubscribed isLiked likeCount createdAt user{id name donatorTier donatorBadge moderatorRoles avatar{large}}}
                ... on ListActivity{id userId type status progress replyCount isLocked isSubscribed isLiked likeCount createdAt user{id name donatorTier donatorBadge avatar{large}}media{id type status isAdult title{userPreferred}bannerImage coverImage{large}}}
            }
        }
    }
    '''

    variables = {
        'page': 1, 
        'type': 'global', 
        'filter': 'all', 
        'isFollowing': False, 
        'hasReplies': True
    }


    pageResponse = requests.post(uri, json={'query': query, 'variables': variables}, headers=headerzzPage)
    if pageResponse.status_code == 200:
        print("Page response : ", pageResponse)
    else :
        print(pageResponse.text)
    print(pageResponse.json())


##################### METHOD: ITERATION ON FOLLOWED FEED
def postFeed(token) :
    blacklistFile = open("blacklist.txt", "r") #open file in read mode
    blacklist = blacklistFile.readline() #and read in as a whole string
    blacklistFile.close()
    blacklist = blacklist.split(",") #split it in strings
    del blacklist[-1] #remove the last ""
    blacklist = [int(id) for id in blacklist] #and converte all to ints, so that comparisons are faster
    blackset = set(blacklist) #then turn the list into a set for more efficiency
    print("blacklist: " + str(blackset))

    import time
    pageCounter = 1
    likeCounter = 0 #count how many likes; maximum of 30 before 1minute time out
    listCounter = 0 #count the activity of the list that was reached (0 up to 49)
    likes = 0

    continueFlag = True #variable necessary to determine for how long to continue
    with open('lastDate.txt', 'r') as file: # extracting the activity epoch up to which the algorithm has run
        data = file.read().rstrip()
    epochToReach = int(data) # and converting it to integer

    activities = getPage(pageCounter, token, mode=0, userID=None)
    while (len(activities) == 0) : #when errors occur and I get a 0 len page, I try again
        activities = getPage(pageCounter, token, mode=0, userID=None)
    pageCounter += 1

    startingEpoch = activities[0].get('createdAt') #getting epoch of the most recent activity

    while (continueFlag and pageCounter < 100) :
        while (listCounter < len(activities) and continueFlag) :
            activity = activities[listCounter]
            if (activity.get('createdAt') < epochToReach) :
                continueFlag = False
            elif (likeCounter < 30) :
                if (not(activity.get('isLiked')) and not activity.get('userId') in blackset) :
                    successful = postLike(int(activity.get('id')), token)
                    if (successful) :
                        likeCounter += 1
                        likes += 1
                    else : 
                        time.sleep(60)
                        likeCounter = 0 ########### IF THERE IS A MISTAKE IT'S HERE
                        listCounter -= 1
                listCounter += 1
            else :
                time.sleep(60)
                likeCounter = 0
        if (continueFlag) : 
            listCounter = 0
            activities = getPage(pageCounter, token, mode=0, userID=None)
            while (len(activities) == 0) :
                activities = getPage(pageCounter, token, mode=0, userID=None)
            pageCounter += 1

    with open('lastDate.txt', "w") as file:
        file.write(str(startingEpoch))
    
    print("posted likes: " + str(likes))


##################### METHOD: ITERATION ON GLOBAL FEED
def postGlobal(token) :
    import time
    pageCounter = 1
    likeCounter = 0 #count how many likes; maximum of 30 before 1minute time out
    listCounter = 0 #count the activity of the list that was reached (0 up to 49)
    likes = 0

    continueFlag = input("Enter the number of activities to like (max50): ")
    try :
        continueFlag = int(continueFlag)
    except ValueError:
        print("wrong input")
        return
    if continueFlag > 50 :
        continueFlag = 50

    activities = getPage(pageCounter, token, mode=1, userID=None)
    while (len(activities) == 0) : #when errors occur and I get a 0 len page, I try again
        activities = getPage(pageCounter, token, mode=1, userID=None)

    while (continueFlag and pageCounter < 100) :
        while (listCounter < len(activities) and continueFlag) :
            activity = activities[listCounter]
            if (likeCounter < 30) :
                if (not(activity.get('isLiked'))) :
                    successful = postLike(int(activity.get('id')), token)
                    if (successful) :
                        likeCounter += 1
                        likes += 1
                        continueFlag -= 1
                    else : 
                        time.sleep(60)
                        likeCounter = 0 ########### IF THERE IS A MISTAKE IT'S HERE
                        listCounter -= 1
                listCounter += 1
            else :
                time.sleep(60)
                likeCounter = 0
        if (continueFlag) : 
            listCounter = 0
            activities = getPage(pageCounter, token, mode=1, userID=None)
            while (len(activities) == 0) :
                activities = getPage(pageCounter, token, mode=1, userID=None)
            time.sleep(15) #so I just wait 15 seconds and ask for the same first page again
    
    print("posted likes: " + str(likes))


##################### METHOD: ITERATION ON USER
def postUser(token, targetUser) :
    import time
    pageCounter = 1
    likeCounter = 0 #count how many likes; maximum of 30 before 1minute time out
    listCounter = 0 #count the activity of the list that was reached (0 up to 49)
    likes = 0

    continueFlag = input("Enter the number of activities to like (max50): ") #MODE 1/2 variable
    try :
        continueFlag = int(continueFlag)
    except ValueError:
        print("wrong input")
        return
    if continueFlag > 50 :
        continueFlag = 50

    userID = getUserID(targetUser, token)
    while userID == 0 or userID == -1 :
        if (userID == 0) :
            userID = getUserID(targetUser, token)
        if (userID == -1) :
            targetUser = input("The inserted username is not valid. Enter another one: ")
            userID = getUserID(targetUser, token)

    activities = getPage(pageCounter, token, mode=2, userID=userID)
    while (len(activities) == 0) : #when errors occur and I get a 0 len page, I try again
        activities = getPage(pageCounter, token, mode=2, userID=userID)
    pageCounter += 1

    while (continueFlag and pageCounter < 100) :
        while (listCounter < len(activities) and continueFlag) :
            activity = activities[listCounter]
            if (likeCounter < 30) :
                if (not(activity.get('isLiked'))) :
                    successful = postLike(int(activity.get('id')), token)
                    if (successful) :
                        likeCounter += 1
                        likes += 1
                        continueFlag -= 1
                    else : 
                        time.sleep(60)
                        likeCounter = 0 ########### IF THERE IS A MISTAKE IT'S HERE
                        listCounter -= 1
                listCounter += 1
            else :
                time.sleep(60)
                likeCounter = 0
        if (continueFlag) : 
            listCounter = 0
            activities = getPage(pageCounter, token, mode=2, userID=userID)
            while (len(activities) == 0) :
                activities = getPage(pageCounter, token, mode=2, userID=userID)
            pageCounter += 1
    
    print("posted likes: " + str(likes))


##################### METHOD: FOLLOW USER
def followUser(token, targetUser):
    userID = getUserID(targetUser, token, toFollow=True)
    while userID[0] == 0 or userID[0] == -1 :
        if (userID[0] == 0) :
            userID = getUserID(targetUser, token, toFollow=True)
        if (userID[0] == -1) :
            targetUser = input("The inserted username is not valid. Enter another one: ")
            userID = getUserID(targetUser, token, toFollow=True)

    if userID[1]:
        return True

    import requests
    uri = 'https://graphql.anilist.co'

    headerzzPage = {
        'Authorization': 'Bearer ' + token,
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    }
    
    query = '''mutation($id:Int){ToggleFollow(userId:$id){id name isFollowing}}'''

    variables = {
            'id': userID[0]
    }

    pageResponse = requests.post(uri, json={'query': query, 'variables': variables}, headers=headerzzPage)
    if pageResponse.status_code == 200:
        print("Page response : ", pageResponse)
        print("\n")
    else :
        print(pageResponse.text)
        return False
    print(pageResponse.json())


##################### METHOD: BLACKLIST USER
def blacklistUser(token, targetUser):
    userID = getUserID(targetUser, token)
    while userID == 0 or userID == -1 :
        if (userID == 0) :
            userID = getUserID(targetUser, token)
        if (userID == -1) :
            targetUser = input("The inserted username is not valid. Enter another one: ")
            userID = getUserID(targetUser, token)
    userID = str(userID) + ','

    blacklistFile = open("blacklist.txt", "a")
    blacklistFile.write(userID)
    blacklistFile.close()


##################### METHOD: BLACKLIST USER
def whitelistUser(token, targetUser):
    userID = getUserID(targetUser, token)
    while userID == 0 or userID == -1 :
        if (userID == 0) :
            userID = getUserID(targetUser, token)
        if (userID == -1) :
            targetUser = input("The inserted username is not valid. Enter another one: ")
            userID = getUserID(targetUser, token)
    userID = str(userID) + ','

    blacklistFile = open("blacklist.txt", "r")
    blacklist = blacklistFile.read()
    blacklistFile.close()
    newblacklist = blacklist.replace(userID, "")
    if newblacklist != blacklist :
        blacklistFile = open("blacklist.txt", "w")
        blacklistFile.write(newblacklist)
        blacklistFile.close()


##################### METHOD: GET USERID OF BLACKLIST USERS
def getBlacklistedUsers(token):
    def getUserName(userID):
        import requests
        uri = 'https://graphql.anilist.co'

        headerzzPage = {
            'Authorization': 'Bearer ' + token,
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }

        query = '''query($id:Int,$name:String){
            User(id:$id,name:$name){
                id name previousNames{name updatedAt}avatar{large}bannerImage about isFollowing isFollower donatorTier donatorBadge createdAt moderatorRoles isBlocked bans options{profileColor restrictMessagesToFollowing}mediaListOptions{scoreFormat}statistics{
                    anime{count meanScore standardDeviation minutesWatched episodesWatched genrePreview:genres(limit:10,sort:COUNT_DESC){genre count}}
                    manga{count meanScore standardDeviation chaptersRead volumesRead genrePreview:genres(limit:10,sort:COUNT_DESC){genre count}}}
                    stats{activityHistory{date amount level}}
                    favourites{
                        anime{edges{favouriteOrder node{id type status(version:2)format isAdult bannerImage title{userPreferred}coverImage{large}startDate{year}}}}
                        manga{edges{favouriteOrder node{id type status(version:2)format isAdult bannerImage title{userPreferred}coverImage{large}startDate{year}}}}
                        characters{edges{favouriteOrder node{id name{userPreferred}image{large}}}}
                        staff{edges{favouriteOrder node{id name{userPreferred}image{large}}}}
                        studios{edges{favouriteOrder node{id name}}
                    }
                }
            }
        }'''


        variables = {
            'id': userID, 
        }

        pageResponse = requests.post(uri, json={'query': query, 'variables': variables}, headers=headerzzPage)
        if pageResponse.status_code == 200:
            print("Page response : ", pageResponse)
        else :
            print(pageResponse.text)

        #Rate Limiting check!
        checkRateLimit(pageResponse)

        import json
        page = pageResponse.json()
        if ('data' not in page
            or 'User' not in page['data'] 
            or 'name' not in page['data']['User']):
            return []
        else :
            return page['data']['User']['name']

    blackListFile = open("blacklist.txt", "r")
    blacklist = blackListFile.read()
    blackListFile.close()
    blacklist = blacklist.split(',') #individual ids
    del blacklist[-1] #deleting ""

    blacklistedNames = []
    for id in blacklist:
        blacklistedNames.append(getUserName(int(id)))
    
    print("Blacklisted Users: " + str(blacklistedNames))


##################### METHOD: DELETE ALL LIKES FORM A USER PAGE
def nukeUser(token, targetUser):
    userID = getUserID(targetUser, token)
    while userID == 0 or userID == -1 :
        if (userID == 0) :
            userID = getUserID(targetUser, token)
        if (userID == -1) :
            targetUser = input("The inserted username is not valid. Enter another one: ")
            userID = getUserID(targetUser, token)

    import time
    pageCounter = 1
    likeCounter = 0 #count how many activities; maximum of 30 before 1minute time out
    listCounter = 0 #count the activity of the list that was reached (0 up to 49)
    un_likes = 0

    #this algo goes on un-liking posts until there is a page with no likes in them
    #the continueFlag is thus set False each time a new page is retrieved and set to True whever the first like is found in a page
    continueFlag = True

    activities = getPage(pageCounter, token, mode=2, userID=userID)
    while (len(activities) == 0) : #when errors occur and I get a 0 len page, I try again
        activities = getPage(pageCounter, token, mode=2, userID=userID)
    pageCounter += 1

    while (continueFlag and pageCounter < 100) :
        continueFlag = False #setup continueFlag to false
        while (listCounter < len(activities)) :
            activity = activities[listCounter]
            if (likeCounter < 30) :
                if (activity.get('isLiked')) :
                    successful = postLike(int(activity.get('id')), token)
                    if (successful) :
                        continueFlag = True
                        likeCounter += 1
                        un_likes += 1
                    else : 
                        time.sleep(60)
                        likeCounter = 0 ########### IF THERE IS A MISTAKE IT'S HERE
                        listCounter -= 1
                listCounter += 1
            else :
                time.sleep(60)
                likeCounter = 0
        if (continueFlag) : 
            listCounter = 0
            activities = getPage(pageCounter, token, mode=2, userID=userID)
            while (len(activities) == 0) :
                activities = getPage(pageCounter, token, mode=2, userID=userID)
            pageCounter += 1
    
    print("posted un-likes: " + str(un_likes))



############### MAIN -> ffs I don't like the __main__
def main():
    code = getAuthorizationCode()
    token = getAccessToken(code)

    presentation = """
            Enter activity mode:
                0-Followed users;
                1-Global users;
                2-Target user;
                3-Target & follow;
                4-Blacklist User;
                5-Whitelist User;
                6-Get Blacklisted Users;
                7-Nuke user;
                Else-end.\n
            Selected Mode:"""

    mode = 0
    while mode >= 0 and mode <= 7 :
        mode = input(presentation)
        try :
            mode = int(mode)
        except ValueError:
            print("wrong input")

        targetUser = ""

        if mode == 0:
            print("Activating followed users mode")
            postFeed(token)

        elif mode == 1:
            print("Activating global users mode")
            postGlobal(token)

        elif mode == 2 or mode == 3:
            targetUser = input("Enter the targetted username: ")
            print("Targetting user " + targetUser)
            postUser(token, targetUser)
            if mode == 3:
                while not followUser(token, targetUser):
                    pass

        elif mode == 4:
            targetUser = input("Enter the user to blacklist: ")
            print("Blacklisting user " + targetUser)
            blacklistUser(token, targetUser)

        elif mode == 5:
            targetUser = input("Enter the user to whitelist: ")
            print("Whitelisting user " + targetUser)
            whitelistUser(token, targetUser)

        elif mode == 6:
            getBlacklistedUsers(token)

        elif mode == 7:
            targetUser = input("Enter the user to nuke: ")
            print("Nuking user " + targetUser)
            nukeUser(token, targetUser)

        else:
            print("thanks for your participation")

        print("My job is done!")



if __name__ == "__main__":
    main()


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