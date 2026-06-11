"""
Views do app fornecedores.

CompradorRequiredMixin: restringe acesso a role comprador/admin ou superuser.
Padrão seguindo GestorRequiredMixin de apps/aprovacoes/views.py (A3 do RESEARCH.md).

Referências:
  FORN-01..05
  T-03-01  CompradorRequiredMixin bloqueia solicitante/gestor/diretor
  T-03-02  ToggleAtivoView aceita apenas POST
  T-03-04  Truncar q a 100 chars (DoS guard)
"""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.postgres.search import TrigramSimilarity
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from apps.requisicoes.models import CategoriaCompra

from .forms import FornecedorForm
from .models import Fornecedor


class CompradorRequiredMixin(LoginRequiredMixin):
    """
    Restringe acesso a usuários com role='comprador', 'admin' ou is_superuser.

    Lança PermissionDenied (HTTP 403) para papéis não autorizados.
    Referência: T-03-01.
    """

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not (
            request.user.is_superuser
            or request.user.role in ("comprador", "admin")
        ):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


def get_queryset_fornecedores(q=None, categoria_pk=None, apenas_ativos=True):
    """
    Retorna queryset de Fornecedor com busca fuzzy ou exata e filtro de categoria.

    - Se q for um CNPJ válido (14 chars alfanuméricos): busca exata no campo cnpj.
    - Caso contrário: busca fuzzy TrigramSimilarity em razao_social (threshold 0.1).
    - Se q vazio: retorna todos ordenados por razao_social.

    Defesas:
    - q truncado a 100 chars (T-03-04 — DoS guard).
    - TrigramSimilarity nunca chamado com q vazio (Pitfall 2 do RESEARCH.md).
    """
    qs = Fornecedor.objects.select_related("categoria")
    if apenas_ativos:
        qs = qs.filter(ativo=True)

    if categoria_pk:
        qs = qs.filter(categoria_id=categoria_pk)

    if q:
        q = q[:100]  # T-03-04 — truncar antes de passar ao ORM
        cnpj_c = q.replace(".", "").replace("/", "").replace("-", "").strip().upper()
        if len(cnpj_c) == 14 and cnpj_c.isalnum():
            # Query parece ser um CNPJ — busca exata (D-03)
            qs = qs.filter(cnpj=cnpj_c)
        else:
            # Fuzzy no nome (D-03)
            qs = (
                qs.annotate(sim=TrigramSimilarity("razao_social", q))
                .filter(sim__gt=0.1)
                .order_by("-sim")
            )
    else:
        qs = qs.order_by("razao_social")

    return qs


class ListaFornecedoresView(CompradorRequiredMixin, View):
    """
    Lista fornecedores com busca fuzzy HTMX e filtro de categoria.

    GET com HTMX: retorna partial fornecedor_list.html.
    GET sem HTMX: retorna página completa lista.html.
    q vazio retorna lista completa, nunca 404 (Pitfall 4 do RESEARCH.md).
    """

    def get(self, request):
        q = request.GET.get("q", "").strip()
        categoria_pk = request.GET.get("categoria", "")
        mostrar_inativos = request.GET.get("mostrar_inativos", "") == "1"
        qs = get_queryset_fornecedores(
            q=q or None,
            categoria_pk=categoria_pk or None,
            apenas_ativos=not mostrar_inativos,
        )
        ctx = {
            "fornecedores": qs,
            "categorias": CategoriaCompra.objects.filter(ativo=True),
            "q": q,
            "categoria_pk": categoria_pk,
            "mostrar_inativos": mostrar_inativos,
        }
        if request.htmx:
            return render(request, "fornecedores/partials/fornecedor_list.html", ctx)
        return render(request, "fornecedores/lista.html", ctx)


class CadastrarFornecedorView(CompradorRequiredMixin, View):
    """
    Criação de novo fornecedor.

    GET: exibe formulário vazio.
    POST: valida, salva e redireciona para lista.
    """

    def get(self, request):
        form = FornecedorForm()
        return render(request, "fornecedores/form.html", {"form": form, "titulo": "Novo Fornecedor"})

    def post(self, request):
        form = FornecedorForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("fornecedores:lista")
        return render(request, "fornecedores/form.html", {"form": form, "titulo": "Novo Fornecedor"})


class EditarFornecedorView(CompradorRequiredMixin, View):
    """
    Edição de fornecedor existente.

    Fornecedor é global (sem isolamento por unidade — FORN-01 não exige).
    GET/POST: mesmo padrão de CadastrarFornecedorView com instance=fornecedor.
    """

    def get(self, request, pk):
        fornecedor = get_object_or_404(Fornecedor, pk=pk)
        form = FornecedorForm(instance=fornecedor)
        return render(
            request,
            "fornecedores/form.html",
            {"form": form, "titulo": "Editar Fornecedor", "fornecedor": fornecedor},
        )

    def post(self, request, pk):
        fornecedor = get_object_or_404(Fornecedor, pk=pk)
        form = FornecedorForm(request.POST, instance=fornecedor)
        if form.is_valid():
            form.save()
            return redirect("fornecedores:lista")
        return render(
            request,
            "fornecedores/form.html",
            {"form": form, "titulo": "Editar Fornecedor", "fornecedor": fornecedor},
        )


class ToggleAtivoView(CompradorRequiredMixin, View):
    """
    Alterna o campo ativo do fornecedor sem deletar o registro.

    Aceita apenas POST (T-03-02 — GET retorna 405).
    Retorna partial de linha atualizada para HTMX outerHTML swap.

    Referências:
      FORN-04  toggle ativo sem perda de histórico
      T-03-02  aceita apenas POST
    """

    def post(self, request, pk):
        fornecedor = get_object_or_404(Fornecedor, pk=pk)
        fornecedor.ativo = not fornecedor.ativo
        fornecedor.save(update_fields=["ativo", "atualizado_em"])
        return render(
            request,
            "fornecedores/partials/fornecedor_row.html",
            {"fornecedor": fornecedor},
        )
