# Piloter ComfyUI depuis l'interface

Le bas de la barre latérale affiche l'état du moteur : allumé ou éteint, carte
détectée, VRAM libre. Depuis la machine hôte, deux boutons le démarrent et
l'arrêtent. Le script de lancement est trouvé tout seul à côté de ComfyUI ;
`COMFY_LANCEUR` permet d'en imposer un autre.

**Le studio ne lance pas le `.bat` : il rejoue la commande qu'il contient.**
Lancer le fichier ouvrait une console à chaque démarrage et, à cause de
`--windows-standalone-build`, rouvrait le navigateur sur ComfyUI. En extrayant
la ligne `python.exe …` et en y ajoutant `--disable-auto-launch`, on évite les
deux — et ton `.bat` reste intact pour un lancement manuel, avec ses réglages.
Si la commande est illisible, on retombe sur le fichier, console comprise.

L'arrêt est refusé tant qu'une génération est en cours **ou en attente** : le
créneau entre deux tâches suffirait sinon à couper le moteur sous les suivantes.
