# Citations for `_bestrec_run/`

This file is the attribution source of truth for external methods, datasets,
and pretrained encoders used by `_bestrec_run/`. Local scripts may combine,
adapt, or reimplement these components, but the components listed here are
prior work.

| Component | Citation | Used by |
|---|---|---|
| SASRec | Wang-Cheng Kang and Julian McAuley. 2018. "Self-Attentive Sequential Recommendation." ICDM. DOI: 10.1109/ICDM.2018.00035. | `_bestrec_run/run_sasrec_sbert.py` and SASRec-style sequential experiments |
| BLaIR / Amazon Reviews 2023 | Yupeng Hou, Jiacheng Li, Xiangjun Fu, Zhankui He, An Yan, Xiusi Chen, and Julian McAuley. 2024. "Bridging Language and Items for Retrieval and Recommendation: Benchmarking LLMs as Semantic Encoders." arXiv:2403.03952. | BLaIR encoder caches, Amazon Reviews 2023 data, text-feature experiments |
| SASRecText adaptor | Hou et al. 2024 reference code, `external/AmazonReviews2023/seq_rec_results/model/sasrectext.py`. | `--mlp-adaptor` in `_bestrec_run/run_sasrec_sbert.py` |
| SBERT / MiniLM-L6-v2 | Nils Reimers and Iryna Gurevych. 2019. "Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks." EMNLP-IJCNLP. | MiniLM title and rich-text encoder caches |
| BERT4Rec | Fei Sun, Jun Liu, Jian Wu, Changhua Pei, Xiao Lin, Wenwu Ou, and Peng Jiang. 2019. "BERT4Rec: Sequential Recommendation with Bidirectional Encoder Representations from Transformer." CIKM. | `_bestrec_run/run_bert4rec.py` |
| TIGER | Shashank Rajput et al. 2023. "Recommender Systems with Generative Retrieval." NeurIPS. | Comparator framing and `_bestrec_run/run_tiger_minimal.py` prototype |
| LIGER | Liu Yang et al. 2024. "Unifying Generative and Dense Retrieval for Sequential Recommendation." arXiv:2411.18814. | Comparator framing and external `facebookresearch/liger` reference |
| UniSRec | Yupeng Hou, Shanlei Mu, Wayne Xin Zhao, Yaliang Li, Bolin Ding, and Ji-Rong Wen. 2022. "Towards Universal Sequence Representation Learning for Recommender Systems." KDD. arXiv:2206.05941. | Prior modality-based sequential recommendation context |
| iALS | Yifan Hu, Yehuda Koren, and Chris Volinsky. 2008. "Collaborative Filtering for Implicit Feedback Datasets." ICDM. | Implicit-feedback matrix factorization baselines |
| EASE | Harald Steck. 2019. "Embarrassingly Shallow Autoencoders for Sparse Data." WWW. | EASE baseline family |
| LightGCN | Xiangnan He, Kuan Deng, Xiang Wang, Yan Li, Yongdong Zhang, and Meng Wang. 2020. "LightGCN: Simplifying and Powering Graph Convolution Network for Recommendation." SIGIR. | Graph collaborative filtering baseline |
| DropoutNet | Maksims Volkovs, Guangwei Yu, and Tomi Poutanen. 2017. "DropoutNet: Addressing Cold Start in Recommender Systems." NeurIPS. | Cold-start baseline family |
| CLCRec | Yinwei Wei et al. 2021. "Contrastive Learning for Cold-Start Recommendation." ACM Multimedia. | Contrastive cold-start baseline family |
| MultiVAE | Dawen Liang, Rahul G. Krishnan, Matthew D. Hoffman, and Tony Jebara. 2018. "Variational Autoencoders for Collaborative Filtering." WWW. | VAE collaborative filtering baseline |

## Local Contributions To Cite Separately

- 5-core Amazon Reviews 2023 preprocessing pipeline:
  `_bestrec_run/preprocess_5core_standard.py`.
- Memory-efficient chunked-full-softmax implementation:
  `chunked_full_softmax_loss()` in `_bestrec_run/run_sasrec_sbert.py`.
- Cached `all_item_features()` evaluation optimization in
  `_bestrec_run/run_sasrec_sbert.py`.
- NaN-trap diagnosis for left-padding + key-padding-mask + norm-first
  Transformer residual propagation, documented in `SOTA_FINAL_HONEST.md`.
- Empirical transfer evaluation of the Hou et al. SASRecText MLP adaptor on
  this repository's 5-core preprocessing.
