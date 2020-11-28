
# Merged POS/MORPH and Commodity annotation

- for all `comm` files from `../comm/*/*comm` (and the corresponding `conll` files from `../*/*conll`)
- convert the `comm` file to TSV format using [comm2conll.py](https://github.com/cdli-gh/cdli-accounting-viz)
- append the result of this conversion to the `conll` file, using [CoNLL-Merge](https://github.com/acoli-repo/conll-merge) (`cmd/merge.sh`)
- command (pseudo-code)
	
		$> cat ../comm/MY/FILE.comm | \
		   python3 cdli-accounting-viz/code/comm2conll.py | \
		   conll-merge/cmd/merge.sh ../morph/MY/FILE.conll -- -lev > MY/FILE.conll

## Known issues

Due to a segmentation issue in `comm2conll.py`, artificial tokens have been created when the type of unit contained a whitespace. In the merged files, these are marked as pseudo-tokens (with `*RETOK*-...`), e.g., in P100005. This marking should be fully consistent throughout the corpus.

	*RETOK*-capacity"    ?               ?       ?               ?       B-COUNT l       60      "dry    *       *
	1(barig)             1(bariga)[unit] NU      N               D       I-COUNT *       *       *       sila3   60
	ur-{d}isztaran       Urisztaran[1]   PN      PN.GEN.ABS      D       _       _       _       _       _       _
	*RETOK*-capacity"    ?               ?       ?               ?       B-COUNT l       60      "dry    *       *
	1(barig)             1(bariga)[unit] NU      N               D       I-COUNT *       *       *       sila3   60
	ur-{d}ba-ba6         Urbaba[1]       PN      PN              D       _       _       _       _       _       _
	lu2                  lu[person]      N       N               D       _       _       _       _       _       _
	gir2-su{ki}          Girsu[1][-ak]   SN      SN.GEN          D       _       _       _       _       _       _

In this case, the original unit was `"dry capacity"`. In subsequent processing, their annotations should be merged with those of the *following* token.
