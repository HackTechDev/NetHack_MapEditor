-- Modèle nhmapedit : Caserne
-- Dortoir de soldats endormis autour de leur sergent ; une armurerie
-- de fortune dans le coin. Pour une vraie caserne, déclarez la salle
-- avec des.region({ region = {...}, type = "barracks" }).
des.level_init({ style = "solidfill", fg = " " });
des.map([[
-----------
|.........|
|.........|
|.........+
|.........|
-----------
]]);

des.monster({ id = "soldier", x = 2, y = 1, asleep = 1 });
des.monster({ id = "soldier", x = 4, y = 1, asleep = 1 });
des.monster({ id = "soldier", x = 6, y = 1, asleep = 1 });
des.monster({ id = "soldier", x = 2, y = 4, asleep = 1 });
des.monster({ id = "soldier", x = 4, y = 4, asleep = 1 });
des.monster({ id = "sergeant", x = 8, y = 2, asleep = 1 });
des.object({ class = ")", x = 9, y = 1 });
des.object({ class = "[", x = 9, y = 4 });
