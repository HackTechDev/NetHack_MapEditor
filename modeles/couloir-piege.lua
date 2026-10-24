-- Modèle nhmapedit : Couloir piégé
-- Long couloir semé de pièges ; une porte secrète permet de le
-- contourner.
des.level_init({ style = "solidfill", fg = " " });
des.map([[
-------------
|...........|
|-----S-----|
+...........+
-------------
]]);

des.trap("arrow", 2, 3);
des.trap("dart", 4, 3);
des.trap("trap door", 6, 3);
des.trap("sleep gas", 8, 3);
des.trap("falling rock", 10, 3);
