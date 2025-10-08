from decimal import Decimal

from django.db.models import Case, DecimalField, F, Value, When, Window
from django.db.models.functions import Lag


def annotate_revenue_on_checkins(checkins_queryset):
    """
    Takes a Checkin queryset and returns a new queryset annotated with
    incremental weight and revenue, calculated at the database level.

    Usage:
        filtered_checkins = Checkin.objects.filter(...)
        revenue_qs = annotate_revenue_on_checkins(filtered_checkins)
        # revenue_qs now has .incremental_weight and .revenue attributes
    """

    window = Window(
        expression=Lag("net_weight", default=Decimal(0)),
        partition_by=[F("localJourney_id"), F("declaracion_id")],
        order_by=F("checkin_time").asc(),
    )

    # 2. Annotate the queryset with the previous weight, calculate the
    #    incremental weight (ensuring it's not negative), and then the revenue.
    annotated_queryset = (
        checkins_queryset.annotate(
            # Get the previous weight using the window function
            previous_net_weight=window
        )
        .annotate(
            # Calculate the incremental weight
            incremental_weight_raw=F("net_weight")
            - F("previous_net_weight")
        )
        .annotate(
            # Ensure incremental weight is not less than 0, just like max(..., 0)
            incremental_weight=Case(
                When(incremental_weight_raw__lt=0, then=Value(Decimal(0))),
                default=F("incremental_weight_raw"),
                output_field=DecimalField(),
            )
        )
        .annotate(
            # Finally, calculate the revenue on the database side
            revenue=(
                F("incremental_weight")
                * (F("unit_price") / Decimal(100))
                * (F("rate") / Decimal(100))
            )
        )
    )

    return annotated_queryset
