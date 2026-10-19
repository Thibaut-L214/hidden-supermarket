# Mesures de performance — prototype rayon œufs

Budgets de référence : TECH.md §07 (60 fps visés, p95 < 25 ms, 30 fps stables sur matériel modeste). Ces chiffres sont des cibles, pas des garanties.

## Comment mesurer

- Lancer `pnpm dev`, ouvrir `http://localhost:5173/?perf`, ou appuyer sur la touche à gauche de `1` (`²` en AZERTY, `` ` `` en QWERTY).
- L'encart affiche : fps moyen et p95 du temps d'image (fenêtre glissante de 300 images), draw calls, triangles, géométries, textures, tas JS (Chrome uniquement), temps de chargement de chaque GLB.
- Mesurer sur la fenêtre visible et au premier plan : un onglet masqué ne produit pas d'images.

## Relevé du 2026-10-18, après les lots 1 à 4 (magasin, hangar et logistique, paysage, parvis) (Chrome, macOS, fenêtre 858 × 1072, devicePixelRatio 2)

Compteurs de rendu, relevés par image dans le navigateur intégré. Ils ne dépendent pas du matériel. Entre parenthèses, les valeurs de l'étape 6, avant l'enrichissement.

| Vue | Draw calls | Triangles |
| --- | ---: | ---: |
| Magasin, vue de départ (allée centrale) | 115 (54) | 135 656 (20 642) |
| Magasin, le long des gondoles | 61 (20) | 68 648 (8 484) |
| Magasin, vitrines réfrigérées | 43 | 52 760 |
| Terrasse, chaîne en cours, regard sur le hangar et le paysage | 130 (74) | 190 608 (13 146) |
| Parvis, vue vers l'extérieur | 20 (14) | 17 356 (2 772) |
| Parvis, face à la façade (intérieur visible derrière les vitrines) | 210 | 198 316 |

| Ressource | Export Blender | Optimisé (servi) | Transfert gzip | Chargement local |
| --- | ---: | ---: | ---: | ---: |
| `store.glb` | 12,5 Mo | 3,1 Mo | 829 Ko | 15 ms |
| `terrace_eggs.glb` | 7,1 Mo | 1,7 Mo | 609 Ko | 15 ms |

`store.glb` contient 187 000 triangles et 333 000 sommets (`node scripts/inspect-glb.mjs public/assets/store/store.glb`). Les marchandises représentent l'essentiel : gondole Boissons 35 000 triangles, chaque vitrine 15 000.

| Autre | Valeur |
| --- | --- |
| Tas JS après chargement | 48 Mo |
| Programmes de shaders | 8 |
| Bake d'occlusion à l'export | environ 3 s pour le magasin |

Le module de terrasse est préchargé dès que le joueur vise le rayon : les portes s'ouvrent sans attente réseau perceptible.

## Relevé du 2026-10-19, après post-processing (GTAO, bloom, SMAA), ciel et environnements

Compteurs par image, passes d'ombre et de post-processing comprises (GTAO redessine la scène une fois pour ses normales). Terrasse, regard sur le garde-corps et l'horizon : 499 draw calls, 674 000 triangles, 60 fps sur la machine de développement (plafonné par la synchronisation verticale, onglet au premier plan).

La qualité réduite (menu pause) coupe tout le post-processing : rendu direct, MSAA du canvas, pixel ratio 1, pas d'ombres. Cible de repli si les machines modestes ne tiennent pas 30 fps : garder le bloom et SMAA, couper GTAO (`POST_SETTINGS` dans `src/app/postprocessing.ts`).

## Non mesuré

- **fps et p95 réels** : la session de développement tournait dans un onglet en arrière-plan, sans `requestAnimationFrame`. À relever sur les machines cibles (Chrome, Firefox, Safari desktop) avec l'encart `?perf`, en parcourant magasin, terrasse pendant la chaîne et parvis.
- Matériel modeste et mobile : non testé (décision mobile reportée, TECH.md §07).

## Pistes si un budget est dépassé

- Qualité graphique réduite (menu pause) : pixel ratio 1, ombres du soleil coupées.
- Vue de la façade depuis le parvis : 210 appels de dessin, au-delà de la cible de 150, car tout l'intérieur du magasin reste dessiné derrière les vitrines (pas d'occlusion). Piste : vitrines plus opaques et intérieur masqué quand le joueur est sur le parvis.
- Marchandises : premier poste de triangles. Leviers suivants : moins de segments, rangées arrière omises, ou instanciation (`EXT_mesh_gpu_instancing`) au prix de l'occlusion bakée par objet.
- Les GLB passent par `scripts/optimize-glb.mjs` : dedup, prune (empties conservés), weld, reorder, compression meshopt par filtres. Pas de quantification : elle déplacerait des échelles dans les transforms de nœuds, dont dépendent pivots et contrat.
- Textures définitives en KTX2 : installer KTX-Software (`toktx`) ; le script signale les textures restées non compressées. Le runtime sait déjà les lire (`KTX2Loader`, transcodeur copié dans `public/basis/`).
- Ne pas basculer `renderer.shadowMap.autoUpdate` à la volée : avec three r186, les matériaux compilés ensuite perdent leurs uniforms de brouillard (scène noyée dans la brume).
