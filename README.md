TaskMaster
==========

Master your tasks

See `legacy` for an old CSV/pyshelve type thing.  The new stuff is all SQL DB with RESTful API.

API
---

* /tasks/
  * GET
    * list all closed
    * single-mode (triage, etc
    * search
* /tasks/{id}
* /tasks/{id}/similar
* /tasks/{id}/action
  * close
  * duplicate

Modes
-----

A key new concept here is the idea of "modes" - we don't want to see all our tasks all the time; we want to be able to focus and only occasionally triage, schedule etc.  Here are some steps in the lifecycle of a task:

1. Collect - into system (sometimes with tags)
   * write new (CLI, WebGUI, app)
     * upsert mode
   * import bulk (CLI opts to pre-triage)
     * txt
     * keep
     * csv
   * scan or individual gitlab/github issue
   * send email to certian box (which would then have fulltext and option to send subsequent to cancel -or- tie in with users inbox directly)
   * recycled from closed
2. Triage - set details (anything missing details)
   * anything missing certian details
   * assign contexts
   * count pomodoros
   * tags
   * important/urgent
3. Schedule / delegate (null schedule, not warm)
   * or delegate w/ rewarm for checkbckin
   * say when to wake
   * or stage/warm NOW
   * bulk re-schedule
4. Stage (past wakeup)
   * frog
   * "warm tasks"
   * execute/cycle/close/triage
5. Execute (warm=true)
   * live
6. Close (append close)
   * recycle
7. Others...
   * assign
   * follow up
   * status report

DB
--
Main:
* id
* Name
* Urgent
* Important
* poms
* wakeup
* staged/warm (T/F)
* sync URL
* depends on ID

Tags:
* TID
* type - source, context, project, goal, assignee
* value

Filters
-------
* all/None
* open (all but closed)
* triage (triage/new; some asleep, wake, warm)
* schedule (triage/new; schedule)
* stage (awake, warm)
* execute (warm)
* closed (closed)

How to
------

* Run the API: `$ TMSQLAPI_SETTINGS=sample.cfg python tmsqlapi.py`
* Run the Client: `$ ./tm2.py -a http://127.0.0.1:5000/ new`
