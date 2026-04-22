# Gerador de Relatório Mensal

## O que este projeto faz
Você preenche um formulário no navegador e o sistema gera um PDF com:
- título do relatório
- período
- cards com indicadores
- gráfico de evolução
- insights estratégicos

## Como instalar
1. Instale o Python 3 no computador.
2. Abra a pasta do projeto.
3. No terminal, rode:

```bash
pip install -r requirements.txt
```

## Como iniciar
No terminal, rode:

```bash
python app.py
```

Depois abra no navegador:

```bash
http://127.0.0.1:5000
```

## Como usar
1. Preencha os campos.
2. Clique em **Gerar PDF**.
3. O arquivo será baixado automaticamente.

## Onde alterar o visual
- Formulário: `templates/index.html`
- Lógica e PDF: `app.py`
