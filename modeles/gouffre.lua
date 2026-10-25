-- Modèle nhmapedit : Gouffre
-- Salle crevée de trous qui mènent au niveau inférieur ; une
-- passerelle de sol permet de la traverser.
des.level_init({ style = "solidfill", fg = " " });
des.map([[
-----------
|.........|
+.........+
|.........|
-----------
]]);

des.trap("hole", 2, 1);
des.trap("hole", 3, 1);
des.trap("hole", 4, 1);
des.trap("hole", 6, 1);
des.trap("hole", 7, 1);
des.trap("hole", 8, 1);
des.trap("hole", 2, 3);
des.trap("hole", 3, 3);
des.trap("hole", 5, 3);
des.trap("hole", 6, 3);
des.trap("hole", 8, 3);
