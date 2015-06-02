# mass_reports_for_splunk
An (ugly) script to generate a large number of sheduled PDF views in Splunk based on a template

## Introduction

**Need**: provide a dashboard to a large group of sysadmin, showing their systems only.
 
Difficulties:
-	Cannot provide 100's of accounts on the Splunk SH (operation processes not designed to do it)
-	Permissions are tricky: limitation role->index, but what about more precise search terms? (without the possibility to bypass) -> probably doable, but needs a SH lock-down and proper role modelling
-	PDF generation as alternative
 - No templates system
 - Various workaround needed (see later)
 - Limited in formating
 - No monitoring of reporting errors (or difficult…)
 
PDF Generator:
-	Limited formating control
-	page layout, font size, graph size, graph format (size of label area vs graph area, …)
-	No bookmark/hyperlink within report
Template system:
-	Developed own script
Workarounds:
-	Scheduled PDF works only if using saved searches, not inline… http://answers.splunk.com/answers/74295/empty-scheduled-pdf-reports.html#answer-98352
-	Scheduledview report format is not used, it takes only the global configuration?!
-	Refreshing (via rest endpoint) the scheduledview does not refresh/reinitialise the schedule. I have to set explicitely again via REST the schedule. 
-	Larger charts (takes more width on the page, A3 landscape). Size is hard coded (600px)
-	Top alignement in table cells (default is bottom).
-	Line feed in Multivalue cell (nicer format in the PDF): 
  '''eval Description=mvappend(Description," ",mvappend("","Advisories: ",Adv))'''
- Single Value "missuse" to show conditionally a header with multiple values (text): use delim to insert "&lt;br/&gt;" that will be honored (fortunately!) by the PDF generator (but not by the view…)
External reporting engine?
-	Any recommendation for external reporting engine? Jasper reports?
 
## Abstract
A dashboard in Splunk can be scheduled to be delivered as PDF per email to a list of email addresses.
This works well, but only for static dashboards (simple XML dashboards without Form elements), i.e. it is not possible to give parameters to the scheduler to change the queries or the destination emails.
The solution described here consists in a script that can be run on the splunk server (search head) that will:
-	Based on a csv list of parameters and templates
-	create saved searches for every pannel for every dashboard to be generated
-	create a dashboard for every parameter set
-	schedule the dashboard for delivery following date/hour and email parameters
-	force a refresh of splunk to consider the new dashboards and schedule without restarting splunk

**Work in progress:**
This script is a work in progress. It is currently heavily tailored to my vulnerability score dashboard usecase, and doesn't perform a lot of error checking (it's my first Python script ever). Given wrong parameters, it will mostly stop without complaining much...
Help, comments, bugfixes, improvements are welcome!
Note:
Because of a bug in Splunk Scheduler, the dashboards' panels must be based on savedsearches, and not inline. If the panels use inline searches, the scheduled PDF are empty (but work fine when created manually). The script must therefore create first all saved searches, then the dashboard that references these searches.

