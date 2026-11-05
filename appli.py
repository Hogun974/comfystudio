# -*- coding: utf-8 -*-
"""Le studio installable : le manifeste et ses icones, fabriques ici.

CE QUE LES NAVIGATEURS EXIGENT, releve le 5 novembre 2026 dans leur propre
documentation — web.dev/articles/install-criteria,
developer.chrome.com/blog/update-install-criteria,
developer.mozilla.org (Guides/Making_PWAs_installable, revu le 6 octobre 2026),
webkit.org/blog/16993 (Safari 26) et web.dev/articles/maskable-icon :

  - Chrome et Edge (ordinateur et Android) : un manifeste lie depuis la page,
    avec « name » ou « short_name », « start_url », un « display » parmi
    standalone / fullscreen / minimal-ui, et DEUX icones PNG, 192 et 512 px.
    La page doit etre servie en HTTPS (ou depuis localhost).
  - PLUS DE SERVICE WORKER EXIGE pour installer depuis le menu, depuis
    Chrome 108 sur Android et 112 sur ordinateur. Chrome ignore d'ailleurs un
    gestionnaire « fetch » vide : un service worker qui laisse tout passer ne
    rapporterait rien, et un qui met en cache rapporterait un risque — voir
    plus bas.
  - Safari iOS : depuis Safari 26, tout site pose sur l'ecran d'accueil s'ouvre
    en appli, manifeste ou non ; les icones du manifeste servent (depuis 15.4)
    sauf si un « apple-touch-icon » est declare, qui passe devant.
  - Une icone « maskable » garde l'essentiel dans un cercle de 40 % de la
    largeur : Android la decoupe en rond, en goutte ou en carre arrondi. Une
    icone a part, et non « any maskable » : l'une a besoin de marge, l'autre
    non.

POURQUOI FABRIQUER LES ICONES ICI PLUTOT QUE LES POSER DANS web/. Un PNG
pose dans web/ est un fichier de plus que DEUX empaquetages doivent
emporter : le Dockerfile copie web/ en entier, mais paquet/comfystudio.spec
nomme ses fichiers un par un — et web/demarrage.html y manquait encore le
5 novembre 2026, c'est-a-dire que /demarrage rendait une erreur dans
l'executable. Un module Python, lui, suit tout seul : « COPY *.py » dans
l'image, l'analyse des imports dans PyInstaller. Le dessin tient en
quarante lignes de bibliotheque standard (zlib + struct, comme les PNG des
bancs) et se calcule une fois par processus.

AUCUN SERVICE WORKER, ET C'EST UNE DECISION. Le studio est prive : chaque page
montre les conversations d'UN compte, et un cache de service worker appartient
a l'origine, pas au compte — deux personnes qui se succedent sur le meme
telephone partageraient ce qu'il garde. Les criteres ne l'exigent plus, il ne
servirait donc qu'a cacher des choses, et c'est justement ce qu'on refuse.
banc_page.py exige qu'aucune page n'en enregistre : en poser un un jour sera
une decision ecrite, pas un ajout en passant.
"""
import functools
import struct
import zlib

NOM = "ComfyStudio"
# Les couleurs de la page (web/index.html, :root) : --nuit pour le fond du
# lancement, --plan pour la barre de titre, --braise pour le dessin. Reprises
# ici en dur : le manifeste n'a pas de feuille de style, et une icone non plus.
NUIT = "#15120f"
PLAN = "#1d1915"
BRAISE = "#e8a33d"

CHEMIN_MANIFESTE = "/manifest.webmanifest"
PREFIXE_ICONES = "/icones/"

# nom servi -> (cote en pixels, plein cadre ?)
# « Plein cadre » : fond jusqu'aux bords, pour les deux usages qui decoupent
# eux-memes l'icone — l'icone « maskable » d'Android et l'apple-touch-icon,
# qu'iOS arrondit et dont il noircirait la transparence.
ICONES = {
    "appli-192.png": (192, False),
    "appli-512.png": (512, False),
    "appli-masque-192.png": (192, True),
    "appli-masque-512.png": (512, True),
    "appli-apple-180.png": (180, True),
}

# CE QUI S'OUVRE SANS COMPTE, en adresses EXACTES et non en prefixe. Chrome
# va chercher le manifeste SANS cookie (le manifeste est demande en
# « credentials: omit » tant que la balise ne dit pas le contraire) : ferme, il
# rendrait le 401 « connexion requise » et le studio ne serait jamais
# installable sous STUDIO_AUTH=obligatoire. Rien ici ne dit quoi que ce soit
# d'un compte ni de l'installation : un nom, trois couleurs, un dessin.
CHEMINS_LIBRES = frozenset([CHEMIN_MANIFESTE]
                           + [PREFIXE_ICONES + n for n in ICONES])


def _rgb(hexa):
    return tuple(int(hexa[i:i + 2], 16) for i in (1, 3, 5))


def png(cote, lignes):
    """Un PNG RGBA 8 bits a partir de lignes deja assemblees (bytes)."""
    def morceau(genre, donnees):
        return (struct.pack(">I", len(donnees)) + genre + donnees
                + struct.pack(">I", zlib.crc32(genre + donnees) & 0xFFFFFFFF))
    brut = b"".join(b"\x00" + ligne for ligne in lignes)   # filtre 0 partout
    return (b"\x89PNG\r\n\x1a\n"
            + morceau(b"IHDR", struct.pack(">IIBBBBB", cote, cote, 8, 6, 0, 0, 0))
            + morceau(b"IDAT", zlib.compress(brut, 9))
            + morceau(b"IEND", b""))


def _couvre(d):
    """Part d'un pixel couverte par une forme dont il est a « d » px du bord
    (negatif dedans). L'anticrenelage le moins cher qui soit, et il suffit a
    des cercles."""
    return 0.0 if d >= 0.5 else 1.0 if d <= -0.5 else 0.5 - d


@functools.lru_cache(maxsize=None)
def dessiner(cote, plein):
    """L'icone du studio : un objectif ambre sur le fond sombre de la page.

    Un anneau et un point, centres, de rayon 30 % du cote au plus : dans le
    cercle sur de 40 % d'une icone « maskable », et assez gros pour se lire
    a 48 px sur un ecran d'accueil. Non plein, le fond est un carre aux angles
    arrondis, transparent au-dela.

    Un QUART seulement est calcule, puis replie : le dessin est symetrique et
    le cote toujours pair, et cela divise par quatre les 262 144 pixels de la
    grande icone.
    """
    fond, ambre = _rgb(PLAN), _rgb(BRAISE)
    c = cote / 2.0
    r_ext, r_int, r_point = 0.30 * cote, 0.19 * cote, 0.075 * cote
    arrondi = 0.22 * cote
    moitie = cote // 2
    quart = []
    for y in range(moitie):
        ligne = bytearray()
        dy = c - (y + 0.5)
        for x in range(moitie):
            dx = c - (x + 0.5)
            r = (dx * dx + dy * dy) ** 0.5
            if plein:
                a_fond = 1.0
            else:
                # Distance signee au carre arrondi qui remplit le cadre.
                qx, qy = dx - (c - arrondi), dy - (c - arrondi)
                hors = (max(qx, 0.0) ** 2 + max(qy, 0.0) ** 2) ** 0.5
                a_fond = _couvre(hors + min(max(qx, qy), 0.0) - arrondi)
            anneau = _couvre(r - r_ext) - _couvre(r - r_int)
            a = max(anneau, _couvre(r - r_point))
            ligne += bytes((round(fond[0] + (ambre[0] - fond[0]) * a),
                            round(fond[1] + (ambre[1] - fond[1]) * a),
                            round(fond[2] + (ambre[2] - fond[2]) * a),
                            round(255 * a_fond)))
        # La moitie droite est la gauche lue a l'envers, pixel par pixel.
        pixels = [bytes(ligne[i:i + 4]) for i in range(0, len(ligne), 4)]
        quart.append(bytes(ligne) + b"".join(reversed(pixels)))
    return png(cote, quart + quart[::-1])


def icone(nom):
    """Les octets de l'icone servie sous ce nom, ou None."""
    if nom not in ICONES:
        return None
    return dessiner(*ICONES[nom])


def manifeste():
    """Le manifeste, tel que /manifest.webmanifest le sert.

    « id », « start_url » et « scope » valent « / » : le studio n'a qu'une
    adresse, et un id explicite evite qu'un changement de start_url fasse
    croire au navigateur a une AUTRE appli, installee en double.
    Le nom n'est pas traduit : c'est un nom propre, le meme que <title>.
    """
    return {
        "id": "/",
        "name": NOM,
        "short_name": NOM,
        "start_url": "/",
        "scope": "/",
        "display": "standalone",
        "background_color": NUIT,
        "theme_color": PLAN,
        "icons": [
            {"src": PREFIXE_ICONES + nom, "sizes": f"{cote}x{cote}",
             "type": "image/png", "purpose": "maskable" if plein else "any"}
            for nom, (cote, plein) in ICONES.items()
            # L'apple-touch-icon n'est pas une icone de manifeste : iOS la lit
            # par sa balise, et Chrome n'a que faire d'un 180.
            if not nom.startswith("appli-apple")],
    }
