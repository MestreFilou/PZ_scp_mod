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
- [x] Extérieur refait d'après l'image de Lucas : route d'accès depuis la ville, enceinte en béton de 2 étages avec barbelés, grande porte, cour d'entrée, poste de garde, tour de guet (3 volées d'escaliers, cabine vitrée), porte intérieure, cours du garage / centrale / bâtiment de la Porte A, toits avec panneaux solaires et ventilations (rendu : `art/rendu_exterieur_site.png`)
- [x] Ascenseur de la Porte A : cabine dans un puits, descente visible niveau par niveau (option `LiftRide`, désactivable : retour au fondu)
- [ ] Vérifier en jeu : la descente de l'ascenseur (pas de chute ni de dégâts, le sol du haut revient), les escaliers de la tour (tuiles d'escalier du mod, sinon escaliers en bois du jeu), les murets du toit qu'on peut enjamber
- [ ] Vraies fenêtres (ouvrables, cassables) dans la tour et le bâtiment : aujourd'hui ce sont des murs avec une bande vitrée dessinée
- Plan et aperçus : `art/site_plan.png`, `art/preview_*.png`. Pour modifier le plan : `tools/make_site_layout.py`, puis `tools/make_site_preview.py`.
- Note : un site construit avec l'ancienne version reste en place avec ses anciennes tuiles mais n'est plus géré ; il faut une nouvelle partie (ou construire le nouveau site ailleurs).

## Règles
- Sons et assets : uniquement sous licence libre (CC0 / CC-BY / CC-BY-SA, ex. Containment Breach) avec crédits.
- Rien de SCP: Secret Laboratory ni d'autres jeux propriétaires (inspiration seulement).
