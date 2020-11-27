
# Shallow morphological annotation over the Ur-III corpus

Based on an extrapolation from the MTAAC Gold corpus, including external components (overlap with ETSCRI).

Using `pos/*/*conll` as input, these files were automatically created by iterating the [MTAAC Glosser](https://github.com/cdli-gh/glosser) over all files, using the following command:

	$> cut -f 2- pos/DIR/FILE.conll | \
	   java Glosser mtaac-morph.dict.tsv mtaac-morph-ext.dict.tsv | cut -f 1-3,5,9 | \
	   java Merger -pos 2 -code 3 -gloss 4 | cut -f 1-3,6,7 > morph/DIR/FILE.conll
	
Note that the Glosser differs from our [morphological pre-annotator (MPAT)](https://github.com/cdli-gh/morphology-pre-annotation-tool) in that it implements frequency-based heuristics to infer the annotation of *unseen* words, and in that it returns one possible analysis only, using context-free disambiguation on grounds of frequency.

The Merger is a Glosser auxiliary class that returns Glosser output (and its inference strategy) if it is either 

1. consistent with original `POS` annotation, or 
2. based on a direct dictionary lookup.

In the latter case, the statistical POS tagger is actually *likely* to be incorrect. If Glosser annotations are neither consistent with `POS` nor directly backed by the dictionary, then the merger does

3. resort to the value of `POS`.

## Format

 - `WORD` (from `pos/`)
 - `SEGM` (from `pos/`)
 - `POS` (from `pos/`)
 - `MORPH` (from Glosser, if consistent with `POS` or confirmed by dictionary lookup)
 - `CODE` (produced by Glosser and Merger, this indicates the lookup/inference strategy, i.e.
	 - `D`    dictionary lookup, may override `POS`
	 - `I...` Glosser inference for an unseen word, only if compliant with `POS`
	 - `POS`  annotation taken from `POS` in case Glosser inference was not consistent with `POS`

Note that we lose the original `ID` column of the files in `pos/`.

## Statistics

| total per CODE | subset | ratio | CODE/subset | --- | --- | --- |
| -------------- | ------ | ----- | ----------- | --- | --- | --- |
| 3012502	 | 	 | 89%	 | D	 | POS ~ D	 | POS <> D	 | top deviating POS prediction	 | 
| 	 | 1441881	 | 48%	 | N	 | 100%	 | 0%	 | PN	 | 
| 	 | 869905	 | 29%	 | NU	 | 77%	 | 23%	 | N	 | 
| 	 | 297478	 | 10%	 | PN	 | 45%	 | 55%	 | N	 | 
| 	 | 230436	 | 8%	 | V	 | 95%	 | 5%	 | N	 | 
| 	 | 172802	 | 6%	 | other	 | 	 | 	 | 	 | 
| 	 | 	 | 	 | 	 | 	 | 	 | 	 | 
| 210216	 | 	 | 6%	 | I...	 | 	 | 	 | 	 | 
| 	 | 41248	 | 20%	 | Ia	 | 	 | 	 | 	 | 
| 	 | 23789	 | 11%	 | Iab	 | 	 | 	 | 	 | 
| 	 | 5660	 | 3%	 | Iabc	 | 	 | 	 | 	 | 
| 	 | 1329	 | 1%	 | Iabcd	 | 	 | 	 | 	 | 
| 	 | 48490	 | 23%	 | Iabcde	 | 	 | 	 | 	 | 
| 	 | 26538	 | 13%	 | Iabcdef	 | 	 | 	 | 	 | 
| 	 | 25017	 | 12%	 | Iabcdefg	 | 	 | 	 | 	 | 
| 	 | 35342	 | 17%	 | Iabcdefgh	 | 	 | 	 | 	 | 
| 	 | 1856	 | 1%	 | Iabcdefghi	 | 	 | 	 | 	 | 
| 	 | 947	 | 0%	 | Iabcdefghij	 | 	 | 	 | 	 | 
| 	 | 	 | 	 | 	 | 	 | 	 | 	 | 
| 145713	 | 	 | 4%	 | POS	 | 	 | 	 | 	 | 
| 	 | 40696	 | 28%	 | N	 | 	 | 	 | 	 | 
| 	 | 40009	 | 27%	 | PN	 | 	 | 	 | 	 | 
| 	 | 28893	 | 20%	 | V	 | 	 | 	 | 	 | 
| 	 | 8648	 | 6%	 | FN	 | 	 | 	 | 	 | 
| 	 | 5714	 | 4%	 | DN	 | 	 | 	 | 	 | 
| 	 | 5329	 | 4%	 | GN	 | 	 | 	 | 	 | 
| 	 | 4308	 | 3%	 | NU	 | 	 | 	 | 	 | 
| 	 | 12116	 | 8%	 | other	 | 	 | 	 | 	 | 
| 	 | 	 | 	 | 	 | 	 | 	 | 	 | 
| 3368431	 | 	 | 	 | total	 | 	 | 	 | 	 | 
| 
