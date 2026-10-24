-- Modèle nhmapedit : Îlot dans la lave
-- Îlot de sol au milieu d'un lac de lave, avec un coffre : il faut
-- voler, geler ou se téléporter pour l'atteindre.
des.level_init({ style = "solidfill", fg = " " });
des.map([[
LLLLLLLLL
LLLLLLLLL
LLL...LLL
LLL...LLL
LLLLLLLLL
LLLLLLLLL
]]);

des.object({ x = 4, y = 2, id = "chest", contents = function()
   des.object({ class = "*" });
   des.object({ class = "=" });
end });
