-- Modèle nhmapedit : Temple
-- Salle avec un autel au centre. Pour qu'un prêtre la garde, déclarez
-- la salle avec des.region({ region = {...}, type = "temple" }).
des.level_init({ style = "solidfill", fg = " " });
des.map([[
---+---
|.....|
|.....|
|.....|
|.....|
-------
]]);
des.altar({ x = 3, y = 2, align = "random" });
