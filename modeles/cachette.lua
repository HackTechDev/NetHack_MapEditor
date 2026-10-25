-- Modèle nhmapedit : Cachette secrète
-- Placard dérobé derrière une porte secrète, contenant un coffre
-- verrouillé.
-- Modèle nhmapedit@cyber : Planque secrète
-- Placard dérobé derrière une porte secrète : un coffre verrouillé, des
-- eddies, un stim et une puce.
des.level_init({ style = "solidfill", fg = " " });
des.map([[
-----
|...|
|...S
-----
]]);

des.object({ x = 1, y = 1, id = "chest", locked = 1, contents = function()
   des.object({ class = "$", quantity = 50 });
   des.object({ class = "!" });
   des.object({ class = "?" });
end });
