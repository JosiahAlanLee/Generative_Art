"""History Flow bands from the Git revisions of a set of text files.

After Viégas, Wattenberg and Dave (2004), "Studying cooperation and conflict
between authors with history flow visualizations", CHI 2004. Each drawn version
is a column whose length is the text's length. Text that survives from one
version to the next is joined by a band; deleted text ends, inserted text
begins in the later column.

Two departures from the paper, both deliberate:

* Matching uses Git's blame identity — originating commit, original file and
  original line — instead of the paper's sentence-token diff. A line that is
  edited, even by one character, becomes a new line from the editing commit.
* A band's class is the class of the commit that ``git blame`` names: the last
  commit to change the line. It is not the first writer of the words and it is
  not a share of authorship.

Classes come from evidence recorded in the repository and are reported with
that evidence: a ``Co-Authored-By: Claude`` trailer or a commit authored as
Claude; the branch name of the pull request that brought a commit onto the
first-parent line (``codex/`` or ``claude/``); presence in the first drawn
version; otherwise ``direct``. The prefixes are parameters.

Standard library and the ``git`` executable only. Reading a repository runs
``git`` locally; nothing here touches the network.
"""
import re
import subprocess
from pathlib import Path

__all__ = ["CLASSES", "extract", "versions_from_runs", "transitions"]

HEADER = re.compile(r"^([0-9a-f]{40}) (\d+) (\d+)(?: (\d+))?$")
MERGE = re.compile(r"^Merge pull request #(\d+) from [^/\s]+/(\S+)")
CLAUDE_TRAILER = re.compile(r"^Co-Authored-By:\s*Claude\b", re.I | re.M)

# Order matters for the legend and for tests; every class has a fixed texture.
CLASSES = ("base", "codex", "claude", "direct")
DEFAULT_PREFIXES = {"codex/": "codex", "claude/": "claude"}


def _git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], check=True,
                          capture_output=True, text=True).stdout


def _exists(repo, rev, path):
    return subprocess.run(["git", "-C", str(repo), "cat-file", "-e", f"{rev}:{path}"],
                          capture_output=True).returncode == 0


def _blame(repo, rev, path):
    """[(origin_sha, original_path, original_line, characters)] in file order."""
    out = _git(repo, "blame", "--line-porcelain", rev, "--", path)
    rows, sha, line, name = [], None, None, None
    for row in out.split("\n"):
        if row.startswith("\t"):
            rows.append((sha, name, line, len(row)))   # tab removed, newline added
            continue
        m = HEADER.match(row)
        if m:
            sha, line = m.group(1), int(m.group(2))
        elif row.startswith("filename "):
            name = row[9:]
    return rows


def _mainline_origins(repo, mainline):
    """Map each commit to the first-parent commit that brought it onto the line."""
    via, previous = {}, None
    for m in mainline:
        span = m if previous is None else f"{previous}..{m}"
        for c in _git(repo, "rev-list", span).split():
            via.setdefault(c, m)
        previous = m
    return via


def extract(repo, files, rev="HEAD", prefixes=None):
    """Read every first-parent revision of ``rev`` that changed one of ``files``.

    Returns a JSON-ready record: the drawn versions, the evidence for each
    origin's class, and the blamed lines of every version as runs. ``files``
    keep their given order, which is the order text is stacked in a column.
    """
    repo = Path(repo)
    prefixes = dict(DEFAULT_PREFIXES if prefixes is None else prefixes)
    head = _git(repo, "rev-parse", rev).strip()
    mainline = _git(repo, "rev-list", "--first-parent", "--reverse", head).split()
    drawn = []
    for i, c in enumerate(mainline):
        if i == 0:
            changed = any(_exists(repo, c, f) for f in files)
        else:
            changed = bool(_git(repo, "diff", "--name-only", f"{mainline[i-1]}", c, "--", *files).strip())
        if changed:
            drawn.append(c)
    if not drawn:
        raise ValueError("none of the files exists on the first-parent line")
    via = _mainline_origins(repo, mainline)
    base_cut = set(_git(repo, "rev-list", drawn[0]).split())

    origins, origin_index = [], {}
    def origin(sha):
        if sha in origin_index:
            return origin_index[sha]
        author, body = _git(repo, "log", "-1", "--format=%an%x00%B", sha).split("\x00", 1)
        merge = via.get(sha, sha)
        subject = _git(repo, "log", "-1", "--format=%s", merge).strip()
        branch = None
        m = MERGE.match(subject)
        if m:
            branch = m.group(2)
        evidence = []
        if sha in base_cut:
            cls = "base"
            evidence.append("present at the first drawn version")
        elif author == "Claude" or CLAUDE_TRAILER.search(body):
            cls = "claude"
            evidence.append("commit author or Co-Authored-By trailer names Claude")
        else:
            cls = "direct"
            for prefix, name in prefixes.items():
                if branch and branch.startswith(prefix):
                    cls = name
                    evidence.append(f"merged from branch {branch}")
                    break
            if cls == "direct":
                evidence.append("first-parent commit without a recognised branch or trailer")
        origin_index[sha] = len(origins)
        origins.append({"commit": sha, "class": cls, "via": merge, "branch": branch,
                        "subject": _git(repo, "log", "-1", "--format=%s", sha).strip(),
                        "evidence": evidence})
        return origin_index[sha]

    versions = []
    for c in drawn:
        meta = _git(repo, "log", "-1", "--format=%cI%x00%s", c).strip().split("\x00")
        runs = []
        for fi, path in enumerate(files):
            if not _exists(repo, c, path):
                continue
            for sha, name, line, chars in _blame(repo, c, path):
                oi = origin(sha)
                orig_file = name
                if (runs and runs[-1][0] == fi and runs[-1][1] == oi and runs[-1][2] == orig_file
                        and runs[-1][3] + len(runs[-1][4]) == line):
                    runs[-1][4].append(chars)
                else:
                    runs.append([fi, oi, orig_file, line, [chars]])
        versions.append({"commit": c, "date": meta[0], "subject": meta[1], "runs": runs})
    return {"repository": str(repo), "rev": head, "files": list(files),
            "prefixes": prefixes, "origins": origins, "versions": versions}


def versions_from_runs(record):
    """Expand runs into per-version line lists of (key, class, file index, chars).

    ``key`` is the blame identity (origin index, original path, original line);
    equal keys in two versions are the same surviving line.
    """
    classes = [o["class"] for o in record["origins"]]
    out = []
    for v in record["versions"]:
        lines = []
        for fi, oi, name, start, chars in v["runs"]:
            for k, n in enumerate(chars):
                lines.append(((oi, name, start + k), classes[oi], fi, n))
        out.append(lines)
    return out


def transitions(a, b):
    """Bands joining version ``a`` to ``b`` as (i0, i1, j0, j1, class) index spans.

    A band is a maximal run of lines that survive with consecutive positions in
    both versions and share a class. Indices are inclusive-exclusive.
    """
    where = {line[0]: i for i, line in enumerate(a)}
    bands = []
    for j, line in enumerate(b):
        i = where.get(line[0])
        if i is None:
            continue
        if bands and bands[-1][1] == i and bands[-1][3] == j and bands[-1][4] == line[1]:
            bands[-1][1] += 1
            bands[-1][3] += 1
        else:
            bands.append([i, i + 1, j, j + 1, line[1]])
    return [tuple(x) for x in bands]
