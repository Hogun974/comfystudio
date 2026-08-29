#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Point d'entree de l'installeur ComfyStudio.

Ce fichier est ecrit dans une syntaxe que MEME Python 2 sait lire, et il n'y a
rien d'autre dedans. C'est voulu : lance par erreur avec un vieux Python, tout
le programme echouait sur un SyntaxError incomprehensible a sa premiere
f-string, sans jamais dire ce qui manquait vraiment. Le controle de version doit
donc vivre dans un fichier qui se laisse lire par la version fautive.

Le programme lui-meme est dans installation.py.
"""
import os
import sys

MINIMUM = (3, 8)

if sys.version_info < MINIMUM:
    v = ".".join(str(x) for x in sys.version_info[:3])
    sys.stderr.write("\n")
    sys.stderr.write("  ComfyStudio a besoin de Python %d.%d ou plus recent.\n"
                     % MINIMUM)
    sys.stderr.write("  Celui qui vient de lancer ce fichier est le %s.\n\n" % v)
    sys.stderr.write("  Essaie plutot :\n")
    sys.stderr.write("      python3 installer.py\n")
    sys.stderr.write("  ou lance le script prevu pour ton systeme :\n")
    sys.stderr.write("      ./installer.sh          (macOS, Linux)\n")
    sys.stderr.write("      installer.bat           (Windows)\n\n")
    sys.stderr.write("  Si python3 n'existe pas :\n")
    sys.stderr.write("      macOS            brew install python\n")
    sys.stderr.write("                       ou xcode-select --install\n")
    sys.stderr.write("      Debian, Ubuntu   sudo apt install python3 python3-venv\n")
    sys.stderr.write("      Fedora           sudo dnf install python3\n\n")
    sys.exit(1)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from installation import main          # noqa: E402

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.stderr.write("\ninterrompu.\n")
        sys.exit(1)
