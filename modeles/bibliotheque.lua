-- Modèle nhmapedit : Bibliothèque
-- Salle remplie de rouleaux et de livres de sorts tirés au hasard.
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
