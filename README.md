TaskMaster
==========

Master your tasks - KanBan-style RESTful API for managing tasks as cards

- RESTful API based on FastAPI and SQLModel
- Data model with Boards, Lists, Cards, and Categories
- API with some CRUD endpoints but some obvious missing
- TUI to show board of lists
- Web GUI showing lists as "papers on a desk"

Currently an alpha quality software, missing key features, see #93.

See "history" below for how to run "v2" which is currently better.



Run it
------

- `git clone https://github.com/ctengel/taskmaster.git`
- `fastapi dev --port 29325 kanapi.py`
- Open http://127.0.0.1:29325/desk/ for the "papers on a desk" web GUI
- `KANAPI_URL=http://127.0.0.1:29325/ ./kantui.py`
- `KANAPI_URL=http://127.0.0.1:29325/ ./kancli.py --help`
- `KANAPI_URL=http://127.0.0.1:29325/ flask --app tmgui run --port 29319`

### Desk web GUI

The desk (`desk/`, served by kanapi at `/desk/`) shows each list as a paper
laid side by side on a desk.  Papers can be created on the fly, dragged into a
new order, renamed, and "put away" into a drawer, optionally with a wakeup
date so they come back to the desk automatically.  A list's `board_order`
holds its place in the row; a null `board_order` means it is put away, like a
closed card's null `list_order`.

- Everything works by mouse (drag & drop papers and tasks) or keyboard: the
  TUI keys (`n`/`e`/`m`/`wasd`/`c`) plus `N` new paper, `A`/`D` move paper,
  `r` rename, `z` put away, `b` drawer, `p`/`P` print, `g` refresh.
- The search box (`/`) is an *upsert*: type to find a task on visible (or
  all) papers, and if it isn't found, Enter writes it on the current paper.
- Print one paper (its printer button), marked papers (checkboxes), or the
  whole desk via the browser's print dialog.

Notes:
- Lists that existed before the desk have no `board_order`, so they start in
  the drawer; pull out the ones you want on the desk once.
- Closing a task needs one list created with `--closed` (see below).
- Task colors come from `category_color` (e.g.
  `curl -X POST localhost:29325/categories/ -H 'Content-Type: application/json' -d '{"category_id": 1, "category_name": "Home", "category_color": "#4C8A64"}'`);
  categories without a color get a stable fallback color.

### Recommended setup

Create categories:
1. Home
2. Work
etc...

Create a few lists as follows:
1. Inbox
2. Complete
3. Doing
4. Ready/Must
5. In waiting/ bullpen
6. Active backlog
7. Someday

```
$ ./kancli.py new-list inbox
1
$ ./kancli.py new-list --closed done
2
$ ./kancli.py new-list doing
3
$ ./kancli.py new-list today
4
$ ./kancli.py new-list bullpen
5
$ ./kancli.py new-list backlog
6
$ ./kancli.py new-list someday
7
$ ./kancli.py new-list --category-id 1 --wakeup 2026-01-01 nextyear
8
```

Next, go ahead and create any sleeping lists for stuff way out in th future.

Typically we would show lists `6 5 4 3 2` in kantui etc.

### Import data

From there you can now add any existing data you want to keep.  If you have an existing v0.2 tm instance...

1. Load all data from existing instance `curl http://taskmasterv02/tasks/?mode=all > taskmaster-v0.2-tasks.json`
2. Convert to CSV via `mlr --j2c cat taskmaster-v0.2-tasks.json > taskmaster-v0.2-tasks.csv`
3. Play with it in your favorite spreadsheet editor
4. Import via newtasks stdin to appropriate lists `./kancli.py add --category-id 1 --list-id 1 < tasks.txt`

Roadmap
-------

- packaging
- ~~server side board definition~~ done: desk order/away state lives in `board_order`
- desk paradigm in TUI and Android clients

History
-------

The current (v3) KanBan based FastAPI version is the 3rd iteration.

The first (v1/legacy) was an old CSV/pyshelve type thing.  There are limited docs and it is likely to be completely removed shortly, but for now it is available under `legacy/`

The second (v2) was much more feature-rich and RESTful API and SQL based. It also has a decent CLI and WebGUI.


### v2 API


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

### v2 Modes

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

### v2 DB

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

To upgrade DB from one v2.x verision to another see `sql/`

### v2 Filters
* all/None
* open (all but closed)
* triage (triage/new; some asleep, wake, warm)
* schedule (triage/new; schedule)
* stage (awake, warm)
* execute (warm)
* closed (closed)

### v2 How to

* Run the API: `$ TMSQLAPI_SETTINGS=sample.cfg python tmsqlapi.py`
* Run the Client: `$ ./tm2.py -a http://127.0.0.1:5000/ new`

Note that there is no install needed, but client requires `inquirer`.
