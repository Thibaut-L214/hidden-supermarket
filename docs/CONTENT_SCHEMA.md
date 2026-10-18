# Schéma des contenus pédagogiques

Référence : TECH.md §08, GDD.md §08. Les contenus vivent dans `src/data/chains/*.ts`, séparés du code.

## Cartel

| Champ | Type | Règle |
| --- | --- | --- |
| `id` | `string` | unique, préfixé par la filière (`eggs.collect`) |
| `title` | `string` | court |
| `short` | `string` | une idée, ≤ 140 caractères, affiché dans la vue immersive |
| `detail` | `string` | texte du panneau à la demande |
| `kind` | `"schematic" \| "verified"` | `schematic` = illustration, `verified` = affirmation de terrain |
| `source` | `SourceRef \| "TODO_SOURCE"` | obligatoire pour `verified` |
| `scope` | `string` | échelle géographique et période (ex. « France, 2024 ») |
| `status` | `"draft" \| "review" \| "validated"` | validation éditoriale L214 |

## Source

| Champ | Type | Règle |
| --- | --- | --- |
| `id` | `string` | unique |
| `label` | `string` | titre lisible |
| `url` | `string` | lien consultable |
| `publisher` | `string` | organisme auteur |
| `consultedAt` | `string` | date ISO de consultation |

## Règles

- Aucun chiffre ni fait inventé. Toute donnée inconnue vaut `TODO_SOURCE`.
- Un `TODO_SOURCE` ou un `status` autre que `validated` bloque le build de publication ; il reste permis en développement.
- Pas de généralisation (« tous les animaux… ») : contextualiser par pays, filière et période via `scope`.
- Les scènes compressées dans l'espace ou le temps affichent « représentation schématique ».
