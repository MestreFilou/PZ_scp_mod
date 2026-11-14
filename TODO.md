# TODO (demandes de Lucas, liste tenue à jour)

Légende : [x] fait (non testé en jeu sauf mention), [ ] à faire.

## Textures (priorité 1)
- [x] Nouveau tileset `scp_facility_02` : murs, sols, portes, panneaux par zone (EZ / LCZ / HCZ)
- [x] Portes de confinement lourdes pour les salles de niveau ≥ 3
- [x] Dimension de poche de SCP-106 : nouvelles tuiles (murs, sols, sorties) + éclairage d'ambiance
- [ ] Vérifier en jeu : le pack se charge, portes qui s'ouvrent/ferment, panneaux, éclairage
- [ ] Tuile de corrosion de SCP-106 (encore vanilla)
- [ ] Props restants : console du broyeur de fémur (réutilise la tuile de l'ogive)

## Comportement des SCP (priorité 2)
- [x] Retirer les bruits de zombies (gémissements, morsures, cris de douleur) des SCP, garder leurs propres sons
- [x] Démarche propre à chaque SCP avec les allures du jeu (096 traîne les pieds puis sprinte, 106 très lent, 049 et 049-2 lents, 173 ne mord plus)
- [ ] Vraies animations propres (173 raide, 096 bras ballants, 939 à quatre pattes) : il faut des clips d'animation faits dans Blender sur le squelette PZ + un AnimSet, à ajouter au brief Blender
- [ ] Pas de pas des SCP : bruits de pas encore ceux du jeu (173 devrait seulement racler)

## Site (plus tard, dans une autre discussion)
- [ ] Relier le site à la carte en surface par une grande porte / entrée
- [ ] Refaire le site entièrement
- [ ] Couloirs plus étroits, comme dans SCP – Containment Breach (« c'est étroit »)
- [ ] Étudier une extension de carte (map mod B42) entièrement dédiée au site, reliée au reste de Knox Country
- Note : le site déjà généré garde les anciennes tuiles ; il faut le reconstruire pour voir les nouvelles.

## Règles
- Sons et assets : uniquement sous licence libre (CC0 / CC-BY / CC-BY-SA, ex. Containment Breach) avec crédits.
- Rien de SCP: Secret Laboratory ni d'autres jeux propriétaires (inspiration seulement).
