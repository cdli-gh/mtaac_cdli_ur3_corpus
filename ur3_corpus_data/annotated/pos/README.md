# POS/NER annotation of the MTAAC-Ur III corpus

automated annotation accoding to CDLI specifications

- NER and POS annotation
	- https://github.com/cdli-gh/Sumerian-Translation-Pipeline
	- using models `CRF_POS` (HC reports F1 0.991) and `CRF_NER` (HC reports F1 0.913)
	- dictionary-based morphological segmentation

## TODO

- provide train/test classification in JSON file
- provide script to overwrite automatically annotated files with gold files (where available) and to log their status
- enrich morphology with glosses for unseen words using https://github.com/cdli-gh/glosser

## History

- 2019/10/29 conversion & data publication -- CC
- 2019/10/07 statistical and neural POS/NER taggers -- HC (developer), RP (mentor)
- (tbc: dictionary-based morphology analysis by whom and when?)

## Acknowledgments

- tagger developed within GSoC 2020 project by Himanshu Choudhary, mentored by Ravneet Punia
- supported and advised by MTAAC project members and CDLI staff
- todo: acknowledge GSoC and MTAAC funding

## Contributors

- HC [Himanshu Choudhary](https://www.linkedin.com/in/himanshudce/) 
- RP [Ravneet Punia](https://www.linkedin.com/in/ravneetpunia/)
- RB Rachit Bansal
- CC Christian Chiarcos
