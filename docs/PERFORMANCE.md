# Mesures de performance — prototype rayon œufs

Budgets de référence : TECH.md §07 (60 fps visés, p95 < 25 ms, 30 fps stables sur matériel modeste). Ces chiffres sont des cibles, pas des garanties.

## Comment mesurer

- Lancer `pnpm dev`, ouvrir `http://localhost:5173/?perf`, ou appuyer sur la touche à gauche de `1` (`²` en AZERTY, `` ` `` en QWERTY).
- L'encart affiche : fps moyen et p95 du temps d'image (fenêtre glissante de 300 images), draw calls, triangles, géométries, textures, tas JS (Chrome uniquement), temps de chargement de chaque GLB.
- Mesurer sur la fenêtre visible et au premier plan : un onglet masqué ne produit pas d'images.

## Relevé du 2026-10-18, après le lot 1 « magasin détaillé » (Chrome, macOS, fenêtre 858 × 1072, devicePixelRatio 2)

Compteurs de rendu, relevés par image dans le navigateur intégré. Ils ne dépendent pas du matériel. Entre parenthèses, les valeurs de l'étape 6.

| Vue | Draw calls | Triangles |
| --- | ---: | ---: |
| Magasin, vue de départ (allée centrale) | 115 (54) | 135 656 (20 642) |
| Magasin, le long des gondoles | 61 (20) | 68 648 (8 484) |
| Magasin, vitrines réfrigérées | 43 | 52 760 |
| Terrasse, chaîne en cours (inchangée par le lot 1) | 74 | 13 146 |
| Parvis, vue vers l'extérieur | 20 (14) | 17 356 (2 772) |

| Ressource | Export Blender | Optimisé (servi) | Transfert gzip | Chargement local |
| --- | ---: | ---: | ---: | ---: |
| `store.glb` | 11,8 Mo | 2,9 Mo | 793 Ko | 15 ms |
| `terrace_eggs.glb` | 562 Ko | 204 Ko | 56 Ko | 15 ms |

`store.glb` contient 187 000 triangles et 333 000 sommets (`node scripts/inspect-glb.mjs public/assets/store/store.glb`). Les marchandises représentent l'essentiel : gondole Boissons 35 000 triangles, chaque vitrine 15 000.

| Autre | Valeur |
| --- | --- |
| Tas JS après chargement | 48 Mo |
| Programmes de shaders | 8 |
| Bake d'occlusion à l'export | environ 3 s pour le magasin |

Le module de terrasse est préchargé dès que le joueur vise le rayon : les portes s'ouvrent sans attente réseau perceptible.

## Non mesuré

- **fps et p95 réels** : la session de développement tournait dans un onglet en arrière-plan, sans `requestAnimationFrame`. À relever sur les machines cibles (Chrome, Firefox, Safari desktop) avec l'encart `?perf`, en parcourant magasin, terrasse pendant la chaîne et parvis.
- Matériel modeste et mobile : non testé (décision mobile reportée, TECH.md §07).

## Pistes si un budget est dépassé

- Qualité graphique réduite (menu pause) : pixel ratio 1, ombres du soleil coupées.
- Marchandises : premier poste de triangles. Leviers suivants : moins de segments, rangées arrière omises, ou instanciation (`EXT_mesh_gpu_instancing`) au prix de l'occlusion bakée par objet.
- Les GLB passent par `scripts/optimize-glb.mjs` : dedup, prune (empties conservés), weld, reorder, compression meshopt par filtres. Pas de quantification : elle déplacerait des échelles dans les transforms de nœuds, dont dépendent pivots et contrat.
- Textures définitives en KTX2 : installer KTX-Software (`toktx`) ; le script signale les textures restées non compressées. Le runtime sait déjà les lire (`KTX2Loader`, transcodeur copié dans `public/basis/`).
- Ne pas basculer `renderer.shadowMap.autoUpdate` à la volée : avec three r186, les matériaux compilés ensuite perdent leurs uniforms de brouillard (scène noyée dans la brume).
