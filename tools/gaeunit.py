#!/usr/bin/env python
'''
GAEUnit: Google App Engine Unit Test Framework

Usage:

1. Put gaeunit.py into your application directory.  Modify 'app.yaml' by
   adding the following mapping below the 'handlers:' section:

   - url: /test.*
     script: gaeunit.py

2. Write your own test cases by extending unittest.TestCase.

3. Launch the development web server.  To run all tests, point your browser to:

   http://localhost:8080/test     (Modify the port if necessary.)
   
   For plain text output add '?format=plain' to the above URL.
   See README.TXT for information on how to run specific tests.

4. The results are displayed as the tests are run.

Visit http://code.google.com/p/gaeunit for more information and updates.

------------------------------------------------------------------------------
Copyright (c) 2008-2009, George Lei and Steven R. Farley.  All rights reserved.

Distributed under the following BSD license:

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

* Redistributions of source code must retain the above copyright notice,
  this list of conditions and the following disclaimer.

* Redistributions in binary form must reproduce the above copyright notice,
  this list of conditions and the following disclaimer in the documentation
  and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
------------------------------------------------------------------------------
'''

__author__ = "George Lei and Steven R. Farley"
__email__ = "George.Z.Lei@Gmail.com"
__version__ = "#Revision: 1.2.8 $"[11:-2]
__copyright__= "Copyright (c) 2008-2009, George Lei and Steven R. Farley"
__license__ = "BSD"
__url__ = "http://code.google.com/p/gaeunit"

import sys
import os
import unittest
import time
import logging
import cgi
import django.utils.simplejson

from google.appengine.ext import webapp
from google.appengine.api import apiproxy_stub_map  
from google.appengine.api import datastore_file_stub
from google.appengine.ext.webapp.util import run_wsgi_app

_LOCAL_TEST_DIR = 'test'  # location of files
_WEB_TEST_DIR = '/test'   # how you want to refer to tests on your web server

# or:
# _WEB_TEST_DIR = '/u/test'
# then in app.yaml:
#   - url: /u/test.*
#     script: gaeunit.py


##############################################################################
# Main request handler
##############################################################################


class MainTestPageHandler(webapp.RequestHandler):
    def get(self):
        unknown_args = [arg for arg in self.request.arguments()
                        if arg not in ("format", "package", "name")]
        if len(unknown_args) > 0:
            errors = []
            for arg in unknown_args:
                errors.append(_log_error("The request parameter '%s' is not valid." % arg))
            self.error(404)
            self.response.out.write(" ".join(errors))
            return

        format = self.request.get("format", "html")
        if format == "html":
            self._render_html()
        elif format == "plain":
            self._render_plain()
        else:
            error = _log_error("The format '%s' is not valid." % cgi.escape(format))
            self.error(404)
            self.response.out.write(error)
            
    def _render_html(self):
        suite, error = _create_suite(self.request)
        if not error:
            self.response.out.write(_MAIN_PAGE_CONTENT % (_test_suite_to_json(suite), _WEB_TEST_DIR, __version__))
        else:
            self.error(404)
            self.response.out.write(error)
        
    def _render_plain(self):
        self.response.headers["Content-Type"] = "text/plain"
        runner = unittest.TextTestRunner(self.response.out)
        suite, error = _create_suite(self.request)
        if not error:
            self.response.out.write("====================\n" \
                                    "GAEUnit Test Results\n" \
                                    "====================\n\n")
            _run_test_suite(runner, suite)
        else:
            self.error(404)
            self.response.out.write(error)


##############################################################################
# JSON test classes
##############################################################################


class JsonTestResult(unittest.TestResult):
    def __init__(self):
        unittest.TestResult.__init__(self)
        self.testNumber = 0

    def render_to(self, stream):
        result = {
            'runs': self.testsRun,
            'total': self.testNumber,
            'errors': self._list(self.errors),
            'failures': self._list(self.failures),
            }

        stream.write(django.utils.simplejson.dumps(result).replace('},', '},\n'))

    def _list(self, list):
        dict = []
        for test, err in list:
            d = { 
              'desc': test.shortDescription() or str(test), 
              'detail': err,
            }
            dict.append(d)
        return dict


class JsonTestRunner:
    def run(self, test):
        self.result = JsonTestResult()
        self.result.testNumber = test.countTestCases()
        startTime = time.time()
        test(self.result)
        stopTime = time.time()
        timeTaken = stopTime - startTime
        return self.result


class JsonTestRunHandler(webapp.RequestHandler):
    def get(self):    
        self.response.headers["Content-Type"] = "text/javascript"
        test_name = self.request.get("name")
        _load_default_test_modules()
        suite = unittest.defaultTestLoader.loadTestsFromName(test_name)
        runner = JsonTestRunner()
        _run_test_suite(runner, suite)
        runner.result.render_to(self.response.out)


# This is not used by the HTML page, but it may be useful for other client test runners.
class JsonTestListHandler(webapp.RequestHandler):
    def get(self):
        self.response.headers["Content-Type"] = "text/javascript"
        suite, error = _create_suite(self.request)
        if not error:
            self.response.out.write(_test_suite_to_json(suite))
        else:
            self.error(404)
            self.response.out.write(error)


##############################################################################
# Module helper functions
##############################################################################


def _create_suite(request):
    package_name = request.get("package")
    test_name = request.get("name")

    loader = unittest.defaultTestLoader
    suite = unittest.TestSuite()

    error = None

    try:
        if not package_name and not test_name:
                modules = _load_default_test_modules()
                for module in modules:
                    suite.addTest(loader.loadTestsFromModule(module))
        elif test_name:
                _load_default_test_modules()
                suite.addTest(loader.loadTestsFromName(test_name))
        elif package_name:
                package = reload(__import__(package_name))
                module_names = package.__all__
                for module_name in module_names:
                    suite.addTest(loader.loadTestsFromName('%s.%s' % (package_name, module_name)))
    
        if suite.countTestCases() == 0:
            raise Exception("'%s' is not found or does not contain any tests." %  \
                            (test_name or package_name or 'local directory: \"%s\"' % _LOCAL_TEST_DIR))
    except Exception, e:
        error = str(e)
        _log_error(error)

    return (suite, error)


def _load_default_test_modules():
    if not _LOCAL_TEST_DIR in sys.path:
        sys.path.append(_LOCAL_TEST_DIR)
    module_names = [mf[0:-3] for mf in os.listdir(_LOCAL_TEST_DIR) if mf.endswith(".py")]
    return [reload(__import__(name)) for name in module_names]


def _get_tests_from_suite(suite, tests):
    for test in suite:
        if isinstance(test, unittest.TestSuite):
            _get_tests_from_suite(test, tests)
        else:
            tests.append(test)


def _test_suite_to_json(suite):
    tests = []
    _get_tests_from_suite(suite, tests)
    test_tuples = [(type(test).__module__, type(test).__name__, test._testMethodName) \
                   for test in tests]
    test_dict = {}
    for test_tuple in test_tuples:
        module_name, class_name, method_name = test_tuple
        if module_name not in test_dict:
            mod_dict = {}
            method_list = []
            method_list.append(method_name)
            mod_dict[class_name] = method_list
            test_dict[module_name] = mod_dict
        else:
            mod_dict = test_dict[module_name]
            if class_name not in mod_dict:
                method_list = []
                method_list.append(method_name)
                mod_dict[class_name] = method_list
            else:
                method_list = mod_dict[class_name]
                method_list.append(method_name)
                
    return django.utils.simplejson.dumps(test_dict)


def _run_test_suite(runner, suite):
    """Run the test suite.

    Preserve the current development apiproxy, create a new apiproxy and
    replace the datastore with a temporary one that will be used for this
    test suite, run the test suite, and restore the development apiproxy.
    This isolates the test datastore from the development datastore.

    """        
    original_apiproxy = apiproxy_stub_map.apiproxy
    try:
       apiproxy_stub_map.apiproxy = apiproxy_stub_map.APIProxyStubMap() 
       temp_stub = datastore_file_stub.DatastoreFileStub('GAEUnitDataStore', None, None, trusted=True)  
       apiproxy_stub_map.apiproxy.RegisterStub('datastore', temp_stub)
       # Allow the other services to be used as-is for tests.
       for name in ['user', 'urlfetch', 'mail', 'memcache', 'images']: 
           apiproxy_stub_map.apiproxy.RegisterStub(name, original_apiproxy.GetStub(name))
       runner.run(suite)
    finally:
       apiproxy_stub_map.apiproxy = original_apiproxy


def _log_error(s):
   logging.warn(s)
   return s

           
################################################
# Browser HTML, CSS, and Javascript
################################################


# This string uses Python string formatting, so be sure to escape percents as %%.
_MAIN_PAGE_CONTENT = """
<html>
<head>
    <style>
        body {font-family:arial,sans-serif; text-align:center}
        #title {font-family:"Times New Roman","Times Roman",TimesNR,times,serif; font-size:28px; font-weight:bold; text-align:center}
        #version {font-size:87%%; text-align:center;}
        #weblink {font-style:italic; text-align:center; padding-top:7px; padding-bottom:7px}
        #results {padding-top:20px; margin:0pt auto; text-align:center; font-weight:bold}
        #testindicator {width:750px; height:16px; border-style:solid; border-width:2px 1px 1px 2px; background-color:#f8f8f8;}
        #footerarea {text-align:center; font-size:83%%; padding-top:25px}
        #errorarea {padding-top:25px}
        .error {border-color: #c3d9ff; border-style: solid; border-width: 2px 1px 2px 1px; width:750px; padding:1px; margin:0pt auto; text-align:left}
        .errtitle {background-color:#c3d9ff; font-weight:bold}
    </style>
    <script language="javascript" type="text/javascript">
        var testsToRun = %s;
        var totalRuns = 0;
        var totalErrors = 0;
        var totalFailures = 0;

        function newXmlHttp() {
          try { return new XMLHttpRequest(); } catch(e) {}
          try { return new ActiveXObject("Msxml2.XMLHTTP"); } catch (e) {}
          try { return new ActiveXObject("Microsoft.XMLHTTP"); } catch (e) {}
          alert("XMLHttpRequest not supported");
          return null;
        }
        
        function requestTestRun(moduleName, className, methodName) {
            var methodSuffix = "";
            if (methodName) {
                methodSuffix = "." + methodName;
            }
            var xmlHttp = newXmlHttp();
            xmlHttp.open("GET", "%s/run?name=" + moduleName + "." + className + methodSuffix, true);
            xmlHttp.onreadystatechange = function() {
                if (xmlHttp.readyState != 4) {
                    return;
                }
                if (xmlHttp.status == 200) {
                    var result = eval("(" + xmlHttp.responseText + ")");
                    totalRuns += parseInt(result.runs);
                    totalErrors += result.errors.length;
                    totalFailures += result.failures.length;
                    document.getElementById("testran").innerHTML = totalRuns;
                    document.getElementById("testerror").innerHTML = totalErrors;
                    document.getElementById("testfailure").innerHTML = totalFailures;
                    if (totalErrors == 0 && totalFailures == 0) {
                        testSucceed();
                    } else {
                        testFailed();
                    }
                    var errors = result.errors;
                    var failures = result.failures;
                    var details = "";
                    for(var i=0; i<errors.length; i++) {
                        details += '<p><div class="error"><div class="errtitle">ERROR ' +
                                   errors[i].desc +
                                   '</div><div class="errdetail"><pre>'+errors[i].detail +
                                   '</pre></div></div></p>';
                    }
                    for(var i=0; i<failures.length; i++) {
                        details += '<p><div class="error"><div class="errtitle">FAILURE ' +
                                    failures[i].desc +
                                    '</div><div class="errdetail"><pre>' +
                                    failures[i].detail +
                                    '</pre></div></div></p>';
                    }
                    var errorArea = document.getElementById("errorarea");
                    errorArea.innerHTML += details;
                } else {
                    document.getElementById("errorarea").innerHTML = xmlHttp.responseText;
                    testFailed();
                }
            };
            xmlHttp.send(null);            
        }

        function testFailed() {
            document.getElementById("testindicator").style.backgroundColor="red";
        }
        
        function testSucceed() {
            document.getElementById("testindicator").style.backgroundColor="green";
        }
        
        function runTests() {
            // Run each test asynchronously (concurrently).
            var totalTests = 0;
            for (var moduleName in testsToRun) {
                var classes = testsToRun[moduleName];
                for (var className in classes) {
                    // TODO: Optimize for the case where tests are run by class so we don't
                    //       have to always execute each method separately.  This should be
                    //       possible when we have a UI that allows the user to select tests
                    //       by module, class, and method.
                    //requestTestRun(moduleName, className);
                    methods = classes[className];
                    for (var i = 0; i < methods.length; i++) {
                        totalTests += 1;
                        var methodName = methods[i];
                        requestTestRun(moduleName, className, methodName);
                    }
                }
            }
            document.getElementById("testtotal").innerHTML = totalTests;
        }

    </script>
    <title>GAEUnit: Google App Engine Unit Test Framework</title>
</head>
<body onload="runTests()">
    <div id="headerarea">
        <div id="title">GAEUnit: Google App Engine Unit Test Framework</div>
        <div id="version">Version %s</div>
    </div>
    <div id="resultarea">
        <table id="results"><tbody>
            <tr><td colspan="3"><div id="testindicator"> </div></td</tr>
            <tr>
                <td>Runs: <span id="testran">0</span>/<span id="testtotal">0</span></td>
                <td>Errors: <span id="testerror">0</span></td>
                <td>Failures: <span id="testfailure">0</span></td>
            </tr>
        </tbody></table>
    </div>
    <div id="errorarea"></div>
    <div id="footerarea">
        <div id="weblink">
        <p>
            Please visit the <a href="http://code.google.com/p/gaeunit">project home page</a>
            for the latest version or to report problems.
        </p>
        <p>
            Copyright 2008-2009 <a href="mailto:George.Z.Lei@Gmail.com">George Lei</a>
            and <a href="mailto:srfarley@gmail.com>Steven R. Farley</a>
        </p>
        </div>
    </div>
</body>
</html>
"""


##############################################################################
# Script setup and execution
##############################################################################


application = webapp.WSGIApplication([('%s'      % _WEB_TEST_DIR, MainTestPageHandler),
                                      ('%s/run'  % _WEB_TEST_DIR, JsonTestRunHandler),
                                      ('%s/list' % _WEB_TEST_DIR, JsonTestListHandler)],
                                      debug=True)

def main():
    run_wsgi_app(application)                                    

if __name__ == '__main__':
    main()
