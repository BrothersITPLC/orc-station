from django.contrib.auth.models import AbstractUser, BaseUserManager, Group
from django.db import models, transaction

from base.models import BaseModel
from utils import uploadTo


class Department(BaseModel):
    name = models.CharField(max_length=100, unique=True)
    created_by = models.ForeignKey(
        "users.CustomUser",
        on_delete=models.CASCADE,
        related_name="departments",
        null=True,
    )

    def __str__(self):
        return self.name


# Create your models here.
# class CustomUser(BaseModel, AbstractUser):
#     GENDER_CHOICES = [
#         ("Female", "Female"),
#         ("Male", "Male"),
#     ]
#     profile_image = models.ImageField(upload_to="posts/", null=True, blank=True)
#     email_verified = models.BooleanField(default=False)
#     email_verification_token = models.CharField(max_length=1000, blank=True, null=True)
#     gender = models.CharField(max_length=50, choices=GENDER_CHOICES, default="Male")
#     department = models.ForeignKey(
#         Department, on_delete=models.PROTECT, related_name="users", null=True
#     )
#     username = models.CharField(max_length=100, unique=True)
#     phone_number = models.CharField(max_length=100, blank=True, null=True)
#     role = models.ForeignKey(Group, on_delete=models.SET_NULL, null=True, blank=True)
#     assigned_by = models.ForeignKey(
#         "self", null=True, on_delete=models.RESTRICT, name="manager", blank=True
#     )
#     session_token = models.TextField(blank=True, null=True)
#     kebele = models.CharField(max_length=200, blank=True, null=True)
#     woreda = models.ForeignKey(
#         "address.Woreda",
#         on_delete=models.SET_NULL,
#         null=True,
#         blank=True,
#         related_name="users",
#     )

#     current_station = models.ForeignKey(
#         "workstations.WorkStation",
#         null=True,
#         on_delete=models.RESTRICT,
#         name="current_station",
#         blank=True,
#     )

#     def save(self, *args, **kwargs):
#         with transaction.atomic():
#             if self.pk is not None:
#                 self.groups.clear()
#                 if self.role:
#                     self.groups.add(self.role)

#                 old_instance = CustomUser.objects.filter(pk=self.pk).first()
#                 if old_instance and old_instance.profile_image:
#                     if old_instance.profile_image != self.profile_image:
#                         old_instance.profile_image.delete(save=False)

#             super(CustomUser, self).save(*args, **kwargs)

#     # def save(self, *args, **kwargs):
#     #     with transaction.atomic():
#     #         if self.pk is not None:  # Only validate on updates
#     #             self.groups.clear()
#     #             if self.role:
#     #                 self.groups.add(self.role)

#     #             old_instance = CustomUser.objects.filter(pk=self.pk).first()
#     #             if (
#     #                 old_instance.profile_image
#     #                 and old_instance.profile_image != self.profile_image
#     #             ):
#     #                 old_instance.profile_image.delete(save=False)

#     #         super(CustomUser, self).save(*args, **kwargs)

#     def delete(self, *args, **kwargs):
#         with transaction.atomic():
#             if self.profile_image:
#                 self.profile_image.delete(save=False)
#             super(CustomUser, self).delete(*args, **kwargs)

#     def get_latest_status(self):
#         """
#         Returns the most recent status for this user.
#         """
#         latest_status = (
#             UserStatus.objects.filter(user=self).order_by("-created_at").first()
#         )
#         return latest_status.status if latest_status else None

#     class Meta:
#         unique_together = ("email",)

#     def __str__(self):
#         return f"{self.first_name} {self.last_name} ({self.username})"


class CustomUser(BaseModel, AbstractUser):
    GENDER_CHOICES = [
        ("Female", "Female"),
        ("Male", "Male"),
    ]
    profile_image = models.ImageField(upload_to="posts/", null=True, blank=True)
    email_verified = models.BooleanField(default=False)
    email_verification_token = models.CharField(max_length=1000, blank=True, null=True)
    gender = models.CharField(max_length=50, choices=GENDER_CHOICES, default="Male")
    department = models.ForeignKey(
        "users.Department", on_delete=models.PROTECT, related_name="users", null=True
    )
    username = models.CharField(max_length=100, unique=True)
    phone_number = models.CharField(max_length=100, blank=True, null=True)
    role = models.ForeignKey(Group, on_delete=models.SET_NULL, null=True, blank=True)
    assigned_by = models.ForeignKey(
        "self", null=True, on_delete=models.RESTRICT, name="manager", blank=True
    )
    session_token = models.TextField(blank=True, null=True)
    kebele = models.CharField(max_length=200, blank=True, null=True)
    woreda = models.ForeignKey(
        "address.Woreda",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users",
    )
    current_station = models.ForeignKey(
        "workstations.WorkStation",
        null=True,
        on_delete=models.RESTRICT,
        name="current_station",
        blank=True,
    )

    def get_latest_status(self):
        """
        Returns the most recent status for this user.
        """
        latest_status = (
            UserStatus.objects.filter(user=self).order_by("-created_at").first()
        )
        return latest_status.status if latest_status else None

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.username})"

    class Meta:
        unique_together = ("email",)


class UserStatus(BaseModel):
    status_choices = [("active", "Active"), ("inactive", "Inactive")]
    status = models.CharField(
        max_length=10,
        choices=status_choices,
        null=True,
    )
    changed_by = models.ForeignKey(
        "users.CustomUser",
        on_delete=models.RESTRICT,
        related_name="status_changes",
    )
    report = models.ForeignKey(
        "users.Report",
        on_delete=models.RESTRICT,
        related_name="status_changes",
        null=True,
        blank=True,
    )
    user = models.ForeignKey(
        "users.CustomUser", on_delete=models.CASCADE, related_name="user_status"
    )


class Report(BaseModel):
    employee = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name="employee_reports"
    )
    report = models.TextField()

    reporter = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name="reporter_reports"
    )
    station = models.ForeignKey(
        "workstations.WorkStation", on_delete=models.CASCADE, related_name="reports"
    )
    is_seen = models.BooleanField(default=False)

    def __str__(self):
        return self.report
