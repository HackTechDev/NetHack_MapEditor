-- Modèle nhmapedit : Armurerie
-- Réserve d'armes et d'armures aléatoires, derrière une porte
-- verrouillée.
-- Modèle nhmapedit@cyber : Planque d'armes
-- Stock d'armes et d'armures derrière une porte verrouillée, en
-- attendant le prochain coup.
des.level_init({ style = "solidfill", fg = " " });
des.map([[
-------
|.....|
|.....|
|.....|
---+---
]]);

des.object({ class = ")", x = 1, y = 1 });
des.object({ class = ")", x = 2, y = 1 });
des.object({ class = ")", x = 3, y = 1 });
des.object({ class = "[", x = 4, y = 1 });
des.object({ class = "[", x = 5, y = 1 });
des.object({ class = "[", x = 1, y = 3 });
des.object({ class = ")", x = 5, y = 3 });
des.door("locked", 3, 4);
