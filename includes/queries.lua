-- queries.lua
-- Helper functions for querying bullets.lua data.
-- Load this after bullets.lua (and companies/proficiencies metadata) via \directlua{dofile(...)}.

-- Returns experience_text for all bullets matching company_key,
-- excluding archive-only bullets (experience_text == "none").
function getBulletsForCompany(company_key)
  local result = {}
  for _, b in ipairs(bullets) do
    if b.company == company_key and b.experience_text and b.experience_text ~= "" and b.experience_text ~= "none" then
      table.insert(result, b.experience_text)
    end
  end
  return result
end

-- Returns {company, detail} pairs for all bullets tagged with skill_key.
-- Uses proficiency_text if set, falls back to experience_text.
-- Skips bullets where experience_text == "none" and no proficiency_text exists.
-- Handles nil company (personal/independent items).
function getItemsForSkill(skill_key)
  local result = {}
  for _, b in ipairs(bullets) do
    if b.proficiencies then
      for _, s in ipairs(b.proficiencies) do
        if s == skill_key then
          local detail = b.proficiency_text or b.experience_text
          if detail and detail ~= "" and detail ~= "none" then
            local company_name = ""
            if b.company and experiences and experiences[b.company] then
              company_name = experiences[b.company].company
            end
            table.insert(result, {
              company = company_name,
              detail  = detail,
            })
          end
          break
        end
      end
    end
  end
  return result
end

-- Returns pmm_experience_text for all bullets matching company_key tagged with pmm_proficiencies.
-- Skips bullets with no pmm_experience_text.
function getPMMBulletsForCompany(company_key)
  local result = {}
  for _, b in ipairs(bullets) do
    if b.company == company_key and b.pmm_experience_text then
      table.insert(result, b.pmm_experience_text)
    end
  end
  return result
end

-- Returns {company, detail} pairs for all bullets tagged with a PMM skill key.
-- Uses pmm_proficiency_text if set, falls back to pmm_experience_text.
-- Skips bullets with no pmm_proficiencies or no usable PMM text.
function getPMMItemsForSkill(skill_key)
  local result = {}
  for _, b in ipairs(bullets) do
    if b.pmm_proficiencies then
      for _, s in ipairs(b.pmm_proficiencies) do
        if s == skill_key then
          local detail = b.pmm_proficiency_text or b.pmm_experience_text
          if detail then
            local company_name = ""
            if b.company and experiences and experiences[b.company] then
              company_name = experiences[b.company].company
            end
            table.insert(result, {
              company = company_name,
              detail  = detail,
            })
          end
          break
        end
      end
    end
  end
  return result
end

-- Returns the alts array for a specific bullet identified by company + experience_text.
-- Returns an empty table if not found or no alts exist.
function getAltsForBullet(company_key, experience_text)
  for _, b in ipairs(bullets) do
    if b.company == company_key and b.experience_text == experience_text then
      return b.alts or {}
    end
  end
  return {}
end
