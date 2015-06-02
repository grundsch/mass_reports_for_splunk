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

**Solution:**
- Template system:	Developed own script

Workarounds:
-	Scheduled PDF works only if using saved searches, not inline… http://answers.splunk.com/answers/74295/empty-scheduled-pdf-reports.html#answer-98352
-	Scheduledview report format is not used, it takes only the global configuration?!
-	Refreshing (via rest endpoint) the scheduledview does not refresh/reinitialise the schedule. I have to set explicitely again via REST the schedule. 
-	Larger charts (takes more width on the page, A3 landscape). Size is hard coded (600px)
-	Top alignement in table cells (default is bottom).
-	Line feed in Multivalue cell (nicer format in the PDF): 
  `eval Description=mvappend(Description," ",mvappend("","Advisories: ",Adv))`
- Single Value "missuse" to show conditionally a header with multiple values (text): use delim to insert `"&lt;br/&gt;"` that will be honored (fortunately!) by the PDF generator (but not by the view…)
External reporting engine?
-	Any recommendation for external reporting engine? Jasper reports?

See https://github.com/grundsch/mass_reports_for_splunk/wiki for a detailed description of the script.
