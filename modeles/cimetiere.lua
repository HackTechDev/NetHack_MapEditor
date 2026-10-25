-- Modèle nhmapedit : Cimetière
-- Enclos de tombes entre des arbres où rôdent des morts-vivants ; les
-- tombes sans texte reçoivent une épitaphe tirée au hasard. Type de
-- salle : "graveyard".
des.level_init({ style = "solidfill", fg = " " });
des.map([[
-----------
|T.......T|
|.........|
|.........|
|T.......T|
-----+-----
]]);

des.monster({ class = "Z", x = 3, y = 2 });
des.monster({ class = "Z", x = 7, y = 3 });
des.monster({ id = "ghost", x = 5, y = 1 });
des.grave(2, 2, "Ci-gît un aventurier trop curieux");
des.grave({ x = 4, y = 3 });
des.grave({ x = 6, y = 2 });
des.grave({ x = 8, y = 2 });
