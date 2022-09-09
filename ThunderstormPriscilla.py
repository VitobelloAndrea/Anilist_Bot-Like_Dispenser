# API client
client_name = "xxx"
client_redirectURL = "xxx"
client_ID = 000
client_Secret = "xxx"



import time
import webbrowser
webbrowser.open_new_tab("https://anilist.co/api/v2/oauth/authorize?client_id=" + str(client_ID) + "&redirect_uri=" + client_redirectURL + "&response_type=code")

from datetime import datetime
ts = str(datetime.now().replace(microsecond=0))

def date_to_webkit(date_string):
    epoch_start = datetime(1601, 1, 1)
    date_ = datetime.strptime(date_string, '%Y-%m-%d %H:%M:%S')
    diff = date_ - epoch_start
    seconds_in_day = 60 * 60 * 24
    return '{:<017d}'.format(
        diff.days * seconds_in_day + diff.seconds + diff.microseconds)

print(ts)
webkit_ts = date_to_webkit(ts)
print(webkit_ts)


time.sleep(3)
#import os
#os.system("taskkill /f /im chrome.exe")
time.sleep(3)


exec(open("ThunderstormTheRevenge.py").read())