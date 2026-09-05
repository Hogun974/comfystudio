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
Le refus s'écrit sous l'état du moteur, en rouge, jusqu'au clic suivant — il
n'est pas avalé.

**Les deux boutons n'apparaissent que si `GET /api/comfy` répond
`pilotable`** : l'appel vient de la machine hôte *et* un script de lancement a
été trouvé. C'est la même garde que le serveur pose sur les deux `POST`, relue
par la page ; un bouton visible à un visiteur du réseau, qui rendrait 403 au
clic, serait pire que pas de bouton. Le serveur rend la main dès que ComfyUI est
lancé, avant qu'il ne réponde : le panneau s'interroge toutes les deux secondes
pendant la minute et demie qui suit un clic, toutes les dix secondes sinon.

> **Du premier commit au 6 septembre 2026, cette page décrivait un panneau que
> la page n'avait jamais eu.** La pastille, « ComfyUI… », les deux boutons,
> `GET /api/comfy` et les deux routes `POST` existaient tous — et aucune ligne
> du script de `web/index.html` ne les reliait. Le panneau disait « ComfyUI… »
> pour toujours, les boutons dormaient sous `display:none`, et les routes,
> gardées et éprouvées par `banc_console.py`, n'avaient aucun appelant. C'est
> le relevé de ce banc (section 7, « une route que rien n'appelle ») qui l'a
> dit le 5 septembre. Depuis le 6, `banc_page.py` tient les deux moitiés :
> chaque champ lu est un champ rendu, les boutons ne dépendent que de
> `pilotable`, chaque bouton vise une route `POST` servie et chaque route a
> son bouton, un refus est écrit dans une zone qui existe, et le panneau se
> repeint après le clic. `banc_mutations.py` porte les douze mutations qui
> les éprouvent.
