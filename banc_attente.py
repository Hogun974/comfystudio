# -*- coding: utf-8 -*-
"""Une demande qui reclame une machine en pause est-elle gardee, ou perdue ?

    python banc_attente.py

Le studio refusait : « PC pourrait faire ce travail, mais elle est en pause
depuis plus de 30 minutes. » Le refus etait juste — faire patienter une
demi-heure pour une machine que personne ne compte rallumer, c'est perdre le
temps de quelqu'un poliment — mais il laissait la demande a retaper.

Ce que ce banc verifie, et rien d'autre :
  - la demande est GARDEE, pas refusee, et le message est une proposition ;
  - elle n'immobilise AUCUN des trois travailleurs ;
  - le retour de la machine la relance toute seule, une fois et une seule ;
  - elle expire, et l'expiration se DIT ;
  - l'utilisateur peut la retirer a tout moment, et le retrait tient.

Aucune carte, aucun ComfyUI, aucun rendu : le parc est celui du 31 aout — pc
(RTX 2080 Ti, 11 Go) et zima (GTX 1060, 5,9 Go) — pose en memoire.
"""
import asyncio
import json
import os
import sys
import tempfile
import time

os.environ["STUDIO_DONNEES"] = tempfile.mkdtemp(prefix="banc_attente_")
os.environ["STUDIO_AUTH"] = "libre"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import serveur as S  # noqa: E402

ok, rate = [], []


def dit(vrai, quoi, detail=""):
    (ok if vrai else rate).append(quoi)
    print(f"  {'ok ' if vrai else 'NON'}  {quoi}{' — ' + detail if detail else ''}")


# Un moteur que les DEUX cartes tiennent : ce qui decide dans ce banc, c'est la
# pause, jamais la taille de la carte. Le plus petit du catalogue.
CLE = min(S.CATALOGUE, key=lambda c: S.CATALOGUE[c].get("vram", 0))
PID = "u" * 32


def poser(pause_pc=None, pause_zima=None, zima_equipee=False):
    """Le parc, et l'inventaire de chaque machine.

    « zima_equipee » decide s'il existe un recours : sans elle, pc en pause est
    la seule machine capable, et c'est exactement la situation qui produisait le
    refus. Avec elle, patienter_pause n'a rien a proposer et rend la main.
    """
    S.REGISTRE.clear()
    S.ETAT_NOEUDS.clear()
    S.MODELES_NOEUD.clear()
    S.VERROUS_NOEUD.clear()
    S.ARMEES.clear()
    S.EN_FILE.clear()
    S.EN_VOL.clear()
    del S.ATTENTE[:]
    S.TACHES.clear()
    S.CONVERSATIONS.clear()
    for ident, titre, vram, ram, pause in (
            ("pc", "PC (RTX 2080 Ti)", 11.0, 63.8, pause_pc),
            ("zima", "NAS ZimaOS", 5.9, 23.4, pause_zima)):
        S.REGISTRE[ident] = {"id": ident, "titre": titre, "agent": True,
                             "jeton": ident, "pause": pause}
        S.ETAT_NOEUDS[ident] = {"repond": True, "vram": vram, "ram": ram,
                                "vu": time.time()}
    dossiers = {}
    for sous, nom, _repo, _distant in S.CATALOGUE[CLE]["fichiers"]:
        dossiers.setdefault(sous, set()).add(nom)
    S.MODELES_NOEUD["pc"] = {"quand": time.time(), "dossiers": dossiers}
    if zima_equipee:
        S.MODELES_NOEUD["zima"] = {"quand": time.time(), "dossiers": dossiers}


def demande(texte="un chat en costume"):
    """Une demande en file, comme api_generer la pose : tache, tour, EN_FILE."""
    tid = os.urandom(8).hex()
    conv = S.CONVERSATIONS.get("c1")
    if conv is None:
        conv = S._vide(proprietaire=PID)
        conv["id"] = "c1"
        S.CONVERSATIONS["c1"] = conv
    S.TACHES[tid] = {"etapes": [], "etat": "en cours", "demande": texte,
                     "conversation": "c1", "proprietaire": PID, "image": None}
    S.enregistrer_tour(conv, tid, texte, {}, None, None, [], "en cours")
    S.EN_FILE[tid] = {"tid": tid, "texte": texte, "conversation": "c1",
                      "proprietaire": PID, "image": None, "modele": None,
                      "taille": None, "priorite": "", "noeud": None}
    return tid


def tour_de(tid):
    return next((t for t in S.CONVERSATIONS["c1"]["tours"] if t["id"] == tid), {})


def dernier_mot(tid):
    e = (S.TACHES.get(tid) or {}).get("etapes") or []
    return e[-1]["msg"] if e else ""


class Req(dict):
    """Le minimum qu'attendent qui(), est_admin() et les gestionnaires."""

    def __init__(self, pid=PID, match=None, corps=None):
        super().__init__(pid=pid, compte="")
        self.match_info = match or {}
        self.headers, self.cookies = {}, {}
        self._corps = corps

    async def json(self):
        if self._corps is None:
            raise ValueError("pas de corps")
        return self._corps


def lire(rep):
    return rep.status, json.loads(rep.text)


def _vider_file():
    """La file, videe entre deux cas. Un travail oublie fausse le cas suivant."""
    while not S.FILE_ATTENTE.empty():
        S.FILE_ATTENTE.get_nowait()
        S.FILE_ATTENTE.task_done()


async def main():
    print(f"\n  moteur du banc : {CLE} ({S.CATALOGUE[CLE].get('vram', 0)} Go)\n")
    S.FILE_ATTENTE = asyncio.Queue()
    S.ARRET = False
    S.PREFERENCES["pause_propose"] = 30
    S.PREFERENCES["armee_heures"] = 12

    # ── 1. le refus est devenu une proposition ──────────────────────────
    poser(pause_pc=time.time() - 40 * 60)
    tid = demande()
    try:
        await S.patienter_pause(CLE, tid)
        leve = None
    except S.MachineEnPause as e:
        leve = e
    except Exception as e:                                  # noqa: BLE001
        leve = e
    dit(isinstance(leve, S.MachineEnPause),
        "une pause de 40 min leve MachineEnPause, pas une erreur",
        type(leve).__name__)
    dit(isinstance(leve, S.MachineEnPause) and not isinstance(leve, RuntimeError),
        "elle ne passe PAS par RuntimeError — soumettre_robuste ne doit pas "
        "la prendre pour une panne de machine")
    dit(leve.noeuds == ["pc"], "elle nomme la machine a attendre", str(leve.noeuds))

    # ── 2. armer garde la demande, et le dit comme une proposition ──────
    dit(S.armer(tid, leve) is True, "la demande est armee")
    dit(tid in S.ARMEES and tid in S.EN_FILE,
        "elle reste dans EN_FILE — donc dans _file.json, donc dans le reveil")
    msg = dernier_mot(tid)
    dit("gardee en attente" in msg and "partira toute seule" in msg,
        "le message propose au lieu de refuser", msg[:90])
    dit("Reactive-la dans /admin" not in msg,
        "il n'ordonne plus d'aller rallumer la machine")
    dit("Retire-la de la file" in msg, "et il rappelle le recours")
    dit(tour_de(tid).get("etat") == "en cours",
        "le tour reste « en cours » : la demande n'a pas echoue",
        str(tour_de(tid).get("etat")))
    dit((S.TACHES[tid].get("etat") or "en cours") != "erreur",
        "la tache non plus")

    # ── 3. l'echeance se compte depuis la PREMIERE mise de cote ─────────
    jusqua = S.ARMEES[tid]["jusqua"]
    S.ARMEES.pop(tid)
    S.armer(tid, leve)                     # rearmee une seconde fois
    dit(abs(S.ARMEES[tid]["jusqua"] - jusqua) < 0.001,
        "une machine qui flotte entre pause et travail ne repousse pas "
        "l'echeance", f"{S.ARMEES[tid]['jusqua'] - jusqua:+.3f} s")

    # ── 4. reglage a zero : on retrouve le refus d'avant, tel quel ──────
    S.PREFERENCES["armee_heures"] = 0
    tid0 = demande("sans attente")
    dit(S.armer(tid0, leve) is False, "a zero heure, rien n'est arme")
    dit("est en pause depuis plus de 30 minutes" in leve.refus
        and "Reactive-la dans /admin" in leve.refus,
        "et le message d'avant est encore la, mot pour mot", leve.refus[:70])
    S.PREFERENCES["armee_heures"] = 12

    # ── 5. le reveil ────────────────────────────────────────────────────
    poser(pause_pc=time.time() - 40 * 60)
    tid = demande()
    S.armer(tid, S.MachineEnPause(CLE, [S.noeud("pc")]))
    S.ARMEES[tid]["quand"] -= 60            # le plancher de 15 s est passe
    dit(await S.reveiller_armees("pc") == 0,
        "machine toujours en pause : rien ne repart")
    dit(await S.reveiller_armees("zima") == 0,
        "et le battement d'une AUTRE machine ne la concerne pas")

    S.REGISTRE["pc"]["pause"] = None        # ce que fait api_admin_pause
    partis = await S.reveiller_armees("pc")
    dit(partis == 1, "la machine revient : la demande repart toute seule")
    dit(tid not in S.ARMEES and tid in S.ATTENTE and tid in S.EN_FILE,
        "elle quitte l'attente et reprend une place dans la file")
    dit(S.FILE_ATTENTE.qsize() == 1, "un travail, et un seul, dans la file",
        str(S.FILE_ATTENTE.qsize()))
    job = S.FILE_ATTENTE.get_nowait(); S.FILE_ATTENTE.task_done()
    dit(job["tid"] == tid and job["texte"] == "un chat en costume"
        and job["conv"]["id"] == "c1",
        "avec ce qu'elle portait : son texte et sa conversation")
    dit("est revenue" in dernier_mot(tid), "et l'utilisateur le lit",
        dernier_mot(tid)[:70])

    # ── 6. deux reveils dans la meme seconde, un seul depart ────────────
    # La fin de pause et le battement de la machine arrivent ensemble : sans le
    # desarmement pose AVANT le premier await, la demande partait deux fois —
    # donc deux images pour une demande.
    poser(pause_pc=time.time() - 40 * 60)
    tid = demande()
    S.armer(tid, S.MachineEnPause(CLE, [S.noeud("pc")]))
    S.ARMEES[tid]["quand"] -= 60
    S.REGISTRE["pc"]["pause"] = None
    deux = await asyncio.gather(S.reveiller_armees("pc"), S.reveiller_armees())
    dit(sum(deux) == 1 and S.FILE_ATTENTE.qsize() == 1,
        "deux reveils simultanes ne mettent la demande qu'une fois en file",
        f"{deux}, {S.FILE_ATTENTE.qsize()} en file")
    S.FILE_ATTENTE.get_nowait(); S.FILE_ATTENTE.task_done()

    # ── 7. le plancher anti-va-et-vient ─────────────────────────────────
    poser(pause_pc=time.time() - 40 * 60)
    tid = demande()
    S.armer(tid, S.MachineEnPause(CLE, [S.noeud("pc")]))
    S.REGISTRE["pc"]["pause"] = None
    dit(await S.reveiller_armees("pc") == 0,
        "armee il y a une seconde : on ne la relance pas tout de suite — "
        "chaque relance coute une analyse complete")

    # ── 8. l'expiration se dit ──────────────────────────────────────────
    poser(pause_pc=time.time() - 40 * 60)
    tid = demande()
    S.armer(tid, S.MachineEnPause(CLE, [S.noeud("pc")]))
    await S.expirer_armees()
    dit(tid in S.ARMEES, "avant l'echeance, rien ne bouge")
    S.ARMEES[tid]["jusqua"] = time.time() - 1
    S.ARMEES[tid]["depuis"] = time.time() - 12 * 3600
    await S.expirer_armees()
    dit(tid not in S.ARMEES and tid not in S.EN_FILE,
        "a l'echeance, la demande est relachee des deux registres")
    dit(S.TACHES[tid]["etat"] == "erreur" and tour_de(tid).get("etat") == "erreur",
        "et le tour porte enfin une fin — pas un « en cours » eternel")
    dit("n'est pas revenue en 12 h" in (tour_de(tid).get("erreur") or ""),
        "qui dit ce qui s'est passe", (tour_de(tid).get("erreur") or "")[:80])

    # ── 9. le panneau de file la montre ─────────────────────────────────
    poser(pause_pc=time.time() - 40 * 60)
    tid = demande()
    S.armer(tid, S.MachineEnPause(CLE, [S.noeud("pc")]))
    _, d = lire(await S.api_file(Req()))
    ligne = next((l for l in d["lignes"] if l["tid"] == tid), None)
    dit(ligne is not None, "la demande armee apparait dans la file")
    dit(ligne and ligne["etat"] == "attente machine",
        "avec son propre etat, distinct de « en attente »",
        ligne and ligne["etat"])
    dit(ligne and ligne.get("armee") and ligne.get("reste_h", 0) > 11,
        "et le temps qu'il lui reste", f"{(ligne or {}).get('reste_h', 0):.1f} h")
    dit(ligne and ligne["annulable"], "elle est annulable")
    dit(d["a_moi"] == 1 and d["armees"] == 1 and d["en_attente"] == 0,
        "le compteur de l'en-tete ne la perd pas : une file vide avec une "
        "demande armee n'est pas une file vide",
        f"a_moi={d['a_moi']} armees={d['armees']} en_attente={d['en_attente']}")

    # ── 10. l'utilisateur peut la retirer, et le retrait tient ──────────
    st, d = lire(await S.api_file_annuler(Req(match={"tid": tid})))
    dit(st == 200 and d.get("quoi") == "retiree",
        "le retrait repond « retiree » — et non « deja terminee », qui etait "
        "la reponse d'avant faute de connaitre cet etat", f"{st} {d}")
    dit(tid not in S.ARMEES and tid not in S.EN_FILE,
        "la demande a quitte l'attente et le fichier")
    S.REGISTRE["pc"]["pause"] = None
    dit(await S.reveiller_armees("pc") == 0 and S.FILE_ATTENTE.qsize() == 0,
        "et le retour de la machine ne la ressuscite pas")
    dit(tour_de(tid).get("etat") == "erreur", "le tour est clos")

    # ── 11. un autre a qui personne n'a rien demande ────────────────────
    poser(pause_pc=time.time() - 40 * 60)
    tid = demande()
    S.armer(tid, S.MachineEnPause(CLE, [S.noeud("pc")]))
    st, d = lire(await S.api_file_annuler(Req(pid="v" * 32, match={"tid": tid})))
    dit(st == 404 and tid in S.ARMEES,
        "un voisin ne retire pas la demande d'un autre", str(st))
    _, d = lire(await S.api_file(Req(pid="v" * 32)))
    ligne = next((l for l in d["lignes"] if l["tid"] == tid), None)
    dit(ligne and ligne["demande"] == "demande d'un autre utilisateur",
        "et n'en lit pas le texte")

    # ── 12. une machine libre existe : rien n'est arme ──────────────────
    # La proposition ne doit pas remplacer un travail qui pouvait partir. Le
    # 31 aout, le studio accusait deja le PC en pause pendant que le NAS avait
    # le moteur demande et travaillait.
    poser(pause_pc=time.time() - 40 * 60, zima_equipee=True)
    tid = demande()
    cible = S.choisir_noeud(CLE)
    dit(cible is not None and cible["id"] == "zima",
        "une autre machine capable est choisie sans passer par l'attente",
        str(cible and cible["id"]))

    # ── 13. LES TROIS TRAVAILLEURS NE RESTENT PAS PLANTES LA ────────────
    # Le point qui decide de tout : mettre une demande de cote ne doit pas
    # couter un travailleur. Il y en a trois ; cinq demandes qui attendent une
    # machine eteinte les auraient tous immobilises, et le studio entier avec.
    poser(pause_pc=time.time() - 40 * 60)
    S.FILE_ATTENTE = asyncio.Queue()
    vrai_executer = S.executer

    async def faux_executer(tid_, *a, **k):
        await asyncio.sleep(0)
        raise S.MachineEnPause(CLE, [S.noeud("pc")])

    S.executer = faux_executer
    tids = [demande(f"demande {i}") for i in range(5)]
    for t in tids:
        S.ATTENTE.append(t)
        r = S.EN_FILE[t]
        await S.FILE_ATTENTE.put({"tid": t, "texte": r["texte"],
                                  "conv": S.CONVERSATIONS["c1"], "image": None,
                                  "modele": None, "taille": None, "priorite": "",
                                  "noeud": None, "plan": None})
    equipe = [asyncio.create_task(S.travailleur()) for _ in range(S.TRAVAILLEURS)]
    try:
        await asyncio.wait_for(S.FILE_ATTENTE.join(), 10)
        vide = True
    except asyncio.TimeoutError:
        vide = False
    dit(vide, f"{S.TRAVAILLEURS} travailleurs digerent 5 demandes qui attendent "
              f"une machine eteinte, sans se bloquer")
    dit(all(t in S.ARMEES for t in tids) and len(S.ARMEES) == 5,
        "les cinq sont armees", f"{len(S.ARMEES)}/5")
    dit(all(t in S.EN_FILE for t in tids),
        "les cinq survivraient a un redemarrage — elles sont dans _file.json")
    dit(not S.EN_VOL, "aucune ne tient un travailleur", str(list(S.EN_VOL)))
    dit(all(tour_de(t).get("etat") == "en cours" for t in tids),
        "et aucune n'a ete ecrite en echec")

    # Le meme parc, une machine qui revient : la file repart d'elle-meme.
    S.executer = vrai_executer
    for t in tids:
        S.ARMEES[t]["quand"] -= 60
    S.REGISTRE["pc"]["pause"] = None
    partis = await S.reveiller_armees("pc")
    dit(partis == 5 and S.FILE_ATTENTE.qsize() == 5,
        "et les cinq repartent au retour de la machine", f"{partis} relancees")
    for t in equipe:
        t.cancel()
    await asyncio.gather(*equipe, return_exceptions=True)

    # ── 14. le fichier de file porte bien les armees ────────────────────
    poser(pause_pc=time.time() - 40 * 60)
    tid = demande()
    S.armer(tid, S.MachineEnPause(CLE, [S.noeud("pc")]))
    S.sauver_file()
    with open(S.FICHIER_FILE, encoding="utf-8") as f:
        sur_disque = json.load(f)
    dit(any(r.get("tid") == tid for r in sur_disque),
        "une demande armee est ecrite dans _file.json", f"{len(sur_disque)} ligne(s)")
    dit(any(isinstance(r.get("arme_depuis"), (int, float)) for r in sur_disque),
        "avec l'heure de sa mise de cote — un redemarrage ne remet pas "
        "l'echeance a zero")

    # ── 15. le reglage se pose, et l'ancien champ n'a pas casse ────────
    # La validation portait UN seul reglage et exigeait sa presence. En passer
    # a deux facultatifs est exactement le genre de changement qui casse le
    # champ d'a cote sans qu'on s'en apercoive.
    S.ADMIN_JETON = "jeton-de-banc"
    req = Req(corps={"armee_heures": 6})
    req.headers["X-Admin"] = S.ADMIN_JETON
    req.method = "POST"
    st, d = lire(await S.api_admin_reglages(req))
    dit(st == 200 and S.PREFERENCES["armee_heures"] == 6,
        "le nouveau reglage se pose seul", f"{st} {d}")
    dit(S.PREFERENCES["pause_propose"] == 30,
        "sans toucher a celui de la pause", str(S.PREFERENCES["pause_propose"]))

    req = Req(corps={"pause_propose": 45})
    req.headers["X-Admin"] = S.ADMIN_JETON
    req.method = "POST"
    st, d = lire(await S.api_admin_reglages(req))
    dit(st == 200 and S.PREFERENCES["pause_propose"] == 45,
        "et l'ancien se pose toujours seul, comme le fait la page", f"{st} {d}")

    for corps, pourquoi in (({"armee_heures": 999}, "au-dela d'une semaine"),
                            ({"armee_heures": -1}, "negatif"),
                            ({"armee_heures": True}, "un booleen"),
                            ({"pause_propose": 5000}, "une pause de 3 jours"),
                            ({"couleur": "bleu"}, "un reglage inconnu")):
        req = Req(corps=corps)
        req.headers["X-Admin"] = S.ADMIN_JETON
        req.method = "POST"
        st, _ = lire(await S.api_admin_reglages(req))
        dit(st == 400, f"refuse : {pourquoi}", str(st))
    dit(S.PREFERENCES["armee_heures"] == 6 and S.PREFERENCES["pause_propose"] == 45,
        "et aucun refus n'a laisse de trace",
        str(dict(S.PREFERENCES)))

    # ── 14. le clic n'attend pas le plancher ────────────────────────────
    # Le plancher de 15 s protege d'une machine qui flotte entre pause et
    # travail. Un administrateur qui clique ne flotte pas — et api_admin_pause
    # annonçait « reveillees: 0 » pendant que les demandes repartaient au
    # battement suivant. Un chiffre faux est pire que pas de chiffre.
    S.PREFERENCES["armee_heures"] = 12
    poser(pause_pc=time.time() - 40 * 60)
    tid = demande()
    S.armer(tid, S.MachineEnPause(CLE, [S.noeud("pc")]))
    S.REGISTRE["pc"]["pause"] = None
    dit(await S.reveiller_armees("pc") == 0,
        "armee a l'instant : le battement la laisse dormir")
    dit(await S.reveiller_armees("pc", plancher=False) == 1,
        "le clic, lui, la reveille tout de suite")
    _vider_file()

    # ── 15. baisser le delai raccourcit ce qui attend DEJA ──────────────
    # « armee_heures » ne valait que pour les demandes a venir : l'echeance
    # etait figee a l'armement. L'administrateur croyait avoir coupe l'attente
    # et s'en allait.
    poser(pause_pc=time.time() - 40 * 60)
    tid = demande()
    S.armer(tid, S.MachineEnPause(CLE, [S.noeud("pc")]))
    S.EN_FILE[tid]["arme_depuis"] = S.ARMEES[tid]["depuis"] = time.time() - 2 * 3600
    avant = S.ARMEES[tid]["jusqua"]
    S.PREFERENCES["armee_heures"] = 1
    S.reviser_echeances()
    dit(S.ARMEES[tid]["jusqua"] < avant,
        "l'echeance recule avec le reglage",
        f"{(avant - S.ARMEES[tid]['jusqua']) / 3600:.0f} h de moins")
    dit(S.ARMEES[tid]["jusqua"] < time.time() and S.ARMEES[tid].get("raccourcie"),
        "elle est deja passee, et l'on sait POURQUOI")
    await S.expirer_armees()
    dit("raccourci" in (tour_de(tid).get("erreur") or ""),
        "la demande sort en disant que c'est /admin, pas la machine",
        (tour_de(tid).get("erreur") or "")[:80])

    # ── 16. et remonter le delai efface la marque ───────────────────────
    # Sans cet effacement, une demande expirant des heures plus tard pour la
    # VRAIE raison accusait encore un raccourcissement qui n'existait plus.
    poser(pause_pc=time.time() - 40 * 60)
    tid = demande()
    S.armer(tid, S.MachineEnPause(CLE, [S.noeud("pc")]))
    S.EN_FILE[tid]["arme_depuis"] = S.ARMEES[tid]["depuis"] = time.time() - 2 * 3600
    S.PREFERENCES["armee_heures"] = 1
    S.reviser_echeances()
    dit(S.ARMEES[tid].get("raccourcie"), "marquee une premiere fois")
    S.PREFERENCES["armee_heures"] = 12
    S.reviser_echeances()
    dit(not S.ARMEES[tid].get("raccourcie") and S.ARMEES[tid]["jusqua"] > time.time(),
        "on remonte le delai : la marque tombe avec elle")
    S.ARMEES[tid]["jusqua"] = time.time() - 1
    await S.expirer_armees()
    dit("n'est pas revenue" in (tour_de(tid).get("erreur") or ""),
        "et l'expiration accuse de nouveau la machine",
        (tour_de(tid).get("erreur") or "")[:80])

    S.PREFERENCES["armee_heures"] = 12
    S.sauver_reglages()
    S.PREFERENCES["armee_heures"] = 0
    S.charger_reglages()
    dit(S.PREFERENCES["armee_heures"] == 12,
        "le reglage survit a un redemarrage du studio",
        str(S.PREFERENCES["armee_heures"]))

    print(f"\n  {len(ok)} verifications passees, {len(rate)} echouees")
    for r in rate:
        print("    a regarder :", r)
    return 1 if rate else 0


# asyncio.get_event_loop() leve depuis Python 3.14 hors d'une boucle :
# le banc passait dans le conteneur et echouait sur la machine de
# celui qui l'ecrit.
sys.exit(asyncio.run(main()))
