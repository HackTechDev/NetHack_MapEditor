-- Modèle nhmapedit : Prison
-- Quatre cellules closes par des barreaux le long d'un couloir : on
-- voit à l'intérieur, mais on n'y entre qu'en creusant ou en se
-- téléportant. Un prisonnier pacifique dort dans l'une d'elles.
des.level_init({ style = "solidfill", fg = " " });
des.map([[
-------------
|..|..|..|..|
|..|..|..|..|
|FF|FF|FF|FF|
+...........+
-------------
]]);

des.monster({ x = 7, y = 1, class = "@", asleep = 1, peaceful = 1 });
