# An Agentic Framework for Crafting AutoML end-to-end Pipelines

## Abstract

State of the art AutoML frameworks allow for automatic hyperparameter tuning for machine learning (ML) models.
Despite these methods have shown increased performance thanks to their systematic search for the optimal model, they commonly automate a small portion of the entire ML workflow, disregarding crucial steps such as data preprocessing, feature engineering/selection, validation, deployment, etc.
Recent advancements in large language models (LLMs) have paved the way for more comprehensive AutoML solutions that aim to automate the entire ML pipeline by means of code generation---the whole idea can be described as an AI agent _autonomously_ crafting a tool for data science tasks.
While other works have explored the exploitation of LLM-based AI agents for automating ML tasks often leading to black-box solutions with limited user controllability, in this paper we present a novel agentic framework for AutoML that keep human users in control.
Our focus here is on how to let ML practitioners express their expertise, needs, and constraints about the desired ML pipeline, and how to let the agent iteratively refine the generated solution ML based such information.

This approach not only democratizes the access to ML for non-experts but also leverages the planning capabilities of Large Language Models (LLMs) to construct robust, performant pipelines while mitigating issues like technical hallucinations.

## Introduction

## Related Work

- Main reference: [AutoML-Agent](https://arxiv.org/pdf/2410.02958)
  - this paper proposes a multi-agent framework that orchestrates specialized LLM agents (Agent Manager, Prompt Agent, Data Agent, etc...) to automate everything from data retrieval and preprocessing to model design, training, and deployment.
  - uses RAG planning strategy, plan is divided to multiple steps for specilized agents.
- [AutoML survey](https://l1nq.com/3XvzI)
- [Agentic AI survey](https://ieeexplore.ieee.org/stamp/stamp.jsp?tp=&arnumber=10849561)

### Agentic AI

### AutoML

## Methodology

### Agent State Machine

### Machine Learning Pipeline

### Human-in-the-Loop

## Experiments

## Results

## Conclusion

We propose an LLM-based agentic framework for end-to-end AutoML. By combining the generative power of LLMs with structured agentic workflows and human feedback, we address the limitations of current tools, paving the way for more intuitive and powerful AI assistants.
