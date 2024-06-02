from typing import List, Type


class PistonRuntime(Type):
    language: str
    version: str
    aliases: List[str]


class PistonExecute(Type):
    language: str
    run: "PistonOutput"


class PistonOutput(Type):
    stdout: str
    stderr: str
    code: int
    output: str
