"""Host-owned fitting and frozen-fold scoring, without model-provider imports."""

import math
import random

import numpy as np
import pandas as pd
from sklearn.base import clone

from ageml.protocol import checked_predictions


def seed_process(seed):
    if type(seed) is not int or not 0 <= seed <= 2**32 - 1:
        raise ValueError("run_seed must be an integer between 0 and 2**32 - 1")
    random.seed(seed)
    np.random.seed(seed)


def fit_seeded_model(build_model, X, y, hyperparameters, seed):
    """Build a fresh estimator, seed every exposed random_state, then fit it.

    The generated factory must return an unfitted sklearn-compatible estimator.
    Preprocessing and resampling belong inside its pipeline, never outside CV.
    """
    seed_process(seed)
    model = clone(build_model(X.copy(), y.copy(), **hyperparameters))
    parameters = model.get_params(deep=True)
    effective = {
        name: seed
        for name in parameters
        if name == "random_state" or name.endswith("__random_state")
    }
    model.set_params(**effective)
    model.fit(X.copy(), y.copy())
    return model, effective


def evaluate_candidate(
    build_model,
    train_df,
    validation_df,
    target,
    task,
    hyperparameters,
    seed,
    metric_fn,
    cv_folds=None,
):
    """Return the arithmetic mean of complete fold scores, never pooled OOF score.

    Any failed/nonfinite fold rejects the candidate; partial CV is not ranked.
    A representative last-fold model is returned for artifact verification only.
    """
    splits = cv_folds if cv_folds is not None else [None]
    scores, predictions, seed_parameters = [], [], []
    for fold_id, split in enumerate(splits):
        training = train_df if split is None else train_df.iloc[split["train"]]
        validation = (
            validation_df if split is None else train_df.iloc[split["validation"]]
        )
        training = training.reset_index(drop=True)
        validation = validation.reset_index(drop=True)
        X, y = training.drop(columns=[target]), training[target]
        X_val, y_val = validation.drop(columns=[target]), validation[target]
        model, effective = fit_seeded_model(build_model, X, y, hyperparameters, seed)
        values = checked_predictions(
            model, X_val, task, y.unique() if task == "classification" else None
        )
        score = float(metric_fn(y_val, values))
        if not math.isfinite(score):
            raise ValueError(f"Nonfinite validation score in fold {fold_id}")
        scores.append(score)
        seed_parameters.append(effective)
        rows = list(range(len(validation))) if split is None else split["validation"]
        predictions.extend(
            {"fold": fold_id, "row_id": row, "prediction": value}
            for row, value in zip(rows, values)
        )
    return (
        model,
        {
            "validation_score": float(np.mean(scores)),
            "cv_fold_scores": scores if cv_folds is not None else None,
            "effective_random_states": seed_parameters,
        },
        pd.DataFrame(predictions),
    )
