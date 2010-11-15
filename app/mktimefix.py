from time import *
from calendar import timegm

# fix for mktime bug
# https://garage.maemo.org/tracker/index.php?func=detail&aid=4453&group_id=854&atid=3201
mktime = lambda time_tuple: calendar.timegm(time_tuple) + timezone

