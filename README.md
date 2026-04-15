# Resume

LuaLaTeX-based resume system. Resume files select and arrange content blocks; all data lives in Lua includes.

There are two data approaches in parallel — the original (`data.lua`) and a newer unified model (`bullets.lua`). Both are functional; the v2 resumes use the new model.

## Files

### Resume files

| File | Description |
|------|-------------|
| `experience-resume.tex` | Traditional experience-focused resume with bullets |
| `skill-resume-AI.tex` | Skill-based resume, AI/ML focus |
| `skill-resume-API.tex` | Skill-based resume, API/engineering focus |
| `skill-resume-CMS.tex` | Skill-based resume, CMS/content platform focus |
| `skill-resume-PM.tex` | Skill-based PM resume (original data model) |
| `skill-resume-PM-v2.tex` | Skill-based PM resume (unified data model) |

### Includes — original model

| File | Description |
|------|-------------|
| `includes/data.lua` | All content: experience bullets and proficiency items |
| `includes/uselua.tex` | Loads `data.lua` and defines `renderBullets`, `renderItems` helpers |
| `includes/styles.tex` | Formatting commands and block builders (`\expblock`, `\profblock`) |
| `includes/proficiencies.tex` | `\pro*` shorthand commands |
| `includes/experiences.tex` | `\exp*` shorthand commands |
| `includes/header.tex` | Contact header |
| `includes/education.tex` | Education block |

### Includes — unified data model (v2)

| File | Description |
|------|-------------|
| `includes/bullets.lua` | Single source of truth: all bullets with company, proficiency tags, experience text, proficiency text, and alts |
| `includes/queries.lua` | `getBulletsForCompany()`, `getItemsForSkill()`, `getAltsForBullet()` |
| `includes/uselua-bullets.tex` | Loads `bullets.lua` + `queries.lua`; defines `\profblockQ`, `\expblockQ`, and `Q`-suffixed shorthands |

---

## Original Model

Content lives in `includes/data.lua` under two top-level tables:
- `experiences` — job metadata + bullet arrays, keyed by employer
- `proficiencies` — skill metadata + item arrays (company + detail pairs), keyed by skill

### Updating content

**Contact info:** Edit the `contact` table at the top of `data.lua`.

**Updating a job:** Find the job key in `experiences` (e.g. `instapage`, `nerdwallet`). Edit `title`, `company`, `dateStart`, `dateEnd`, `location`, `desc`, `body`, or `bullets`. Bullets are a plain array of strings.

**Adding a new job:** Add an entry to `experiences` in `data.lua`, then add a shorthand in `experiences.tex`:
```latex
\newcommand{\expnewjob}[1][]{\expblock[#1]{newjob}}
```

**Updating a proficiency:** Find the key in `proficiencies` (e.g. `AI`, `ML`). Each item has `company` and `detail`. Leave `company` as `""` to render without a label.

**Adding a new proficiency:** Add an entry to `proficiencies` in `data.lua`, then add a shorthand in `proficiencies.tex`:
```latex
\newcommand{\pronewskill}[1][1,2,3]{\profblock{NewSkill}{#1}}
```

### Creating a resume (original)

1. Copy an existing resume file (e.g. `skill-resume-PM.tex`)
2. Arrange the blocks in the document body
3. Pass bullet/item indices to control what appears:

```latex
\expinstapage[1,2,3,4]     % show bullets 1–4
\expinstapage               % no bullets

\proai[1,2,4]              % show items 1, 2, and 4
\proai                     % show all items (default)
```

---

## Unified Data Model (v2)

Content lives in `includes/bullets.lua` as a flat array of self-contained bullet records. Each record is the single source of truth for one bullet across all views (experience section, proficiency section, targeted variants).

### Bullet record shape

```lua
{
  company          = "instapage",            -- key into experiences table (nil = personal/independent)
  proficiencies    = { "ML", "Experimentation" },  -- drives proficiency view; omit if not proficiency-mapped
  experience_text  = "Launched ML-powered experimentation feature...",  -- canonical experience bullet
  proficiency_text = "Owned development of an experimentation feature...",  -- optional proficiency reframe
  alts = {                                   -- alternate phrasings from archived resumes
    "Launched ML-powered experimentation feature that uses reinforcement learning...",
  },
}
```

- `proficiency_text` falls back to `experience_text` if nil
- `experience_text = "none"` marks proficiency-only or personal bullets (excluded from experience view)
- `company = nil` marks personal/independent items — render without a company label

### Query functions (`queries.lua`)

| Function | Returns |
|----------|---------|
| `getBulletsForCompany(key)` | `experience_text` strings for a company, newest-first, excludes `"none"` |
| `getItemsForSkill(key)` | `{company, detail}` pairs for all bullets tagged with a skill |
| `getAltsForBullet(key, text)` | `alts` array for a specific bullet — use when targeting a role |

### Creating a resume (v2)

1. Copy `skill-resume-PM-v2.tex`
2. Input `uselua.tex` (metadata) and `uselua-bullets.tex` (bullet queries)
3. Use `Q`-suffixed block commands — same index selection as the original:

```latex
\promlQ[1,2,3]         % items 1–3 from getItemsForSkill("ML")
\promlQ                % all items (default)

\expinstapageQ[1,2]    % bullets 1–2 from getBulletsForCompany("instapage")
\expinstapageQ         % no bullets (proficiency-resume default)
```

Available `Q` shorthands: `\provocQ`, `\proanalyticsQ`, `\proexperimentQ`, `\proprototypingQ`, `\proapiQ`, `\proaiQ`, `\promlQ`, `\proragQ`, `\procmsQ`, and `\exp*Q` for all companies.

### Skill keys

Skills with a **proficiency entry** in `proficiencies.lua` — usable in `\profblockQ` / `\pro*Q` shorthands in resume files:

| Key | Name | Shorthand |
|-----|------|-----------|
| `AI` | AI, LLMs, and Agentic Workflows | `\proaiQ` |
| `ML` | Machine Learning | `\promlQ` |
| `Experimentation` | Experimentation | `\proexperimentQ` |
| `Analytics` | Business Analytics | `\proanalyticsQ` |
| `API` | API Development & Integration | `\proapiQ` |
| `Prototyping` | Prototyping | `\proprototypingQ` |
| `RAG` | RAG | `\proragQ` |
| `VoC` | Voice of the Customer / Stakeholder Management | `\provocQ` |
| `CMS` | CMS | `\procmsQ` |
| `SEO` | SEO & Organic Growth | `\proseoQ` |
| `Growth` | Growth | `\progrowthQ` |
| `AdTech` | Ad Tech & MarTech | `\proadtechQ` |
| `Platform` | Platform Product Management | — [need bullets] |
| `Content` | Content & Editorial Product | — [need bullets] |
| `B2B` | B2B | — [need bullets] |
| `Consumer` | Consumer / B2C | — [need bullets] |
| `SaaS` | SaaS | — [need bullets] |

---

## Overriding Styles

All formatting commands in `styles.tex` use `\providecommand` — define before `\input{includes/styles.tex}` to override per-resume:

```latex
\providecommand{\desc}[1]{- #1\vspace{3pt}\par}
\input{includes/styles.tex}
```

Overridable commands: `\grayt`, `\sectiontitle`, `\bullets`, `\citem`, `\proficiency`, `\profdesc`, `\jobtitle`, `\company`, `\location`, `\dates`, `\desc`, `\body`, `\school`, `\degree`.

The block builders (`\profblock`, `\expblock`, `\profblockQ`, `\expblockQ`) are not overridable this way — restyle the formatting commands they call instead.

### Lua helpers
`capfirst(s)` capitalizes the first letter of a string, available in any `\directlua` call:
```latex
\newcommand{\desc}[1]{\textit{\directlua{tex.print(capfirst("#1"))}}\par}
```

---

## Bullets Editor (Web UI)

A local web interface for editing `includes/bullets.lua` — tagging bullets with proficiency
keys, writing PMM text variants, and reviewing alts — without touching the file directly.

### Setup (first time only)

```bash
cd web
pip install -r requirements.txt
```

Requires Python 3 and `lupa` (Lua bridge). If `pip install lupa` fails, install Lua first:

```bash
brew install lua
pip install -r requirements.txt
```

### Launch

```bash
cd web
python app.py
```

Open **http://localhost:5001** in your browser.

> Port 5000 is taken by macOS AirPlay. The server runs on 5001.

### Stop

`Ctrl+C` in the terminal where `app.py` is running.

If it was launched in the background:

```bash
pkill -f "python app.py"
```

### Features

- **Company** filter — radio chips to view one company at a time or all
- **Title** filter — All / PM / PMM (filters by which proficiency tags are present)
- **Fields** filter — tri-state per field (✓ filled / ✗ empty / — ignore): PM Exp, PM Prof, PMM Exp, PMM Prof, PM Tag, PMM Tag
- Inline editing of all text fields with auto-sizing textareas
- PM and PMM proficiency tag management (add / remove)
- Alts panel — expand/collapse, promote alt to `experience_text`
- Per-card Save / Discard, plus Save All
- Backup written to `includes/bullets.lua.bak` before every save
- Card border indicates PMM status: grey (untagged) / orange (partial) / green (complete)

---

## Building

Compile with **LuaLaTeX**. The magic comment on line 1 of each `.tex` file (`% !TEX program = lualatex`) sets this automatically in most editors.
