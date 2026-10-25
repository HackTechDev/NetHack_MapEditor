-- Modèle nhmapedit : Ruines
-- Restes d'une salle aux murs effondrés : des pans de mur, des
-- rochers et un objet oublié.
des.level_init({ style = "solidfill", fg = " " });
des.map([[
--- --  --- 
|..  .  ...|
  ...... ...
|.. ... ... 
 .....  ..| 
--  -- ---- 
]]);

des.object("boulder", 5, 2);
des.object("boulder", 8, 4);
des.object({ class = "(", x = 2, y = 3 });
