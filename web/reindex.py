"""
reindex.py — Index stability for resume .tex files.

Primary path (used on every bullet save):
    reindex_from_cache(old_bullets, new_bullets)
    — Compares fresh computed indices against cached_idx stored in bullets.lua.
    — Builds per-skill change maps, patches only the tex commands that moved.
    — Returns (updated_bullets_with_new_cache, changes_dict).

Manual/setup path:
    reindex_all()
    — Parses archived PDFs to establish ground-truth indices.
    — Use once when re-establishing ground truth, not on every save.

    seed_cached_indices()
    — Populates cached_idx on every bullet from current computed state.
    — Run once after reindex_all() to initialise the cache.

CLI:
    python reindex.py          # seed cached indices from current state
    python reindex.py --pdf    # re-establish from PDFs, then seed
"""

import os
import re
import fitz  # pymupdf
from lua_parser import read_bullets, lua_serialize

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RESUMES_DIR  = os.path.join(PROJECT_ROOT, "resumes")
BULLETS_PATH = os.path.join(PROJECT_ROOT, "includes", "bullets.lua")

# ─── Constants ───────────────────────────────────────────────────────────────

SKILL_COMMANDS = {
    "propmAiQ":          "AI",
    "propmMlQ":          "ML",
    "propmExperimentQ":  "Experimentation",
    "propmAnalyticsQ":   "Analytics",
    "propmApiQ":         "API",
    "propmVoCQ":         "VoC",
    "propmPrototypingQ": "Prototyping",
    "propmCmsQ":         "CMS",
    "propmSeoQ":         "SEO",
    "propmGrowthQ":      "Growth",
    "propmAdtechQ":      "AdTech",
    "propmRagQ":         "RAG",
}
SKILL_CMD_FOR = {v: k for k, v in SKILL_COMMANDS.items()}

EXP_COMMANDS = {
    "instapage":   "expinstapageQ",
    "nerdwallet":  "expnerdwalletQ",
    "stubhub":     "expstubhubQ",
    "aenetworks":  "expaenetworksQ",
    "adweek":      "expadweekQ",
    "prometheus":  "expprometheusQ",
    "mediabistro": "expmediabistroQ",
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

PDF_TEX_PAIRS = [
    ("Evan Dierlam - Product Manager - Resume - AI.pdf",  "skill-resume-AI.tex"),
    ("Evan Dierlam - Product Manager - Resume - API.pdf", "skill-resume-API.tex"),
    ("Evan Dierlam - Product Manager - Resume - CMS.pdf", "skill-resume-CMS.tex"),
    ("Evan Dierlam - Product Manager - Resume - PM.pdf",  "skill-resume-PM.tex"),
    ("Evan Dierlam - Product Manager - Resume - EXP.pdf", "resume-EXP.tex"),
]

BULLET_CHAR = "ਭ"

# ─── Index computation (mirrors queries.lua) ─────────────────────────────────

def compute_all_indices(bullets):
    """
    For every bullet, compute its current 1-based position in each relevant
    query result.  Returns a list of dicts (parallel to bullets):

        {"AI": 2, "Prototyping": 4, "exp": 5}

    Keys are skill keys for proficiency queries; "exp" is the experience
    position within getBulletsForCompany.  A key is absent when the bullet
    doesn't qualify for that query.
    """
    # Build ordered lists of qualifying global indices per skill
    skill_order  = {}   # skill_key → [global_i, ...]
    exp_order    = {}   # company_key → [global_i, ...]

    for i, b in enumerate(bullets):
        for skill in (b.get("proficiencies") or []):
            detail = b.get("proficiency_text") or b.get("experience_text")
            if detail and detail not in ("", "none"):
                skill_order.setdefault(skill, []).append(i)

        ckey = b.get("company")
        exp  = b.get("experience_text")
        if ckey and exp and exp not in ("", "none"):
            exp_order.setdefault(ckey, []).append(i)

    # Build per-bullet index dicts
    # Pre-index lists for O(1) lookup
    skill_pos = {skill: {gi: pos + 1 for pos, gi in enumerate(lst)}
                 for skill, lst in skill_order.items()}
    exp_pos   = {ckey:  {gi: pos + 1 for pos, gi in enumerate(lst)}
                 for ckey, lst  in exp_order.items()}

    result = []
    for i, b in enumerate(bullets):
        idx = {}
        for skill in (b.get("proficiencies") or []):
            p = skill_pos.get(skill, {}).get(i)
            if p is not None:
                idx[skill] = p
        ckey = b.get("company")
        if ckey:
            p = exp_pos.get(ckey, {}).get(i)
            if p is not None:
                idx["exp"] = p
        result.append(idx)

    return result


# ─── Cache-based reindex (primary path) ──────────────────────────────────────

def _build_change_maps(old_bullets, fresh_indices):
    """
    Diff fresh computed indices against cached_idx stored in old_bullets.
    Returns {dimension_key: {old_pos: new_pos_or_None}} where dimension_key
    is a skill key or "exp:<company_key>".
    """
    change_maps = {}

    for i, (old_b, new_idx) in enumerate(zip(old_bullets, fresh_indices)):
        if not isinstance(old_b, dict):
            continue
        old_idx = old_b.get("cached_idx") or {}

        all_dims = set(old_idx) | set(new_idx)
        for dim in all_dims:
            old_pos = old_idx.get(dim)
            new_pos = new_idx.get(dim)
            if old_pos == new_pos:
                continue
            # Determine change-map key: skills use the skill key,
            # experience uses "exp:<company_key>"
            if dim == "exp":
                ckey = old_bullets[i].get("company")
                map_key = f"exp:{ckey}" if ckey else None
            else:
                map_key = dim  # skill key
            if map_key:
                change_maps.setdefault(map_key, {})[old_pos] = new_pos

    return change_maps


def _remap_index_list(old_indices, change_map):
    """
    Apply change_map to a list of 1-based indices.
    Drops indices that map to None (bullet removed from skill).
    Preserves display order, deduplicates.
    """
    seen = set()
    result = []
    for idx in old_indices:
        new = change_map.get(idx, idx)   # unmapped entries stay the same
        if new is not None and new not in seen:
            result.append(new)
            seen.add(new)
    return result


def _find_tex_files():
    """Return all .tex paths under RESUMES_DIR."""
    return [
        os.path.join(RESUMES_DIR, f)
        for f in os.listdir(RESUMES_DIR)
        if f.endswith(".tex")
    ]


def _apply_change_maps(change_maps):
    """
    For each changed dimension, scan only tex files that reference that command
    and remap indices.  Returns {tex_name: {cmd: (old_list, new_list)}}.
    """
    tex_files = _find_tex_files()
    all_changes = {}

    for map_key, change_map in change_maps.items():
        if map_key.startswith("exp:"):
            ckey = map_key[4:]
            cmd  = EXP_COMMANDS.get(ckey)
        else:
            cmd = SKILL_CMD_FOR.get(map_key)
        if not cmd:
            continue

        pattern = re.compile(r"(\\%s)\[([\d,\s]+)\]" % re.escape(cmd))

        for tex_path in tex_files:
            with open(tex_path) as f:
                content = f.read()
            if cmd not in content:
                continue

            original = content

            def do_remap(m, _map=change_map, _cmd=cmd):
                old_list = [int(x.strip()) for x in m.group(2).split(",") if x.strip()]
                new_list = _remap_index_list(old_list, _map)
                return m.group(1) + "[" + ",".join(str(i) for i in new_list) + "]"

            content = pattern.sub(do_remap, content)

            if content != original:
                tex_name = os.path.basename(tex_path)
                # Record old vs new for the report
                for m_old, m_new in zip(
                    pattern.finditer(original), pattern.finditer(content)
                ):
                    old_list = [int(x.strip()) for x in m_old.group(2).split(",") if x.strip()]
                    new_list = [int(x.strip()) for x in m_new.group(2).split(",") if x.strip()]
                    if old_list != new_list:
                        all_changes.setdefault(tex_name, {})[cmd] = (old_list, new_list)

                with open(tex_path, "w") as f:
                    f.write(content)

    return all_changes


def reindex_from_cache(old_bullets, new_bullets):
    """
    Primary reindex path — no PDF parsing needed.

    1. Compute fresh indices for new_bullets.
    2. Diff against cached_idx in old_bullets.
    3. Build per-dimension change maps; patch only affected tex commands.
    4. Attach updated cached_idx to new_bullets.

    Returns (updated_bullets, changes_dict).
    changes_dict: {tex_name: {cmd: (old_indices, new_indices)}}
    """
    fresh = compute_all_indices(new_bullets)
    change_maps = _build_change_maps(old_bullets, fresh)
    changes = _apply_change_maps(change_maps) if change_maps else {}

    # Inject updated cached_idx into new bullets
    updated = []
    for b, idx in zip(new_bullets, fresh):
        updated.append({**b, "cached_idx": idx} if idx else {**b})

    return updated, changes


# ─── Seed (one-time initialisation) ──────────────────────────────────────────

def seed_cached_indices():
    """
    Populate cached_idx on every bullet from the current computed state and
    write bullets.lua.  Run once after reindex_all() to initialise the cache.
    Returns count of bullets updated.
    """
    bullets = read_bullets()
    fresh   = compute_all_indices(bullets)
    updated = [{**b, "cached_idx": idx} if idx else {**b}
               for b, idx in zip(bullets, fresh)]

    with open(BULLETS_PATH, "w") as f:
        f.write(lua_serialize(updated))

    return sum(1 for idx in fresh if idx)


# ─── PDF-based reindex (manual / ground-truth restore) ───────────────────────

PROFICIENCY_NAMES = {
    "AI, LLMs, and Agentic Workflows":               "AI",
    "Machine Learning":                              "ML",
    "Experimentation":                               "Experimentation",
    "Business Analytics":                            "Analytics",
    "API Development & Integration":                 "API",
    "Voice of the Customer / Stakeholder Management":"VoC",
    "Prototyping":                                   "Prototyping",
    "RAG":                                           "RAG",
    "CMS":                                           "CMS",
    "SEO & Organic Growth":                          "SEO",
    "Ad Tech & MarTech":                             "AdTech",
    "Platform Product Management":                   "Platform",
    "Content & Editorial Product":                   "Content",
    "B2B":                                           "B2B",
    "Consumer / B2C":                                "Consumer",
    "SaaS":                                          "SaaS",
    "Growth":                                        "Growth",
}


def _decode_latex(text):
    text = text.replace("\\%", "%").replace("\\$", "$").replace("\\&", "&")
    text = text.replace("\\textemdash", "\u2014").replace("\\textendash", "\u2013")
    text = re.sub(r"\\[a-zA-Z]+\b", " ", text)
    text = re.sub(r"\\(.)", r"\1", text)
    return re.sub(r"\s+", " ", text).strip()


def _norm(text):
    return _decode_latex(text).lower()


def _similarity(a, b):
    from difflib import SequenceMatcher
    return SequenceMatcher(None, _norm(a), _norm(b)).ratio()


def _get_items_for_skill(bullets, skill_key):
    result = []
    for b in bullets:
        profs = b.get("proficiencies") or []
        if isinstance(profs, str):
            profs = [profs]
        if skill_key not in profs:
            continue
        detail = b.get("proficiency_text") or b.get("experience_text")
        if not detail or detail in ("", "none"):
            continue
        ckey    = b.get("company")
        display = next((d for d, k in COMPANY_DISPLAY.items() if k == ckey), "") if ckey else ""
        result.append({"company": display, "detail": detail})
    return result


def _get_bullets_for_company(bullets, company_key):
    return [b["experience_text"] for b in bullets
            if b.get("company") == company_key
            and b.get("experience_text") not in (None, "", "none")]


def _collect_bullets(lines):
    out, current = [], None
    for line in lines:
        if line.startswith(BULLET_CHAR):
            if current is not None:
                out.append(current)
            current = line[len(BULLET_CHAR):].strip()
        elif current is not None and line.strip():
            current += " " + line.strip()
    if current is not None:
        out.append(current)
    return out


def _extract_pdf_text(pdf_path):
    doc = fitz.open(pdf_path)
    return "\n".join(doc[i].get_text() for i in range(len(doc)))


def _parse_proficiency_sections(pdf_text):
    lines = pdf_text.splitlines()
    prof_start = exp_start = None
    for i, line in enumerate(lines):
        if line.strip() == "PROFICIENCIES" and prof_start is None:
            prof_start = i
        elif line.strip() == "EXPERIENCE" and prof_start is not None:
            exp_start = i
            break
    if prof_start is None:
        return {}
    section = lines[prof_start + 1: exp_start]

    blocks, current_key, current_lines = [], None, []
    for line in section:
        stripped = line.strip()
        if stripped in PROFICIENCY_NAMES:
            if current_key:
                blocks.append((current_key, current_lines))
            current_key, current_lines = PROFICIENCY_NAMES[stripped], []
        elif current_key is not None:
            current_lines.append(line)
    if current_key:
        blocks.append((current_key, current_lines))

    result = {}
    for skill_key, block_lines in blocks:
        parsed = []
        for text in _collect_bullets(block_lines):
            company, body = "", text
            for display_name in COMPANY_DISPLAY:
                if text.startswith(display_name + ": "):
                    company, body = display_name, text[len(display_name) + 2:]
                    break
            parsed.append((company, body.strip()))
        result[skill_key] = parsed
    return result


def _parse_experience_sections(pdf_text):
    lines = pdf_text.splitlines()
    exp_start = edu_start = None
    for i, line in enumerate(lines):
        if line.strip() == "EXPERIENCE" and exp_start is None:
            exp_start = i
        elif line.strip() == "EDUCATION" and exp_start is not None:
            edu_start = i
            break
    if exp_start is None:
        return {}
    section = lines[exp_start + 1: edu_start]

    blocks, current_key, current_lines = [], None, []
    for line in section:
        matched = False
        for display_name, ckey in COMPANY_DISPLAY.items():
            if line.strip().startswith(display_name + " ("):
                if current_key:
                    blocks.append((current_key, current_lines))
                current_key, current_lines = ckey, []
                matched = True
                break
        if not matched and current_key is not None:
            current_lines.append(line)
    if current_key:
        blocks.append((current_key, current_lines))

    return {ckey: _collect_bullets(blines) for ckey, blines in blocks}


def _match_to_indices(pdf_bullets, candidates, is_proficiency):
    from difflib import SequenceMatcher
    indices = []
    for item in pdf_bullets:
        text = item[1] if is_proficiency else item
        best_idx, best_score = None, 0.0
        for i, cand in enumerate(candidates):
            cand_text = cand["detail"] if is_proficiency else cand
            score = _similarity(text, cand_text)
            if score > best_score:
                best_score, best_idx = score, i + 1
        if best_idx is not None and best_score >= 0.6 and best_idx not in indices:
            indices.append(best_idx)
    return indices


def _patch_tex(tex_path, updates):
    with open(tex_path) as f:
        original = content = f.read()
    for cmd, new_indices in updates.items():
        new_str = ",".join(str(i) for i in new_indices)
        content = re.sub(
            r"(\\%s)\[[\d,\s]+\]" % re.escape(cmd),
            lambda m, s=new_str, c=cmd: "\\" + c + "[" + s + "]",
            content,
        )
    if content != original:
        with open(tex_path, "w") as f:
            f.write(content)
    return content != original


def reindex_resume(pdf_path, tex_path, bullets):
    pdf_text = _extract_pdf_text(pdf_path)
    is_exp   = os.path.basename(tex_path) == "resume-EXP.tex"
    updates  = {}

    if is_exp:
        for ckey, cmd in EXP_COMMANDS.items():
            pdf_bullets = _parse_experience_sections(pdf_text).get(ckey)
            if not pdf_bullets:
                continue
            candidates = _get_bullets_for_company(bullets, ckey)
            indices    = _match_to_indices(pdf_bullets, candidates, is_proficiency=False)
            if indices:
                updates[cmd] = indices
    else:
        for skill_key, pdf_items in _parse_proficiency_sections(pdf_text).items():
            candidates = _get_items_for_skill(bullets, skill_key)
            indices    = _match_to_indices(pdf_items, candidates, is_proficiency=True)
            cmd        = SKILL_CMD_FOR.get(skill_key)
            if cmd and indices:
                updates[cmd] = indices

    with open(tex_path) as f:
        tex_content = f.read()

    changes = {}
    for cmd, new_idx in updates.items():
        m = re.search(r"\\%s\[([\d,\s]+)\]" % re.escape(cmd), tex_content)
        if m:
            old_idx = [int(x.strip()) for x in m.group(1).split(",") if x.strip()]
            if old_idx != new_idx:
                changes[cmd] = (old_idx, new_idx)

    if updates:
        _patch_tex(tex_path, updates)
    return changes


def reindex_all():
    """PDF-based ground-truth restore.  Patches tex files; does NOT update cache."""
    bullets = read_bullets()
    summary = {}
    for pdf_name, tex_name in PDF_TEX_PAIRS:
        pdf_path = os.path.join(RESUMES_DIR, pdf_name)
        tex_path = os.path.join(RESUMES_DIR, tex_name)
        if not os.path.exists(pdf_path) or not os.path.exists(tex_path):
            continue
        changes = reindex_resume(pdf_path, tex_path, bullets)
        if changes:
            summary[tex_name] = changes
    return summary


# ─── CLI ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    if "--pdf" in sys.argv:
        print("Re-establishing indices from PDFs…")
        changes = reindex_all()
        if changes:
            for tex_name, cmds in changes.items():
                print(f"\n{tex_name}:")
                for cmd, (old, new) in cmds.items():
                    print(f"  \\{cmd}: [{','.join(str(i) for i in old)}] → [{','.join(str(i) for i in new)}]")
        else:
            print("  No changes.")
        print()

    print("Seeding cached indices…")
    n = seed_cached_indices()
    print(f"  {n} bullets updated.")
