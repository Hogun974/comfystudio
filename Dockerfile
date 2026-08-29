# ComfyStudio — interface en langage naturel pour ComfyUI
#
# Le studio ne fait tourner AUCUN modele : il pilote un ComfyUI et un Ollama qui
# vivent ailleurs. L'image est donc minuscule et sans CUDA.
FROM python:3.12-slim

# aiohttp sert l'interface et parle a ComfyUI. huggingface_hub n'est qu'un
# confort : le studio sait aussi telecharger en HTTPS direct, ce qui lui permet
# de fonctionner la ou pip n'est pas installable.
# av (PyAV) lit la cadence d'une video. Il manquait : serveur.py l'importe
# dans un try, si bien que la fluidite video repartait sur 24 im/s par
# defaut, sans que rien ne le signale. Une degradation muette est pire
# qu'une erreur.
RUN pip install --no-cache-dir "aiohttp>=3.9" "huggingface_hub>=0.24" "av>=12" \
 && useradd --create-home --uid 10001 studio

WORKDIR /app

# Tous les modules Python, et non une liste nommee. Une liste se perime : celle
# d'avant ne copiait que serveur.py, et l'image livree plantait au premier
# import — catalogue.py, fournisseurs.py et comptes.py manquaient, sans que rien
# ne l'annonce avant le demarrage.
COPY *.py ./
COPY web/ ./web/
COPY noeuds.exemple.json ./
# Le modele d'aiguillage. Sans lui le studio retombe sur le modele de
# langage pour CHAQUE demande : le meme resultat, mais des milliers de fois
# plus lentement, et l'image ne le disait nulle part.
COPY aiguilleur.json ./

# Le studio SERT ces fichiers aux machines qui viennent s'enroler (/api/noeud/…).
# Sans eux dans l'image, on ne peut plus ajouter de machine depuis un studio en
# conteneur.
COPY noeud.sh noeud.bat modeles.sh maj_noeud.sh maj_noeud.bat ./
COPY zimaos-comfyui.yml zimaos-registry.yml ./

# Point de montage de ComfyUI s'il tourne sur la MEME machine. Sans ce
# reglage, le chemin par defaut serait « ComfyUI_windows_portable », qui n'a
# aucun sens ici et s'affichait tel quel dans le journal du conteneur.
ENV COMFY_DIR=/comfy
# Conversations, comptes, cles d'API, registre des televersements : a monter,
# sinon tout est perdu au redemarrage du conteneur.
ENV STUDIO_DONNEES=/donnees \
    STUDIO_HOTE=0.0.0.0 \
    STUDIO_PORT=8199 \
    COMFY_URL=http://comfyui:8188 \
    OLLAMA_URL=http://ollama:11434 \
    PYTHONUNBUFFERED=1
VOLUME ["/donnees"]
EXPOSE 8199

# Le volume appartient a l'utilisateur non privilegie : sans cela, le studio ne
# peut pas ecrire ses conversations et s'arrete sur une erreur de permission.
RUN mkdir -p /donnees && chown -R studio:studio /app /donnees
USER studio

# Un conteneur declare « healthy » alors que le serveur est mort ne sert a rien :
# on interroge une vraie route.
# /api/compte et non /api/modeles : depuis que la connexion est obligatoire,
# /api/modeles repond 401 sans session, et le conteneur se declarait malade
# alors qu il fonctionnait parfaitement.
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8199/api/compte', timeout=4).status == 200 else 1)"

# Sans shell : le signal d'arret arrive directement au serveur.
CMD ["python", "-u", "serveur.py"]
