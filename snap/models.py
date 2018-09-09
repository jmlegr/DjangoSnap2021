from django.db import models
from django.contrib.auth.models import User
from django.core.validators import validate_comma_separated_integer_list
from django.db.models import signals

import os
from django.core.files.storage import default_storage
from django.db.models import FileField
from snap.objets import BlockSnap
from django.db.models.fields import related


    

class Classe(models.Model):
    nom= models.CharField(max_length=10)
    def __str__(self):
        return '%s' % self.nom
    
class Eleve(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    classe =models.ForeignKey(Classe,null=True,on_delete=models.SET_NULL)
    prg=models.ForeignKey('ProgrammeBase',null=True,blank=True,
                          on_delete=models.SET_NULL,verbose_name='Programme de la séance')
    def __str__(self):
        return '%s' % self.user.username
    

    
def user_directory_path(instance, filename):
    # file will be uploaded to MEDIA_ROOT/user_<id>/<filename>
    return 'user_{0}/{1}'.format(instance.user.id, filename)

class ProgrammeBase(models.Model):
    #Nom du programme de base
    user=models.ForeignKey(User,on_delete=models.CASCADE) #utilisateur
    nom=models.CharField(max_length=50,null=True,blank=True)
    description = models.CharField(max_length=255, blank=True)
    file=models.FileField(upload_to=user_directory_path)
    creation=models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return '%s (%s)' % (self.nom,self.user_id)
    
class Evenement(models.Model):
    ENVIRONNEMENT='ENV'
    ETAT_PROGRAMME='EPR'
    STRUCTURE_PROGRAMME='SPR'
    SCRIPT='SCR'
    AUTRE='AUT'
    TYPE_EVENEMENT_CHOICES=(
        (ENVIRONNEMENT,'Environnement'),
        (ETAT_PROGRAMME,'Etat du Programme'),
        (STRUCTURE_PROGRAMME,'Structure du Programme'),
        (SCRIPT,'Script'),
        (AUTRE,'Autre évènement'),
        )
    user=models.ForeignKey(User,on_delete=models.CASCADE) #utilisateur
    session_key=models.CharField(max_length=40,null=True)
    programme=models.ForeignKey(ProgrammeBase,null=True, on_delete=models.SET_NULL) #programme de base chargé
    type=models.CharField(max_length=3,choices=TYPE_EVENEMENT_CHOICES, default=AUTRE) #type d'évènement
    time=models.IntegerField() #Temps (local à Snap) de l'évènement
    numero=models.IntegerField() #numero d'ordre de l'évènement, indépendant du type
    creation=models.DateTimeField(auto_now_add=True)
    def toD3(self):
        res={}
        res['id']=self.id
        res['type']=self.type
        res['type_display']=self.get_type_display()
        res['numero']=self.numero
        res['time']=self.time
        return res
    
    def __str__(self):
        return '(%s) %s n°%s' % (self.user,self.get_type_display(),self.numero)
    class Meta:
        ordering=('-creation',)

class EvenementENV(models.Model):
    """
        Evenement lié à la modification de l'environnement
        (chargement/sauvegarde, clics divers )
    """
    ENV_CHOICES=(
        ('LANCE','Lancement (ou relancement) de Snap'),
        ('MENU', 'Clic Menu'),
        ('PARAM','Clic Menu paramètres'),
        ('NEW','Nouveau programme vide'),
        ('LOBA','Chargement programme de Base'),
        ('LOVER','Chargement d\'une version sauvegardée'), # id dans detail 
        ('IMPORT','Importation fichier local'), # normalement suivi d'un EPR  LOAD (pas encore) ou/et SPR OPEN
        ('EXPORT','Exportation fichier local'),        
        ('FULL','Plein écran'),
        ('APP','Ecran application'),
        ('SSCRN','Ecran réduit'),
        ('NSCRN','Ecran normal'),
        ('SBS','Pas à pas'),
        ('GREEN','Clic Green Flag'),
        ('PAUSE','Clic Mise en pause'),
        ('REPR','Clic Reprise'),
        ('STOP','Clic Stop'),
        ('KEY','Evènement Clavier'),
        ('AFFBL','Affichage Blocs'), # category  detail?
        ('AFFVAR','Affichage ou non Variable'), #avec nom en option et valeur en bool   
        ('DROPEX','Drop dans la palette (suppression)'), # normalement suivi d'un évènement suppression 
        ('UNDROP','Undrop'), #origine dans detail
        ('REDROP','Redrop'),   
        ('DUPLIC','Duplication'), #menu dupliquer, detail=JMLid(orig), valueInt=JMLid(copie) 
        ('POPUP','Ouverture popup'),
        ('AUTRE','(Non identifié)'),
        )
    evenement=models.ForeignKey(Evenement,on_delete=models.CASCADE,related_name='environnement')
    type=models.CharField(max_length=6,choices=ENV_CHOICES, default='AUTRE') #type d'évènement
    click=models.BooleanField(default=False)
    key=models.BooleanField(default=False)    
    detail=models.TextField(null=True,blank=True)
    valueBool=models.NullBooleanField(null=True)
    valueInt=models.IntegerField(null=True)
    valueChar=models.CharField(max_length=30,null=True,blank=True)
    #block=models.ForeignKey(Block,on_delete=models.CASCADE)
    
    def toD3(self):
        """rendu json pour d3.js"""
        res={}
        res['d3id']='%s_%s' % (self.evenement.id, self.id) #id pour les data de d3.js
        res['id']=self.id
        res["evenement"]=self.evenement.toD3()
        res['type']=self.type
        res['type_display']=self.get_type_display()
        res['detail']=self.detail
        return res
    
    def __str__(self):
        return '(%s) %s: %s %s' % (self.evenement,self.get_type_display(),self.detail,"(clic)" if (self.click) else "")
    
    class Meta:
        ordering=('-evenement__time',)
        get_latest_by=['evenement__time',]

class SnapProcess(models.Model):
    """
        Process de Snap
    """
    receiver=models.CharField(max_length=30,null=True) #lutin en cause
    topBlockSelector=models.CharField(max_length=30,null=True,) #slector du bloc du haut
    topBlockId=models.PositiveIntegerField(null=True) # id du bloc du haut
    click=models.BooleanField(default=False) #lancement arret sur clic du script
    errorFlag=models.BooleanField(default=False)
    class Meta:
        abstract = True
        ordering = ['receiver','+topBlockId']

def userSnapShot(instance, filename):
        # file will be uploaded to MEDIA_ROOT/user_<id>/<filename>
        return 'user_{0}/SnapShots/{1}'.format(instance.evenement.user.id, filename)
class SnapSnapShot(models.Model):
    evenement=models.ForeignKey(Evenement,on_delete=models.CASCADE,related_name='image')
    image=models.ImageField(upload_to=userSnapShot,blank=True)
    
    def delete(self,*args,**kwargs):
        #ne marche pas sur un delete ou sur un queryset.delete
        # You have to prepare what you need before delete the model
        storage, path = self.image.storage, self.image.path
        # Delete the model before the file
        super(SnapSnapShot, self).delete(*args, **kwargs)
        # Delete the file after the model
        storage.delete(path)
        

    
    
class EvenementEPR(SnapProcess):
    """
        Evenement lié à la modification de l'état du programme
    """
    EPR_CHOICES=(
        ('NEW','Nouveau programme vide'),
        ('LOAD','Programme chargé'), # id dans detail si LOVER, nom du prg de base si LOBA
        ('SAVE','Programme sauvegardé'),
        ('START','Lancement'),
        ('STOP','Arrêt'), #arrêt manuel
        ('FIN','Terminaison'),
        ('PAUSE','Pause'),
        ('REPR','Reprise'),
        ('ERR','Erreur'),
        ('ASK','Demande d\'une entrée utilisateur'),
        ('ANSW','Entrée de l\'utilisateur'), #strockée dans detail
        ('SNP','Snapshot'), #id de l'image dans detail
        ('AUTRE','(Non identifié)'),
        )
    evenement=models.ForeignKey(Evenement,on_delete=models.CASCADE,related_name='evenementepr')
    type=models.CharField(max_length=5,choices=EPR_CHOICES, default='AUTRE') #type d'évènement    
    detail=models.CharField(max_length=100,null=True,blank=True)
    processes=models.CharField(max_length=100,null=True,blank=True) # liste des process en cours, sous la forme "id-nom"
    
    def toD3(self):
        """rendu json pour d3.js"""
        res={}
        res['d3id']='%s_%s' % (self.evenement.id, self.id) #id pour les data de d3.js
        res['id']=self.id
        res["evenement"]=self.evenement.toD3()
        res['type']=self.type
        res['type_display']=self.get_type_display()
        res['detail']=self.detail
        return res
    
    def __str__(self):
        return '(%s) %s: %s %s' % (self.evenement,self.get_type_display(),self.detail,"(clic)" if (self.click) else "")
    
    class Meta:
        ordering=('-evenement__time',)
        get_latest_by=['evenement__time',]

class BlockInput(models.Model):
    """
        Entrée d'une brique
    """
    JMLid=models.IntegerField(null=True) #JMLid du block en cause
    typeMorph=models.CharField(max_length=30,null=True,blank=True)
    rang=models.IntegerField(default=0) #rang de l'entrée
    contenu=models.CharField(max_length=50,null=True,blank=True)#contenu de l'entrée
    isNumeric=models.BooleanField(default=True) 
    isPredicate=models.BooleanField(default=False)
    
    class Meta:
        ordering = ['rang']
        
    def __str__(self):
        return '%s, %s (JML %s)' % (self.rang,self.contenu,self.JMLid)

    
class EvenementSPR(models.Model):
    """
        Evenement lié à la modification de la structure du programme
        pour des raisons d'efficacité à l'enregistrement,
        on ne crée les inputs que lors de la création de la brique,
        ou lors du changement d'une entrée. On pourra les retrouver ensuite.
    """
    SPR_CHOICES=(
        ('DROP','Déplacement d\'un bloc'), #si insertion, droppedTarget indiqué, location=
        ('NEW','Création d\'une brique'),        
        ('DUPLIC','Duplication de bloc' )  ,       
        ('DEL','Suppression d\'un bloc'),
        ('NEWVAR','Création nouvelle variable globale'), #nom dans detail
        ('NEWVARL','Création nouvelle variable locale'), #nom dans detail
        ('DELVAR','Suppression variable'), #nom dans detail
        ('RENVAR','renommage variable'), #nouveau nom dans detail, ancien dans location
        ('RENVARL','renommage variable locale'), #nouveau nom dans detail, ancien dans location
        ('RENVARB','renommage variable de bloc'), #nouveau nom dans detail, ancien dans location
        ('RENVAT','renommage variable, juste le template'), #nouveau nom dans detail, ancien dans location
        ('RENVATL','renommage variable locale, juste le template'), #nouveau nom dans detail, ancien dans location
        ('RENVATB','renommage variable de bloc, juste le template'), #nouveau nom dans detail, ancien dans location
        ('VAL','Changement d\'une valeur'), # on renvois le blockmorph, id de l'entrée dans detail, rang dans location
                                            # si location=null, c'est un CommentMorph normalement (donc contenu dans blockSpec)
        ('+IN','Ajout d\'une entrée'),
        ('-IN','Suppression d\'une entrée'),
        ('NEWVAL','Création et insertion d\'une entrée'), #création + remplacement d'une entrée existante (id remplacée dans détailAction, rang dans location
        ('DROPVAL','Déplacement et insertion d\'une entrée'), #déplacement + remplacement d'une entrée existante (id remplacée dans détailAction
        ('ERR','Erreur'), #erreur détectée, précision dans détail
        ('OPEN','Ouverture de Scripts'),
        ('AUTRE','(Non identifié'),
        )
    evenement=models.ForeignKey(Evenement,on_delete=models.CASCADE,related_name='evenementspr')
    type=models.CharField(max_length=7,choices=SPR_CHOICES, default='AUTRE') #type d'évènement    
    detail=models.TextField(null=True,blank=True)
    location=models.CharField(max_length=30,null=True,blank=True)
    #Informations sur le block    
    blockId=models.IntegerField(null=True) #JMLid du block en cause
    typeMorph=models.CharField(max_length=30,null=True,blank=True) #type du block
    selector=models.CharField(max_length=30,null=True,blank=True) #selector du block 
    blockSpec=models.CharField(max_length=50,null=True,blank=True) #blockSpec du block ou valeur
    category=models.CharField(max_length=30,null=True,blank=True) #categorie du block
    parentId=models.IntegerField(null=True) #JMLid du block parent (ou lieu d'insertion)
    nextBlockId=models.IntegerField(null=True) #JMLid du block suivant
    childId=models.IntegerField(null=True) #JMLid du block enfant (si wrap)
    targetId=models.IntegerField(null=True) #JMLid du block cible (si location)
    inputs=models.ManyToManyField(BlockInput,null=True) #entrée(s) du block
    scripts=models.ManyToManyField('Block') #les blocks de départ des scripts
    def __str__(self):
        return '(%s) %s (%s) %s' % (self.evenement,self.get_type_display(),self.blockId,self.detail if self.detail else '')
    
    def toBlockSnap(self,time,action):
        """
        crée un BlockSnap de base (sans les inputs/nextblocks etc
        """
        return BlockSnap(JMLid=self.blockId,
                         time=time,
                         typeMorph=self.typeMorph,
                         blockSpec=self.blockSpec,
                         selector=self.selector,
                         action=action)
    def addToListeBlockSnap(self,liste,time,action):
        """
        crée et ajoute (récursivement) les BlockSnap dans la liste
        """
        b=self.blockSnap(time, action)
        liste.addBlock(b)
        for i in self.inputs.all():
            bi=BlockSnap(JMLid=i.JMLid,time=time,typeMorph=i.typeMorph,action=action)
            bi.rang=i.rang
            bi.contenu=i.contenu
            b.addInput(bi)
            liste.addBlock(bi)
        return b
    
            
    def toD3(self):
        """rendu json pour d3.js"""
        res={}
        res['d3id']='%s_%s' % (self.evenement.id, self.id) #id pour les data de d3.js
        res['id']=self.id
        res["evenement"]=self.evenement.toD3()
        res['type']=self.type
        res['type_display']=self.get_type_display()
        res['detail']=self.detail
        return res
    def aff(self,niv=0):
        print('type:%s blockId:%s spec:%s morph:%s detail:%s' 
              % (self.type,self.blockId,self.blockSpec,self.typeMorph,self.detail))
        if niv>0:
            print('    loc:%s parentId:%s next:%s child:%s target:%s'
                    % (self.location,self.parentId,self.nextBlockId,self.childId,self.targetId))
        if niv>1:
            print('    inputs',[i for i in self.inputs.all()])
        if niv>2:
            print('    scripts:',[(s, [si for si in s.inputs.all()]) for s in self.scripts.all()])
        
    class Meta:
        ordering=('-evenement__time',)
        get_latest_by=['evenement__time',]

class Block(models.Model):
    """
        definition de base d'un block
    """
    JMLid=models.IntegerField(null=True) #JMLid du block en cause
    typeMorph=models.CharField(max_length=30,null=True,blank=True) #type du block
    selector=models.CharField(max_length=30,null=True,blank=True) #selector du block
    blockSpec=models.CharField(max_length=50,null=True,blank=True) #blockSpec du block
    category=models.CharField(max_length=30,null=True,blank=True) #categorie du block
    #parent=models.OneToOneField('self',null=True,on_delete=models.CASCADE,related_name='fils') #block parent (ou lieu d'insertion)
    parent=models.IntegerField(null=True)
    nextBlock=models.OneToOneField('self',null=True,on_delete=models.SET_NULL,related_name='prec') #block suivant
    #child=models.ForeignKey('Block',null=True,on_delete=models.CASCADE,related_name='child_Block') #block enfant (si wrap)
    inputs=models.ManyToManyField(BlockInput,null=True) #entrée(s) du block (inputSlotMorph ou Cslotmorph
    inputsBlock=models.ManyToManyField('self',null=True,symmetrical=False) #entrée(s) du block qui sont des blocks
 
    def __str__(self):
        return '%s(JML %s, id %s)' %(self.selector,self.JMLid,self.id)
    
class InfoReceived(models.Model):
    block_id=models.IntegerField()
    time=models.IntegerField()
    action=models.CharField(max_length=30,null=True,blank=True)
    blockSpec=models.CharField(max_length=100,null=True,blank=True)
    user=models.CharField(max_length=10)
    
   



class Document(models.Model):
    description = models.CharField(max_length=255, blank=True)
    user=models.ForeignKey(User,null=True,on_delete=models.CASCADE)
    document = models.FileField(upload_to=user_directory_path)
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name='Date de sauvegarde')    
    def __str__(self):
        return '{0} ({1}, {2})'.format(self.description,self.user,self.uploaded_at.strftime('%Y-%m-%d à %H:%M:%S'))

