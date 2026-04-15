-- Unified bullet store
-- Single source of truth for all resume bullet content.
-- Each record is a self-contained document with all variant phrasings embedded.
--
-- Fields:
--   company          : key into companies table (nil = personal/independent)
--   proficiencies    : array of skill keys — drives proficiency section
--   experience_text  : canonical bullet for experience view ("none" = proficiency/archive-only)
--   proficiency_text : optional reframe for proficiency view (falls back to experience_text if nil)
--   alts             : alternate phrasings collected from archived resumes

bullets = {

  -- ============================================================
  -- ACME CORP
  -- ============================================================

  {
    company = "acmecorp",
    proficiencies = { "Roadmap", "Strategy" },
    experience_text = "Defined and executed multi-quarter roadmap for core automation features, aligning priorities with engineering, design, and executive stakeholders.",
    cached_idx = { exp = 1 },
  },

  {
    company = "acmecorp",
    proficiencies = { "Analytics", "Experimentation" },
    experience_text = "Launched A/B testing framework to measure feature adoption, driving a 22\\% improvement in activation rate within two quarters.",
    cached_idx = { exp = 2 },
  },

  {
    company = "acmecorp",
    proficiencies = { "CustomerResearch" },
    experience_text = "Ran 30+ customer discovery interviews to identify top friction points, translating insights into a prioritized backlog and a reduction in churn.",
    cached_idx = { exp = 3 },
  },

  -- ============================================================
  -- WIDGET CO
  -- ============================================================

  {
    company = "widgetco",
    proficiencies = { "Search", "DataResearch" },
    experience_text = "Rebuilt search ranking model in partnership with data science, increasing click-through rate by 18\\% and reducing zero-result searches by 40\\%.",
    cached_idx = { exp = 4 },
  },

  {
    company = "widgetco",
    proficiencies = { "Roadmap" },
    experience_text = "Coordinated cross-functional roadmap across three engineering squads, delivering five major features on time over a 12-month period.",
    cached_idx = { exp = 5 },
  },

  -- ============================================================
  -- STARTUPXYZ
  -- ============================================================

  {
    company = "startupxyz",
    proficiencies = { "Strategy" },
    experience_text = "Defined MVP scope and launch criteria for the core product, shipping the first paid customer within six months of joining.",
    cached_idx = { exp = 6 },
  },

}
