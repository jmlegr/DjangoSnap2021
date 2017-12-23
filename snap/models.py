from django.db import models
from django.contrib.auth.models import User


def user_directory_path(instance, filename):
    # file will be uploaded to MEDIA_ROOT/user_<id>/<filename>
    return 'user_{0}/{1}'.format(instance.user.id, filename)

class ProgrammeBase(models.Model):
    #Nom du programme de base
    user=models.ForeignKey(User,on_delete=models.CASCADE) #utilisateur
    nom=models.CharField(max_length=50,null=True,blank=True)
    file=models.FileField(upload_to=user_directory_path)
    creation=models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return '%s (%s)' % (self.nom,self.user_id)
    
class Evenement(models.Model):
    ENVIRONNEMENT='ENV'
    ETAT_PROGRAMME='EPR'
    STRUCTURE_PROGRAMME='SPR'
    AUTRE='AUT'
    TYPE_EVENEMENT_CHOICES=(
        (ENVIRONNEMENT,'Environnement'),
        (ETAT_PROGRAMME,'Etat du Programme'),
        (STRUCTURE_PROGRAMME,'Structure du Programme'),
        (AUTRE,'Autre évènement'),
        )
    user=models.ForeignKey(User,on_delete=models.CASCADE) #utilisateur
    programme=models.ForeignKey(ProgrammeBase,null=True, on_delete=models.CASCADE) #programme de base chargé
    type=models.CharField(max_length=3,choices=TYPE_EVENEMENT_CHOICES, default=AUTRE) #type d'évènement
    time=models.IntegerField() #Temps (local à Snap) de l'évènement
    numero=models.IntegerField() #numero d'ordre de l'évènement, indépendant du type
    creation=models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering=('-creation',)

class EvenementENV(models.Model):
    """
        Evenement lié à la modification de l'environnement
        (chargement/sauvegarde, clics divers )
    """
    ENV_CHOICES=(
        ('MENU', 'Clic Menu'),
        ('PARAM','Clic Menu paramètres'),
        ('NEW','Nouveau programme vide'),
        ('LOBA','Chargement programme de Base'),
        ('LOVER','Chargement d\'une version sauvegardée'),
        ('IMPORT','Importation fichier local'),
        ('EXPORT','Exportation fichier local'),
        ('FSCR','Plein écran'),
        ('SSCR','Ecran réduit'),
        ('SBS','Pas à pas'),
        ('GREEN','Clic Green Flag'),
        ('PAUSE','Clic Mise en pause'),
        ('REPR','Clic Reprise'),
        ('STOP','Clic Stop'),
        ('KEY','Lancement par une touche'),
        ('AFFBL','Affichage Blocs'),
        ('AFFVAR','Affichage ou non Variable'), #avec nom en option et valeur en bool        
        ('AUTRE','(Non identifié)'),
        )
    evenement=models.ForeignKey(Evenement,on_delete=models.CASCADE)
    type=models.CharField(max_length=6,choices=ENV_CHOICES, default='AUTRE') #type d'évènement
    click=models.BooleanField(default=False)
    key=models.BooleanField(default=False)    
    detail=models.CharField(max_length=30,null=True,blank=True)
    valueBool=models.NullBooleanField(null=True)
    valueInt=models.IntegerField(null=True)
    valueChar=models.CharField(max_length=30,null=True,blank=True)
    #block=models.ForeignKey(Block,on_delete=models.CASCADE)
    class Meta:
        ordering=('-evenement__creation',)

class EvenementEPR(models.Model):
    """
        Evenement lié à la modification de l'état du programme
    """
    EPR_CHOICES=(
        ('NEW','Nouveau programme vide'),
        ('LOAD','Programme chargé'),
        ('RUN','Lancement'),
        ('STOP','Arrêt'), #arrêt manuel
        ('FIN','Terminaison'),
        ('PAUSE','Pause'),
        ('REPR','Reprise'),
        ('ERR','Erreur'),
        ('AUTRE','(Non identifié)'),
        )
    evenement=models.ForeignKey(Evenement,on_delete=models.CASCADE)
    type=models.CharField(max_length=5,choices=EPR_CHOICES, default='AUTRE') #type d'évènement
    click=models.BooleanField()
    detail=models.CharField(max_length=30,null=True,blank=True)
    #block=models.ForeignKey(Block,on_delete=models.CASCADE)
    class Meta:
        ordering=('-evenement__creation',)

       
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



class Document(models.Model):
    description = models.CharField(max_length=255, blank=True)
    user=models.ForeignKey(User,null=True,on_delete=models.CASCADE)
    document = models.FileField(upload_to=user_directory_path)
    uploaded_at = models.DateTimeField(auto_now_add=True)    
    def __str__(self):
        return '{0} ({1}, {2})'.format(self.description,self.user,self.uploaded_at.strftime('%Y-%m-%d à %H:%M:%S'))
    
    