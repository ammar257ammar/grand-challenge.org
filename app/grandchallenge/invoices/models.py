from django.db import models


class PaymentStatusChoices(models.TextChoices):
    INITIALIZED = "INITIALIZED", "Initialized"
    ISSUED = "ISSUED", "Issued"
    COMPLIMENTARY = "COMPLIMENTARY", "Complimentary"
    PAID = "PAID", "Paid"


class Invoice(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    issued_on = models.DateField(
        help_text="The date when the invoice was issued", blank=True, null=True
    )
    paid_on = models.DateField(
        help_text="The date when the invoice was paid", blank=True, null=True
    )
    last_checked_on = models.DateField(
        help_text="The date when the invoice status was last checked",
        blank=True,
        null=True,
    )

    challenge = models.ForeignKey(
        to="challenges.Challenge",
        on_delete=models.PROTECT,
        related_name="invoices",
    )

    support_costs_euros = models.PositiveIntegerField(
        help_text="The support contribution in Euros"
    )
    compute_costs_euros = models.PositiveIntegerField(
        help_text="The capacity reservation in Euros"
    )
    storage_costs_euros = models.PositiveIntegerField(
        help_text="The storage costs in Euros"
    )

    internal_invoice_number = models.CharField(
        max_length=16, help_text="The internal invoice number", blank=True
    )
    internal_client_number = models.CharField(
        max_length=8, help_text="The internal client number", blank=True
    )
    internal_comments = models.TextField(
        help_text="Internal comments about the invoice", blank=True
    )

    contact_name = models.CharField(
        max_length=32,
        help_text="Name of the person the invoice should be sent to",
        blank=True,
    )
    contact_email = models.EmailField(
        help_text="Email of the person the invoice should be sent to",
        blank=True,
    )
    billing_address = models.TextField(
        help_text="The physical address of the client", blank=True
    )
    vat_number = models.CharField(
        max_length=32, help_text="The VAT number of the client", blank=True
    )
    external_reference = models.TextField(
        help_text="Optional reference to be included with the invoice for the client",
        blank=True,
    )

    PaymentStatusChoices = PaymentStatusChoices
    payment_status = models.CharField(
        max_length=13,
        choices=PaymentStatusChoices.choices,
        default=PaymentStatusChoices.INITIALIZED,
    )
