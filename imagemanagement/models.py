from django.db import models
from django.contrib.auth.models import User
import uuid
import base64

# Create your models here.
# class Uploadfiles(models.Model):
#     file = models.ImageField(upload_to='uploads')
#     username = User.username
#     def __init__(self, f, n):
#         id = base64.b64encode(uuid.uuid4().bytes).replace('=', '')
#         self.file = f
#         self.username = n