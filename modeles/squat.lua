-- Modèle nhmapedit : Repaire d'orques
-- Salle encombrée où une bande d'orques dort autour de son capitaine,
-- avec leur butin : de l'or et des vivres.
-- Modèle nhmapedit@cyber : Squat de gang
-- Squat encombré de gravats où un gang (membres, petites frappes et
-- gros durs) dort autour de son capitaine, sur un tas d'eddies et de
-- provisions volées.
des.level_init({ style = "solidfill", fg = " " });
des.map([[
-----  -----
|...----...|
|..........|
+..........|
|...----...|
-----  -----
]]);

des.monster({ id = "orc-captain", x = 9, y = 2, asleep = 1 });
des.monster({ id = "hill orc", x = 2, y = 1, asleep = 1 });
des.monster({ id = "hill orc", x = 8, y = 4, asleep = 1 });
des.monster({ id = "goblin", x = 5, y = 2, asleep = 1 });
des.monster({ id = "hobgoblin", x = 6, y = 3, asleep = 1 });
des.object("boulder", 2, 4);
des.object({ id = "gold piece", x = 10, y = 1, quantity = 80 });
des.object({ class = "%", x = 10, y = 4 });
des.object({ class = "%", x = 1, y = 3 });
