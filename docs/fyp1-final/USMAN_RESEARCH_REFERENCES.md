# Research context and verified references

AI-assisted companion to `USMAN_FINAL_REPORT_DRAFT.md`. Primary publication
pages and their abstracts/metadata were checked on 2026-11-22. The summaries
below identify conceptual connections; they do not claim reproduction of those
papers' algorithms, datasets, guarantees or reported performance. Convert citation
format to the university/team style when integrating the final report.

## Calibration and selective answers

Guo et al. study confidence calibration and temperature scaling. Halite adapts
temperature fitting to heuristic ranking scores and adds an other bucket. The
paper's successful calibration results do not establish calibration of this
different system. Halite must rely on its own held-out ECE and retain relative-
support wording when that evidence is insufficient. [Guo et al., 2017](https://proceedings.mlr.press/v70/guo17a.html).

Geifman and El-Yaniv study selective classification: rejecting instances trades
coverage against prediction risk. This motivates showing accuracy and coverage
together. Halite's empirical threshold and bootstrap intervals do not inherit
their neural-classifier risk guarantee. [Geifman and El-Yaniv, 2017](https://proceedings.neurips.cc/paper/2017/hash/4a8423d5e91fda00bb7e46540e2b0cf1-Abstract.html).

## Source attribution and generation evaluation

Rashkin et al. define Attributable to Identified Sources and an annotation
framework for checking generated output against supplied sources. This supports
Halite's distinction between a valid citation identifier and a claim following
from the cited text. Its constructed-pair packet and three labels are a local
protocol; they should not be called an implementation of the paper's annotation
pipeline. [Rashkin et al., 2023](https://aclanthology.org/2023.cl-4.2/).

Min et al. evaluate long-form generation through atomic facts supported by a
knowledge source. Halite currently audits sentence spans, which can contain
several factual assertions. Accordingly, its supported-sentence ratio is not
FActScore and must not be reported as an atomic factual-precision measurement.
[Min et al., 2023](https://aclanthology.org/2023.emnlp-main.741/).

Es et al. introduce RAGAs for reference-free evaluation of retrieval-augmented
generation across retrieval and generation dimensions. This is a relevant
automated-evaluation alternative. Halite retains independent human labels for
its checker comparison; an automated judge result alone is not the agreed
human reference. [Es et al., 2024](https://aclanthology.org/2024.eacl-demo.16/).

## Bibliography

1. Chuan Guo, Geoff Pleiss, Yu Sun and Kilian Q. Weinberger. 2017.
   *On Calibration of Modern Neural Networks.* Proceedings of ICML,
   PMLR 70:1321–1330. [Primary publication](https://proceedings.mlr.press/v70/guo17a.html).
2. Yonatan Geifman and Ran El-Yaniv. 2017.
   *Selective Classification for Deep Neural Networks.* Advances in Neural
   Information Processing Systems 30. [Primary publication](https://proceedings.neurips.cc/paper/2017/hash/4a8423d5e91fda00bb7e46540e2b0cf1-Abstract.html).
3. Hannah Rashkin, Vitaly Nikolaev, Matthew Lamm, Lora Aroyo, Michael Collins,
   Dipanjan Das, Slav Petrov, Gaurav Singh Tomar, Iulia Turc and David Reitter. 2023.
   *Measuring Attribution in Natural Language Generation Models.* Computational
   Linguistics 49(4):777–840. DOI 10.1162/coli_a_00486.
   [Primary publication](https://aclanthology.org/2023.cl-4.2/).
4. Sewon Min, Kalpesh Krishna, Xinxi Lyu, Mike Lewis, Wen-tau Yih, Pang Wei Koh,
   Mohit Iyyer, Luke Zettlemoyer and Hannaneh Hajishirzi. 2023.
   *FActScore: Fine-grained Atomic Evaluation of Factual Precision in Long Form
   Text Generation.* EMNLP 2023. [Primary publication](https://aclanthology.org/2023.emnlp-main.741/).
5. Shahul Es, Jithin James, Luis Espinosa Anke and Steven Schockaert. 2024.
   *RAGAs: Automated Evaluation of Retrieval Augmented Generation.* EACL System
   Demonstrations: 150–158. DOI 10.18653/v1/2024.eacl-demo.16.
   [Primary publication](https://aclanthology.org/2024.eacl-demo.16/).

No literature result replaces the actual FAA temporal benchmark. Keep the
report's numerical claims linked to the committed result files and their
independent replay rather than citing external accuracy as Halite's evidence.
