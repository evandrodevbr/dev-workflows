# PDF e documento visual: HTML + CSS + Playwright

Todo PDF passa por aqui: design primeiro, depois render, depois inspeção visual das páginas.

## Por que não reportlab direto

`platypus` com tabela longa estoura margem e corta linhas entre páginas. HTML + CSS de impressão
resolve quebra de página, cabeçalho repetido e margens com regras declarativas.

## 1. HTML com CSS de impressão

```css
@page { size: A4; margin: 18mm 16mm; }
table { width: 100%; border-collapse: collapse; }
thead { display: table-header-group; }   /* repete o cabeçalho em cada página */
tr, img, figure { break-inside: avoid; }
h1, h2 { break-after: avoid; }
td { overflow-wrap: anywhere; }          /* texto longo não empurra a margem */
```

## 2. Render com Playwright

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    page = p.chromium.launch().new_page()
    page.goto("file:///caminho/relatorio.html")
    page.pdf(path="relatorio.pdf", format="A4", print_background=True, prefer_css_page_size=True)
```

## 3. Inspeção visual obrigatória

Converta cada página em PNG e abra com Read:

```bash
pdftoppm -png -r 110 relatorio.pdf /tmp/qa/pagina
ls /tmp/qa/pagina-*.png
```

Em cada imagem, confira:

- nada cortado nas bordas (texto, tabela, imagem);
- tabela longa quebra entre páginas com o cabeçalho repetido;
- nenhuma linha órfã de título no pé da página;
- fontes carregadas (sem fallback inesperado).

Achou problema: ajuste o CSS, renderize de novo e inspecione de novo. Só entregue depois de todas as
páginas passarem.
