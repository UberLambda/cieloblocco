import os
import builtins
from typing import Any, Callable, Generic, TypeVar, Optional, Dict

import dotenv
dotenv.load_dotenv()

all_vars: Dict[str, 'Var[T]'] = {}
_var_t = TypeVar('T')


class VarError(Exception):
    def __init__(self, what: str, var: 'Var[T]'):
        super().__init__(what)
        self.what: str = what
        self.var: 'Var[T]' = var

    def __str__(self) -> str:
        return f"{self.what}\n{self.var}"


class Var(Generic[_var_t]):
    def __init__(self,
                 key: str,
                 default: Optional[_var_t] = None,
                 type: Optional[Callable[[str], _var_t]] = None,
                 optional: bool = True,
                 help: str = None):
        self.key: str = key
        self.help: str = help
        self.default: Optional[_var_t] = default
        self.value: Optional[_var_t] = default
        self.type: Optional[Callable[[str], _var_t]] = type or builtins.type(default)
        self.optional: bool = optional
        self.sync()
        all_vars[self.key] = self

    def sync(self):
        self.value: Optional[_var_t] = os.getenv(self.key)
        if self.value is not None:
            self.value = self.type(self.value) if self.type is not None else self.value
        elif self.optional:
            self.value = self.default
        else:
            raise VarError(f"${{{self.key}}} not set", self)

    def __str__(self) -> str:
        doc = f"{self.key}"
        extras = ["optional"] * self.optional
        extras += [f"default = {self.default}"] * bool(self.default)
        extras += [f"type = {self.type.__name__}"] * bool(self.type)
        doc += f" [{','.join(extras)}]" if extras else ""
        if self.help:
            doc += f"\n\t{self.help}"
        return doc

    def __repr__(self) -> str:
        return f'Var({self.key}={repr(self.value)})'

    def __get__(self, instance: 'Var', owner: Any) -> Optional[_var_t]:
        return self.value
