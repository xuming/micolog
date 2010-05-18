#!/usr/bin/python

# Code copied from http://code.google.com/appengine/articles/remote_api.html
# with minor modifications.

import code
import getpass
import os
import sys

DIR_PATH = "/root/dev/google_appengine"
sys.path.append(os.path.join(os.path.dirname(__file__), '..\\'))

SCRIPT_DIR = os.path.join(DIR_PATH, 'google', 'appengine', 'tools')

EXTRA_PATHS = [
  DIR_PATH,
  os.path.join(DIR_PATH, 'lib', 'antlr3'),
  os.path.join(DIR_PATH, 'lib', 'django'),
  os.path.join(DIR_PATH, 'lib', 'webob'),
  os.path.join(DIR_PATH, 'lib', 'yaml', 'lib'),
]
sys.path = EXTRA_PATHS + sys.path
from google.appengine.ext.remote_api import remote_api_stub
from google.appengine.ext import db

def auth_func():
  return raw_input('Username:'), getpass.getpass('Password:')

if len(sys.argv) < 2:
  print "Usage: %s app_id [host]" % (sys.argv[0],)
app_id = sys.argv[1]
if len(sys.argv) > 2:
  host = sys.argv[2]
else:
  host = '%s.appspot.com' % app_id
os.environ['APPLICATION_ID']=app_id

from google.appengine.api import apiproxy_stub_map
from google.appengine.api import urlfetch_stub
apiproxy_stub_map.apiproxy = apiproxy_stub_map.APIProxyStubMap()
apiproxy_stub_map.apiproxy.RegisterStub('urlfetch',urlfetch_stub.URLFetchServiceStub())

from google.appengine.api import datastore_file_stub
from google.appengine.api import mail_stub
#from google3.apphosting.api import user_service_stub

#apiproxy_stub_map.apiproxy.RegisterStub('user',user_service_stub.UserServiceStub())
apiproxy_stub_map.apiproxy.RegisterStub('datastore_v3',  datastore_file_stub.DatastoreFileStub(app_id, '/tmp/dev_appserver.datastore', '/dev/null'))
apiproxy_stub_map.apiproxy.RegisterStub('mail',mail_stub.MailServiceStub()) 


#remote_api_stub.ConfigureRemoteDatastore(app_id, '/remote_api', auth_func, host)
from model import *
code.interact('App Engine interactive console for %s' % (app_id,), None, locals())
