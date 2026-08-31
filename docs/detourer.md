# Détourer

« détoure-la », « enlève le fond », « isole le personnage » : le sujet est
isolé et le fond devient transparent, en PNG. **Deux secondes.** Comme
l'agrandissement, la demande est reconnue à l'écrit — il n'y a rien à
interpréter, et laisser un modèle décider risquerait qu'il redessine l'image.

Tiré du workflow officiel *BiRefNet: Remove Background* (444 Mo).

Un piège vérifié plutôt que supposé : le masque rendu par `RemoveBackground`
désigne le **sujet**, pas le fond. Sans `InvertMask`, on obtient exactement
l'inverse — 11 % de transparence au lieu de 87 %, c'est-à-dire le personnage
effacé et le décor conservé. L'inversion que place le workflow officiel n'est
pas décorative.
