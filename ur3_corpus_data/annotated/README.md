# MTAAC-Ur III corpus with linguistic annotations

mostly automatically created

- `pos/` parts of speech and named entities, CDLI-CoNLL format
- `morph/` pos extended with shallow morphological annotation (automated), CoNLL/TSV format
- `comm/` annotation and interpretation of numbers, commodities and their modifiers, XML format
- `comm_conll/'  pos, morph and comm annotations merged in a CoNLL/TSV format (using the first interpretation per number from `comm/`


- `translit.tsv` all syllabic characters as used in `morph/` with frequency counts. excluded determinatives, incomplete signs, content in parentheses and upper case transliterations. This can be used to develop a morphological transducer.