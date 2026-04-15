"""
generate_md.py — Generate .md and .docx from a resume .tex file.

Reads the .tex file to discover which proficiency/experience blocks and
index lists are active, then pulls the corresponding bullet text from
bullets.lua via lupa (same source as LaTeX).

Outputs both a .md and a .docx (via pandoc) alongside the PDF.

Usage:
    python generate_md.py skill-resume-AI
    python generate_md.py resume-EXP
    python generate_md.py skill-resume-PMM

Called by VS Code LaTeX Workshop recipe after every successful build.
"""

import os
import re
import subprocess
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RESUMES_DIR  = os.path.join(PROJECT_ROOT, "resumes")
INCLUDES_DIR = os.path.join(PROJECT_ROOT, "includes")
DATA_DIR     = os.path.join(PROJECT_ROOT, "data")

# ─── LaTeX helpers ───────────────────────────────────────────────────────────

def _decode(text):
    """Strip LaTeX escapes for plain-text output."""
    if not text:
        return ""
    text = text.replace("\\%",  "%")
    text = text.replace("\\$",  "$")
    text = text.replace("\\&",  "&")
    text = text.replace("\\#",  "#")
    text = text.replace("\\textemdash",  "\u2014")
    text = text.replace("\\textendash",  "\u2013")
    text = re.sub(r"\\[a-zA-Z]+\b", " ", text)
    text = re.sub(r"\\(.)",        r"\1", text)
    return re.sub(r"  +", " ", text).strip()


# ─── Command → data-key maps ─────────────────────────────────────────────────

# PM proficiency command suffix → skill key
PM_PROF_CMDS = {
    "propmAiQ":             "AI",
    "propmMlQ":             "ML",
    "propmExperimentQ":     "Experimentation",
    "propmAnalyticsQ":      "Analytics",
    "propmApiQ":            "API",
    "propmVoCQ":            "VoC",
    "propmPrototypingQ":    "Prototyping",
    "propmCmsQ":            "CMS",
    "propmSeoQ":            "SEO",
    "propmGrowthQ":         "Growth",
    "propmAdtechQ":         "AdTech",
    "propmRagQ":            "RAG",
    "propmDesignSystemsQ":  "DesignSystems",
}

# PMM proficiency command → skill key
PMM_PROF_CMDS = {
    "propmmPositioningQ": "Positioning",
    "propmmGtmQ":         "GTM",
    "propmmResearchQ":    "Research",
    "propmmEnablementQ":  "Enablement",
    "propmmLifecycleQ":   "Lifecycle",
    "propmmAnalyticsQ":   "Analytics",
    "propmmContentQ":     "Content",
    "propmmDemandQ":      "Demand",
    "propmmTechnicalQ":   "TechnicalPMM",
    "propmmAiQ":          "AI",
    "propmmPartnerQ":     "Partner",
}

# PM experience command → company key
PM_EXP_CMDS = {
    "expinstapageQ":   "instapage",
    "expnerdwalletQ":  "nerdwallet",
    "expstubhubQ":     "stubhub",
    "expaenetworksQ":  "aenetworks",
    "expadweekQ":      "adweek",
    "expprometheusQ":  "prometheus",
    "expmediabistroQ": "mediabistro",
}

# PMM experience command → company key  (note: prometeus typo matches the .tex)
PMM_EXP_CMDS = {
    "expinstapagePMMQ":   "instapage",
    "expnerdwalletPMMQ":  "nerdwallet",
    "expstubhubPMMQ":     "stubhub",
    "expaenetworksPMMQ":  "aenetworks",
    "expadweekPMMQ":      "adweek",
    "expprometeusPMMQ":   "prometheus",
    "expmediabistroPMMQ": "mediabistro",
}

COMPANY_DISPLAY = {
    "instapage":   "Instapage",
    "nerdwallet":  "NerdWallet",
    "stubhub":     "StubHub",
    "aenetworks":  "A+E Networks",
    "adweek":      "Adweek",
    "prometheus":  "Prometheus Global Media",
    "mediabistro": "Mediabistro",
}

ALL_CMDS = {**PM_PROF_CMDS, **PMM_PROF_CMDS, **PM_EXP_CMDS, **PMM_EXP_CMDS}

# ─── Tex file parser ─────────────────────────────────────────────────────────

# Matches \commandName  or  \commandName[1,2,3]
_CMD_RE = re.compile(r"\\([a-zA-Z]+)(?:\[([0-9,\s]+)\])?")


def parse_tex(tex_path):
    """
    Scan a .tex file for known block commands (in document order).
    Returns a list of dicts:
        {"type": "pm_prof"|"pmm_prof"|"pm_exp"|"pmm_exp",
         "key":  skill_key or company_key,
         "indices": [1,2,3] or []}
    """
    with open(tex_path) as f:
        source = f.read()

    # Strip comments (% to end of line, but not \%)
    source = re.sub(r"(?<!\\)%.*", "", source)

    blocks = []
    for m in _CMD_RE.finditer(source):
        cmd     = m.group(1)
        raw_idx = m.group(2) or ""
        indices = [int(x.strip()) for x in raw_idx.split(",") if x.strip()]

        if cmd in PM_PROF_CMDS:
            blocks.append({"type": "pm_prof",  "key": PM_PROF_CMDS[cmd],  "indices": indices})
        elif cmd in PMM_PROF_CMDS:
            blocks.append({"type": "pmm_prof", "key": PMM_PROF_CMDS[cmd], "indices": indices})
        elif cmd in PM_EXP_CMDS:
            blocks.append({"type": "pm_exp",   "key": PM_EXP_CMDS[cmd],   "indices": indices})
        elif cmd in PMM_EXP_CMDS:
            blocks.append({"type": "pmm_exp",  "key": PMM_EXP_CMDS[cmd],  "indices": indices})

    return blocks


# ─── Lua data loader ─────────────────────────────────────────────────────────

def _load_lua():
    """Load all resume data via lupa. Returns (bullets, companies, pm_profs, pmm_profs, contact)."""
    from lupa import LuaRuntime

    def _to_py(obj):
        if obj is None:
            return None
        if not hasattr(obj, "items"):
            return obj
        items = list(obj.items())
        if not items:
            return {}
        if all(isinstance(k, int) for k in (k for k, _ in items)):
            return [_to_py(v) for _, v in sorted(items)]
        return {str(k): _to_py(v) for k, v in items}

    lua = LuaRuntime(unpack_returned_tuples=True)

    def load(path):
        with open(path) as f:
            lua.execute(f.read())

    load(os.path.join(DATA_DIR,     "contact.lua"))
    load(os.path.join(DATA_DIR,     "companies.lua"))
    load(os.path.join(INCLUDES_DIR, "proficiencies.lua"))
    load(os.path.join(INCLUDES_DIR, "pmm", "proficiencies.lua"))
    load(os.path.join(DATA_DIR,     "bullets.lua"))

    g = lua.globals()
    return (
        _to_py(g.bullets),
        _to_py(g.experiences),
        _to_py(g.proficiencies),
        _to_py(g.pmm_proficiencies),
        _to_py(g.contact),
    )


# ─── Query helpers (mirror queries.lua) ─────────────────────────────────────

def _get_skill_items(bullets, skill_key):
    result = []
    for b in bullets:
        profs = b.get("proficiencies") or []
        if skill_key not in profs:
            continue
        detail = b.get("proficiency_text") or b.get("experience_text")
        if not detail or detail in ("", "none"):
            continue
        ckey    = b.get("company")
        display = COMPANY_DISPLAY.get(ckey, "") if ckey else ""
        result.append({"company": display, "detail": detail})
    return result


def _get_pmm_skill_items(bullets, skill_key):
    result = []
    for b in bullets:
        profs = b.get("pmm_proficiencies") or []
        if skill_key not in profs:
            continue
        detail = b.get("pmm_proficiency_text") or b.get("pmm_experience_text")
        if not detail:
            continue
        ckey    = b.get("company")
        display = COMPANY_DISPLAY.get(ckey, "") if ckey else ""
        result.append({"company": display, "detail": detail})
    return result


def _get_company_bullets(bullets, company_key):
    return [b["experience_text"] for b in bullets
            if b.get("company") == company_key
            and b.get("experience_text") not in (None, "", "none")]


def _select(items, indices):
    """Pick 1-based indices from a list; empty indices = all items."""
    if not indices:
        return list(items)
    return [items[i - 1] for i in indices if 1 <= i <= len(items)]


# ─── Markdown renderer ────────────────────────────────────────────────────────

def _render_prof_block(skill_meta, items):
    """Render one proficiency block."""
    lines = [f"### {_decode(skill_meta['name'])}"]
    lines.append(_decode(skill_meta["description"]))
    lines.append("")
    for item in items:
        text = _decode(item["detail"])
        if item["company"]:
            lines.append(f"- **{item['company']}:** {text}")
        else:
            lines.append(f"- {text}")
    lines.append("")
    return "\n".join(lines)


def _render_exp_block(company_meta, bullets_list, is_pmm=False):
    """Render one experience block."""
    title      = _decode(company_meta.get("pmm_title" if is_pmm else "title", ""))
    company    = _decode(company_meta.get("company", ""))
    date_start = _decode(company_meta.get("dateStart", ""))
    date_end   = _decode(company_meta.get("dateEnd", ""))
    location   = _decode(company_meta.get("location", ""))
    desc       = _decode(company_meta.get("desc", ""))
    body_key   = "pmm_body" if is_pmm else "body"
    body       = _decode(company_meta.get(body_key) or company_meta.get("body", ""))

    lines = [f"### {title} | {company} | {date_start} \u2013 {date_end}"]
    lines.append(f"{location} \u2014 {desc}")
    lines.append("")
    if body:
        lines.append(body)
        lines.append("")
    for b in bullets_list:
        lines.append(f"- {_decode(b)}")
    if bullets_list:
        lines.append("")
    return "\n".join(lines)


def generate_markdown(tex_basename):
    """
    Generate markdown content for the named resume variant.
    Returns (md_content, output_stem) where output_stem is used for .md/.docx filenames.
    """
    tex_path = os.path.join(RESUMES_DIR, tex_basename + ".tex")
    if not os.path.exists(tex_path):
        raise FileNotFoundError(f"Not found: {tex_path}")

    blocks = parse_tex(tex_path)
    bullets, companies, pm_profs, pmm_profs, contact = _load_lua()

    # Derive the output key (AI, EXP, PMM, etc.)
    key = re.sub(r"^(?:skill-)?resume-", "", tex_basename)
    output_stem = f"Evan Dierlam - Product Manager - Resume - {key}"

    lines = []

    # ── Header ──
    lines += [
        f"# {contact['name']}",
        contact["title"],
        "",
        f"{contact['location']} · {contact['email']} · {contact['phone']} · {contact['linkedin']}",
        "",
        "---",
        "",
    ]

    # ── Proficiency and Experience sections in document order ──
    current_section = None
    for blk in blocks:
        is_prof = blk["type"] in ("pm_prof", "pmm_prof")
        section = "prof" if is_prof else "exp"

        if section != current_section:
            current_section = section
            lines.append("## Proficiencies" if is_prof else "## Experience")
            lines.append("")

        if is_prof:
            if blk["type"] == "pm_prof":
                meta  = pm_profs.get(blk["key"])
                items = _select(_get_skill_items(bullets, blk["key"]), blk["indices"])
            else:
                meta  = pmm_profs.get(blk["key"])
                items = _select(_get_pmm_skill_items(bullets, blk["key"]), blk["indices"])
            if meta and items:
                lines.append(_render_prof_block(meta, items))
        else:
            ckey   = blk["key"]
            is_pmm = blk["type"] == "pmm_exp"
            cmeta  = companies.get(ckey)
            if not cmeta:
                continue
            raw   = _get_company_bullets(bullets, ckey)
            blist = _select(raw, blk["indices"]) if blk["indices"] else []
            lines.append(_render_exp_block(cmeta, blist, is_pmm=is_pmm))

    # ── Education ──
    lines += [
        "## Education",
        "",
        "Sam Houston State University — Huntsville, TX",
        "Bachelor of Arts in Journalism",
        "",
    ]

    return "\n".join(lines), output_stem


# ─── Output writers ───────────────────────────────────────────────────────────

def write_md(content, output_stem):
    path = os.path.join(RESUMES_DIR, output_stem + ".md")
    with open(path, "w") as f:
        f.write(content)
    return path


def write_docx(md_path, output_stem):
    docx_path = os.path.join(RESUMES_DIR, output_stem + ".docx")
    ref_path    = os.path.join(PROJECT_ROOT, "web", "resume-reference.docx")
    filter_path = os.path.join(PROJECT_ROOT, "web", "remove-ids.lua")
    cmd = ["pandoc", md_path, "-o", docx_path, "--lua-filter", filter_path]
    if os.path.exists(ref_path):
        cmd += ["--reference-doc", ref_path]
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        return docx_path
    except FileNotFoundError:
        print("  pandoc not found — skipping .docx", file=sys.stderr)
        return None
    except subprocess.CalledProcessError as e:
        print(f"  pandoc error: {e.stderr.decode()}", file=sys.stderr)
        return None


# ─── CLI ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python generate_md.py <tex-basename>")
        print("  e.g. python generate_md.py skill-resume-AI")
        sys.exit(1)

    # Accept either a bare basename (skill-resume-AI) or an absolute path
    # from LaTeX Workshop's %DOC% variable (/abs/path/to/resumes/skill-resume-AI)
    arg = re.sub(r"\.tex$", "", sys.argv[1])
    basename = os.path.basename(arg)
    content, stem = generate_markdown(basename)

    md_path   = write_md(content, stem)
    docx_path = write_docx(md_path, stem)

    print(f"  .md  → {os.path.basename(md_path)}")
    if docx_path:
        print(f"  .docx → {os.path.basename(docx_path)}")
