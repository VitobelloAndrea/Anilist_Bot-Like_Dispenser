# Anilist_Bot-Like_Dispenser

# TODO
- ***DONE*** deal with failed requests (pages: send the same request again; like: wait for a minute, then restart where you stopped)
- ***DONE*** add a check on the number of requests remaining for the current minute (useless as of now, but the API might change over time)
- ***DONE*** add a mode for the global list
- ***DONE*** add a mode to target a specific user
- add a check on "hasNextPage" because i think right now the algorithm would loop and make a mess
- add a GUI (possibly done with the "single exe" update?)
- get everything inside a single exe because it comes a lot easier, and set it up so that it asks for the credentials at the start and that's it, the app is tuned
- ***DONE*** manage exception of users that cannot receive likes
- add a mode to target many users through a single command
- add commands concatenations
- ***DONE*** nuke a user
- ***DONE*** add a blacklist to check against when posting a like, and a whitelist command
