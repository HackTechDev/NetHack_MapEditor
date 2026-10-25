-- Modèle nhmapedit : Arène
-- Grande salle ronde bordée de gradins (piliers) : deux combattants
-- s'y affrontent, sous l'œil d'un public de statues.
-- Modèle nhmapedit@cyber : Arène de combats illégaux
-- Fosse ronde bordée de piliers : deux combattants s'y affrontent
-- devant un public de statues, sous les paris des fixers.
des.level_init({ style = "solidfill", fg = " " });
des.map([[
    -------    
  ---.....---  
 --.........-- 
--...........--
|.............|
+.............+
|.............|
--...........--
 --.........-- 
  ---.....---  
    -------    
]]);

des.monster({ x = 5, y = 5 });
des.monster({ x = 9, y = 5 });
des.object({ id = "statue", x = 3, y = 3 });
des.object({ id = "statue", x = 11, y = 3 });
des.object({ id = "statue", x = 3, y = 7 });
des.object({ id = "statue", x = 11, y = 7 });
