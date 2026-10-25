-- Modèle nhmapedit : Galerie de mine
-- Boyaux creusés par les gnomes, où brillent des pierres précieuses ;
-- un nain y travaille encore avec sa pioche.
-- Modèle nhmapedit@cyber : Tunnel des Bas-fonds
-- Boyaux creusés par les squatteurs, où brillent des gemmes ; un foreur
-- y travaille encore avec sa perceuse.
des.level_init({ style = "solidfill", fg = " " });
des.map([[
##########   
#   #    ### 
# ### ##   # 
#     #  ### 
####### ##   
]]);

des.monster("gnome", 0, 2);
des.monster("gnome lord", 8, 0);
des.monster("dwarf", 11, 3);
des.object({ class = "*", x = 4, y = 1 });
des.object({ class = "*", x = 9, y = 1 });
des.object({ class = "*", x = 6, y = 4 });
