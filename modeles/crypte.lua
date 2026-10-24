-- Modèle nhmapedit : Crypte
-- Petite salle funéraire cachée derrière une porte secrète : un
-- sarcophage (grande caisse) gardé par des morts-vivants.
des.level_init({ style = "solidfill", fg = " " });
des.map([[
---------
|.......|
|.......S
|.......|
---------
]]);

des.monster({ class = "Z", x = 4, y = 1 });
des.monster({ class = "M", x = 6, y = 2 });
des.monster({ class = "Z", x = 4, y = 3 });
des.object({ x = 2, y = 2, id = "large box", contents = function()
   des.object("corpse");
end });
