-- Modèle nhmapedit : Laboratoire militaire
-- Laboratoire gardé par des soldats et un lieutenant : paillasses,
-- potions et baguette d'essai derrière des barreaux, accès piégé.
-- Modèle nhmapedit@cyber : Labo Militech
-- Labo secret de Militech gardé par des soldats et un lieutenant :
-- prototypes (stims, implant) derrière des barreaux, accès piégé, un
-- drone de combat en veille.
des.level_init({ style = "solidfill", fg = " " });
des.map([[
-------------
|.....F.....|
|.....F.....|
+.....F.....|
|.....F.....|
-------------
]]);

des.monster("soldier", 3, 1);
des.monster("soldier", 3, 4);
des.monster("lieutenant", 4, 2);
des.monster({ id = "iron golem", x = 10, y = 3, asleep = 1 });
des.trap("magic", 1, 3);
des.object({ class = "!", x = 8, y = 1 });
des.object({ class = "!", x = 9, y = 1 });
des.object({ class = "/", x = 10, y = 2 });
des.object("expensive camera", 8, 4);
