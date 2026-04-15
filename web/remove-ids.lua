-- remove-ids.lua: strip heading identifiers so pandoc doesn't create Word bookmarks
function Header(el)
  el.identifier = ""
  return el
end
