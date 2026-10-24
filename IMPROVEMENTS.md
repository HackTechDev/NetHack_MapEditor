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
| 1. Couverture du format Lua | 0 / 5 | régions, entités manquantes, plusieurs cartes, `contents`, éléments aléatoires |
| 2. Affichage | 5 / 5 | — |
| 3. Outils d'édition | 8 / 9 | générateurs |
| 4. Entités | 4 / 4 | — |
| 5. Vérification | 3 / 3 | — |
| 6. Intégration avec le jeu | 3 / 3 | — |
| 7. Fichiers et formats | 4 / 4 | — |
| 8. Configuration et confort | 3 / 3 | — |
| 9. Qualité du projet | 2 / 4 | intégration continue, paquet installable |
| 10. Nouvelles idées | 0 / 6 | toutes |

Prochaines étapes conseillées : les **régions** (thème 1), présentes dans
presque tous les niveaux de `dat/`, puis l'**intégration continue**, peu
coûteuse maintenant que les tests existent.

## 1. Couverture du format Lua des niveaux

Aujourd'hui, l'éditeur ne gère que la première `des.map()` et les entités à
coordonnées fixes qui la suivent. Le reste du script est conservé, mais il
reste invisible dans l'éditeur.

- **Régions** **[moyen]** : afficher et éditer `des.region()` (zones
  éclairées ou sombres, salles typées : temple, boutique, zoo…),
  `des.non_diggable()`, `des.non_passwall()`, `des.teleport_region()` et
  `des.levregion()`. On les montrerait sous forme de rectangles en
  surimpression, avec une touche pour passer d'un calque à l'autre. Ce
  sont des éléments clés de presque tous les niveaux de `dat/`.
- **Entités manquantes** **[facile]** : `des.gold()`, `des.grave()`,
  `des.drawbridge()`, `des.feature()` (avec ses options `looted`,
  `swarm`…) et `des.terrain()` sur une seule case.
- **Plusieurs cartes par fichier** **[gros]** : beaucoup de niveaux
  (Vlad, Sokoban, les quêtes…) enchaînent plusieurs `des.map()`. On
  pourrait proposer un onglet ou une liste des cartes, chacune avec ses
  propres entités, et afficher leur position les unes par rapport aux
  autres.
- **Contenu des fonctions `contents`** **[gros]** : éditer les entités
  déclarées dans `des.map({ ..., contents = function() ... end })` et
  `des.room()`, dont les coordonnées sont relatives à la carte ou à la
  salle.
- **Éléments aléatoires** **[moyen]** : signaler visuellement dans la
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
- **Générateurs** **[gros]** : labyrinthe (comme `des.mazewalk()`),
  grottes de type « mines », placement automatique de salles reliées par
  des couloirs.

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

- **Calques d'affichage** **[moyen]** : une touche pour n'afficher que le
  terrain, que les entités ou que les régions (quand elles seront
  gérées), utile sur les niveaux très chargés.
- **Autres langues** **[facile]** : le mécanisme de traduction
  (`nhi18n.py`) accepte d'autres catalogues que l'anglais ; il suffirait
  d'un fichier `nhi18n_xx.py` et de l'ajouter au choix de la langue.
- **Souris dans les fenêtres** **[facile]** : choisir dans les listes et
  les formulaires d'un clic, faire défiler à la molette.
- **Raccourcis vers les modèles** **[facile]** : associer un modèle
  favori à une touche dans le fichier de configuration.
- **Couverture des tests** **[facile]** : mesurer la part du code
  exercée par les tests (module `trace` de la bibliothèque standard) et
  ajouter des tests pour les fenêtres de saisie.
- **Comparaison de versions** **[moyen]** : afficher les cases qui
  diffèrent entre la carte en cours et le fichier enregistré (ou la
  version d'origine `fichier.lua~`).
