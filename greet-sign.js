/**
 * Seconds to allow member to walk from front door to warehouse door,
 * before timing out the greeting, in seconds
 */
const HALL_WALK_TIME_SEC = 40;

/**
 * How often to retrieve recent DoorFlow events, in seconds
 */
const PROCESS_EVENT_TIME_SEC = 2;

/**
 * How often to update the display, in seconds
 */
const DISPLAY_GREETING__TIME_SEC = 2;

/**
 * Whether debug messages should be displayed
 */
const DEBUG = true;

/**
 * Application that displays a message on the marquis
 */
//const DISPLAY_APP = "/home/pi/cheerled/cheer-text.py";
const DISPLAY_APP = "/bin/echo";

//
// Internal (non-npm-installed) modules
//
const fs = require("fs");
const child_process = require("child_process");

// External (npm-installed) modules
const fetch = require("node-fetch");

/**
 * The security credentials are read from `private.json`. The format of this
 * file is:
 *
 * {
 *   "nexudus" :
 *   {
 *     "username" : "<nexudus_username>"
 *     "password" : "<nexudus_password>"
 *   },
 *   "doorflow" :
 *   {
 *     "username" : "<doorflow_username>",
 *     "password" : "<doorflow_password>"
 *   }
 * }
 */
let             { nexudus, doorflow } = JSON.parse(fs.readFileSync("./private.json"));

let             idle = false;
let             lastEventTimestamp = (new Date()).getTime();
let             lastMessage = null;
let             nexudusBearer;

let             pendingEvents = {};
let             displayQueue = [];
let             idleQueue = [];
const           PACMAN = Symbol("pacman");
const           idleMessages =
      [
        { message : "Welcome to",              args : [ "-a", "scroll_up" ] },
        { message : "Lowell Makes",            args : [ "-a", "scroll_down" ] },
        { message : "Welcome to Lowell Makes", args : [ ] },
        { message : "Welcome to Lowell Makes", args : [ ] },
        { message : " ",                       args : [ "-a", "pacman" ] },
        { message : " ",                       args : [ "-a", "pacman" ] },
        { message : "Welcome to Lowell Makes", args : [ ] },
        { message : "Welcome to Lowell Makes", args : [ ] },
        { message : " ",                       args : [ ] },
        { message : " ",                       args : [ ] }
      ];


/**
 * Return the current time, in hours, minutes, and seconds, formatted for log
 * messages
 */
function timeNow()
{
  let             now = new Date();

  return [
    ("00" + now.getHours()).substr(-2),
    ("00" + now.getMinutes()).substr(-2),
    ("00" + now.getSeconds()).substr(-2)
  ].join(":");
      
}

/**
 * Display a debug message, if debugging is enabled.
 *
 * @param {Any*}
 *   This variable argument list may contain any arguments that may be passed
 *   to `console.log`.
 */
function debug()
{
  if (DEBUG)
  {
    console.log(timeNow(), ...arguments);
  }
}


/**
 * Retrieve the recent events from DoorFlow
 *
 * @return {Array<Object>}
 *   Array of the most recent event objects.
 */
async function getDoorFlowEvents()
{
  let             url;
  let             auth;
  let             res;
  let             json;
  let             params;
  let             stage;

  try
  {
    stage = "get doorflow events";

    url = "https://api.doorflow.com/api/3/events?n=10";
    res = await fetch(
      url,
      {
        method  : "GET",
        headers :
        {
          Authorization  : ("Basic " +
                            Buffer
                              .from(doorflow.username + ":" + doorflow.password)
                              .toString('base64')),
          accept         : "application/json",
          "Content-Type" : "application/json"
        }
      });

    return res.json();
  }
  catch(e)
  {
    console.error(`error at stage ${stage}: ${e}`);
    return [];
  }
}

/**
 * Given a member's legal name, find out their preferred name, aka salutation.
 *
 * @param {Sring} coworker
 *   The legal name of the member
 *
 * @param {String} credentialsNumber
 *   The DoorFlow-identified key fob number
 *
 * @return {String}
 *   The preferred name of the member if available; otherwise, the legal name
 */
async function getSalutation(coworker, credentialsNumber)
{
  let             url;
  let             res;
  let             json;
  let             params;
  let             stage;
  let             lastName;
  const           CLIENT_ID = "be294b9c-2cba-4482-bd43-6d05c461521c"; // a random UUID

  try
  {
    //
    // Authenticate
    //

    // We only need to authenticate if not previously done
    if (! nexudusBearer)
    {
      stage = "authenticate";

      params = new URLSearchParams();
      params.append("grant_type", "password");
      params.append("username", nexudus.username);
      params.append("password", nexudus.password);
      params.append("client_id", CLIENT_ID);

      url = "https://spaces.nexudus.com/api/token";
      res = await fetch(
        url,
        {
          method  : "POST",
          body    : params,
          headers :
          {
            accept         : "application/json",
            "Content-Type" : "application/x-www-form-urlencoded"
          }
        });

      json = await res.json();

      // Save bearer token
      nexudusBearer = "Bearer " + json.access_token;
    }

    //
    // Search Coworkers
    //
    // We need to match either the KeyFobNumber or the AccessPincode.
    // Searches on those don't work, but the full name of the member
    // isn't necessarily unique because registrations are self-done
    // for sign-ups for tours, and then redone (not reused) when
    // signing up for membership. So instead we'll search just on the
    // member's last name, and then filter out the one with the
    // matching keyFobNumber or AccessPincode.
    stage = "search coworkers";

    // Get just the last name of the coworker
    lastName = coworker.trim().split(" ");
    lastName = lastName[lastName.length - 1];

    debug("Searching for", lastName);
    params = new URLSearchParams();
    params.append("page", "1");
    params.append("size", "20");
    params.append("Coworker_FullName", lastName);

    url = "https://spaces.nexudus.com/api/spaces/coworkers?" + params;
    res = await fetch(
      url,
      {
        method: "GET",
        headers:
        {
          authorization : nexudusBearer
        }
      });

    json = await res.json();

    // Match the one with the given keyFobId
    json = json.Records.filter(
      (rec) =>
      {
        debug(
          "filter looking for " + JSON.stringify(credentialsNumber) +
            ", found: rec.KeyFobNumber=" + JSON.stringify(rec.KeyFobNumber) +
            ", rec.AccessPincode=" + JSON.stringify(rec.AccessPincode));
        return [ rec.KeyFobNumber, rec.AccessPincode ].includes(credentialsNumber);
      });

    // If key fob or access pin were not found, we couldn't find the
    // member record that matches. Therefore, we can't find a
    // preferred name, so we'll use the full name.
    if (json.length === 0)
    {
      return coworker;
    }

    // Use the preferred name, aka salutation
    return json[0].Salutation;
  }
  catch(e)
  {
    console.error(`error at stage ${stage} searching for ${coworker}: ${e}`);

    // Couldn't find coworker record, so just use their full name
    return coworker;
  }
}

/**
 * Expire an event. This can occur when either the member badges through the
 * warehouse door, or when the member fails to badge through the warehouse
 * door within a timeout period.
 *
 * @param {Object} ev
 *   The event data, from the DoorFlow badge-in event at the front door
 *
 * @param {Boolean} badgedOut
 *   Whether we were called as a result of the member badging through the
 *   warehouse door (true), or as a result of the event timing out (false)
 */
function expireEvent(ev, badgedOut)
{
  debug(`${badgedOut ? "Completed: " : "Expired: "} ${ev.person_name}`);

  // If we timed out, display a message. Otherwise, cancel the timer
  if (! badgedOut)
  {
    ev.timer = null;
    debug(`TIMEOUT for ${ev.person_name}`);
    debug(JSON.stringify(ev, null, "  "));
  }
  else
  {
    clearTimeout(ev.timer);
    ev.timer = null;
  }

  // The timer has expired. Mark this event as dead so it'll be
  // cleared from the display queue
  ev.isDead = true;

  // Remove this event from the pending events list
  delete pendingEvents[ev.person_name];
}

/**
 * Process the recently received events. This implies:
 *
 * - eliminating all events other than a member badging through the front and
 *   warehouse doors
 * - separating the resulting events by door
 * - adding front door events to the pending event queue
 * - removing an event from the pending event queue when its matching
     warehouse door events occurs
 * - as events are removed from the pending event queue, also mark
 *   them as dead, so that the displayQueue processing can remove them
 *   from that queue as well. (The pending event queue is easy to
 *   remove things from, as its not, really a queue; it's an Object.
 *   The display queue, OTOH, is an array. We leave things on the
 *   display queue rather than doing an O(n) sequential search of the
 *   array looking for it. It'll get removed soon as we process the
 *   display queue, anyway.
 */
async function processRecentEvents()
{
  let             events;
  let             frontDoorEvents;
  let             warehouseDoorEvents;
  let             salutation;
  const           now = new  Date();
  const           hour = now.getHours();
  const           period = hour < 12 ? "morning" : hour < 18 ? "afternoon" : "evening";
  const           FRONT_DOOR_ID = 5559;
  const           WAREHOUSE_DOOR_ID = 5828;

  // Retrieve the most recent batch of events
  events = await getDoorFlowEvents();
  if (! Array.isArray(events))
  {
    console.log(timeNow(), "BAD EVENTS:\n" + JSON.stringify(events, null, "  "));
    return;
  }

  // Filter out events for no person, rejected admitance, and those
  // that we've already seen
  events = events.filter(ev => ev.person_name &&
                         [ FRONT_DOOR_ID, WAREHOUSE_DOOR_ID ].includes(ev.door_controller_id) &&
                         ev.event_label.startsWith("Admitted") &&
                         (new Date(ev.updated_at)).getTime() > lastEventTimestamp);

  // If no events remain, there's nothing to do right now
  if (events.length === 0)
  {
    return;
  }

  // Update the last event timestamp for the next time we get here.
  // The events are received sorted, with the most recent event first.
  // We can take advantage of that to avoid doing our own sorting. The
  // first event in the event list is always the most recent.
  lastEventTimestamp = (new Date(events[0].updated_at)).getTime();

  // Get the recent front door events
  frontDoorEvents = events.filter(ev => ev.door_controller_id == FRONT_DOOR_ID);

  // Get the recent warehouse door events
  warehouseDoorEvents = events.filter(ev => ev.door_controller_id == WAREHOUSE_DOOR_ID);

  // Add front door events to the pending-events queue
  for (let i = frontDoorEvents.length - 1; i >= 0; i--)
  {
    let             ev = frontDoorEvents[i];

    debug(`Adding ${ev.person_name} to the pending event list`);

    // If this is a second (or later) badge-in for this person, ensure
    // there's no active timer from the prior one and that it's unused
    // for display
    if (pendingEvents[ev.person_name])
    {
      clearTimeout(pendingEvents[ev.person_name].timer);
      pendingEvents[ev.person_name].isDead = true;
    }

    // Associate this event with its person name, making it easy
    // to locate it later when that person badges in to the
    // warehouse door
    pendingEvents[ev.person_name] = ev;

    // This event is live!
    ev.isDead = false;

    // Add a timeout so this entry goes away even if never badged
    // through the warehouse door.
    ev.timer = setTimeout(expireEvent, HALL_WALK_TIME_SEC * 1000, ev, false);

    // Add this person to the display queue
    salutation = await getSalutation(ev.person_name, ev.credentials_number);
    displayQueue.push(
      {
        args : [ "-c red", `Good ${period}, `, "-c green", `${salutation}` ],
        ev   : ev
      });
    debug("Display queue:\n" +
          JSON.stringify(displayQueue,
                         (key, value) => key == "ev" ? value.isDead : value,
                         "  "));
  }

  // Remove events from the pending-events queue, when badged
  // through the warehouse door
  for (let i = warehouseDoorEvents.length - 1; i >= 0; i--)
  {
    let             ev = warehouseDoorEvents[i];
    const           pendingEvent = pendingEvents[ev.person_name];

    // If there's a pending event for this person, expire it.
    if (pendingEvent)
    {
      expireEvent(pendingEvent, true);
    }
    else
    {
      // FUTURE:
      // We should really sound a klaxon in this case. It means that
      // the member piggybacked on someone else's badging in to the
      // front door, but then badged themselves through the warehouse
      // door. Naughty, naughty, naughty. Every member is supposed to
      // badge themselves through the front door...
      debug(`Ignoring unmatched event for ${ev.person_name}`);
    }
  }

  // Object.keys(pendingEvents).forEach(
  //   (name) =>
  //   {
  //     debug(
  //       `Pending event for ${name}:\n` +
  //         `${JSON.stringify(pendingEvents[name],
  //                           (key, value) => key == "timer" ? "<TIMER>" : value,
  //                           "  ")}`);
  //   });
}

/**
 * Figure out which greeting to display next, and display it
 */
function displayGreetings()
{
  let             args;
  let             message;
  let             messageInfo;
  let             entry = null;

  // First, search the display queue for the first non-dead entry
  while (displayQueue.length > 0)
  {
    entry = displayQueue.shift();

    // If this entry is dead, ignore it
    if (entry.ev.isDead)
    {
      entry = null;
      continue;
    }

    break;
  }

  // initialize argument list for display on marquis
  args = [ "/dev/ttyUSB0" ];

  // Did we find a non-dead entry?
  if (entry)
  {
    // Yup. Push it back on the round-robin queue, and prepare to
    // display it
    displayQueue.push(entry);
    args.push.apply(args, entry.args);
    message = entry.message;
    args.push(message);

    // We're (no longer) idle
    idle = false;
  }
  else
  {
    // There were no non-dead entries. Start or continue idle processing.
    // Were we already idle?
    if (! idle)
    {
      // Nope. Reset the idle queue with the in-order
      // set of idle messages
      idleQueue = [];
      idleQueue.push.apply(idleQueue, idleMessages);

      // We're idle now
      idle = true;
    }

    // Get the next idle message to be displayed, and push it back
    // on the queue
    messageInfo = idleQueue.shift();

    // Put it back on the queue
    idleQueue.push(messageInfo);

    // Retrieve the args and add the message to them
    args.push.apply(args, messageInfo.args);
    message = messageInfo.message;
    args.push(message);
  }

  // Only display a message if it differs from what's already displayed
  if (message != lastMessage)
  {
    console.log(timeNow(), DISPLAY_APP, JSON.stringify(args));
    let child = child_process.spawn(DISPLAY_APP, args);
    // child.stdout.on("data", (data) => console.log("DISPLAY_APP stdout: " + data));
    lastMessage = message;
  }
}

// Begin processing events
setInterval(processRecentEvents, 2000);

// Begin handling messages to be displayed
setInterval(displayGreetings, 1000);
