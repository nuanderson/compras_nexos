from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

from apps.relatorios import services as relatorios_services


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "core/dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["kpis"] = relatorios_services.get_dashboard_kpis(self.request.user)
        return ctx
