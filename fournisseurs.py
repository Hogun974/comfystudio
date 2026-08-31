# -*- coding: utf-8 -*-
"""Modeles distants : LLM par cle d'API, et images « nano banana ».

Le studio tourne en local par defaut, et rien ne l'oblige a en sortir. Mais un
petit modele local ecrit mal, et certaines machines n'ont pas de carte du tout :
pouvoir brancher une cle d'API, pour le texte, pour l'image, ou pour les deux,
evite d'avoir a choisir entre « tout local » et « rien ».

Deux principes tiennent tout le fichier :

- **Le local reste la reference.** Un fournisseur distant qui echoue n'arrete
  rien : l'appelant retombe sur le modele local et le dit dans le journal. Une
  cle expiree ne doit pas transformer le studio en presse-papier.

- **Le nom du modele est un reglage, jamais une constante cachee.** Les
  catalogues des fournisseurs changent plus vite que ce fichier. Les defauts
  ci-dessous sont un point de depart ; quand un nom devient caduc, l'erreur du
  fournisseur remonte telle quelle dans le journal, et le reglage se corrige
  depuis la page d'administration sans toucher au code.

Ce module ne connait ni les cles ni les reglages : on les lui passe. Il ne les
enregistre nulle part et ne les journalise jamais.
"""
import asyncio
import base64
import contextvars
import json
import re

import aiohttp

# Delai large : un gros modele distant peut mettre une minute, et couper une
# generation a mi-chemin coute plus cher que d'attendre.
DELAI = aiohttp.ClientTimeout(total=180)


class EchecFournisseur(RuntimeError):
    """Le fournisseur n'a pas repondu, ou a repondu qu'il ne pouvait pas.

    Portee volontairement bavarde : le message remonte jusqu'au journal de la
    tache, parce que « modele inconnu » et « cle refusee » ne se corrigent pas
    de la meme facon, et que l'utilisateur est le seul a pouvoir le faire.
    """


# ── Texte ────────────────────────────────────────────────────────────────
#
# Chaque entree dit comment parler au fournisseur. « modele » n'est qu'un
# defaut : la page d'administration peut en imposer un autre.

LLM = {
    "anthropic": {
        "titre": "Anthropic (Claude)",
        "url": "https://api.anthropic.com/v1/messages",
        "modele": "claude-sonnet-5",
        "aide": "cle sur console.anthropic.com, commence par sk-ant-",
    },
    "openai": {
        "titre": "OpenAI",
        "url": "https://api.openai.com/v1/chat/completions",
        "modele": "gpt-4o",
        "aide": "cle sur platform.openai.com, commence par sk-",
    },
    "mistral": {
        "titre": "Mistral",
        "url": "https://api.mistral.ai/v1/chat/completions",
        "modele": "mistral-large-latest",
        "aide": "cle sur console.mistral.ai",
    },
    "mammouth": {
        # Agregateur francais : une seule cle pour GPT, Claude, Gemini et les
        # autres, en dialecte OpenAI. « mammouth-recommended » laisse le service
        # choisir, ce qui evite d'avoir a suivre les noms de modeles.
        "titre": "Mammouth",
        "url": "https://api.mammouth.ai/v1/chat/completions",
        "modele": "mammouth-recommended",
        "aide": "cle sur mammouth.ai ; texte seulement, pas d'image ni de son",
    },
    "google": {
        "titre": "Google (Gemini)",
        "url": "https://generativelanguage.googleapis.com/v1beta/models",
        # 2.5-flash a ete retire aux nouveaux comptes le 28 aout 2026, Google
        # renvoyant vers celui-ci. Modifiable depuis /admin quand il vieillira.
        "modele": "gemini-3.6-flash",
        "aide": "cle sur aistudio.google.com",
    },
}

# ── Image ────────────────────────────────────────────────────────────────

IMAGE = {
    "nanobanana": {
        "titre": "Nano Banana (Gemini Image)",
        "url": "https://generativelanguage.googleapis.com/v1beta/models",
        "modele": "gemini-2.5-flash-image",
        "aide": "meme cle que Google Gemini ; sait aussi retoucher une image fournie",
    },
}


# ── Musique et video ─────────────────────────────────────────────────────

AUDIO = {
    "lyria": {
        "titre": "Lyria 3 (Google)",
        "url": "https://generativelanguage.googleapis.com/v1beta/models",
        "modele": "lyria-3-clip-preview",
        "aide": "meme cle que Google ; clips d'environ 30 s",
    },
}

VIDEO = {
    "veo": {
        "titre": "Veo 3.1 (Google)",
        "url": "https://generativelanguage.googleapis.com/v1beta/models",
        "modele": "veo-3.1-fast-generate-preview",
        "aide": "meme cle que Google ; facturation a la seconde de video",
    },
}


OBJET3D = {
    "meshy": {
        "titre": "Meshy",
        "url": "https://api.meshy.ai/openapi/v1/image-to-3d",
        # « modele » sert ici de type de maillage : standard, smart-topology
        # ou lowpoly. Le champ de la page d'administration s'y prete tel quel.
        "modele": "standard",
        "aide": "cle sur meshy.ai (msy-…) ; part d'une image, rend un .glb",
    },
}


def _entete(fournisseur, cle):
    if fournisseur == "anthropic":
        return {"x-api-key": cle, "anthropic-version": "2023-06-01",
                "content-type": "application/json"}
    if fournisseur == "google":
        # Gemini prend la cle en en-tete plutot qu'en parametre d'URL : une URL
        # se retrouve dans les journaux du proxy, l'en-tete non.
        return {"x-goog-api-key": cle, "content-type": "application/json"}
    return {"Authorization": f"Bearer {cle}", "content-type": "application/json"}


def _corps_texte(fournisseur, modele, systeme, invite, temperature, json_mode):
    """Le meme echange, dans les trois dialectes en usage."""
    if fournisseur == "anthropic":
        corps = {"model": modele, "max_tokens": 4096, "temperature": temperature,
                 "messages": [{"role": "user", "content": invite}]}
        if systeme:
            corps["system"] = systeme
        return corps
    if fournisseur == "google":
        corps = {"contents": [{"parts": [{"text": invite}]}],
                 "generationConfig": {"temperature": temperature}}
        if systeme:
            corps["system_instruction"] = {"parts": [{"text": systeme}]}
        if json_mode:
            corps["generationConfig"]["responseMimeType"] = "application/json"
        return corps
    # OpenAI et compatibles
    messages = ([{"role": "system", "content": systeme}] if systeme else [])
    messages.append({"role": "user", "content": invite})
    corps = {"model": modele, "messages": messages, "temperature": temperature}
    if json_mode:
        corps["response_format"] = {"type": "json_object"}
    return corps


def _lire_texte(fournisseur, d):
    """Le texte d'une reponse, dans les trois dialectes.

    Une reponse VIDE est dite a voix haute. Elle est arrivee deux fois de suite
    sur une traduction, le 30 aout : le studio a repli sur le francais et
    prevenu l'utilisateur — le garde-fou a tenu — mais rien dans le journal ne
    permettait de savoir POURQUOI le modele n'avait rien rendu. On imprime donc
    ce qui explique : le motif d'arret et les types de blocs recus. Jamais le
    contenu, qui porterait la demande de quelqu'un.
    """
    texte = _extraire_texte(fournisseur, d)
    if not texte.strip():
        print(f"  [{fournisseur}] reponse sans texte — {_pourquoi_vide(fournisseur, d)}",
              flush=True)
    return texte


def _pourquoi_vide(fournisseur, d):
    """De quoi comprendre une reponse vide, sans jamais recopier son contenu."""
    if fournisseur == "anthropic":
        types = [b.get("type") for b in d.get("content", []) or []]
        return (f"arret={d.get('stop_reason')} blocs={types or 'aucun'} "
                f"usage={(d.get('usage') or {}).get('output_tokens')}")
    if fournisseur == "google":
        cands = d.get("candidates") or []
        if not cands:
            return f"aucun candidat, filtre={d.get('promptFeedback')}"
        return (f"arret={cands[0].get('finishReason')} "
                f"parts={len((cands[0].get('content') or {}).get('parts') or [])}")
    choix = d.get("choices") or []
    return (f"arret={choix[0].get('finish_reason')}" if choix else "aucun choix")


def _extraire_texte(fournisseur, d):
    if fournisseur == "anthropic":
        return "".join(b.get("text", "") for b in d.get("content", [])
                       if b.get("type") == "text")
    if fournisseur == "google":
        cands = d.get("candidates") or []
        if not cands:
            return ""
        return "".join(p.get("text", "")
                       for p in cands[0].get("content", {}).get("parts", []))
    choix = d.get("choices") or []
    return (choix[0].get("message", {}).get("content", "") if choix else "")


# Champs qu'un fournisseur peut refuser sans que la demande soit fautive : on
# les retire et on recommence, une seule fois.
_FACULTATIFS = ("temperature", "top_p", "top_k")


def _retirer(corps, champ):
    """Enleve un champ, ou qu'il soit niche. Vrai s'il y etait."""
    if champ in corps:
        corps.pop(champ)
        return True
    for niche in ("generationConfig", "options"):
        if isinstance(corps.get(niche), dict) and champ in corps[niche]:
            corps[niche].pop(champ)
            return True
    return False


def _champ_refuse(message, corps):
    """Le champ facultatif que le fournisseur dit ne pas vouloir, s'il y en a un."""
    bas = (message or "").lower()
    for champ in _FACULTATIFS:
        if champ in bas and (champ in corps
                             or any(champ in (corps.get(x) or {})
                                    for x in ("generationConfig", "options"))):
            return champ
    return None


def _pourquoi(d, statut):
    """Le message d'erreur du fournisseur, ramene a une ligne lisible."""
    err = d.get("error")
    if isinstance(err, dict):
        detail = err.get("message") or err.get("type") or ""
    elif isinstance(err, str):
        detail = err
    else:
        detail = d.get("message") or ""
    return f"HTTP {statut}" + (f" : {str(detail)[:200]}" if detail else "")


# Ce que le dernier appel a coute, tel que le fournisseur l'a compte lui-meme.
# Une ContextVar et non une variable de module : deux demandes se chevauchent
# sans arret dans ce studio, et un compteur partage attribuerait les jetons de
# l'une a l'autre. Une coroutine voit ce que ses propres appels y ont pose.
_JETONS = contextvars.ContextVar("jetons", default=(None, None))


def _compter_jetons(fournisseur, d):
    """(entree, sortie) tels que le fournisseur les rend, ou (None, None).

    On ne DEDUIT rien : compter les caracteres pour en faire des jetons donne un
    nombre qui a l'air juste et qui ne l'est pas. Quand l'API se tait — Veo et
    Meshy ne rendent qu'un nom de tache — l'appelant le saura et pourra le dire.
    """
    try:
        if fournisseur == "anthropic":
            u = d.get("usage") or {}
            return (u.get("input_tokens"), u.get("output_tokens"))
        if fournisseur == "google" or "usageMetadata" in d:
            u = d.get("usageMetadata") or {}
            # candidatesTokenCount manque sur une reponse bloquee, alors que
            # l'invite, elle, a bien ete lue et facturee.
            return (u.get("promptTokenCount"), u.get("candidatesTokenCount"))
        u = d.get("usage") or {}
        return (u.get("prompt_tokens"), u.get("completion_tokens"))
    except AttributeError:
        return (None, None)


def jetons_du_dernier_appel():
    """(entree, sortie) du dernier appel abouti dans cette coroutine."""
    return _JETONS.get()


async def _poster(url, corps, entetes, fournisseur):
    """Un envoi, avec un second essai si un champ facultatif est refuse."""
    for reste in (True, False):
        try:
            async with aiohttp.ClientSession(timeout=DELAI) as s:
                async with s.post(url, json=corps, headers=entetes) as r:
                    brut = await r.text()
                    try:
                        d = json.loads(brut)
                    except ValueError:
                        d = {}
                    if r.status == 200:
                        # Pose meme quand le fournisseur ne dit rien : sans
                        # cela, un appel muet heriterait du decompte du
                        # precedent, dans la meme coroutine.
                        _JETONS.set(_compter_jetons(fournisseur, d))
                        return d
                    pourquoi = _pourquoi(d, r.status)
        except asyncio.TimeoutError:
            raise EchecFournisseur("delai depasse")
        except aiohttp.ClientError as e:
            raise EchecFournisseur(f"injoignable ({type(e).__name__})")
        champ = _champ_refuse(pourquoi, corps) if reste else None
        if not champ or not _retirer(corps, champ):
            raise EchecFournisseur(pourquoi)
    raise EchecFournisseur(pourquoi)


async def texte(fournisseur, cle, invite, systeme=None, temperature=0.4,
                json_mode=False, modele=None):
    """Une reponse en texte, chez le fournisseur demande.

    Leve EchecFournisseur si quoi que ce soit cloche — a l'appelant de retomber
    sur le local.
    """
    conf = LLM.get(fournisseur)
    if not conf:
        raise EchecFournisseur(f"fournisseur inconnu : {fournisseur}")
    if not cle:
        raise EchecFournisseur(f"aucune cle enregistree pour {fournisseur}")
    modele = modele or conf["modele"]
    corps = _corps_texte(fournisseur, modele, systeme, invite, temperature, json_mode)
    url = (f"{conf['url']}/{modele}:generateContent" if fournisseur == "google"
           else conf["url"])
    d = await _poster(url, corps, _entete(fournisseur, cle), fournisseur)
    rendu = _lire_texte(fournisseur, d)
    if not rendu.strip():
        raise EchecFournisseur("reponse vide")
    return rendu


async def image(fournisseur, cle, invite, modele=None, entree=None):
    """Une image, rendue en octets bruts avec son type MIME.

    « entree » est une image a retoucher, sous forme (octets, type MIME) : c'est
    la ou ces modeles sont interessants, l'edition guidee par une phrase.
    """
    return await _media(IMAGE, fournisseur, cle, invite, modele, entree, "image")


async def musique(fournisseur, cle, invite, modele=None):
    """Un morceau, rendu en octets bruts avec son type MIME.

    Meme appel que pour une image : ces modeles rendent leur resultat en clair
    dans la reponse, encode en base64. Seul le type MIME change.
    """
    return await _media(AUDIO, fournisseur, cle, invite, modele, None, "musique")


async def _media(table, fournisseur, cle, invite, modele=None, entree=None,
                 quoi="media"):
    conf = table.get(fournisseur)
    if not conf:
        raise EchecFournisseur(f"fournisseur de {quoi} inconnu : {fournisseur}")
    if not cle:
        raise EchecFournisseur(f"aucune cle enregistree pour {fournisseur}")
    modele = modele or conf["modele"]
    parts = [{"text": invite}]
    if entree:
        octets, mime = entree
        parts.insert(0, {"inline_data": {"mime_type": mime,
                                         "data": base64.b64encode(octets).decode()}})
    corps = {"contents": [{"parts": parts}]}
    url = f"{conf['url']}/{modele}:generateContent"
    d = await _poster(url, corps, _entete("google", cle), fournisseur)

    for cand in d.get("candidates") or []:
        for p in cand.get("content", {}).get("parts", []):
            enligne = p.get("inlineData") or p.get("inline_data")
            if enligne and enligne.get("data"):
                mime = enligne.get("mimeType") or enligne.get("mime_type") or "image/png"
                return base64.b64decode(enligne["data"]), mime
    # Rien recu : le plus souvent un refus, qui met alors un texte a la place.
    # Le rapporter vaut mieux qu'un « rien recu » opaque — Lyria refuse par
    # exemple les paroles nommant une personne reelle (PROHIBITED_CONTENT).
    texte_rendu = _lire_texte("google", d).strip()
    bloc = (d.get("promptFeedback") or {}).get("blockReason")
    if bloc:
        raise EchecFournisseur(f"demande refusee par le fournisseur ({bloc})")
    raison = (d.get("candidates") or [{}])[0].get("finishReason") or ""
    raise EchecFournisseur(f"aucun resultat rendu"
                           + (f" ({raison})" if raison else "")
                           + (f" : {texte_rendu[:160]}" if texte_rendu else ""))


def indice(cle):
    """De quoi reconnaitre une cle sans la reveler : ses quatre derniers signes."""
    cle = cle or ""
    return ("…" + cle[-4:]) if len(cle) > 8 else "…"


async def video(fournisseur, cle, invite, modele=None, entree=None,
                secondes_max=600, tid=None, dire=None):
    """Une video. Le seul appel qui ne rend pas son resultat tout de suite.

    Veo travaille en tache longue : on soumet, on obtient un nom d'operation,
    on interroge jusqu'a ce qu'elle soit finie, puis on va chercher le fichier.
    D'ou la fonction separee — les trois autres modalites tiennent en un aller.

    « dire » recoit les nouvelles a mesure : sans cela, l'utilisateur regarde une
    barre immobile pendant plusieurs minutes sans savoir si ca avance.
    """
    conf = VIDEO.get(fournisseur)
    if not conf:
        raise EchecFournisseur(f"fournisseur de video inconnu : {fournisseur}")
    if not cle:
        raise EchecFournisseur(f"aucune cle enregistree pour {fournisseur}")
    modele = modele or conf["modele"]
    entetes = _entete("google", cle)

    instance = {"prompt": invite}
    if entree:
        octets, mime = entree
        instance["image"] = {"bytesBase64Encoded": base64.b64encode(octets).decode(),
                             "mimeType": mime}
    depart = await _poster(f"{conf['url']}/{modele}:predictLongRunning",
                           {"instances": [instance]}, entetes, fournisseur)
    operation = depart.get("name")
    if not operation:
        raise EchecFournisseur(f"aucune operation rendue : {json.dumps(depart)[:160]}")

    base = "https://generativelanguage.googleapis.com/v1beta"
    attendu = 0
    async with aiohttp.ClientSession(timeout=DELAI) as s:
        while attendu < secondes_max:
            await asyncio.sleep(10)
            attendu += 10
            async with s.get(f"{base}/{operation}", headers=entetes) as r:
                brut = await r.text()
                try:
                    etat = json.loads(brut)
                except ValueError:
                    etat = {}
                if r.status != 200:
                    raise EchecFournisseur(_pourquoi(etat, r.status))
            if etat.get("error"):
                raise EchecFournisseur(_pourquoi(etat, 200))
            if etat.get("done"):
                break
            if dire and attendu % 30 == 0:
                dire(f"video en cours chez {conf['titre']} ({attendu} s)")
        else:
            raise EchecFournisseur(f"toujours pas prete apres {secondes_max} s")

    octets, mime = await _extraire_video(etat, entetes)
    if not octets:
        raise EchecFournisseur(f"operation finie sans video : {json.dumps(etat)[:200]}")
    return octets, mime


def _cherche(objet, clefs):
    """Premiere valeur trouvee sous l'une de ces clefs, a n'importe quelle
    profondeur. Les reponses de taches longues changent de forme d'une version a
    l'autre : chercher vaut mieux qu'un chemin fige qui casse en silence."""
    if isinstance(objet, dict):
        for k, v in objet.items():
            if k in clefs and isinstance(v, str) and v:
                return v
            trouve = _cherche(v, clefs)
            if trouve:
                return trouve
    elif isinstance(objet, list):
        for x in objet:
            trouve = _cherche(x, clefs)
            if trouve:
                return trouve
    return None


async def _extraire_video(etat, entetes):
    """La video, qu'elle soit jointe en clair ou derriere un lien."""
    enligne = _cherche(etat, {"bytesBase64Encoded", "videoBytes", "data"})
    if enligne:
        return base64.b64decode(enligne), "video/mp4"
    lien = _cherche(etat, {"uri", "url", "downloadUri"})
    if not lien:
        return None, ""
    async with aiohttp.ClientSession(timeout=DELAI) as s:
        async with s.get(lien, headers=entetes) as r:
            if r.status != 200:
                raise EchecFournisseur(f"telechargement refuse (HTTP {r.status})")
            return await r.read(), r.headers.get("Content-Type", "video/mp4")


# Ou lire le catalogue de chaque fournisseur, et comment reconnaitre la
# modalite d'un modele a son nom. Les listes changent : c'est justement pour
# cela qu'on les lit au lieu de les figer.
_CATALOGUES = {
    "anthropic": "https://api.anthropic.com/v1/models?limit=200",
    "openai": "https://api.openai.com/v1/models",
    "mistral": "https://api.mistral.ai/v1/models",
    "mammouth": "https://api.mammouth.ai/v1/models",
    "google": "https://generativelanguage.googleapis.com/v1beta/models?pageSize=1000",
    "nanobanana": "https://generativelanguage.googleapis.com/v1beta/models?pageSize=1000",
    "lyria": "https://generativelanguage.googleapis.com/v1beta/models?pageSize=1000",
    "veo": "https://generativelanguage.googleapis.com/v1beta/models?pageSize=1000",
}

_MOTIFS = {
    "nanobanana": r"image",
    "lyria": r"lyria|music",
    "veo": r"veo",
}

# Ecarte ce qui n'est pas de la generation de texte quand on cherche un LLM.
_PAS_TEXTE = r"image|video|veo|lyria|tts|embedding|audio|imagen|whisper|dall|moderation"


_TYPES_MESHY = ("standard", "smart-topology", "lowpoly")


async def lister_modeles(fournisseur, cle):
    """Les identifiants de modeles utilisables chez ce fournisseur.

    Rend une liste, vide si le fournisseur ne sait pas repondre — on ne bloque
    jamais la page d'administration sur un catalogue indisponible.
    """
    if fournisseur == "meshy":
        # Meshy n'expose pas de catalogue : ses trois topologies sont fixes.
        return list(_TYPES_MESHY)
    url = _CATALOGUES.get(fournisseur)
    if not url or not cle:
        return []
    entete = _entete("google" if "googleapis" in url else fournisseur, cle)
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as s:
            async with s.get(url, headers=entete) as r:
                if r.status != 200:
                    return []
                d = json.loads(await r.text())
    except (aiohttp.ClientError, asyncio.TimeoutError, ValueError):
        return []

    noms = []
    for m in (d.get("models") or d.get("data") or []):
        nom = (m.get("name") or m.get("id") or "").replace("models/", "")
        if not nom:
            continue
        methodes = m.get("supportedGenerationMethods") or []
        motif = _MOTIFS.get(fournisseur)
        if motif:
            if not re.search(motif, nom, re.I):
                continue
            # Veo ne repond pas a generateContent : filtrer sur cette methode
            # ferait disparaitre toute la video.
            if methodes and not any(x in methodes for x in
                                    ("generateContent", "predictLongRunning")):
                continue
        elif fournisseur in LLM:
            if re.search(_PAS_TEXTE, nom, re.I):
                continue
            if methodes and "generateContent" not in methodes:
                continue
        noms.append(nom)
    return sorted(set(noms))


async def objet3d(fournisseur, cle, invite, modele=None, entree=None,
                  secondes_max=600, tid=None, dire=None):
    """Un maillage, a partir d'une image. Tache longue, comme la video.

    Meshy part d'une image et non d'un texte : c'est aussi ce que fait la voie
    locale, qui dessine d'abord une vue de reference puis la sculpte. Sans
    image, on ne bricole pas un substitut — on le dit, et l'appelant retombe
    sur le local, qui sait produire cette vue.
    """
    conf = OBJET3D.get(fournisseur)
    if not conf:
        raise EchecFournisseur(f"fournisseur 3D inconnu : {fournisseur}")
    if not cle:
        raise EchecFournisseur(f"aucune cle enregistree pour {fournisseur}")
    if not entree:
        raise EchecFournisseur("aucune image de depart")
    octets, mime = entree
    corps = {"image_url": f"data:{mime};base64," + base64.b64encode(octets).decode(),
             "model_type": modele or conf["modele"], "should_texture": True}
    if invite:
        corps["texture_prompt"] = invite[:600]
    entetes = {"Authorization": f"Bearer {cle}", "content-type": "application/json"}

    depart = await _poster(conf["url"], corps, entetes, fournisseur)
    tache = depart.get("result") or depart.get("id")
    if not tache:
        raise EchecFournisseur(f"aucune tache rendue : {json.dumps(depart)[:160]}")

    attendu = 0
    async with aiohttp.ClientSession(timeout=DELAI) as s:
        while attendu < secondes_max:
            await asyncio.sleep(10)
            attendu += 10
            async with s.get(f"{conf['url']}/{tache}", headers=entetes) as r:
                brut = await r.text()
                try:
                    etat = json.loads(brut)
                except ValueError:
                    etat = {}
                if r.status != 200:
                    raise EchecFournisseur(_pourquoi(etat, r.status))
            statut = etat.get("status")
            if statut == "SUCCEEDED":
                break
            if statut in ("FAILED", "CANCELED"):
                raison = (etat.get("task_error") or {}).get("message") or statut
                raise EchecFournisseur(f"{statut} : {str(raison)[:160]}")
            if dire and attendu % 30 == 0:
                dire(f"maillage en cours chez {conf['titre']} "
                     f"({etat.get('progress', 0)} %)")
        else:
            raise EchecFournisseur(f"toujours pas pret apres {secondes_max} s")

    liens = etat.get("model_urls") or {}
    lien = liens.get("glb") or next((v for v in liens.values() if v), None)
    if not lien:
        raise EchecFournisseur("tache finie sans maillage")
    async with aiohttp.ClientSession(timeout=DELAI) as s:
        async with s.get(lien) as r:
            if r.status != 200:
                raise EchecFournisseur(f"telechargement refuse (HTTP {r.status})")
            return await r.read(), "model/gltf-binary"
