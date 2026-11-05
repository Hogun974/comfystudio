# -*- coding: utf-8 -*-
"""Les rappels : le studio previent un programme qu'un rendu est fini.

POURQUOI CE MODULE. Un programme qui demande un rendu (un workflow n8n, un
agent IA, un script) ne veut pas interroger le studio toutes les cinq secondes
pendant dix minutes. Il donne une URL — typiquement celle d'un noeud
« Webhook » ou « Wait » de n8n — et le studio y POSTe un evenement JSON quand
le rendu se termine. Cette URL est publique pour qui la connait : le recepteur
doit donc pouvoir PROUVER que l'evenement vient du studio, et non de
quelqu'un qui a lu l'URL dans un journal. D'ou la signature.

POURQUOI A LA MAIN. La signature est vingt lignes de hmac et de hashlib, et le
format est celui de Stripe (« t=<horodatage>,v1=<hex> »), que GitHub, Slack et
la plupart des recettes n8n imitent : un integrateur reconnait le format, et
trouve une recette qui le verifie. Aucune bibliotheque n'apporterait plus que
ces vingt lignes, et le studio doit demarrer sur un NAS sans pip.

COMMENT UN RECEPTEUR VERIFIE (Python ; signature_valide() n'importe que la
bibliotheque standard, elle se recopie telle quelle) :

    corps = await request.read()       # les OCTETS recus, jamais le JSON
                                       # relu puis reecrit : un espace de
                                       # plus et la signature tombe a cote
    entete = request.headers.get("X-ComfyStudio-Signature")
    if not rappels.signature_valide(SECRET, entete, corps):
        return web.Response(status=401)
    # puis dedupliquer sur X-ComfyStudio-Livraison : un essai repete porte
    # le meme identifiant

Un noeud Code de n8n fait la meme chose avec
crypto.createHmac('sha256', secret).update(`${t}.${corpsBrut}`).digest('hex'),
a condition de recevoir le corps BRUT (option « Raw Body » du noeud Webhook)
et d'avoir autorise le module (NODE_FUNCTION_ALLOW_BUILTIN=crypto) : un
JSON.stringify du corps deja decode ne redonne pas les memes octets.

CE QU'IL NE FAIT PAS.
  - Il ne garde rien sur disque lui-meme : c'est serveur.py qui inscrit
    chaque livraison en cours (_rappels.json) et la reprend au demarrage.
    Le programme peut toujours interroger le rendu par son identifiant ; le
    rappel est une commodite, pas la seule voie.
  - livrer() ne connait pas la liste des hotes : c'est a l'appelant d'avoir
    passe l'URL par url_autorisee() AVANT, a l'enregistrement de la demande.
  - Il ne resout pas les noms : un hote de la liste qui pointe ailleurs est le
    choix de celui qui l'a declare. La comparaison est textuelle, donc une
    autre ecriture d'une adresse (« 127.1 », « 2130706433 ») ne correspond a
    rien et echoue fermee.
  - Il ne chiffre rien : sur http, le corps se lit en route. La signature
    prouve l'origine et l'integrite, pas la confidentialite.
"""
import asyncio
import hashlib
import hmac
import json
import time
import urllib.parse

# Les quatre fins d'un rendu. Une liste fermee : un nom mal tape
# (« rendu.termine ») partirait sans erreur et n'aurait aucune branche pour le
# recevoir dans le workflow — livrer() le refuse avant tout essai.
# « rappel.essai » : l'evenement que le proprietaire d'une cle envoie lui-meme
# pour verifier son branchement (POST /api/v1/rappels/essai) — un recepteur doit
# pouvoir le reconnaitre et ne rien en faire.
EVENEMENTS = ("rendu.fini", "rendu.erreur", "rendu.question", "rendu.annule",
              "rappel.essai")

ENTETE_SIGNATURE = "X-ComfyStudio-Signature"
ENTETE_EVENEMENT = "X-ComfyStudio-Evenement"
# LE MEME IDENTIFIANT D'UN ESSAI A L'AUTRE. Un essai dont la reponse s'est
# perdue en route a peut-etre ete traite : le recepteur ne peut le savoir
# qu'en reconnaissant l'identifiant, et c'est sur lui qu'il deduplique.
ENTETE_LIVRAISON = "X-ComfyStudio-Livraison"

# CINQ MINUTES, la valeur de Stripe. Assez pour une horloge de NAS qui derive
# de quelques dizaines de secondes faute de NTP, assez peu pour qu'un corps
# signe vole dans un journal ne se rejoue pas le lendemain.
TOLERANCE = 300

# L'attente AVANT chaque essai : quatre essais en deux minutes et demie. Le
# premier part tout de suite ; les suivants laissent a un n8n qui redemarre
# (une trentaine de secondes sur un petit serveur) le temps de revenir. Au-dela,
# le recepteur est en panne pour de bon et le programme interrogera le rendu.
# LA COURSE AU WAIT DE n8n (voir _PASSAGERS) tient aussi dedans : entre la
# reponse du studio au POST du rendu et l'execution posee « waiting » sur le
# disque de n8n, il n'y a que le noeud Wait et une ecriture — quelques
# secondes au plus en general (estimation, pas une mesure), que l'essai de
# 5 s couvre ; ceux de 30 et 120 s couvrent un n8n charge. Un essai de plus,
# plus tot, ne ferait gagner que quelques secondes de reveil.
DELAIS = (0, 5, 30, 120)

# Dix secondes : un noeud Webhook de n8n repond des reception (« Respond
# immediately » est son defaut). Un recepteur qui met plus longtemps fait un
# travail lourd avant de repondre, et il doit le faire apres.
DELAI_REPONSE = 10

# Ce qui merite un nouvel essai : le recepteur est la mais pas pret. 408
# (delai de requete), 425 (trop tot, RFC 8470), 429 (trop de requetes) le disent
# en toutes lettres ; un 5xx dit qu'il a casse, pas qu'il refuse. Tout autre
# 4xx est un refus raisonne — mauvaise signature, URL perimee — et insister ne
# le changera pas.
#
# 409, PARCE QUE C'EST LE « PAS ENCORE » DE n8n. L'URL de reprise d'un noeud
# Wait ($execution.resumeUrl) existe des le debut de l'execution, avant que
# celle-ci ait ATTEINT le Wait : un rendu qui finit dans cet intervalle trouve
# une execution encore « running », et n8n repond 409 « is running already »
# (packages/cli/src/webhooks/waiting-webhooks.ts, branche master lue le
# 5 novembre 2026 ; ConflictError vaut 409). Classe en refus, le rappel etait
# perdu au premier essai et le workflow dormait jusqu'a son delai. Le meme 409
# dit aussi « deja finie » — n8n ne les distingue que dans le texte du message,
# qu'on ne lit pas : c'est une phrase, pas un contrat (celle de « finished
# already » perd meme un guillemet sur master). Le prix de l'ambiguite
# est trois POST de trop en deux minutes et demie vers une execution finie, que
# n8n refuse sans rien executer ; celui de l'autre choix est un rappel perdu.
# Les vrais definitifs de n8n restent des refus : 404 (execution inconnue, ou
# Wait sans webhook pour cette methode) et 401 (jeton de reprise invalide).
_PASSAGERS = (408, 409, 425, 429)

# LES CARACTERES SUR LESQUELS DEUX LECTEURS D'URL DIVERGENT. urlsplit et le
# client HTTP (yarl, sous aiohttp) ne decoupent pas forcement pareil une URL qui
# contient une barre inverse ou un espace — les navigateurs lisent « \ » comme
# « / ». Une URL que l'un lit « hote autorise » et l'autre « ailleurs » est
# exactement la requete forgee qu'on cherche a empecher : on la refuse.
_AMBIGUS = frozenset("\\") | frozenset(chr(i) for i in range(0x21)) | {"\x7f"}


def corps_de(evenement):
    """Les octets exacts qui seront signes puis envoyes.

    UNE SEULE ECRITURE, DETERMINISTE. sort_keys et les separateurs compacts
    font qu'un meme evenement donne les memes octets quel que soit l'ordre dans
    lequel le dict a ete construit : un banc, un journal ou un recepteur qui
    recalcule tombent juste. ensure_ascii=False garde une lettre accentuee en
    UTF-8 au lieu de son echappement « \\u00e9 » : c'est ce qu'un humain lit
    dans l'historique d'execution de n8n.
    """
    return json.dumps(evenement, ensure_ascii=False, separators=(",", ":"),
                      sort_keys=True).encode("utf-8")


def _empreinte(secret, horodatage, corps):
    # L'HORODATAGE EST DANS CE QUI EST SIGNE, et c'est tout son interet : sans
    # lui, un corps signe vole se rejouerait indefiniment, et changer le « t= »
    # de l'en-tete suffirait a le rajeunir.
    return hmac.new(secret.encode("utf-8"),
                    f"{horodatage}.".encode("ascii") + corps,
                    hashlib.sha256).hexdigest()


def signature(secret, horodatage, corps):
    """L'en-tete X-ComfyStudio-Signature : « t=<horodatage>,v1=<hex> »."""
    return f"t={int(horodatage)},v1={_empreinte(secret, int(horodatage), corps)}"


def signature_valide(secret, entete, corps, maintenant=None,
                     tolerance=TOLERANCE):
    """Vrai si l'en-tete signe bien ce corps, avec ce secret, a l'heure dite.

    NE LEVE JAMAIS. Un recepteur appelle cette fonction sur ce que n'importe
    qui lui envoie : un en-tete absent, tronque ou hostile doit donner « non »,
    pas une pile d'appels qui deviendrait un 500 — et un 500 que le studio
    re-essaierait.

    L'ORDRE DES CHAMPS N'EST PAS UNE PROMESSE, et plusieurs « v1= » sont
    permis : pendant une rotation de secret, l'emetteur peut signer avec
    l'ancien et le nouveau, et le recepteur accepte si l'un des deux tombe
    juste — c'est ainsi que Stripe change de secret sans coupure.

    LA TOLERANCE VAUT DANS LES DEUX SENS. Un horodatage dans le futur n'est pas
    plus frais : c'est un corps signe en avance, ou une horloge folle, et
    l'accepter rouvrirait le rejeu pour toute la duree de l'avance.
    """
    try:
        if not isinstance(entete, str) or not entete:
            return False
        if isinstance(corps, str):
            corps = corps.encode("utf-8")
        horodatages, empreintes = [], []
        for morceau in entete.split(","):
            cle, egal, valeur = morceau.strip().partition("=")
            if not egal:
                continue
            if cle == "t":
                horodatages.append(valeur.strip())
            elif cle == "v1":
                empreintes.append(valeur.strip())
        # UN SEUL t=. Deux horodatages, c'est un en-tete fabrique pour qu'un
        # lecteur prenne le premier et un autre le dernier.
        if len(horodatages) != 1 or not empreintes:
            return False
        brut = horodatages[0]
        if not _chiffres(brut):
            return False
        t = int(brut)
        quand = time.time() if maintenant is None else maintenant
        if abs(quand - t) > tolerance:
            return False
        attendu = _empreinte(secret, t, corps).encode("ascii")
        # compare_digest pour chacun, et on ne s'arrete pas au premier qui
        # echoue : l'ordre des v1= ne doit rien changer. Les octets plutot que
        # les chaines : compare_digest leve sur une chaine non ASCII, et un
        # v1= hostile ne doit pas faire rater le v1= juste qui le suit.
        bon = False
        for v in empreintes:
            if hmac.compare_digest(attendu,
                                   v.lower().encode("utf-8", "replace")):
                bon = True
        return bon
    except Exception:
        return False


def _chiffres(texte):
    # isdigit() seul accepte les exposants (U+00B2), sur lesquels int() leve
    # ensuite : on exige des chiffres ASCII.
    return texte.isascii() and texte.isdigit()


def _entree(entree):
    """(hote, port ou None) d'une entree de la liste, ou None si illisible."""
    e = (entree or "").strip().lower().rstrip(".")
    if not e:
        return None
    if e.startswith("["):
        # IPv6 entre crochets, comme dans une URL : « [::1]:5678 ». Sans les
        # crochets, on ne saurait pas ou finit l'adresse et ou commence le port.
        fin = e.find("]")
        if fin < 0:
            return None
        hote, reste = e[1:fin], e[fin + 1:]
        if not reste:
            return hote, None
        if not reste.startswith(":") or not _chiffres(reste[1:]):
            return None
        return hote, int(reste[1:])
    if e.count(":") == 1:
        hote, _, port = e.partition(":")
        if not _chiffres(port):
            return None
        return hote.rstrip("."), int(port)
    # Plusieurs deux-points sans crochets : une IPv6 nue, donc sans port.
    return e, None


def url_autorisee(url, hotes):
    """None si le studio peut POSTer a cette URL ; sinon un code court.

    LA LISTE DES HOTES, C'EST LA DEFENSE CONTRE LA REQUETE FORGEE COTE SERVEUR
    (SSRF). Le studio vit sur le reseau local : une URL de rappel choisie
    librement le ferait POSTer n'importe ou chez soi — le routeur, une console
    d'administration, le NAS lui-meme. L'URL n'est donc acceptee que si son
    hote figure dans la liste declaree par le proprietaire de la cle d'acces, A
    LA CREATION de la cle et avec son mot de passe : quelqu'un qui vole la cle
    ne peut pas l'etendre.

    Codes : « illisible », « schema », « identifiants », « hote ».
    """
    if not isinstance(url, str) or not url or any(c in _AMBIGUS for c in url):
        return "illisible"
    try:
        morceaux = urllib.parse.urlsplit(url)
        schema = morceaux.scheme.lower()
        hote = morceaux.hostname
        # .port leve sur un port non numerique ou hors bornes : on le lit ici,
        # dans le try, plutot que de le decouvrir plus bas.
        port = morceaux.port
    except ValueError:
        return "illisible"
    # http et https seulement : file://, ftp://, gopher:// ou javascript:
    # feraient faire au client tout autre chose qu'un POST.
    if schema not in ("http", "https"):
        return "schema"
    # PAS D'IDENTIFIANTS DANS L'URL. « http://hote.autorise@ailleurs/ » est le
    # piege classique : un oeil (ou une regex) lit « hote.autorise », le client
    # se connecte a « ailleurs ». Et un vrai « user:mdp@ » finirait en clair
    # dans les journaux du studio.
    if morceaux.username is not None or morceaux.password is not None \
            or "@" in morceaux.netloc:
        return "identifiants"
    if not hote:
        return "illisible"
    hote = hote.lower().rstrip(".")
    if port is None:
        port = 443 if schema == "https" else 80
    # Liste vide : rien n'est autorise. « Pas de liste, pas de restriction »
    # serait la panne exacte que cette fonction existe pour empecher, ouverte
    # a toute cle creee sans y penser.
    if isinstance(hotes, str):
        # Une chaine seule n'est pas une liste de caracteres-hotes.
        hotes = (hotes,)
    for entree in hotes or ():
        lu = _entree(entree)
        if lu is None:
            continue
        h, p = lu
        # UNE ENTREE SANS PORT NE VAUT QUE POUR LE PORT PAR DEFAUT DU SCHEMA
        # (80 en http, 443 en https). Elle valait pour TOUS les ports de
        # l'hote : declarer « 192.168.1.10 » pour un n8n sur 5678 laissait une
        # cle volee faire POSTer le studio sur ComfyUI (8188), une console
        # d'administration, n'importe quel service de la machine (revue du
        # 4 novembre 2026). Qui veut un port le nomme : « hote:5678 ».
        defaut = 443 if schema == "https" else 80
        if h == hote and (p == port if p is not None else port == defaut):
            return None
    return "hote"


def _raison_du_statut(statut):
    """(fini, raison) pour une reponse recue."""
    if 200 <= statut < 300:
        return True, "livre"
    if 300 <= statut < 400:
        # ON NE SUIT PAS, ET ON N'INSISTE PAS : la cible d'une redirection
        # n'est pas dans la liste des hotes autorises, et redemander ne la
        # fera pas changer.
        return True, "redirection"
    if statut in _PASSAGERS:
        # 409 a sa raison : dans le journal du studio, « conflit apres 4
        # essai(s) » dit a l'operateur que n8n n'attendait pas (Wait jamais
        # atteint, ou execution deja finie), pas qu'il etait surcharge.
        return False, "conflit" if statut == 409 else "recepteur occupe"
    if statut >= 500:
        return False, "erreur du recepteur"
    return True, "refuse par le recepteur"


async def livrer(session, url, corps, secret, *, evenement, livraison,
                 delais=DELAIS, horloge=time.time, dormir=asyncio.sleep,
                 delai=DELAI_REPONSE):
    """POSTe le corps signe, avec re-essais. Rend
    {"livre": bool, "essais": int, "statut": int | None, "raison": str}.

    NE LEVE JAMAIS — sauf asyncio.CancelledError, qu'on laisse passer : un
    arret du studio doit pouvoir interrompre un rappel qui attend deux minutes
    son quatrieme essai, et une annulation avalee le ferait pendre.

    L'URL doit avoir ete acceptee par url_autorisee() : cette fonction ne
    connait pas la liste.
    """
    rendu = {"livre": False, "essais": 0, "statut": None,
             "raison": "aucun essai"}
    if evenement not in EVENEMENTS:
        rendu["raison"] = "evenement inconnu"
        return rendu
    try:
        # aiohttp ICI et pas en tete : les fonctions de signature restent
        # importables sans lui, par un recepteur qui n'a que la bibliotheque
        # standard.
        import aiohttp
    except ImportError:
        rendu["raison"] = "aiohttp absent"
        return rendu
    try:
        attente_max = aiohttp.ClientTimeout(total=delai)
        for attente in delais:
            await dormir(attente)
            rendu["essais"] += 1
            # SIGNE A NOUVEAU A CHAQUE ESSAI, avec l'heure de l'essai : le
            # quatrieme part deux minutes et demie apres le premier, et
            # l'horodatage d'origine approcherait la tolerance du recepteur —
            # au-dela, il serait refuse comme un rejeu.
            entetes = {
                "Content-Type": "application/json",
                ENTETE_SIGNATURE: signature(secret, int(horloge()), corps),
                ENTETE_EVENEMENT: evenement,
                ENTETE_LIVRAISON: livraison,
                "User-Agent": "ComfyStudio-rappel",
            }
            try:
                # allow_redirects=False : une redirection ferait sortir la
                # requete de la liste des hotes autorises, vers une cible que
                # personne n'a declaree.
                async with session.post(url, data=corps, headers=entetes,
                                        allow_redirects=False,
                                        timeout=attente_max) as reponse:
                    statut = reponse.status
            except asyncio.CancelledError:
                raise
            except asyncio.TimeoutError:
                rendu["statut"], rendu["raison"] = None, "delai depasse"
                continue
            except Exception:
                rendu["statut"], rendu["raison"] = None, "injoignable"
                continue
            rendu["statut"] = statut
            fini, rendu["raison"] = _raison_du_statut(statut)
            if fini:
                rendu["livre"] = rendu["raison"] == "livre"
                return rendu
        return rendu
    except asyncio.CancelledError:
        raise
    except Exception:
        # Un dormir() ou une session qui leve autre chose : le rappel est
        # perdu, le studio, lui, ne doit pas l'etre.
        rendu["raison"] = "erreur interne"
        return rendu
