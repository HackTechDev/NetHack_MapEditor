-- Modèle nhmapedit : Antre du dragon
-- Caverne irrégulière où dort un dragon, sur son trésor.
des.level_init({ style = "solidfill", fg = " " });
des.map([[
  -------    
 --.....---- 
--.........--
|...........|
--.........--
 ---.....--  
   ---.---   
]]);

des.monster({ x = 6, y = 3, class = "D", asleep = 1 });
des.object({ class = "*", x = 5, y = 3 });
des.object({ x = 7, y = 3, id = "gold piece", quantity = 500 });
