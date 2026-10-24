# nhmapedit — éditeur de cartes NetHack en mode terminal

Petit éditeur plein écran (Python 3 + curses, sans dépendance externe) pour
créer et modifier les cartes des niveaux spéciaux de NetHack 5.0 / 3.7.
Ces niveaux sont des scripts Lua (`dat/*.lua`) qui utilisent `des.map()`,
`des.monster()`, `des.stair()`…

![nhmapedit : le niveau de Médusa, avec une salle en cours de tracé](docs/capture.svg)

## Lancement

```sh
python3 nhmapedit.py                    # nouvelle carte 75x19
python3 nhmapedit.py mon_niveau.lua     # ouvre (ou crée) un fichier
python3 nhmapedit.py --new 40x12 petit.lua
```

Il faut un terminal d'au moins 80x24 ; à partir d'environ 105 colonnes, une
palette (outils et terrains) s'affiche à droite de la carte. Les cartes plus
grandes que l'écran défilent.

## Utilisation

Appuyez sur `?` dans l'éditeur pour l'aide complète.

| Touche | Action |
|---|---|
| Flèches, `h j k l` | déplacer le curseur (Maj+flèches, PgPréc/PgSuiv, Début/Fin : rapide) |
| `. # - \| + S H { \ K } P W L Z I T F A C B x` | choisir ce terrain comme pinceau (et peindre si l'outil est le Pinceau) |
| `e` | pinceau « roche » (espace) |
| `y` | pipette : prend comme pinceau le terrain sous le curseur (aussi au clic droit) |
| `1`…`8` | outil : Pinceau, Ligne, Rectangle, Rectangle plein, Salle, Remplissage, Copier, Coller |
| `9`, `0` | outil Ellipse, Ellipse pleine (un cercle est une ellipse tracée dans un carré) |
| `G` | outil Semis aléatoire : peint au hasard une partie des cases d'une zone, selon une densité en % |
| `R` | remplacer un terrain par un autre, sur toute la carte ou dans une zone, avec une proportion en % (comme `des.replace_terrain()`) |
| `M` | symétrie : aucune → gauche/droite → haut/bas → les deux ; pinceau, formes, remplissage, semis et remplacement sont reproduits en miroir autour du centre de la carte (axes marqués `*` sur le cadre ; le collage et les entités ne sont pas reflétés) |
| `E` | insérer une ligne ou une colonne au curseur, ou la supprimer ; la carte et les entités sont décalées |
| `D` | outil Couper : pour déplacer une zone, terrain et entités compris ; la zone est vidée puis l'outil Coller la repose |
| `X`, `Y`, `O` | presse-papiers : miroir gauche/droite, miroir haut/bas, rotation d'un quart de tour (entités comprises) |
| Espace / Entrée | appliquer l'outil (outils à deux points : ancre puis tracé ; Échap annule) |
| `d` | crayon baissé : peint en se déplaçant (tout le trait s'annule en une fois) |
| `a` | avance automatique après chaque caractère tapé (pratique pour « taper » une carte) |
| `m` | placer une entité : escalier, échelle, autel, monstre, objet, piège, porte, gravure |
| `r` | répéter la dernière entité placée sous le curseur |
| Suppr, Retour arrière, `z` | supprimer les entités sous le curseur |
| `i` | liste des entités (Entrée : y aller, `e` : modifier, `d` : supprimer) |
| Tab | afficher / masquer les entités (un symbole souligné signale plusieurs entités sur la case ; la barre d'état les liste toutes) |
| `c` | afficher / masquer les règles de coordonnées (colonnes en haut, lignes à gauche) |
| `f` | aperçu du retournement aléatoire que NetHack applique aux niveaux sans `noflip` : aucun → horizontal → vertical → les deux (l'édition reste possible, les règles gardent les vraies coordonnées) |
| `J` | rendu « comme dans le jeu » : murs en traits avec leurs coins et jonctions, sol en points, symboles et couleurs du jeu, portes et couloirs secrets cachés (l'édition reste possible) |
| `p` | propriétés : taille, `level_init`, drapeaux, placement (halign/valign ou x,y), éclairage |
| `v` | vérifier la carte (largeur > 76, entités dans les murs, escaliers en double…) |
| `t` | tester : copie la carte dans le répertoire du jeu (voir plus bas) |
| `u` / `U` (ou Ctrl-R) | annuler / rétablir |
| `n`, `o`, `s`, `w` | nouveau, ouvrir, enregistrer, enregistrer sous (Tab complète les chemins) |
| `q` | quitter |

La souris est gérée : clic = déplacer le curseur et appliquer l'outil,
glisser = peindre (Pinceau) ou tracer (Rectangle, Ligne, Salle…),
clic droit = pipette.

Les listes de monstres et d'objets se filtrent en tapant une partie du nom.
Une lettre seule (`d`, `D`…) donne un monstre aléatoire de cette classe, un
symbole seul (`!`, `?`…) un objet aléatoire de cette classe. Les options Lua
supplémentaires se saisissent sous la forme `peaceful=1, asleep=1` ou
`buc="cursed", spe=2`.

## Fichiers existants

L'éditeur ouvre n'importe quel niveau de `dat/` qui contient un `des.map()`.
Il édite :

- `des.level_init()` et `des.level_flags()` ;
- la **première** carte `des.map()` du fichier ;
- les entités à **coordonnées fixes** écrites après cette carte (escaliers,
  échelles, autels, monstres, objets, pièges, portes, gravures).

Tout le reste du script (régions, boucles, éléments aléatoires, autres
cartes…) est conservé tel quel à l'enregistrement. Un fichier ouvert puis
enregistré sans modification reste identique octet pour octet. Lors du
premier enregistrement, l'original est gardé sous `fichier.lua~`.

Les coordonnées des entités sont relatives à la carte, comme dans les
scripts NetHack. La barre d'état affiche aussi la position réelle de la
case dans le niveau de 80x21 (`niveau (x,y)`), calculée comme le fait
NetHack à partir de `halign`/`valign` ou de la position fixe de la carte ;
elle vaut `(?)` quand la carte est placée au hasard.

## Tester un niveau dans NetHack

Appuyez sur `t` : l'éditeur écrit l'état actuel de la carte (même non
enregistré) dans le répertoire de données du jeu, sous le nom
`nhme-<nom>.lua`. Le préfixe `nhme-` évite qu'un niveau du jeu portant le
même nom, rangé dans `nhdat`, soit chargé à la place du vôtre. Ensuite :

1. lancez le jeu en mode wizard : `nethack -D` ;
2. tapez `#wizloaddes`, puis le nom indiqué (par ex. `nhme-medusa-1`).

Après une modification, appuyez de nouveau sur `t` et refaites
`#wizloaddes`, sans relancer le jeu.

Le répertoire du jeu est cherché dans `$NHMAPEDIT_HACKDIR`, puis
`~/nh/install/games/lib/nethackdir`, puis `../NetHack-5.0.0/playground`.
S'il n'est trouvé dans aucun de ces endroits, l'éditeur le demande.

Pour remplacer un vrai niveau du jeu, mettez le fichier dans `dat/` des
sources et recompilez/réinstallez (`make install`), ou référencez-le dans
`dat/dungeon.lua`.

## Fichiers

- `nhmapedit.py` : l'interface curses.
- `nhlevel.py` : le modèle de niveau, la lecture et l'écriture du Lua.
- `gen_data.py` : extrait des sources de NetHack les listes de monstres,
  d'objets et de pièges dans `nhdata.json`. À relancer si les sources
  changent : `python3 gen_data.py [chemin/vers/NetHack-5.0.0]`.
- `nhdata.json` : les données générées (394 monstres, 422 objets, 24 pièges).
- `docs/capture.py` : régénère la capture d'écran `docs/capture.svg` en
  pilotant l'éditeur dans un pseudo-terminal :
  `python3 docs/capture.py [--level niveau.lua] [--size 108x30]`.

## Licence

Le code de nhmapedit est distribué sous licence MIT (voir `LICENSE`).

`nhdata.json` est extrait des sources de NetHack (noms des monstres, objets
et pièges) et relève de la NetHack General Public License. NetHack est
Copyright (c) Stichting Mathematisch Centrum, Amsterdam, 1985 et ses
contributeurs.
