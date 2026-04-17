## [4.6.1](https://github.com/Mala1180/automl-llm/compare/4.6.0...4.6.1) (2026-04-17)

### Bug Fixes

* reduce nn size and add some experiments result ([df93a12](https://github.com/Mala1180/automl-llm/commit/df93a120edae9060b4b9efc5631ce5483d6d99b5))

### Refactoring

* update README and add script for downloading datasets ([4b19b8a](https://github.com/Mala1180/automl-llm/commit/4b19b8ae197e9f8160d0a219c225820b2a22df86))

## [4.6.0](https://github.com/Mala1180/automl-llm/compare/4.5.1...4.6.0) (2026-04-16)

### Features

* improve artifact logging (explanation and pipelines are logged if pipelines fail), improve general specification fixing regression tasks ([bb33209](https://github.com/Mala1180/automl-llm/commit/bb33209afb9baafb4ed70a5771e4b143b98e6f1d))

## [4.5.1](https://github.com/Mala1180/automl-llm/compare/4.5.0...4.5.1) (2026-04-15)

### Bug Fixes

* fix csv creation ([824f14e](https://github.com/Mala1180/automl-llm/commit/824f14ec02e60e96aab0ddbe52ef603ac688593a))

## [4.5.0](https://github.com/Mala1180/automl-llm/compare/4.4.0...4.5.0) (2026-04-15)

### Features

* add balanced_accuracy as default metric ([998fefa](https://github.com/Mala1180/automl-llm/commit/998fefa4962181868bc523a9d4a99c699852af8e))

### Refactoring

* change csv file name ([065f03b](https://github.com/Mala1180/automl-llm/commit/065f03b90f7bb1ee16edfd9f230f44d5d81481f2))
* **specification:** change step condition in yaml, now it can be string or dict ([4ec601c](https://github.com/Mala1180/automl-llm/commit/4ec601ce5327bc52b75a2ad34ad96011584b6381))

## [4.4.0](https://github.com/Mala1180/automl-llm/compare/4.3.0...4.4.0) (2026-04-15)

### Features

* add dataset ids and workers to csv ([2fcc4b2](https://github.com/Mala1180/automl-llm/commit/2fcc4b2f73fd7d1be26e062501991a7c0aa524ec))

### General maintenance

* improve trace logging ([0d49b96](https://github.com/Mala1180/automl-llm/commit/0d49b96cfe215b0e487ca997e63badd497b0db2e))

## [4.3.0](https://github.com/Mala1180/automl-llm/compare/4.2.0...4.3.0) (2026-04-14)

### Features

* add input/output tokens to results ([17dd554](https://github.com/Mala1180/automl-llm/commit/17dd55465f9a9444da08301cbe6375ec8619c4ed))

## [4.2.0](https://github.com/Mala1180/automl-llm/compare/4.1.0...4.2.0) (2026-04-14)

### Features

* improve execution time logging ([a2343cf](https://github.com/Mala1180/automl-llm/commit/a2343cf80ac0a427a0b7c7b647e1ade55efe4086))

### Refactoring

* add timed_call for llm invocations ([f2d5a18](https://github.com/Mala1180/automl-llm/commit/f2d5a18e4c3ccfbdc9dc1c238c93510aac415313))

## [4.1.0](https://github.com/Mala1180/automl-llm/compare/4.0.0...4.1.0) (2026-04-13)

### Features

* add csv creation for experiments results, log inference and training time ([2e4200c](https://github.com/Mala1180/automl-llm/commit/2e4200c099fff0df9212540c8ab25ce578a71114))
* add token usage and costs logs ([e4a3255](https://github.com/Mala1180/automl-llm/commit/e4a3255a9df4a5dbbea6c048cbd0aef1d31707a4))

### Dependency updates

* **deps:** update mlflow dependency ([7512e5c](https://github.com/Mala1180/automl-llm/commit/7512e5c632df56101ad5d4a04bd504a96fe850ee))

### Bug Fixes

* fix train test split for regression problems ([9fb5933](https://github.com/Mala1180/automl-llm/commit/9fb5933540d137863bb1f805aacc5cf04e55f298))

### General maintenance

* change run name format ([0ff4649](https://github.com/Mala1180/automl-llm/commit/0ff4649f9f1432958a58fa2a5b8021751767adc8))
* save all error files ([730e37e](https://github.com/Mala1180/automl-llm/commit/730e37e015035b5ad2c648048cc78c1b3b03fa90))

## [4.0.0](https://github.com/Mala1180/automl-llm/compare/3.5.0...4.0.0) (2026-04-10)

### ⚠ BREAKING CHANGES

* **execution:** add elapsed time, refactor parallelism with Pool, add status to ExecutionPipeline

### Bug Fixes

* refactor runs structure on mlflow, fix increment of execution_attempts ([9110379](https://github.com/Mala1180/automl-llm/commit/91103790b3bd8e551df96a07c0fe87f7eb75f7de))
* stratify dataset for split, modify prompt to classify better the kind of problem (regression/classification) ([eb40c1d](https://github.com/Mala1180/automl-llm/commit/eb40c1d6f0ad8c0f13057f7506b368f98df726b4))

### Refactoring

* **execution:** add elapsed time, refactor parallelism with Pool, add status to ExecutionPipeline ([b27962d](https://github.com/Mala1180/automl-llm/commit/b27962d86c076e8b1d37943c2854ecfee210c162))

## [3.5.0](https://github.com/Mala1180/automl-llm/compare/3.4.0...3.5.0) (2026-04-01)

### Features

* **specification:** add possibility to provide list of names in feature name condition ([fad7edb](https://github.com/Mala1180/automl-llm/commit/fad7edbb35e1296b625cc85f4129a6a3e8272f58))

### General maintenance

* add openml dependency ([472b3c4](https://github.com/Mala1180/automl-llm/commit/472b3c42d6ec7cb41f3d6772a728483a9f466ebd))
* improve logs ([08dcec0](https://github.com/Mala1180/automl-llm/commit/08dcec08a2b3310ddad209d7686b3f0fb865d164))
* remove dataset dir ([fa1bdbc](https://github.com/Mala1180/automl-llm/commit/fa1bdbc121f01e992ba125eee907eb51caf987a9))

### Refactoring

* change natural language condition in specification, pass generation_attempts through specification ([993ed5f](https://github.com/Mala1180/automl-llm/commit/993ed5f50d11918120f6904d4123add84e1097fc))
* update main entry point, add run name to logs, setup main of experiments ([9d4c1e9](https://github.com/Mala1180/automl-llm/commit/9d4c1e92dde07c0e410f8056b3faa6fb3a840c96))

## [3.4.0](https://github.com/Mala1180/automl-llm/compare/3.3.0...3.4.0) (2026-03-27)

### Features

* add target feature inference, validation metric in input, and best run evaluation per pipeline ([5555a4a](https://github.com/Mala1180/automl-llm/commit/5555a4a3dd955e4a555dd7e3ed51dfb5c204690e))
* modify models training using train/val datasets, add evaluation agent to pick best pipeline after evaluation on test set ([1925d88](https://github.com/Mala1180/automl-llm/commit/1925d88d42df77fa95bc11aa47a1f166e1e39bdf))

### Bug Fixes

* move target feature identification before planning ([8c343b2](https://github.com/Mala1180/automl-llm/commit/8c343b2a6f19e8f52da4ef63aa4c4fd2b2e7dafd))

### General maintenance

* add mlflow stuffs to gitignore ([e342ff8](https://github.com/Mala1180/automl-llm/commit/e342ff8c09487dad8eb2aa3dfa09810616e50558))
* fix some typos in readme ([ee7197b](https://github.com/Mala1180/automl-llm/commit/ee7197b18d4bfef3a4f94407728d821ecd7d04c9))
* fix typing and improve mlflow run names ([b0a75d0](https://github.com/Mala1180/automl-llm/commit/b0a75d070dd73aa1d9be3289bf4c3954f7c694ee))
* minor refinements on prompts, logs and specifications ([40fc358](https://github.com/Mala1180/automl-llm/commit/40fc3588e7cf8aa3b7e751dbc42159a257c48bf8))
* modify logs ([9a8326f](https://github.com/Mala1180/automl-llm/commit/9a8326f9b74108aae843ae9a7320229013db5128))
* rename ordering field in specification ([1aae3a5](https://github.com/Mala1180/automl-llm/commit/1aae3a5ac06aaf136e62da3d7ddcec89d7d1cfc5))

### Refactoring

* improve log models/artifacts, improve some prompts, exclude sklearn from mypy checks ([7b1d732](https://github.com/Mala1180/automl-llm/commit/7b1d732bd824b077eb5c39f9a51c16b897617df2))
* update DatasetFeatureCondition fields ([c84b359](https://github.com/Mala1180/automl-llm/commit/c84b359903708e0fe9f8ace4399881e2b252d778))

## [3.3.0](https://github.com/Mala1180/automl-llm/compare/3.2.0...3.3.0) (2026-03-18)

### Features

* add TimeBudget and tasks deadline ([7a116d9](https://github.com/Mala1180/automl-llm/commit/7a116d96990bcedcf993ce28876fc41397ad4ada))

### Refactoring

* change constraints indentation in specification files ([687112d](https://github.com/Mala1180/automl-llm/commit/687112d217fdc6a111c53257edaea948f337a6e2))
* change orderings indentation in specification files ([9aeef71](https://github.com/Mala1180/automl-llm/commit/9aeef714af8dc03140ab0255cfdf8218662e3409))

## [3.2.0](https://github.com/Mala1180/automl-llm/compare/3.1.1...3.2.0) (2026-03-17)

### Features

* **execution:** add explanation to run description ([fc53847](https://github.com/Mala1180/automl-llm/commit/fc53847202bdc8b4794ddfbbce52fe92bd799429))

## [3.1.1](https://github.com/Mala1180/automl-llm/compare/3.1.0...3.1.1) (2026-03-17)

### Bug Fixes

* **execution:** fix class of structured output model ([541066f](https://github.com/Mala1180/automl-llm/commit/541066f7525c5ec50900cb4f891d34f477186200))

### Refactoring

* max_exploration is now specified in the specification ([0478f83](https://github.com/Mala1180/automl-llm/commit/0478f834046bf1c0865898063ee8691ddd0ea104))

## [3.1.0](https://github.com/Mala1180/automl-llm/compare/3.0.0...3.1.0) (2026-03-16)

### Features

* add pipeline exploration cap with random selection, improve prompts for code generation ([82578a2](https://github.com/Mala1180/automl-llm/commit/82578a2fd0768e0ee66d7f004798c89058a0eb81))
* improve logging and nesting of runs ([48adff0](https://github.com/Mala1180/automl-llm/commit/48adff023745c29f6bfd715563216606a594fe03))
* **planning:** add TrueCondition, semantic constraints, refactor planning agent in order to generate a list of pipelines ([9258a66](https://github.com/Mala1180/automl-llm/commit/9258a66762e87f1f8334dde1cfcce5c10d408b17))

### General maintenance

* fill README.md ([82846d3](https://github.com/Mala1180/automl-llm/commit/82846d374c3bdb7b2c7d625bafa142ae2c1471ff))

### Refactoring

* remove initial and terminal fields from specification ([8b90150](https://github.com/Mala1180/automl-llm/commit/8b90150af43adebadf9f8c642eda4408390428cb))

## [3.0.0](https://github.com/Mala1180/automl-llm/compare/2.0.1...3.0.0) (2026-03-12)

### ⚠ BREAKING CHANGES

* remove pipeline graph and create one pipeline at a time
* **specification:** remove graph validation

### Features

* add hyperparameters to pipeline and specification ([2890f70](https://github.com/Mala1180/automl-llm/commit/2890f70a098584509f60fbd4cb38ed074e3fc781))
* add main for the entire workflow ([c332715](https://github.com/Mala1180/automl-llm/commit/c332715d68574b4fe5d342d99c85b2b9bf658da7))
* add technical details in specification ([1ad7bf8](https://github.com/Mala1180/automl-llm/commit/1ad7bf8a719b3264e6d7746c0f0cafeb5812220a))
* **executing:** add human feedback, remove system metrics logs ([40f7a86](https://github.com/Mala1180/automl-llm/commit/40f7a86480b173e75b5bf113efd683152b4d8058))
* **execution:** add nested runs and autolog ([75a22b2](https://github.com/Mala1180/automl-llm/commit/75a22b2657433f5fbbbc41e398e6d698693e933d))
* pipeline generation works ([12e5dec](https://github.com/Mala1180/automl-llm/commit/12e5dec56d952cee7883e1e5ecc4962cbd004658))
* **planning:** add z3 solver for pipelines exploration ([3541e89](https://github.com/Mala1180/automl-llm/commit/3541e89019b516aadd7a5b37fa3bdbfb19715960))
* **specification:** add encoding for DatasetCondition ([12ef6cd](https://github.com/Mala1180/automl-llm/commit/12ef6cd79d44b6a5fcd845f7f6008df6c65a0762))
* **specification:** add encoding for NaturalLanguageCondition ([4c92de7](https://github.com/Mala1180/automl-llm/commit/4c92de72ecfd0659ca591a7eb3e96003c18960df))
* **specification:** add sequence short hand for ordering rules ([c52c737](https://github.com/Mala1180/automl-llm/commit/c52c73720891cb8c8a889602bc2249232261d50c))
* **specification:** improve typing of constraint condition ([3b3eeed](https://github.com/Mala1180/automl-llm/commit/3b3eeed41538510588e2f2dacd81aef9f0692b5b))

### Dependency updates

* **deps:** add imblearn ([49c699c](https://github.com/Mala1180/automl-llm/commit/49c699c4eba4d5b9d78e98f06bb45b993f4f6617))
* **deps:** add z3 solver dependency ([c9a865f](https://github.com/Mala1180/automl-llm/commit/c9a865feeaf09ee3cf5c2b7881add0b9787cba67))

### Bug Fixes

* **solver:** add constraints to step indexes to avoid duplicates solutions ([0849e70](https://github.com/Mala1180/automl-llm/commit/0849e70ddf84919d05fe9f367f1dff645c45b067))

### Performance improvements

* **execution:** add multiprocess computation for code execution ([c17638e](https://github.com/Mala1180/automl-llm/commit/c17638e764965f7740b963de3905a8e3f7a9256f))

### General maintenance

* fix some imports and refactor attempts in execution agent ([fa3e31e](https://github.com/Mala1180/automl-llm/commit/fa3e31efc0ba8192834577284eb44d528b32338d))
* generation of pipelines via z3 ([2cd7801](https://github.com/Mala1180/automl-llm/commit/2cd7801ce57864dc28a7afc30587aefba2928f2d))
* improve constraints ([349ff85](https://github.com/Mala1180/automl-llm/commit/349ff85acba09301840d316c7035475cd674998d))
* improve constraints, generate solutions ([3cb4a81](https://github.com/Mala1180/automl-llm/commit/3cb4a81ac86ff19ca61e4ab1967170d987ddb2fb))
* improve Pipeline hyperparameter string representation ([160d1c9](https://github.com/Mala1180/automl-llm/commit/160d1c9475ed302a6920bd981aad7daa60a2ebbf))
* rename yaml specification ([300d7fb](https://github.com/Mala1180/automl-llm/commit/300d7fb7d53441f12beee3c5edffd64502c942d1))
* **resources:** add specification for regression case ([238e33d](https://github.com/Mala1180/automl-llm/commit/238e33de574aba168d4b1581d455502aba9b2142))

### Refactoring

* **executing:** add validation after code execution, change structure of judge model response ([63fac71](https://github.com/Mala1180/automl-llm/commit/63fac7152e43675e86158f5b0b3249d68aa1b476))
* remove pipeline graph and create one pipeline at a time ([fd12256](https://github.com/Mala1180/automl-llm/commit/fd122562713de055aaeac7b9c040474fb477d5ea))
* **specification:** change IfCondition to support various condition types (add StepCondition) ([af38dcd](https://github.com/Mala1180/automl-llm/commit/af38dcd05490b4411cad1f8f9acf72004550bcdd))
* **specification:** change order created by sequence ([586d008](https://github.com/Mala1180/automl-llm/commit/586d008a018140458625721aefad241dc76168ba))
* **specification:** remove graph validation ([d167a69](https://github.com/Mala1180/automl-llm/commit/d167a69cc3149c079f6ea5328e67eb4215f4e0a2))

## [2.0.1](https://github.com/Mala1180/automl-llm/compare/2.0.0...2.0.1) (2026-02-17)

### Bug Fixes

* correct arg name in draw function call ([9214684](https://github.com/Mala1180/automl-llm/commit/9214684a0f0cf9f95776083e1786ffe7ff1f4f64))

### Tests

* add test for invalid paths ([3e6fca2](https://github.com/Mala1180/automl-llm/commit/3e6fca2f4c16f827398aea9e5371604d8b998ada))
* improve test organization ([b574682](https://github.com/Mala1180/automl-llm/commit/b574682958408bc9a1347eb431cda5d892efdb35))
* **specification:** add tests for specification parsing ([8cb73fd](https://github.com/Mala1180/automl-llm/commit/8cb73fdcfd5f7f501d6b362d98bfa3915002d12e))

### Refactoring

* improve specification package structure ([77158e0](https://github.com/Mala1180/automl-llm/commit/77158e0a8dd537be003d078f116b801d7fc5f42c))

## [2.0.0](https://github.com/Mala1180/automl-llm/compare/1.1.0...2.0.0) (2026-02-10)

### ⚠ BREAKING CHANGES

* change specification and graph creation (from one pipeline to multiple pipeline generation)

### Features

* **execution:** change code generation in order to iterate over pipelines, add explanation node, save code and explanation in out dir ([30631b4](https://github.com/Mala1180/automl-llm/commit/30631b4de384ab112b0cd98a77f897dfe2c99368))
* **execution:** setup agents that generate code for machine learning pipelines ([bd5e167](https://github.com/Mala1180/automl-llm/commit/bd5e1677c071d0146f1615571433bd4b82aecdee))
* **specification:** add hyperparameters (not yet in execution) ([dd79a69](https://github.com/Mala1180/automl-llm/commit/dd79a69ebe5f3485905bd4dedbbebeb686e1616d))
* **specification:** add natural language version of specification ([6a4b0a3](https://github.com/Mala1180/automl-llm/commit/6a4b0a3e1d510c4a8c7ee745d4beaf1994a172bd))

### General maintenance

* **planning:** remove usused langchain version ([11b88bf](https://github.com/Mala1180/automl-llm/commit/11b88bfddec8abb72b11556f5770c47a472b689a))
* **release:** 1.2.0 [skip ci] ([7d8c7e3](https://github.com/Mala1180/automl-llm/commit/7d8c7e35a7f604ac9835efd3a8b363a3f3dc1b6c))
* **release:** 1.2.0 [skip ci] ([1da2fc0](https://github.com/Mala1180/automl-llm/commit/1da2fc0ef993202b48190528df42eb2830deb95e))
* **release:** 1.2.0 [skip ci] ([ec14d3f](https://github.com/Mala1180/automl-llm/commit/ec14d3f4c7265bcaf40272b94695180bcbb325ae))
* **specification:** improve PipelineGraph typing ([8116c49](https://github.com/Mala1180/automl-llm/commit/8116c497c9fdc6529e71e53ae68b88bf2cde047e))
* **test:** improve a test ([9219b32](https://github.com/Mala1180/automl-llm/commit/9219b32548650e2f50b420be1de8f394465deb4b))

### Refactoring

* change specification and graph creation (from one pipeline to multiple pipeline generation) ([4ae02e9](https://github.com/Mala1180/automl-llm/commit/4ae02e9900dc897a05ffca5c1feef1d90a214116))
* **specification:** improve constraints check ([8fde8b5](https://github.com/Mala1180/automl-llm/commit/8fde8b5e0949108a214fd8663d8802412c1ef240))

## [1.2.0](https://github.com/Mala1180/automl-llm/compare/1.1.0...1.2.0) (2026-02-10)

### Features

* **execution:** change code generation in order to iterate over pipelines, add explanation node, save code and explanation in out dir ([30631b4](https://github.com/Mala1180/automl-llm/commit/30631b4de384ab112b0cd98a77f897dfe2c99368))
* **execution:** setup agents that generate code for machine learning pipelines ([bd5e167](https://github.com/Mala1180/automl-llm/commit/bd5e1677c071d0146f1615571433bd4b82aecdee))
* **specification:** add hyperparameters (not yet in execution) ([dd79a69](https://github.com/Mala1180/automl-llm/commit/dd79a69ebe5f3485905bd4dedbbebeb686e1616d))
* **specification:** add natural language version of specification ([6a4b0a3](https://github.com/Mala1180/automl-llm/commit/6a4b0a3e1d510c4a8c7ee745d4beaf1994a172bd))

### General maintenance

* **planning:** remove usused langchain version ([11b88bf](https://github.com/Mala1180/automl-llm/commit/11b88bfddec8abb72b11556f5770c47a472b689a))
* **release:** 1.2.0 [skip ci] ([1da2fc0](https://github.com/Mala1180/automl-llm/commit/1da2fc0ef993202b48190528df42eb2830deb95e))
* **release:** 1.2.0 [skip ci] ([ec14d3f](https://github.com/Mala1180/automl-llm/commit/ec14d3f4c7265bcaf40272b94695180bcbb325ae))
* **specification:** improve PipelineGraph typing ([8116c49](https://github.com/Mala1180/automl-llm/commit/8116c497c9fdc6529e71e53ae68b88bf2cde047e))
* **test:** improve a test ([9219b32](https://github.com/Mala1180/automl-llm/commit/9219b32548650e2f50b420be1de8f394465deb4b))

### Refactoring

* **specification:** improve constraints check ([8fde8b5](https://github.com/Mala1180/automl-llm/commit/8fde8b5e0949108a214fd8663d8802412c1ef240))

## [1.2.0](https://github.com/Mala1180/automl-llm/compare/1.1.0...1.2.0) (2026-02-06)

### Features

* **execution:** change code generation in order to iterate over pipelines, add explanation node, save code and explanation in out dir ([30631b4](https://github.com/Mala1180/automl-llm/commit/30631b4de384ab112b0cd98a77f897dfe2c99368))
* **execution:** setup agents that generate code for machine learning pipelines ([bd5e167](https://github.com/Mala1180/automl-llm/commit/bd5e1677c071d0146f1615571433bd4b82aecdee))
* **specification:** add hyperparameters (not yet in execution) ([dd79a69](https://github.com/Mala1180/automl-llm/commit/dd79a69ebe5f3485905bd4dedbbebeb686e1616d))
* **specification:** add natural language version of specification ([6a4b0a3](https://github.com/Mala1180/automl-llm/commit/6a4b0a3e1d510c4a8c7ee745d4beaf1994a172bd))

### General maintenance

* **release:** 1.2.0 [skip ci] ([ec14d3f](https://github.com/Mala1180/automl-llm/commit/ec14d3f4c7265bcaf40272b94695180bcbb325ae))
* **specification:** improve PipelineGraph typing ([8116c49](https://github.com/Mala1180/automl-llm/commit/8116c497c9fdc6529e71e53ae68b88bf2cde047e))
* **test:** improve a test ([9219b32](https://github.com/Mala1180/automl-llm/commit/9219b32548650e2f50b420be1de8f394465deb4b))

### Refactoring

* **specification:** improve constraints check ([8fde8b5](https://github.com/Mala1180/automl-llm/commit/8fde8b5e0949108a214fd8663d8802412c1ef240))

## [1.2.0](https://github.com/Mala1180/automl-llm/compare/1.1.0...1.2.0) (2026-02-06)

### Features

* **execution:** setup agents that generate code for machine learning pipelines ([bd5e167](https://github.com/Mala1180/automl-llm/commit/bd5e1677c071d0146f1615571433bd4b82aecdee))
* **specification:** add natural language version of specification ([6a4b0a3](https://github.com/Mala1180/automl-llm/commit/6a4b0a3e1d510c4a8c7ee745d4beaf1994a172bd))

### General maintenance

* **specification:** improve PipelineGraph typing ([8116c49](https://github.com/Mala1180/automl-llm/commit/8116c497c9fdc6529e71e53ae68b88bf2cde047e))
* **test:** improve a test ([9219b32](https://github.com/Mala1180/automl-llm/commit/9219b32548650e2f50b420be1de8f394465deb4b))

### Refactoring

* **specification:** improve constraints check ([8fde8b5](https://github.com/Mala1180/automl-llm/commit/8fde8b5e0949108a214fd8663d8802412c1ef240))

## [1.1.0](https://github.com/Mala1180/automl-llm/compare/1.0.0...1.1.0) (2026-01-30)

### Features

* **specification:** add specification class ([b6680f1](https://github.com/Mala1180/automl-llm/commit/b6680f1cff9ca462494d1456dae1948f0cfbcc96))

### Refactoring

* rename planning agent class and improve prompts ([8946626](https://github.com/Mala1180/automl-llm/commit/89466264e9cb6fbdbd39054e898b29a0574b54aa))
* **specification:** add defaults field, improve specification with parsing ([60430e6](https://github.com/Mala1180/automl-llm/commit/60430e6289222d2b547b0a5502b6ada7ebcf5089))

## 1.0.0 (2026-01-27)

### Features

* add basic agent and tools, add adult dataset for use case ([d1d465a](https://github.com/Mala1180/automl-llm/commit/d1d465a8fac14e283e3b43c0cd72eb336a6d6a9b))
* add fail fast option to Validator, replace "condition" with "if" in specification constraints ([54383e9](https://github.com/Mala1180/automl-llm/commit/54383e9a312d44ae01fbd7065dd2db330f064b5f))
* add new planning agent using langgraph api ([a8e3475](https://github.com/Mala1180/automl-llm/commit/a8e34753cb403336e3e2a704a5d464751576d224))
* add streaming and human in the loop ([30f8993](https://github.com/Mala1180/automl-llm/commit/30f899397ca0fd30ca388cd33016b619d8908368))
* refactor agents, add automl use case, add Validator and tests ([6b0a903](https://github.com/Mala1180/automl-llm/commit/6b0a90330da58121b4901a3e61a60d2de90fb97c))
* use planning agent to generate a right ML pipeline ([d8a46ce](https://github.com/Mala1180/automl-llm/commit/d8a46ceed71ef86edfd7ce55ae07abb2666f3cad))

### Build and continuous integration

* downgrade networkx dependency and add more python versions ([32aae40](https://github.com/Mala1180/automl-llm/commit/32aae40519637906b5e961b4888412771bc8773e))
* fix python versions ([fcec2ad](https://github.com/Mala1180/automl-llm/commit/fcec2adab35bc1c2b9e75ec59f54e831deefb3dc))
* remove publish on pypi ([ace9ad5](https://github.com/Mala1180/automl-llm/commit/ace9ad5d1f69b774d0e560d9e3dbc8120809d7dc))

### General maintenance

* fix mypy errors ([9a43e6f](https://github.com/Mala1180/automl-llm/commit/9a43e6fdd007a03f413f34e8e437407c101a665d))
* fix project name ([54217f3](https://github.com/Mala1180/automl-llm/commit/54217f30d37a1099712a528681011ade0a7a0f78))
* initialise repository renaming files and removing init workflow [skip ci] ([b39060c](https://github.com/Mala1180/automl-llm/commit/b39060cf4cd3fe8e0d2ee7aa6028aef2da08c9ee))

### Refactoring

* refactor project structure ([b9ea111](https://github.com/Mala1180/automl-llm/commit/b9ea111c426f3760e01c3eb93bd02d2358bcf8ff))
* separate agent implementation (langchain/langgraph), improve prompt in langgraph agent ([b02310c](https://github.com/Mala1180/automl-llm/commit/b02310cc24af4d0fd6fd05d7ce235b6480eefe3d))

## [2.4.1](https://github.com/aequitas-aod/template-python-project-poetry/compare/2.4.0...2.4.1) (2025-12-19)

### Dependency updates

* **deps:** update dependency mypy to v1.19.1 ([#130](https://github.com/aequitas-aod/template-python-project-poetry/issues/130)) ([0f98e57](https://github.com/aequitas-aod/template-python-project-poetry/commit/0f98e5718e54dec894dff74a7e0578a6ff22111c))
* **deps:** update dependency ruff to v0.14.10 ([#131](https://github.com/aequitas-aod/template-python-project-poetry/issues/131)) ([07befd5](https://github.com/aequitas-aod/template-python-project-poetry/commit/07befd503668474f87b70ee19496fcd5c654cbd8))
* **deps:** update dependency ruff to v0.14.9 ([#128](https://github.com/aequitas-aod/template-python-project-poetry/issues/128)) ([f433dac](https://github.com/aequitas-aod/template-python-project-poetry/commit/f433dac716942f342ea5f4439fa27723e4d10d7f))
* **deps:** update node.js to 24.12 ([#126](https://github.com/aequitas-aod/template-python-project-poetry/issues/126)) ([f5569e1](https://github.com/aequitas-aod/template-python-project-poetry/commit/f5569e17b89bb5bedaa9fb1443cf5d3979bbf2bd))

### Bug Fixes

* update README and trigger release ([edc3b83](https://github.com/aequitas-aod/template-python-project-poetry/commit/edc3b83d3075a0b28064fdbca5cdadd81a0bd012))
* update testpypi repository ([a7ad894](https://github.com/aequitas-aod/template-python-project-poetry/commit/a7ad89490c9ee884571797ec163a52f0dbcbfa4d))

### Build and continuous integration

* **deps:** update actions/upload-artifact action to v6 ([#129](https://github.com/aequitas-aod/template-python-project-poetry/issues/129)) ([ad910a0](https://github.com/aequitas-aod/template-python-project-poetry/commit/ad910a01c325d72a28837028acec8f0b61e55489))

### General maintenance

* rename also project name in pyproject.toml ([caaf2c4](https://github.com/aequitas-aod/template-python-project-poetry/commit/caaf2c40784258f2a5c3498df922f0e0863b5268))
* update lock file ([df88518](https://github.com/aequitas-aod/template-python-project-poetry/commit/df88518fa403ffe72be3133e8494b52e15107594))
* update README ([6ab1904](https://github.com/aequitas-aod/template-python-project-poetry/commit/6ab1904041c1cee4c53ec22d0e7815ab67c4fe81))
* update README, remove poetry script ([473886a](https://github.com/aequitas-aod/template-python-project-poetry/commit/473886a11a4bfa233054764b104848356ac2e6ec))

### Refactoring

* **ci:** change pypi credentials with token ([cf9d36c](https://github.com/aequitas-aod/template-python-project-poetry/commit/cf9d36c2af7952a4b2922846de7f270d0e472279))

## [2.4.0](https://github.com/aequitas-aod/template-python-project-poetry/compare/2.3.1...2.4.0) (2025-12-10)

### Features

* add ruff for formatting and static checking ([c81c5db](https://github.com/aequitas-aod/template-python-project-poetry/commit/c81c5dbd0705701fe732fefaed87fac13f9a32bb))
* remove the need for release token in deploy ([e04cc4f](https://github.com/aequitas-aod/template-python-project-poetry/commit/e04cc4f19d23503773b6f389fac479c43b21a515))
* update poetry ([e0927d4](https://github.com/aequitas-aod/template-python-project-poetry/commit/e0927d47da111b00a4c24e3d3e7e2842d8d53173))
* update renovate config ([cff7985](https://github.com/aequitas-aod/template-python-project-poetry/commit/cff7985fd4f6fc6e3e60faf509fdb8d7069b8e7b))

### Dependency updates

* **deps:** update dependency coverage to v7.6.12 ([#94](https://github.com/aequitas-aod/template-python-project-poetry/issues/94)) ([8a685c3](https://github.com/aequitas-aod/template-python-project-poetry/commit/8a685c39475c7a326f3279ac2b4e2b42db36184f))
* **deps:** update dependency mypy to v1.19.0 ([#123](https://github.com/aequitas-aod/template-python-project-poetry/issues/123)) ([04274c1](https://github.com/aequitas-aod/template-python-project-poetry/commit/04274c102f13bc1ae4ab3e6ea04b9efa6862545d))
* **deps:** update dependency poethepoet to ^0.37.0 ([#91](https://github.com/aequitas-aod/template-python-project-poetry/issues/91)) ([da1203c](https://github.com/aequitas-aod/template-python-project-poetry/commit/da1203cc30881a683fc1ff1f7704e7c3409deba5))
* **deps:** update dependency poetry to v1.8.5 ([#95](https://github.com/aequitas-aod/template-python-project-poetry/issues/95)) ([3753438](https://github.com/aequitas-aod/template-python-project-poetry/commit/37534380d65f5eaa8c6bdd891a5ec9022c3ee180))
* **deps:** update dependency pytest to v8.3.5 ([#99](https://github.com/aequitas-aod/template-python-project-poetry/issues/99)) ([f8efc33](https://github.com/aequitas-aod/template-python-project-poetry/commit/f8efc33d5e99e7715d2db1caba12ce4afc038c5f))
* **deps:** update dependency semantic-release-preconfigured-conventional-commits to v1.1.148 ([#89](https://github.com/aequitas-aod/template-python-project-poetry/issues/89)) ([100f92e](https://github.com/aequitas-aod/template-python-project-poetry/commit/100f92e0ebfe777842eb4671706063c4b884285d))
* **deps:** update dependency semantic-release-preconfigured-conventional-commits to v1.1.157 ([#117](https://github.com/aequitas-aod/template-python-project-poetry/issues/117)) ([7f9f7f3](https://github.com/aequitas-aod/template-python-project-poetry/commit/7f9f7f318c5e976969058bbf3c4f5b48f97bb753))
* **deps:** update node.js to 22.21 ([#107](https://github.com/aequitas-aod/template-python-project-poetry/issues/107)) ([c538958](https://github.com/aequitas-aod/template-python-project-poetry/commit/c5389581a71236662007e48957d9a7a36224466b))
* **deps:** update node.js to v24 ([#119](https://github.com/aequitas-aod/template-python-project-poetry/issues/119)) ([36e1d22](https://github.com/aequitas-aod/template-python-project-poetry/commit/36e1d226acd1c003e01f1b44f3a8588e28e6f65e))

### Bug Fixes

* **ci:** remove branch option from semantic release command ([7a6dc99](https://github.com/aequitas-aod/template-python-project-poetry/commit/7a6dc99c778cc95f2cc97e65140b9494b15d1499))
* dry-run release if secrets are unset ([4b2f887](https://github.com/aequitas-aod/template-python-project-poetry/commit/4b2f8871d0f1815ccfe91593ee4cf6cecb36f3be))
* permissions in deploy job ([220f351](https://github.com/aequitas-aod/template-python-project-poetry/commit/220f351498cb339eda6870be17a333bdb4290bcd))
* restore GITHUB_TOKEN in ci for deployment ([f942dbd](https://github.com/aequitas-aod/template-python-project-poetry/commit/f942dbdc89a42fd69538c711f36143a42d5db380))
* typo in init script ([97f89f3](https://github.com/aequitas-aod/template-python-project-poetry/commit/97f89f3d0798d3659952bfe4b7b81ee62abf35f6))

### Build and continuous integration

* **deps:** update actions/checkout action to v5 ([4aa5fc1](https://github.com/aequitas-aod/template-python-project-poetry/commit/4aa5fc10dd356155c59feb24beda48727bcae30e))
* **deps:** update actions/checkout action to v6 ([#121](https://github.com/aequitas-aod/template-python-project-poetry/issues/121)) ([f9ff32a](https://github.com/aequitas-aod/template-python-project-poetry/commit/f9ff32aac2dea524346523e882af70da80102284))
* **deps:** update actions/setup-node action to v5 ([#112](https://github.com/aequitas-aod/template-python-project-poetry/issues/112)) ([0b5b5b9](https://github.com/aequitas-aod/template-python-project-poetry/commit/0b5b5b94de2d6a76b2cfa4805acbf9128ca2f87b))
* **deps:** update actions/setup-node action to v6 ([#114](https://github.com/aequitas-aod/template-python-project-poetry/issues/114)) ([dd06cf1](https://github.com/aequitas-aod/template-python-project-poetry/commit/dd06cf18f02859b1edf67d1ae4807cb431e63411))
* **deps:** update actions/setup-python action to v6 ([#113](https://github.com/aequitas-aod/template-python-project-poetry/issues/113)) ([964d1d8](https://github.com/aequitas-aod/template-python-project-poetry/commit/964d1d8dd202f24c2dfbc8f5eac97d19285b60c4))
* **deps:** update actions/upload-artifact action to v5 ([#120](https://github.com/aequitas-aod/template-python-project-poetry/issues/120)) ([88a11fc](https://github.com/aequitas-aod/template-python-project-poetry/commit/88a11fcf7cb349df930cdbb9184d3a944f243185))

### General maintenance

* add .gitattributes ([341e4e2](https://github.com/aequitas-aod/template-python-project-poetry/commit/341e4e20a081961387f3734fbc2f4246549e1af3))
* explain renovate in README.md ([2fef3b6](https://github.com/aequitas-aod/template-python-project-poetry/commit/2fef3b6e7cb3041e009462a365714b596ffadfeb))
* **release:** 2.4.0 [skip ci] ([6addcb7](https://github.com/aequitas-aod/template-python-project-poetry/commit/6addcb775fcfb3db5de5dcd3db326007acb5bf05)), closes [#94](https://github.com/aequitas-aod/template-python-project-poetry/issues/94) [#95](https://github.com/aequitas-aod/template-python-project-poetry/issues/95) [#99](https://github.com/aequitas-aod/template-python-project-poetry/issues/99) [#89](https://github.com/aequitas-aod/template-python-project-poetry/issues/89)
* update readme to mention init.yml ([8a2eedc](https://github.com/aequitas-aod/template-python-project-poetry/commit/8a2eedc5cec09c0b1f622dc5cb5a938394df92b9))

### Refactoring

* replace unittest with pytest ([07bfff4](https://github.com/aequitas-aod/template-python-project-poetry/commit/07bfff44fb937ac416558376f0b1d81ac30814a6))

## [2.4.0](https://github.com/aequitas-aod/template-python-project-poetry/compare/2.3.1...2.4.0) (2025-10-19)

### Features

* remove the need for release token in deploy ([e04cc4f](https://github.com/aequitas-aod/template-python-project-poetry/commit/e04cc4f19d23503773b6f389fac479c43b21a515))
* update poetry ([e0927d4](https://github.com/aequitas-aod/template-python-project-poetry/commit/e0927d47da111b00a4c24e3d3e7e2842d8d53173))
* update renovate config ([cff7985](https://github.com/aequitas-aod/template-python-project-poetry/commit/cff7985fd4f6fc6e3e60faf509fdb8d7069b8e7b))

### Dependency updates

* **deps:** update dependency coverage to v7.6.12 ([#94](https://github.com/aequitas-aod/template-python-project-poetry/issues/94)) ([8a685c3](https://github.com/aequitas-aod/template-python-project-poetry/commit/8a685c39475c7a326f3279ac2b4e2b42db36184f))
* **deps:** update dependency poetry to v1.8.5 ([#95](https://github.com/aequitas-aod/template-python-project-poetry/issues/95)) ([3753438](https://github.com/aequitas-aod/template-python-project-poetry/commit/37534380d65f5eaa8c6bdd891a5ec9022c3ee180))
* **deps:** update dependency pytest to v8.3.5 ([#99](https://github.com/aequitas-aod/template-python-project-poetry/issues/99)) ([f8efc33](https://github.com/aequitas-aod/template-python-project-poetry/commit/f8efc33d5e99e7715d2db1caba12ce4afc038c5f))
* **deps:** update dependency semantic-release-preconfigured-conventional-commits to v1.1.148 ([#89](https://github.com/aequitas-aod/template-python-project-poetry/issues/89)) ([100f92e](https://github.com/aequitas-aod/template-python-project-poetry/commit/100f92e0ebfe777842eb4671706063c4b884285d))

### Bug Fixes

* dry-run release if secrets are unset ([4b2f887](https://github.com/aequitas-aod/template-python-project-poetry/commit/4b2f8871d0f1815ccfe91593ee4cf6cecb36f3be))
* permissions in deploy job ([220f351](https://github.com/aequitas-aod/template-python-project-poetry/commit/220f351498cb339eda6870be17a333bdb4290bcd))
* restore GITHUB_TOKEN in ci for deployment ([f942dbd](https://github.com/aequitas-aod/template-python-project-poetry/commit/f942dbdc89a42fd69538c711f36143a42d5db380))
* typo in init script ([97f89f3](https://github.com/aequitas-aod/template-python-project-poetry/commit/97f89f3d0798d3659952bfe4b7b81ee62abf35f6))

### General maintenance

* update readme to mention init.yml ([8a2eedc](https://github.com/aequitas-aod/template-python-project-poetry/commit/8a2eedc5cec09c0b1f622dc5cb5a938394df92b9))

## [2.3.1](https://github.com/aequitas-aod/template-python-project-poetry/compare/2.3.0...2.3.1) (2025-10-18)

### Bug Fixes

* avoid changing deploy.yml upon template instantiation ([527c8fa](https://github.com/aequitas-aod/template-python-project-poetry/commit/527c8fa3bf9e7697e07bae77ea5225c532893601))

## [2.3.0](https://github.com/aequitas-aod/template-python-project-poetry/compare/2.2.0...2.3.0) (2025-10-18)

### Features

* change default assignee in renovate.json upon template usage ([a2aced1](https://github.com/aequitas-aod/template-python-project-poetry/commit/a2aced11bb5f0fe59741ac1cf5f932b6b9326101))
* dry-run release for first comit ([522d73e](https://github.com/aequitas-aod/template-python-project-poetry/commit/522d73ec3ed3dc2676c83c395cb1a558133c7827))

### Bug Fixes

* **ci:** avoid double workflow runs in renovate branches ([d35cd0a](https://github.com/aequitas-aod/template-python-project-poetry/commit/d35cd0af14ae427a702d6d59024069ced82dc773))

## [2.2.0](https://github.com/aequitas-aod/template-python-project-poetry/compare/2.1.7...2.2.0) (2025-10-18)

### Features

* **ci:** automate renaming of the project upon template instantiation ([92b5ccc](https://github.com/aequitas-aod/template-python-project-poetry/commit/92b5cccbd53b94c227e07da3c44cbbb7a3e825f2))

### Dependency updates

* **deps:** update dependency coverage to v7.6.0 ([c8e18d2](https://github.com/aequitas-aod/template-python-project-poetry/commit/c8e18d27b3717fab5a306f92e5cef46bbfe8112c))
* **deps:** update dependency coverage to v7.6.1 ([39241c5](https://github.com/aequitas-aod/template-python-project-poetry/commit/39241c5f705195e12f71176c4d9b5abfdc4340f1))
* **deps:** update dependency mypy to v1.11.0 ([c074706](https://github.com/aequitas-aod/template-python-project-poetry/commit/c07470647ca9a102896f61e3e997ad6f9e52cc36))
* **deps:** update dependency mypy to v1.11.1 ([1cf7087](https://github.com/aequitas-aod/template-python-project-poetry/commit/1cf70874502342227f8337955ed31ad478d04bb3))
* **deps:** update dependency mypy to v1.11.2 ([59ae46d](https://github.com/aequitas-aod/template-python-project-poetry/commit/59ae46d261ccea4b6bd091097b8ce6f506c14c8a))
* **deps:** update dependency mypy to v1.13.0 ([#97](https://github.com/aequitas-aod/template-python-project-poetry/issues/97)) ([d07b1fb](https://github.com/aequitas-aod/template-python-project-poetry/commit/d07b1fb95d3de8b1b62740e91b0e30a56a7a45ac))
* **deps:** update dependency poethepoet to ^0.28.0 ([12309fe](https://github.com/aequitas-aod/template-python-project-poetry/commit/12309fe6f715a084bc743701f8dfea20c3d4a425))
* **deps:** update dependency pytest to v8.3.1 ([b8b9269](https://github.com/aequitas-aod/template-python-project-poetry/commit/b8b926921892ebdad8c8cd091d1e1535af98f457))
* **deps:** update dependency pytest to v8.3.2 ([0a38ca0](https://github.com/aequitas-aod/template-python-project-poetry/commit/0a38ca072a39800e5d381d7b6957ef06565f90a6))
* **deps:** update dependency pytest to v8.3.3 ([b9b0b46](https://github.com/aequitas-aod/template-python-project-poetry/commit/b9b0b46a9cab6e08d2228cdb5cb3394a5e10d36e))
* **deps:** update dependency semantic-release-preconfigured-conventional-commits to v1.1.101 ([948ced1](https://github.com/aequitas-aod/template-python-project-poetry/commit/948ced132b873882d0fa41a518816a161ce1fa1e))
* **deps:** update dependency semantic-release-preconfigured-conventional-commits to v1.1.102 ([0dd3a31](https://github.com/aequitas-aod/template-python-project-poetry/commit/0dd3a311121f4a6b3edafcd3ef4d4053d9724dd3))
* **deps:** update dependency semantic-release-preconfigured-conventional-commits to v1.1.103 ([bc4ebf0](https://github.com/aequitas-aod/template-python-project-poetry/commit/bc4ebf0dab5c9a05e457b7aba6f7aef4f0c44bd1))
* **deps:** update dependency semantic-release-preconfigured-conventional-commits to v1.1.104 ([4516f19](https://github.com/aequitas-aod/template-python-project-poetry/commit/4516f19200fd485be7f40ea83bd7d4a891624bc5))
* **deps:** update dependency semantic-release-preconfigured-conventional-commits to v1.1.105 ([e00b988](https://github.com/aequitas-aod/template-python-project-poetry/commit/e00b988bad39ff8f3b056d0d4732794bace329ea))
* **deps:** update dependency semantic-release-preconfigured-conventional-commits to v1.1.91 ([0f31cdc](https://github.com/aequitas-aod/template-python-project-poetry/commit/0f31cdcfb5288420a8bd621111abbb7113b2a0fc))
* **deps:** update dependency semantic-release-preconfigured-conventional-commits to v1.1.92 ([f27a563](https://github.com/aequitas-aod/template-python-project-poetry/commit/f27a5638cd1064a14e66b17106ec2ad554791b7c))
* **deps:** update dependency semantic-release-preconfigured-conventional-commits to v1.1.93 ([a845b00](https://github.com/aequitas-aod/template-python-project-poetry/commit/a845b00c817ce3a9530b100d2cc2879d56a8ec1d))
* **deps:** update dependency semantic-release-preconfigured-conventional-commits to v1.1.94 ([c83cd26](https://github.com/aequitas-aod/template-python-project-poetry/commit/c83cd26736eabca651769311c1e2d5bcdb7d93f7))
* **deps:** update dependency semantic-release-preconfigured-conventional-commits to v1.1.95 ([663ba6c](https://github.com/aequitas-aod/template-python-project-poetry/commit/663ba6ce2976683f792dc2c475a63a680187168f))
* **deps:** update dependency semantic-release-preconfigured-conventional-commits to v1.1.96 ([16ec1e2](https://github.com/aequitas-aod/template-python-project-poetry/commit/16ec1e2d6d717440f2e6573f39e710fa7e7141c7))
* **deps:** update dependency semantic-release-preconfigured-conventional-commits to v1.1.97 ([5df66c6](https://github.com/aequitas-aod/template-python-project-poetry/commit/5df66c6f80894ed0ce62ef07563efe9a4983b199))
* **deps:** update dependency semantic-release-preconfigured-conventional-commits to v1.1.98 ([93d7116](https://github.com/aequitas-aod/template-python-project-poetry/commit/93d711610b05d4776e88ea819f8ce74c8b13f507))
* **deps:** update dependency semantic-release-preconfigured-conventional-commits to v1.1.99 ([8932671](https://github.com/aequitas-aod/template-python-project-poetry/commit/893267187b02a7806b5ad6cffaeb0e46f9c4a5e4))
* **deps:** update node.js to 20.16 ([ad9ed47](https://github.com/aequitas-aod/template-python-project-poetry/commit/ad9ed47d495f01ae3afe41df849c3d7a00b2879d))
* **deps:** update node.js to 20.17 ([f7404b1](https://github.com/aequitas-aod/template-python-project-poetry/commit/f7404b12361181ebd25c2befbe939d6837fa1a42))
* **deps:** update npm to v10.8.2 ([81a3216](https://github.com/aequitas-aod/template-python-project-poetry/commit/81a321619b7f9826fd558ae243d401b74656108e))
* **deps:** update npm to v10.8.3 ([3c3409d](https://github.com/aequitas-aod/template-python-project-poetry/commit/3c3409dc8268cf919789778b901331da872b40c5))

### Bug Fixes

* **deps:** remove useless dependencies from scikitlearn and pandas ([eabdd5e](https://github.com/aequitas-aod/template-python-project-poetry/commit/eabdd5e6b506add1eca5076a2dd919e588e5700d))
* **deps:** update dependency scikit-learn to v1.5.2 ([2437ea0](https://github.com/aequitas-aod/template-python-project-poetry/commit/2437ea0f4b004c68a7f4a7ca5e9e661e659713a8))

### General maintenance

* **release:** 2.1.8 [skip ci] ([12c8451](https://github.com/aequitas-aod/template-python-project-poetry/commit/12c84510d8083348a221f4d160f6bb249ee8dd23))
* **vscode:** fix vscode configuration looking for tests ([457b3b4](https://github.com/aequitas-aod/template-python-project-poetry/commit/457b3b484234da285088cc81edcbf5d6d23f5053))

## [2.1.8](https://github.com/aequitas-aod/template-python-project-poetry/compare/2.1.7...2.1.8) (2024-09-11)

### Dependency updates

* **deps:** update dependency coverage to v7.6.0 ([c8e18d2](https://github.com/aequitas-aod/template-python-project-poetry/commit/c8e18d27b3717fab5a306f92e5cef46bbfe8112c))
* **deps:** update dependency coverage to v7.6.1 ([39241c5](https://github.com/aequitas-aod/template-python-project-poetry/commit/39241c5f705195e12f71176c4d9b5abfdc4340f1))
* **deps:** update dependency mypy to v1.11.0 ([c074706](https://github.com/aequitas-aod/template-python-project-poetry/commit/c07470647ca9a102896f61e3e997ad6f9e52cc36))
* **deps:** update dependency mypy to v1.11.1 ([1cf7087](https://github.com/aequitas-aod/template-python-project-poetry/commit/1cf70874502342227f8337955ed31ad478d04bb3))
* **deps:** update dependency mypy to v1.11.2 ([59ae46d](https://github.com/aequitas-aod/template-python-project-poetry/commit/59ae46d261ccea4b6bd091097b8ce6f506c14c8a))
* **deps:** update dependency poethepoet to ^0.28.0 ([12309fe](https://github.com/aequitas-aod/template-python-project-poetry/commit/12309fe6f715a084bc743701f8dfea20c3d4a425))
* **deps:** update dependency pytest to v8.3.1 ([b8b9269](https://github.com/aequitas-aod/template-python-project-poetry/commit/b8b926921892ebdad8c8cd091d1e1535af98f457))
* **deps:** update dependency pytest to v8.3.2 ([0a38ca0](https://github.com/aequitas-aod/template-python-project-poetry/commit/0a38ca072a39800e5d381d7b6957ef06565f90a6))
* **deps:** update dependency pytest to v8.3.3 ([b9b0b46](https://github.com/aequitas-aod/template-python-project-poetry/commit/b9b0b46a9cab6e08d2228cdb5cb3394a5e10d36e))
* **deps:** update dependency semantic-release-preconfigured-conventional-commits to v1.1.101 ([948ced1](https://github.com/aequitas-aod/template-python-project-poetry/commit/948ced132b873882d0fa41a518816a161ce1fa1e))
* **deps:** update dependency semantic-release-preconfigured-conventional-commits to v1.1.102 ([0dd3a31](https://github.com/aequitas-aod/template-python-project-poetry/commit/0dd3a311121f4a6b3edafcd3ef4d4053d9724dd3))
* **deps:** update dependency semantic-release-preconfigured-conventional-commits to v1.1.103 ([bc4ebf0](https://github.com/aequitas-aod/template-python-project-poetry/commit/bc4ebf0dab5c9a05e457b7aba6f7aef4f0c44bd1))
* **deps:** update dependency semantic-release-preconfigured-conventional-commits to v1.1.104 ([4516f19](https://github.com/aequitas-aod/template-python-project-poetry/commit/4516f19200fd485be7f40ea83bd7d4a891624bc5))
* **deps:** update dependency semantic-release-preconfigured-conventional-commits to v1.1.105 ([e00b988](https://github.com/aequitas-aod/template-python-project-poetry/commit/e00b988bad39ff8f3b056d0d4732794bace329ea))
* **deps:** update dependency semantic-release-preconfigured-conventional-commits to v1.1.91 ([0f31cdc](https://github.com/aequitas-aod/template-python-project-poetry/commit/0f31cdcfb5288420a8bd621111abbb7113b2a0fc))
* **deps:** update dependency semantic-release-preconfigured-conventional-commits to v1.1.92 ([f27a563](https://github.com/aequitas-aod/template-python-project-poetry/commit/f27a5638cd1064a14e66b17106ec2ad554791b7c))
* **deps:** update dependency semantic-release-preconfigured-conventional-commits to v1.1.93 ([a845b00](https://github.com/aequitas-aod/template-python-project-poetry/commit/a845b00c817ce3a9530b100d2cc2879d56a8ec1d))
* **deps:** update dependency semantic-release-preconfigured-conventional-commits to v1.1.94 ([c83cd26](https://github.com/aequitas-aod/template-python-project-poetry/commit/c83cd26736eabca651769311c1e2d5bcdb7d93f7))
* **deps:** update dependency semantic-release-preconfigured-conventional-commits to v1.1.95 ([663ba6c](https://github.com/aequitas-aod/template-python-project-poetry/commit/663ba6ce2976683f792dc2c475a63a680187168f))
* **deps:** update dependency semantic-release-preconfigured-conventional-commits to v1.1.96 ([16ec1e2](https://github.com/aequitas-aod/template-python-project-poetry/commit/16ec1e2d6d717440f2e6573f39e710fa7e7141c7))
* **deps:** update dependency semantic-release-preconfigured-conventional-commits to v1.1.97 ([5df66c6](https://github.com/aequitas-aod/template-python-project-poetry/commit/5df66c6f80894ed0ce62ef07563efe9a4983b199))
* **deps:** update dependency semantic-release-preconfigured-conventional-commits to v1.1.98 ([93d7116](https://github.com/aequitas-aod/template-python-project-poetry/commit/93d711610b05d4776e88ea819f8ce74c8b13f507))
* **deps:** update dependency semantic-release-preconfigured-conventional-commits to v1.1.99 ([8932671](https://github.com/aequitas-aod/template-python-project-poetry/commit/893267187b02a7806b5ad6cffaeb0e46f9c4a5e4))
* **deps:** update node.js to 20.16 ([ad9ed47](https://github.com/aequitas-aod/template-python-project-poetry/commit/ad9ed47d495f01ae3afe41df849c3d7a00b2879d))
* **deps:** update node.js to 20.17 ([f7404b1](https://github.com/aequitas-aod/template-python-project-poetry/commit/f7404b12361181ebd25c2befbe939d6837fa1a42))
* **deps:** update npm to v10.8.2 ([81a3216](https://github.com/aequitas-aod/template-python-project-poetry/commit/81a321619b7f9826fd558ae243d401b74656108e))
* **deps:** update npm to v10.8.3 ([3c3409d](https://github.com/aequitas-aod/template-python-project-poetry/commit/3c3409dc8268cf919789778b901331da872b40c5))

### Bug Fixes

* **deps:** update dependency scikit-learn to v1.5.2 ([2437ea0](https://github.com/aequitas-aod/template-python-project-poetry/commit/2437ea0f4b004c68a7f4a7ca5e9e661e659713a8))

## [2.1.7](https://github.com/aequitas-aod/template-python-project-poetry/compare/2.1.6...2.1.7) (2024-07-10)

### Dependency updates

* **deps:** update dependency semantic-release-preconfigured-conventional-commits to v1.1.89 ([ef9d882](https://github.com/aequitas-aod/template-python-project-poetry/commit/ef9d8829ac28eb125a332aa3d57791e10d3caf69))
* **deps:** update dependency semantic-release-preconfigured-conventional-commits to v1.1.90 ([1dab7eb](https://github.com/aequitas-aod/template-python-project-poetry/commit/1dab7eb84b1619cf0d4682a4fd6eea9d5925df91))

### Bug Fixes

* move automl-llm folder upon renaming ([dcba4ab](https://github.com/aequitas-aod/template-python-project-poetry/commit/dcba4ab25a0a0c619ee8afacad9ff01a6f5bcfd6))

## [2.1.6](https://github.com/aequitas-aod/template-python-project-poetry/compare/2.1.5...2.1.6) (2024-07-03)


### Bug Fixes

* **ci:** test release on all branches (use cmdline) ([db73c87](https://github.com/aequitas-aod/template-python-project-poetry/commit/db73c87689116f79322da3257813ea3327ccb922))

## [2.1.5](https://github.com/aequitas-aod/template-python-project-poetry/compare/2.1.4...2.1.5) (2024-07-03)


### Bug Fixes

* **ci:** test release on all branches ([f8ea880](https://github.com/aequitas-aod/template-python-project-poetry/commit/f8ea8807885441d52db8891f65e702e592ad412f))

## [2.1.4](https://github.com/aequitas-aod/template-python-project-poetry/compare/2.1.3...2.1.4) (2024-07-03)


### Dependency updates

* **deps:** update dependency semantic-release-preconfigured-conventional-commits to v1.1.86 ([4bcc762](https://github.com/aequitas-aod/template-python-project-poetry/commit/4bcc7626f5b8643a7381b0c9c71b3d7a20a91ed1))


### Bug Fixes

* **deps:** update dependency scikit-learn to v1.5.1 ([edd9a84](https://github.com/aequitas-aod/template-python-project-poetry/commit/edd9a8415a5caaa2a64038a15c73cb4715e95765))


### Revert previous changes

* Revert "chore(deps): update dependency semantic-release-preconfigured-convent…" ([a51ce70](https://github.com/aequitas-aod/template-python-project-poetry/commit/a51ce70691409b04ea0948bb5cda8c562486b323))


### General maintenance

* improve readme ([9d62046](https://github.com/aequitas-aod/template-python-project-poetry/commit/9d620463be3b80a0da0a575bacbf9c3cce943982))

## [2.1.3](https://github.com/aequitas-aod/template-python-project-poetry/compare/2.1.2...2.1.3) (2024-07-03)


### Bug Fixes

* split prepare and publish phases in semantic-release ([d01a515](https://github.com/aequitas-aod/template-python-project-poetry/commit/d01a515d42e7666e13feea1489e934e84d0c06bd))

## [2.1.2](https://github.com/aequitas-aod/template-python-project-poetry/compare/2.1.1...2.1.2) (2024-07-03)


### Bug Fixes

* **ci:** pypi credentials ([42aa559](https://github.com/aequitas-aod/template-python-project-poetry/commit/42aa559de022c8a9381779d47750428195f708d8))

## [2.1.1](https://github.com/aequitas-aod/template-python-project-poetry/compare/2.1.0...2.1.1) (2024-07-03)


### Bug Fixes

* rename step in ci just to trigger new release ([d7f1d15](https://github.com/aequitas-aod/template-python-project-poetry/commit/d7f1d15e0bb590431099752e0b8529d9934df062))

## [2.1.0](https://github.com/aequitas-aod/template-python-project-poetry/compare/2.0.0...2.1.0) (2024-07-03)


### Features

* **ci:** add preliminary static checks and coverage before testing ([8566322](https://github.com/aequitas-aod/template-python-project-poetry/commit/8566322028fcfa92188be58627b13362dfa9b106))

## [2.0.0](https://github.com/aequitas-aod/template-python-project-poetry/compare/1.0.1...2.0.0) (2024-07-03)


### ⚠ BREAKING CHANGES

* use poetry instead of setup.py

### Features

* use poetry instead of setup.py ([f8bcfa1](https://github.com/aequitas-aod/template-python-project-poetry/commit/f8bcfa14bf7992b16e77929b6f5112dd7f977383))


### Dependency updates

* **deps:** update dependency pandas to v2.2.1 ([be273ce](https://github.com/aequitas-aod/template-python-project-poetry/commit/be273ce0d591432389c5da7d8bee343079db4871))
* **deps:** update dependency pandas to v2.2.2 ([dd4507a](https://github.com/aequitas-aod/template-python-project-poetry/commit/dd4507a5ae73bd2019729786dcbadb051a024049))
* **deps:** update dependency scikit-learn to v1.4.1.post1 ([d24ef8b](https://github.com/aequitas-aod/template-python-project-poetry/commit/d24ef8bc4bedf055630f95eb04a6db1833b3d4d7))
* **deps:** update dependency scikit-learn to v1.4.2 ([613452a](https://github.com/aequitas-aod/template-python-project-poetry/commit/613452a825e12cb0f5f2962e6ba5dd22dadf058a))
* **deps:** update dependency scikit-learn to v1.5.0 ([6d42082](https://github.com/aequitas-aod/template-python-project-poetry/commit/6d4208275a45736a4d4161dc88324aa3f6ca2b86))
* **deps:** update dependency semantic-release-preconfigured-conventional-commits to v1.1.86 ([847ef5a](https://github.com/aequitas-aod/template-python-project-poetry/commit/847ef5a1ee00d72a7eb330d7f089c3130ced26ff))
* **deps:** update node.js to 20.12 ([2ffe13a](https://github.com/aequitas-aod/template-python-project-poetry/commit/2ffe13aeba2daea05735531926badafc0c6e78e2))
* **deps:** update node.js to 20.13 ([65182e8](https://github.com/aequitas-aod/template-python-project-poetry/commit/65182e88da58a8ad06bffb712572e388309767c2))
* **deps:** update node.js to 20.14 ([a132a42](https://github.com/aequitas-aod/template-python-project-poetry/commit/a132a42cf67d01fdf79778ffde824fb3300527ac))
* **deps:** update node.js to 20.15 ([76a552b](https://github.com/aequitas-aod/template-python-project-poetry/commit/76a552bc42965f6ee23754065b2673403b26a91c))


### General maintenance

* **release:** simplify renovate conf ([23da9b6](https://github.com/aequitas-aod/template-python-project-poetry/commit/23da9b61d38adbe974c53240f05fb71ea685fb03))

## [1.0.1](https://github.com/aequitas-aod/template-python-project/compare/1.0.0...1.0.1) (2024-02-02)


### Dependency updates

* **deps:** update dependency pandas to v2.1.2 ([8fe0d36](https://github.com/aequitas-aod/template-python-project/commit/8fe0d36a83c74ff23c059735a69f91ebef4904f3))
* **deps:** update dependency pandas to v2.1.3 ([27eb2b6](https://github.com/aequitas-aod/template-python-project/commit/27eb2b6e5cd7bdac497412095bdd71ee8bc9f12c))
* **deps:** update dependency pandas to v2.1.4 ([cd2b1d4](https://github.com/aequitas-aod/template-python-project/commit/cd2b1d4c3d22d352a89d57794402df9c8779b5c6))
* **deps:** update dependency pandas to v2.2.0 ([b8df6b1](https://github.com/aequitas-aod/template-python-project/commit/b8df6b14bdb94a9e4d290a67ae9090227da61d29))
* **deps:** update dependency scikit-learn to v1.3.2 ([fe7eea2](https://github.com/aequitas-aod/template-python-project/commit/fe7eea22d078a77ed77477a78785c387953888f8))
* **deps:** update dependency scikit-learn to v1.4.0 ([85de0ed](https://github.com/aequitas-aod/template-python-project/commit/85de0ed24d38277ea86a7ac71781631c097e8aaf))
* **deps:** update dependency semantic-release-preconfigured-conventional-commits to v1.1.69 ([fa07343](https://github.com/aequitas-aod/template-python-project/commit/fa07343c199db9cf3a0784abdf1858983f80392c))
* **deps:** update dependency semantic-release-preconfigured-conventional-commits to v1.1.70 ([2f7eb9b](https://github.com/aequitas-aod/template-python-project/commit/2f7eb9b20f5fc44a154c18cdf4ddb413da9819fc))
* **deps:** update dependency semantic-release-preconfigured-conventional-commits to v1.1.71 ([e7efd4f](https://github.com/aequitas-aod/template-python-project/commit/e7efd4f39ac7396621ae9a7182c42975d8756476))
* **deps:** update dependency semantic-release-preconfigured-conventional-commits to v1.1.72 ([17cd38c](https://github.com/aequitas-aod/template-python-project/commit/17cd38c5f6969e7be37be61087c63047d462e00a))
* **deps:** update dependency semantic-release-preconfigured-conventional-commits to v1.1.73 ([ceba297](https://github.com/aequitas-aod/template-python-project/commit/ceba297fb66930fa41cfcc36794f37b16d041c60))
* **deps:** update dependency semantic-release-preconfigured-conventional-commits to v1.1.74 ([a7c030d](https://github.com/aequitas-aod/template-python-project/commit/a7c030de41394700cc0cec89358e59a3709377b2))
* **deps:** update dependency semantic-release-preconfigured-conventional-commits to v1.1.75 ([21e6b9a](https://github.com/aequitas-aod/template-python-project/commit/21e6b9af441d069af6c13ccbd55bad63d4a9a841))
* **deps:** update dependency semantic-release-preconfigured-conventional-commits to v1.1.76 ([fcf51ce](https://github.com/aequitas-aod/template-python-project/commit/fcf51ce4d1048739ca4933ef56cefe69b1f25bb9))
* **deps:** update dependency semantic-release-preconfigured-conventional-commits to v1.1.77 ([24c1ad5](https://github.com/aequitas-aod/template-python-project/commit/24c1ad5c7c2a6df6f8519c4bd3bfd9892cac7bdd))
* **deps:** update dependency semantic-release-preconfigured-conventional-commits to v1.1.78 ([4881854](https://github.com/aequitas-aod/template-python-project/commit/488185409ad1263b83838fba5b07136517c9fe52))
* **deps:** update dependency semantic-release-preconfigured-conventional-commits to v1.1.79 ([b09d25f](https://github.com/aequitas-aod/template-python-project/commit/b09d25f30d81f9bc22cee76f3cf2fe72e1589e62))
* **deps:** update dependency semantic-release-preconfigured-conventional-commits to v1.1.80 ([d9e55c5](https://github.com/aequitas-aod/template-python-project/commit/d9e55c51fa21cf880450cbeee619cca167e55cec))
* **deps:** update dependency semantic-release-preconfigured-conventional-commits to v1.1.81 ([d2608f8](https://github.com/aequitas-aod/template-python-project/commit/d2608f87dc1bb2554c4db8bd8fe57fb75512efdb))
* **deps:** update dependency semantic-release-preconfigured-conventional-commits to v1.1.82 ([22b0719](https://github.com/aequitas-aod/template-python-project/commit/22b0719f19296441890e9e6f122df45efd5e095e))
* **deps:** update dependency semantic-release-preconfigured-conventional-commits to v1.1.83 ([8f2ec20](https://github.com/aequitas-aod/template-python-project/commit/8f2ec20935428b99b28d412040689e56fa30a07e))
* **deps:** update dependency semantic-release-preconfigured-conventional-commits to v1.1.84 ([cb92e70](https://github.com/aequitas-aod/template-python-project/commit/cb92e703568dbf402c51434c510fd97cb6946c52))
* **deps:** update dependency semantic-release-preconfigured-conventional-commits to v1.1.85 ([f05865d](https://github.com/aequitas-aod/template-python-project/commit/f05865d98e638d8c7192bfdb360898b7152400f9))
* **deps:** update node.js to 20.10 ([f393b2a](https://github.com/aequitas-aod/template-python-project/commit/f393b2a2fb2d3aa98b5c5a969ef4df442d5c79de))
* **deps:** update node.js to 20.11 ([63410da](https://github.com/aequitas-aod/template-python-project/commit/63410da68d5122d155caac39b6f99de19d619825))
* **deps:** update node.js to 20.9 ([d107ca2](https://github.com/aequitas-aod/template-python-project/commit/d107ca20dd8414ef39ab6b6b95740b3ae2c75f16))
* **deps:** update node.js to v20 ([61b7e25](https://github.com/aequitas-aod/template-python-project/commit/61b7e250a9afe02465f435c6b709b2fcc872e338))
* **deps:** update python docker tag to v3.12.0 ([b123d48](https://github.com/aequitas-aod/template-python-project/commit/b123d4847e25cc94e86faf1f5ec37a4e0b54e46d))
* **deps:** update python docker tag to v3.12.1 ([ac01a01](https://github.com/aequitas-aod/template-python-project/commit/ac01a014b54008d5c7af4916880413ba864f9a33))


### Bug Fixes

* **release:** include .python-version in MANIFEST.in ([9d794fa](https://github.com/aequitas-aod/template-python-project/commit/9d794faac19b032c5a0f149c3e5e44df018db17b))


### Build and continuous integration

* **deps:** update actions/setup-node action to v4 ([45c9acd](https://github.com/aequitas-aod/template-python-project/commit/45c9acdfed764240e4e150e65a4507205537a16a))
* **deps:** update actions/setup-python action to v5 ([66921e3](https://github.com/aequitas-aod/template-python-project/commit/66921e3580f3223689adf1665a323befbd9b3272))

## 1.0.0 (2023-10-12)


### Features

* add renaming script ([ed33dbc](https://github.com/aequitas-aod/template-python-project/commit/ed33dbc03a68a605e6df7a9465c6985ec9d1e130))
* first commit ([6ddc082](https://github.com/aequitas-aod/template-python-project/commit/6ddc08296facfe64fe912fcd00a255adb2806193))


### Dependency updates

* **deps:** node 18.18 ([73eec49](https://github.com/aequitas-aod/template-python-project/commit/73eec49c6fc53fe3158a0b94be99dcaf6eb328eb))
* **deps:** update dependencies ([0be2f8d](https://github.com/aequitas-aod/template-python-project/commit/0be2f8deb9b8218e509ea0926ceeb78a7a2baa70))
* **deps:** update python docker tag to v3.11.6 ([199ffe6](https://github.com/aequitas-aod/template-python-project/commit/199ffe6a498c6b26d358d97ac2ef7046da68e268))


### Bug Fixes

* readme ([f12fb0b](https://github.com/aequitas-aod/template-python-project/commit/f12fb0b17c08a18a7e145199234dc38d43fd0ddb))
* release workflow ([9c84ec1](https://github.com/aequitas-aod/template-python-project/commit/9c84ec1497a1f8c6c438a248107746df0fa7c612))
* renovate configuration ([0db8978](https://github.com/aequitas-aod/template-python-project/commit/0db89788ad8bef935fa97b77e7fa05aca749da28))


### Build and continuous integration

* enable semantic release ([648759b](https://github.com/aequitas-aod/template-python-project/commit/648759ba41fda0cad343493709a57bcb908f7229))
* fix release by installing correct version of node ([d809f17](https://github.com/aequitas-aod/template-python-project/commit/d809f17fc96c7295e0ec526161a56f558d49aa47))


### General maintenance

* **ci:** dry run release on testpypi for template project ([b90a25a](https://github.com/aequitas-aod/template-python-project/commit/b90a25a0f1f439e0bf548eec0bfae21b1f8c44b1))
* **ci:** use jq to parse package.json ([66af494](https://github.com/aequitas-aod/template-python-project/commit/66af494bc406d4b9b649153f910016cceb1b63ce))
* initial todo-list ([154e024](https://github.com/aequitas-aod/template-python-project/commit/154e024ac1bb8a1f1c99826ab2ed6a28e703a513))
* remove useless Dockerfile ([0272af7](https://github.com/aequitas-aod/template-python-project/commit/0272af71647e254f7622d38ace6000f0cbc7f17d))
* write some instructions ([7da9554](https://github.com/aequitas-aod/template-python-project/commit/7da9554a6e458c5fc253a222b295fbeb6a7862ec))
