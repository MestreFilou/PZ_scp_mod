# Modèles 3D et textures (à remplacer)

Les tenues utilisent pour l'instant des **modèles vanilla** avec des **textures temporaires**.

| Objet | Modèle provisoire (clothingItems/*.xml) | Texture provisoire |
|---|---|---|
| Combinaison Classe-D | `skinned\clothes\Boilersuit` | `media/textures/SCP/SCP_ClassD_Jumpsuit.png` |
| Casque NTF | `skinned\clothes\Hat_Army` | `media/textures/SCP/SCP_MTF_Helmet.png` |
| Gilet NTF | `skinned\clothes\Vest_BulletArmy` | `media/textures/SCP/SCP_MTF_Vest.png` |
| Uniforme NTF | `skinned\clothes\Boilersuit` | `media/textures/SCP/SCP_MTF_Uniform.png` |
| Combinaison NRBC | `skinned\clothes\HazmatSuit` | `media/textures/SCP/SCP_Hazmat_Suit.png` |
| Masque à gaz | `skinned\clothes\Hat_GasMask` | `media/textures/SCP/SCP_GasMask.png` |
| SCP-035 | `skinned\clothes\Hat_HockeyMask` | `media/textures/SCP/SCP_035_Mask.png` |
| SCP-173 / 096 / 106 | `skinned\clothes\Boilersuit` | `media/textures/SCP/SCP_173_Shell.png` etc. |

Pour remplacer : déposer le modèle `.fbx`/`.x` ici (par ex. `models_X/Skinned/Clothes/SCP_MTF_Helmet.fbx`),
puis changer `m_MaleModel` / `m_FemaleModel` dans le XML correspondant de `media/clothing/clothingItems/`.

Déjà remplacés (images Gemini) : icônes `media/textures/Item_SCP_*.png`, `poster.png`, `icon.png`, `preview.png`.
Planches de concept pour les futurs modèles 3D : `art/concepts/` à la racine du dépôt (hors du mod).

Encore temporaires :
- Sons : `media/sound/*.ogg` (bips et bruits générés)
- Tuiles de corrosion / dimension de poche : constantes en haut de `media/lua/shared/SCP_106_Logic.lua`
