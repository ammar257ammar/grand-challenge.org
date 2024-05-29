import json
import tempfile
from pathlib import Path

import pytest
from guardian.shortcuts import assign_perm, remove_perm
from requests import put

from grandchallenge.archives.models import ArchiveItem
from grandchallenge.cases.widgets import WidgetChoices
from grandchallenge.components.models import ComponentInterface, InterfaceKind
from grandchallenge.subdomains.utils import reverse
from tests.archives_tests.factories import (
    ArchiveFactory,
    ArchiveItemFactory,
    ArchivePermissionRequestFactory,
)
from tests.cases_tests import RESOURCE_PATH
from tests.components_tests.factories import (
    ComponentInterfaceFactory,
    ComponentInterfaceValueFactory,
)
from tests.factories import ImageFactory, UserFactory
from tests.reader_studies_tests.factories import ReaderStudyFactory
from tests.uploads_tests.factories import (
    UserUploadFactory,
    create_upload_from_file,
)
from tests.utils import get_view_for_user, recurse_callbacks


@pytest.mark.django_db
class TestObjectPermissionRequiredViews:
    def test_permission_required_views(self, client):
        a = ArchiveFactory()
        u = UserFactory()
        p = ArchivePermissionRequestFactory(archive=a)

        for view_name, kwargs, permission, obj, redirect in [
            ("create", {}, "archives.add_archive", None, None),
            (
                "detail",
                {"slug": a.slug},
                "use_archive",
                a,
                reverse(
                    "archives:permission-request-create",
                    kwargs={"slug": a.slug},
                ),
            ),
            ("update", {"slug": a.slug}, "change_archive", a, None),
            ("editors-update", {"slug": a.slug}, "change_archive", a, None),
            ("uploaders-update", {"slug": a.slug}, "change_archive", a, None),
            ("users-update", {"slug": a.slug}, "change_archive", a, None),
            (
                "permission-request-update",
                {"slug": a.slug, "pk": p.pk},
                "change_archive",
                a,
                None,
            ),
            ("cases-create", {"slug": a.slug}, "upload_archive", a, None),
            (
                "items-reader-study-update",
                {"slug": a.slug},
                "use_archive",
                a,
                None,
            ),
        ]:

            def _get_view():
                return get_view_for_user(
                    client=client,
                    viewname=f"archives:{view_name}",
                    reverse_kwargs=kwargs,
                    user=u,
                )

            response = _get_view()
            if redirect is not None:
                assert response.status_code == 302
                assert response.url == redirect
            else:
                assert response.status_code == 403

            assign_perm(permission, u, obj)

            response = _get_view()
            assert response.status_code == 200

            remove_perm(permission, u, obj)

    def test_permission_required_list_views(self, client):
        a = ArchiveFactory()
        u = UserFactory()

        for view_name, kwargs, permission, objs in [
            ("list", {}, "view_archive", {a})
        ]:

            def _get_view():
                return get_view_for_user(
                    client=client,
                    viewname=f"archives:{view_name}",
                    reverse_kwargs=kwargs,
                    user=u,
                )

            response = _get_view()
            assert response.status_code == 200
            assert set() == {*response.context[-1]["object_list"]}

            assign_perm(permission, u, list(objs))

            response = _get_view()
            assert response.status_code == 200
            assert objs == {*response.context[-1]["object_list"]}

            for obj in objs:
                remove_perm(permission, u, obj)


def add_image_to_archive(image, archive):
    interface = ComponentInterfaceFactory()
    civ = ComponentInterfaceValueFactory(interface=interface, image=image)
    item = ArchiveItemFactory(archive=archive)
    item.values.set([civ])


def create_archive_with_user_and_image(patient_id=""):
    a = ArchiveFactory()
    u = UserFactory()
    i = ImageFactory(patient_id=patient_id)
    add_image_to_archive(i, a)
    a.add_user(u)
    return a, u, i


@pytest.mark.django_db
class TestArchiveViewSetPatients:
    @staticmethod
    def get_view(client, user, archive_pk):
        return get_view_for_user(
            client=client,
            viewname="api:archive-patients",
            reverse_kwargs={"pk": archive_pk},
            user=user,
        )

    def test_no_access_archive(self, client):
        a, u, i = create_archive_with_user_and_image()
        a.remove_user(u)
        response = self.get_view(client, u, a.pk)
        assert response.status_code == 404

    def test_empty_archive(self, client):
        a, u, i = create_archive_with_user_and_image()
        a.items.all().delete()
        response = self.get_view(client, u, a.pk)
        assert response.status_code == 200
        assert len(response.data) == 0

    def test_archive_no_patients(self, client):
        a, u, i = create_archive_with_user_and_image()
        [add_image_to_archive(ImageFactory(), a) for _ in range(3)]
        response = self.get_view(client, u, a.pk)
        assert response.status_code == 200
        assert len(response.data) == 1
        assert response.data[0] == ""

    def test_archive_some_patients(self, client):
        a, u, i = create_archive_with_user_and_image()
        patients = [f"Patient {i}" for i in range(3)]
        [add_image_to_archive(ImageFactory(patient_id=p), a) for p in patients]
        response = self.get_view(client, u, a.pk)
        assert response.status_code == 200
        assert set(response.data) == set(patients + [""])


@pytest.mark.django_db
class TestArchiveViewSetStudies:
    @staticmethod
    def get_view(client, user, archive_pk, patient_id):
        return get_view_for_user(
            client=client,
            viewname="api:archive-studies",
            user=user,
            reverse_kwargs={"pk": archive_pk},
            data={"patient_id": patient_id},
        )

    def test_no_access_archive(self, client):
        p_id = "patient_id"
        a, u, i = create_archive_with_user_and_image(p_id)
        a.remove_user(u)
        response = self.get_view(client, u, a.pk, p_id)
        assert response.status_code == 404

    def test_single_empty_study(self, client):
        p_id = "patient_id"
        a, u, i = create_archive_with_user_and_image(p_id)
        response = self.get_view(client, u, a.pk, p_id)
        assert response.status_code == 200
        assert len(response.data) == 1
        assert response.data[0] == ""

    def test_multiple_empty_studies_distinct(self, client):
        p_id = "patient_id"
        a, u, i = create_archive_with_user_and_image(p_id)
        for _ in range(3):
            add_image_to_archive(ImageFactory(patient_id=p_id), a)
        response = self.get_view(client, u, a.pk, p_id)
        assert response.status_code == 200
        assert len(response.data) == 1
        assert response.data[0] == ""

    def test_study_some_patients(self, client):
        p_id = "patient_id"
        a, u, i = create_archive_with_user_and_image(p_id)
        studies = [f"Study {i}" for i in range(3)]
        for s in studies:
            i = ImageFactory(patient_id=p_id, study_description=s)
            add_image_to_archive(i, a)
        response = self.get_view(client, u, a.pk, p_id)
        assert response.status_code == 200
        assert set(response.data) == set(studies + [""])


@pytest.mark.django_db
def test_api_archive_item_list_is_filtered(client):
    a1, a2 = ArchiveFactory(), ArchiveFactory()
    a1_editor, user = UserFactory(), UserFactory()
    a1.add_editor(a1_editor)
    _, _ = (ArchiveItemFactory(archive=a1), ArchiveItemFactory(archive=a1))
    i3 = ArchiveItemFactory(archive=a2)

    # user does not see any archive items
    response = get_view_for_user(
        viewname="api:archives-item-list", user=user, client=client
    )
    assert response.status_code == 200
    assert response.json()["count"] == 0

    # editor of archive 1 sees the items from archive 1, but not from archive 2
    response = get_view_for_user(
        viewname="api:archives-item-list", user=a1_editor, client=client
    )
    assert response.status_code == 200
    assert response.json()["count"] == 2
    assert i3.id not in (
        response.json()["results"][0]["pk"],
        response.json()["results"][1]["pk"],
    )


@pytest.mark.django_db
def test_api_archive_item_retrieve_permissions(client):
    archive = ArchiveFactory()
    editor, user = UserFactory(), UserFactory()
    archive.add_editor(editor)
    i1 = ArchiveItemFactory(archive=archive)

    # editor can retrieve archive item
    response = get_view_for_user(
        viewname="api:archives-item-detail",
        reverse_kwargs={"pk": i1.pk},
        user=editor,
        client=client,
    )
    assert response.status_code == 200
    assert response.json()["pk"] == str(i1.pk)

    # user cannot retrieve archive item
    response = get_view_for_user(
        viewname="api:archives-item-detail",
        reverse_kwargs={"pk": i1.pk},
        user=user,
        client=client,
    )
    assert response.status_code == 404

    # add user to archive
    archive.add_user(user)
    response = get_view_for_user(
        viewname="api:archives-item-detail",
        reverse_kwargs={"pk": i1.pk},
        user=user,
        client=client,
    )
    assert response.status_code == 200
    assert response.json()["pk"] == str(i1.pk)


@pytest.mark.django_db
def test_api_archive_item_add_and_update_value(
    client, settings, django_capture_on_commit_callbacks
):
    # Override the celery settings
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    archive = ArchiveFactory()
    editor = UserFactory()
    archive.add_editor(editor)
    item = ArchiveItemFactory(archive=archive)
    ci = ComponentInterfaceFactory(
        kind=InterfaceKind.InterfaceKindChoices.BOOL
    )

    # add civ
    with django_capture_on_commit_callbacks() as callbacks:
        response = get_view_for_user(
            viewname="api:archives-item-detail",
            reverse_kwargs={"pk": item.pk},
            data={"values": [{"interface": ci.slug, "value": True}]},
            user=editor,
            client=client,
            method=client.patch,
            content_type="application/json",
            HTTP_X_FORWARDED_PROTO="https",
        )
    recurse_callbacks(
        callbacks=callbacks,
        django_capture_on_commit_callbacks=django_capture_on_commit_callbacks,
    )

    assert response.status_code == 200
    assert response.json()["pk"] == str(item.pk)
    item.refresh_from_db()
    assert item.values.count() == 1
    civ = item.values.get()
    assert civ.interface.slug == ci.slug
    assert civ.value

    # update civ
    with django_capture_on_commit_callbacks() as callbacks:
        response = get_view_for_user(
            viewname="api:archives-item-detail",
            reverse_kwargs={"pk": item.pk},
            data={"values": [{"interface": ci.slug, "value": False}]},
            user=editor,
            client=client,
            method=client.patch,
            content_type="application/json",
            HTTP_X_FORWARDED_PROTO="https",
        )
    recurse_callbacks(
        callbacks=callbacks,
        django_capture_on_commit_callbacks=django_capture_on_commit_callbacks,
    )

    assert response.status_code == 200
    assert response.json()["pk"] == str(item.pk)
    item.refresh_from_db()
    assert item.values.count() == 1
    new_civ = item.values.get()
    assert new_civ.interface.slug == ci.slug
    assert new_civ != civ


@pytest.mark.django_db
def test_api_archive_item_add_and_update_non_image_file(
    client, settings, django_capture_on_commit_callbacks
):
    # Override the celery settings
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    archive = ArchiveFactory()
    editor = UserFactory()
    archive.add_editor(editor)
    item = ArchiveItemFactory(archive=archive)
    assert item.values.count() == 0
    ci = ComponentInterfaceFactory(kind=InterfaceKind.InterfaceKindChoices.PDF)
    upload = create_upload_from_file(
        creator=editor, file_path=RESOURCE_PATH / "test.pdf"
    )

    # add civ
    with django_capture_on_commit_callbacks() as callbacks:
        response = get_view_for_user(
            viewname="api:archives-item-detail",
            reverse_kwargs={"pk": item.pk},
            data={
                "values": [
                    {"interface": ci.slug, "user_upload": upload.api_url}
                ]
            },
            user=editor,
            client=client,
            method=client.patch,
            content_type="application/json",
            HTTP_X_FORWARDED_PROTO="https",
        )
    recurse_callbacks(
        callbacks=callbacks,
        django_capture_on_commit_callbacks=django_capture_on_commit_callbacks,
    )

    assert response.status_code == 200
    assert response.json()["pk"] == str(item.pk)
    item.refresh_from_db()
    assert item.values.count() == 1
    civ = item.values.get()
    assert civ.interface.slug == ci.slug

    # update civ
    upload2 = create_upload_from_file(
        creator=editor, file_path=RESOURCE_PATH / "test.zip"
    )

    with django_capture_on_commit_callbacks() as callbacks:
        response = get_view_for_user(
            viewname="api:archives-item-detail",
            reverse_kwargs={"pk": item.pk},
            data={
                "values": [
                    {"interface": ci.slug, "user_upload": upload2.api_url}
                ]
            },
            user=editor,
            client=client,
            method=client.patch,
            content_type="application/json",
            HTTP_X_FORWARDED_PROTO="https",
        )
    recurse_callbacks(
        callbacks=callbacks,
        django_capture_on_commit_callbacks=django_capture_on_commit_callbacks,
    )

    assert response.status_code == 200
    assert response.json()["pk"] == str(item.pk)
    item.refresh_from_db()
    assert item.values.count() == 1
    new_civ = item.values.get()
    assert new_civ.interface.slug == ci.slug
    assert new_civ != civ


@pytest.mark.django_db
def test_api_archive_item_add_and_update_json_file(
    client, settings, django_capture_on_commit_callbacks
):
    # Override the celery settings
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    archive = ArchiveFactory()
    editor = UserFactory()
    archive.add_editor(editor)
    item = ArchiveItemFactory(archive=archive)
    assert item.values.count() == 0
    ci = ComponentInterfaceFactory(
        kind=InterfaceKind.InterfaceKindChoices.ANY, store_in_database=False
    )

    with tempfile.NamedTemporaryFile(mode="w+", suffix=".json") as file:
        json.dump('{"Foo": "bar"}', file)
        file.seek(0)
        upload = create_upload_from_file(
            creator=editor, file_path=Path(file.name)
        )
        # add civ
        with django_capture_on_commit_callbacks() as callbacks:
            response = get_view_for_user(
                viewname="api:archives-item-detail",
                reverse_kwargs={"pk": item.pk},
                data={
                    "values": [
                        {"interface": ci.slug, "user_upload": upload.api_url}
                    ]
                },
                user=editor,
                client=client,
                method=client.patch,
                content_type="application/json",
                HTTP_X_FORWARDED_PROTO="https",
            )
        recurse_callbacks(
            callbacks=callbacks,
            django_capture_on_commit_callbacks=django_capture_on_commit_callbacks,
        )
    assert response.status_code == 200
    assert response.json()["pk"] == str(item.pk)
    item.refresh_from_db()
    assert item.values.count() == 1
    civ = item.values.get()
    assert civ.interface.slug == ci.slug

    # update civ
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".json") as file:
        json.dump('{"Foo": "bar"}', file)
        file.seek(0)
        upload2 = create_upload_from_file(
            creator=editor, file_path=Path(file.name)
        )

        with django_capture_on_commit_callbacks() as callbacks:
            response = get_view_for_user(
                viewname="api:archives-item-detail",
                reverse_kwargs={"pk": item.pk},
                data={
                    "values": [
                        {"interface": ci.slug, "user_upload": upload2.api_url}
                    ]
                },
                user=editor,
                client=client,
                method=client.patch,
                content_type="application/json",
                HTTP_X_FORWARDED_PROTO="https",
            )
        recurse_callbacks(
            callbacks=callbacks,
            django_capture_on_commit_callbacks=django_capture_on_commit_callbacks,
        )
    assert response.status_code == 200
    assert response.json()["pk"] == str(item.pk)
    item.refresh_from_db()
    assert item.values.count() == 1
    new_civ = item.values.get()
    assert new_civ.interface.slug == ci.slug
    assert new_civ != civ


@pytest.mark.django_db
def test_api_archive_item_create(client, settings):
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)
    archive = ArchiveFactory()
    editor, user = UserFactory.create_batch(2)
    archive.add_editor(editor)
    archive.add_user(user)
    ci = ComponentInterfaceFactory(kind=ComponentInterface.Kind.STRING)

    response = get_view_for_user(
        viewname="api:archives-item-list",
        client=client,
        method=client.post,
        data={"archive": archive.api_url, "values": []},
        user=user,
        content_type="application/json",
        follow=True,
    )

    # User does not have access to the archive
    assert response.status_code == 400
    assert response.json()["archive"] == [
        "Invalid hyperlink - Object does not exist."
    ]

    assert archive.items.count() == 0
    response = get_view_for_user(
        viewname="api:archives-item-list",
        client=client,
        method=client.post,
        data={
            "archive": archive.api_url,
            "values": [{"interface": ci.slug, "value": "bar"}],
        },
        user=editor,
        content_type="application/json",
        follow=True,
    )
    assert response.status_code == 400
    assert "Values can only be added via update" in response.json()
    assert archive.items.count() == 0

    response = get_view_for_user(
        viewname="api:archives-item-list",
        client=client,
        method=client.post,
        data={"archive": archive.api_url, "values": []},
        content_type="application/json",
        user=editor,
        follow=True,
    )
    assert response.status_code == 201
    assert archive.items.count() == 1


@pytest.mark.django_db
def test_archive_items_to_reader_study_update(client, settings):
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)
    archive = ArchiveFactory()
    rs = ReaderStudyFactory()

    editor, user = UserFactory(), UserFactory()
    archive.add_user(user)
    archive.add_editor(editor)
    rs.add_editor(editor)

    im1, im2, im3, im4 = ImageFactory.create_batch(4)
    overlay = ComponentInterface.objects.get(slug="generic-overlay")
    image = ComponentInterface.objects.get(slug="generic-medical-image")

    civ1, civ2, civ3, civ4 = (
        ComponentInterfaceValueFactory(interface=image, image=im1),
        ComponentInterfaceValueFactory(interface=image, image=im2),
        ComponentInterfaceValueFactory(interface=overlay, image=im3),
        ComponentInterfaceValueFactory(interface=overlay, image=im4),
    )

    ai1 = ArchiveItemFactory(archive=archive)
    ai2 = ArchiveItemFactory(archive=archive)

    ai1.values.add(civ1)
    ai2.values.add(civ2)

    response = get_view_for_user(
        viewname="archives:items-reader-study-update",
        client=client,
        reverse_kwargs={"slug": archive.slug},
        user=user,
    )
    assert response.status_code == 200
    assert str(rs.pk) not in response.rendered_content

    response = get_view_for_user(
        viewname="archives:items-reader-study-update",
        client=client,
        reverse_kwargs={"slug": archive.slug},
        follow=True,
        user=editor,
    )

    assert response.status_code == 200
    assert str(rs.pk) in response.rendered_content

    assert im1.name in response.rendered_content
    assert im2.name in response.rendered_content
    assert im3.name not in response.rendered_content
    assert im4.name not in response.rendered_content

    ai1.values.add(civ3)
    ai2.values.add(civ4)

    response = get_view_for_user(
        viewname="archives:items-reader-study-update",
        client=client,
        reverse_kwargs={"slug": archive.slug},
        follow=True,
        user=editor,
    )

    assert response.status_code == 200

    assert (
        f"{image.title}: {im1.name}, {overlay.title}: {im3.name}"
        in response.rendered_content
    )
    assert (
        f"{image.title}: {im2.name}, {overlay.title}: {im4.name}"
        in response.rendered_content
    )


@pytest.mark.django_db
def test_archive_item_add_image(
    client, settings, django_capture_on_commit_callbacks
):
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)
    archive = ArchiveFactory()
    item = ArchiveItemFactory(archive=archive)
    editor = UserFactory()
    archive.add_editor(editor)
    ci_img = ComponentInterfaceFactory(
        kind=InterfaceKind.InterfaceKindChoices.IMAGE
    )
    ci_value = ComponentInterfaceFactory(
        kind=InterfaceKind.InterfaceKindChoices.BOOL
    )
    civ_value = ComponentInterfaceValueFactory(interface=ci_value, value=True)
    item.values.add(civ_value)
    upload = create_upload_from_file(
        file_path=RESOURCE_PATH / "image10x10x10.mha",
        creator=editor,
    )
    with django_capture_on_commit_callbacks(execute=True):
        with django_capture_on_commit_callbacks(execute=True):
            response = get_view_for_user(
                viewname="archives:item-edit",
                client=client,
                method=client.post,
                reverse_kwargs={
                    "pk": item.pk,
                    "slug": archive.slug,
                },
                user=editor,
                data={
                    ci_img.slug: upload.pk,
                    f"WidgetChoice-{ci_img.slug}": WidgetChoices.IMAGE_UPLOAD.name,
                },
            )
    assert response.status_code == 302
    assert item.values.count() == 2
    assert "image10x10x10.mha" == item.values.get(interface=ci_img).image.name
    old_civ_img = item.values.get(interface=ci_img)

    with django_capture_on_commit_callbacks(execute=True):
        with django_capture_on_commit_callbacks(execute=True):
            response = get_view_for_user(
                viewname="archives:item-edit",
                client=client,
                method=client.post,
                reverse_kwargs={
                    "pk": item.pk,
                    "slug": archive.slug,
                },
                user=editor,
                data={
                    ci_img.slug: old_civ_img.image.pk,
                    f"WidgetChoice-{ci_img.slug}": WidgetChoices.IMAGE_SEARCH.name,
                },
            )
    assert response.status_code == 302
    assert item.values.get(interface=ci_img).image.pk == old_civ_img.image.pk
    assert item.values.get(interface=ci_img) == old_civ_img

    image = ImageFactory()
    assign_perm("cases.view_image", editor, image)
    with django_capture_on_commit_callbacks(execute=True):
        with django_capture_on_commit_callbacks(execute=True):
            response = get_view_for_user(
                viewname="archives:item-edit",
                client=client,
                method=client.post,
                reverse_kwargs={
                    "pk": item.pk,
                    "slug": archive.slug,
                },
                user=editor,
                data={
                    ci_img.slug: image.pk,
                    f"WidgetChoice-{ci_img.slug}": WidgetChoices.IMAGE_SEARCH.name,
                },
            )
    assert response.status_code == 302
    assert item.values.get(interface=ci_img).image.pk == image.pk
    assert item.values.get(interface=ci_img) != old_civ_img


@pytest.mark.django_db
def test_archive_item_add_file(
    client, settings, django_capture_on_commit_callbacks
):
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)
    archive = ArchiveFactory()
    item = ArchiveItemFactory(archive=archive)
    editor = UserFactory()
    archive.add_editor(editor)
    ci = ComponentInterfaceFactory(kind=InterfaceKind.InterfaceKindChoices.PDF)
    upload = create_upload_from_file(
        creator=editor, file_path=RESOURCE_PATH / "test.pdf"
    )

    with django_capture_on_commit_callbacks(execute=True):
        with django_capture_on_commit_callbacks(execute=True):
            response = get_view_for_user(
                viewname="archives:item-edit",
                client=client,
                method=client.post,
                reverse_kwargs={
                    "pk": item.pk,
                    "slug": archive.slug,
                },
                user=editor,
                data={ci.slug: upload.pk},
            )
    assert response.status_code == 302
    assert "test" in ArchiveItem.objects.get().values.first().file.name


@pytest.mark.django_db
def test_archive_item_add_json_file(
    client, settings, django_capture_on_commit_callbacks
):
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)
    archive = ArchiveFactory()
    item = ArchiveItemFactory(archive=archive)
    editor = UserFactory()
    archive.add_editor(editor)
    ci = ComponentInterfaceFactory(
        kind=InterfaceKind.InterfaceKindChoices.ANY, store_in_database=False
    )

    with tempfile.NamedTemporaryFile(mode="w+", suffix=".json") as file:
        json.dump('{"Foo": "bar"}', file)
        file.seek(0)
        upload = create_upload_from_file(
            creator=editor, file_path=Path(file.name)
        )
        with django_capture_on_commit_callbacks(execute=True):
            with django_capture_on_commit_callbacks(execute=True):
                response = get_view_for_user(
                    viewname="archives:item-edit",
                    client=client,
                    method=client.post,
                    reverse_kwargs={
                        "pk": item.pk,
                        "slug": archive.slug,
                    },
                    user=editor,
                    data={ci.slug: upload.pk},
                )
        assert response.status_code == 302
        assert (
            file.name.split("/")[-1]
            in ArchiveItem.objects.get().values.first().file.name
        )


@pytest.mark.django_db
def test_archive_item_add_value(
    client, settings, django_capture_on_commit_callbacks
):
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)
    archive = ArchiveFactory()
    item = ArchiveItemFactory(archive=archive)
    editor = UserFactory()
    archive.add_editor(editor)
    ci = ComponentInterfaceFactory(
        kind=InterfaceKind.InterfaceKindChoices.BOOL
    )

    with django_capture_on_commit_callbacks(execute=True):
        with django_capture_on_commit_callbacks(execute=True):
            response = get_view_for_user(
                viewname="archives:item-edit",
                client=client,
                method=client.post,
                reverse_kwargs={
                    "pk": item.pk,
                    "slug": archive.slug,
                },
                user=editor,
                data={ci.slug: True},
            )
    assert response.status_code == 302
    assert ArchiveItem.objects.get().values.first().value


@pytest.mark.django_db
def test_archive_item_create_permissions(client):
    archive = ArchiveFactory()
    user, uploader, editor = UserFactory.create_batch(3)
    archive.add_user(user)
    archive.add_uploader(uploader)
    archive.add_editor(editor)

    response = get_view_for_user(
        viewname="archives:item-create",
        reverse_kwargs={"slug": archive.slug},
        client=client,
        user=user,
    )
    assert response.status_code == 403

    response = get_view_for_user(
        viewname="archives:item-create",
        reverse_kwargs={"slug": archive.slug},
        client=client,
        user=uploader,
    )
    assert response.status_code == 403

    response = get_view_for_user(
        viewname="archives:item-create",
        reverse_kwargs={"slug": archive.slug},
        client=client,
        user=editor,
    )
    assert response.status_code == 200


@pytest.mark.django_db
def test_archive_item_create_view(
    client, settings, django_capture_on_commit_callbacks
):
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    archive = ArchiveFactory()
    editor = UserFactory()
    archive.add_editor(editor)
    ai1 = ArchiveItemFactory(archive=archive)
    ci_str = ComponentInterfaceFactory(
        kind=InterfaceKind.InterfaceKindChoices.STRING
    )
    ci_img = ComponentInterfaceFactory(
        kind=InterfaceKind.InterfaceKindChoices.IMAGE
    )
    ci_img2 = ComponentInterfaceFactory(
        kind=InterfaceKind.InterfaceKindChoices.IMAGE
    )
    ci_json = ComponentInterfaceFactory(
        kind=InterfaceKind.InterfaceKindChoices.ANY, store_in_database=False
    )
    ci_json2 = ComponentInterfaceFactory(
        kind=InterfaceKind.InterfaceKindChoices.ANY, store_in_database=True
    )

    im1, im2 = ImageFactory.create_batch(2)
    civ_str = ComponentInterfaceValueFactory(
        interface=ci_str, value="civ-title"
    )
    civ_img = ComponentInterfaceValueFactory(interface=ci_img, image=im1)
    ai1.values.set([civ_str, civ_img])

    response = get_view_for_user(
        viewname="archives:item-create",
        reverse_kwargs={"slug": archive.slug},
        client=client,
        user=editor,
    )
    assert len(response.context["form"].fields) == 3
    assert response.context["form"].fields[ci_str.slug]
    assert response.context["form"].fields[ci_img.slug]
    assert response.context["form"].fields["title"]

    im_upload = create_upload_from_file(
        file_path=RESOURCE_PATH / "test_grayscale.jpg",
        creator=editor,
    )
    image = ImageFactory()
    assign_perm("cases.view_image", editor, image)
    upload = UserUploadFactory(filename="file.json", creator=editor)
    presigned_urls = upload.generate_presigned_urls(part_numbers=[1])
    response = put(presigned_urls["1"], data=b'{"foo": "bar"}')
    upload.complete_multipart_upload(
        parts=[{"ETag": response.headers["ETag"], "PartNumber": 1}]
    )
    upload.save()

    with django_capture_on_commit_callbacks(execute=True):
        response = get_view_for_user(
            viewname="archives:item-create",
            client=client,
            reverse_kwargs={"slug": archive.slug},
            data={
                ci_str.slug: "new-title",
                ci_img.slug: str(im_upload.pk),
                f"WidgetChoice-{ci_img.slug}": WidgetChoices.IMAGE_UPLOAD.name,
                ci_img2.slug: str(image.pk),
                f"WidgetChoice-{ci_img2.slug}": WidgetChoices.IMAGE_SEARCH.name,
                ci_json.slug: str(upload.pk),
                ci_json2.slug: '{"some": "content"}',
                "title": "archive-item title",
            },
            user=editor,
            method=client.post,
        )

    assert response.status_code == 302
    assert ArchiveItem.objects.count() == 2
    ai2 = ArchiveItem.objects.order_by("created").last()
    assert ai2.title == "archive-item title"
    assert ai2.values.count() == 5
    assert ai2.values.get(interface=ci_str).value == "new-title"
    assert ai2.values.get(interface=ci_img).image.name == "test_grayscale.jpg"
    assert ai2.values.get(interface=ci_img2).image == image
    assert ai2.values.get(interface=ci_json).file.read() == b'{"foo": "bar"}'
    assert ai2.values.get(interface=ci_json2).value == {"some": "content"}


@pytest.mark.django_db
def test_archive_item_bulk_delete_permissions(client):
    user, editor = UserFactory.create_batch(2)
    archive = ArchiveFactory()
    archive.add_editor(editor)

    i1, i2 = ArchiveItemFactory.create_batch(2, archive=archive)

    response = get_view_for_user(
        client=client,
        viewname="archives:items-bulk-delete",
        reverse_kwargs={"slug": archive.slug},
        user=editor,
    )
    assert list(
        response.context["form"].fields["civ_sets_to_delete"].queryset
    ) == [i1, i2]

    # for the normal user the queryset is empty
    response = get_view_for_user(
        client=client,
        viewname="archives:items-bulk-delete",
        reverse_kwargs={"slug": archive.slug},
        user=user,
    )
    assert (
        list(response.context["form"].fields["civ_sets_to_delete"].queryset)
        == []
    )
