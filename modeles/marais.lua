-- Modèle nhmapedit : Marais
-- Damier de sol et d'eau, comme le marais de Juiblex ; des créatures
-- rampent entre les mares. Type de salle : "swamp".
-- Modèle nhmapedit@cyber : Égouts inondés
-- Damier de sol et d'eau, comme le marais de Juiblex ; des créatures
-- rampent entre les flaques. Type de salle : "swamp".
des.level_init({ style = "solidfill", fg = " " });
des.map([[
-----------
|.}.}.}.}.|
|}.}.}.}.}|
+.}.}.}.}.+
|}.}.}.}.}|
|.}.}.}.}.|
-----------
]]);

des.monster({ class = "F", x = 3, y = 1 });
des.monster({ class = ";", x = 4, y = 3 });
des.monster({ class = "F", x = 7, y = 5 });
