from django.db import models

# Create your models here.
class Question(models.Model):
    question_text = models.CharField(max_length=200)
    pub_date = models.DateTimeField('date published')
    
class InfoReceived(models.Model):
    block_id=models.IntegerField()
    time=models.IntegerField()
    action=models.CharField(max_length=30,null=True,blank=True)
    blockSpec=models.CharField(max_length=100,null=True,blank=True)
    user=models.CharField(max_length=10)