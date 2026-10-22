"use strict";
const $ = (id) => document.getElementById(id);
const ACTIVE = new Set(["queued", "running"]);
const PREVIEWABLE = /\.(svg|png|jpg)$/;
// Options are plain values, or [value, label] pairs when the value is not a good label.
const select = (name, options, value) => ({
  name,
  options: typeof options === "string" ? options.split(" ") : options,
  value,
});
const numeric = (name, value, min, max, step = 1) => ({
  name,
  value,
  min,
  max,
  step,
});
const check = (name, value = false) => ({ name, value, type: "checkbox" });
const optionValue = (o) => (Array.isArray(o) ? o[0] : o);
const optionLabel = (o) => (Array.isArray(o) ? o[1] : o);
const labels = {
  only: "Object / study",
  png: "PNG preview export",
  "no-optimize": "Keep original drawing order",
  dry_run: "NumPy dry run (no Blender proof)",
  no_clay: "Skip clay preview",
  face_patterns: "Face patterns",
  plates: "Plate study cameras + farmstead",
  zoneMode: "Text zone treatment",
  time: "Light",
  strength: "Ink strength (%)",
  density: "Density (%)",
  imperfection: "Imperfection (%)",
  flora: "Flora weight",
  land: "Land weight",
  built: "Building weight",
  sky: "Sky weight",
  paper: "Include paper rectangle (proof only)",
  riso: "Misregister ink layers",
  decay: "Decay (artistic, 0–1)",
  format: "Page size",
  bleed: "Add bleed",
  seed: "Seed",
  view: "Camera",
  case: "Scene case",
  compat: "Engine",
  penWidth: "Nib (mm)",
};
const labelFor = (name) =>
  labels[name] || name[0].toUpperCase() + name.slice(1);
const schemas = {
  driftless: [
    {
      title: "Scene",
      fields: [
        { name: "seed", value: "e2", type: "text" },
        select(
          "focal",
          "auto oak pine grove farmstead watertower prairie rocktop monument rock bluff sun vista",
          "auto",
        ),
        select("season", "auto spring summer autumn winter", "auto"),
        select("rock", "auto sandstone limestone quartzite", "auto"),
        select("time", "auto day dusk night", "auto"),
        select("frame", "auto none border arch oculus arcade", "auto"),
        numeric("density", 100, 50, 160),
        numeric("imperfection", 50, 0, 100),
        numeric("flora", 60, 0, 100),
        numeric("land", 60, 0, 100),
        numeric("built", 50, 0, 100),
        numeric("sky", 50, 0, 100),
        select(
          "compat",
          [
            ["", "current"],
            ["1.1", "1.1 (plates kept before 1.2)"],
          ],
          "",
        ),
      ],
    },
    {
      title: "Page & inks",
      fields: [
        select(
          "format",
          "codex codexSpread codexPlot 6x9 5.5x8.5 7x10 8.5x11 a5 a4 a3 8x8 spread6x9",
          "a4",
        ),
        select(
          "palette",
          "codex irongall fieldriso lush barnyard prussian graphite dusk nocturne kraft",
          "codex",
        ),
        numeric("strength", 100, 0, 100),
        numeric("penWidth", 0.35, 0.2, 0.8, 0.05),
        select("zone", "none codex top middle bottom", "none"),
        select("zoneMode", "fade tint", "fade"),
        check("landscape"),
        check("bleed"),
        check("paper"),
        check("riso"),
        check("no-optimize"),
      ],
    },
  ],
  farm: [
    {
      title: "Object & surface",
      fields: [
        numeric("seed", 22, 0, 4294967196),
        select(
          "only",
          "barn tractor disk_harrow hay_rake wagon farmyard comparison",
          "barn",
        ),
        numeric("decay", 0.72, 0, 1, 0.01),
        check("png", true),
      ],
    },
  ],
  infernal: [
    {
      title: "Pipeline",
      fields: [
        select(
          "case",
          "recorded_route rehearsed_route late_opening gate_unavailable",
          "recorded_route",
        ),
        select("view", "main low tower barn", "main"),
        check("dry_run", true),
        check("plates"),
        check("face_patterns"),
        check("no_clay"),
      ],
    },
  ],
};
const notes = {
  driftless:
    "Deterministic landscape plates. SVG preview and export share the same generated file. The nib changes the lines, not only their width.",
  farm: "Seeded equipment and barns. Individual pages are 190 × 140 mm; the farmyard is 280 × 210 mm. The existing batch builder offsets object seeds by family index (barn +0, tractor +1, harrow +2, rake +3, wagon +4).",
  infernal:
    "Existing fixed scene seeds. Separate bpy and engraving Python environments; every stage writes inside a private source workspace. Tower/barn views require Plates. Dry runs omit Blender validation.",
};
// Settings that a generator accepts but ignores in the current combination: disabled, with the reason.
const inert = {
  driftless(p) {
    const off = {};
    if (p.format === "codexPlot")
      for (const k of ["landscape", "bleed", "riso"])
        off[k] = "codexPlot keeps its fixed A4 sheet";
    if (p.compat === "1.1") off.rock = "engine 1.1 draws sandstone only";
    return off;
  },
  farm(p) {
    return p.only === "comparison"
      ? { decay: "the comparison always draws decay 0, 0.38 and 0.9" }
      : {};
  },
  infernal(p) {
    const off = {};
    if (p.dry_run) off.no_clay = "a dry run makes no clay preview";
    if (p.plates) off.face_patterns = "plates already include face patterns";
    return off;
  },
};

let token = "",
  instance = null,
  runtimes = {},
  current = null,
  currentJob = null,
  queueActive = false,
  preparing = false,
  artifact = "",
  loaded = null,
  svgDocument = null,
  previewURL = null,
  previewSerial = 0,
  filesKey = "",
  previewsKey = "",
  logState = { job: null, status: null };
let selectedGenerator = "driftless";
const drafts = {};
const historyItems = new Map();
const artifactLinks = new Map();
const EMPTY = $("empty").cloneNode(true);

const setText = (el, text) => {
  if (el.textContent !== text) el.textContent = text;
};
function fields(gen) {
  return schemas[gen].flatMap((s) => s.fields);
}
function readParams() {
  const p = {};
  for (const f of fields(selectedGenerator)) {
    const el = $("p-" + f.name);
    p[f.name] =
      f.type === "checkbox"
        ? el.checked
        : f.options || f.type === "text"
          ? el.value
          : Number(el.value);
  }
  return p;
}
function renderControls(gen, params = {}) {
  selectedGenerator = gen;
  $("generator").value = gen;
  $("controls").replaceChildren();
  $("generator-note").textContent = notes[gen];
  for (const [i, section] of schemas[gen].entries()) {
    const block = document.createElement("details");
    block.open = i === 0;
    const summary = document.createElement("summary");
    summary.textContent = section.title;
    block.append(summary);
    for (const f of section.fields) {
      const label = document.createElement("label");
      label.textContent = labelFor(f.name);
      const el = document.createElement(f.options ? "select" : "input");
      el.id = "p-" + f.name;
      el.setAttribute("aria-label", labelFor(f.name));
      if (f.options) {
        for (const option of f.options) {
          const opt = document.createElement("option");
          opt.value = optionValue(option);
          opt.textContent = optionLabel(option);
          el.append(opt);
        }
      } else {
        el.type = f.type || "number";
        if (f.min !== undefined) {
          el.min = f.min;
          el.max = f.max;
          el.step = f.step;
        }
        el.required = f.type !== "checkbox";
      }
      const value = params[f.name] ?? f.value;
      if (f.type === "checkbox") el.checked = value;
      else el.value = value;
      el.addEventListener("change", applyConstraints);
      if (f.type === "checkbox") label.prepend(el);
      else label.append(el);
      block.append(label);
    }
    $("controls").append(block);
  }
  applyConstraints();
}
function applyConstraints(event) {
  // Plates include the face patterns; the server refuses both together.
  if (event?.target?.id === "p-plates" && event.target.checked)
    $("p-face_patterns").checked = false;
  const p = readParams();
  const off = inert[selectedGenerator](p);
  const reasons = new Map();
  for (const f of fields(selectedGenerator)) {
    const el = $("p-" + f.name);
    const why = off[f.name];
    el.disabled = Boolean(why);
    el.parentElement.classList.toggle("inactive", Boolean(why));
    el.parentElement.title = why ? "No effect: " + why : "";
    if (why) reasons.set(why, [...(reasons.get(why) || []), labelFor(f.name)]);
  }
  const lines = [...reasons].map(
    ([why, names]) => `${names.join(", ")}: no effect, ${why}.`,
  );
  if (selectedGenerator === "infernal") {
    for (const opt of $("p-view").options)
      opt.disabled = !p.plates && ["tower", "barn"].includes(opt.value);
    if (!p.plates && ["tower", "barn"].includes(p.view))
      lines.push("The tower and barn cameras need Plates.");
  }
  $("control-note").textContent = lines.join(" ");
  $("control-note").hidden = !lines.length;
}
function message(text = "") {
  $("message").textContent = text;
}
function status(text) {
  setText($("connection"), text);
}
async function loadConfig() {
  const r = await fetch("/api/config");
  const config = await r.json();
  if (!r.ok) throw new Error(config.error || r.statusText);
  token = config.token;
  instance = config.instance;
  runtimes = config.runtimes;
  $("runtimes").textContent = Object.entries(config.runtimes)
    .map(([k, v]) => k + ": " + (v || "not configured / unavailable"))
    .join("\n");
  $("output-root").textContent = config.output_root;
}
async function api(path, data, retry = true) {
  const r = await fetch(
    path,
    data === undefined
      ? {}
      : {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-Workbench-Token": token,
          },
          body: JSON.stringify(data),
        },
  );
  // A new instance id means the server restarted with a new session token.
  const seen = r.headers.get("X-Workbench-Instance");
  if (seen && instance && seen !== instance) {
    await loadConfig();
    status("LOCAL / CONNECTED · SERVER RESTARTED");
    // A refused POST did nothing on the server, so it is safe to send again with the new token.
    if (data !== undefined && r.status === 403 && retry)
      return api(path, data, false);
  }
  const result = await r.json();
  if (!r.ok) throw new Error(result.error || r.statusText);
  return result;
}
function fileURL(job, path) {
  return (
    "/api/jobs/" +
    job +
    "/files/" +
    path.split("/").map(encodeURIComponent).join("/")
  );
}
function displayName(path) {
  return path
    .replace(/^artifacts\//, "")
    .replace(/^workspace\/studies\/infernal-landscape\/output\//, "");
}
function jobTitle(recipe) {
  const p = recipe.params;
  if (recipe.generator === "driftless")
    return (
      `driftless / ${p.seed} · ${p.format}` +
      (p.penWidth && p.penWidth !== 0.35 ? ` · ${p.penWidth} mm nib` : "") +
      (p.compat ? ` · engine ${p.compat}` : "")
    );
  if (recipe.generator === "farm")
    return `farm / ${p.only.replace("_", " ")} · seed ${p.seed} · decay ${p.decay}`;
  return (
    `infernal / ${p.case} · ${p.view}` +
    (p.plates ? " · plates" : p.face_patterns ? " · face patterns" : "") +
    (p.dry_run ? " · dry run" : "")
  );
}
function save(data, name) {
  const url = URL.createObjectURL(
    new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }),
  );
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
// Refuses anything the form cannot show, rather than dropping it: a recipe that loads is the
// recipe that renders.
function applyRecipe(recipe) {
  if (
    !recipe ||
    typeof recipe !== "object" ||
    !Object.hasOwn(schemas, recipe.generator) ||
    !recipe.params ||
    typeof recipe.params !== "object" ||
    Array.isArray(recipe.params)
  )
    throw Error("Not a workbench recipe");
  const known = new Map(fields(recipe.generator).map((f) => [f.name, f]));
  const unknown = Object.keys(recipe.params).filter((k) => !known.has(k));
  if (unknown.length)
    throw Error(
      `Not loaded: the recipe has settings this form doesn't: ${unknown.join(", ")}.`,
    );
  for (const [k, v] of Object.entries(recipe.params)) {
    const f = known.get(k);
    const ok = f.options
      ? f.options.map(optionValue).includes(v)
      : f.type === "checkbox"
        ? typeof v === "boolean"
        : f.type === "text"
          ? typeof v === "string"
          : typeof v === "number" && Number.isFinite(v);
    if (!ok)
      throw Error(
        `Not loaded: ${labelFor(k)} has a value this form can't show (${JSON.stringify(v)}).`,
      );
  }
  renderControls(recipe.generator, recipe.params);
}

$("generator").onchange = () => {
  drafts[selectedGenerator] = readParams();
  renderControls($("generator").value, drafts[$("generator").value]);
};
$("recipe").onsubmit = async (e) => {
  e.preventDefault();
  message();
  try {
    const job = await api("/api/jobs", {
      generator: selectedGenerator,
      params: readParams(),
    });
    await chooseJob(job.id);
  } catch (err) {
    message(err.message);
  }
};
$("save-recipe").onclick = () =>
  save(
    { generator: selectedGenerator, params: readParams() },
    "workbench-recipe.json",
  );
$("load-recipe").onchange = async (e) => {
  try {
    applyRecipe(JSON.parse(await e.target.files[0].text()));
    message("Recipe loaded. Render creates a fresh job folder.");
  } catch (err) {
    message(err.message);
  }
  e.target.value = "";
};
$("use-recipe").onclick = () => {
  if (!currentJob) return;
  try {
    applyRecipe(currentJob.recipe);
    message(
      "Settings from the selected job loaded. Render creates a fresh job folder.",
    );
  } catch (err) {
    message(err.message);
  }
};
$("cancel").onclick = async () => {
  try {
    await api("/api/jobs/" + current + "/cancel", {});
    await refresh();
  } catch (err) {
    message(err.message);
  }
};
$("prepare").onclick = async () => {
  const job = current,
    source = artifact;
  preparing = true;
  updateButtons();
  message("Making the vpype copy…");
  try {
    await api("/api/jobs/" + job + "/prepare", { file: source });
    if (current === job) {
      artifact = source.replace(/\.svg$/, ".vpype.svg");
      loaded = null;
    }
    await refresh();
    message(
      "vpype copy saved beside the original and shown here; the original is unchanged.",
    );
  } catch (err) {
    message(err.message);
  } finally {
    preparing = false;
    updateButtons();
  }
};
$("zoom").onchange = () => {
  // Keep the point at the centre of the view where it is.
  const box = $("paper");
  const cx =
    (box.scrollLeft + box.clientWidth / 2) / Math.max(1, box.scrollWidth);
  const cy =
    (box.scrollTop + box.clientHeight / 2) / Math.max(1, box.scrollHeight);
  applyZoom();
  box.scrollLeft = cx * box.scrollWidth - box.clientWidth / 2;
  box.scrollTop = cy * box.scrollHeight - box.clientHeight / 2;
};
$("preview").addEventListener("load", applyZoom);
new ResizeObserver(() => {
  if ($("zoom").value === "fit") applyZoom();
}).observe($("paper"));
$("preview-file").onchange = () =>
  showArtifact($("preview-file").value).catch((err) => message(err.message));

async function chooseJob(id) {
  current = id;
  artifact = "";
  loaded = null;
  await refresh();
}
// History entries are updated in place, so focus, hover and clicks survive the polling.
function renderHistory(jobs) {
  const box = $("jobs");
  const seen = new Set();
  let prev = null;
  for (const job of jobs) {
    seen.add(job.id);
    let item = historyItems.get(job.id);
    if (!item) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "job";
      const title = document.createElement("strong");
      const state = document.createElement("small");
      const date = document.createElement("small");
      button.append(title, state, date);
      button.onclick = () =>
        chooseJob(job.id).catch((err) => message(err.message));
      item = { button, title, state, date };
      historyItems.set(job.id, item);
    }
    setText(item.title, jobTitle(job.recipe));
    setText(item.state, job.status);
    if (item.state.className !== job.status) item.state.className = job.status;
    setText(item.date, new Date(job.created).toLocaleString());
    const pressed = String(current === job.id);
    if (item.button.getAttribute("aria-pressed") !== pressed)
      item.button.setAttribute("aria-pressed", pressed);
    const want = prev ? prev.nextSibling : box.firstChild;
    if (item.button !== want) box.insertBefore(item.button, want);
    prev = item.button;
  }
  for (const [id, item] of historyItems)
    if (!seen.has(id)) {
      item.button.remove();
      historyItems.delete(id);
    }
}
// Download links and the preview menu change only when the job's files do.
function renderFiles(job) {
  const key =
    job.id + "|" + job.files.map((f) => f.path + ":" + f.size).join("|");
  if (key === filesKey) return;
  filesKey = key;
  const box = $("artifacts");
  if (box.dataset.job !== job.id) {
    box.replaceChildren();
    artifactLinks.clear();
    box.dataset.job = job.id;
  }
  const seen = new Set();
  let prev = null;
  for (const file of job.files) {
    seen.add(file.path);
    let a = artifactLinks.get(file.path);
    if (!a) {
      a = document.createElement("a");
      a.href = fileURL(job.id, file.path) + "?download";
      artifactLinks.set(file.path, a);
    }
    setText(a, file.path + " · " + (file.size / 1024).toFixed(1) + " KB");
    const want = prev ? prev.nextSibling : box.firstChild;
    if (a !== want) box.insertBefore(a, want);
    prev = a;
  }
  for (const [path, a] of artifactLinks)
    if (!seen.has(path)) {
      a.remove();
      artifactLinks.delete(path);
    }
  const previews = job.files.filter((f) => PREVIEWABLE.test(f.path));
  const pkey = job.id + "|" + previews.map((f) => f.path).join("|");
  if (pkey === previewsKey) return;
  previewsKey = pkey;
  const selector = $("preview-file");
  selector.replaceChildren();
  for (const f of previews) {
    const option = document.createElement("option");
    option.value = f.path;
    option.textContent = displayName(f.path);
    selector.append(option);
  }
  if (!previews.length) {
    const option = document.createElement("option");
    option.textContent = "No previewable file yet";
    selector.append(option);
  }
  selector.disabled = !previews.length;
  if (artifact) selector.value = artifact;
}
// The log is fetched while a job is active and once more when it settles. New text is appended,
// so a selection survives, and the view follows the end only if it was already there.
async function updateLog(job) {
  const switched = logState.job !== job.id;
  if (!switched && !ACTIVE.has(job.status) && !ACTIVE.has(logState.status))
    return;
  const r = await fetch("/api/jobs/" + job.id + "/log");
  if (!r.ok || current !== job.id) return;
  const text = await r.text();
  if (current !== job.id) return;
  logState = { job: job.id, status: job.status };
  const box = $("log");
  const atEnd =
    switched || box.scrollTop + box.clientHeight >= box.scrollHeight - 4;
  const old = box.textContent;
  if (text !== old) {
    if (!switched && old && text.startsWith(old))
      box.append(document.createTextNode(text.slice(old.length)));
    else box.textContent = text || "No output yet.";
  }
  if (atEnd) box.scrollTop = box.scrollHeight;
}
function clearPreview(note) {
  artifact = "";
  loaded = null;
  svgDocument = null;
  previewSerial++;
  $("preview").hidden = true;
  $("preview").removeAttribute("src");
  $("empty").replaceChildren(
    ...(note ? [note] : EMPTY.cloneNode(true).childNodes),
  );
  $("empty").hidden = false;
  $("inspection").hidden = true;
  $("download").hidden = true;
}
// A file is (re)loaded when it is new, when its size changes (it was still being written), and
// once when its job settles. A failed load is retried on the same conditions, not every poll.
async function updatePreview(job) {
  const previews = job.files.filter((f) => PREVIEWABLE.test(f.path));
  if (!previews.length) {
    const note = ACTIVE.has(job.status)
      ? "Rendering… the proof appears when the first file is written."
      : job.status === "succeeded"
        ? null
        : `No proof: the job ${job.status}. See the job log.`;
    if (
      artifact ||
      loaded ||
      $("empty").hidden ||
      $("empty").textContent !== (note ?? EMPTY.textContent)
    )
      clearPreview(note);
    return;
  }
  const target =
    previews.find((f) => f.path === artifact) ||
    previews.find(
      (f) => f.path.endsWith(".svg") && !f.path.endsWith(".vpype.svg"),
    ) ||
    previews[0];
  const settled = !ACTIVE.has(job.status);
  const stale =
    !loaded ||
    loaded.job !== job.id ||
    loaded.path !== target.path ||
    loaded.size !== target.size ||
    (settled && !loaded.settled);
  if (stale) await showArtifact(target.path);
  if (artifact && $("preview-file").value !== artifact)
    $("preview-file").value = artifact;
}
function updateButtons() {
  const job = currentJob;
  $("cancel").disabled = !job || !ACTIVE.has(job.status);
  $("use-recipe").disabled = !job;
  let why = "";
  if (!runtimes.vpype)
    why =
      "vpype was not found: install it, set WORKBENCH_VPYPE and restart the server";
  else if (!job || job.status !== "succeeded") why = "needs a successful render";
  else if (!artifact.endsWith(".svg") || artifact.endsWith(".vpype.svg"))
    why = "select an original SVG";
  else if (queueActive) why = "wait for the render queue to finish";
  else if (preparing) why = "the copy is being made";
  else if (
    job.files.some(
      (f) => f.path === artifact.replace(/\.svg$/, ".vpype.svg"),
    )
  )
    why = "this SVG already has a vpype copy";
  $("prepare").disabled = Boolean(why);
  $("prepare").title = why;
}
async function refresh() {
  const jobs = await api("/api/jobs");
  queueActive = jobs.some((j) => ACTIVE.has(j.status));
  if (!current && jobs.length) current = jobs[0].id;
  renderHistory(jobs);
  if (!current) {
    updateButtons();
    return;
  }
  const requested = current;
  const job = await api("/api/jobs/" + requested);
  if (current !== requested) return;
  currentJob = job;
  setText($("proof-title"), jobTitle(job.recipe) + " · " + job.status);
  setText(
    $("job-location"),
    job.directory + (job.error ? " — " + job.error : ""),
  );
  await updateLog(job);
  if (current !== requested) return;
  renderFiles(job);
  await updatePreview(job);
  updateButtons();
}
function drawSVG() {
  if (!svgDocument) return;
  if (previewURL) URL.revokeObjectURL(previewURL);
  previewURL = URL.createObjectURL(
    new Blob([new XMLSerializer().serializeToString(svgDocument)], {
      type: "image/svg+xml",
    }),
  );
  $("preview").src = previewURL;
}
// Fit, or a percentage of the sheet's physical size (an SVG in mm shows at 96 px per inch at 100%).
function applyZoom() {
  const img = $("preview");
  if (img.hidden) return;
  const w = img.naturalWidth,
    h = img.naturalHeight;
  img.classList.toggle("fallback", !w || !h);
  if (!w || !h) {
    img.style.width = img.style.height = "";
    return;
  }
  let scale;
  if ($("zoom").value === "fit") {
    const box = $("paper"),
      cs = getComputedStyle(box);
    const aw =
      box.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight);
    const ah =
      box.clientHeight -
      parseFloat(cs.paddingTop) -
      parseFloat(cs.paddingBottom);
    scale = Math.max(0.01, Math.min(aw / w, ah / h));
  } else scale = Number($("zoom").value) / 100;
  img.style.width = Math.round(w * scale) + "px";
  img.style.height = Math.round(h * scale) + "px";
}
// Inkscape-style layers often carry style="display:inline", which beats a display attribute,
// so the switches set the inline style.
function visible(g) {
  return g.getAttribute("display") !== "none" && g.style?.display !== "none";
}
function setVisible(g, on) {
  if (g.style) g.style.setProperty("display", on ? "inline" : "none");
  else g.setAttribute("display", on ? "inline" : "none");
}
const MM = {
  mm: 1,
  cm: 10,
  in: 25.4,
  pt: 25.4 / 72,
  pc: 25.4 / 6,
  px: 25.4 / 96,
  q: 0.25,
  "": 25.4 / 96,
};
function sheet(svg) {
  const mm = (v) => {
    const m = /^\s*([\d.]+)\s*(mm|cm|in|pt|pc|px|q)?\s*$/i.exec(v || "");
    return m ? Number(m[1]) * MM[(m[2] || "").toLowerCase()] : null;
  };
  const w = mm(svg.getAttribute("width")),
    h = mm(svg.getAttribute("height"));
  return w && h
    ? `${+w.toFixed(3)} × ${+h.toFixed(3)} mm`
    : `${svg.getAttribute("width")} × ${svg.getAttribute("height")}`;
}
async function showArtifact(path) {
  const serial = ++previewSerial,
    jobId = current,
    job = currentJob;
  const file = job?.id === jobId ? job.files.find((f) => f.path === path) : null;
  artifact = path;
  loaded = {
    job: jobId,
    path,
    size: file?.size,
    settled: !ACTIVE.has(job?.status),
  };
  const url = fileURL(jobId, path);
  $("download").href = url + "?download";
  $("download").hidden = false;
  $("download").textContent = path.endsWith(".vpype.svg")
    ? "Download vpype copy"
    : "Download original";
  $("layers").replaceChildren();
  $("inspection").hidden = !path.endsWith(".svg");
  svgDocument = null;
  updateButtons();
  try {
    if (path.endsWith(".svg")) {
      const response = await fetch(url);
      if (!response.ok) throw Error("Preview unavailable");
      const source = await response.text();
      if (serial !== previewSerial || jobId !== current) return;
      const doc = new DOMParser().parseFromString(source, "image/svg+xml");
      if (doc.querySelector("parsererror"))
        throw Error("the SVG is incomplete or invalid");
      svgDocument = doc;
      const svg = doc.documentElement,
        ns = "http://www.inkscape.org/namespaces/inkscape";
      const subpaths = Array.from(svg.querySelectorAll("path")).reduce(
        (n, p) => n + (p.getAttribute("d")?.match(/[Mm]/g)?.length || 0),
        0,
      );
      const drawn = svg.querySelectorAll(
        "path,polyline,line,polygon,circle,ellipse,rect",
      ).length;
      const strokes =
        subpaths +
        svg.querySelectorAll("polyline,line,polygon,circle,ellipse,rect")
          .length;
      const layers = Array.from(svg.querySelectorAll("g")).filter(
        (g) => g.hasAttributeNS(ns, "label") || g.hasAttribute("data-layer"),
      );
      $("dimensions").textContent =
        `${sheet(svg)} · viewBox ${svg.getAttribute("viewBox")} · ${drawn.toLocaleString()} drawing elements · ${strokes.toLocaleString()} strokes`;
      for (const g of layers) {
        const label = document.createElement("label");
        const input = document.createElement("input");
        input.type = "checkbox";
        input.checked = visible(g);
        input.onchange = () => {
          setVisible(g, input.checked);
          drawSVG();
        };
        label.append(
          input,
          document.createTextNode(
            g.getAttributeNS(ns, "label") || g.getAttribute("data-layer"),
          ),
        );
        $("layers").append(label);
      }
      $("inspection-note").textContent =
        (layers.length
          ? "Layer switches affect the proof only; downloads retain every layer. "
          : "No labeled layers. ") +
        (svg.querySelector("image") ? "Contains raster content. " : "") +
        "Zoom percentages are of the sheet's physical size. Browser proof is not a physical pen simulation.";
      // Render as an image Blob: SVG scripts cannot run in the app document.
      $("empty").hidden = true;
      $("preview").hidden = false;
      drawSVG();
    } else {
      if (previewURL) {
        URL.revokeObjectURL(previewURL);
        previewURL = null;
      }
      $("empty").hidden = true;
      $("preview").hidden = false;
      // The size in the URL makes the browser fetch a file that has grown since it was shown.
      $("preview").src = url + (file ? "?v=" + file.size : "");
    }
  } catch (err) {
    if (serial !== previewSerial) return;
    loaded.failed = true;
    $("preview").hidden = true;
    $("inspection").hidden = true;
    $("empty").replaceChildren(
      `Preview not ready: ${err.message}. It is tried again when the file changes or the job finishes.`,
    );
    $("empty").hidden = false;
  }
}
async function start() {
  renderControls("driftless");
  try {
    await loadConfig();
    status("LOCAL / CONNECTED");
    await refresh();
  } catch (err) {
    status("DISCONNECTED");
    message(err.message);
  }
}
let polling = false;
setInterval(async () => {
  if (polling || !token || document.hidden) return;
  polling = true;
  try {
    await refresh();
    if ($("connection").textContent === "DISCONNECTED")
      status("LOCAL / CONNECTED");
  } catch (err) {
    status("DISCONNECTED");
    message(err.message);
  } finally {
    polling = false;
  }
}, 1500);
start();
