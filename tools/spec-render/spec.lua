-- Pandoc Lua filter for the OMP working spec.
--
-- 1. Reads the title, stage, version and date from the document itself
--    (the H1 and the "**Editors' draft v0.5, 2026-11-06**" line), so the
--    file name never has to carry them.
-- 2. Turns status markers such as [agreed] or [proposed, 10-14] into
--    styled spans.
-- 3. Marks RFC 2119 keywords (MUST, SHOULD NOT, MAY, ...).
-- 4. Rewrites relative links to absolute GitHub links, so a downloaded
--    copy still resolves them.
-- 5. Wraps tables so wide ones scroll on small screens.

local stringify = pandoc.utils.stringify

-- Order matters: the first prefix that matches wins.
local STATUS = {
  { "no objection", "agreed" },
  { "agreed", "agreed" },
  { "proposed", "proposed" },
  { "open", "open" },
  { "editors", "editors" },
  { "deferred", "quiet" },
  { "parked", "quiet" },
  { "discussed", "quiet" },
}

local KEYWORDS = {
  MUST = true, SHOULD = true, MAY = true, SHALL = true,
  REQUIRED = true, RECOMMENDED = true, OPTIONAL = true,
}

local MONTHS = {
  "January", "February", "March", "April", "May", "June", "July",
  "August", "September", "October", "November", "December",
}

local meta_out = {}
local repo_url, source_dir, ref

local function status_kind(text)
  local lower = text:lower()
  for _, pair in ipairs(STATUS) do
    if lower:sub(1, #pair[1]) == pair[1] then
      return pair[2]
    end
  end
end

local function long_date(iso)
  local y, m, d = iso:match("^(%d%d%d%d)%-(%d%d)%-(%d%d)$")
  if not y then return iso end
  return string.format("%s %d, %s", MONTHS[tonumber(m)], tonumber(d), y)
end

-- Collapse "a/b/../c" style paths.
local function resolve(dir, target)
  local parts = {}
  for seg in (dir .. "/" .. target):gmatch("[^/]+") do
    if seg == ".." then
      table.remove(parts)
    elseif seg ~= "." then
      table.insert(parts, seg)
    end
  end
  return table.concat(parts, "/")
end

-- Find "[status ...]" runs that pandoc split across Str and Space nodes.
local function mark_status(inlines)
  local out = pandoc.Inlines({})
  local i = 1
  while i <= #inlines do
    local el = inlines[i]
    local done = false
    if el.t == "Str" and el.text:sub(1, 1) == "[" then
      local buf, j = {}, i
      while j <= #inlines and j < i + 16 do
        local cur = inlines[j]
        if cur.t == "Str" then
          table.insert(buf, cur.text)
          if cur.text:find("]", 1, true) then break end
        elseif cur.t == "Space" then
          table.insert(buf, " ")
        else
          break
        end
        j = j + 1
      end
      local inner, trail = table.concat(buf):match("^%[([^%]]+)%](.*)$")
      local kind = inner and status_kind(inner)
      if kind then
        -- "proposed, 10-14" -> word "proposed" + note ", 10-14", so the
        -- contents sidebar can show the word alone.
        local word, sep, note = inner:match("^([^,;]+)([,;]%s*)(.+)$")
        local parts = { pandoc.Span(pandoc.Inlines(word or inner), { class = "st-word" }) }
        if note then
          table.insert(parts, pandoc.Span(pandoc.Inlines(sep), { class = "st-sep" }))
          table.insert(parts, pandoc.Span(pandoc.Inlines(note), { class = "st-note" }))
        end
        out:insert(pandoc.Span(parts, { class = "st st-" .. kind }))
        if trail ~= "" then out:insert(pandoc.Str(trail)) end
        i = j + 1
        done = true
      end
    end
    if not done then
      out:insert(el)
      i = i + 1
    end
  end
  return out
end

-- Wrap MUST, MUST NOT, SHOULD, SHOULD NOT, MAY and friends.
local function mark_keywords(inlines)
  local out = pandoc.Inlines({})
  local i = 1
  while i <= #inlines do
    local el = inlines[i]
    local word, trail = "", ""
    if el.t == "Str" then
      word, trail = el.text:match("^(%u+)(%p*)$")
    end
    if word and KEYWORDS[word] then
      local text = word
      local nxt, after = inlines[i + 1], inlines[i + 2]
      if trail == "" and (word == "MUST" or word == "SHOULD" or word == "SHALL")
          and nxt and nxt.t == "Space" and after and after.t == "Str" then
        local w2, t2 = after.text:match("^(NOT)(%p*)$")
        if w2 then
          text = word .. " NOT"
          trail = t2
          i = i + 2
        end
      end
      out:insert(pandoc.Span(pandoc.Inlines(text), { class = "kw" }))
      if trail ~= "" then out:insert(pandoc.Str(trail)) end
    else
      out:insert(el)
    end
    i = i + 1
  end
  return out
end

local function Inlines(inlines)
  return mark_keywords(mark_status(inlines))
end

local function Link(link)
  local t = link.target
  if repo_url and ref and not t:match("^%a[%w+.-]*:") and not t:match("^#") then
    local path, frag = t:match("^([^#]*)(.*)$")
    link.target = string.format("%s/blob/%s/%s%s", repo_url, ref,
      resolve(source_dir, path), frag)
  end
  return link
end

-- Header text without status pills, for labelling cells on small screens.
local function plain_label(cell)
  local copy = pandoc.Blocks(cell.contents):walk({
    Span = function(s)
      if s.classes:includes("st") then return {} end
    end,
  })
  return stringify(copy):gsub("%s+$", "")
end

local function Table(tbl)
  local labels = {}
  local head = tbl.head.rows[1]
  if head then
    for i, cell in ipairs(head.cells) do labels[i] = plain_label(cell) end
  end
  for _, body in ipairs(tbl.bodies) do
    for _, row in ipairs(body.body) do
      for i, cell in ipairs(row.cells) do
        if labels[i] and labels[i] ~= "" then
          cell.attributes["data-label"] = labels[i]
        end
        cell.contents = { pandoc.Div(cell.contents, { class = "cv" }) }
      end
    end
  end
  return pandoc.Div({ tbl }, { class = "table-wrap" })
end

local function Pandoc(doc)
  local blocks = doc.blocks
  -- Title from the first H1, split "Series: Title".
  if blocks[1] and blocks[1].t == "Header" and blocks[1].level == 1 then
    local full = stringify(blocks[1].content)
    local series, title = full:match("^(.-):%s+(.+)$")
    meta_out.series = series or ""
    meta_out.doctitle = title or full
    meta_out.pagetitle = full
    meta_out.title = full
    blocks:remove(1)
  end
  -- Stage, version and date from the first bold lead-in.
  for idx, blk in ipairs(blocks) do
    if blk.t == "Para" and blk.content[1] and blk.content[1].t == "Strong" then
      local lead = stringify(blk.content[1])
      local stage, version, date = lead:match("^(.-)%s+(v[%d%.]+),%s*(%d%d%d%d%-%d%d%-%d%d)$")
      if stage then
        meta_out.stage, meta_out.version, meta_out.date = stage, version, date
        meta_out.date_long = long_date(date)
        -- Drop the lead-in and the ". " after it; keep the rest as the lede.
        local rest = pandoc.Inlines({})
        for k = 2, #blk.content do rest:insert(blk.content[k]) end
        while rest[1] and (rest[1].t == "Space" or
            (rest[1].t == "Str" and rest[1].text:match("^%p+$"))) do
          rest:remove(1)
        end
        blocks[idx] = pandoc.Div({ pandoc.Para(rest) }, { class = "lede" })
        break
      end
    end
    if idx > 5 then break end
  end
  for k, v in pairs(meta_out) do doc.meta[k] = v end

  -- A tag build must match the version written in the document.
  local expected = doc.meta.expected_version and stringify(doc.meta.expected_version) or ""
  if expected ~= "" and expected ~= meta_out.version then
    error(string.format("Tag %s does not match the document version %s",
      expected, tostring(meta_out.version)))
  end
  return doc
end

local function Meta(meta)
  repo_url = meta.repo_url and stringify(meta.repo_url) or nil
  ref = meta.build_commit and stringify(meta.build_commit) or nil
  source_dir = meta.source_path and pandoc.path.directory(stringify(meta.source_path)) or "."
  if ref == "" then ref = nil end
end

return {
  { Meta = Meta },
  { Inlines = Inlines, Link = Link, Table = Table },
  { Pandoc = Pandoc },
}
