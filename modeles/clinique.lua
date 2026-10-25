-- Modèle nhmapedit : Infirmerie
-- Salle de soins tenue par des infirmières, avec un évier, des potions
-- de soins et des instruments ; une réserve attenante.
-- Modèle nhmapedit@cyber : Clinique de charcudoc
-- Clinique clandestine tenue par des infirmières-androïdes : évier,
-- stims de soins, scanner médical et scalpel laser ; une réserve
-- attenante pour les implants d'occasion.
des.level_init({ style = "solidfill", fg = " " });
des.map([[
-------------
|...|.......|
|.K.|.......|
|...+.......+
|...|.......|
-------------
]]);

des.monster("nurse", 7, 2);
des.monster("nurse", 10, 4);
des.object("potion of healing", 1, 1);
des.object("potion of extra healing", 3, 1);
des.object("stethoscope", 1, 4);
des.object("scalpel", 3, 4);
des.object({ class = "!", x = 6, y = 4 });
des.object({ class = "/", x = 2, y = 3 });
