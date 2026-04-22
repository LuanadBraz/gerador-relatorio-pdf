from flask import Flask, render_template, request, send_file, redirect, url_for, flash
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import os
import uuid
from datetime import datetime
import traceback

app = Flask(__name__)
app.secret_key = "relatorio"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# =========================
# ESTILOS GLOBAIS
# =========================
styles = getSampleStyleSheet()

title_style = ParagraphStyle(
    "title_style",
    parent=styles["Heading2"],
    fontName="Helvetica-Bold",
    fontSize=11,
    leading=13,
    textColor=colors.HexColor("#264a73"),
    spaceAfter=4,
)

body_style = ParagraphStyle(
    "body_style",
    parent=styles["Normal"],
    fontName="Helvetica",
    fontSize=9,
    leading=12,
    textColor=colors.HexColor("#1f2937"),
)

def parse_valor(valor):
    if not valor:
        return 0.0
    valor = str(valor).replace("R$", "").replace("%", "").replace(" ", "")
    valor = valor.replace(".", "").replace(",", ".")
    try:
        return float(valor)
    except ValueError:
        return 0.0


def formatar_moeda(valor):
    txt = f"{valor:,.2f}"
    txt = txt.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {txt}"


def formatar_percentual(valor):
    valor = int(round(valor))
    return f"{valor}%"


def calcular_crescimento_percentual(valor_atual, valor_anterior):
    try:
        valor_atual = float(valor_atual)
        valor_anterior = float(valor_anterior)

        if valor_anterior == 0:
            return 0.0

        return ((valor_atual - valor_anterior) / valor_anterior) * 100
    except (ValueError, TypeError):
        return 0.0


def gerar_grafico(meses, ggr, receita, path):
    plt.figure(figsize=(7.6, 2.8))
    x = list(range(len(meses)))

    plt.plot(x, ggr, marker="o", label="GGR")
    plt.plot(x, receita, marker="o", label="Receita")

    plt.xticks(x, meses)
    plt.title("Evolução Mensal de GGR e Receita")
    plt.legend()
    plt.tight_layout()
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()


def draw_logo(c, x, y):
    logo_path = os.path.join(BASE_DIR, "static", "Logonova.png")

    largura = 50 * mm
    altura = 18 * mm

    if os.path.exists(logo_path):
        c.drawImage(
            logo_path,
            x,
            y - altura,
            width=largura,
            height=altura,
            preserveAspectRatio=True,
            mask="auto"
        )


def draw_period_table(c, x, y_top, width, periodo, data_atualizacao):
    row_h = 8 * mm
    label_w = 48 * mm

    c.setStrokeColor(colors.HexColor("#d79b33"))
    c.setLineWidth(1)

    c.setFillColor(colors.HexColor("#2b4f7d"))
    c.rect(x, y_top - row_h, label_w, row_h, fill=1, stroke=1)
    c.setFillColor(colors.HexColor("#f7f7f7"))
    c.rect(x + label_w, y_top - row_h, width - label_w, row_h, fill=1, stroke=1)

    c.setFillColor(colors.HexColor("#2b4f7d"))
    c.rect(x, y_top - 2 * row_h, label_w, row_h, fill=1, stroke=1)
    c.setFillColor(colors.HexColor("#f7f7f7"))
    c.rect(x + label_w, y_top - 2 * row_h, width - label_w, row_h, fill=1, stroke=1)

    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(x + 4 * mm, y_top - row_h + 2.7 * mm, "Período")
    c.drawString(x + 4 * mm, y_top - 2 * row_h + 2.7 * mm, "Data de Atualização")

    c.setFillColor(colors.HexColor("#1f2937"))
    c.setFont("Helvetica", 9)
    c.drawString(x + label_w + 4 * mm, y_top - row_h + 2.7 * mm, periodo)
    c.drawString(x + label_w + 4 * mm, y_top - 2 * row_h + 2.7 * mm, data_atualizacao)


def draw_card(c, x, y, w, h, titulo, valor):
    c.setFillColor(colors.HexColor("#264a73"))
    c.setStrokeColor(colors.HexColor("#d79b33"))
    c.setLineWidth(1)
    c.roundRect(x, y, w, h, 4 * mm, fill=1, stroke=1)

    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 9)
    titulo_y = y + h - 11 * mm
    c.drawCentredString(x + w / 2, titulo_y, titulo.upper())

    c.setFillColor(colors.HexColor("#f0c66b"))
    c.setFont("Helvetica-Bold", 11)
    valor_y = y + 8.5 * mm
    c.drawCentredString(x + w / 2, valor_y, valor)


def draw_insights(c, x, y_top, width, texto):
    titulo = Paragraph("ANÁLISE DE PERFORMANCE", title_style)
    _, th = titulo.wrap(width, 20 * mm)
    titulo.drawOn(c, x, y_top - th)

    linhas = [linha.strip() for linha in texto.splitlines() if linha.strip()]
    if not linhas:
        linhas = ["Nenhum insight informado."]

    corpo_html = "<br/>".join([f"• {linha}" for linha in linhas])
    corpo = Paragraph(corpo_html, body_style)
    _, bh = corpo.wrap(width, 40 * mm)
    corpo.drawOn(c, x, y_top - th - 4 * mm - bh)


def gerar_analise_automatica(meses, lista_ggr, lista_receita, novos_jogadores, jogadores_anterior, comissao):
    analises = []

    if len(meses) >= 2 and len(lista_ggr) >= 2:
        ggr_anterior = lista_ggr[-2]
        ggr_atual = lista_ggr[-1]
        mes_anterior = meses[-2]
        mes_atual = meses[-1]

        if ggr_atual > ggr_anterior:
            analises.append(f"Crescimento do GGR de {mes_anterior} para {mes_atual}.")
        elif ggr_atual < ggr_anterior:
            analises.append(f"Queda do GGR de {mes_anterior} para {mes_atual}.")
        else:
            analises.append(f"O GGR permaneceu estável de {mes_anterior} para {mes_atual}.")

    if len(meses) >= 2 and len(lista_receita) >= 2:
        receita_anterior = lista_receita[-2]
        receita_atual = lista_receita[-1]
        mes_anterior = meses[-2]
        mes_atual = meses[-1]

        if receita_atual > receita_anterior:
            analises.append(f"A receita apresentou evolução de {mes_anterior} para {mes_atual}.")
        elif receita_atual < receita_anterior:
            analises.append(f"A receita apresentou retração de {mes_anterior} para {mes_atual}.")
        else:
            analises.append(f"A receita permaneceu estável entre {mes_anterior} e {mes_atual}.")

    if comissao > 0:
        analises.append(f"Houve comissão no período no valor de {formatar_moeda(comissao)}.")
    else:
        analises.append("Não houve comissão registrada no período.")

    if jogadores_anterior > 0:
        if novos_jogadores > jogadores_anterior:
            analises.append("Houve aumento de novos jogadores em relação ao período anterior.")
        elif novos_jogadores < jogadores_anterior:
            analises.append("Houve redução de novos jogadores em relação ao período anterior.")
        else:
            analises.append("A quantidade de novos jogadores permaneceu estável em relação ao período anterior.")
    else:
        if novos_jogadores > 0:
            analises.append("Houve entrada de novos jogadores no período atual.")
        else:
            analises.append("Não houve novos jogadores registrados no período.")

    return "\n".join(analises)


@app.route("/")
def index():
    return render_template(
        "index.html",
        today=datetime.now().strftime("%d/%m/%Y"),
        brand_name="PlayBonds",
        brand_subtitle="Relatórios"
    )


@app.route("/gerar-pdf", methods=["POST"])
def gerar_pdf():
    try:
        nome = request.form.get("affiliate_name", "").strip()
        periodo = request.form.get("period", "").strip()
        data = request.form.get("update_date", "").strip()

        ggr_form = parse_valor(request.form.get("ggr", "0"))
        comissao = parse_valor(request.form.get("comissao", "0"))
        novos_jogadores = parse_valor(request.form.get("novos_jogadores", "0"))
        jogadores_anterior = parse_valor(request.form.get("jogadores_anterior", "0"))
        insights_digitados = request.form.get("insights", "").strip()

        num_meses_raw = request.form.get("num_meses", "2")
        try:
            num_meses = int(num_meses_raw)
        except ValueError:
            num_meses = 2

        meses = []
        lista_ggr = []
        lista_receita = []

        for i in range(num_meses):
            nome_mes = request.form.get(f"mes_{i}", "").strip()
            valor_ggr = parse_valor(request.form.get(f"ggr_{i}", "0"))
            valor_receita = parse_valor(request.form.get(f"receita_{i}", "0"))

            if nome_mes:
                meses.append(nome_mes)
                lista_ggr.append(valor_ggr)
                lista_receita.append(valor_receita)

        if not nome or not periodo or not data:
            flash("Preencha nome da empresa, período e data.")
            return redirect(url_for("index"))

        if len(meses) < 2:
            flash("Adicione pelo menos 2 meses para gerar o gráfico.")
            return redirect(url_for("index"))

        ggr = ggr_form if ggr_form > 0 else sum(lista_ggr)
        receita_liquida = comissao

        if novos_jogadores > 0:
            ticket_medio = receita_liquida / novos_jogadores
        else:
            ticket_medio = 0.0

        crescimento = calcular_crescimento_percentual(novos_jogadores, jogadores_anterior)

        if insights_digitados:
            insights = insights_digitados
        else:
            insights = gerar_analise_automatica(
                meses=meses,
                lista_ggr=lista_ggr,
                lista_receita=lista_receita,
                novos_jogadores=novos_jogadores,
                jogadores_anterior=jogadores_anterior,
                comissao=comissao
            )

        pdf_name = f"relatorio_{uuid.uuid4().hex[:8]}.pdf"
        chart_name = f"grafico_{uuid.uuid4().hex[:8]}.png"

        pdf_path = os.path.join(OUTPUT_DIR, pdf_name)
        chart_path = os.path.join(OUTPUT_DIR, chart_name)

        gerar_grafico(meses, lista_ggr, lista_receita, chart_path)

        c = canvas.Canvas(pdf_path, pagesize=A4)
        page_w, page_h = A4

        c.setFillColor(colors.HexColor("#f4f5f7"))
        c.rect(0, 0, page_w, page_h, fill=1, stroke=0)

        margem_x = 15 * mm
        area_w = page_w - (2 * margem_x)
        topo = page_h - 15 * mm

        draw_logo(c, margem_x, topo - 5 * mm)

        c.setFillColor(colors.HexColor("#264a73"))
        c.setFont("Helvetica-Bold", 17)
        c.drawCentredString(page_w / 2, topo - 30 * mm, "Relatório Executivo de Performance")

        c.setFillColor(colors.HexColor("#1f2937"))
        c.setFont("Helvetica-Bold", 14)
        c.drawCentredString(page_w / 2, topo - 35 * mm, nome.upper())

        c.setStrokeColor(colors.HexColor("#d79b33"))
        c.setLineWidth(1)
        c.line(margem_x, topo - 36 * mm, page_w - margem_x, topo - 36 * mm)

        draw_period_table(c, margem_x, topo - 40 * mm, area_w, periodo, data)

        c.setFillColor(colors.HexColor("#264a73"))
        c.setFont("Helvetica-Bold", 12)
        c.drawString(margem_x, topo - 65 * mm, "RESUMO FINANCEIRO")

        card_w = 42 * mm
        card_h = 24 * mm
        gap_x = 10 * mm

        total_cards_width = (card_w * 3) + (gap_x * 2)
        start_x = (page_w - total_cards_width) / 2

        x1 = start_x
        x2 = x1 + card_w + gap_x
        x3 = x2 + card_w + gap_x

        y_row1 = topo - 95 * mm
        y_row2 = topo - 124 * mm

        draw_card(c, x1, y_row1, card_w, card_h, "Receita Líquida", formatar_moeda(receita_liquida))
        draw_card(c, x2, y_row1, card_w, card_h, "GGR", formatar_moeda(ggr))
        draw_card(c, x3, y_row1, card_w, card_h, "Comissão", formatar_moeda(comissao))

        jogadores_txt = str(int(novos_jogadores)) if float(novos_jogadores).is_integer() else str(novos_jogadores)

        draw_card(c, x1, y_row2, card_w, card_h, "Ticket Médio", formatar_moeda(ticket_medio))
        draw_card(c, x2, y_row2, card_w, card_h, "Novos Jogadores", jogadores_txt)
        draw_card(c, x3, y_row2, card_w, card_h, "Crescimento", formatar_percentual(crescimento))

        c.setFillColor(colors.HexColor("#264a73"))
        c.setFont("Helvetica-Bold", 12)
        c.drawString(margem_x, topo - 137 * mm, "EVOLUÇÃO MENSAL DE GGR E RECEITA")

        graf_x = margem_x
        graf_y = topo - 187 * mm
        graf_w = area_w
        graf_h = 42 * mm

        c.setFillColor(colors.white)
        c.setStrokeColor(colors.HexColor("#d1d5db"))
        c.rect(graf_x, graf_y, graf_w, graf_h, fill=1, stroke=1)

        c.drawImage(
            chart_path,
            graf_x + 2 * mm,
            graf_y + 2 * mm,
            width=graf_w - 4 * mm,
            height=graf_h - 4 * mm,
            preserveAspectRatio=True,
            mask="auto"
        )

        insights_top = graf_y - 8 * mm
        draw_insights(c, margem_x, insights_top, area_w, insights)

        c.save()

        if os.path.exists(chart_path):
            os.remove(chart_path)

        return send_file(pdf_path, as_attachment=True, download_name="relatorio_mensal.pdf")

    except Exception as e:
        print("ERRO AO GERAR PDF:")
        traceback.print_exc()
        flash(f"Erro ao gerar PDF: {str(e)}")
        return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True)
