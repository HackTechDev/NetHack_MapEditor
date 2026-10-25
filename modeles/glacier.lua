-- Modèle nhmapedit : Glacier
-- Sol de glace glissant crevassé d'eau glacée, avec un yéti endormi.
-- Modèle nhmapedit@cyber : Chambre cryogénique
-- Sol gelé et glissant crevassé d'eau glacée, où dort un yéti échappé
-- d'un labo.
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
