// English practice — lock-screen / home-screen widget for Scriptable (iOS).
//
// Paste this into a new Scriptable script called "English", set GIST_URL
// below, then add a Scriptable widget to your lock screen and pick this script.
//
// Two things it deliberately does NOT do:
//
//   * tick every second. iOS refreshes widgets on its own budget, roughly every
//     15-30 minutes. Only Live Activities update continuously, and third-party
//     scripting apps can't create those. The escalating ntfy pushes are what
//     supply real urgency; this is ambient awareness.
//   * trust the payload's clock. The Mac publishes status whenever it happens to
//     be awake, so the countdown is computed here, on the phone, from the actual
//     current time. A stale payload can be wrong about what's left to do — never
//     about how much of the day is gone.

const GIST_URL = "PASTE_YOUR_GIST_RAW_URL_HERE";

const CACHE = FileManager.local();
const CACHE_PATH = CACHE.joinPath(CACHE.cacheDirectory(), "english-c1-status.json");
const STALE_MINUTES = 45;

async function loadStatus() {
  try {
    // Cache-buster: gist raw responses are cached, and a widget showing
    // yesterday's state is worse than one admitting it doesn't know.
    const request = new Request(`${GIST_URL}?t=${Date.now()}`);
    request.timeoutInterval = 10;
    const status = await request.loadJSON();
    CACHE.writeString(CACHE_PATH, JSON.stringify(status));
    return status;
  } catch (error) {
    if (CACHE.fileExists(CACHE_PATH)) return JSON.parse(CACHE.readString(CACHE_PATH));
    return null;
  }
}

function minutesToMidnight() {
  const now = new Date();
  const midnight = new Date(now);
  midnight.setHours(24, 0, 0, 0);
  return Math.max(0, Math.round((midnight - now) / 60000));
}

function humanize(minutes) {
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return h ? `${h}h ${String(m).padStart(2, "0")}m` : `${m}m`;
}

function todayISO() {
  const now = new Date();
  now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
  return now.toISOString().slice(0, 10);
}

function ageMinutes(status) {
  if (!status || !status.generated_at) return null;
  return Math.round((Date.now() - new Date(status.generated_at)) / 60000);
}

function summarize(status) {
  // A payload from a previous day says nothing about today. This happens every
  // night at midnight, and whenever the Mac has been shut for a day.
  if (!status || status.date !== todayISO()) {
    return { headline: "—", detail: "no fresh status", done: false, streak: status ? status.streak : 0 };
  }
  if (status.done) {
    return { headline: "done", detail: "reps · journal · check", done: true, streak: status.streak };
  }
  return {
    headline: humanize(minutesToMidnight()),
    detail: status.remaining.length ? status.remaining.join(" · ") : "—",
    done: false,
    streak: status.streak,
  };
}

function buildAccessory(widget, view, status) {
  // Lock-screen accessory widgets render monochrome, so urgency has to live in
  // the words and glyphs — colour would simply be discarded here.
  const top = widget.addStack();
  top.centerAlignContent();
  const flame = top.addText(`🔥 ${view.streak}`);
  flame.font = Font.boldSystemFont(14);
  top.addSpacer(6);
  const headline = top.addText(view.done ? "✓ done" : view.headline);
  headline.font = Font.boldSystemFont(14);

  widget.addSpacer(2);
  const detail = widget.addText(view.detail);
  detail.font = Font.systemFont(11);
  detail.lineLimit = 2;

  const age = ageMinutes(status);
  if (age !== null && age > STALE_MINUTES) {
    const note = widget.addText(`as of ${new Date(status.generated_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`);
    note.font = Font.systemFont(9);
  }
}

function buildHome(widget, view, status) {
  const urgent = !view.done && minutesToMidnight() <= 120;
  widget.backgroundColor = new Color(view.done ? "#14532d" : urgent ? "#7f1d1d" : "#1f2937");

  const title = widget.addText("English");
  title.font = Font.mediumSystemFont(12);
  title.textColor = new Color("#ffffff", 0.6);

  widget.addSpacer(4);
  const headline = widget.addText(view.done ? `🔥 ${view.streak}` : view.headline);
  headline.font = Font.boldSystemFont(28);
  headline.textColor = Color.white();

  const detail = widget.addText(view.detail);
  detail.font = Font.systemFont(13);
  detail.textColor = new Color("#ffffff", 0.85);
  detail.lineLimit = 2;

  widget.addSpacer(4);
  const age = ageMinutes(status);
  const footer = widget.addText(
    view.done ? "done for today" : `🔥 ${view.streak} on the line` + (age !== null && age > STALE_MINUTES ? " · stale" : "")
  );
  footer.font = Font.systemFont(11);
  footer.textColor = new Color("#ffffff", 0.6);
}

const status = await loadStatus();
const view = summarize(status);
const widget = new ListWidget();
widget.refreshAfterDate = new Date(Date.now() + 15 * 60 * 1000);

const family = config.widgetFamily || "medium";
if (family.startsWith("accessory")) {
  buildAccessory(widget, view, status);
} else {
  buildHome(widget, view, status);
}

if (config.runsInWidget) {
  Script.setWidget(widget);
} else {
  await widget.presentMedium();
}
Script.complete();
