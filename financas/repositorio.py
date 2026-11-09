from __future__ import annotations

import csv
import sqlite3
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from financas.dinheiro import para_centavos

TIPOS = ("receita", "despesa")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS transacoes (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo       TEXT    NOT NULL CHECK (tipo IN ('receita', 'despesa')),
    valor      INTEGER NOT NULL CHECK (valor > 0),   -- centavos
    categoria  TEXT    NOT NULL,
    data       TEXT    NOT NULL,                     -- AAAA-MM-DD
    descricao  TEXT    NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_transacoes_data ON transacoes (data);
"""


@dataclass(frozen=True)
class Transacao:
    id: int
    tipo: str
    valor: int  # centavos
    categoria: str
    data: str
    descricao: str

    @property
    def valor_com_sinal(self) -> int:
        return self.valor if self.tipo == "receita" else -self.valor


class Repositorio:
    def __init__(self, caminho: str | Path = ":memory:") -> None:
        self._conexao = sqlite3.connect(str(caminho))
        self._conexao.row_factory = sqlite3.Row
        self._conexao.executescript(_SCHEMA)

    def fechar(self) -> None:
        self._conexao.close()

    def __enter__(self) -> "Repositorio":
        return self

    def __exit__(self, *_exc) -> None:
        self.fechar()

    # --- escrita ------------------------------------------------------
    def adicionar(
        self,
        tipo: str,
        valor: str | int | float,
        categoria: str,
        data: str | None = None,
        descricao: str = "",
    ) -> Transacao:
        if tipo not in TIPOS:
            raise ValueError(f"tipo inválido: {tipo!r} (use {' ou '.join(TIPOS)})")
        centavos = para_centavos(valor)
        if centavos <= 0:
            raise ValueError("o valor deve ser maior que zero")
        categoria = categoria.strip().lower()
        if not categoria:
            raise ValueError("a categoria não pode ser vazia")
        data = data or date.today().isoformat()
        try:
            date.fromisoformat(data)
        except ValueError as exc:
            raise ValueError(f"data inválida: {data!r} (use AAAA-MM-DD)") from exc

        with self._conexao:
            cursor = self._conexao.execute(
                "INSERT INTO transacoes (tipo, valor, categoria, data, descricao) VALUES (?, ?, ?, ?, ?)",
                (tipo, centavos, categoria, data, descricao.strip()),
            )
        return self.buscar(cursor.lastrowid)

    def remover(self, id_: int) -> None:
        with self._conexao:
            cursor = self._conexao.execute("DELETE FROM transacoes WHERE id = ?", (id_,))
        if cursor.rowcount == 0:
            raise KeyError(f"transação {id_} não encontrada")

    # --- leitura ------------------------------------------------------
    @staticmethod
    def _para_transacao(linha: sqlite3.Row) -> Transacao:
        return Transacao(**dict(linha))

    def buscar(self, id_: int) -> Transacao:
        linha = self._conexao.execute("SELECT * FROM transacoes WHERE id = ?", (id_,)).fetchone()
        if linha is None:
            raise KeyError(f"transação {id_} não encontrada")
        return self._para_transacao(linha)

    def listar(self, mes: str | None = None, categoria: str | None = None) -> list[Transacao]:
        """Lista transações, opcionalmente filtradas por mês (AAAA-MM) e categoria."""
        consulta = "SELECT * FROM transacoes WHERE 1 = 1"
        parametros: list[str] = []
        if mes:
            _validar_mes(mes)
            consulta += " AND substr(data, 1, 7) = ?"
            parametros.append(mes)
        if categoria:
            consulta += " AND categoria = ?"
            parametros.append(categoria.strip().lower())
        consulta += " ORDER BY data, id"
        return [self._para_transacao(l) for l in self._conexao.execute(consulta, parametros)]

    def saldo(self) -> int:
        linha = self._conexao.execute(
            "SELECT COALESCE(SUM(CASE tipo WHEN 'receita' THEN valor ELSE -valor END), 0) AS saldo FROM transacoes"
        ).fetchone()
        return int(linha["saldo"])

    def resumo_mensal(self, mes: str) -> dict:
        """Totais do mês (AAAA-MM) e despesas agrupadas por categoria, da maior para a menor."""
        _validar_mes(mes)
        linhas = self._conexao.execute(
            """
            SELECT tipo, categoria, SUM(valor) AS total
            FROM transacoes
            WHERE substr(data, 1, 7) = ?
            GROUP BY tipo, categoria
            ORDER BY total DESC
            """,
            (mes,),
        ).fetchall()
        receitas = sum(l["total"] for l in linhas if l["tipo"] == "receita")
        despesas = sum(l["total"] for l in linhas if l["tipo"] == "despesa")
        return {
            "mes": mes,
            "receitas": receitas,
            "despesas": despesas,
            "saldo": receitas - despesas,
            "despesas_por_categoria": {l["categoria"]: l["total"] for l in linhas if l["tipo"] == "despesa"},
        }

    def exportar_csv(self, destino: str | Path) -> int:
        """Grava todas as transações em CSV e retorna quantas linhas foram exportadas."""
        transacoes = self.listar()
        with open(destino, "w", newline="", encoding="utf-8") as arquivo:
            escritor = csv.writer(arquivo)
            escritor.writerow(["id", "data", "tipo", "categoria", "valor", "descricao"])
            for t in transacoes:
                escritor.writerow([t.id, t.data, t.tipo, t.categoria, f"{t.valor / 100:.2f}", t.descricao])
        return len(transacoes)


def _validar_mes(mes: str) -> None:
    try:
        date.fromisoformat(f"{mes}-01")
    except ValueError as exc:
        raise ValueError(f"mês inválido: {mes!r} (use AAAA-MM)") from exc
