-- Modèle nhmapedit : Lac souterrain
-- Caverne occupée par un lac d'eau profonde où nagent des anguilles ;
-- un trésor brille sur l'îlot central.
-- Modèle nhmapedit@cyber : Réservoir inondé
-- Caverne noyée sous une eau profonde où nagent des anguilles géantes ;
-- un butin brille sur l'îlot central.
des.level_init({ style = "solidfill", fg = " " });
des.map([[
  ---------  
 --.......-- 
--..}}}}}..--
|..}}}.}}}..|
--..}}}}}..--
 --.......-- 
  ----.----  
]]);

des.monster("giant eel", 4, 2);
des.monster("giant eel", 8, 4);
des.object({ class = "*", x = 6, y = 3 });
