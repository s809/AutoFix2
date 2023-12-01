from typing import Any
from django.db.models.query import QuerySet
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import redirect
from django.views.generic import *
from django.views.generic.edit import DeletionMixin
from django.urls import *
from django.contrib.auth.mixins import LoginRequiredMixin
from .context_processors import nav_urls
from django.db.models import Q

from .forms import *


class BaseListView(LoginRequiredMixin, ListView):
    template_name = "list.html"
    def post(self, request, *args, **kwargs):
        self.kwargs.update(request.resolver_match.kwargs)
        return self.get(request, *args, **kwargs)


class CheckPermissionsMixin(LoginRequiredMixin):
    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        if not self.check_permissions(request):
            return redirect("..")
        return super().get(self, request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        if not self.check_permissions(request):
            return redirect("..")
        return super().post(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        if not self.check_permissions(request):
            return redirect("..")
        return super().delete(request, *args, **kwargs)

class CheckCreatePermissionsMixin(CheckPermissionsMixin):
    def check_permissions(self, request):
        return request.user.position in ["AD", *self.model.create_allowed_to]

class CheckViewPermissionsMixin(CheckPermissionsMixin):
    def check_permissions(self, request):
        try:
            return self.parent.check_permissions(request)
        except:
            return request.user.position in ["AD", *self.model.edit_allowed_to]

class PaginatedListView(CheckViewPermissionsMixin, BaseListView):
    paginate_by = 20

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        self.search = request.GET.get("search", None)
        return super().get(request, *args, **kwargs)

    def get_queryset(self) -> QuerySet[Any]:
        queryset = super().get_queryset()
        if self.search:
            queryset = queryset.filter(self.model.search(self.search))
        return queryset

class BaseCreateView(CheckCreatePermissionsMixin, LoginRequiredMixin, CreateView):
    template_name = "create.html"
    success_url = ".."

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["initial"]["position"] = self.request.user.position
        return kwargs


class BaseUpdateView(CheckViewPermissionsMixin, UpdateView, DeletionMixin):
    template_name = "update.html"
    success_url = ".."
    extra_views = []

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["initial"]["position"] = self.request.user.position
        return kwargs

    def get_context_data(self, request = None, *args, **kwargs):
        self.object = self.get_object()
        context = super().get_context_data(**kwargs)
        context["extra_contexts"] = []

        for extra_view in self.extra_views:
            clsview = extra_view.as_view()
            view = clsview(self.request, *args, **(kwargs | { "pk": self.object.id }))
            context["extra_contexts"].append(view.context_data)

        return context

    def get(self, request, *args, **kwargs):
        if request.GET.get("delete") is not None:
            self.delete(request, *args, **kwargs)
            return HttpResponseRedirect(request.META.get('HTTP_REFERER', self.get_success_url()))
        return super().get(request, *args, **kwargs)


class RepairOrderListView(PaginatedListView):
    plural_name = "Заявки на ремонт"
    model = RepairOrder
    template_name = "repair_order_list.html"

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        self.master_list = Employee.objects.filter(
            position = Employee.Position.Mechanic).order_by("last_name", "first_name", "patronymic"
        )
        self.filter_master = Employee.objects.filter(id = int(request.GET.get("filter_master", 0))
                                                     if request.user.position != Employee.Position.Mechanic
                                                     else request.user.id).first()
        self.show_finished = int(request.GET.get("show_finished", 0)) == 1
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        filter = Q();
        if self.filter_master:
            filter &= Q(master_id = self.filter_master.id)
        if not self.show_finished:
            filter &= Q(finish_date__isnull = True) | Q(is_paid = False)
        return super().get_queryset().filter(filter).order_by("finish_until", "id")


class ServiceListView(PaginatedListView):
    plural_name = "Услуги"
    model = Service
    queryset = Service.objects.order_by("name")

class WarehouseItemListView(PaginatedListView):
    plural_name = "Расходники"
    model = WarehouseItem
    queryset = WarehouseItem.objects.order_by("name")

class WarehouseProviderListView(PaginatedListView):
    plural_name = "Поставщики расходников"
    model = WarehouseProvider
    queryset = WarehouseProvider.objects.order_by("name")

class EmployeeListView(PaginatedListView):
    plural_name = "Сотрудники"
    model = Employee
    hide_delete = True
    template_name = "employee_list.html"

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        self.show_removed = int(request.GET.get("show_removed", 0)) == 1
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        kwargs = {"end_date__isnull": True}
        if self.show_removed:
            kwargs.pop("end_date__isnull")
        return super().get_queryset().filter(**kwargs).order_by("last_name", "first_name", "patronymic")


class ServiceHistoryListView(BaseListView):
    plural_name = "Выполненные услуги"
    subdir = "history/"
    model = ServiceHistory
    def get_queryset(self):
        return ServiceHistory.objects.filter(repair_order_id = self.kwargs["pk"])
class WarehouseUseListView(BaseListView):
    plural_name = "Использованные расходники"
    subdir = "warehouse_uses/"
    model = WarehouseUse
    def get_queryset(self):
        return WarehouseUse.objects.filter(repair_order_id = self.kwargs["pk"])
class WarehouseRestockListView(BaseListView):
    plural_name = "Пополнения"
    subdir = "restocks/"
    model = WarehouseRestock
    def get_queryset(self):
        return WarehouseRestock.objects.filter(item_id = self.kwargs["pk"])


class RepairOrderView:
    model = RepairOrder
    form_class = RepairOrderForm
    extra_views = [
        ServiceHistoryListView,
        WarehouseUseListView
    ]
class ServiceView:
    model = Service
    form_class = ServiceForm
class WarehouseItemView:
    model = WarehouseItem
    form_class = WarehouseItemForm
    extra_views = [
        WarehouseRestockListView
    ]
class WarehouseProviderView:
    model = WarehouseProvider
    form_class = WarehouseProviderForm
class EmployeeView(LoginRequiredMixin):
    model = Employee
    success_url = ".."

class RepairOrderCreateView(RepairOrderView, BaseCreateView):
    pass
class ServiceCreateView(ServiceView, BaseCreateView):
    pass
class WarehouseItemCreateView(WarehouseItemView, BaseCreateView):
    pass
class WarehouseProviderCreateView(WarehouseProviderView, BaseCreateView):
    pass
class EmployeeCreateView(CheckCreatePermissionsMixin, EmployeeView, CreateView):
    form_class = EmployeeCreationForm
    template_name = "create.html"

class RepairOrderUpdateView(RepairOrderView, BaseUpdateView):
    def check_permissions(self, request):
        can_access = request.user.id == self.get_object().master_id if request.user.position == Employee.Position.Mechanic \
            else True
        return can_access and super().check_permissions(request)
class ServiceUpdateView(ServiceView, BaseUpdateView):
    pass
class WarehouseItemUpdateView(WarehouseItemView, BaseUpdateView):
    pass
class WarehouseProviderUpdateView(WarehouseProviderView, BaseUpdateView):
    pass
class EmployeeUpdateView(CheckViewPermissionsMixin, EmployeeView, UpdateView):
    form_class = EmployeeChangeForm
    template_name = "update.html"


class ServiceHistoryView:
    model = ServiceHistory
    parent = RepairOrder
    form_class = ServiceHistoryForm
    def get_form_kwargs(self) -> dict[str, Any]:
        kwargs = super().get_form_kwargs()
        kwargs["initial"].update({"order": self.kwargs['order']})
        return kwargs
class WarehouseUseView:
    model = WarehouseUse
    parent = RepairOrder
    form_class = WarehouseUseForm
    def get_form_kwargs(self) -> dict[str, Any]:
        kwargs = super().get_form_kwargs()
        kwargs["initial"].update({"order": self.kwargs['order']})
        return kwargs
class WarehouseRestockView:
    model = WarehouseRestock
    parent = WarehouseItem
    form_class = WarehouseRestockForm
    def get_form_kwargs(self) -> dict[str, Any]:
        kwargs = super().get_form_kwargs()
        kwargs["initial"].update({"item": self.kwargs['item']})
        return kwargs

class ServiceHistoryCreateView(ServiceHistoryView, BaseCreateView):
    pass
class WarehouseUseCreateView(WarehouseUseView, BaseCreateView):
    pass
class WarehouseRestockCreateView(WarehouseRestockView, BaseCreateView):
    pass

class ServiceHistoryUpdateView(ServiceHistoryView, BaseUpdateView):
    pass
class WarehouseUseUpdateView(WarehouseUseView, BaseUpdateView):
    pass
class WarehouseRestockUpdateView(WarehouseRestockView, BaseUpdateView):
    pass


def RedirectUpView(request, *args, **kwargs):
    return redirect('..')


def HomePageView(request):
    if request.user.is_authenticated:
        return redirect(nav_urls(request)["first_visible_entry"])
    else:
        return redirect('login')
