from django.db import models

from base.models import BaseModel
from users.models import CustomUser
from utils import uploadTo


# Create your models here.
class News(BaseModel):
    title = models.CharField(max_length=255)
    content = models.TextField()
    image = models.ImageField(upload_to=uploadTo, blank=True, null=True)
    published_at = models.DateTimeField()
    author = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
