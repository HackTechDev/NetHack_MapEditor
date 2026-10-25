-- Modèle nhmapedit : Zoo
-- Salle pleine de monstres endormis, chacun sur un tas d'or. Déclarez
-- la salle avec des.region({ region = {...}, type = "zoo" }) pour que
-- NetHack la peuple lui-même.
des.level_init({ style = "solidfill", fg = " " });
des.map([[
---------
|.......|
|.......|
|.......|
----+----
]]);

des.monster({ x = 1, y = 1, asleep = 1 });
des.monster({ x = 4, y = 1, asleep = 1 });
des.monster({ x = 7, y = 1, asleep = 1 });
des.monster({ x = 2, y = 3, asleep = 1 });
des.monster({ x = 6, y = 3, asleep = 1 });
des.gold(30, 1, 1);
des.gold(30, 4, 1);
des.gold(30, 7, 1);
des.gold(30, 2, 3);
des.gold(30, 6, 3);
