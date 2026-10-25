-- Modèle nhmapedit : Cabinet du magicien
-- Pièce ronde derrière une porte verrouillée : un lanceur de sorts
-- endormi, ses livres et une baguette.
-- Modèle nhmapedit@cyber : Repaire du netrunner
-- Pièce ronde derrière une porte verrouillée : un netrunner endormi,
-- ses logiciels et un implant.
des.level_init({ style = "solidfill", fg = " " });
des.map([[
  -----  
 --...-- 
--.....--
|.......|
--.....--
 --...-- 
  --+--  
]]);

des.door("locked", 4, 6);
des.monster({ class = "@", x = 4, y = 3, asleep = 1 });
des.object({ class = "+", x = 3, y = 1 });
des.object({ class = "+", x = 5, y = 1 });
des.object({ class = "/", x = 4, y = 2 });
des.object({ class = "?", x = 2, y = 3 });
