# Fonctionnalités de nhmapedit

Liste complète de ce que fait l'éditeur. Pour apprendre à s'en servir,
voir le [tutoriel](TUTORIAL.md) ; pour le détail des touches, le
[README](README.md) ou `?` dans l'éditeur.

## Généralités

- Éditeur plein écran en mode terminal, écrit en Python 3 avec `curses`,
  sans aucune dépendance externe.
- Édite les niveaux spéciaux de NetHack 5.0 / 3.7, écrits en Lua
  (`dat/*.lua` : `des.map()`, `des.monster()`, `des.stair()`…).
- Utilisable au clavier (flèches ou `h j k l`) et à la souris (clic,
  glisser, clic droit, molette).
- Palette des outils et des terrains à droite de la carte quand le
  terminal est assez large ; défilement des cartes plus grandes que
  l'écran ; terminal de 80x24 au minimum.
- Annulation et rétablissement (`u` / Ctrl-Z, `U` / Ctrl-R / Ctrl-Y) sur
  300 commandes, terrain, entités et propriétés du niveau compris ; un
  trait au crayon ou à la souris s'annule en une fois ; le curseur
  revient où la commande a eu lieu.
- Historique des commandes (`V`) : chaque modification est nommée
  (« Salle : sol », « Ajout : escalier up », « Drapeaux : noflip »…) ;
  on revient d'un coup à n'importe quel état, en avant ou en arrière.
- `[modifié]` disparaît quand l'annulation ramène à l'état enregistré.
- Interface en français ou en anglais.

## Affichage

- Règles de coordonnées en haut et à gauche, colonne et ligne du curseur
  surlignées (`c` pour les masquer).
- Barre d'état : coordonnées relatives à la carte et position réelle
  dans le niveau de 80x21 (calculée d'après `halign`/`valign` ou la
  position fixe), terrain et entités de la case.
- Couleurs des terrains, monstres et objets reprises du jeu.
- Rendu « comme dans le jeu » (`J`) : murs en traits Unicode avec coins
  et jonctions, sol en points, portes et couloirs secrets cachés ; repli
  en ASCII si le terminal n'est pas en UTF-8.
- Aperçu des retournements aléatoires de NetHack (`f`) : horizontal,
  vertical ou les deux, avec avertissement si le niveau peut être
  retourné.
- Entités masquables (`Tab`) ; symbole souligné quand plusieurs entités
  occupent une case.
- Monstres et objets aléatoires sur fond magenta, avec le symbole de leur
  classe ou `?`.
- Aide complète (`?`) et barre d'aide contextuelle qui rappelle les
  touches utiles : ancre posée, outil Coller, crayon baissé, entités sous
  le curseur, rendu jeu…

## Dessin du terrain

- Les 23 caractères de carte de `des.map()` : sol, couloir, murs, portes,
  portes et couloirs secrets, fontaine, trône, évier, douves, bassin,
  eau, lave, mur de lave, glace, arbre, barreaux, air, nuage, limite,
  transparent, roche.
- Taper un caractère de terrain le choisit comme pinceau ; pipette (`y`
  ou clic droit).
- Outils :
  - Pinceau (`1`), avec crayon baissé (`d`) et avance automatique (`a`)
    pour « taper » une carte ;
  - Ligne (`2`), Rectangle (`3`), Rectangle plein (`4`) ;
  - Salle (`5`) : murs et sol en un geste ;
  - Remplissage (`6`) ;
  - Ellipse (`9`) et Ellipse pleine (`0`), sans trou en diagonale ;
  - Semis aléatoire (`G`) avec une densité en % ;
  - Remplacer un terrain par un autre (`R`), partout ou dans une zone,
    avec une proportion, comme `des.replace_terrain()`.
- Outils à deux points : ancre puis tracé, aperçu en direct ; Échap
  annule.
- Mode symétrie (`M`) : gauche/droite, haut/bas ou les deux, autour du
  centre de la carte.
- Insertion et suppression de lignes et de colonnes (`E`), entités
  décalées.
- Presse-papiers : copier (`7`), couper pour déplacer (`D`), coller
  (`8`), entités comprises ; miroirs (`X`, `Y`) et rotation d'un quart de
  tour (`O`), avec échange des murs `-` et `|`.
- Redimensionnement de la carte (propriétés).

## Entités

- Escaliers et échelles (montants, descendants), autels (alignement,
  type), monstres, objets, pièges, portes (état), gravures (type, texte),
  or (`des.gold`, montant), tombes (`des.grave`, épitaphe), ponts-levis
  (`des.drawbridge`, côté et état), éléments de décor (`des.feature` :
  fontaine, évier, bassin, trône, arbre) et terrain d'une case
  (`des.terrain`), pris en compte par la vérification de connexité.
- Régions : `des.region()` sous ses deux formes (salle typée avec `type`,
  `lit`, `filled`, `irregular`, `joined`, `arrival_room` ; ou
  `selection.area(...)` éclairée ou sombre), `des.non_diggable()` et
  `des.non_passwall()` (zone ou niveau entier), `des.teleport_region()`
  (`dir`, `region_islev`) et `des.levregion()` (type, nom) ; tracé à deux
  points, options, redessin de la zone, décalage à l'insertion de lignes
  et de colonnes ; régions affichées en couleur de fond (bleu salles
  typées, vert téléportation ; jaune éclairage seul et rouge non
  creusable, masqués par défaut) et listées dans la barre
  d'état ; régions écrites avec du code affichées en lecture seule.
- Les salles `temple` créées dans l'éditeur comptent pour la règle
  « autel hors d'une salle temple ».
- Placement (`m`), répétition de la dernière entité (`r`), suppression
  (`z`, Suppr), liste des entités et des régions avec aller, modifier,
  supprimer (`i`).
- Listes de monstres, d'objets et de pièges extraites des sources de
  NetHack (`gen_data.py` → `nhdata.json`), filtrables au clavier ; une
  lettre ou un symbole seul donne un monstre ou un objet aléatoire de
  cette classe ; formes féminines, noms sans préfixe et descriptions
  reconnus.
- Formulaires d'options : pour les monstres `peaceful`, `asleep`,
  `female`, `invisible`, `cancelled`, `waiting`, `name`, `appear_as`,
  `m_lev_adj`, `keep_default_invent` ; pour les objets `buc`, `spe`,
  `quantity`, `name`, `achievement`, `montype`, `buried`, `locked`,
  `trapped`, `eroded`, `greased`, `lit` ; autres options en saisie libre.
- Inventaire des monstres et contenu des conteneurs et des statues,
  imbriqués (un sac dans un coffre), écrits en `function() ... end`.

## Niveau

- Propriétés (`p`) : taille, `des.level_init()` (style, terrain de
  remplissage, options), drapeaux de `des.level_flags()` à cocher,
  placement de la carte (`halign`/`valign` ou position fixe), éclairage.
- Nouvelle carte (`n`) : roche, sol ou salle entourée de murs.

## Fichiers

- Ouverture de n'importe quel niveau de `dat/` contenant un `des.map()` :
  chaque carte, `level_init`, `level_flags`, les entités à
  position fixe et les régions sont éditables, qu'ils suivent la carte
  ou soient dans sa fonction `contents = function() ... end` ; tout le reste du script est conservé.
- Aller-retour exact : un fichier ouvert puis enregistré sans
  modification reste identique octet pour octet (vérifié sur les 93
  niveaux de `dat/`).
- Fichiers à plusieurs cartes : passage de l'une à l'autre (`[`, `]`),
  liste des cartes (`N`) avec leur taille et leur placement, ajout d'une
  carte, plan du niveau de 80x21 montrant la place de chacune ; les
  entités suivant une carte lui appartiennent ; l'annulation traverse
  les changements de carte.
- Copie de l'original sous `fichier.lua~` au premier enregistrement.
- Enregistrer (`s`), enregistrer sous (`w`), ouvrir (`o`) avec
  complétion des chemins par Tab ; confirmation avant de perdre des
  modifications.
- Import d'une carte en texte brut (`o` sur un `.txt`).
- Export de la carte seule en texte (`.txt`) ou en image (`.svg`, `.png`
  via `rsvg-convert` ou ImageMagick), telle qu'elle est affichée.
- Bibliothèque de modèles (`b`), vingt livrés avec leurs entités :
  temple, boutique, salle du trône, bibliothèque, armurerie, cuisine,
  tour ronde, prison, escaliers, fontaine décorée, bosquet, pont sur la
  rivière, île entourée de douves, îlot dans la lave, antre du dragon,
  coffre-fort, cachette secrète, crypte, couloir piégé, petit
  labyrinthe ; enregistrement du presse-papiers comme nouveau modèle.
- Sauvegarde de secours régulière (`.nhme-autosave`), proposée à la
  réouverture après un arrêt brutal.
- Salles à thème : ouverture de `themerms.lua`, édition des salles
  dessinées par `des.map()` et création de nouvelles salles.

## Vérification (`v`)

- Connexité : chemin de l'escalier montant au descendant, sans diagonale
  par les portes ; passages secrets, eau et lave signalés ; zones
  fermées.
- Règles de NetHack : carte trop large ou qui déborde du niveau, porte
  dans un coin ou hors d'un mur, escalier ou autel dans l'eau ou sur du
  terrain remplacé, autel hors d'une salle `temple`, entité dans un mur
  ou hors de la carte, escaliers en double, noms inconnus, retournement
  possible, escaliers absents.
- Exécution du script complet avec le vrai Lua et une bibliothèque `des`
  factice : erreurs de syntaxe et d'exécution, noms, paramètres,
  drapeaux, styles, états et types invalides, fonctions inexistantes,
  avec le numéro de ligne.
- Compilation proposée de l'interpréteur Lua des sources de NetHack s'il
  n'y en a pas sur le système.

## Intégration avec NetHack

- Essai immédiat (`t`) : copie de la carte en cours (même non
  enregistrée) dans le répertoire du jeu sous `nhme-<nom>.lua`, avec le
  drapeau `noflip`.
- Avec tmux : lancement de NetHack en mode wizard (panneau, fenêtre ou
  session tmux) et chargement automatique de la carte par
  `#wizloaddes` ; rechargement à chaque nouvel appui sur `t` ; jamais de
  second jeu si une partie est en cours.
- Sans tmux : instructions pas à pas.
- Ajout du niveau au donjon (`p` → Donjon) : édition de
  `dat/dungeon.lua` (profondeur, tirage, probabilité, variantes,
  alignement, drapeaux, bones, `chainlevel`), modification et retrait des
  niveaux spéciaux, avec contrôles.
- Essai des salles à thème avec la variable `THEMERM`.

## Configuration

- Fichier `~/.config/nhmapedit/config` (ou `$NHMAPEDIT_CONFIG`), au
  format INI, exemple commenté dans `docs/config.exemple` :
  répertoire du jeu, `dungeon.lua`, taille par défaut, règles, entités,
  Unicode, délai de la sauvegarde de secours, langue, couleurs des
  terrains, remplacement de touches.
- Erreurs de configuration signalées au démarrage sans bloquer.
- Variables d'environnement : `NHMAPEDIT_HACKDIR`, `NHMAPEDIT_DUNGEON`,
  `NHMAPEDIT_LANG`, `NHMAPEDIT_LUA`, `NHMAPEDIT_DAT`, `NHMAPEDIT_LUAC`.
- Langue choisie selon la locale (français si elle commence par `fr`,
  anglais sinon), imposable par la configuration ou `NHMAPEDIT_LANG`.

## Qualité

- 81 tests automatiques (`python3 -m unittest`) : aller-retour sur
  `dat/`, outils, entités, fichiers, vérification, export, modèles,
  configuration, traduction, parcours de l'interface dans un
  pseudo-terminal.
- Code découpé en modules thématiques (`nhme_*.py`, `nhlevel.py`,
  `nhcheck.py`…).
- Capture d'écran du README régénérable (`docs/capture.py`).
