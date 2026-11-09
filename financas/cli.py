from __future__ import annotations

import argparse
import sys
from pathlib import Path

from financas.dinheiro import formatar
from financas.repositorio import TIPOS, Repositorio

BANCO_PADRAO = Path.home() / ".financas" / "financas.db"


def construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="financas", description="Gerenciador financeiro pessoal.")
    parser.add_argument("--banco", type=Path, default=BANCO_PADRAO)
    sub = parser.add_subparsers(dest="comando", required=True)

    add = sub.add_parser("add", help="registra uma receita ou despesa")
    add.add_argument("tipo", choices=TIPOS)
    add.add_argument("valor", help="em reais, ex.: 49.90")
    add.add_argument("categoria")
    add.add_argument("-d", "--data", help="AAAA-MM-DD (padrão: hoje)")
    add.add_argument("--descricao", default="")

    lst = sub.add_parser("list", help="lista transações")
    lst.add_argument("--mes", help="AAAA-MM")
    lst.add_argument("--categoria")

    sub.add_parser("saldo", help="saldo total")

    res = sub.add_parser("resumo", help="resumo de um mês")
    res.add_argument("mes", help="AAAA-MM")

    rm = sub.add_parser("rm", help="remove uma transação")
    rm.add_argument("id", type=int)

    exp = sub.add_parser("exportar", help="exporta tudo para CSV")
    exp.add_argument("destino", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = construir_parser().parse_args(argv)
    args.banco.parent.mkdir(parents=True, exist_ok=True)
    try:
        with Repositorio(args.banco) as repo:
            if args.comando == "add":
                t = repo.adicionar(args.tipo, args.valor, args.categoria, args.data, args.descricao)
                print(f"#{t.id} {t.tipo} {formatar(t.valor)} em {t.categoria} ({t.data})")
            elif args.comando == "list":
                for t in repo.listar(args.mes, args.categoria):
                    print(f"#{t.id:<4} {t.data}  {t.tipo:<8} {formatar(t.valor):>14}  {t.categoria:<14} {t.descricao}")
            elif args.comando == "saldo":
                print(f"saldo: {formatar(repo.saldo())}")
            elif args.comando == "resumo":
                r = repo.resumo_mensal(args.mes)
                print(f"Resumo de {r['mes']}")
                print(f"  receitas: {formatar(r['receitas'])}")
                print(f"  despesas: {formatar(r['despesas'])}")
                print(f"  saldo:    {formatar(r['saldo'])}")
                for categoria, total in r["despesas_por_categoria"].items():
                    print(f"    - {categoria}: {formatar(total)}")
            elif args.comando == "rm":
                repo.remover(args.id)
                print(f"removida: #{args.id}")
            elif args.comando == "exportar":
                total = repo.exportar_csv(args.destino)
                print(f"{total} transações exportadas para {args.destino}")
    except (ValueError, KeyError) as exc:
        print(f"erro: {exc.args[0] if exc.args else exc}", file=sys.stderr)
        return 1
    return 0
