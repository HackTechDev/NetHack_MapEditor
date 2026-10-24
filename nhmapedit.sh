#!/usr/bin/env bash
# Lance l'éditeur de cartes nhmapedit.
#
# Usage : ./nhmapedit.sh [fichier.lua] [--new LARGEURxHAUTEUR]
#         ./nhmapedit.sh --install   (lien dans ~/.local/bin/nhmapedit)
#
# Fonctionne aussi depuis un lien symbolique placé n'importe où.

set -euo pipefail

# dossier de l'éditeur, même si le script est appelé par un lien
DIR=$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")

if [[ ${1:-} == --install ]]; then
    BIN="$HOME/.local/bin"
    mkdir -p "$BIN"
    ln -sfn "$DIR/nhmapedit.sh" "$BIN/nhmapedit"
    echo "Lien créé : $BIN/nhmapedit -> $DIR/nhmapedit.sh"
    case ":$PATH:" in
        *":$BIN:"*) echo "Lancez l'éditeur avec : nhmapedit" ;;
        *) echo "Ajoutez $BIN à votre PATH pour lancer : nhmapedit" ;;
    esac
    exit 0
fi

PYTHON=${PYTHON:-python3}
if ! command -v "$PYTHON" >/dev/null; then
    echo "nhmapedit : $PYTHON introuvable (installez Python 3)." >&2
    exit 1
fi
if ! "$PYTHON" -c "import curses" 2>/dev/null; then
    echo "nhmapedit : le module curses de Python est absent." >&2
    exit 1
fi

exec "$PYTHON" "$DIR/nhmapedit.py" "$@"
