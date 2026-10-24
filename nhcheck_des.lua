-- Vérification d'un niveau avec le vrai Lua, sans le jeu.
--
-- Usage : lua nhcheck_des.lua donnees.lua nhlib.lua niveau.lua
--   donnees.lua : écrit par nhmapedit (listes de monstres, d'objets et de
--                 pièges, définies dans la table DATA) ;
--   nhlib.lua   : bibliothèque de NetHack (percent, shuffle…), ou « - ».
--
-- Le script du niveau est exécuté avec une bibliothèque « des » factice
-- qui contrôle les paramètres. Chaque problème est écrit sur une ligne :
--   <gravité> ligne <n> : <message>     (gravité : ! erreur, ? douteux)

local datafile, nhlibfile, levelfile = arg[1], arg[2], arg[3]
dofile(datafile)

local function set(list)
   local s = {}
   for _, v in ipairs(list) do s[v] = true end
   return s
end

local MONSTERS = set(DATA.monsters)
local OBJECTS = set(DATA.objects)
local TRAPS = set(DATA.traps)
local FLAGS = set({ "noteleport", "hardfloor", "nommap", "shortsighted",
   "arboreal", "mazelevel", "shroud", "graveyard", "icedpools", "corrmaze",
   "premapped", "sokoban", "solidify", "inaccessibles", "noflip", "noflipx",
   "noflipy", "hot", "cold", "temperate", "nomongen", "nodeathdrops",
   "noautosearch", "fumaroles", "stormy" })
local STYLES = set({ "solidfill", "mazegrid", "maze", "rogue", "mines",
   "swamp" })
local DOORS = set({ "random", "open", "closed", "locked", "nodoor",
   "broken", "secret" })
local ALIGNS = set({ "random", "law", "neutral", "chaos", "noalign",
   "coaligned", "noncoaligned", "align[0]", "align[1]", "align[2]" })
local ALTARS = set({ "altar", "shrine", "sanctum" })
local ENGRAVINGS = set({ "dust", "engrave", "burn", "mark", "blood" })
local MON_KEYS = set({ "id", "class", "x", "y", "coord", "peaceful",
   "asleep", "name", "female", "invisible", "cancelled", "revived",
   "avenge", "fleeing", "blinded", "paralyzed", "stunned", "confused",
   "waiting", "m_lev_adj", "tail", "group", "adjacentok", "ignorewater",
   "countbirth", "appear_as", "inventory", "keep_default_invent",
   "montype", "seentraps", "dead", "align" })
local OBJ_KEYS = set({ "id", "class", "spe", "buc", "name", "quantity",
   "buried", "lit", "eroded", "locked", "trapped", "trap_known",
   "recharged", "greased", "broken", "achievement", "x", "y", "coord",
   "montype", "historic", "male", "female", "laid_by_you", "contents",
   "corpsenm", "material", "erodeproof", "nocorpse" })

local problems = 0

local function where()
   -- première fonction appelante qui vient du fichier du niveau
   for lvl = 2, 30 do
      local info = debug.getinfo(lvl, "Sl")
      if not info then break end
      if info.short_src and info.short_src:find(levelfile, 1, true)
         and info.currentline > 0 then
         return info.currentline
      end
   end
   return 0
end

local function report(sev, fmt, ...)
   problems = problems + 1
   io.write(string.format("%s ligne %d : %s\n", sev, where(),
                          string.format(fmt, ...)))
end

-- Objet qui accepte tout : index, appel, opérateurs (sélections,
-- objets, monstres renvoyés par des.*)
local any
local function coord_table()
   return setmetatable({ x = 1, y = 1, 1, 1 }, getmetatable(any))
end
local anymt = {
   __index = function(t, k)
      if k == "numpoints" then return function() return 0 end end
      if k == "rndcoord" then return coord_table end
      if k == "x" or k == "y" then return 1 end
      return any
   end,
   __call = function() return any end,
   __add = function() return any end, __sub = function() return any end,
   __band = function() return any end, __bor = function() return any end,
   __bxor = function() return any end, __unm = function() return any end,
   __mul = function() return any end, __div = function() return any end,
   __mod = function() return any end, __idiv = function() return any end,
   __pow = function() return any end,
   __len = function() return 0 end,
   __concat = function(a, b) return tostring(a) .. tostring(b) end,
   __tostring = function() return "?" end,
   __eq = function() return false end,
   __lt = function() return false end, __le = function() return true end,
}
any = setmetatable({}, anymt)

-- Bouchons des bibliothèques du jeu
nh = setmetatable({
   rn2 = function(n) return 0 end,
   random = function(a, b) return a or 0 end,
   level_difficulty = function() return 1 end,
   is_genocided = function() return false end,
   debug_themerm = function() return nil end,
   gettext = function(s) return s end,
   pline = function() end,
   stairways = function() return {} end,
}, { __index = function() return function() return any end end })

selection = setmetatable({}, {
   __index = function()
      return function()
         local s = setmetatable({}, anymt)
         return s
      end
   end,
   __call = function() return setmetatable({}, anymt) end,
})
local selmt = getmetatable(selection)

-- constantes du jeu (src/nhlua.c)
nhc = setmetatable({ COLNO = 80, ROWNO = 21 },
                   { __index = function() return 0 end })
u = setmetatable({ role = "", race = "", gender = "", align = "",
   alignment = "" }, { __index = function() return 0 end })
obj = setmetatable({}, { __index = function() return function() return any end end })

-- Contrôles communs
local function table_arg(fname, args)
   if type(args[1]) == "table" then return args[1] end
   return nil
end

local function check_keys(fname, t, keys)
   for k, _ in pairs(t) do
      if type(k) == "string" and not keys[k] then
         report("?", "des.%s : paramètre inconnu « %s »", fname, k)
      end
   end
end

local function run_function(f, ...)
   if type(f) == "function" then f(...) end
end

local function check_monster(id)
   if type(id) == "string" and #id > 1 and not MONSTERS[id:lower()] then
      report("!", "monstre inconnu : %s", id)
   end
end

local function check_object(id)
   if type(id) == "string" and #id > 1 and not OBJECTS[id:lower()] then
      report("!", "objet inconnu : %s", id)
   end
end

local function check_choice(fname, what, value, valid)
   if type(value) == "string" and not valid[value] then
      report("!", "des.%s : %s « %s » invalide", fname, what, value)
   end
end

-- La bibliothèque des factice
local D = {}

function D.level_init(t)
   if type(t) == "table" and t.style then
      check_choice("level_init", "style", t.style, STYLES)
   end
end

function D.level_flags(...)
   for _, f in ipairs({ ... }) do
      if not FLAGS[f] then
         report("!", "des.level_flags : drapeau inconnu « %s »", tostring(f))
      end
   end
end

function D.map(t)
   if type(t) == "table" then run_function(t.contents, any) end
   return any
end

function D.room(t)
   if type(t) == "table" then run_function(t.contents, any) end
   return any
end

function D.monster(...)
   local args = { ... }
   local t = table_arg("monster", args)
   if t then
      check_keys("monster", t, MON_KEYS)
      check_monster(t.id)
      run_function(t.inventory, any)
   elseif type(args[1]) == "string" then
      check_monster(args[1])
   end
   return any
end

function D.object(...)
   local args = { ... }
   local t = table_arg("object", args)
   if t then
      check_keys("object", t, OBJ_KEYS)
      check_object(t.id)
      -- montype : monstre d'une statue ou d'un cadavre ; « spinach »
      -- pour une boîte d'épinards
      if t.montype ~= "spinach" then check_monster(t.montype) end
      check_choice("object", "buc", t.buc, set({ "random", "blessed",
         "uncursed", "cursed", "not-cursed", "not-uncursed",
         "not-blessed" }))
      run_function(t.contents, any)
   elseif type(args[1]) == "string" then
      check_object(args[1])
   end
   return any
end

function D.trap(...)
   local args = { ... }
   local ty = args[1]
   if type(ty) == "table" then ty = ty.type end
   if type(ty) == "string" and not TRAPS[ty] then
      report("!", "piège inconnu : %s", ty)
   end
   return any
end

local function stair(fname)
   return function(...)
      local args = { ... }
      local d = args[1]
      if type(d) == "table" then d = d.dir end
      if type(d) == "string" and d ~= "up" and d ~= "down" then
         report("!", "des.%s : direction « %s » invalide", fname, d)
      end
   end
end
D.stair = stair("stair")
D.ladder = stair("ladder")

function D.altar(t)
   if type(t) == "table" then
      check_choice("altar", "alignement", t.align, ALIGNS)
      check_choice("altar", "type", t.type, ALTARS)
   end
end

function D.door(...)
   local args = { ... }
   local s = args[1]
   if type(s) == "table" then s = s.state end
   check_choice("door", "état", s, DOORS)
end

function D.engraving(...)
   local args = { ... }
   local ty = args[2]
   if type(args[1]) == "table" and args[1].type then ty = args[1].type end
   check_choice("engraving", "type", ty, ENGRAVINGS)
end

-- Fonctions reconnues sans contrôle particulier
for _, name in ipairs({ "region", "levregion", "teleport_region",
   "non_diggable", "non_passwall", "replace_terrain", "terrain",
   "corridor", "random_corridors", "mazewalk", "gold", "grave",
   "drawbridge", "feature", "reset_level", "finalize_level", "wallify",
   "message", "exclusion", "mineralize", "gas_cloud", "wall_property",
   "set_record_name", "get_record_name" }) do
   D[name] = function() return any end
end

des = setmetatable(D, { __index = function(_, k)
   return function()
      report("!", "fonction inconnue : des.%s", tostring(k))
      return any
   end
end })

-- Exécution
if nhlibfile ~= "-" then
   local ok, err = pcall(dofile, nhlibfile)
   if not ok then
      io.write("? ligne 0 : nhlib.lua non chargé (" .. tostring(err) .. ")\n")
   end
end

local chunk, err = loadfile(levelfile)
if not chunk then
   io.write("! " .. err:gsub("^[^:]*:(%d+):", "ligne %1 :") .. "\n")
   os.exit(1)
end
local ok, rerr = pcall(chunk)
if not ok then
   local msg = tostring(rerr)
   local line = msg:match(":(%d+):")
   msg = msg:gsub("^[^:]*:%d+: ", "")
   io.write(string.format("! ligne %s : erreur à l'exécution : %s\n",
                          line or "?", msg))
   os.exit(1)
end
os.exit(problems > 0 and 1 or 0)
