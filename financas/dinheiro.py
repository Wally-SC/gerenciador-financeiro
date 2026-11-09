"""Valores monetários guardados como inteiros em centavos.

Evita os erros de arredondamento de ``float`` (0.1 + 0.2 != 0.3).
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation


def para_centavos(valor: str | int | float | Decimal) -> int:
    """Converte um valor em reais para centavos, exigindo no máximo 2 casas decimais.

    >>> para_centavos("19.90")
    1990
    >>> para_centavos("1.234,56".replace(".", "").replace(",", "."))
    123456
    """
    try:
        decimal = Decimal(str(valor).strip())
    except InvalidOperation as exc:
        raise ValueError(f"valor inválido: {valor!r}") from exc
    if not decimal.is_finite():
        raise ValueError(f"valor inválido: {valor!r}")
    centavos = decimal * 100
    if centavos != centavos.to_integral_value():
        raise ValueError(f"use no máximo 2 casas decimais: {valor!r}")
    return int(centavos)


def formatar(centavos: int) -> str:
    """Formata centavos como ``R$ 1.234,56``."""
    sinal = "-" if centavos < 0 else ""
    reais, resto = divmod(abs(centavos), 100)
    inteiro = f"{reais:,}".replace(",", ".")
    return f"{sinal}R$ {inteiro},{resto:02d}"
