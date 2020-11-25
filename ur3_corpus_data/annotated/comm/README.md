# Commodity annotation of the MTAAC-Ur III corpus

automated annotation in accordance with cdli-accounting-viz

- annotation and interpretation of numbers
- identification of commodities that these numbers refer to
- identification of modifiers of these commodities
- published in a shallow XML format that complements the original ATF files with markup for commodities, numbers and their interpretation in Arabic numerals and modern units
- note that the ATF metadata is not fully preserved in *.comm files
	- https://github.com/cdli-gh/cdli-accounting-viz, see `code/commodify_corpus.py`
	- rule-based annotation based on pattern matching and dictionary lookup
- files for which the commodity annotation did not return `<count>` elements are omitted from the release

statistics:
	
	63,282 files with annotations
	595,928 numbers
	264,146 commodifies
	
## Known issues

parsing errors in four files, omitted from the release

	P110041
	P114312
	P139202
	P143160

## TODO

- provide train/test classification in JSON file

## History

- 2020/11/25 full corpus annotation & data publication -- CC
- 2020/11/24 standalone annotator that returns annotations rather than statistics -- CC
- 2020/10/07 visualization pipeline for CDLI accounting corpora -- LB

## Acknowledgments

- annotator developed within a GSoC 2020 project by Logan Born, mentored by Maxim Ionov, https://summerofcode.withgoogle.com/archive/2020/projects/4616852216479744/
- supported and advised by MTAAC project members and CDLI staff
- todo: acknowledge GSoC and MTAAC funding

## Contributors

- LB [Logan Born](https://mrlogarithm.github.io/about-me/about.html)
- MI Maxim Ionov
- CC Christian Chiarcos
