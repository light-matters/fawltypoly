"""Compile the scalar arithmetic whitelist to a Python function without eval/exec.

Only constructed AST nodes are compiled; input forms are never Python source.
The generated function can access its arguments, captured constants, and the
explicit numerical operators below. This avoids interpreting an AST per vertex.
"""

import ast
import cmath
import math
import numbers
import types
from collections.abc import Mapping

from basilisp.lang.interfaces import ISeq
from basilisp.lang.symbol import Symbol


def _conjugate(z):
    return complex(z).conjugate()


def _real(z):
    return complex(z).real


def _imag(z):
    return complex(z).imag


OPERATORS = {
    "expt": (2, pow), "pow": (2, pow), "**": (2, pow), "Power": (2, pow),
    "complex": (2, complex), "Complex": (2, complex),
}
for aliases, fn in [
    (("sin", "Sin"), cmath.sin), (("cos", "Cos"), cmath.cos),
    (("tan", "Tan"), cmath.tan), (("asin", "ArcSin"), cmath.asin),
    (("acos", "ArcCos"), cmath.acos), (("atan", "ArcTan"), cmath.atan),
    (("exp", "Exp"), cmath.exp), (("log", "Log"), cmath.log),
    (("sqrt", "Sqrt"), cmath.sqrt), (("abs", "magnitude", "Abs"), abs),
    (("conjugate", "Conjugate"), _conjugate), (("real-part", "Re"), _real),
    (("imag-part", "Im"), _imag),
]:
    for alias in aliases:
        OPERATORS[alias] = (1, fn)

CONSTANTS = {"pi": math.pi, "Pi": math.pi, "PI": math.pi, "E": math.e, "e": math.e, "I": 1j}
ANGLES = {"theta": "theta", "th": "theta", "phi": "phi", "ph": "phi"}


def _token(symbol):
    return "/" if symbol.name == "/" else str(symbol).rsplit("/", 1)[-1]


def _finite(value):
    if isinstance(value, bool) or not isinstance(value, numbers.Number):
        return False
    z = complex(value)
    return math.isfinite(z.real) and math.isfinite(z.imag)


def compile_expression(form, parameters, imaginary_tolerance=1e-10):
    if (not isinstance(parameters, Mapping)
            or any(not isinstance(key, Symbol) or _token(key) in ANGLES or _token(key) in CONSTANTS
                   for key in parameters)
            or not all(_finite(value) for value in parameters.values())
            or not _finite(imaginary_tolerance) or isinstance(imaginary_tolerance, complex)
            or imaginary_tolerance < 0):
        raise ValueError("Invalid symbolic parameters or imaginary tolerance")
    constants = []
    globals_ = {"__builtins__": {}}

    def constant(value):
        index = len(constants)
        constants.append(value)
        return ast.Subscript(value=ast.Name(id="_constants", ctx=ast.Load()),
                             slice=ast.Constant(value=index), ctx=ast.Load())

    def node(value):
        if _finite(value):
            return constant(value)
        if isinstance(value, Symbol):
            token = _token(value)
            if token in ANGLES:
                return ast.Name(id=ANGLES[token], ctx=ast.Load())
            if value in parameters:
                return constant(parameters[value])
            if token in CONSTANTS:
                return constant(CONSTANTS[token])
            raise ValueError(f"Unknown expression symbol; supply it in :parameters: {value}")
        if not isinstance(value, ISeq):
            raise ValueError(f"Expected a finite number, symbol or arithmetic expression: {value}")
        parts = list(value)
        if not parts or not isinstance(parts[0], Symbol):
            raise ValueError("Expected a symbolic arithmetic operator")
        token, arguments = _token(parts[0]), parts[1:]
        if token in ("+", "-", "*", "/"):
            if not arguments:
                if token in ("-", "/"):
                    raise ValueError(f"Wrong symbolic operator arity: {token}")
                return constant(0 if token == "+" else 1)
            children = [node(x) for x in arguments]
            if len(children) == 1 and token == "-":
                return ast.UnaryOp(op=ast.USub(), operand=children[0])
            if len(children) == 1 and token == "/":
                return ast.BinOp(left=constant(1), op=ast.Div(), right=children[0])
            result = children[0]
            for child in children[1:]:
                result = ast.BinOp(left=result, op={"+": ast.Add, "-": ast.Sub,
                                                  "*": ast.Mult, "/": ast.Div}[token](), right=child)
            return result
        if token not in OPERATORS:
            raise ValueError(f"Unsupported symbolic operator: {parts[0]}")
        arity, operation = OPERATORS[token]
        if len(arguments) != arity:
            raise ValueError(f"Wrong symbolic operator arity: {token}")
        name = f"_operator_{len(globals_)}"
        globals_[name] = operation
        return ast.Call(func=ast.Name(id=name, ctx=ast.Load()), args=[node(x) for x in arguments], keywords=[])

    body = node(form)
    definition = dict(name="_equation", args=ast.arguments(posonlyargs=[],
                      args=[ast.arg(arg="theta"), ast.arg(arg="phi")], vararg=None,
                      kwonlyargs=[], kw_defaults=[], kwarg=None, defaults=[]),
                      body=[ast.Return(value=body)], decorator_list=[], returns=None, type_comment=None)
    if "type_params" in ast.FunctionDef._fields:
        definition["type_params"] = []
    module = ast.fix_missing_locations(ast.Module(body=[ast.FunctionDef(**definition)], type_ignores=[]))
    compiled = compile(module, "<fawltypoly arithmetic expression>", "exec")
    function_code = next(value for value in compiled.co_consts if isinstance(value, types.CodeType))
    globals_["_constants"] = tuple(constants)
    equation = types.FunctionType(function_code, globals_)

    def evaluate(theta, phi):
        value = equation(theta, phi)
        z = complex(value)
        if (not _finite(value)
                or abs(z.imag) > imaginary_tolerance * max(1, abs(z.real))):
            raise ValueError(f"Expression must produce a finite real value: theta={theta}, phi={phi}, value={value}")
        return z.real

    return evaluate
