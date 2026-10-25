-- Modèle nhmapedit : Glacier
-- Sol de glace glissant crevassé d'eau glacée, avec un yéti endormi.
des.level_init({ style = "solidfill", fg = " " });
des.map([[
  ---------  
 --IIIIIII-- 
--IIIWIIIII--
|IIIIIIIWWII|
--IIWWIIIII--
 --IIIIIII-- 
  ----I----  
]]);

des.monster({ id = "yeti", x = 6, y = 3, asleep = 1 });
