# Tutoriel : votre premier niveau avec nhmapedit

Ce tutoriel construit pas à pas un petit niveau, **la crypte** : deux
salles reliées par un couloir, une porte secrète, une fontaine, des
escaliers, quelques monstres et un coffre garni. On le vérifie, on
l'enregistre, puis on l'essaie dans NetHack. Comptez une demi-heure.

Pour chaque étape, les touches à taper sont indiquées entre crochets :
`[5]`, `[Espace]`… L'aide complète s'affiche à tout moment avec `[?]`,
et la barre du bas rappelle les touches utiles selon la situation.

À la fin, la carte ressemblera à ceci :

```
 -----------
 |.........|            --------------
 |.<{......|            |.....d......|
 |.........S############+....d.d.....|
 |.........|            |....}}}}....|
 |.......(.|            |...}}}}}}...|
 -----------            |....}}}}....|
                        |............|
                        |..........>.|
                        --------------
```

## 1. Lancer l'éditeur

Dans un terminal d'au moins 80 colonnes sur 24 lignes (105 colonnes
pour voir la palette à droite), depuis le dossier de l'éditeur :

```sh
python3 nhmapedit.py --new 40x12 crypte.lua
```

`--new 40x12` crée une carte de 40 colonnes sur 12 lignes, remplie de
roche ; `crypte.lua` est le fichier où elle sera enregistrée. Il n'existe
pas encore : il sera créé au premier enregistrement.

L'écran se compose de :

- la **ligne de titre** : nom du fichier, `[modifié]` s'il y a des
  changements non enregistrés, taille de la carte ;
- les **règles** de coordonnées, en haut (colonnes) et à gauche (lignes) ;
  la colonne et la ligne du curseur y sont surlignées (`c` les masque) ;
- la **carte** dans son cadre ;
- la **palette** à droite : les outils avec leur touche, les terrains
  avec leur caractère ;
- trois lignes d'**état** : la case sous le curseur (coordonnées dans la
  carte, puis dans le niveau de 80x21, terrain, entités), l'outil et le
  pinceau, le dernier message ;
- la **barre d'aide**, en vidéo inverse, qui change selon ce que vous
  faites.

Le curseur se déplace avec les flèches (ou `h j k l`), plus vite avec
Maj+flèches. `[g]` va directement à une position : tapez `12 4` puis
Entrée. Les coordonnées affichées sont **relatives à la carte**, comme
dans les scripts de NetHack : la case en haut à gauche est `(0,0)`.

**Pressé ?** `[n]` puis « assistant » génère un niveau complet prêt à
essayer : salles et couloirs, labyrinthe, caverne ou grande salle, avec
les escaliers et quelques monstres, objets et pièges. Ce tutoriel part
plutôt d'une carte vide pour montrer chaque outil.

## 2. La première salle

L'outil **Salle** trace un rectangle de murs rempli de sol.

1. `[5]` choisit l'outil Salle. La barre du bas indique
   « Espace: poser l'ancre (1er coin) ».
2. Placez le curseur en `(1,1)` et appuyez sur `[Espace]` : l'**ancre**
   est posée.
3. Déplacez le curseur jusqu'en `(11,7)`. L'aperçu de la salle suit le
   curseur, en vidéo inverse, et la barre d'état donne sa taille.
4. `[Espace]` trace la salle.

Une erreur ? `[u]` annule, `[U]` rétablit ; le message nomme la commande
concernée. `[V]` affiche l'**historique** de toutes vos commandes : en
choisir une ramène la carte à cet état. Pendant le tracé, `[Échap]`
retire l'ancre sans rien dessiner.

> Avec la souris : cliquez sur un coin et glissez jusqu'au coin opposé.

## 3. La seconde salle

Même outil, de `(24,2)` à `(37,10)` : `[Espace]` sur le premier coin,
`[Espace]` sur le second. Si vous êtes à l'aise avec la souris, faites-le
cette fois en glissant.

## 4. Le couloir

Un couloir est fait de cases `#`. Pour le tracer d'un coup :

1. `[#]` : le pinceau devient « couloir » (ligne Pinceau de la barre
   d'état). Taper un caractère de terrain change toujours le pinceau.
2. `[2]` : outil **Ligne**.
3. `[Espace]` en `(12,4)`, puis `[Espace]` en `(23,4)`.

## 5. Les portes

Les murs touchés par le couloir doivent devenir des portes.

1. `[1]` : outil **Pinceau**. Avec lui, taper un caractère de terrain
   peint aussi la case sous le curseur.
2. En `(24,4)`, tapez `[+]` : une porte.
3. En `(11,4)`, tapez `[S]` : une **porte secrète**. Elle s'affiche en
   magenta ; dans le jeu, elle ressemblera à un mur jusqu'à ce qu'on la
   trouve.

`[J]` montre la carte « comme dans le jeu » : murs en traits continus,
sol en points, porte secrète dessinée comme le mur. `[J]` à nouveau
revient aux caractères de la carte. L'édition reste possible dans les
deux modes.

## 6. Le décor

**Une fontaine.** Toujours avec le Pinceau, tapez `[{]` en `(4,3)`.

**Une mare.** Au centre de la seconde salle, une petite étendue d'eau
profonde, tracée avec l'outil **Ellipse pleine** :

1. `[}]` : pinceau « douves » (de l'eau profonde).
2. `[0]` : outil Ellipse pleine (`[9]` ne trace que le contour).
3. `[Espace]` en `(28,5)`, `[Espace]` en `(33,7)`.

Un cercle est une ellipse tracée dans un carré. Le contour d'une ellipse
n'a jamais de trou en diagonale : on ne peut pas s'y faufiler.

**La symétrie.** `[M]` active un mode miroir (gauche/droite, haut/bas
ou les deux) : tout ce qui est peint est reproduit autour du centre de
la carte, dont les axes sont marqués `*` sur le cadre. Précieux pour un
niveau dessiné sur toute la largeur ; `[M]` jusqu'à « Symétrie
désactivée » pour en sortir.

**Variante : le semis.** L'outil `[G]` (Semis) peint au hasard une
proportion des cases d'une zone : pratique pour des arbres (`T`), des
rochers, de l'eau éparse. L'éditeur demande la densité en %.

**Variante : le labyrinthe.** L'outil `[Q]` (Labyrinthe) creuse un
labyrinthe dans la zone tracée, comme `des.mazewalk()`. Il demande le
style des murs (`-` et `|`, roche, ou le pinceau), le terrain des passages
et un pourcentage de boucles (0 : un seul chemin entre deux points). Le
tirage ne vous plaît pas ? `u` l'annule, Espace en refait un sur la même
zone.

## 7. Les escaliers

Les escaliers, monstres, objets, pièges… sont des **entités** : elles ne
font pas partie du dessin `des.map` mais sont écrites après lui, avec
leurs coordonnées.

1. Placez le curseur en `(3,3)`, dans la première salle.
2. `[m]` ouvre la liste des entités. Choisissez **Escalier** (flèches
   puis Entrée, ou tapez les premières lettres pour filtrer).
3. Choisissez **montant (up)**. Le symbole `<` apparaît.
4. En `(35,9)`, `[m]`, **Escalier**, **descendant (down)** : `>`.

## 8. Monstres et objets

**Un chacal endormi.** En `(30,3)` :

1. `[m]`, **Monstre**.
2. Tapez `jackal` pour filtrer la liste, puis Entrée. (Une lettre seule,
   comme `d`, donnerait un monstre aléatoire de cette classe.)
3. Le formulaire **Options du monstre** s'ouvre. Descendez sur
   « endormi (asleep) » et appuyez sur Entrée : la valeur passe de
   « (défaut) » à « oui ». `[Échap]` termine.

**D'autres chacals.** `[r]` répète la dernière entité sous le curseur :
déplacez-vous en `(31,4)` puis `[r]`, en `(29,4)` puis `[r]`.

**Un coffre garni.** En `(9,6)` :

1. `[m]`, **Objet**, tapez `chest`, Entrée.
2. Dans **Options de l'objet**, choisissez « verrouillé (locked) » →
   « oui ».
3. Choisissez « contenu (conteneur, statue) (contents) » : une liste
   vide s'ouvre.
   « + ajouter un objet » : choisissez `potion of healing`, puis
   `[Échap]` pour fermer son formulaire. Ajoutez de même un
   `scroll of teleportation`.
4. `[Échap]` ferme la liste du contenu, `[Échap]` le formulaire du coffre.

Quand plusieurs entités occupent une case, son symbole est souligné et la
barre d'état les énumère.

**La liste des entités.** `[i]` les montre toutes : Entrée y amène le
curseur, `[e]` en modifie une, `[d]` la supprime. Sur la carte,
`[z]` (ou Suppr) supprime les entités sous le curseur, et `[Tab]` les
masque pour voir le terrain dessous.

## 9. Vérifier

`[v]` lance la vérification. Chaque message commence par sa gravité :
`!` erreur, `?` à vérifier, `-` simple remarque. Vous devriez lire :

```
- NetHack peut retourner ce niveau au chargement (dans les deux sens) :
  f pour un aperçu, drapeau noflip pour l'empêcher.
- Connexité : l'escalier descendant (35,9) n'est accessible que par un
  passage secret (S ou H).
```

- La **connexité** : l'éditeur a trouvé un chemin de `<` à `>`, mais il
  passe par la porte secrète. C'est voulu ici ; remplacez le `S` par un
  `+` et la remarque disparaît. Remplacez-le par un mur `|` : le message
  devient une erreur `!`, l'escalier est inaccessible.
- Le **retournement** : NetHack retourne au hasard les niveaux qui ne
  l'interdisent pas. `[f]` montre les quatre orientations possibles
  (`[f]` jusqu'à revenir à « sens d'origine »). Pour l'interdire :
  `[p]` (propriétés), **Drapeaux**, cochez `noflip` avec Entrée, puis
  `[Échap]` deux fois.

Si un interpréteur Lua est installé (`lua5.4`), `[v]` exécute aussi le
script complet avec une bibliothèque `des` factice et signale les fautes
de frappe dans les noms de monstres ou d'objets. Sinon, l'éditeur propose
une fois de compiler celui des sources de NetHack.

## 10. Enregistrer

`[s]` enregistre dans `crypte.lua`. Ouvrez le fichier dans un éditeur de
texte : c'est un script Lua ordinaire, comme ceux de `dat/` :

```lua
des.level_init({ style = "solidfill", fg = " " });
des.level_flags("mazelevel", "noflip");

des.map([[
...
]]);

des.stair("up", 3, 3);
des.stair("down", 35, 9);
des.monster({ x = 30, y = 3, id = "jackal", asleep = 1 });
des.monster({ x = 29, y = 4, id = "jackal", asleep = 1 });
des.monster({ x = 31, y = 4, id = "jackal", asleep = 1 });
des.object({ x = 9, y = 6, id = "chest", locked = 1, contents = function()
   des.object("potion of healing");
   des.object("scroll of teleportation");
end });
```

`[w]` enregistre sous un autre nom. Si vous quittez (`[q]`) avec des
modifications non enregistrées, l'éditeur le demande. Et si le terminal
se ferme brutalement, une **sauvegarde de secours**
(`crypte.lua.nhme-autosave`) sera proposée à la réouverture.

## 11. Essayer le niveau dans NetHack

Il faut NetHack 5.0 / 3.7 compilé et installé, avec le mode wizard
autorisé (c'est le cas d'une installation de développement).

Appuyez sur `[t]`. L'éditeur copie la carte (même non enregistrée) dans
le répertoire du jeu sous le nom `nhme-crypte.lua`, avec le drapeau
`noflip`.

- **Avec tmux**, il propose de lancer le jeu : NetHack démarre en mode
  wizard dans un panneau ou une fenêtre tmux et la carte y est chargée
  automatiquement. Modifiez la carte, `[t]` à nouveau : elle est
  rechargée dans le même jeu.
- **Sans tmux**, une fenêtre explique la marche à suivre : lancez
  `nethack -D` dans un autre terminal, tapez `#wizloaddes` puis
  `nhme-crypte`.

Dans le jeu, Ctrl-F révèle toute la carte et Ctrl-T téléporte : pratique
pour aller voir le coffre et chercher la porte secrète.

Si l'éditeur ne trouve pas le répertoire du jeu, il le demande ; vous
pouvez l'indiquer une fois pour toutes dans le fichier de configuration
(voir plus bas).

## 12. Aller plus loin

**Modèles.** `[b]` ouvre la bibliothèque : une vingtaine de morceaux de
carte, du temple avec son autel à l'antre du dragon endormi sur son or,
en passant par la crypte, la prison ou le couloir piégé. Le modèle
choisi va dans le presse-papiers et l'outil Coller (`8`) s'active :
`[X]`, `[Y]`, `[O]` le retournent ou le font pivoter, `[Espace]` le pose
(coin haut-gauche au curseur). La dernière ligne de la bibliothèque
enregistre votre propre presse-papiers comme modèle.

**Copier, couper, coller.** `[7]` copie une zone (deux coins, comme une
salle), `[D]` la coupe pour la déplacer, entités comprises ; `[8]` la
colle.

**Remplacer.** `[R]` remplace un terrain par un autre, partout ou dans
une zone, avec une proportion : par exemple 30 % du sol en eau.

**Insérer une ligne ou une colonne.** `[E]` au curseur ; la carte et les
entités se décalent.

**Ouvrir un niveau existant.** `[o]` puis le chemin, par exemple
`../NetHack-5.0.0/dat/medusa-1.lua` (Tab complète les chemins).
L'éditeur modifie la carte et les entités à position fixe, et conserve
tout le reste du script. Ouvrir `themerms.lua` propose ses salles à
thème.

**Placer le niveau dans le donjon.** `[p]` puis **Donjon** ajoute le
niveau à `dat/dungeon.lua` : branche, profondeur, probabilité. Après
`make install` dans les sources, il apparaît dans les nouvelles parties.

**Exporter.** `[w]` vers un nom en `.txt` écrit la carte seule ; vers un
`.svg` ou un `.png`, une image de la carte telle qu'elle est affichée
(essayez avec `[J]`). `[o]` sur un `.txt` importe une carte dessinée dans
un éditeur de texte.

**Configuration.** Copiez `docs/config.exemple` dans
`~/.config/nhmapedit/config` et retirez les `#` des lignes voulues :
répertoire du jeu, taille par défaut des nouvelles cartes, couleurs des
terrains, raccourcis (par exemple `ctrl-z = u`), délai de la sauvegarde
de secours, langue.

**English.** L'interface existe en anglais : elle suit la locale, ou
`NHMAPEDIT_LANG=en python3 nhmapedit.py`.

Bonne construction de niveaux, et méfiez-vous des chacals endormis !
