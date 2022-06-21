import contextlib
from base64 import b32encode

from allauth_2fa.forms import TOTPAuthenticateForm
from allauth_2fa.mixins import ValidTOTPDeviceRequiredMixin
from allauth_2fa.views import TwoFactorSetup
from django.conf import settings
from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import DetailView, FormView, UpdateView
from django_otp.plugins.otp_totp.models import TOTPDevice
from guardian.core import ObjectPermissionChecker
from guardian.mixins import LoginRequiredMixin
from guardian.mixins import (
    PermissionRequiredMixin as ObjectPermissionRequiredMixin,
)
from guardian.shortcuts import get_objects_for_user
from rest_framework.decorators import action
from rest_framework.permissions import DjangoObjectPermissions
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from rest_framework_guardian.filters import ObjectPermissionsFilter

from grandchallenge.algorithms.models import Job
from grandchallenge.challenges.models import Challenge
from grandchallenge.evaluation.models import Submission
from grandchallenge.organizations.models import Organization
from grandchallenge.profiles.forms import NewsletterSignupForm, UserProfileForm
from grandchallenge.profiles.models import UserProfile
from grandchallenge.profiles.serializers import UserProfileSerializer
from grandchallenge.subdomains.utils import reverse, reverse_lazy


def profile(request):
    """Redirect to the profile page of the currently signed in user."""
    if request.user.is_authenticated:
        url = reverse(
            "profile-detail", kwargs={"username": request.user.username}
        )
    else:
        url = reverse("account_login")

    return redirect(url)


class UserProfileObjectMixin:
    def get_object(self, queryset=None):
        try:
            return (
                UserProfile.objects.select_related("user__verification")
                .exclude(user__username__iexact=settings.ANONYMOUS_USER_NAME)
                .get(user__username__iexact=self.kwargs["username"])
            )
        except ObjectDoesNotExist:
            raise Http404("User not found.")


class UserProfileDetail(UserProfileObjectMixin, DetailView):
    model = UserProfile
    context_object_name = "profile"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        profile_user = context["object"].user
        profile_groups = profile_user.groups.all()

        organizations = Organization.objects.filter(
            Q(members_group__in=profile_groups)
            | Q(editors_group__in=profile_groups)
        ).distinct()

        archives = (
            get_objects_for_user(
                user=self.request.user,
                perms="archives.view_archive",
                accept_global_perms=False,
            )
            .filter(
                Q(editors_group__in=profile_groups)
                | Q(uploaders_group__in=profile_groups)
                | Q(users_group__in=profile_groups)
            )
            .distinct()
        )
        reader_studies = (
            get_objects_for_user(
                user=self.request.user,
                perms="reader_studies.view_readerstudy",
                accept_global_perms=False,
            )
            .filter(
                Q(editors_group__in=profile_groups)
                | Q(readers_group__in=profile_groups)
            )
            .distinct()
        )
        challenges = Challenge.objects.filter(
            Q(admins_group__in=profile_groups)
            | Q(participants_group__in=profile_groups),
            hidden=False,
        ).distinct()
        algorithms = (
            get_objects_for_user(
                user=self.request.user,
                perms="algorithms.view_algorithm",
                accept_global_perms=False,
            )
            .filter(
                Q(editors_group__in=profile_groups)
                | Q(users_group__in=profile_groups)
            )
            .distinct()
        )

        checker = ObjectPermissionChecker(user_or_group=profile_user)
        for qs in [archives, reader_studies, challenges, algorithms]:
            # Perms can only be prefetched for sets of the same objects
            checker.prefetch_perms(objects=qs)

        object_list = [*archives, *reader_studies, *challenges, *algorithms]

        role = {}
        for obj in object_list:
            obj_perms = checker.get_perms(obj)
            if f"change_{obj._meta.model_name}" in obj_perms:
                role[obj] = "editor"
            elif f"view_{obj._meta.model_name}" in obj_perms:
                role[obj] = "user"
            else:
                role[obj] = "participant"

        context.update(
            {
                "object_list": object_list,
                "object_role": role,
                "num_submissions": Submission.objects.filter(
                    creator=profile_user
                ).count(),
                "num_algorithms_run": Job.objects.filter(
                    creator=profile_user
                ).count(),
                "organizations": organizations,
            }
        )

        return context


class UserProfileUpdate(
    LoginRequiredMixin,
    ObjectPermissionRequiredMixin,
    UserProfileObjectMixin,
    UpdateView,
):
    model = UserProfile
    form_class = UserProfileForm
    context_object_name = "profile"
    permission_required = "change_userprofile"
    raise_exception = True


class NewsletterSignUp(
    LoginRequiredMixin,
    ObjectPermissionRequiredMixin,
    UserProfileObjectMixin,
    UpdateView,
):
    model = UserProfile
    form_class = NewsletterSignupForm
    context_object_name = "profile"
    permission_required = "change_userprofile"
    raise_exception = True

    def form_valid(self, form):
        messages.add_message(
            self.request,
            messages.SUCCESS,
            "Newsletter preference successfully saved.",
        )
        return super().form_valid(form)

    def get_success_url(self):
        return self.request.GET.get("next")


class UserProfileViewSet(GenericViewSet):
    serializer_class = UserProfileSerializer
    permission_classes = (DjangoObjectPermissions,)
    filter_backends = (ObjectPermissionsFilter,)
    queryset = UserProfile.objects.all()

    @action(detail=False, methods=["get"])
    def self(self, request):
        obj = get_object_or_404(UserProfile, user=request.user)
        serializer = self.get_serializer(instance=obj)
        return Response(serializer.data)


class TwoFactorSetup(TwoFactorSetup):
    def get_secret_key(self):
        return b32encode(self.device.bin_key).decode("utf-8")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["secret_key"] = self.get_secret_key()
        return context

    def form_invalid(self, form):
        response = super().form_invalid(form)
        # and display an error message
        messages.add_message(self.request, messages.ERROR, "Incorrect token.")
        return response


class TwoFactorRemove(ValidTOTPDeviceRequiredMixin, FormView):
    form_class = TOTPAuthenticateForm
    template_name = "allauth_2fa/remove.html"

    def get_success_url(self):
        return reverse_lazy(
            "profile-detail", kwargs={"username": self.request.user.username}
        )

    def form_valid(self, form):
        response = super().form_valid(form)
        with contextlib.suppress(ObjectDoesNotExist):
            # Delete any backup tokens and their related static device.
            static_device = self.request.user.staticdevice_set.get(
                name="backup"
            )
            static_device.token_set.all().delete()
            static_device.delete()

        # Delete TOTP device.
        device = TOTPDevice.objects.get(user=self.request.user)
        device.delete()
        return response

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs
