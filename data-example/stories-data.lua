-- stories-data.lua
-- Interview story bank. Company is the primary key, entries are stories within that company.

stories = {

  acmecorp = {
    {
      title   = "Rebuilt onboarding flow",
      context = "Activation rate was dropping as enterprise customer complexity increased.",
      action  = "Ran discovery interviews, identified three key friction points, redesigned the first-run experience.",
      result  = "Activation rate improved 22\\% over two quarters; reduced support ticket volume by 30\\%.",
    },
  },

  widgetco = {
    {
      title   = "Search ranking overhaul",
      context = "Buyers were struggling to find relevant parts; zero-result searches were costing revenue.",
      action  = "Partnered with data science to rebuild the ranking model using behavioral signals.",
      result  = "CTR up 18\\%, zero-result searches down 40\\%, NPS increased by 12 points.",
    },
  },

}
