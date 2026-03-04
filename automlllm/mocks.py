from automlllm.common.types import Step
from automlllm.planning.agent import PlanningPipeline

planned_pipeline_1 = PlanningPipeline(
    steps=[
        Step(
            name="imputation",
            candidate="simple_imputer",
            hyperparameters={"strategy": ["mean"]},
        ),
        Step(
            name="features",
            candidate="select_k_best",
            hyperparameters={"k": [5, 10]},
        ),
        Step(
            name="classification",
            candidate="random_forest",
            hyperparameters={
                "n_estimators": [200],
                "max_depth": [None, 20],
            },
        ),
    ]
)


planned_pipeline_2 = PlanningPipeline(
    steps=[
        Step(
            name="imputation",
            candidate="iterative_imputer",
            hyperparameters={"max_iter": [10, 20], "random_state": [42]},
        ),
        Step(
            name="features",
            candidate="pca",
            hyperparameters={"n_components": [5, 10]},
        ),
        Step(
            name="classification",
            candidate="knn",
            hyperparameters={
                "n_neighbors": [5, 10],
                "weights": ["uniform", "distance"],
            },
        ),
    ]
)
