# STARL Markup Project

Tag every bullet in `bullets.lua` with the product focus area(s) it demonstrates, enabling fast matching of bullets to job description requirements.

## What is STARL?

An extension of the STAR method (Situation, Task, Action, Result) adding **L** for **Leadership**. The goal here is to categorize bullets by *product focus area* so that when a JD emphasizes a particular capability, the best matching bullets can be surfaced quickly.

## Product Focus Areas

Defined in `sources/Product Focus Areas.md`:

| Key | Focus Area |
|-----|------------|
| `vision` | Product Vision |
| `market` | Market Strategy |
| `roadmap` | Prioritization / Roadmap |
| `discovery` | Discovery (Finding new features) |
| `alignment` | Stakeholder & Customer Management |
| `delivery` | Delivery of Roadmap |
| `analysis` | Analysis |
| `experimentation` | Experimentation |
| `accountability` | Accountability |
| `sme` | Subject Matter Expertise |
| `leadership` | Leadership |
| `customer` | Customer-Centric Approach |

## Proposed Schema Change

Add an optional `focus` array to each bullet record in `bullets.lua`, parallel to `proficiencies`:

```lua
{
  company          = "instapage",
  proficiencies    = { "ML", "Experimentation" },
  focus            = { "delivery", "experimentation" },
  experience_text  = "Launched ML-powered experimentation feature...",
  ...
}
```

## Plan

1. **Finalize focus area keys** — confirm the key list above, add/remove as needed
2. **Add `focus` field to bullets.lua** — tag each bullet with one or more focus area keys
3. **Write query helper** — add `getBulletsForFocus(focus_key)` to `queries.lua`
4. **Update README** — document the new field and query function
5. **Use in targeting** — when matching to a JD, identify which focus areas are emphasized and pull the highest-signal bullets for each

## Files

| File | Role |
|------|------|
| `includes/bullets.lua` | Source data to be tagged |
| `sources/Product Focus Areas.md` | Focus area definitions and JD language examples |
| `includes/queries.lua` | Add `getBulletsForFocus()` here |

## Notes

- `focus` tags are for targeting/matching — they don't drive any resume rendering directly
- A bullet can have multiple focus tags
- Archive-only bullets (`experience_text = "none"`) should still be tagged if relevant — they may be useful for cover letters or interview prep
- The `sources/` directory also has archived resume `.txt` files and a CSV (`Interview structure.xlsx - All stories.csv`) that may have pre-existing story categorization worth reviewing before tagging
