-- Modèle nhmapedit : Cuisine
-- Salle avec un évier et des provisions tirées au hasard.
des.level_init({ style = "solidfill", fg = " " });
des.map([[
-------
|K....|
|.....|
|.....+
-------
]]);

des.object({ class = "%", x = 3, y = 1 });
des.object({ class = "%", x = 4, y = 1 });
des.object({ class = "%", x = 5, y = 2 });
