"""Converting between millilitres, cups and US fluid ounces."""

ML_PER_CUP = 250            # a standard glass or steel tumbler
ML_PER_US_FL_OZ = 29.5735

UNITS = ("ml", "cups", "fl oz")


def to_ml(value: float, unit: str) -> float:
    if unit == "ml":
        return value
    if unit == "cups":
        return value * ML_PER_CUP
    if unit == "fl oz":
        return value * ML_PER_US_FL_OZ
    raise ValueError(f"Unknown unit: {unit}")


def from_ml(ml: float, unit: str) -> float:
    if unit == "ml":
        return ml
    if unit == "cups":
        return ml / ML_PER_CUP
    if unit == "fl oz":
        return ml / ML_PER_US_FL_OZ
    raise ValueError(f"Unknown unit: {unit}")


def convert(value: float, from_unit: str, to_unit: str) -> float:
    return from_ml(to_ml(value, from_unit), to_unit)


def litres(ml: int) -> str:
    """2000 -> "2 L", 1250 -> "1.25 L"."""
    text = f"{ml / 1000:.2f}".rstrip("0").rstrip(".")
    return f"{text} L"
