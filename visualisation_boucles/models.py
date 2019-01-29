from django.db import models
from django_mysql.models import JSONField
from django.contrib.auth.models import User
from snap.models import ProgrammeBase
# Create your models here.

class Reconstitution(models.Model):
    user=models.ForeignKey(User,on_delete=models.CASCADE) #utilisateur
    session_key=models.CharField(max_length=40)
    programme=models.TextField()
    creation=models.DateTimeField(auto_now_add=True)
    modification=models.DateTimeField(auto_now=True,null=True)
    detail_json = JSONField()  # requires Django-Mysql package
