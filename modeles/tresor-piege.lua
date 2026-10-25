-- Modèle nhmapedit : Chambre au trésor piégée
-- Un coffre garni au fond d'une salle dont chaque approche est
-- piégée.
des.level_init({ style = "solidfill", fg = " " });
des.map([[
---------
|.......|
|.......|
+.......|
|.......|
|.......|
---------
]]);

des.object({ x = 6, y = 3, id = "chest", trapped = 1, contents = function()
   des.object({ class = "*" });
   des.object({ class = "=" });
end });
des.trap("land mine", 2, 3);
des.trap("bear", 4, 2);
des.trap("bear", 4, 4);
des.trap("teleport", 5, 3);
des.trap("fire", 6, 2);
des.trap("fire", 6, 4);
