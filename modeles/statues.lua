-- Modèle nhmapedit : Galerie de statues
-- Couloir bordé de statues de pierre ; l'une d'elles n'en est pas une
-- et attend son heure.
des.level_init({ style = "solidfill", fg = " " });
des.map([[
-------------
|...........|
+...........+
|...........|
-------------
]]);

des.object({ id = "statue", x = 2, y = 1 });
des.object({ id = "statue", x = 5, y = 1 });
des.object({ id = "statue", x = 8, y = 1 });
des.object({ id = "statue", x = 2, y = 3 });
des.object({ id = "statue", x = 5, y = 3 });
des.object({ id = "statue", x = 8, y = 3 });
des.trap("statue", 11, 1);
