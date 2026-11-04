# Contenu adulte

Le studio ne filtre pas. L'aiguilleur a pour consigne de transcrire fidèlement la
demande, sans édulcorer. Pony reçoit automatiquement sa balise `rating_explicit`
quand c'est pertinent — sans elle il s'autocensure.

Une seule limite est codée en dur : le contenu sexuel impliquant des mineurs est
refusé, avant l'aiguillage et après la réécriture du prompt.

Une demande venue d'un programme ([Piloter le studio par
programme](piloter-par-programme.md)) suit exactement les mêmes règles, et le
garde-fou y est passé **avant la file** : le programme reçoit un refus `422`
(`refus_mineurs`) au lieu d'un rendu en erreur découvert plus tard, et rien
n'est compté dans le plafond de sa clé.

Une règle s'ajoute dès qu'une clé d'API est posée : **une demande adulte ne sort
jamais de la machine**, ni vers un LLM distant, ni vers un générateur d'images
distant. Elle est appliquée dans le code, avant l'appel, et le journal de la
tâche l'annonce.
