import json
client = open("client.json")
variables = json.load(client)

client_name = variables["client_name"]
client_redirectURL = variables["client_redirectURL"]
client_ID = int(variables["client_ID"])
client_Secret = variables["client_Secret"]


import time
import webbrowser

webbrowser.open_new_tab("https://anilist.co/api/v2/oauth/authorize?client_id=" + str(client_ID) + "&redirect_uri=" + client_redirectURL + "&response_type=code")
time.sleep(8)
#import os
#os.system("taskkill /f /im chrome.exe")
#time.sleep(3)
import ThunderstormTheRevenge as storm
storm.main()

