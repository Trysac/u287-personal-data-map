# Token-phrase rules for column classification

Status: accepted (generated, pending human review)

## Context

Column names must be classified into personal-data categories with first-match priority. Simple individual-token matching would misclassify names like ship_date as date_of_birth, while a fixed sequence of all tokens in a rule would never match real columns.

## Decision

Store each DEFAULT_RULES rule as a tuple of token phrases (e.g., "date of birth", "birthdate"). A column matches when any phrase's tokenization (same splitter as column names) appears contiguously in the column's tokens. This supports multi-token phrases and single tokens in the same Rule object.

## Consequences

The rule representation stays a flat tuple[str, ...] as specified, while matching is precise enough to satisfy adversarial boundary tests. Custom rules must use the same phrase-in-tuple convention.
