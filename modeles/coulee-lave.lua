-- Modèle nhmapedit : Coulée de lave
-- Rivière de lave longeant un mur ; un pont-levis permet de la franchir
-- quand on sait l'ouvrir (baguette d'ouverture, sort, ou la bonne
-- mélodie).
-- Modèle nhmapedit@cyber : Fonderie en fusion
-- Coulée de lave le long d'un mur de l'usine ; un pont-levis la
-- franchit pour qui sait l'ouvrir (implant d'ouverture, logiciel, ou le
-- bon code).
des.level_init({ style = "solidfill", fg = " " });
des.map([[
...LLLL|...
...LLLL|...
...LLLL|...
...LLLL|...
...LLLL|...
]]);

des.drawbridge({ dir = "east", state = "closed", x = 6, y = 2 });
