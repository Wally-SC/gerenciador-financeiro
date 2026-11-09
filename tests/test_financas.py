import csv

import pytest

from financas import Repositorio, formatar, para_centavos
from financas.cli import main


@pytest.fixture
def repo():
    with Repositorio() as r:
        yield r


@pytest.mark.parametrize(
    "entrada, esperado",
    [("19.90", 1990), ("0.10", 10), (5, 500), ("1234.56", 123456), (0.1, 10)],
)
def test_para_centavos(entrada, esperado):
    assert para_centavos(entrada) == esperado


@pytest.mark.parametrize("entrada", ["abc", "1.234", "NaN", "inf", ""])
def test_para_centavos_invalido(entrada):
    with pytest.raises(ValueError):
        para_centavos(entrada)


def test_soma_sem_erro_de_ponto_flutuante():
    assert para_centavos("0.1") + para_centavos("0.2") == para_centavos("0.3")


@pytest.mark.parametrize(
    "centavos, esperado",
    [(0, "R$ 0,00"), (5, "R$ 0,05"), (123456, "R$ 1.234,56"), (-990, "-R$ 9,90"), (100000000, "R$ 1.000.000,00")],
)
def test_formatar(centavos, esperado):
    assert formatar(centavos) == esperado


def test_saldo(repo):
    repo.adicionar("receita", "3000", "salario", "2026-10-05")
    repo.adicionar("despesa", "1200.50", "aluguel", "2026-10-06")
    repo.adicionar("despesa", "89.90", "mercado", "2026-10-07")
    assert repo.saldo() == 3000_00 - 1200_50 - 89_90


def test_saldo_vazio(repo):
    assert repo.saldo() == 0


def test_resumo_mensal_agrupa_por_categoria(repo):
    repo.adicionar("receita", "5000", "salario", "2026-10-05")
    repo.adicionar("despesa", "100", "mercado", "2026-10-06")
    repo.adicionar("despesa", "50", "mercado", "2026-10-20")
    repo.adicionar("despesa", "800", "aluguel", "2026-10-10")
    repo.adicionar("despesa", "999", "lazer", "2026-11-01")  # outro mês

    r = repo.resumo_mensal("2026-10")
    assert r["receitas"] == 5000_00
    assert r["despesas"] == 950_00
    assert r["saldo"] == 4050_00
    assert list(r["despesas_por_categoria"].items()) == [("aluguel", 800_00), ("mercado", 150_00)]


def test_listar_filtros(repo):
    repo.adicionar("despesa", "10", "Mercado", "2026-10-01")
    repo.adicionar("despesa", "20", "lazer", "2026-11-01")
    assert len(repo.listar(mes="2026-10")) == 1
    assert len(repo.listar(categoria="MERCADO")) == 1  # categoria é normalizada
    assert len(repo.listar()) == 2


def test_validacoes(repo):
    with pytest.raises(ValueError):
        repo.adicionar("transferencia", "10", "x")
    with pytest.raises(ValueError):
        repo.adicionar("despesa", "0", "x")
    with pytest.raises(ValueError):
        repo.adicionar("despesa", "-5", "x")
    with pytest.raises(ValueError):
        repo.adicionar("despesa", "10", "   ")
    with pytest.raises(ValueError):
        repo.adicionar("despesa", "10", "x", "10/10/2026")
    with pytest.raises(ValueError):
        repo.resumo_mensal("2026-13")


def test_remover(repo):
    t = repo.adicionar("despesa", "10", "x", "2026-10-01")
    repo.remover(t.id)
    assert repo.listar() == []
    with pytest.raises(KeyError):
        repo.remover(t.id)


def test_exportar_csv(repo, tmp_path):
    repo.adicionar("receita", "10.5", "freela", "2026-10-01", "projeto, com vírgula")
    destino = tmp_path / "saida.csv"
    assert repo.exportar_csv(destino) == 1
    with open(destino, encoding="utf-8") as f:
        linhas = list(csv.reader(f))
    assert linhas[0] == ["id", "data", "tipo", "categoria", "valor", "descricao"]
    assert linhas[1][4] == "10.50"
    assert linhas[1][5] == "projeto, com vírgula"


def test_persistencia_em_arquivo(tmp_path):
    banco = tmp_path / "f.db"
    with Repositorio(banco) as r:
        r.adicionar("receita", "100", "x", "2026-10-01")
    with Repositorio(banco) as r:
        assert r.saldo() == 100_00


def test_cli(tmp_path, capsys):
    base = ["--banco", str(tmp_path / "f.db")]
    assert main(base + ["add", "receita", "100", "salario", "-d", "2026-10-01"]) == 0
    assert main(base + ["add", "despesa", "30.5", "mercado", "-d", "2026-10-02"]) == 0
    assert main(base + ["saldo"]) == 0
    assert "R$ 69,50" in capsys.readouterr().out
    assert main(base + ["resumo", "2026-10"]) == 0
    assert main(base + ["add", "despesa", "abc", "x"]) == 1
