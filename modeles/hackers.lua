-- Modèle nhmapedit : Atelier d'apprentis
-- Salle de travail découpée en alcôves où étudient des apprentis
-- lanceurs de sorts, entre leurs rouleaux, un livre et une baguette.
-- Modèle nhmapedit@cyber : Planque de hackers
-- Open space découpé en boxes où des apprentis hackers piratent entre
-- leurs puces, un logiciel et un graveur de puces ; des bugs réseau
-- grouillent dans les câbles.
des.level_init({ style = "solidfill", fg = " " });
des.map([[
-----------
|.|.|.|...|
|.........|
|.........+
|.|.|.|...|
-----------
]]);

des.monster("apprentice", 8, 2);
des.monster({ id = "apprentice", x = 5, y = 3, asleep = 1 });
des.monster("grid bug", 1, 1);
des.monster("grid bug", 3, 4);
des.object("magic marker", 8, 1);
des.object({ class = "?", x = 3, y = 1 });
des.object({ class = "?", x = 5, y = 1 });
des.object({ class = "+", x = 1, y = 4 });
des.object({ class = "/", x = 7, y = 4 });
