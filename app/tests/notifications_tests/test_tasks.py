import pytest
from django.core import mail
from django.utils.timezone import now

from grandchallenge.notifications.models import Notification
from grandchallenge.notifications.tasks import send_unread_notification_emails
from tests.factories import UserFactory
from tests.notifications_tests.factories import NotificationFactory


@pytest.mark.django_db
def test_notification_email():
    user1, user2 = UserFactory.create_batch(2)
    user2.is_active = False
    user2.save()
    _ = NotificationFactory(user=user1, type=Notification.Type.GENERIC)
    _ = NotificationFactory(user=user2, type=Notification.Type.GENERIC)

    assert user1.user_profile.has_unread_notifications
    assert user1.user_profile.receive_notification_emails
    assert user2.user_profile.has_unread_notifications
    assert user2.user_profile.receive_notification_emails
    assert len(mail.outbox) == 0
    send_unread_notification_emails()
    assert len(mail.outbox) == 1
    email = mail.outbox[-1]
    assert user1.email in email.to
    assert user2.email not in email.to
    assert "You have 1 new notification" in email.body


@pytest.mark.django_db
def test_notification_email_last_sent_at_updated():
    user1 = UserFactory()
    _ = NotificationFactory(user=user1, type=Notification.Type.GENERIC)
    assert not user1.user_profile.notification_email_last_sent_at
    send_unread_notification_emails()
    user1.refresh_from_db()
    assert user1.user_profile.notification_email_last_sent_at


@pytest.mark.django_db
def test_notification_email_only_about_new_unread_notifications():
    user1 = UserFactory()
    _ = NotificationFactory(user=user1, type=Notification.Type.GENERIC)

    # mimic sending notification email by updating time stamp
    user1.user_profile.notification_email_last_sent_at = now()
    user1.user_profile.save()

    _ = NotificationFactory(user=user1, type=Notification.Type.GENERIC)
    send_unread_notification_emails()

    # user has 2 unread notifications
    assert len(user1.user_profile.unread_notifications) == 2
    # but only receives an email about unread notifications since the last email
    assert mail.outbox[-1].to[0] == user1.email
    assert "You have 1 new notification" in mail.outbox[-1].body


@pytest.mark.django_db
def test_notification_email_opt_out():
    user1 = UserFactory()
    user1.user_profile.receive_notification_emails = False
    user1.user_profile.save()

    _ = NotificationFactory(user=user1, type=Notification.Type.GENERIC)

    send_unread_notification_emails()
    assert len(mail.outbox) == 0

    user1.user_profile.receive_notification_emails = True
    user1.user_profile.save()

    send_unread_notification_emails()
    assert len(mail.outbox) == 1


@pytest.mark.django_db
def test_notification_email_counts():
    user1, user2, user3 = UserFactory.create_batch(3)
    _ = NotificationFactory(user=user1, type=Notification.Type.GENERIC)
    _ = NotificationFactory(user=user2, type=Notification.Type.GENERIC)
    _ = NotificationFactory(user=user2, type=Notification.Type.GENERIC)

    assert len(mail.outbox) == 0
    send_unread_notification_emails()
    assert len(mail.outbox) == 2

    assert mail.outbox[0].to[0] == user1.email
    assert "You have 1 new notification" in mail.outbox[0].body

    assert mail.outbox[1].to[0] == user2.email
    assert "You have 2 new notifications" in mail.outbox[1].body

    send_unread_notification_emails()
    assert len(mail.outbox) == 2
