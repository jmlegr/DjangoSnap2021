from django.db import models
from django.contrib.auth.models import User


    
class InfoReceived(models.Model):
    block_id=models.IntegerField()
    time=models.IntegerField()
    action=models.CharField(max_length=30,null=True,blank=True)
    blockSpec=models.CharField(max_length=100,null=True,blank=True)
    user=models.CharField(max_length=10)
    
class Point(models.Model):
    x=models.IntegerField()
    y=models.IntegerField()
    def __str__(self):
        return '(%s,%s)' % (self.x,self.y)
    
class Bounds(models.Model):
    origin=models.OneToOneField(Point,related_name='origin',on_delete=models.CASCADE)
    corner=models.OneToOneField(Point,related_name='corner',on_delete=models.CASCADE)
    
class Inputs(models.Model):
    valeur=models.CharField(max_length=30,blank=True)
    type=models.CharField(max_length=30,blank=True)
    def __str__(self):
        return '%s (%s)' % (self.valeur,self.type)
    
class DroppedBlock(models.Model):
    block_id=models.IntegerField()    
    blockSpec=models.CharField(max_length=100,null=True,blank=True)
    category=models.CharField(max_length=30,null=True,blank=True)
    inputs=models.ManyToManyField(Inputs,null=True)
    bounds=models.OneToOneField(Bounds,on_delete=models.CASCADE)
    parent_id=models.IntegerField(null=True)
    def __str__(self):
        return '%s (%s)' % (self.blockSpec,self.block_id)
    
class ActionProgrammation(models.Model):
    user = models.ForeignKey(User,on_delete=models.CASCADE)
    time=models.IntegerField()
    action=models.CharField(max_length=30,null=True,blank=True)
    sens=models.SmallIntegerField(default=0), #0: normal, -1:undo, +1:redo
    situation=models.CharField(max_length=30,null=True,blank=True)
    typeMorph=models.CharField(max_length=30,null=True,blank=True)
    lastDroppedBlock=models.OneToOneField(DroppedBlock,on_delete=models.CASCADE)
    
    def __str__(self):
        return '(%s) %s %s' % (self.user_id,self.time,self.action)

def user_directory_path(instance, filename):
    # file will be uploaded to MEDIA_ROOT/user_<id>/<filename>
    return 'user_{0}/{1}'.format(instance.user.id, filename)

class Document(models.Model):
    description = models.CharField(max_length=255, blank=True)
    user=models.ForeignKey(User,null=True,on_delete=models.CASCADE)
    document = models.FileField(upload_to=user_directory_path)
    uploaded_at = models.DateTimeField(auto_now_add=True)    
    def __str__(self):
        return '{0} ({1}, {2})'.format(self.description,self.user,self.uploaded_at.strftime('%Y-%m-%d à %H:%M:%S'))
    
    