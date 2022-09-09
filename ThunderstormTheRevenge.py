# API client
client_name = "xxx"
client_redirectURL = "xxx"
client_ID = 000
client_Secret = "xxx"


##################### METHOD: GETTING A PAGE (actually a post message)
def getPage(pageNumber, token) :
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

    import json
    activities = pageResponse.json()['data']['Page']['activities']

    #print(type(activities[0]))
    #print(activities[0])

    return activities



############### METHOD: MAKE THE ACTIVITY POST REQUEST
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
    if response.status_code == 200:
        print("response : ", response)
    else :
        print(response.text)

    #just to check: webbrowser.open_new_tab("https://anilist.co/activity/" + str(activityNumber))



import sqlite3
import webbrowser
from wsgiref import headers
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




######################### GETTING THE STUPID ACCESS TOKEN

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




############### TIME TO ITERATE! 
import time

pageCounter = 1
likeCounter = 0 #count how many likes; maximum of 30 before 1minute time out
listCounter = 0 #count the activity of the list that was reached (0 up to 49)
continueFlag = True

with open('lastDate.txt', 'r') as file: # extracting the activity epoch up to which the algorithm has run
    data = file.read().rstrip()
epochToReach = int(data) # and converting it to integer

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
                postLike(int(activity.get('id')), token)
                likeCounter += 1
            listCounter += 1
        else :
            time.sleep(60)
            likeCounter = 0
    if (continueFlag) : 
        listCounter = 0
        activities = getPage(pageCounter, token)
        pageCounter += 1

with open('lastDate.txt', "w") as file:
    file.write(str(startingEpoch))

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