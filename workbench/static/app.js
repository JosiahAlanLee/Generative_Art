"use strict";
const $ = (id) => document.getElementById(id);
const select = (name, options, value) => ({
  name,
  options: options.split(" "),
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
  paper: "Include paper rectangle",
  riso: "Misregister ink layers",
  decay: "Decay (artistic, 0–1)",
  format: "Page size",
  bleed: "Add bleed",
  seed: "Seed",
  view: "Camera",
  case: "Scene case",
};
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
    "Deterministic landscape plates. SVG preview and export share the same generated file.",
  farm: "Seeded equipment and barns. Individual pages are 190 × 140 mm; the farmyard is 280 × 210 mm. The existing batch builder offsets object seeds by family index (barn +0, tractor +1, harrow +2, rake +3, wagon +4).",
  infernal:
    "Existing fixed scene seeds. Separate bpy and engraving Python environments; every stage writes inside a private source workspace. Tower/barn views require Plates. Dry runs omit Blender validation.",
};
let token = "",
  current = null,
  currentJob = null,
  artifact = "",
  svgDocument = null,
  previewURL = null,
  previewSerial = 0;
let selectedGenerator = "driftless";
const drafts = {};
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
      label.textContent =
        labels[f.name] || f.name[0].toUpperCase() + f.name.slice(1);
      const el = document.createElement(f.options ? "select" : "input");
      el.id = "p-" + f.name;
      el.setAttribute(
        "aria-label",
        labels[f.name] || f.name[0].toUpperCase() + f.name.slice(1),
      );
      if (f.options) {
        for (const option of f.options) {
          const opt = document.createElement("option");
          opt.value = option;
          opt.textContent = option;
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
      if (f.type === "checkbox") label.prepend(el);
      else label.append(el);
      block.append(label);
    }
    $("controls").append(block);
  }
}
function message(text = "") {
  $("message").textContent = text;
}
async function api(path, data) {
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
    const recipe = JSON.parse(await e.target.files[0].text());
    if (
      !schemas[recipe.generator] ||
      !recipe.params ||
      typeof recipe.params !== "object"
    )
      throw Error("Not a workbench recipe");
    renderControls(recipe.generator, recipe.params);
    message("Recipe loaded. Render creates a fresh job folder.");
  } catch (err) {
    message(err.message);
  }
  e.target.value = "";
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
  const button = $("prepare");
  button.disabled = true;
  message("Preparing copy…");
  try {
    await api("/api/jobs/" + current + "/prepare", { file: artifact });
    await refresh();
    message(
      "Prepared copy saved beside the original. Select it below to inspect.",
    );
  } catch (err) {
    message(err.message);
  } finally {
    button.disabled =
      !currentJob ||
      currentJob.status !== "succeeded" ||
      !artifact.endsWith(".svg") ||
      artifact.endsWith(".vpype.svg");
  }
};
$("zoom").onchange = () => {
  const scale = Number($("zoom").value);
  $("preview").style.width = scale + "%";
  $("preview").style.height = scale === 100 ? "100%" : "auto";
};
$("preview-file").onchange = () =>
  showArtifact($("preview-file").value).catch((err) => message(err.message));
async function chooseJob(id) {
  current = id;
  artifact = "";
  await refresh();
}
async function refresh() {
  const jobs = await api("/api/jobs");
  $("jobs").replaceChildren();
  for (const job of jobs) {
    const button = document.createElement("button");
    button.className = "job";
    button.setAttribute("aria-pressed", String(current === job.id));
    const title = document.createElement("strong");
    title.textContent =
      job.recipe.generator +
      " / " +
      (job.recipe.params.seed ?? job.recipe.params.case);
    const state = document.createElement("small");
    state.className = job.status;
    state.textContent = job.status;
    const date = document.createElement("small");
    date.textContent = new Date(job.created).toLocaleString();
    button.append(title, state, date);
    button.onclick = () =>
      chooseJob(job.id).catch((err) => message(err.message));
    $("jobs").append(button);
  }
  if (!current) {
    if (jobs.length) {
      current = jobs[0].id;
    } else return;
  }
  const requested = current;
  const job = await api("/api/jobs/" + requested);
  if (current !== requested) return;
  currentJob = job;
  $("proof-title").textContent = job.recipe.generator + " · " + job.status;
  $("job-location").textContent =
    job.directory + (job.error ? " — " + job.error : "");
  $("cancel").disabled = !["queued", "running"].includes(job.status);
  const logText = await (await fetch("/api/jobs/" + job.id + "/log")).text();
  if (current !== requested) return;
  $("log").textContent = logText;
  $("log").scrollTop = $("log").scrollHeight;
  $("artifacts").replaceChildren();
  const previews = job.files.filter((f) => /\.(svg|png|jpg)$/.test(f.path));
  const selector = $("preview-file");
  selector.replaceChildren();
  selector.disabled = !previews.length;
  for (const file of job.files) {
    const a = document.createElement("a");
    a.href = fileURL(job.id, file.path) + "?download";
    a.textContent = file.path + " · " + (file.size / 1024).toFixed(1) + " KB";
    $("artifacts").append(a);
  }
  for (const f of previews) {
    const option = document.createElement("option");
    option.value = f.path;
    option.textContent = f.path.replace(/^artifacts\//, "");
    selector.append(option);
  }
  if (previews.length) {
    if (!previews.some((f) => f.path === artifact))
      await showArtifact(
        (previews.find((f) => f.path.endsWith(".svg")) || previews[0]).path,
      );
    selector.value = artifact;
  } else {
    artifact = "";
    svgDocument = null;
    previewSerial++;
    $("preview").hidden = true;
    $("empty").hidden = false;
    $("inspection").hidden = true;
    $("download").hidden = true;
  }
  $("prepare").disabled =
    job.status !== "succeeded" ||
    !artifact.endsWith(".svg") ||
    artifact.endsWith(".vpype.svg");
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
async function showArtifact(path) {
  const serial = ++previewSerial,
    jobId = current;
  artifact = path;
  const url = fileURL(jobId, path);
  $("download").href = url + "?download";
  $("download").hidden = false;
  $("download").textContent = path.endsWith(".vpype.svg")
    ? "Download prepared copy"
    : "Download original";
  $("empty").hidden = true;
  $("preview").hidden = false;
  $("layers").replaceChildren();
  $("inspection").hidden = !path.endsWith(".svg");
  svgDocument = null;
  if (path.endsWith(".svg")) {
    const response = await fetch(url);
    if (!response.ok) throw Error("Preview unavailable");
    const source = await response.text();
    if (serial !== previewSerial || jobId !== current) return;
    svgDocument = new DOMParser().parseFromString(source, "image/svg+xml");
    if (svgDocument.querySelector("parsererror")) throw Error("Invalid SVG");
    const svg = svgDocument.documentElement,
      ns = "http://www.inkscape.org/namespaces/inkscape";
    const subpaths = Array.from(svg.querySelectorAll("path")).reduce(
      (n, p) => n + (p.getAttribute("d")?.match(/[Mm]/g)?.length || 0),
      0,
    );
    const layers = Array.from(svg.querySelectorAll("g")).filter(
      (g) => g.hasAttributeNS(ns, "label") || g.hasAttribute("data-layer"),
    );
    $("dimensions").textContent =
      `${svg.getAttribute("width")} × ${svg.getAttribute("height")} · viewBox ${svg.getAttribute("viewBox")} · ${svg.querySelectorAll("path,polyline,line,polygon,circle,ellipse,rect").length.toLocaleString()} SVG elements · ${subpaths.toLocaleString()} path subpaths`;
    for (const g of layers) {
      const label = document.createElement("label");
      const input = document.createElement("input");
      input.type = "checkbox";
      input.checked = true;
      input.onchange = () => {
        g.setAttribute("display", input.checked ? "inline" : "none");
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
      "Browser proof is not a physical pen simulation. vpype may change grouping and styling; inspect its copy.";
    // Render as an image Blob: SVG scripts cannot run in the app document.
    drawSVG();
  } else {
    if (previewURL) {
      URL.revokeObjectURL(previewURL);
      previewURL = null;
    }
    $("preview").src = url;
  }
  $("prepare").disabled =
    currentJob?.status !== "succeeded" ||
    !path.endsWith(".svg") ||
    path.endsWith(".vpype.svg");
}
async function start() {
  renderControls("driftless");
  try {
    const config = await api("/api/config");
    token = config.token;
    $("connection").textContent = "LOCAL / CONNECTED";
    $("runtimes").textContent = Object.entries(config.runtimes)
      .map(([k, v]) => k + ": " + (v || "not configured / unavailable"))
      .join("\n");
    $("output-root").textContent = config.output_root;
    await refresh();
  } catch (err) {
    $("connection").textContent = "DISCONNECTED";
    message(err.message);
  }
}
let polling = false;
setInterval(async () => {
  if (polling || !token) return;
  polling = true;
  try {
    await refresh();
    $("connection").textContent = "LOCAL / CONNECTED";
  } catch (err) {
    $("connection").textContent = "DISCONNECTED";
    message(err.message);
  } finally {
    polling = false;
  }
}, 1500);
start();
