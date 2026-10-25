-- Modèle nhmapedit : Poste des Keystone Kops
-- Poste de police : un sergent et ses agents dans le bureau, deux
-- cellules à barreaux au fond, dont une occupée.
-- Modèle nhmapedit@cyber : Poste du NCPD
-- Commissariat du NCPD : un sergent et ses flics au comptoir, deux
-- cellules à barreaux au fond, dont une occupée par un détenu.
des.level_init({ style = "solidfill", fg = " " });
des.map([[
-------------
|...|...|...|
|...|...|...|
|-F---F---F-|
|...........|
|...........+
-------------
]]);

des.monster("Kop Sergeant", 6, 4);
des.monster("Keystone Kop", 3, 5);
des.monster("Keystone Kop", 9, 4);
des.monster({ class = "@", x = 6, y = 1, asleep = 1, peaceful = 1 });
des.object("credit card", 1, 4);
des.object("bugle", 10, 5);
