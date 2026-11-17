# Outils

Scripts Python qui fabriquent une partie du mod. Ils se lancent depuis la racine du dépôt
(`python3 tools/<script>.py`) et n'ont besoin que de **Pillow** et **numpy**
(plus **ffmpeg** pour les sons). Chaque fichier qu'ils écrivent est à commiter avec eux.

| Script | Ce qu'il fabrique | Fichiers écrits |
|---|---|---|
| `make_site_layout.py` | Le plan du site (niveaux, salles, portes, mobilier, butin, extérieur) | `media/lua/shared/SCP_Facility_Data.lua`, `art/renders/site_plan.png` |
| `make_facility_tiles.py` | Les tuiles du site (murs, sols, portes et leurs images d'ouverture, meubles, extérieur) | `media/texturepacks/scp_facility.pack`, `media/scp_facility.tiles`, `art/tilesheets/scp_facility_02_tilesheet.png` |
| `make_site_preview.py` | Les aperçus isométriques du site avec les vraies tuiles | `art/renders/preview_*.png` |
| `make_item_icons.py` | Les icônes des petites anomalies (SCP-207, 268, 330…) | `media/textures/Item_SCP_*.png` |
| `make_weapon_models.py` | Les modèles 3D, textures et icônes des armes de la Fondation (`preview` : rendus en plus) | `media/models_X/static/weapons/*.x`, `media/textures/weapons/*.png`, `media/textures/Item_SCP_*.png`, `art/renders/weapons/` |
| `make_site_cells.py` | Les cellules de carte du site (forêt, clairière, route d'accès) et la région de départ « Site SCP » | `media/maps/SCP Site/*`, `media/lua/shared/SCP_SiteLocation.lua`, `art/renders/site_cells.png` |
| `make_weapon_sounds.py` | Les sons de la masse à choc (synthétisés) | `media/sound/SCP_ShockMaul_*.ogg` |

(`media/` = `Contents/mods/SCPFoundation/42/media/`.)

Ordre après un changement du plan : `make_site_layout.py`, puis `make_site_preview.py` pour les aperçus.
Après un changement de tuiles : `make_facility_tiles.py` (et `make_site_layout.py` si de nouvelles
tuiles sont utilisées dans le plan).

Les rendus de travail vont dans `tools/out/`, qui n'est pas suivi par git.
