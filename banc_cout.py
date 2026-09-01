# -*- coding: utf-8 -*-
"""Banc du compteur d'appels distants.

Ce qu'il faut prouver, et rien d'autre :

  1. les jetons rendus par chaque dialecte d'API sont lus tels quels,
     et une API qui se tait rend (None, None) — pas une estimation ;
  2. un appel abouti laisse une ligne relisible, avec le compte, la modalite,
     les octets et la duree ;
  3. le fichier se relit meme si la derniere ligne a ete coupee en plein vol ;
  4. le plafond eteint le nuage PAR LE CHEMIN EXISTANT — nuage_actif,
     llm_distant_possible, choix_distant — et se dit en francais ;
  5. la demande en cours n'est pas cassee : le repli local est toujours la ;
  6. le compteur est borne : le mois d'avant-hier disparait du fichier ;
  7. rien n'est ecrit depuis la boucle d'evenements.

Lance dans un conteneur jetable :
  docker run --rm -v /tmp/x:/banc -w /banc --entrypoint python \\
      comfystudio:latest banc_cout.py
"""
import asyncio
import io
import json
import os
import shutil
import sys
import threading
import tempfile
import time

DONNEES = tempfile.mkdtemp(prefix="banc_cout_")
os.environ["STUDIO_DONNEES"] = DONNEES
os.environ["STUDIO_HOTE"] = "127.0.0.1"

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fournisseurs
import serveur

VERTS = []
ROUGES = []


def verifier(quoi, condition, detail=""):
    (VERTS if condition else ROUGES).append(quoi)
    print(("  ok   " if condition else "  RATE ") + quoi
          + (f"   [{detail}]" if detail else ""), flush=True)


print("=" * 70)
print("1. les jetons, tels que le fournisseur les compte")
print("=" * 70)

# Formes reelles des trois dialectes, reduites a ce qu'on y lit.
verifier("Anthropic : usage.input_tokens / output_tokens",
         fournisseurs._compter_jetons(
             "anthropic",
             {"content": [{"type": "text", "text": "bonjour"}],
              "usage": {"input_tokens": 812, "output_tokens": 143}})
         == (812, 143))

verifier("OpenAI et compatibles : usage.prompt_tokens / completion_tokens",
         fournisseurs._compter_jetons(
             "openai",
             {"choices": [{"message": {"content": "x"}}],
              "usage": {"prompt_tokens": 40, "completion_tokens": 9}})
         == (40, 9))

verifier("Google : usageMetadata.promptTokenCount / candidatesTokenCount",
         fournisseurs._compter_jetons(
             "google",
             {"candidates": [{"content": {"parts": [{"text": "x"}]}}],
              "usageMetadata": {"promptTokenCount": 1290,
                                "candidatesTokenCount": 77}})
         == (1290, 77))

verifier("Nano Banana passe par la meme metadonnee que Gemini",
         fournisseurs._compter_jetons(
             "nanobanana",
             {"usageMetadata": {"promptTokenCount": 15,
                                "candidatesTokenCount": 1290}})
         == (15, 1290))

# Le point qui compte : ne RIEN inventer quand l'API se tait.
verifier("Veo ne rend qu'un nom de tache : aucun jeton, et on ne l'estime pas",
         fournisseurs._compter_jetons(
             "veo", {"name": "models/veo-3.1/operations/abc"}) == (None, None))
verifier("Meshy non plus",
         fournisseurs._compter_jetons("meshy", {"result": "018f-…"})
         == (None, None))
verifier("une reponse bloquee garde les jetons d'entree, deja lus",
         fournisseurs._compter_jetons(
             "google", {"promptFeedback": {"blockReason": "SAFETY"},
                        "usageMetadata": {"promptTokenCount": 33}})
         == (33, None))


print()
print("=" * 70)
print("2. un appel abouti laisse une ligne relisible")
print("=" * 70)


async def consigner_quelques():
    serveur.consigner_appel_distant("anthropic", "llm", None, 3.2,
                                    octets=1840, jetons=(812, 143))
    serveur.consigner_appel_distant("anthropic", "llm", None, 1.1,
                                    octets=420, jetons=(200, 30))
    serveur.consigner_appel_distant("nanobanana", "image", None, 9.4,
                                    octets=1_240_000, jetons=(15, 1290))
    # Le cas franc : le fournisseur ne dit rien.
    serveur.consigner_appel_distant("veo", "video", None, 96.0,
                                    octets=4_100_000, jetons=(None, None))


_b = asyncio.new_event_loop()
_b.run_until_complete(consigner_quelques())
_b.close()
serveur._A_ECRIRE.join()

lignes = [json.loads(l) for l in
          io.open(serveur.FICHIER_COUTS, encoding="utf-8") if l.strip()]
verifier("quatre appels, quatre lignes", len(lignes) == 4, str(len(lignes)))
verifier("une ligne porte quand, mois, fournisseur, modalite, compte",
         all({"quand", "mois", "fournisseur", "modalite", "compte"}
             <= set(l) for l in lignes))
verifier("les jetons rendus sont ecrits tels quels",
         lignes[0]["jetons_entree"] == 812 and lignes[0]["jetons_sortie"] == 143)
verifier("les jetons absents sont ecrits null, pas zero",
         lignes[3]["jetons_entree"] is None,
         json.dumps(lignes[3], ensure_ascii=False)[:110])
verifier("les octets et la duree sont la, mesures",
         lignes[3]["octets"] == 4_100_000 and lignes[3]["secondes"] == 96.0)
verifier("aucun prix nulle part",
         not any(k in l for l in lignes for k in ("euros", "prix", "cout")))

cpt = serveur.COMPTEUR[serveur._mois()]["anonyme"]
verifier("le total en memoire suit : 2 appels texte chez Anthropic",
         cpt["anthropic/llm"]["appels"] == 2)
verifier("1012 jetons d'entree, 173 de sortie",
         cpt["anthropic/llm"]["jetons_entree"] == 1012
         and cpt["anthropic/llm"]["jetons_sortie"] == 173)
verifier("l'appel muet est compte a part, pas noye dans un zero",
         cpt["veo/video"]["sans_jetons"] == 1
         and cpt["veo/video"]["jetons_entree"] == 0)
verifier("appels_du_mois voit les quatre",
         serveur.appels_du_mois("anonyme") == 4)


print()
print("=" * 70)
print("3. une ecriture coupee ne fait pas perdre le fichier")
print("=" * 70)

# Exactement ce qu'un arret de conteneur laisse : une derniere ligne tronquee.
with io.open(serveur.FICHIER_COUTS, "a", encoding="utf-8") as f:
    f.write('{"quand": "2026-08-31 23:59:59", "mois": "' + serveur._mois()
            + '", "fournisseur": "anthro')
serveur.charger_compteur()
verifier("la ligne coupee est sautee, les quatre autres sont relues",
         serveur.appels_du_mois("anonyme") == 4,
         f"{serveur.appels_du_mois('anonyme')} appels relus")


print()
print("=" * 70)
print("4. le plafond, par le chemin qui existe deja")
print("=" * 70)

PID = "banc"
serveur.CLES["anthropic"] = {"cle": "sk-ant-banc", "modele": ""}
serveur.CHOIX["llm"] = "anthropic"
serveur.CHOIX["image"] = "nanobanana"
serveur.CLES["nanobanana"] = {"cle": "banc", "modele": ""}

serveur.PREFERENCES["plafond_nuage"] = 0
verifier("sans plafond, le texte part au loin",
         serveur.llm_distant_possible("un chat roux", PID) == "anthropic")
verifier("sans plafond, l'image aussi",
         serveur.choix_distant("image", "un chat roux", {}, PID) == "nanobanana")
verifier("sans plafond, rien a expliquer",
         serveur.raison_du_local("un chat roux", None, PID) == "")

# Le compte du banc fait ses trois appels du mois.
for _ in range(3):
    serveur._cumuler({"mois": serveur._mois(),
                      "compte": serveur.dossier_utilisateur(PID),
                      "fournisseur": "anthropic", "modalite": "llm",
                      "jetons_entree": 10, "jetons_sortie": 5,
                      "octets": 100, "secondes": 1.0})
serveur.PREFERENCES["plafond_nuage"] = 3

verifier("nuage_actif s'eteint pour le compte au plafond",
         serveur.nuage_actif(PID, "llm") is False)
verifier("… pour TOUTES les modalites, pas seulement le texte",
         serveur.nuage_actif(PID, "image") is False
         and serveur.nuage_actif(PID, "video") is False)
verifier("llm_distant_possible rend le local",
         serveur.llm_distant_possible("un chat roux", PID) == "")
verifier("choix_distant aussi",
         serveur.choix_distant("image", "un chat roux", {}, PID) == "")
raison = serveur.raison_du_local("un chat roux", None, PID)
verifier("et le studio le DIT, en francais, avec le nombre",
         "plafond" in raison and "3" in raison, raison)
verifier("le voisin, lui, n'est pas plafonne",
         serveur.llm_distant_possible("un chat roux", "quelqu-un-d-autre")
         == "anthropic")
verifier("etat_plafond dit ou en est ce compte",
         serveur.etat_plafond(PID) == {"compte": "banc", "mois": serveur._mois(),
                                       "limite": 3, "faits": 3, "atteint": True})
serveur.PREFERENCES["plafond_nuage"] = 0
verifier("plafond a zero : plus aucune limite, comme avant",
         serveur.llm_distant_possible("un chat roux", PID) == "anthropic")
serveur.PREFERENCES["plafond_nuage"] = 3


print()
print("=" * 70)
print("5. la demande en cours n'est pas cassee")
print("=" * 70)

# Ce que voit la suite du code : un moteur local, pas une exception.
verifier("le repli local de chaque moteur distant existe toujours",
         all(m["repli"] in serveur.CATALOGUE
             for m in serveur.MOTEURS_DISTANTS.values()))
verifier("l'interrupteur de la barre du haut rend l'etat, plafond compris",
         serveur.etat_plafond(PID)["atteint"] is True)
serveur.NUAGE[PID] = {"llm": True}
verifier("un interrupteur laisse allume ne rouvre pas le robinet",
         serveur.nuage_actif(PID, "llm") is False)
serveur.NUAGE.pop(PID, None)


print()
print("=" * 70)
print("6. le compteur est borne")
print("=" * 70)

verifier("deux mois montres, pas plus", len(serveur.mois_montres()) == 2)

# Un mois hors de portee de la vue, et beaucoup de lignes.
vieux = "2019-01"
with io.open(serveur.FICHIER_COUTS, "a", encoding="utf-8") as f:
    for i in range(9000):
        f.write(json.dumps({"quand": "2019-01-05 10:00:00", "mois": vieux,
                            "fournisseur": "anthropic", "modalite": "llm",
                            "compte": "vieux", "jetons_entree": 100,
                            "jetons_sortie": 50, "octets": 900,
                            "secondes": 2.0}) + "\n")
avant = os.path.getsize(serveur.FICHIER_COUTS)
serveur.TAILLE_COUTS = 64 * 1024        # le seuil, abaisse pour le banc
serveur._tailler()
apres = os.path.getsize(serveur.FICHIER_COUTS)
verifier("le fichier a fondu", apres < avant // 10, f"{avant} → {apres} octets")
restants = [json.loads(l) for l in
            io.open(serveur.FICHIER_COUTS, encoding="utf-8") if l.strip()]
verifier("plus une seule ligne de 2019", not any(l["mois"] == vieux
                                                 for l in restants))
verifier("les appels du mois en cours sont intacts", len(restants) == 4)
serveur.charger_compteur()
verifier("le compteur relu ne connait pas 2019", vieux not in serveur.COMPTEUR)

# Un studio qui tourne quatre mois d'affilee ne doit pas garder quatre tables.
serveur.COMPTEUR["2026-03"] = {"vieux": {"anthropic/llm": {"appels": 99}}}
serveur.consigner_appel_distant("anthropic", "llm", None, 1.0, octets=1,
                                jetons=(1, 1))
serveur._A_ECRIRE.join()
verifier("un mois passe de la memoire est purge au premier appel suivant",
         "2026-03" not in serveur.COMPTEUR
         and set(serveur.COMPTEUR) <= set(serveur.mois_montres()),
         ", ".join(sorted(serveur.COMPTEUR)))


print()
print("=" * 70)
print("7. rien ne s'ecrit depuis la boucle d'evenements")
print("=" * 70)


async def mesurer_la_boucle(consigner, tours=400):
    """Le retard d'un tour de boucle, avec et sans consignation.

    Une comparaison et non un seuil absolu : la machine du banc heberge vingt
    services, et un a-coup de l'ordonnanceur a 5 ms ne dit rien de notre code.
    Ce qui se mesure ici, c'est le SURCOUT.
    """
    retards = []
    for _ in range(tours):
        t0 = time.perf_counter()
        if consigner:
            serveur.consigner_appel_distant("anthropic", "llm", None, 1.0,
                                            octets=500, jetons=(10, 5))
        await asyncio.sleep(0)
        retards.append(time.perf_counter() - t0)
    return sorted(retards)


def median(v):
    return v[len(v) // 2]


boucle = asyncio.new_event_loop()
temoin = boucle.run_until_complete(mesurer_la_boucle(False))
mesure = boucle.run_until_complete(mesurer_la_boucle(True))
boucle.close()
surcout = (median(mesure) - median(temoin)) * 1000
verifier("consigner coute moins d'un dixieme de milliseconde a la boucle",
         surcout < 0.1,
         f"surcout median {surcout:.4f} ms, temoin {median(temoin)*1000:.4f} ms")
serveur._A_ECRIRE.join()
verifier("les 400 lignes sont bien arrivees sur le disque",
         sum(1 for l in io.open(serveur.FICHIER_COUTS, encoding="utf-8")
             if l.strip()) >= 400)
verifier("l'ecriture se fait dans un fil a part",
         serveur._ECRIVAIN is not None and serveur._ECRIVAIN.daemon
         and serveur._ECRIVAIN.name == "couts-nuage")

# LA preuve : un disque lent. On ralentit le fil d'ecriture de 50 ms par ligne.
# Si l'ecriture etait synchrone, quarante appels coleraient deux secondes a la
# boucle d'evenements — donc a toutes les generations en cours.
_vrai_tailler = serveur._tailler
serveur._tailler = lambda: time.sleep(0.05)


async def quarante_appels():
    t0 = time.perf_counter()
    for _ in range(40):
        serveur.consigner_appel_distant("anthropic", "llm", None, 1.0,
                                        octets=500, jetons=(10, 5))
        await asyncio.sleep(0)
    return time.perf_counter() - t0


boucle = asyncio.new_event_loop()
mis = boucle.run_until_complete(quarante_appels())
boucle.close()
verifier("disque a 50 ms la ligne : la boucle ne l'attend pas",
         mis < 0.2, f"40 appels en {mis*1000:.1f} ms au lieu de 2000 ms")
verifier("… et le fil d'ecriture, lui, a bien du travail en retard",
         serveur._A_ECRIRE.qsize() > 0, f"{serveur._A_ECRIRE.qsize()} en file")
serveur._tailler = _vrai_tailler
serveur._A_ECRIRE.join()

# La file est bornee : un disque bloque coute une ligne, pas une generation.
verifier("la file d'ecriture est bornee", serveur._A_ECRIRE.maxsize == 2000)


print()
print("=" * 70)
print("8. la vue d'administration")
print("=" * 70)


serveur.ADMIN_JETON = "jeton-de-banc"


class FauxReq:
    """Le strict necessaire pour admin_ok() et le handler."""
    method = "GET"
    headers = {"X-Admin": ""}
    cookies = {}

    def __init__(self, admin):
        self._admin = admin
        self.headers = {"X-Admin": serveur.ADMIN_JETON if admin else "faux"}

    def get(self, cle, defaut=None):
        return defaut


boucle = asyncio.new_event_loop()
rep = boucle.run_until_complete(serveur.api_admin_couts(FauxReq(False)))
verifier("sans jeton d'administration : refuse", rep.status == 403)
rep = boucle.run_until_complete(serveur.api_admin_couts(FauxReq(True)))
boucle.close()
vue = json.loads(rep.body.decode())
verifier("deux mois rendus", len(vue["mois"]) == 2)
verifier("le mois en cours porte des comptes",
         bool(vue["mois"][0]["comptes"]))
c0 = vue["mois"][0]["comptes"][0]
verifier("chaque compte a son total et son detail par fournisseur",
         {"compte", "appels", "jetons_entree", "sans_jetons", "octets",
          "secondes", "detail"} <= set(c0))
verifier("le detail nomme le fournisseur ET la modalite",
         all({"fournisseur", "modalite"} <= set(x) for x in c0["detail"]))
verifier("le plafond voyage avec la vue", vue["plafond"] == 3)
verifier("toujours aucun euro dans la reponse",
         "euro" not in rep.body.decode().lower())

print()
print("=" * 70)
print("9. le chemin reel, de la reponse HTTP a la ligne consignee")
print("=" * 70)

# Le seul endroit ou l'on peut se tromper sans que rien ne le dise : les jetons
# voyagent de _poster() jusqu'a _appeler_llm() par une ContextVar. On coupe
# donc au ras du reseau, et pas plus haut — tout le reste est le vrai code.
REPONSE = [{}]


class FausseReponse:
    status = 200

    def __init__(self, corps):
        self._corps = corps

    async def text(self):
        return json.dumps(self._corps)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False


class FausseSession:
    def __init__(self, *a, **k):
        pass

    def post(self, url, json=None, headers=None):
        return FausseReponse(REPONSE[0])

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False


vraie_session = fournisseurs.aiohttp.ClientSession
fournisseurs.aiohttp.ClientSession = FausseSession

serveur.PREFERENCES["plafond_nuage"] = 0
serveur.CHOIX["llm"] = "anthropic"
serveur.TACHES["banc-tid"] = {"proprietaire": "quelqu-un"}
REPONSE[0] = {"content": [{"type": "text", "text": "un chat roux sur un mur"}],
              "usage": {"input_tokens": 812, "output_tokens": 143}}

avant = serveur.appels_du_mois("quelqu-un")
boucle = asyncio.new_event_loop()
rendu = boucle.run_until_complete(
    serveur._appeler_llm("un chat roux", None, None, False, None, 0.4,
                         "banc-tid"))
boucle.close()
serveur._A_ECRIRE.join()
fournisseurs.aiohttp.ClientSession = vraie_session

verifier("l'appel distant a bien rendu son texte",
         rendu == "un chat roux sur un mur")
verifier("un appel de plus au compteur de ce compte",
         serveur.appels_du_mois("quelqu-un") == avant + 1)
derniere = [json.loads(l) for l in
            io.open(serveur.FICHIER_COUTS, encoding="utf-8") if l.strip()][-1]
verifier("les jetons ont traverse fournisseurs.texte() jusqu'a la ligne",
         (derniere["jetons_entree"], derniere["jetons_sortie"]) == (812, 143),
         json.dumps(derniere, ensure_ascii=False))
verifier("la ligne porte le compte, le fournisseur et la modalite",
         derniere["compte"] == "quelqu-un"
         and derniere["fournisseur"] == "anthropic"
         and derniere["modalite"] == "llm")
verifier("les octets rendus sont ceux du texte",
         derniere["octets"] == len("un chat roux sur un mur".encode("utf-8")))

# Et le plafond, sur ce meme chemin reel : la demande n'est pas cassee, elle
# repart en local — ici sans Ollama joignable, donc elle leve, ce qui prouve
# justement qu'elle a quitte le nuage au lieu de le rappeler.
serveur.PREFERENCES["plafond_nuage"] = 1
fournisseurs.aiohttp.ClientSession = FausseSession
boucle = asyncio.new_event_loop()
try:
    boucle.run_until_complete(
        serveur._appeler_llm("un chat roux", None, None, False, None, 0.4,
                             "banc-tid"))
    partie = True
except Exception:
    partie = False
finally:
    boucle.close()
    fournisseurs.aiohttp.ClientSession = vraie_session
    serveur._A_ECRIRE.join()
verifier("au plafond, l'appel ne part plus chez le fournisseur",
         not partie and serveur.appels_du_mois("quelqu-un") == avant + 1,
         f"{serveur.appels_du_mois('quelqu-un')} appels comptes")
serveur.PREFERENCES["plafond_nuage"] = 0

print()
print("=" * 70)
print("10. le plafond sous la rafale : plus un « verifier puis agir »")
print("=" * 70)

# La course ne se voit qu'avec de la LATENCE : c'est pendant l'aller-retour que
# le compteur reste immobile, puisqu'il n'est ecrit qu'au retour. On compte les
# departs au ras du reseau, la ou l'argent sort.
PARTIS = [0]


class ReponseLente(FausseReponse):
    async def text(self):
        await asyncio.sleep(0.20)          # un aller-retour ordinaire
        return json.dumps(self._corps)


class SessionQuiCompte(FausseSession):
    def post(self, url, json=None, headers=None):
        PARTIS[0] += 1
        return ReponseLente(REPONSE[0])


async def rafale(combien):
    return await asyncio.gather(*[
        serveur._appeler_llm("un chat roux", None, None, False, None, 0.4,
                             "banc-tid")
        for _ in range(combien)], return_exceptions=True)


serveur.TACHES["banc-tid"] = {"proprietaire": "rafale"}
fournisseurs.aiohttp.ClientSession = SessionQuiCompte
# TRAVAILLEURS d'abord : c'est le nombre que le studio peut reellement lancer
# ensemble, et donc le depassement qu'on payait. Dix ensuite, pour montrer que
# la correction ne tient pas a un nombre particulier.
for combien in (serveur.TRAVAILLEURS, 10):
    serveur.COMPTEUR.clear()
    serveur._EN_VOL_NUAGE.clear()
    PARTIS[0] = 0
    serveur.PREFERENCES["plafond_nuage"] = 1
    _b = asyncio.new_event_loop()
    _b.run_until_complete(rafale(combien))
    _b.close()
    serveur._A_ECRIRE.join()
    verifier(f"plafond a 1, {combien} appels lances ensemble : un seul part",
             PARTIS[0] == 1 and serveur.appels_du_mois("rafale") == 1,
             f"{PARTIS[0]} partis chez le fournisseur, "
             f"{serveur.appels_du_mois('rafale')} consignes")
fournisseurs.aiohttp.ClientSession = vraie_session
verifier("aucune place n'est restee prise apres la rafale",
         not serveur._EN_VOL_NUAGE, str(serveur._EN_VOL_NUAGE))


class ReponseRefusee(FausseReponse):
    status = 500

    async def text(self):
        return "cle refusee"


class SessionQuiRefuse(FausseSession):
    def post(self, url, json=None, headers=None):
        return ReponseRefusee({})


# Une place jamais rendue fermerait le robinet jusqu'a la fin du mois : c'est la
# panne que la correction pourrait introduire, donc celle qu'on epingle.
serveur.COMPTEUR.clear()
serveur._EN_VOL_NUAGE.clear()
serveur.PREFERENCES["plafond_nuage"] = 5
fournisseurs.aiohttp.ClientSession = SessionQuiRefuse
_b = asyncio.new_event_loop()
try:
    _b.run_until_complete(
        serveur._appeler_llm("un chat roux", None, None, False, None, 0.4,
                             "banc-tid"))
except Exception:                                            # noqa: BLE001
    pass
finally:
    _b.close()
    fournisseurs.aiohttp.ClientSession = vraie_session
verifier("un appel qui echoue rend sa place : une panne de fournisseur ne "
         "ferme pas le robinet du mois",
         not serveur._EN_VOL_NUAGE
         and serveur.appels_du_mois("rafale") == 0,
         f"{serveur._EN_VOL_NUAGE}, "
         f"{serveur.appels_du_mois('rafale')} consignes")
serveur.PREFERENCES["plafond_nuage"] = 0


print()
print("=" * 70)
print("11. l'extinction ne mange pas la fin du journal")
print("=" * 70)

# Le fil d'ecriture est un demon : sans vidange, l'arret emportait tout ce qui
# restait en file. Mesure avant correction, disque a 50 ms la ligne : trente-neuf
# lignes sur quarante perdues, sans un mot — et un compte plafonne se remboursait
# ses appels en redemarrant le studio.
serveur.COMPTEUR.clear()
_vrai_tailler = serveur._tailler
serveur._tailler = lambda: time.sleep(0.01)
_avant = sum(1 for l in io.open(serveur.FICHIER_COUTS, encoding="utf-8")
             if l.strip())
for _ in range(40):
    serveur.consigner_appel_distant("anthropic", "llm", "extinction", 1.0,
                                    octets=5, jetons=(1, 1))
_en_file = serveur._A_ECRIRE.qsize()


async def eteindre():
    await serveur.arreter_file({})


_b = asyncio.new_event_loop()
_b.run_until_complete(eteindre())
_b.close()
serveur._tailler = _vrai_tailler
serveur.ARRET = False
_apres = sum(1 for l in io.open(serveur.FICHIER_COUTS, encoding="utf-8")
             if l.strip())
verifier("les quarante dernieres lignes survivent a l'arret du studio",
         _apres - _avant == 40 and serveur._A_ECRIRE.qsize() == 0,
         f"{_en_file} en file au moment de l'arret, {_apres - _avant} ecrites")
verifier("un compte ne se rembourse plus ses appels en redemarrant",
         serveur.appels_du_mois("extinction") == 40,
         f"{serveur.appels_du_mois('extinction')} appels comptes")
verifier("vider_journal rend zero quand il ne reste rien",
         serveur.vider_journal() == 0)


print()
print("=" * 70)
print("12. en STUDIO_AUTH=libre, le plafond dit ce qu'il ne protege pas")
print("=" * 70)

# LE REPROCHE ETAIT « tout le monde tombe dans le meme seau anonyme ». Mesure :
# faux. Le seau par navigateur existe deja ; ce qu'il ne fait pas, c'est
# proteger, parce que le cookie appartient au visiteur.
_seaux = {serveur.dossier_utilisateur(p) for p in ("a" * 32, "b" * 32, "c" * 32)}
verifier("trois navigateurs, trois seaux — et non un seul « anonyme »",
         len(_seaux) == 3 and "anonyme" not in _seaux,
         ", ".join(sorted(x[:8] for x in _seaux)))
verifier("« anonyme » n'est que le seau d'un pid absent",
         serveur.dossier_utilisateur(None) == "anonyme")

_vrai_auth = serveur.AUTH
serveur.AUTH = "libre"
serveur.PREFERENCES["plafond_nuage"] = 0
verifier("sans plafond, rien a avertir : le studio se tait",
         serveur.avertissement_plafond() == "")
serveur.PREFERENCES["plafond_nuage"] = 10
_mot = serveur.avertissement_plafond()
verifier("avec un plafond, il dit que vider ses cookies remet a zero",
         "navigateur" in _mot and "cookies" in _mot, _mot[:70])
serveur.AUTH = "obligatoire"
verifier("avec des comptes, plus d'avertissement : le seau tient",
         serveur.avertissement_plafond() == "")
serveur.AUTH = _vrai_auth
serveur.PREFERENCES["plafond_nuage"] = 0


# ── 12. la vidange COMPTE-T-ELLE la ligne que le fil tient deja ? ────────
# qsize() ne compte pas l'element deja SORTI de la file. Le cas qui fait mal
# est celui a une seule ligne : un appel consigne a l'instant de l'arret, le fil
# l'a prise, qsize() vaut zero — et l'arret n'imprime rien pendant que la ligne
# est perdue. C'est exactement le silence que vider_journal existe pour rompre.
_bloque = threading.Event()
_vrai_tailler = serveur._tailler
serveur._tailler = lambda: _bloque.wait(30)      # le disque ne repond plus
serveur._A_ECRIRE.put({"mois": serveur._mois(), "compte": "essai",
                       "fournisseur": "x", "modalite": "llm"})
if serveur._ECRIVAIN is None:
    serveur._ECRIVAIN = threading.Thread(target=serveur._fil_ecriture,
                                         daemon=True, name="couts-nuage")
    serveur._ECRIVAIN.start()
time.sleep(0.3)                                   # le fil a pris la ligne
verifier("une ligne prise par le fil n'est plus dans la file",
         serveur._A_ECRIRE.qsize() == 0)
verifier("mais la vidange la compte quand meme",
         serveur.vider_journal(0.2) == 1, str(serveur.vider_journal(0.2)))
_bloque.set()
serveur._tailler = _vrai_tailler
time.sleep(0.3)
verifier("et une fois le disque revenu, il ne reste rien",
         serveur.vider_journal(2) == 0)

# ── 13. une ecriture coupee en plein UTF-8 ──────────────────────────────
# UnicodeDecodeError descend de ValueError, pas d'OSError : ni le filet de la
# ligne ni celui du fichier ne l'attrapaient. La docstring promettait de sauter
# une ligne illisible ; le studio refusait de demarrer.
SAUT = chr(10).encode()
with open(serveur.FICHIER_COUTS, "ab") as f:
    f.write(json.dumps({"mois": serveur._mois(), "compte": "entier",
                        "fournisseur": "x", "modalite": "llm",
                        "appels": 1}).encode() + SAUT)
    f.write(b'{"compte": "cou')                   # coupee au milieu d'un accent
    f.write("é".encode()[:1] + SAUT)
_leve = None
try:
    serveur.charger_compteur()
except Exception as e:                            # noqa: BLE001
    _leve = e
verifier("une ligne coupee en plein UTF-8 ne fait pas tomber le demarrage",
         _leve is None, type(_leve).__name__ if _leve else "")
verifier("et la ligne entiere qui la precede est bien comptee",
         serveur.appels_du_mois("entier") == 1,
         str(serveur.appels_du_mois("entier")))


shutil.rmtree(DONNEES, ignore_errors=True)

print()
print("=" * 70)
print(f"  {len(VERTS)} verifications passees, {len(ROUGES)} echouees")
for r in ROUGES:
    print("  RATE : " + r)
print("=" * 70, flush=True)
sys.exit(1 if ROUGES else 0)
