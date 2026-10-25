"""English translation of the interface (see nhi18n).

Keys are the French texts of the source code, exactly as written in the
_() calls; tests/test_i18n.py checks that none is missing.
"""

EN = {
    # nhmapedit.py
    "nhmapedit — petit éditeur de cartes NetHack en mode terminal.\n\n"
    "Usage : python3 nhmapedit.py [fichier.lua] [--new LARGEURxHAUTEUR]\n\n"
    "Appuyez sur « ? » dans l'éditeur pour l'aide.":
        "nhmapedit — a small terminal map editor for NetHack.\n\n"
        "Usage: python3 nhmapedit.py [file.lua] [--new WIDTHxHEIGHT]\n\n"
        "Press '?' in the editor for help.",
    "Bienvenue ! « ? » pour l'aide.": "Welcome! '?' for help.",
    "Configuration : %s": "Configuration: %s",
    "Nouveau fichier : %s": "New file: %s",
    "Annulé.": "Cancelled.",
    "--new attend LARGEURxHAUTEUR, ex: --new 40x12":
        "--new expects WIDTHxHEIGHT, e.g. --new 40x12",
    "Tracé annulé.": "Drawing cancelled.",
    "Outil Pinceau.": "Pen tool.",
    "Outil : %s.": "Tool: %s.",
    " (presse-papiers vide)": " (clipboard empty)",
    "Densité du semis en %% (1-100) : ": "Scatter density in %% (1-100): ",
    "Pinceau : %s.": "Brush: %s.",
    "Densité invalide.": "Invalid density.",
    "Crayon baissé.": "Pen down.",
    "Crayon levé.": "Pen up.",
    "Symétrie désactivée.": "Symmetry off.",
    "Symétrie : %s.": "Symmetry: %s.",
    "Avance automatique %s.": "Auto advance %s.",
    "activée": "on",
    "désactivée": "off",
    "Aucune entité à répéter (m pour en placer une).":
        "No entity to repeat (m to place one).",
    "Rendu « comme dans le jeu ».": "Rendered as in the game.",
    "Rendu des caractères de carte (des.map).":
        "Rendered as map characters (des.map).",
    "Carte affichée dans son sens d'origine.":
        "Map shown in its original orientation.",
    "Aperçu retourné : %s. %s": "Flip preview: %s. %s",
    "Règles de coordonnées %s.": "Coordinate rulers %s.",
    "affichées": "shown",
    "masquées": "hidden",
    "NetHack peut le faire au chargement.": "NetHack may do it on load.",
    "Empêché par les drapeaux du niveau (noflip...).":
        "Prevented by the level flags (noflip...).",
    "Aller à « x y » : ": "Go to 'x y': ",
    "Position invalide.": "Invalid position.",
    "Ouvrir : ": "Open: ",
    "Aide": "Help",
    "Quitter sans enregistrer ?": "Quit without saving?",

    # nhme_common.py
    "aucun": "none",
    "vertical": "vertical",
    "horizontal": "horizontal",
    "horizontal et vertical": "horizontal and vertical",
    "haut/bas": "top/bottom",
    "gauche/droite": "left/right",
    "les deux axes": "both axes",
    "roche": "stone",
    "sol": "floor",
    "mur -": "wall -",
    "mur |": "wall |",
    "porte sec.": "sec. door",
    "coul. sec.": "sec. corr.",
    "bassin": "pool",
    "eau": "water",
    "mur lave": "lava wall",
    "barreaux": "bars",
    "limite": "boundary",
    "transp.": "transp.",
    "Pinceau": "Pen",
    "Ligne": "Line",
    "Rectangle": "Rectangle",
    "Rectangle plein": "Filled rectangle",
    "Rect plein": "Filled rect",
    "Salle": "Room",
    "Remplissage": "Flood fill",
    "Remplir": "Fill",
    "Copier zone": "Copy area",
    "Copier": "Copy",
    "Coller": "Paste",
    "Ellipse": "Ellipse",
    "Ellipse pleine": "Filled ellipse",
    "Ell. pleine": "Filled ell.",
    "Couper (déplacer) zone": "Cut (move) area",
    "Couper": "Cut",
    "Semis aléatoire": "Random scatter",
    "Semis": "Scatter",
    "Remplacer du terrain": "Replace terrain",
    "Remplacer": "Replace",
    "pacifique": "peaceful",
    "endormi": "asleep",
    "femelle": "female",
    "invisible": "invisible",
    "annulé": "cancelled",
    "attend le héros": "waits for the hero",
    "nom": "name",
    "apparence (obj:…, mon:…, ter:…)": "appearance (obj:…, mon:…, ter:…)",
    "ajustement du niveau": "level adjustment",
    "inventaire": "inventory",
    "garde l'inventaire par défaut": "keeps the default inventory",
    "béni / maudit": "blessed / cursed",
    "enchantement, charges": "enchantment, charges",
    "quantité": "quantity",
    "succès (achievement)": "achievement",
    "monstre (statue, cadavre…)": "monster (statue, corpse…)",
    "contenu (conteneur, statue)": "contents (container, statue)",
    "enterré": "buried",
    "verrouillé": "locked",
    "piégé": "trapped",
    "érosion": "erosion",
    "graissé": "greased",
    "allumé": "lit",

    # nhlevel.py
    "escalier": "stairs",
    "échelle": "ladder",
    "autel": "altar",
    "monstre": "monster",
    "objet": "object",
    "piège": "trap",
    "porte": "door",
    "gravure": "engraving",
    "roche (pierre pleine)": "stone (solid rock)",
    "sol de salle": "room floor",
    "couloir": "corridor",
    "mur horizontal / coin": "horizontal wall / corner",
    "mur vertical": "vertical wall",
    "porte secrète": "secret door",
    "couloir secret": "secret corridor",
    "fontaine": "fountain",
    "trône": "throne",
    "évier": "sink",
    "douves": "moat",
    "bassin d'eau": "pool",
    "eau (plan de l'Eau)": "water (Plane of Water)",
    "lave": "lava",
    "mur de lave": "lava wall",
    "glace": "ice",
    "arbre": "tree",
    "barreaux de fer": "iron bars",
    "air": "air",
    "nuage": "cloud",
    "limite (crosswall)": "boundary (crosswall)",
    "transparent (garde l'existant)": "transparent (keeps what is there)",
    "aucun appel des.map() trouvé dans ce fichier":
        "no des.map() call found in this file",
    " (classe, aléatoire)": " (class, random)",
    " aléatoire": " random",
    "(%d objets)": "(%d objects)",
    "(%d objet)": "(%d object)",

    # nhcheck.py
    "dans les deux sens": "both ways",
    "! Porte en (%d,%d) dans un coin de mur.":
        "! Door at (%d,%d) in a wall corner.",
    "? Porte en (%d,%d) qui n'est pas encadrée par des murs.":
        "? Door at (%d,%d) not set between walls.",
    "montant": "up",
    "descendant": "down",
    "Aucun problème détecté.": "No problem found.",
    " ; elle touche le bord de la carte et peut être reliée au reste du "
    "niveau":
        "; it touches the map edge and may be joined to the rest of the "
        "level",
    "! Largeur %d > %d (MAP_X_LIM) : risque de refus par NetHack.":
        "! Width %d > %d (MAP_X_LIM): NetHack may refuse it.",
    "- NetHack peut retourner ce niveau au chargement (%s) : f pour un "
    "aperçu, drapeau noflip pour l'empêcher.":
        "- NetHack may flip this level on load (%s): f for a preview, "
        "noflip flag to prevent it.",
    "sources de Lua introuvables dans %s/lib":
        "Lua sources not found in %s/lib",
    "? Zone fermée de %d case(s), par exemple en (%d,%d)%s.":
        "? Closed area of %d cell(s), for instance at (%d,%d)%s.",
    "? … et %d autre(s) zone(s) séparée(s).":
        "? … and %d other separate area(s).",
    "! La carte placée en (%d,%d) déborde du niveau (80x21).":
        "! The map placed at (%d,%d) overflows the level (80x21).",
    "- Pas d'escalier/échelle %s à position fixe (peut être placé ailleurs "
    "dans le script).":
        "- No stairs/ladder %s at a fixed position (may be placed elsewhere "
        "in the script).",
    "? %s en (%d,%d) hors de la carte (invisible dans l'éditeur).":
        "? %s at (%d,%d) outside the map (not shown in the editor).",
    "? Autel en (%d,%d) hors d'une salle temple (des.region type "
    "« temple ») : pas de prêtre.":
        "? Altar at (%d,%d) outside a temple room (des.region type "
        "'temple'): no priest.",
    "? Monstre inconnu : %s": "? Unknown monster: %s",
    "? Objet inconnu (vérifiez le nom) : %s":
        "? Unknown object (check the name): %s",
    "! %s %s présent %d fois : un seul est permis par niveau.":
        "! %s %s present %d times: only one is allowed per level.",
    "%s Lua, %s": "%s Lua, %s",
    "- Connexité : l'escalier descendant (%d,%d) n'est accessible que par "
    "un passage secret (S ou H).":
        "- Connectivity: the down stairs (%d,%d) can only be reached "
        "through a secret passage (S or H).",
    "- Zone de %d case(s), par exemple en (%d,%d), accessible seulement par "
    "l'eau ou la lave.":
        "- Area of %d cell(s), for instance at (%d,%d), only reachable "
        "across water or lava.",
    "? Porte en (%d,%d) sur '%s'.": "? Door at (%d,%d) on '%s'.",
    "! %s en (%d,%d) sur du terrain solide '%s'.":
        "! %s at (%d,%d) on solid terrain '%s'.",
    "? Lua : impossible de lancer %s (%s).": "? Lua: cannot run %s (%s).",
    "? Lua : ": "? Lua: ",
    "? Connexité : l'escalier descendant (%d,%d) n'est accessible qu'en "
    "traversant l'eau ou la lave.":
        "? Connectivity: the down stairs (%d,%d) can only be reached "
        "across water or lava.",
    "! Connexité : l'escalier descendant (%d,%d) est inaccessible depuis "
    "le montant (%d,%d).":
        "! Connectivity: the down stairs (%d,%d) cannot be reached from "
        "the up stairs (%d,%d).",
    "! %s en (%d,%d) dans '%s' (%s).": "! %s at (%d,%d) in '%s' (%s).",
    "? %s en (%d,%d) sur '%s' : le terrain sera remplacé.":
        "? %s at (%d,%d) on '%s': the terrain will be replaced.",

    # nhconfig.py
    "terrain inconnu": "unknown terrain",
    "clé inconnue": "unknown key",
    "[%s] : section inconnue": "[%s]: unknown section",
    "LARGEURxHAUTEUR attendu": "WIDTHxHEIGHT expected",
    "oui ou non attendu": "yes or no expected",
    "couleur inconnue (%s)": "unknown color (%s)",
    "touche invalide %s": "invalid key %s",
    "auto, oui ou non attendu": "auto, yes or no expected",
    "nombre de secondes attendu (0 : désactivée)":
        "number of seconds expected (0: off)",
    "fr, en ou auto attendu": "fr, en or auto expected",

    # nhdungeon.py
    "table « dungeon = { ... } » introuvable ou trop complexe":
        "table 'dungeon = { ... }' not found or too complex",
    "nom manquant": "missing name",
    "base manquante": "missing base",
    "bonetag : un seul caractère": "bonetag: a single character",
    "le niveau %s existe déjà": "level %s already exists",
    "chainlevel %s : niveau inconnu ou défini plus loin":
        "chainlevel %s: unknown level or defined further down",
    "plus de %d niveaux spéciaux": "more than %d special levels",
    "nom trop long : %s (%d caractères au plus)":
        "name too long: %s (%d characters at most)",

    # nhexport.py
    "carte vide": "empty map",
    "carte de %dx%d : %dx%d au plus": "%dx%d map: %dx%d at most",
    "caractères inconnus : %s": "unknown characters: %s",
    "conversion en PNG : %s": "PNG conversion: %s",
    "export PNG : installez rsvg-convert (librsvg) ou ImageMagick, ou "
    "exportez en .svg":
        "PNG export: install rsvg-convert (librsvg) or ImageMagick, or "
        "export to .svg",

    # nhtheme.py
    "pas de table « themerooms = { ... } »": "no 'themerooms = { ... }' table",
    "table themerooms non terminée": "unterminated themerooms table",

    # nhme_dialogs.py
    " Échap/q: fermer ": " Esc/q: close ",
    "texte": "text",
    "entier": "integer",
    "entier ou random": "integer or random",
    "Filtre : ": "Filter: ",
    "Entrée: choisir  Échap: annuler": "Enter: choose  Esc: cancel",
    " ↑↓ défiler": " ↑↓ scroll",
    " (o/n) ": " (y/n) ",
    "Terminer": "Done",
    "(défaut)": "(default)",
    "%s (Entrée: modifier, Échap: terminer)": "%s (Enter: change, Esc: done)",
    "%s (Entrée: cocher/décocher, Échap: terminer)":
        "%s (Enter: check/uncheck, Esc: done)",
    "Valeur invalide : %s attendu.": "Invalid value: %s expected.",
    "oui": "yes",
    "non": "no",
    "Autres options : %s": "Other options: %s",
    "%s (%s, vide = défaut) : ": "%s (%s, empty = default): ",
    "(aucune)": "(none)",
    "Monstre (tapez pour filtrer ; une lettre seule = classe)":
        "Monster (type to filter; a single letter = class)",
    "aléatoire": "random",

    # nhme_display.py
    " ?:aide  1-0 D G R:outils  m:entité  i:liste  p:propriétés  t:tester  "
    "s:enregistrer  q:quitter":
        " ?:help  1-0 D G R:tools  m:entity  i:list  p:properties  t:test  "
        "s:save  q:quit",
    "(sans nom)": "(untitled)",
    "Outils": "Tools",
    "Terrain": "Terrain",
    "(%2d,%2d) niveau %s  '%s' %s": "(%2d,%2d) level %s  '%s' %s",
    "Outil: %s   Pinceau: %s (%s)": "Tool: %s   Brush: %s (%s)",
    "   [crayon baissé]": "   [pen down]",
    "   [avance auto]": "   [auto advance]",
    "   [entités masquées]": "   [entities hidden]",
    "   [rendu jeu]": "   [game view]",
    " Espace/Entrée: tracer jusqu'au curseur  flèches/souris: 2e point  "
    "Échap: annuler l'ancre":
        " Space/Enter: draw to the cursor  arrows/mouse: 2nd point  "
        "Esc: cancel the anchor",
    " Crayon baissé : flèches = peindre  caractère = pinceau  d: lever  "
    "u: annuler le trait":
        " Pen down: arrows = paint  character = brush  d: lift  "
        "u: undo the stroke",
    " Espace: remplir la zone sous le curseur avec le pinceau  y: pipette  "
    "u: annuler":
        " Space: fill the area under the cursor with the brush  "
        "y: eyedropper  u: undo",
    " m: ajouter  z: supprimer  i: liste (e: modifier)  r: répéter  "
    "Tab: masquer les entités":
        " m: add  z: delete  i: list (e: edit)  r: repeat  "
        "Tab: hide entities",
    " Rendu jeu :  J: revenir aux caractères de carte  f: retournement  "
    "?: aide":
        " Game view:  J: back to map characters  f: flip  ?: help",
    "Terminal trop petit (min. 40x12)": "Terminal too small (min. 40x12)",
    " : salle « %s »": ": room '%s'",
    "  (retournable : %s, f pour voir)": "  (flippable: %s, f to see)",
    "   ancre (%d,%d) -> %dx%d": "   anchor (%d,%d) -> %dx%d",
    "   [aperçu retourné : %s]": "   [flip preview: %s]",
    "   [symétrie : %s]": "   [symmetry: %s]",
    " Presse-papiers vide :  7: copier  D: couper  b: modèle  "
    "Échap: Pinceau":
        " Clipboard empty:  7: copy  D: cut  b: template  Esc: Pen",
    " Espace: coller (%dx%d, coin haut-gauche au curseur)  X/Y: miroir  "
    "O: rotation  b: modèles  Échap: Pinceau":
        " Space: paste (%dx%d, top-left corner at the cursor)  X/Y: mirror"
        "  O: rotate  b: templates  Esc: Pen",
    "  (R : autre remplacement)": "  (R: another replacement)",
    " Espace: poser l'ancre (1er coin)  caractère: pinceau  M: symétrie  "
    "u: annuler":
        " Space: set the anchor (1st corner)  character: brush  "
        "M: symmetry  u: undo",
    " [modifié]": " [modified]",
    "  (densité %d %%)": "  (density %d %%)",

    # nhme_entities.py
    "Syntaxe invalide : clé = valeur, séparées par des virgules.":
        "Invalid syntax: key = value, separated by commas.",
    "Entrée/e: modifier  d: supprimer  Échap: terminer":
        "Enter/e: edit  d: delete  Esc: done",
    "Salle à thème : seule la carte est enregistrée, pas les entités.":
        "Themed room: only the map is saved, not the entities.",
    "Ajouté : %s (r pour répéter).": "Added: %s (r to repeat).",
    "Aucune entité ici.": "No entity here.",
    "%d entité(s) supprimée(s).": "%d entity(ies) deleted.",
    "Entrée: aller  e: modifier  d: supprimer  Échap: fermer":
        "Enter: go  e: edit  d: delete  Esc: close",
    "Options Lua (ex: peaceful=1, asleep=1) : ":
        "Lua options (e.g. peaceful=1, asleep=1): ",
    "Options du monstre": "Monster options",
    "Options de l'objet": "Object options",
    "Direction": "Direction",
    "Placer une entité en (%d,%d)": "Place an entity at (%d,%d)",
    "Aucune entité.": "No entities.",
    "+ ajouter un objet": "+ add an object",
    "Alignement de l'autel": "Altar alignment",
    "Type d'autel": "Altar type",
    "Supprimé : %s": "Deleted: %s",
    "- retirer l'option": "- remove the option",
    "montant (up)": "up",
    "descendant (down)": "down",
    "Modifié : %s": "Changed: %s",
    "Objet (tapez pour filtrer ; un symbole seul = classe)":
        "Object (type to filter; a single symbol = class)",
    "(aléatoire)": "(random)",
    "Type de piège": "Trap type",
    "État de la porte": "Door state",
    "Type de gravure": "Engraving type",
    "Texte gravé : ": "Engraved text: ",

    # nhme_game.py
    "Lancement de NetHack…": "Starting NetHack…",
    "Fichier dungeon.lua (dans dat/ des sources) : ":
        "dungeon.lua file (in dat/ of the sources): ",
    "Entrée/e: modifier  d: supprimer  Échap: retour":
        "Enter/e: edit  d: delete  Esc: back",
    "Enregistré : %s": "Saved: %s",
    "Niveau ajouté au donjon": "Level added to the dungeon",
    "Copié pour test : %s": "Copied for testing: %s",
    "Tester dans NetHack": "Test in NetHack",
    "Tester une salle à thème": "Test a themed room",
    "Une partie lancée par l'éditeur est en cours : quittez-la pour "
    "relancer avec THEMERM.":
        "A game started by the editor is running: quit it to restart "
        "with THEMERM.",
    "Une partie de NetHack est déjà en cours.":
        "A NetHack game is already running.",
    "Impossible de lancer le jeu dans tmux.":
        "Cannot start the game in tmux.",
    "Carte chargée dans NetHack (%s, %s) ; t la recharge après une "
    "modification.":
        "Map loaded in NetHack (%s, %s); t reloads it after a change.",
    "nom du fichier, sans .lua": "file name, without .lua",
    "profondeur (négatif : depuis le bas)": "depth (negative: from the bottom)",
    "profondeur : tirage en plus": "depth: random extra",
    "probabilité de présence, en %": "chance of being present, in %",
    "variantes (nom-1.lua … nom-N.lua)": "variants (name-1.lua … name-N.lua)",
    "alignement": "alignment",
    "drapeaux": "flags",
    "lettre des fichiers bones": "bones file letter",
    "base comptée depuis ce niveau": "base counted from this level",
    "Niveau du donjon": "Dungeon level",
    "Répertoire de données de NetHack (nethackdir) : ":
        "NetHack data directory (nethackdir): ",
    "Lancer NetHack (mode wizard) et y charger la carte ?":
        "Start NetHack (wizard mode) and load the map into it?",
    "Lancer NetHack avec THEMERM=%s (après make install) ?":
        "Start NetHack with THEMERM=%s (after make install)?",
    "Pas d'exécutable nethack dans %s.": "No nethack executable in %s.",
    "panneau tmux à droite": "tmux pane on the right",
    "fenêtre tmux « nethack »": "tmux window 'nethack'",
    "session tmux « %s »": "tmux session '%s'",
    "Le jeu s'est arrêté au démarrage.": "The game stopped at startup.",
    "NetHack lancé": "NetHack started",
    "+ ajouter ce niveau": "+ add this level",
    "Erreur d'écriture : %s": "Write error: %s",
    "Copier la carte dans %s/%s.lua ?": "Copy the map to %s/%s.lua?",
    "%s : ni nhdat ni sysconf, répertoire refusé.":
        "%s: neither nhdat nor sysconf, directory refused.",
    "Carte copiée (état actuel, même non enregistré) dans :":
        "Map copied (current state, even unsaved) to:",
    "Dans un autre terminal :": "In another terminal:",
    "  1. lancez le jeu en mode wizard :  nethack -D":
        "  1. start the game in wizard mode:  nethack -D",
    "  2. tapez  #wizloaddes  puis Entrée": "  2. type  #wizloaddes  then Enter",
    "Après une modification, appuyez de nouveau sur t puis":
        "After a change, press t again then",
    "refaites #wizloaddes : inutile de relancer le jeu.":
        "redo #wizloaddes: no need to restart the game.",
    "Ctrl-F révèle toute la carte, Ctrl-T téléporte.":
        "Ctrl-F reveals the whole map, Ctrl-T teleports.",
    "(La copie de test a le drapeau noflip : sinon NetHack":
        "(The test copy has the noflip flag: otherwise NetHack",
    "retourne la carte au hasard à chaque chargement.)":
        "flips the map at random on each load.)",
    "Avec tmux installé, l'éditeur peut lancer le jeu et":
        "With tmux installed, the editor can start the game and",
    "charger la carte lui-même.": "load the map itself.",
    "themerms.lua est rangé dans nhdat : le jeu ne lit pas une":
        "themerms.lua is stored in nhdat: the game does not read a",
    "  1. enregistrez (s) : la carte est écrite dans":
        "  1. save (s): the map is written to",
    "  2. dans les sources, lancez « make install » ;":
        "  2. in the sources, run 'make install';",
    "  3. lancez le jeu en mode wizard avec la variable THEMERM :":
        "  3. start the game in wizard mode with the THEMERM variable:",
    "Chaque salle des niveaux ordinaires est alors cette salle,":
        "Every room of the ordinary levels is then this room,",
    "quand elle y tient. Ctrl-F révèle la carte, Ctrl-V change de":
        "when it fits. Ctrl-F reveals the map, Ctrl-V changes",
    "niveau pour en générer d'autres.": "level to generate others.",
    "NetHack lancé avec THEMERM=%s (%s).": "NetHack started with THEMERM=%s (%s).",
    "%-24s %d niveau(x) spécial(aux)": "%-24s %d special level(s)",
    "Donjons de %s (%d niveaux spéciaux sur %d)":
        "Dungeons of %s (%d special levels out of %d)",
    "%s. Corriger ?": "%s. Fix it?",
    "Pour le jouer :": "To play it:",
    "     (le jeu la lit là, puisqu'elle n'est pas dans nhdat) ;":
        "     (the game reads it there, since it is not in nhdat);",
    "  2. dans les sources, « make install » range le nouveau":
        "  2. in the sources, 'make install' stores the new",
    "     dungeon.lua dans nhdat ;": "     dungeon.lua in nhdat;",
    "  3. commencez une nouvelle partie (les parties en cours":
        "  3. start a new game (games in progress",
    "     gardent l'ancien donjon). En mode wizard, #wizwhere":
        "     keep the old dungeon). In wizard mode, #wizwhere",
    "     donne la profondeur des niveaux spéciaux et Ctrl-V":
        "     gives the depth of the special levels and Ctrl-V",
    "     téléporte de niveau.": "     level-teleports.",
    "  3. répondez :  ": "  3. answer:  ",
    "copie posée à côté. Pour voir la salle « %s » :":
        "copy placed next to it. To see the room '%s':",
    "Pour le voir, dans un autre terminal :": "To see it, in another terminal:",
    "%s existe. Écraser ?": "%s exists. Overwrite?",
    "%s ajouté à « %s » dans :": "%s added to '%s' in:",
    "Avec nlevels, il faut un fichier par variante :":
        "With nlevels, one file per variant is needed:",
    "Le jeu tourne dans la session tmux « %s ».":
        "The game runs in the tmux session '%s'.",
    "Retirer %s du donjon ?": "Remove %s from the dungeon?",
    "  1. la carte est copiée dans ": "  1. the map is copied to ",
    "  1. copiez la carte sous %s.lua dans le répertoire du jeu":
        "  1. copy the map as %s.lua into the game directory",
    "%s-1.lua … %s-%d.lua.": "%s-1.lua … %s-%d.lua.",

    # nhme_level.py
    "Compilation de Lua…": "Compiling Lua…",
    "Carte redimensionnée en %dx%d.": "Map resized to %dx%d.",
    "Style de level_init": "level_init style",
    "Autres options de level_init (ex: lit=0) : ":
        "Other level_init options (e.g. lit=0): ",
    "Placement de la carte": "Map placement",
    "Vérification": "Check",
    "Lua compilé : %s": "Lua compiled: %s",
    "Carte importée de %s (%dx%d) ; s l'enregistre en %s.":
        "Map imported from %s (%dx%d); s saves it as %s.",
    "Salle à thème « %s » : seule la carte est éditée ; son contenu "
    "(filler_region…) est conservé.":
        "Themed room '%s': only the map is edited; its contents "
        "(filler_region…) are kept.",
    "Ouvert : %s (%dx%d, %d entités%s).": "Opened: %s (%dx%d, %d entities%s).",
    "Carte exportée : %s": "Map exported: %s",
    "Sauvegarde de secours récupérée ; s pour l'enregistrer dans %s.":
        "Backup recovered; s to save it to %s.",
    "Enregistré : salle « %s » dans %s": "Saved: room '%s' in %s",
    " (sans les entités)": " (without the entities)",
    "Modifications non enregistrées. Enregistrer ? (o/n, Échap annule) ":
        "Unsaved changes. Save? (y/n, Esc cancels) ",
    "Nouvelle carte « largeur hauteur » : ": "New map 'width height': ",
    "Remplir avec": "Fill with",
    "Nouvelle carte %dx%d.": "New %dx%d map.",
    " (fixé par le script)": " (set by the script)",
    "Nouvelle taille « largeur hauteur » (max %dx%d) : ":
        "New size 'width height' (max %dx%d): ",
    "Taille invalide.": "Invalid size.",
    "Terrain de remplissage (fg)": "Fill terrain (fg)",
    "Position « x y » : ": "Position 'x y': ",
    "Alignement horizontal": "Horizontal alignment",
    "Alignement vertical": "Vertical alignment",
    "- Vérification Lua indisponible : installez lua5.4 ou indiquez "
    "l'interpréteur dans NHMAPEDIT_LUA.":
        "- Lua check unavailable: install lua5.4 or set the interpreter "
        "in NHMAPEDIT_LUA.",
    "Pas d'interpréteur Lua : compiler celui des sources de NetHack "
    "(quelques secondes) ?":
        "No Lua interpreter: build the one from the NetHack sources "
        "(a few seconds)?",
    "Enregistrer sous : ": "Save as: ",
    "un fichier": "a file",
    "position fixe x=%d y=%d": "fixed position x=%d y=%d",
    " -> position aléatoire": " -> random position",
    "Donjon : placer le niveau dans dungeon.lua…":
        "Dungeon: put the level in dungeon.lua…",
    "Propriétés du niveau": "Level properties",
    "Options ignorées (syntaxe invalide).": "Options ignored (invalid syntax).",
    "Drapeaux (Entrée: cocher/décocher, Échap: terminer)":
        "Flags (Enter: check/uncheck, Esc: done)",
    "alignement (halign/valign)": "alignment (halign/valign)",
    "position fixe (x, y)": "fixed position (x, y)",
    "Compilation de Lua": "Building Lua",
    "Erreur à l'ouverture : %s": "Error opening: %s",
    "Erreur à l'import : %s": "Import error: %s",
    "+ nouvelle salle à thème": "+ new themed room",
    "Salles à thème de %s (dessinées par des.map)":
        "Themed rooms of %s (drawn with des.map)",
    "Taille « largeur hauteur » : ": "Size 'width height': ",
    ", carte avec contenu : placement non modifiable":
        ", map with contents: placement not editable",
    "Erreur d'export : %s": "Export error: %s",
    "Sauvegarde de secours du %s trouvée (session interrompue). La "
    "récupérer ?":
        "Backup from %s found (interrupted session). Recover it?",
    "Sauvegarde de secours illisible : %s": "Unreadable backup: %s",
    "Erreur d'enregistrement : %s": "Save error: %s",
    "roche (espace)": "stone (space)",
    "sol de salle (.)": "room floor (.)",
    "salle entourée de murs": "room surrounded by walls",
    " -> coin en (%d,%d) du niveau": " -> corner at (%d,%d) of the level",
    "Taille de la carte : %dx%d": "Map size: %dx%d",
    "level_init : %s": "level_init: %s",
    "Drapeaux : %s": "Flags: %s",
    "Placement : %s": "Placement: %s",
    "Carte éclairée (lit) : %s": "Lit map: %s",
    "- Lua : le script s'exécute sans erreur.":
        "- Lua: the script runs without errors.",
    "Échec :\n%s": "Failed:\n%s",
    "La salle « %s » existe déjà.": "Room '%s' already exists.",
    "Salle « %s » introuvable dans %s.": "Room '%s' not found in %s.",
    "(aucun)": "(none)",
    "Nom de la nouvelle salle : ": "Name of the new room: ",

    # nhme_tools.py
    "Collé.": "Pasted.",
    "Rien à annuler.": "Nothing to undo.",
    "Rien à rétablir.": "Nothing to redo.",
    "%d cases remplies.": "%d cells filled.",
    "Remplacer quel terrain ?": "Replace which terrain?",
    "Proportion des cases à remplacer en %% (1-100) : ":
        "Share of the cells to replace in %% (1-100): ",
    "Où remplacer ?": "Replace where?",
    "%d case(s) « %s » remplacée(s) par « %s ».":
        "%d '%s' cell(s) replaced with '%s'.",
    "Carte maintenant en %dx%d%s.": "Map now %dx%d%s.",
    "Zone %dx%d %s (%d entités). Outil Coller actif.":
        "%dx%d area %s (%d entities). Paste tool active.",
    "Presse-papiers vide (outil 7 ou D pour en remplir un).":
        "Clipboard empty (tool 7 or D to fill it).",
    "Presse-papiers %s (%dx%d). Outil Coller actif.":
        "Clipboard %s (%dx%d). Paste tool active.",
    "Presse-papiers vide (outil 7 pour copier).":
        "Clipboard empty (tool 7 to copy).",
    "Pipette : pinceau %s.": "Eyedropper: brush %s.",
    "Modèles (tapez pour filtrer)": "Templates (type to filter)",
    "Modèle %s (%dx%d, %d entités) : outil Coller actif, X/Y/O pour le "
    "retourner.":
        "Template %s (%dx%d, %d entities): Paste tool active, X/Y/O to "
        "flip it.",
    "Presse-papiers vide : copiez d'abord une zone (outil 7).":
        "Clipboard empty: copy an area first (tool 7).",
    "Modèle enregistré : %s": "Template saved: %s",
    "Remplacer « %s » par :": "Replace '%s' with:",
    "Lignes et colonnes (curseur en %d,%d)": "Rows and columns (cursor at %d,%d)",
    "Impossible : la carte n'a plus qu'une ligne ou colonne.":
        "Impossible: the map has only one row or column left.",
    "+ enregistrer le presse-papiers comme modèle":
        "+ save the clipboard as a template",
    "sur toute la carte": "on the whole map",
    "dans une zone (à tracer avec l'ancre)": "in an area (drawn with the anchor)",
    "insérer une ligne au-dessus": "insert a row above",
    "insérer une ligne en dessous": "insert a row below",
    "supprimer la ligne": "delete the row",
    "insérer une colonne à gauche": "insert a column on the left",
    "insérer une colonne à droite": "insert a column on the right",
    "supprimer la colonne": "delete the column",
    "Taille maximale atteinte (%dx%d).": "Maximum size reached (%dx%d).",
    "coupée": "cut",
    "copiée": "copied",
    "Modèle illisible : %s": "Unreadable template: %s",
    "Nom du modèle : ": "Template name: ",
    "Ancre posée ; déplacez-vous puis Espace (Échap annule).":
        "Anchor set; move then press Space (Esc cancels).",
    " (%d entité(s) supprimée(s))": " (%d entity(ies) deleted)",
    "retourné gauche/droite": "flipped left/right",
    "retourné haut/bas": "flipped top/bottom",
    "tourné d'un quart de tour": "rotated a quarter turn",
    "Semis : %d cases sur %d (%d %%).": "Scatter: %d cells out of %d (%d %%).",
    "%s tracé.": "%s drawn.",

    # historique des commandes
    "Modification": "Change",
    "Trait au crayon : %s": "Pen stroke: %s",
    "Remplissage : %s": "Flood fill: %s",
    "Remplacer « %s » par « %s »": "Replace '%s' with '%s'",
    "Couper une zone %dx%d": "Cut a %dx%d area",
    "Coller %dx%d": "Paste %dx%d",
    "Annulé : %s.": "Undone: %s.",
    "Rétabli : %s.": "Redone: %s.",
    "Historique vide.": "History is empty.",
    "   0. (ouverture de la carte)": "   0. (map opened)",
    "(annulé)": "(undone)",
    "Historique : %d commande(s), %d annulée(s) (● état actuel)":
        "History: %d command(s), %d undone (● current state)",
    "Entrée: revenir à cet état  Échap: fermer":
        "Enter: go back to this state  Esc: close",
    "%d commande(s) annulée(s).": "%d command(s) undone.",
    "%d commande(s) rétablie(s).": "%d command(s) redone.",
    "Ajout : %s": "Add: %s",
    "Suppression : %s": "Delete: %s",
    "Modification : %s": "Edit: %s",
    # entités supplémentaires
    "! Pont-levis en (%d,%d) sur '%s' : il doit être posé sur l'eau ou la lave devant le mur, sinon NetHack ne le crée pas.":
        "! Drawbridge at (%d,%d) on '%s': it must stand on the water or lava in front of the wall, otherwise NetHack does not create it.",
    'or': 'gold',
    'tombe': 'grave',
    'pont-levis': 'drawbridge',
    'élément de décor': 'feature',
    'terrain (une case)': 'terrain (one cell)',
    'Montant (vide : aléatoire) : ': 'Amount (empty: random): ',
    "Côté du mur où le pont s'abaisse":
        'Side of the wall where the bridge lowers',
    'État du pont-levis': 'Drawbridge state',
    'Élément de décor': 'Feature',
    'Épitaphe (vide : aléatoire) : ': 'Epitaph (empty: random): ',
    'Terrain de la case': 'Terrain of the cell',
    # régions
    'région': 'region',
    'zone non creusable': 'non-diggable zone',
    'zone sans passe-muraille': 'non-passwall zone',
    'zone de téléportation': 'teleport region',
    "zone d'arrivée": 'arrival region',
    '(tout le niveau)': '(whole level)',
    '[code Lua, non modifiable]': '[Lua code, read-only]',
    "Zone d'une région": 'Region area',
    'type de salle': 'room type',
    'éclairée': 'lit',
    'remplie (1 : peuplée selon le type)':
        'filled (1: stocked according to type)',
    'forme irrégulière': 'irregular shape',
    'reliée aux couloirs': 'joined to corridors',
    "salle d'arrivée": 'arrival room',
    'arrivées concernées (both, down, up)':
        'arrivals concerned (both, down, up)',
    'coordonnées du niveau entier': 'whole-level coordinates',
    'type': 'type',
    'nom (branche, portail)': 'name (branch, portal)',
    'marge': 'padding',
    ' Zone de la région : Espace/Entrée sur le coin opposé  Échap: annuler':
        ' Region area: Space/Enter on the opposite corner  Esc: cancel',
    'Zone : allez au coin opposé puis Espace (Échap annule).':
        'Area: go to the opposite corner then Space (Esc cancels).',
    'Région écrite avec du code Lua : modifiez-la dans le fichier.':
        'Region written with Lua code: edit it in the file.',
    'Modifier : %s': 'Edit: %s',
    'Options : %s': 'Options: %s',
    'Ajouté : %s': 'Added: %s',
    'options': 'options',
    'redessiner la zone (à partir du curseur)':
        'redraw the area (from the cursor)',
    'Éclairage de la zone': 'Area lighting',
    'Entités (%d) et régions (%d)': 'Entities (%d) and regions (%d)',
    'Étendue': 'Extent',
    'éclairée (lit)': 'lit',
    'sombre (unlit)': 'dark (unlit)',
    "Forme de l'appel": 'Call form',
    'une zone (à tracer)': 'an area (to draw)',
    'tout le niveau': 'the whole level',
    'salle ou zone typée : { region = {...}, type = ... }':
        'room or typed area: { region = {...}, type = ... }',
    'éclairage seul : selection.area(...), "lit"':
        'lighting only: selection.area(...), "lit"',
}

HELP = """\
nhmapedit — NetHack map editor (the .lua files of dat/)

MOVING
  Arrows / h j k l       move the cursor
  Shift+arrows, PgUp/PgDn, Home/End   move fast
  g                      go to a position (x y)
  c                      show / hide the coordinate rulers
  f                      preview NetHack's random flip:
                         none, horizontal, vertical, both
  Mouse                  click = move + apply the tool, drag = paint,
                         right click = eyedropper

TERRAIN (the typed character becomes the brush, and paints with the Pen)
  .  floor      #  corridor     -  horiz. wall  |  vert. wall  +  door
  S  secret door     H  secret corridor   {  fountain   \\  throne   K  sink
  }  moat       P  pool         W  water        L  lava        Z  lava wall
  I  ice        T  tree         F  iron bars    A  air         C  cloud
  B  boundary   x  transparent  e  stone (space)
  y  eyedropper: the terrain under the cursor becomes the brush

TOOLS (Space or Enter to apply)
  1 Pen   2 Line   3 Rectangle   4 Filled rectangle   5 Room (walls+floor)
  6 Flood fill   7 Copy an area   8 Paste
  D Cut an area (to move it: the area is emptied, entities included,
    then the Paste tool puts it down wherever you want)
  9 Ellipse   0 Filled ellipse (a circle is an ellipse in a square)
  G Random scatter: paints a random share of the cells of an area,
    with a density in % asked when choosing the tool
  R Replace one terrain with another, on the whole map or in an area,
    with a share in % (like des.replace_terrain)
  M  symmetry: none, left/right, top/bottom, both; everything that
     paints (pen, shapes, fill, scatter, replace) is mirrored around
     the center of the map (axes marked "*" on the frame)
  E  insert or delete a row or a column at the cursor (the map and the
     entities are shifted)
  b  template library (temple, shop, fountain…): the chosen template
     goes to the clipboard; the last line saves the clipboard as a
     template (~/.config/nhmapedit/modeles)
  Clipboard: X mirror left/right   Y mirror top/bottom
             O rotate a quarter turn (clockwise)
  Two-point tools: 1st press = anchor, 2nd press = draw. Esc cancels.
  d  pen down (paints while moving)    a  auto advance
  A stroke (pen down or mouse drag) is undone in one go.

ENTITIES (coordinates relative to the map)
  m  place an entity (stairs, ladder, altar, monster, object, trap,
     door, engraving, gold, grave, drawbridge, feature: fountain,
     sink…, single-cell terrain: des.terrain) or a region
     (des.region: typed room or lit area, des.non_diggable,
     des.non_passwall, des.teleport_region, des.levregion): the region
     starts at the cursor, Space on the opposite corner
  r  repeat the last entity at the cursor
     Monsters and objects: a form shows their common options
     (Enter changes: default -> yes -> no -> default; Esc ends);
     "inventory" (monster) and "contents" (box, statue…) open the
     list of their objects (Enter/e: edit, d: delete)
  Del / Backspace / z   delete the entities under the cursor
  i  entity and region list (Enter: go, e: edit, d: delete;
     e on a region: options or area to redraw)
  Regions as background colours: blue for typed rooms (temple…), green
  for teleport and arrival regions; hidden by default: yellow for areas
  that are only lit or dark, red for non-diggable or non-passwall zones
  Tab  show / hide the entities
  Random monsters and objects: on a magenta background, with the symbol
  of their class (d, !…) or "?" when everything is random
  An underlined symbol means several entities on the cell (only the
  most important is drawn; the status bar lists them all)
  J  render "as in the game" (walls as lines, floor as dots, secret
     doors and corridors hidden); editing still works

LEVEL AND FILES
  p  properties (size, flags, level_init, alignment, lighting);
     "Dungeon" adds the level to dat/dungeon.lua (depth, chance…),
     or edits and removes the special levels of the dungeon
  v  check the map, including connectivity: down stairs reachable
     from the up stairs (doors without diagonals, secret passages,
     water and lava reported) and closed areas; NetHack rules (door in a
     corner, stairs in water, altar outside a temple, map overflowing…);
     with a Lua interpreter, runs the whole script with a fake des
     library (names, parameters, syntax errors)
  t  test: copies the map to the game directory, to load with
     #wizloaddes in wizard mode (nethack -D); with tmux, the editor
     starts the game (pane, window or tmux session) and loads the map
     itself, then reloads it each time t is pressed again
  u / Ctrl-Z  undo      U / Ctrl-R / Ctrl-Y  redo
  V  command history: every change is named there ("Room: floor",
     "Add: stairs up"…); Enter brings the map back to the chosen state,
     forward or backward (300 commands at most)
  n  new       o  open      s  save      w  save as
     o on a .txt: imports a plain text map;
     w to a .txt: exports the map alone; to a .svg or a .png: exports
     it as an image, as displayed (J, Tab)
  q  quit      ?  this help

The bottom bar shows the useful keys for the situation: anchor set,
Paste tool, pen down, entities under the cursor, game view…

Themed rooms: opening themerms.lua (o) offers its rooms drawn with
des.map, or a new room; s only rewrites the map there (or adds the
room), t explains how to see it in the game with THEMERM.

Backup: a modified map is copied at most every minute to
file.lua.nhme-autosave, offered when reopening after a crash, and
deleted on save.

Configuration: ~/.config/nhmapedit/config (or $NHMAPEDIT_CONFIG), in
INI format: game directory, default size, terrain colors, key
remapping, backup delay, language (langue = en).
Commented example: docs/config.exemple.

For an existing file, only the first des.map and the fixed-position
elements following it (with their inventory or contents, if it only
holds plain des.object calls) are edited; the rest of the Lua script
is kept as is on save.
"""
