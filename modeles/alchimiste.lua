-- Modèle nhmapedit : Laboratoire d'alchimiste
-- Paillasses, évier et potions alignées ; un livre de sorts traîne sur
-- la table du fond.
-- Modèle nhmapedit@cyber : Labo de stims clandestin
-- Paillasses, évier et stims alignés ; un logiciel traîne sur la table
-- du fond.
des.level_init({ style = "solidfill", fg = " " });
des.map([[
---------
|K.....| 
|.--.--| 
|......| 
|......+ 
-------- 
]]);

des.object({ class = "!", x = 2, y = 1 });
des.object({ class = "!", x = 3, y = 1 });
des.object({ class = "!", x = 4, y = 1 });
des.object({ class = "!", x = 5, y = 1 });
des.object({ class = "!", x = 6, y = 1 });
des.object({ class = "+", x = 1, y = 3 });
des.object("magic marker", 6, 3);
