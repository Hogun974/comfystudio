# Le modèle de langage peut venir d'une autre machine

Le studio appelle un Ollama, dont l'adresse est un réglage. Sur une machine sans
carte, cet Ollama est ailleurs — et si cette machine-là s'éteint, plus
d'analyse.

**Le premier recours est d'en déclarer plusieurs.** `OLLAMA_URL` accepte une
liste d'adresses séparées par des virgules, et le studio parle à chacune en
direct : mesure du 31 août 2026, la même question coûte 3,8 s en direct contre 74,8 s
par l'agent d'une machine. Voir [Plusieurs Ollama](plusieurs-ollama.md). Ce qui
suit vaut pour les machines qui n'ont **pas** d'adresse joignable — c'est le cas
d'un agent derrière une box.

Chaque agent **annonce le modèle de langage qu'il porte**, et le studio bascule
dessus quand le sien ne répond plus. Il ne peut pas l'appeler directement — une
machine à agent n'a pas d'adresse — alors il **dépose la question** et l'agent
vient la chercher : exactement le chemin des rendus, et rien de plus à exposer.

Trois précautions, chacune pour une faute constatée :

- **un fil séparé dans l'agent.** Sa boucle de travail reste bloquée pendant un
  rendu, parfois plusieurs minutes : une question posée au milieu d'une vidéo
  aurait attendu la fin du rendu ;
- **on substitue un modèle que la machine porte vraiment.** Le studio ne connaît
  que le nom du sien ; le demander tel quel ferait échouer la bascule au moment
  précis où l'on en dépend ;
- **on n'essaie une autre machine que si la sienne ne répond pas.** Un modèle
  distant est plus lent à charger, et la machine qui le porte a peut-être mieux
  à faire.

Dans `/admin`, le pli d'une machine porte un bouton **« poser une question pour
vérifier »**. Une voie de secours qu'on n'essaie jamais n'en est pas une : on
découvre qu'elle est bouchée le jour où l'on en a besoin.
