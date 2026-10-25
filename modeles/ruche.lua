-- Modèle nhmapedit : Ruche
-- Salle irrégulière d'abeilles tueuses autour de leur reine, avec de
-- la gelée royale. Type de salle : "beehive".
-- Modèle nhmapedit@cyber : Essaim de drones
-- Salle irrégulière de drones tueurs autour de leur reine de l'essaim,
-- avec de la gelée royale. Type de salle : "beehive".
des.level_init({ style = "solidfill", fg = " " });
des.map([[
 ------ 
--....--
|......|
|......|
--....--
 --+--- 
]]);

des.monster("queen bee", 3, 2);
des.monster("killer bee", 2, 1);
des.monster("killer bee", 5, 1);
des.monster("killer bee", 1, 3);
des.monster("killer bee", 6, 3);
des.monster("killer bee", 4, 4);
des.object("lump of royal jelly", 4, 2);
des.object("lump of royal jelly", 2, 3);
des.object("lump of royal jelly", 5, 3);
