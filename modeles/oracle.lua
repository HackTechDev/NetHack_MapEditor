-- Modèle nhmapedit : Sanctuaire aux fontaines
-- Comme celui de l'Oracle : une enceinte à quatre fontaines, des
-- centaures pacifiques et un sage au centre.
-- Modèle nhmapedit@cyber : Bureau de la Courtière
-- Comme celui de la Courtière : une enceinte à quatre fontaines, des
-- centaures pacifiques et une sage au centre.
des.level_init({ style = "solidfill", fg = " " });
des.map([[
-----------
|.........|
|.{.....{.|
|.........|
|.{.....{.|
|.........|
-----+-----
]]);

des.monster({ class = "@", x = 5, y = 3, peaceful = 1 });
des.monster({ class = "C", x = 1, y = 1, peaceful = 1 });
des.monster({ class = "C", x = 9, y = 5, peaceful = 1 });
