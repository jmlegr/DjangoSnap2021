from django.db import models
from django.contrib.auth.models import User

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
    
class Point(models.Model):
    x=models.IntegerField()
    y=models.IntegerField()
    
class Bounds(models.Model):
    origin=models.OneToOneField(Point,related_name='origin',on_delete=models.CASCADE)
    corner=models.OneToOneField(Point,related_name='corner',on_delete=models.CASCADE)
    
class Inputs(models.Model):
    valeur=models.CharField(max_length=30,blank=True)
    type=models.CharField(max_length=30,blank=True)
    
class DroppedBlock(models.Model):
    block_id=models.IntegerField()    
    blockSpec=models.CharField(max_length=100,null=True,blank=True)
    category=models.CharField(max_length=30,null=True,blank=True)
    inputs=models.ManyToManyField(Inputs,null=True)
    bounds=models.OneToOneField(Bounds,on_delete=models.CASCADE)
    
class ActionProgrammation(models.Model):
    user = models.ForeignKey(User,on_delete=models.CASCADE)
    time=models.IntegerField()
    action=models.CharField(max_length=30,null=True,blank=True)
    situation=models.CharField(max_length=30,null=True,blank=True)
    typeMorph=models.CharField(max_length=30,null=True,blank=True)
    lastDroppedBlock=models.OneToOneField(DroppedBlock,on_delete=models.CASCADE)
    
    
    
    