La préparation s’exécute sur un runner Windows standard de GitHub Actions dans le dépôt public. Aucun service de traduction payant, clé de joueur, mot de passe ou facturation n’est utilisé. Les modèles restent sur la machine de préparation ; le Codex distribue les résultats.

Le workflow vérifie les dépôts officiels à 05 h 15 UTC, ainsi que sur demande. Il conserve les traductions dont le texte source n’a pas changé, traduit les nouveautés et vérifie les identifiants, variables, liens, coordonnées, parcours et ressources binaires. Les outils de Pathing réappliquent notre adaptation aux sources officielles correspondant à la version publiée et lancent les tests avant publication.

Les recettes actuellement prises en charge sont Pathing, Tekkit All-In-One, Lady Elyssa Guides, Lady Elyssa Succès et Collections et Teh’s Trails. Les descriptions du dépôt de modules et du dépôt de marqueurs sont traitées séparément et couvrent tout le catalogue. Les autres interfaces de modules ne sont pas déclarées traduites sans une recette compatible.

Un changement incompatible ou un XML éditeur ambigu laisse l’ancienne adaptation en ligne et inscrit la nouvelle version dans Pending. La Forge indique « traduction FR en préparation ». Elle n’installe pas une version d’origine à la place d’une adaptation française sans choix explicite.

La prépublication technique `forge-traductions` contient les catalogues et paquets. Elle n’est jamais marquée comme dernière version du Codex. Le manifeste est téléversé en dernier ; les nouveaux paquets portent des noms distincts et leur empreinte SHA-256 est vérifiée à l’installation.

Le dépôt français Blish HUD remplace uniquement l’adresse du dépôt dans settings.json et conserve une sauvegarde. Les téléchargements des modules gardent leurs sources et empreintes officielles, sauf Pathing qui pointe vers la version FR contrôlée. Les nouvelles versions originales de Pathing ne sont proposées dans ce dépôt qu’après préparation FR, afin de protéger l’adaptation installée. La version d’origine reste accessible dans la Forge.

Commandes de préparation :

    python test_traductions.py
    python actualiser.py
    python actualiser.py --publish

Le premier amorçage utilise `--seed --payload <Forge-Packs>`. Il doit être fait avec des paquets déjà construits et vérifiés. Le compte GitHub CLI doit disposer de repo pour publier les catalogues et de workflow pour installer ou modifier la tâche.

Les sources Pathing restent soumises à leur licence d’origine, jointe avec les outils. Les paquets conservent les licences et crédits des auteurs.
