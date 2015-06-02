#!/opt/splunk/bin/python


# (c) Stephane Grundschober, 8.1.2015
# some parts (logger, session, output, refresh) copied from Michael Uschmann's Add-on Debug Refresh app


import ConfigParser
import csv
import logging,  logging.handlers
import sys
import os
import splunk
import splunk.rest as rest
import splunk.auth
import splunk.Intersplunk


# setup logger
myScript = os.path.basename(__file__)
logger = logging.getLogger() # Root-level logger
#logger.setLevel(logging.INFO)
logger.setLevel(logging.DEBUG)
SPLUNK_HOME = os.environ['SPLUNK_HOME']
LOGGING_DEFAULT_CONFIG_FILE = os.path.join(SPLUNK_HOME, 'etc', 'log.cfg')
LOGGING_LOCAL_CONFIG_FILE = os.path.join(SPLUNK_HOME, 'etc', 'log-local.cfg')
LOGGING_STANZA_NAME = 'python'
LOGGING_FILE_NAME = "%s.log" % myScript
BASE_LOG_PATH = os.path.join('var', 'log', 'splunk')
LOGGING_FORMAT = "%(asctime)s %(levelname)-s\t%(module)s:%(lineno)d - %(message)s"
splunk_log_handler = logging.handlers.RotatingFileHandler(os.path.join(SPLUNK_HOME, BASE_LOG_PATH, LOGGING_FILE_NAME), mode='a')
splunk_log_handler.setFormatter(logging.Formatter(LOGGING_FORMAT))
logger.addHandler(splunk_log_handler)
splunk.setupSplunkLogger(logger, LOGGING_DEFAULT_CONFIG_FILE, LOGGING_LOCAL_CONFIG_FILE, LOGGING_STANZA_NAME)


### splunk integration ###


# getting the sessionKey, owner, namespace
results,dummyresults,settings = splunk.Intersplunk.getOrganizedResults()
results = [] # we don't care about incoming results
logger.debug("Setting: %s " % settings )
sessionKey = settings.get("sessionKey", None)
logger.debug("using sessionKey: %s " % sessionKey )
owner      = settings.get("owner", None)
logger.debug("using owner: %s " % owner )
namespace  = settings.get("namespace", None)
logger.debug("using namespace: %s " % namespace )


# change working dir to app
appdir =  os.path.join(SPLUNK_HOME, 'etc', 'apps', namespace) 
logger.debug("dirname of app: %s", appdir)
os.chdir(appdir)


# variables for outputting results to splunk
mylist = []


### get config first ###


if len(sys.argv) > 1:
  options_filename = "./local/" + sys.argv[1]
else:
  options_filename = "./local/dashboard_generator.conf"


mylist.append({"text": "option file: %s " % (options_filename)})


if not(os.path.isfile(options_filename)):
  mylist.append({"text": "option file: %s not found!" % (options_filename)})
  splunk.Intersplunk.outputResults(mylist)
  exit(0)


#getting all options
logger.info("Loading configuration from %s", options_filename)
gen_options_parser = ConfigParser.SafeConfigParser()
gen_options_parser.optionxform = str
gen_options_parser.read(options_filename)
gen_opt = dict(gen_options_parser.items('dashboard_generator'))


# typical config file:
# [dashboard_generator]
# report_list_csv = ./lookup/dashboard_list.csv
# file_to_edit = ./local/savedsearches.conf
# backup = ./local/savedsearches.bak
# prefix = dashboard_
# dashboard_path = ./local/data/ui/views/
# dashboard_template = dashboard_template.xml
# savedsearches_template = ./local/template.conf


### done config


### starting modifiying files and dashboards ###


# csv file listing all the reports and parameters
logger.info("Getting report list from %(report_list_csv)s", gen_opt)
report_list_csv = open(gen_opt["report_list_csv"], 'rb')
report_list = csv.DictReader(report_list_csv)


mylist.append({"text": "report list file: %(report_list_csv)s " % (gen_opt)})


# read the present savedsearches.conf file to edit
logger.info("Reading %(file_to_edit)s", gen_opt)
parser = ConfigParser.ConfigParser()
parser.optionxform = str
parser.read(gen_opt["file_to_edit"])


# but make a backup first
logger.info("write backup to %(backup)s", gen_opt)
backup = open(gen_opt["backup"], 'wb')
parser.write(backup)
backup.close()


# search existing sections for searches to delete
logger.info("Deleting sections containing '%(prefix)s'", gen_opt)
sections=parser.sections()
for section in sections:
        if gen_opt["prefix"] in section:
                logger.debug("deleting old section %s",section)
                parser.remove_section(section)
                # extract the shortname from the section, i.e. the last element after _
                # and delete the corresponding old xml dashboard file
                shortname = section.rpartition("_")[2]
                try:
                        logger.debug("trying to remove old file %s%s%s.xml", gen_opt["dashboard_path"], gen_opt["prefix"], shortname)
                        os.remove("%s%s%s.xml" % (gen_opt["dashboard_path"], gen_opt["prefix"], shortname) )
                except OSError:
                        pass
                else:
                        logger.debug("old dashboard %s%s%s.xml deleted!" % (gen_opt["dashboard_path"], gen_opt["prefix"], shortname))
                        mylist.append({"text": "deleting file: %s%s%s.xml " % (gen_opt["dashboard_path"], gen_opt["prefix"], shortname)})


# recreating everything


logger.info("opening saved searches template %(savedsearches_template)s", gen_opt)
template = ConfigParser.SafeConfigParser()
template.optionxform = str
template.read(gen_opt["savedsearches_template"])


for report in report_list:


        ## generating a new dashboard instance
        logger.info("working on %(shortname)s", report)
        logger.debug("opening dashboard template '%s%s'", gen_opt["dashboard_path"], gen_opt["dashboard_template"])
        t_dashboard = open(gen_opt["dashboard_path"] + gen_opt["dashboard_template"])


        logger.debug("creating new dashboard %s%s%s.xml", gen_opt["dashboard_path"], gen_opt["prefix"], report["shortname"])
        new_dashboard = open("%s%s%s.xml" % ( gen_opt["dashboard_path"], gen_opt["prefix"], report["shortname"]), "wb")
        for line in t_dashboard:
                new_dashboard.write( line % (report) )
        t_dashboard.close()
        new_dashboard.close()
        myoutput = {"text": "new dashboard: %s%s%s.xml " % ( gen_opt["dashboard_path"], gen_opt["prefix"], report["shortname"])}
        myoutput.update(report)
        mylist.append(myoutput)


        ## generating new saved searches instances
        # getting all sections from template
        template_sections = template.sections()
        for t_section in template_sections:
                section_name = t_section % (report)
                #getting all options of the template section, substitutting dictionary values from report
                template_options = template.items(t_section, False, report)
                
                #adding the section to the orginal file
                parser.add_section(section_name)
                #adding individual options, not considering the options generated by the default values used when reading
                for t_option in template_options:
                        if t_option[0] in report_list.fieldnames:
                                continue
                        parser.set(section_name, t_option[0], t_option[1])
                        logger.debug("section: %s \toption: %s \tvalue: %s", section_name, t_option[0], t_option[1])


# writing back savedseaches.conf
output = open(gen_opt["file_to_edit"], 'wb')
parser.write(output)
output.close()


### refreshing everything
reloadLinks = ["/servicesNS/admin/search/admin/savedsearch/_reload", "/servicesNS/admin/search/admin/views/_reload", "/servicesNS/admin/search/admin/scheduledviews/_reload"]


for target in reloadLinks:
    endpointresult={}
    logger.info("reloading the %s endpoints now ..." % target)
    response, content = rest.simpleRequest(target, sessionKey=sessionKey, method='POST')
    endpointresult["endpoint"] = target
    endpointresult["status"] = response['status']
    logger.debug("endpointresult: %s",  endpointresult)


# Updating the cron schedule to force the scheduler to refresh
# first need to reopen the csv list, as the DictReader consumed the entries as we were reading them
logger.info("starting scheduled views update")
report_list_csv = open(gen_opt["report_list_csv"], 'rb')
report_list = csv.DictReader(report_list_csv)


# hit the REST endpoint in the current app with the user nobody (reusing the auhtorisation of the currently logged in user)
# to force a reschedule of the PDF
for report in report_list:
        logger.info("updating sheduled view %(shortname)s", report)
        postArgs = { "action.email.to": report["email"], "cron_schedule": report["cron"], "is_scheduled": 1}
        logger.debug(postArgs)
        response, content = rest.simpleRequest("/servicesNS/nobody/%s/scheduled/views/%s%s" % (namespace, gen_opt["prefix"], report["shortname"]),  sessionKey=sessionKey, postargs=postArgs, method='POST', raiseAllErrors=True)
        endpointresult["endpoint"] = "/servicesNS/nobody/%s/scheduled/views/%s%s" % (namespace, gen_opt["prefix"], report["shortname"])
        endpointresult["status"] = response['status']
        logger.debug("endpointresult: %s", endpointresult)


# spit out debug info as events back to splunk
splunk.Intersplunk.outputResults(mylist)

