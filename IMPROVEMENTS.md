# Améliorations possibles

Idées d'évolution pour nhmapedit, classées par thème. Chaque thème commence
par les améliorations les plus utiles, et chaque idée est marquée selon
l'effort qu'elle demande :
**[facile]** quelques heures, **[moyen]** une journée environ,
**[gros]** plusieurs jours.

Les idées réalisées sont marquées « ✅ **Fait** » ; la liste complète de
ce que fait l'éditeur aujourd'hui est dans [FEATURES.md](FEATURES.md).

## État d'avancement (2026-10-25)

| Thème | Fait | Reste |
|---|---|---|
| 1. Couverture du format Lua | 5 / 5 | — |
| 2. Affichage | 5 / 5 | — |
| 3. Outils d'édition | 9 / 11 | grottes, salles et couloirs |
| 4. Entités | 4 / 4 | — |
| 5. Vérification | 3 / 3 | — |
| 6. Intégration avec le jeu | 3 / 3 | — |
| 7. Fichiers et formats | 4 / 4 | — |
| 8. Configuration et confort | 3 / 3 | — |
| 9. Qualité du projet | 2 / 4 | intégration continue, paquet installable |
| 10. Nouvelles idées | 3 / 7 | langues, raccourcis, couverture, comparaison |
| 11. Idées supplémentaires | 6 / 12 | tirage, $EDITOR, `.des`, sélections, Sokoban, donjon |
| 12. Encore d'autres idées | 5 / 14 | voir la liste |

Prochaines étapes conseillées : l'**intégration continue**, peu coûteuse
maintenant que les tests existent, puis l'**aperçu d'un tirage** et
**Modifier dans `$EDITOR`** (thème 11), qui rendent visible ou modifiable
ce qui ne l'est pas encore.

## 1. Couverture du format Lua des niveaux

Au départ, l'éditeur ne gérait que la première `des.map()` et les entités
à coordonnées fixes qui la suivent ; le reste du script était conservé,
mais invisible dans l'éditeur.

- ✅ **Fait** — **Régions** **[moyen]** : afficher et éditer `des.region()` (zones
  éclairées ou sombres, salles typées : temple, boutique, zoo…),
  `des.non_diggable()`, `des.non_passwall()`, `des.teleport_region()` et
  `des.levregion()`. On les montrerait sous forme de rectangles en
  surimpression, avec une touche pour passer d'un calque à l'autre. Ce
  sont des éléments clés de presque tous les niveaux de `dat/`.
- ✅ **Fait** — **Entités manquantes** **[facile]** : `des.gold()`, `des.grave()`,
  `des.drawbridge()`, `des.feature()` (avec ses options `looted`,
  `swarm`…) et `des.terrain()` sur une seule case.
- ✅ **Fait** — **Plusieurs cartes par fichier** **[gros]** : beaucoup de niveaux
  (Vlad, Sokoban, les quêtes…) enchaînent plusieurs `des.map()`. On
  pourrait proposer un onglet ou une liste des cartes, chacune avec ses
  propres entités, et afficher leur position les unes par rapport aux
  autres.
- ✅ **Fait** — **Contenu des fonctions `contents`** **[gros]** : éditer les entités
  déclarées dans `des.map({ ..., contents = function() ... end })` et
  `des.room()`, dont les coordonnées sont relatives à la carte ou à la
  salle. Les entités et régions littérales de la fonction `contents` de
  la carte sont éditables comme celles qui la suivent (le reste de la
  fonction est recopié tel quel). `des.room()` reste hors de portée : les
  niveaux qui l'emploient (oracle, villes des Mines, niveaux de
  remplissage des quêtes) n'ont pas de `des.map()` et la position des
  salles est tirée au sort par NetHack, il n'y a donc rien à dessiner.
- ✅ **Fait** — **Éléments aléatoires** **[moyen]** : signaler visuellement dans la
  carte les zones où des `des.monster()` ou `des.object()` sans
  coordonnées tomberont, quand une région ou une sélection est indiquée.

## 2. Affichage

- ✅ **Fait** — **Règles de coordonnées** **[facile]** : numéros de colonnes en haut
  et de lignes à gauche (les dizaines et les unités sur deux lignes).
  Indispensable pour relire ou écrire des coordonnées à la main.
- ✅ **Fait** — **Coordonnées absolues** **[facile]** : quand la carte est centrée
  (`halign`/`valign`), afficher dans la barre d'état la position réelle
  dans le niveau de 80x21, en plus de la position relative à la carte.
- ✅ **Fait** — **Rendu « comme dans le jeu »** **[moyen]** : une touche pour basculer
  vers un affichage proche du jeu. Les murs seraient dessinés en traits
  Unicode et les coins calculés comme le fait `wallification()`. Les
  portes secrètes et les couloirs secrets apparaîtraient comme des murs
  et de la roche, pour voir ce que le joueur découvrira.
- ✅ **Fait** — **Aperçu du retournement** **[facile]** : si le niveau n'a pas
  `noflip`, afficher un avertissement et proposer un aperçu en miroir
  (horizontal ou vertical), puisque NetHack retourne ces niveaux au
  hasard.
- ✅ **Fait** — **Index des entités par case** **[facile]** : `entities_at()` parcourt
  toute la liste pour chaque case affichée. Un dictionnaire
  `(x, y) -> [entités]` accélérerait l'affichage des niveaux très
  peuplés.

## 3. Outils d'édition

- ✅ **Fait** — **Pipette** **[facile]** : une touche (ou le clic droit) pour prendre
  comme pinceau le terrain sous le curseur.
- ✅ **Fait** — **Déplacer une zone** **[facile]** : couper, puis coller, en
  déplaçant aussi les entités. Aujourd'hui, il faut copier, coller, puis
  effacer à la main.
- ✅ **Fait** — **Retourner et faire pivoter le presse-papiers** **[facile]** : miroir
  horizontal ou vertical, rotation de 90° (en échangeant `-` et `|`).
- ✅ **Fait** — **Mode symétrie** **[moyen]** : chaque coup de pinceau est reproduit en
  miroir (axe vertical, horizontal ou les deux). Très pratique pour les
  niveaux symétriques comme le château ou les grandes salles.
- ✅ **Fait** — **Formes supplémentaires** **[facile]** : cercle et ellipse (pleins ou
  non), et remplissage aléatoire d'une zone à un pourcentage donné (pour
  des arbres, des rochers ou de l'eau éparse).
- ✅ **Fait** — **Rechercher et remplacer du terrain** **[facile]** : dans une zone ou
  sur toute la carte, comme `des.replace_terrain()`.
- ✅ **Fait** — **Insérer ou supprimer une ligne ou une colonne** **[facile]** : en
  décalant la carte et les entités.
- ✅ **Fait** — **Annulation par trait** **[facile]** : avec le crayon baissé, chaque
  déplacement crée aujourd'hui son propre point d'annulation. Il vaudrait
  mieux regrouper tout un trait en une seule étape.
- ✅ **Fait** — **Générateurs : labyrinthe** **[moyen]** : comme
  `des.mazewalk()`, dans une zone tracée (outil `Q`) : murs `-` et `|`,
  roche ou pinceau, passages en sol ou en couloir, boucles en %.
- **Générateurs : grottes** **[moyen]** : grottes de type « mines »
  (automate cellulaire), dans une zone. Le générateur existe pour une
  carte entière dans l'assistant de niveau (`nhgen.cave`) ; reste à en
  faire un outil sur une zone.
- **Générateurs : salles et couloirs** **[moyen]** : placement
  automatique de salles reliées par des couloirs. Même chose : fait pour
  une carte entière dans l'assistant (`nhgen.rooms_and_corridors`), pas
  encore sur une zone.

## 4. Entités

- ✅ **Fait** — **Formulaires d'options** **[moyen]** : remplacer la saisie libre
  `peaceful=1, asleep=1` par un formulaire à cases à cocher pour les
  options courantes. Pour les monstres : peaceful, asleep, female,
  invisible, name… Pour les objets : buc, spe, quantity, name,
  `achievement`…
- ✅ **Fait** — **Contenu des conteneurs et inventaire des monstres** **[gros]** :
  éditer les fonctions `contents` des coffres et l'`inventory` des
  monstres.
- ✅ **Fait** — **Plusieurs entités par case** **[facile]** : l'affichage ne montre
  qu'une entité par case (la plus prioritaire). Il faudrait signaler
  qu'il y en a plusieurs, par exemple en soulignant le symbole.
- ✅ **Fait** — **Monstres et objets aléatoires plus lisibles** **[facile]** : les
  symboles `M` et `]` sont arbitraires. Une couleur ou un style
  « aléatoire » commun serait plus clair.

## 5. Vérification

- ✅ **Fait** — **Connexité** **[moyen]** : vérifier par remplissage que l'escalier
  descendant est accessible depuis l'escalier montant, en tenant compte
  des portes et des couloirs secrets, de l'eau et de la lave. Signaler
  aussi les zones fermées.
- ✅ **Fait** — **Vérification avec le vrai Lua** **[moyen]** : exécuter le fichier
  avec l'interpréteur Lua de NetHack (`lib/lua-5.4.8`) et une
  bibliothèque `des` factice qui vérifie les paramètres. On attraperait
  les noms d'objets inconnus, les types de pièges invalides et les
  erreurs de syntaxe dans le code conservé, avant même de lancer le jeu.
- ✅ **Fait** — **Règles de NetHack** **[facile]** : porte sur un coin de mur, escalier
  dans l'eau, autel hors d'une salle `temple`, carte placée hors des
  limites une fois centrée…

## 6. Intégration avec le jeu

- ✅ **Fait** — **Lancer le jeu directement** **[moyen]** : la touche `t` copie le
  fichier, mais il faut encore lancer NetHack et taper `#wizloaddes`. On
  pourrait ouvrir le jeu dans un nouveau terminal ou un panneau tmux, et
  lui envoyer la commande automatiquement.
- ✅ **Fait** — **Éditer `dungeon.lua`** **[gros]** : ajouter un nouveau niveau
  spécial au donjon (branche, profondeur, probabilité) sans éditer le
  fichier à la main.
- ✅ **Fait** — **Salles à thème** **[gros]** : éditer les salles de `themerms.lua`,
  qui sont des `des.room()` et des `des.map()` dans des fonctions Lua.

## 7. Fichiers et formats

- ✅ **Fait** — **Import et export en texte brut** **[facile]** : coller ou exporter
  une carte ASCII seule, sans le Lua autour.
- ✅ **Fait** — **Export en image** **[facile]** : réutiliser `docs/capture.py` pour
  exporter la carte seule (en SVG ou en PNG) depuis l'éditeur, par
  exemple pour la partager.
- ✅ **Fait** — **Bibliothèque de modèles** **[moyen]** : des morceaux de carte prêts à
  coller (temple, boutique, puits, pont-levis, fontaine décorée…), rangés
  dans un dossier `modeles/`.
- ✅ **Fait** — **Enregistrement automatique** **[facile]** : une sauvegarde de secours
  régulière dans un fichier `.nhme-autosave`, proposée à la réouverture
  après un plantage.

## 8. Configuration et confort

- ✅ **Fait** — **Fichier de configuration** **[facile]** : `~/.config/nhmapedit/config`
  pour le répertoire du jeu (aujourd'hui, la variable
  `NHMAPEDIT_HACKDIR`), les couleurs, la taille par défaut et les
  raccourcis clavier.
- ✅ **Fait** — **Interface en anglais** **[moyen]** : choix de la langue selon `LANG`,
  pour une diffusion au-delà de la communauté francophone.
- ✅ **Fait** — **Aide contextuelle** **[facile]** : afficher dans la barre du bas les
  touches utiles pour l'outil en cours (ancre posée, collage…).

## 9. Qualité du projet

- ✅ **Fait** — **Tests automatiques** **[facile]** : transformer en tests `unittest`
  les vérifications faites à la main pendant le développement :
  aller-retour identique sur les 93 niveaux de `dat/`, export valide pour
  `luac`, outils de dessin…
- **Intégration continue** **[facile]** : une action GitHub qui lance ces
  tests à chaque push. Les niveaux de `dat/` seraient alors à télécharger
  depuis le dépôt officiel de NetHack, ou à embarquer comme échantillons.
- **Paquet installable** **[facile]** : un `pyproject.toml` avec une
  commande `nhmapedit`, pour l'installer avec `pipx install`.
- ✅ **Fait** — **Découpage de `nhmapedit.py`** **[moyen]** : le fichier dépassait
  1 400 lignes. Il est séparé en plusieurs fichiers : affichage,
  fenêtres de saisie, outils et entités (`nhme_*.py`) ; `nhmapedit.py`
  ne garde que la boucle des touches et la souris (environ 360 lignes).

## 10. Nouvelles idées

Idées apparues pendant le développement des thèmes précédents.

- ✅ **Fait** — **Historique des commandes** **[moyen]** : chaque point
  d'annulation porte le nom de sa commande (« Salle : sol », « Ajout :
  escalier up »…), la touche `V` affiche la liste et ramène la carte à
  n'importe quel état ; l'annulation couvre aussi les propriétés du
  niveau, ramène le curseur et rétablit l'état « non modifié ».

- ✅ **Fait** — **Calques d'affichage** **[moyen]** : une touche pour n'afficher que le
  terrain, que les entités ou que les régions (quand elles seront
  gérées), utile sur les niveaux très chargés. Touche `;` : un calque à
  cocher par élément (terrain, entités, chaque famille de régions,
  placements aléatoires) et des préréglages.
- **Autres langues** **[facile]** : le mécanisme de traduction
  (`nhi18n.py`) accepte d'autres catalogues que l'anglais ; il suffirait
  d'un fichier `nhi18n_xx.py` et de l'ajouter au choix de la langue.
- ✅ **Fait** — **Souris dans les fenêtres** **[facile]** : choisir dans les listes et
  les formulaires d'un clic, faire défiler à la molette. Un second clic
  sur la ligne choisie la valide, le clic droit annule.
- **Raccourcis vers les modèles** **[facile]** : associer un modèle
  favori à une touche dans le fichier de configuration.
- **Couverture des tests** **[facile]** : mesurer la part du code
  exercée par les tests (module `trace` de la bibliothèque standard) et
  ajouter des tests pour les fenêtres de saisie.
- **Comparaison de versions** **[moyen]** : afficher les cases qui
  diffèrent entre la carte en cours et le fichier enregistré (ou la
  version d'origine `fichier.lua~`).

## 11. Idées supplémentaires

Idées proposées après la couverture complète du format Lua, des plus
utiles aux plus accessoires.

- **Aperçu d'un tirage** **[moyen]** : exécuter le script avec la
  bibliothèque `des` factice de la vérification (`nhcheck_des.lua`) et
  montrer un exemple du niveau tel que NetHack pourrait le générer :
  monstres et objets aléatoires placés, `?` résolus. Une touche relance
  un autre tirage.
- **Modifier dans `$EDITOR`** **[facile]** : sur un élément non
  modifiable (région écrite avec du code, placement aléatoire), ouvrir
  l'appel Lua dans l'éditeur de texte, puis relire le fichier au retour.
  Une porte de sortie pour tout ce que l'éditeur ne sait pas traiter.
- **Import des fichiers `.des` de NetHack 3.6** **[moyen]** : lire
  l'ancien format (`MAP … ENDMAP`, `MONSTER:`, `OBJECT:`, `TRAP:`,
  `REGION:`…), encore employé par beaucoup de variantes et de cartes de
  la communauté, et l'enregistrer en Lua.
- **Sélections littérales** **[moyen]** : afficher et éditer les zones
  de `des.replace_terrain()` et de `des.terrain(selection.area(...), "L")`,
  comme les régions.
- ✅ **Fait** — **Murs automatiques** **[moyen]** : un pinceau « mur » qui choisit `-`
  ou `|` selon les voisins, et une commande qui corrige les murs d'une
  zone.
- ✅ **Fait** — **Rechercher et remplacer des entités** **[facile]** : changer tous les
  « orc » en « hill orc », rendre `asleep` tous les monstres d'une zone…
- ✅ **Fait** — **Sélection multiple d'entités** **[moyen]** : déplacer, copier ou
  supprimer d'un coup les entités d'un rectangle, sans toucher au
  terrain.
- ✅ **Fait** — **Vérifications supplémentaires** **[facile]** : région ou zone
  d'arrivée hors du niveau de 80x21, objet ou monstre enfermé dans une
  zone inaccessible, boutique (`shop`) sans porte unique.
- **Règles de Sokoban** **[facile]** : compter rochers et trous, signaler
  un niveau manifestement insoluble.
- ✅ **Fait** — **Statistiques du niveau** **[facile]** : nombre de monstres par
  classe, d'objets et de pièges, placements fixes et aléatoires à part.
- ✅ **Fait** — **Mini-carte** **[facile]** : quand la carte dépasse l'écran, un petit
  aperçu montrant la partie visible.
- **Vue du donjon** **[moyen]** : schéma de `dungeon.lua` (branches,
  profondeurs, niveaux spéciaux) depuis lequel ouvrir un niveau.

## 12. Encore d'autres idées

Idées proposées après la deuxième série d'idées supplémentaires, des
plus utiles aux plus accessoires.

- ✅ **Fait** — **Retour du jeu** **[moyen]** : après un essai avec `t`, récupérer les
  messages d'erreur de NetHack (journal de `#wizloaddes`) et les afficher
  dans l'éditeur, en sautant à la ligne fautive.
- ✅ **Fait** — **Assistant de niveau** **[moyen]** : un niveau prêt à essayer en
  quelques questions (type de niveau, taille, salles, nombre de
  monstres), construit avec les générateurs existants et retouché
  ensuite à la main.
- ✅ **Fait** — **Difficulté estimée** **[moyen]** : additionner le niveau des monstres
  placés (`mlevel`, extrait des sources de NetHack) et indiquer à quelle
  profondeur le niveau conviendrait, en complément des statistiques.
- **Équilibre des objets** **[facile]** : signaler les objets puissants
  posés en clair (baguette de vœu, artefacts) et ceux qu'aucun chemin ne
  permet d'atteindre.
- **Mode « partie rapide »** **[moyen]** : lancer NetHack directement
  sur le niveau, sans menu ni `#wizloaddes`, avec un héros prêt à jouer
  (option de la branche cybernethack si elle existe, sinon une
  sauvegarde préparée).
- ✅ **Fait** — **Annotations** **[facile]** : attacher un commentaire Lua à une case
  ou à une entité (`-- trésor caché ici`), conservé dans le fichier et
  visible au survol.
- ✅ **Fait** — **Calques de travail** **[moyen]** : dessiner sur une couche brouillon
  non enregistrée (notes, repères, cases réservées), affichée en
  surimpression.
- **Tampons de terrain** **[facile]** : petits motifs prêts à poser, plus
  légers que les modèles (pilier 2x2, colonnade, fontaine entourée de
  sol, coin de rivière).
- **Remplissage par motif** **[facile]** : remplir une zone d'un damier
  ou de rayures (`.` et `}`, par exemple) plutôt que d'un seul terrain.
- **Export HTML** **[facile]** : une page autonome avec la carte en
  couleur et la liste des entités au survol, pour partager un niveau sur
  un forum ou un wiki.
- **Gestion d'un dossier de niveaux** **[moyen]** : ouvrir un dossier
  entier (`dat/` ou un projet), passer d'un fichier à l'autre, et
  chercher par exemple « quels niveaux contiennent un trône ? ».
- **Historique persistant** **[moyen]** : garder l'historique des
  commandes entre deux sessions (`fichier.lua.nhme-history`), pour
  annuler encore après avoir rouvert le fichier.
- **Tests de non-régression sur les niveaux** **[facile]** : conserver
  pour chaque niveau de `dat/` un résumé (entités, régions, placements
  aléatoires) et vérifier qu'il ne change pas d'une version de l'éditeur
  à l'autre.
- **Profilage** **[facile]** : mesurer le temps d'affichage des grandes
  cartes chargées de régions, et mettre en cache le calque et la
  mini-carte si nécessaire.
