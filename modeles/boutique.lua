-- Modèle nhmapedit : Boutique
-- Salle à une seule porte, comme l'exige une boutique. Déclarez-la avec
-- des.region({ region = {...}, type = "shop" }) (ou "armor shop"…).
-- Modèle nhmapedit@cyber : Échoppe du marché noir
-- Salle à une seule porte, comme l'exige une boutique : un vendeur s'y
-- installe si vous la déclarez avec des.region({ region = {...}, type =
-- "shop" }) (ou "armor shop"…).
des.level_init({ style = "solidfill", fg = " " });
des.map([[
-------
|.....|
|.....|
|.....|
---+---
]]);
