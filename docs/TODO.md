# TODO (demandes de Lucas, liste tenue à jour)

Légende : [x] fait (non testé en jeu sauf mention), [ ] à faire.

## Textures (priorité 1)
- [x] Nouveau tileset `scp_facility_02` : murs, sols, portes, panneaux par zone (EZ / LCZ / HCZ)
- [x] Portes de confinement lourdes pour les salles de niveau ≥ 3
- [x] Dimension de poche de SCP-106 : tuiles faites avec la roche de la dimension de poche de Containment Breach, éclairage réparti (centre + sorties)
- [ ] Vérifier en jeu : le pack se charge, portes qui s'ouvrent/ferment, panneaux, éclairage
- [ ] Tuile de corrosion de SCP-106 (encore vanilla)
- [ ] Props restants : console du broyeur de fémur (réutilise la tuile de l'ogive)

## Comportement des SCP (priorité 2)
- [x] Retirer les bruits de zombies (gémissements, morsures, cris de douleur) des SCP, garder leurs propres sons
- [x] Démarche propre à chaque SCP avec les allures du jeu (096 traîne les pieds puis sprinte, 106 très lent, 049 et 049-2 lents, 173 ne mord plus)
- [ ] Vraies animations propres (173 raide, 096 bras ballants, 939 à quatre pattes) : il faut des clips d'animation faits dans Blender sur le squelette PZ + un AnimSet, à ajouter au brief Blender
- [ ] Pas de pas des SCP : bruits de pas encore ceux du jeu (173 devrait seulement racler)

## Site (refait, version 2 du plan)
- [x] Site refait entièrement : un seul niveau souterrain, trois zones en enfilade comme dans Containment Breach (confinement léger au nord, lourd au milieu, zone d'entrée au sud), 74 salles
- [x] Couloirs étroits : 2 cases de large (mesuré sur les salles de Containment Breach : environ 2 m)
- [x] Relié à la carte en surface : enceinte murée, grande porte de 4 cases, bâtiment de la Porte A, ascenseur vers le site
- [x] Tuiles faites à partir des textures de Containment Breach (CC BY-SA 3.0), mobilier, panneaux par salle
- [x] Extension de carte étudiée et écartée : sans les outils de mapping B42, les fichiers de carte ne peuvent être ni produits ni testés de façon fiable ; le site reste construit par le mod, à l'endroit choisi
- [ ] Vérifier en jeu (nouvelle partie) : construction complète, grande porte et Porte A (les 4 battants bougent ensemble), ascenseur, éclairage, portes à carte, mobilier qui bloque le passage
- [ ] Choisir un emplacement fixe dans Knox Country (au bord d'une route) et le mettre par défaut dans les options
- [ ] Vrais escaliers ou rampe entre la surface et le site (aujourd'hui : ascenseur)
- [x] Extérieur refait d'après l'image de Lucas : route d'accès depuis la ville, enceinte en béton de 2 étages avec barbelés, grande porte, cour d'entrée, poste de garde, tour de guet (3 volées d'escaliers, cabine vitrée), porte intérieure, cours du garage / centrale / bâtiment de la Porte A, toits avec panneaux solaires et ventilations (rendu : `art/renders/rendu_exterieur_site.png`)
- [x] Ascenseur de la Porte A : cabine dans un puits, descente visible niveau par niveau (option `LiftRide`, désactivable : retour au fondu)
- [ ] Vérifier en jeu : la descente de l'ascenseur (pas de chute ni de dégâts, le sol du haut revient), les escaliers de la tour (tuiles d'escalier du mod, sinon escaliers en bois du jeu), les murets du toit qu'on peut enjamber
- [ ] Vraies fenêtres (ouvrables, cassables) dans la tour et le bâtiment : aujourd'hui ce sont des murs avec une bande vitrée dessinée
- [x] Lot 2 (retours de Lucas) : mobilier plus varié (chaises, tables, canapés, distributeurs, plantes, lits superposés, lits médicaux, paillasses), grande chambre de SCP-106 (corniche, passerelle, plateforme centrale, fosse dont le fond est un niveau plus bas, escalier pour remonter, broyeur de fémur à côté), SCP-049 un niveau plus bas (escalier depuis la zone lourde : cellule, observation, morgue, bloc opératoire), Porte B (monte-charge 3x3 au bout est de la zone d'entrée vers un hangar hors de l'enceinte avec sa route). Version 4 du site. Aperçus : `art/renders/preview_106.png`, `preview_049.png`, `preview_gateb.png`
- [ ] Vérifier en jeu : tomber dans la fosse de 106 (dégâts d'un étage), l'escalier de la fosse et celui de 049 (niveau sous le site), le monte-charge de la Porte B
- [ ] Reste des retours : dimension de poche en labyrinthe avec sortie, 096 assis puis très rapide et mortel (bruit de démembrement), morsure de 939 (animation + son), site sur la carte de sélection
- [x] Mobilier du jeu (Project Zomboid) dans les salles : bureaux 2 cases avec ordinateur et fauteuil, classeurs, casiers, étagères, lits (simples, superposés, hôpital), tables de morgue, comptoirs, éviers, frigos, distributeurs, plantes, tableaux. Fouillables, avec un peu de contenu. Noms et orientations relevés dans les fichiers 42.22. Nos tuiles restent pour ce qui est propre à SCP (consoles, baies, photocopieuse, caisses). Les aperçus dessinent nos tuiles à la place.
- [x] Abords : bande de gravier, clôture grillagée avec barbelés, zone dégagée, lisière de forêt (arbres du jeu)
- [ ] Vérifier en jeu : meubles du jeu bien orientés, fouillables, lits utilisables ; arbres plantés autour
- [ ] Annonce d'introduction enregistrée par Lucas (haut-parleurs + sous-titres), à brancher quand le fichier arrive
- [x] Petites anomalies (wiki SCP, CC BY-SA) : SCP-207 (cola, courir sans fatigue mais le cœur souffre), 268 (casquette, ignoré 15 s), 330 (bonbons, le 3e coupe les mains), 005 (clé, ouvre tout), 109 (gourde infinie), 458 (pizza sans fin), 427 (médaillon, soigne puis mute), 018 (super balle). Clic droit dans l'inventaire. Rangées dans la salle de test, la cafétéria, le bureau du directeur, la salle des objets anormaux, le quartier des gardes ; aussi dans le kit admin.
- [x] Armes à feu du jeu (pistolets, fusils d'assaut, fusil à pompe, chargeurs, munitions) dans l'armurerie, les postes de sécurité, le quartier des gardes, le vestiaire FIM et les casiers militaires
- [ ] Vérifier en jeu : effets des anomalies (surtout 268 avec setGhostMode, 018 sur les zombies), icônes, noms des armes du jeu en 42.22
- Plan et aperçus : `art/renders/site_plan.png`, `art/renders/preview_*.png`. Pour modifier le plan : `tools/make_site_layout.py`, puis `tools/make_site_preview.py`.
- Note : un site construit avec l'ancienne version reste en place avec ses anciennes tuiles mais n'est plus géré ; il faut une nouvelle partie (ou construire le nouveau site ailleurs).

## Règles
- Sons et assets : uniquement sous licence libre (CC0 / CC-BY / CC-BY-SA, ex. Containment Breach) avec crédits.
- Rien de SCP: Secret Laboratory ni d'autres jeux propriétaires (inspiration seulement).
