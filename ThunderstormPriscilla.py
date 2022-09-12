# API client
client_name = "xxx"
client_redirectURL = "xxx"
client_ID = 000
client_Secret = "xxx"



import time
import webbrowser

webbrowser.open_new_tab("https://anilist.co/api/v2/oauth/authorize?client_id=" + str(client_ID) + "&redirect_uri=" + client_redirectURL + "&response_type=code")
time.sleep(3)
#import os
#os.system("taskkill /f /im chrome.exe")
time.sleep(3)
exec(open("ThunderstormTheRevenge.py").read())



