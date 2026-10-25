-- Modèle nhmapedit : Boutique de baguettes
-- Petite salle à une seule porte pour une boutique de baguettes :
-- déclarez-la avec des.region({ region = {...}, type = "wand shop" })
-- pour qu'un marchand s'y installe et la remplisse.
-- Modèle nhmapedit@cyber : Boutique d'implants
-- Échoppe à une seule porte où un vendeur pose des implants : déclarez
-- la salle avec des.region({ region = {...}, type = "wand shop" }) pour
-- qu'il s'installe et remplisse ses vitrines.
des.level_init({ style = "solidfill", fg = " " });
des.map([[
---------
|.......|
|.......|
|.......|
----+----
]]);
