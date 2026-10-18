# Mesures de performance — prototype rayon œufs

Budgets de référence : TECH.md §07 (60 fps visés, p95 < 25 ms, 30 fps stables sur matériel modeste). Ces chiffres sont des cibles, pas des garanties.

## Comment mesurer

- Lancer `pnpm dev`, ouvrir `http://localhost:5173/?perf`, ou appuyer sur la touche à gauche de `1` (`²` en AZERTY, `` ` `` en QWERTY).
- L'encart affiche : fps moyen et p95 du temps d'image (fenêtre glissante de 300 images), draw calls, triangles, géométries, textures, tas JS (Chrome uniquement), temps de chargement de chaque GLB.
- Mesurer sur la fenêtre visible et au premier plan : un onglet masqué ne produit pas d'images.

## Relevé du 2026-10-18 (Chrome, macOS, fenêtre 858 × 1072, devicePixelRatio 2)

Compteurs de rendu, relevés par image dans le navigateur intégré. Ils ne dépendent pas du matériel.

| Vue | Draw calls | Triangles |
| --- | ---: | ---: |
| Magasin, vue de départ (allée centrale) | 41 | 16 514 |
| Magasin, le long des gondoles | 15 | 6 852 |
| Terrasse, chaîne en cours, regard sur le hangar | 36 | 1 044 |
| Parvis, vue vers l'extérieur | 13 | 2 580 |

| Ressource | Valeur |
| --- | --- |
| `store.glb` | 960 Ko, chargé et validé en 27 ms (local) |
| `terrace_eggs.glb` | 82 Ko, chargé et validé en 7 ms (local) |
| Bundle JS de production | 669 Ko (174 Ko gzip), dont three.js pour l'essentiel |
| Tas JS après une visite complète | 24 Mo |
| Programmes de shaders | 9 |

## Non mesuré

- **fps et p95 réels** : la session de développement tournait dans un onglet en arrière-plan, sans `requestAnimationFrame`. À relever sur les machines cibles (Chrome, Firefox, Safari desktop) avec l'encart `?perf`, en parcourant magasin, terrasse pendant la chaîne et parvis.
- Matériel modeste et mobile : non testé (décision mobile reportée, TECH.md §07).

## Pistes si un budget est dépassé

- Qualité graphique réduite (menu pause) : pixel ratio 1, ombres du soleil coupées.
- `store.glb` est le plus lourd : les produits des gondoles sont des boîtes séparées. Fusionner par matériau ou instancier (`EXT_mesh_gpu_instancing`), puis compresser (meshopt via `@gltf-transform/cli`) à l'étape des assets définitifs.
- Textures définitives en KTX2 avec tailles contrôlées.
