# Le studio appelle avec keep_alive=0 (corps_ollama, garder=0 par defaut) :
# CHAQUE appel de production recharge donc le modele. On mesure les deux regimes.
import json, os, sys, time, urllib.request
import serveur
from serveur import corps_ollama, OLLAMA, SYS_TRADUCTION

def poster(corps, timeout=300):
    d = json.dumps(corps).encode()
    r = urllib.request.Request(OLLAMA + "/api/generate", data=d,
                               headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(r, timeout=timeout) as x:
        return json.load(x)

DEMANDE = "1. un vieux hibou perche sur une branche moussue"
for m in ["liquidai/lfm2.5-350m:latest", "digitsflow/bonsai-8b:latest", "qwen2.5vl:7b"]:
    for garder, nom in ((0, "keep_alive=0 (reglage actuel du studio)"),
                        ("10m", "keep_alive=10m (modele garde)")):
        ts = []
        for i in range(4):
            c = corps_ollama(DEMANDE, None, SYS_TRADUCTION, False, m, 0.1, garder)
            t0 = time.time()
            try:
                poster(c)
                ts.append(time.time() - t0)
            except Exception as e:
                ts.append(float("nan"))
        print("%-30s %-38s %s" % (m.split("/")[-1], nom,
              "  ".join("%.1fs" % t for t in ts)), flush=True)
