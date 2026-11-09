# gerenciador-financeiro

Controle financeiro pessoal em linha de comando, com dados em **SQLite**.

## Uso

```bash
python -m financas add receita 5000 salario -d 2026-10-05
python -m financas add despesa 89.90 mercado -d 2026-10-07 --descricao "compra da semana"
python -m financas list --mes 2026-10
python -m financas saldo
python -m financas resumo 2026-10
python -m financas exportar transacoes.csv
```

O banco fica em `~/.financas/financas.db` (use `--banco` para outro caminho).

Exemplo de `resumo`:

```
Resumo de 2026-10
  receitas: R$ 5.000,00
  despesas: R$ 989,90
  saldo:    R$ 4.010,10
    - aluguel: R$ 900,00
    - mercado: R$ 89,90
```

## Decisões de projeto

- **Dinheiro em centavos (inteiros):** nada de `float` para valores monetários.
  A entrada é lida com `Decimal` e rejeita mais de 2 casas decimais.
- **Regras também no banco:** `CHECK` no tipo e no valor, além da validação em
  Python, e índice na coluna de data.
- **SQL parametrizado:** nenhuma consulta é montada por concatenação de texto
  vinda do usuário.
- **Agregações no SQL:** saldo e resumo mensal usam `SUM`/`GROUP BY`.

## Testes

```bash
pip install pytest
pytest
```
