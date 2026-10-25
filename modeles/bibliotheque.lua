-- Modèle nhmapedit : Bibliothèque
-- Salle remplie de rouleaux et de livres de sorts tirés au hasard.
-- Modèle nhmapedit@cyber : Archives de données
-- Salle pleine de puces et de logiciels tirés au hasard : une mine pour
-- un netrunner.
des.level_init({ style = "solidfill", fg = " " });
des.map([[
---------
|.......|
|.......|
|.......+
|.......|
---------
]]);

des.object({ class = "?", x = 1, y = 1 });
des.object({ class = "+", x = 3, y = 1 });
des.object({ class = "?", x = 5, y = 1 });
des.object({ class = "+", x = 7, y = 1 });
des.object({ class = "+", x = 1, y = 4 });
des.object({ class = "?", x = 3, y = 4 });
des.object({ class = "+", x = 5, y = 4 });
des.object({ class = "?", x = 7, y = 4 });
