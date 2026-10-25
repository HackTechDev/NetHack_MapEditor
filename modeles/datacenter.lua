-- Modèle nhmapedit : Salle aux grilles
-- Salle parcourue de rangées de barreaux de fer, où grouillent des
-- insectes et tourbillonne un vortex d'énergie.
-- Modèle nhmapedit@cyber : Data center
-- Salle des serveurs : des baies (barreaux) en rangées, des bugs réseau
-- dans les allées et une tempête de données qui tourne entre les
-- racks ; une holosphère oubliée sur une console.
des.level_init({ style = "solidfill", fg = " " });
des.map([[
---------------
|.............|
|.FFFFF.FFFFF.|
|.............+
|.FFFFF.FFFFF.|
|.............|
---------------
]]);

des.monster("grid bug", 2, 1);
des.monster("grid bug", 9, 3);
des.monster("grid bug", 12, 5);
des.monster("energy vortex", 6, 3);
des.object("crystal ball", 13, 1);
des.trap("magic", 7, 5);
