import resources
import yaml
from z3 import Int, Not, Solver, sat, Or, And, Bool, Implies, AtMost
from functools import cache
from dataclasses import dataclass


FILE_SPEC = resources.get_resource_path("automl-specification.yml")
with open(FILE_SPEC, "r") as f:
    SPEC = yaml.safe_load(f)


@cache
def candidates_of_step(step):
    candidates = []
    for candidate in SPEC["pipeline"]["steps"][step]["candidates"]:
        if len(candidate) != 1:
            raise ValueError(f"Candidate {candidate} for step {step} has more than one component, which is not supported yet.")
        for k in candidate:
            candidates.append(k)
    return tuple(candidates)


class Variables:
    def __init__(self):
        self.__variables = dict()

    def add(self, variable):
        self.__variables[str(variable)] = variable

    def __getitem__(self, key):
        return self.__variables[key]
    
    def __iter__(self):
        return iter(self.__variables.values())
    
    def __items__(self):
        return self.__variables.items()
    
    def __len__(self):
        return len(self.__variables)
    
    def int(self, name):
        variable = Int(name)
        self.add(variable)
        return variable
    
    def bool(self, name):
        variable = Bool(name)
        self.add(variable)
        return variable
    
    def with_name(self, name):
        for variable_name, variable in self.__variables.items():
            if variable_name.startswith(name):
                yield variable


@dataclass
class PartialOrderConstraint:
    before: str
    after: str

    def add_to(self, constraints: Solver, using: Variables):
        before = using[f"index_of_step_{self.before}"]
        after = using[f"index_of_step_{self.after}"]
        constraints.add(before < after)


def partial_ordering():
    for item in SPEC["pipeline"]["partial_ordering"]:
        yield PartialOrderConstraint(before=item["before"], after=item["after"])


@dataclass
class Constraint:
    condition: dict[str, str | dict[str, str]]
    forbid: list[str | dict[str, str]]
    require: list[str | dict[str, str]]

    @classmethod
    def __parse_constraint(cls, item: str | dict[str, str], using: Variables, positive: bool = True):
        if isinstance(item, str):
            return using[f"do_step_{item}"] == positive
        elif isinstance(item, dict):
            conditions = []
            for step, candidate in item.items():
                condition = using[f"do_step_{step}"] == True
                if len(candidate) == 1 and isinstance(candidate, str):
                    if positive:
                        condition = And(condition, using[f"implement_{step}_as_{candidate}"] == True)
                    else:
                        condition = Implies(condition, using[f"implement_{step}_as_{candidate}"] == False)
                conditions.append(condition)
            if len(conditions) == 1:
                return conditions[0]
            else:
                return Or(*conditions)
        elif isinstance(item, list):
            conditions = [cls.__parse_constraint(i, using, positive=positive) for i in item]
            if len(conditions) == 1:
                return conditions[0]
            else:
                return And(*conditions)
        else:
            raise ValueError(f"Invalid constraint item: {item}")

    def add_to(self, constraints: Solver, using: Variables):
        precondition = self.__parse_constraint(self.condition, using)
        effects = []
        if self.forbid:
            forbid_effect = self.__parse_constraint(self.forbid, using, positive=False)
            effects.append(forbid_effect)
        if self.require:
            require_effect = self.__parse_constraint(self.require, using, positive=True)
            effects.append(require_effect)
        if len(effects) == 0:
            raise ValueError(f"Constraint {self} has no effects.")
        elif len(effects) == 1:
            constraints.add(Implies(precondition, effects[0]))
        else:
            constraints.add(Implies(precondition, And(*effects)))


def constraints():
    for item in SPEC["pipeline"]["constraints"]:
        yield Constraint(condition=item["if"], forbid=item.get("forbid", []), require=item.get("require", []))


if __name__ == "__main__":
    steps = tuple(SPEC["pipeline"]["steps"].keys())
    solver = Solver()
    variables = Variables()
    for step in steps:
        step_index = variables.int(f"index_of_step_{step}")
        solver.add(step_index in range(len(steps)))
        do_step = variables.bool(f"do_step_{step}")
        # constraints.add(do_step >= 0, do_step <= 1)
        for candidate in candidates_of_step(step):
            implement_step_as = variables.bool(f"implement_{step}_as_{candidate}")
            # constraints.add(implement_step_as >= 0, implement_step_as <= 1)
        # constraints.add(sum(variables.with_name(f"implement_{step}_as_")) == 1)
        solver.add(AtMost(*variables.with_name(f"implement_{step}_as_"), 1))
    for constraint in partial_ordering():
        constraint.add_to(solver, using=variables)
    for constraint in constraints():
        constraint.add_to(solver, using=variables)
    
    print(solver)
    input("---")
    while solver.check() == sat:
        model = solver.model()
        print(model)
        input("---")
    print("No more solutions.")