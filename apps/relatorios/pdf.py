"""
Builders de PDF para os relatórios do app relatorios.

Toda a lógica ReportLab (Platypus) fica isolada aqui — as views ficam finas.
As views chamam build_gastos_pdf / build_requisicoes_pdf e recebem um BytesIO
pronto para ser servido via FileResponse.

IMPORTANTE: nunca gravar em disco — sempre BytesIO in-memory (T-05-09, seguro
em Docker/multi-processo). Nunca usar xhtml2pdf nem WeasyPrint — ReportLab
Platypus é obrigatório (CLAUDE.md §PDF Generation).

Funções públicas:
    build_gastos_pdf(dados, data_inicio, data_fim) -> BytesIO
    build_requisicoes_pdf(requisicoes) -> BytesIO

Helpers internos:
    _formato_brl(valor) -> str
    _estilo_tabela() -> TableStyle
"""
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Table, TableStyle


def _formato_brl(valor) -> str:
    """
    Converte um Decimal para string no formato brasileiro: 'R$ 12.345,67'.

    Usa substituição em cadeia para trocar separadores de milhar e decimal:
      1. Formata com vírgula de milhar e ponto decimal (padrão Python/C)
      2. Troca ',' por placeholder 'X'
      3. Troca '.' por ','
      4. Troca 'X' por '.'

    Exemplo:
        _formato_brl(Decimal('12345.67')) → 'R$ 12.345,67'
    """
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _estilo_tabela() -> TableStyle:
    """
    Retorna um TableStyle padrão para as tabelas dos relatórios.

    Estilo:
        - Cabeçalho: fundo #0f3460 (azul escuro), texto branco, Helvetica-Bold
        - Corpo: FONTSIZE 10, grid cinza, linhas alternadas branco/#f5f5f5
    """
    return TableStyle([
        # Cabeçalho — linha 0
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f3460")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        # Fonte — toda a tabela
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        # Grid
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#2a2a4a")),
        # Linhas alternadas do corpo (a partir da linha 1)
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f5f5")]),
    ])


def build_gastos_pdf(dados, data_inicio, data_fim) -> BytesIO:
    """
    Gera o PDF do relatório de Gastos por Categoria.

    Args:
        dados:       list[dict] — cada dict tem 'categoria_nome' (str|None) e 'total' (Decimal).
                     Retorno de services.get_gastos_por_categoria().
        data_inicio: str — data de início do período (ex.: '2026-06-01').
        data_fim:    str — data de fim do período (ex.: '2026-06-12').

    Returns:
        BytesIO — buffer posicionado em 0, pronto para FileResponse.

    Requisitos: REL-04, D-07.
    NUNCA grava em disco — apenas BytesIO in-memory (T-05-09).
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    # Cabeçalho do relatório
    story.append(Paragraph("Relatório de Gastos por Categoria", styles["Heading1"]))
    story.append(Paragraph(f"Período: {data_inicio} a {data_fim}", styles["Normal"]))

    # Dados da tabela
    table_data = [["Categoria", "Total (R$)"]]
    for row in dados:
        table_data.append([
            row["categoria_nome"] or "Sem categoria",
            _formato_brl(row["total"]),
        ])

    # Tabela com estilo e KeepTogether para evitar quebra de página no meio da tabela
    t = Table(table_data)
    t.setStyle(_estilo_tabela())
    story.append(KeepTogether([t]))

    doc.build(story)
    buffer.seek(0)
    return buffer


def build_requisicoes_pdf(requisicoes) -> BytesIO:
    """
    Gera o PDF do Painel de Status de Requisições.

    Args:
        requisicoes: QuerySet de Requisicao com select_related em categoria, unidade.
                     Retorno de services.get_requisicoes_painel().

    Returns:
        BytesIO — buffer posicionado em 0, pronto para FileResponse.

    Requisitos: REL-04, D-07.
    NUNCA grava em disco — apenas BytesIO in-memory (T-05-09).
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    # Cabeçalho do relatório
    story.append(Paragraph("Painel de Status de Requisições", styles["Heading1"]))

    # Dados da tabela
    table_data = [["Descrição", "Categoria", "Unidade", "Valor (R$)", "Status", "Criado em"]]
    for r in requisicoes:
        table_data.append([
            r.descricao[:40],
            r.categoria.nome,
            r.unidade.nome,
            _formato_brl(r.valor_estimado),
            r.get_status_display(),
            r.criado_em.strftime("%d/%m/%Y"),
        ])

    # Tabela com estilo e KeepTogether
    t = Table(table_data)
    t.setStyle(_estilo_tabela())
    story.append(KeepTogether([t]))

    doc.build(story)
    buffer.seek(0)
    return buffer
