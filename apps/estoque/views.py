"""
Views do app estoque.

EST-01 — cadastro de item
EST-03 — atualização de quantidade com select_for_update + transaction.atomic
EST-05 — isolamento de unidade (IDOR guard)
EST-06 — visão consolidada comprador/admin

T-03-05 — get_object_or_404 sempre com filtro unidade_organizacional para Solicitante
T-03-06 — PermissionDenied se Solicitante/Gestor/Diretor acessar visao consolidada
T-03-07 — select_for_update + transaction.atomic em AtualizarQuantidadeView
T-03-08 — validação de quantidade >= 0 no AtualizarQuantidadeForm
T-03-09 — unidade_organizacional atribuída por request.user.default_unit (nunca pelo form)
"""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.generic import ListView

from .forms import AtualizarQuantidadeForm, ItemEstoqueForm
from .models import ItemEstoque


class ListaEstoqueView(LoginRequiredMixin, ListView):
    """
    Lista de itens de estoque.

    Solicitante/Gestor/Diretor: vê apenas itens da própria unidade (D-06).
    Comprador/Admin: vê itens de todas as unidades.
    """

    template_name = "estoque/lista.html"
    context_object_name = "itens"

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser or user.role in ("comprador", "admin"):
            return (
                ItemEstoque.objects.select_related("unidade_medida", "unidade_organizacional")
                .order_by("nome")
            )
        # Solicitante, Gestor, Diretor — filtrar por unidade
        if not user.default_unit:
            return ItemEstoque.objects.none()
        return (
            ItemEstoque.objects.filter(unidade_organizacional=user.default_unit)
            .select_related("unidade_medida")
            .order_by("nome")
        )


class CadastrarItemEstoqueView(LoginRequiredMixin, View):
    """
    Cadastra um novo item de estoque vinculado à unidade do usuário.

    unidade_organizacional vem de request.user.default_unit — nunca do form (T-03-09).
    """

    template_name = "estoque/form.html"

    def get(self, request):
        form = ItemEstoqueForm()
        return render(request, self.template_name, {"form": form, "titulo": "Novo Item"})

    def post(self, request):
        form = ItemEstoqueForm(request.POST)
        if form.is_valid():
            item = form.save(commit=False)
            item.unidade_organizacional = request.user.default_unit
            item.save()
            return redirect("estoque:lista")
        return render(request, self.template_name, {"form": form, "titulo": "Novo Item"})


class EditarItemEstoqueView(LoginRequiredMixin, View):
    """
    Edita um item de estoque.

    IDOR guard: Solicitante/Gestor/Diretor só acessam items da própria unidade (T-03-05, EST-05).
    """

    template_name = "estoque/form.html"

    def _get_item(self, request, pk):
        user = request.user
        if user.is_superuser or user.role in ("comprador", "admin"):
            return get_object_or_404(ItemEstoque, pk=pk)
        return get_object_or_404(
            ItemEstoque,
            pk=pk,
            unidade_organizacional=user.default_unit,
        )

    def get(self, request, pk):
        item = self._get_item(request, pk)
        form = ItemEstoqueForm(instance=item)
        return render(request, self.template_name, {"form": form, "titulo": "Editar Item", "item": item})

    def post(self, request, pk):
        item = self._get_item(request, pk)
        form = ItemEstoqueForm(request.POST, instance=item)
        if form.is_valid():
            edited = form.save(commit=False)
            # Preservar unidade_organizacional original — nunca do form (T-03-09)
            edited.unidade_organizacional = item.unidade_organizacional
            edited.save()
            return redirect("estoque:lista")
        return render(request, self.template_name, {"form": form, "titulo": "Editar Item", "item": item})


class AtualizarQuantidadeView(LoginRequiredMixin, View):
    """
    Atualiza a quantidade de um item de estoque.

    Usa select_for_update() dentro de transaction.atomic() para prevenir
    race conditions (D-05, T-03-07).
    IDOR guard: filtra por unidade_organizacional do usuário (T-03-05).
    Valida quantidade >= 0 via AtualizarQuantidadeForm (T-03-08).
    """

    def post(self, request, pk):
        try:
            with transaction.atomic():
                item = ItemEstoque.objects.select_for_update().get(
                    pk=pk,
                    unidade_organizacional=request.user.default_unit,
                )
                form = AtualizarQuantidadeForm(request.POST, instance=item)
                if form.is_valid():
                    form.save()
                    return render(
                        request,
                        "estoque/partials/item_row.html",
                        {"item": item},
                    )
                # Form inválido — retorna partial com erros
                return render(
                    request,
                    "estoque/partials/item_row.html",
                    {"item": item, "form": form},
                    status=422,
                )
        except ItemEstoque.DoesNotExist:
            raise Http404


class VisaoConsolidadaView(LoginRequiredMixin, ListView):
    """
    Visão consolidada de estoque de todas as unidades.

    Apenas Comprador e Admin (EST-06, T-03-06).
    Levanta PermissionDenied para Solicitante/Gestor/Diretor.
    """

    template_name = "estoque/visao_consolidada.html"
    context_object_name = "itens"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not (
            request.user.is_superuser
            or request.user.role in ("comprador", "admin")
        ):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return (
            ItemEstoque.objects.select_related("unidade_medida", "unidade_organizacional")
            .order_by("unidade_organizacional__nome", "nome")
        )
