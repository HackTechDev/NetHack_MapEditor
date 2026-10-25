-- Modèle nhmapedit : Poste de garde
-- Petite salle de garde commandant un couloir : deux gardes
-- vigilants derrière une porte fermée.
des.level_init({ style = "solidfill", fg = " " });
des.map([[
-----     
|...|     
|...+#####
|...|     
-----     
]]);

des.door("closed", 4, 2);
des.monster("watchman", 1, 1);
des.monster("watchman", 1, 3);
des.object({ class = ")", x = 3, y = 1 });
