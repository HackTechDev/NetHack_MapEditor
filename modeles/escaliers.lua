-- Modèle nhmapedit : Escaliers
-- Petite salle avec les deux escaliers, pour un niveau de test.
des.level_init({ style = "solidfill", fg = " " });
des.map([[
-------
|.....|
|.....+
|.....|
-------
]]);
des.stair("up", 1, 1);
des.stair("down", 5, 3);
