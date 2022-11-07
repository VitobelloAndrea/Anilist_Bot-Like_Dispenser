import json
import time
import requests
import sqlite3

client = open("client.json")
variables = json.load(client)
client.close() #if there is a mistake, here! delete this!

client_name = variables["client_name"]
client_redirectURL = variables["client_redirectURL"]
client_ID = int(variables["client_ID"])
client_Secret = variables["client_Secret"]



##################### METHOD: CHECK LIMIT RATE - if the number of remaining requests is equal to 1 or less, than wait 60 seconds
# to avoid incurring in any penalities (https://anilist.gitbook.io/anilist-apiv2-docs/overview/rate-limiting)
# PARAMETERS: response - response to a message that includes the rate limit fields among the headers
def checkRateLimit(response) :
    if "x-ratelimit-remaining" in response.headers and int(response.headers["x-ratelimit-remaining"]) <= 1 :
        print("oh shit, taking a pause cause I've almost finished the requests for this minute")
        time.sleep(60)


##################### METHOD: GET USER ID - since the site only retrieves it after submitting the username
# PARAMS: targetUser = username; token
# RETURNS: userID if the username is found; 0 if the username is not found; -1 if other errors have occurred
def getUserID(targetUser, token, toFollow=False) :
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
    while pageResponse.status_code != 200:
        print("Page response : ", pageResponse)
        if pageResponse.status_code == 404: #INVALID USERNAME
            targetUser = input("The inserted username is not valid. Enter another one: ")
            variables = { 'name': targetUser }
            pageResponse = requests.post(uri, json={'query': query, 'variables': variables}, headers=headerzzPage)
        elif pageResponse.status_code == 429: #TOO MANY REQUESTS: GOTTA TAKE A PAUSE
            print("Too many requests - getUser taking a nap")
            time.sleep(60)
        else: #ALL OTHER CASES -> do it again, kek
            pageResponse = requests.post(uri, json={'query': query, 'variables': variables}, headers=headerzzPage)
    
    #now pageResponse.status_code is 200
    print("Page response : ", pageResponse)
    userID = pageResponse.json()['data']['User']['id']
    isFollowing = pageResponse.json()['data']['User']['isFollowing']
    
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
# mode = 3 -> getting notifications
def getPage(pageNumber, token, mode, userID) :
    uri = 'https://graphql.anilist.co'

    headerzzPage = {
        'Authorization': 'Bearer ' + token,
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    }

    #selecting query and variable depending on the mode
    if mode == 0 : #mode 0 -> feed
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

    elif mode == 1 : #mode 1 -> global feed
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
            'page': 1, 
            'type': 'global', 
            'filter': 'all', 
            'isFollowing': False, 
            'hasReplies': True
        }

    elif mode == 2 : #mode 2 -> followed user
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
        variables = {
            'id': userID, 
            'page': pageNumber
        }

    elif mode == 3 : #mode 3 -> getting notifications
        #Here I removed some lines to try and make the request less expensive
        query = '''query($page:Int,$types:[NotificationType]){
            Page(page:$page,perPage:50){
                pageInfo{total perPage currentPage lastPage hasNextPage}
                notifications(type_in:$types,resetNotificationCount:true){
                    ... on ActivityMentionNotification{id type context activityId user{id name}createdAt}
                    ... on ActivityLikeNotification{id type context activityId user{id name}createdAt}
                }
            }
        }'''

        variables = {
            'page': pageNumber, 
            'feed': "activity", 
            'types': ["ACTIVITY_MENTION", "ACTIVITY_LIKE"]
        }

    pageResponse = requests.post(uri, json={'query': query, 'variables': variables}, headers=headerzzPage)
    while pageResponse.status_code != 200: #things didn't go as expected, so doing it again cause why not
        print(pageResponse.text)
        if pageResponse.status_code == 429:
            print("Too many requests - getPage taking a nap")
            time.sleep(60)
        pageResponse = requests.post(uri, json={'query': query, 'variables': variables}, headers=headerzzPage)

    #now we finally got our status code 200
    print("Page response : ", pageResponse)

    #Rate Limiting check!
    checkRateLimit(pageResponse)

    """
    activities = pageResponse.json()
    if ('data' not in activities
        or 'Page' not in activities['data'] 
        or 'activities' not in activities['data']['Page']):
        return []
    else :
        return activities['data']['Page']['activities']
    """
    #now since all pages have status code 200 I can delete all that commented shit above, right?
    activities = pageResponse.json()
    if mode != 3 :
        return activities['data']['Page']['activities'], activities['data']['Page']['pageInfo']['hasNextPage']
    elif mode == 3 :
        return activities['data']['Page']['notifications'], activities['data']['Page']['pageInfo']['hasNextPage']


##################### METHOD: MAKE THE ACTIVITY POST REQUEST
# PARAMETERS: activityNumber, which uniquely identifies the activity, and the token code, necessary for the post request to be identified
# RETURN: True if the post is successful; False if the post is unsuccessful
def postLike(activityNumber, token) :
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


##################### METHOD: GET THE PAGE CODE
def getAuthorizationCode() :
    con = sqlite3.connect('C:\\Users\\andre\\AppData\\Local\\Google\\Chrome\\User Data\\Default\\History')
    cursor = con.cursor()
    cursor.execute("SELECT url FROM urls ORDER BY last_visit_time DESC LIMIT 30")
    urls = cursor.fetchall()

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
    print("Token obtained\n")
    token = access_token.json()["access_token"]

    return token


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

    pageCounter = 1
    likeCounter = 0 #count how many likes; maximum of 30 before 1minute time out
    listCounter = 0 #count the activity of the list that was reached (0 up to 49)
    likes = 0

    continueFlag = True #variable necessary to determine for how long to continue
    with open('lastDate.txt', 'r') as file: # extracting the activity epoch up to which the algorithm has run
        data = file.read().rstrip()
    epochToReach = int(data) # and converting it to integer

    activities, hasNextPage = getPage(pageCounter, token, mode=0, userID=None)
    pageCounter += 1

    startingEpoch = activities[0].get('createdAt') #getting epoch of the most recent activity

    while (continueFlag and hasNextPage) :
        while (listCounter < len(activities) and continueFlag) :
            activity = activities[listCounter]
            if (activity.get('createdAt') < epochToReach) :
                continueFlag = False
            elif (likeCounter < 30) :
                if (not(activity.get('isLiked')) and ((not activity.get('userId') in blackset) or (likeCounter % 10 == 0))) : #randomply liking blacklisted users with probability about 1/10 (using likeCounter cause that way I can avoid importing random)
                    successful = postLike(int(activity.get('id')), token)
                    if (successful) :
                        likeCounter += 1
                        likes += 1
                    else : 
                        print("Unsuccessful message -> taking a pause")
                        time.sleep(60)
                        likeCounter = 0 ########### IF THERE IS A MISTAKE IT'S HERE
                        listCounter -= 1
                listCounter += 1
            else :
                print("Reached 30 like requests -> taking a pause")
                time.sleep(60)
                likeCounter = 0
        if (continueFlag) : 
            listCounter = 0
            activities, hasNextPage = getPage(pageCounter, token, mode=0, userID=None)
            pageCounter += 1

    with open('lastDate.txt', "w") as file:
        file.write(str(startingEpoch))
    
    print("posted likes: " + str(likes))


##################### METHOD: ITERATION ON GLOBAL FEED
def postGlobal(token) :
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

    activities, hasNextPage = getPage(pageCounter, token, mode=1, userID=None)

    while (continueFlag and hasNextPage) :
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
                        print("Unsuccessful message -> taking a pause")
                        time.sleep(60)
                        likeCounter = 0 ########### IF THERE IS A MISTAKE IT'S HERE
                        listCounter -= 1
                listCounter += 1
            else :
                print("Reached 30 like requests -> taking a pause")
                time.sleep(60)
                likeCounter = 0
        if (continueFlag) : 
            listCounter = 0
            activities, hasNextPage = getPage(pageCounter, token, mode=1, userID=None)
            time.sleep(15) #so I just wait 15 seconds and ask for the same first page again
    
    print("posted likes: " + str(likes))


##################### METHOD: ITERATION ON USER
def postUser(token, targetUser) :
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

    activities, hasNextPage = getPage(pageCounter, token, mode=2, userID=userID)
    pageCounter += 1

    while (continueFlag and hasNextPage) :
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
                        print("Unsuccessful message -> taking a pause")
                        time.sleep(60)
                        likeCounter = 0 ########### IF THERE IS A MISTAKE IT'S HERE
                        listCounter -= 1
                listCounter += 1
            else :
                print("Reached 30 like requests -> taking a pause")
                time.sleep(60)
                likeCounter = 0
        if (continueFlag) : 
            listCounter = 0
            activities, hasNextPage = getPage(pageCounter, token, mode=2, userID=userID)
            pageCounter += 1
    
    print("posted likes: " + str(likes))


##################### METHOD: FOLLOW USER
def followUser(token, targetUser):
    userID = getUserID(targetUser, token, toFollow=True)

    if userID[1]: #the user is already followed, so we can go back to the main
        return

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
    while pageResponse.status_code != 200:
        print(pageResponse.text)
        if pageResponse.status_code == 429:
            print("Too many requests - followUser taking a nap")
            time.sleep(60)
        pageResponse = requests.post(uri, json={'query': query, 'variables': variables}, headers=headerzzPage)
    
    #at this point pageResponse.status_code is 200
    print("Page response : ", pageResponse)
    print(pageResponse.json())


##################### METHOD: BLACKLIST USER
def blacklistUser(token, targetUser):
    userID = getUserID(targetUser, token)
    userID = str(userID) + ','

    blacklistFile = open("blacklist.txt", "a")
    blacklistFile.write(userID)
    blacklistFile.close()


##################### METHOD: BLACKLIST USER
def whitelistUser(token, targetUser):
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

    pageCounter = 1
    likeCounter = 0 #count how many activities; maximum of 30 before 1minute time out
    listCounter = 0 #count the activity of the list that was reached (0 up to 49)
    un_likes = 0

    #this algo goes on un-liking posts until there is a page with no likes in them
    #the continueFlag is thus set False each time a new page is retrieved and set to True whever the first like is found in a page
    continueFlag = True

    activities, hasNextPage = getPage(pageCounter, token, mode=2, userID=userID)
    pageCounter += 1

    while (continueFlag and hasNextPage) :
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
            activities, hasNextPage = getPage(pageCounter, token, mode=2, userID=userID)
            pageCounter += 1
    
    print("posted un-likes: " + str(un_likes))


##################### METHOD: FOLLOW SPREE FROM USER'S FOLLOWING LIST
# Objective: 
# 1. follow all users from someone's following list
# 2. add all those users to a greylist with a timestamp
# 3. check after a week against the activities received analytics
# TODO -> it will be easier to solve this with already the analytics
def followSpree(token, targetUser):
    userID = getUserID(targetUser, token)
    pageNumber = 1
    pass

    #to implement separately: getting a batch of users
    #alternative to avoid making a new function, make it an iteration
    #->ask for new pages as long as "hasnext", and concatenate users
    headerzzPage = {
        'Authorization': 'Bearer ' + token,
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    }

    pageQuery = '''
    query( $id:Int!, $page:Int ){
        Page( page:$page ){
            pageInfo{total perPage currentPage lastPage hasNextPage}
            following(userId:$id,sort:USERNAME){id name}
        }
    }'''

    variables = {
        'id': userID, 
        'type': "following", 
        'page': pageNumber
    }
    #remember to ask for new pages until "hasnext" becomes false

    #then: this will be computationally expensive
    #for all users in the list, perform
    #0. if the user is not followed
    #1. postUser with a random number of likes between 10 and 15
    #2. followUser
    #3. add the user to the greylist

    #TODO: add a function "updateGreyList" so that
    #1. for all users in the greyList
    #2. check if elapsed time is greater than 4 days
    #3. if so, check if the user has posted likes and followed back
    #4. if so, remove the user from the greyList
    #5. if not, remove the user from the greylist, unfollow and nuke it
    pass


##################### METHOD: 
#TODO
def updateAnalytics(token):
    with open('notificationLastDate.txt', 'r') as file: # epoch of last activity stored
        data = file.read().rstrip()
    epochToReach = int(data) # and converting it to integer

    notifications = open("notifications.json")
    receivedNotifications = json.load(notifications) #receivedNotifications is a dictionary
    notifications.close() #if there is a mistake, here! delete this!

    activities, hasNextPage = getPage(pageNumber=1, token=token, mode=3, userID=None)
    pageCounter = 2
    startingEpoch = activities[0]['createdAt'] #getting epoch of the most recent activity

    continueFlag = True #variable necessary to determine for how long to continue (check if the current activity has been seen already)
    listCounter = 0
    notificationCounter = 0
    while (continueFlag and hasNextPage) :
        while (listCounter < len(activities) and continueFlag) :
            activity = activities[listCounter]
            if (activity['createdAt'] <= epochToReach) :
                continueFlag = False
            else :
                if activity['user']['id'] not in receivedNotifications : #if userID not in the json, add a dictionary for that
                    receivedNotifications[activity['user']['id']] = {"username":activity['user']['name'], "likes":[], "mentions":[]}
                if activity['type'] == 'ACTIVITY_LIKE' :
                    receivedNotifications[activity['user']['id']]['likes'].append(activity['createdAt'])
                else :
                    receivedNotifications[activity['user']['id']]['mentions'].append(activity['createdAt'])
                notificationCounter += 1
                listCounter += 1
        if (continueFlag) :
            listCounter = 0
            activities, hasNextPage = getPage(pageCounter, token=token, mode=3, userID=None)
            pageCounter += 1

    with open('notificationLastDate.txt', "w") as file:
        file.write(str(startingEpoch))

    with open('notifications.json', 'w') as file:
        json.dump(receivedNotifications, file)

    print("Recorded notifications: " + str(notificationCounter))




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
                8-Follow spree from user following list;
                9-Update analytics;
                999-End.\n
            Selected Mode:"""

    mode = 0
    while mode >= 0 and mode <= 9 :
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
                followUser(token, targetUser)

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

        elif mode == 8:
            targetUser = input("Enter the vector user: ")
            print("Following user " + targetUser + "'s following list")
            followSpree(token, targetUser)

        elif mode == 9:
            updateAnalytics(token)

        elif mode == 999:
            print("thanks for your participation")

        else: 
            mode = 0 #resetting the mode since it was not intentionally ended
            print("Job completed! Or is there more to do?")




if __name__ == "__main__":
    main()