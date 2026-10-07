# Contemporary Symbolic Regression Methods and their Relative Performance

- Reference ID: [paper bibliography 8]
- Status: Adopted
- Category: C/D
- Citation: La Cava, W., Orzechowski, P., Burlacu, B., de Franca, F. O., Virgolin, M., Jin, Y., Kommenda, M., & Moore, J. H. (2021). *Contemporary Symbolic Regression Methods and their Relative Performance*. NeurIPS Datasets and Benchmarks. arXiv:2107.14351.
- arXiv: https://arxiv.org/abs/2107.14351
- Source checked:
  - User-provided PDF `2107.14351v1.pdf`
  - arXiv v1 source files for text-level search
- Access: PDF saved / source text checked
- Local PDF: `references/Contemporary Symbolic Regression Methods and their Relative Performance.pdf`

## Why this paper matters

- It provides a large, reproducible symbolic regression benchmark study.
- It motivates using benchmark problems, train/test splits, repeated trials, and transparent experimental settings when comparing symbolic regression methods.
- It supports the paper's use of repeated stochastic executions rather than judging a GP/BO method from a single run.

## Information used in this project

- The paper uses `No. of trials per dataset` in its experiment table, with `10` trials.
- The experiment design states that each algorithm was trained on each dataset in `10 repeated trials` with a different random state.
- The random state controlled both the train/test split and the algorithm seed.
- The appendix describes jobs as training each method on a single dataset for a fixed random seed.
- Therefore, in this project, the number of experiment repetitions should be described as `independent trials` or `independent runs`, with `different random seeds` as the reproducibility/control mechanism.

## Wording decision

- Avoid using `seed count` as the primary label for the number of experiment repetitions.
- Prefer `independent runs` / `independent trials`.
- In Japanese paper text, use `独立実行数` or `独立試行数`.
- When needed, write `独立実行数 100（異なる乱数シードを使用）`.

