'''
Created on 7 oct. 2018

@author: duff
'''
from rest_framework import serializers
from snap.models import ProgrammeBase,EvenementENV, EvenementEPR, EvenementSPR,\
    Evenement, SnapSnapShot, Classe
from snap import serializers as snapserializers
from django.contrib.auth.models import User
class ProgrammeBaseSerializer(serializers.ModelSerializer):
    class Meta:
        model=ProgrammeBase
        fields = '__all__'
        read_only_fields=('user','nom','description','file',)
        
class EvenementENVSerializer(serializers.ModelSerializer):
    evenement=snapserializers.EvenementSerializer(required=False)    
    class Meta:
        model=EvenementENV
        fields='__all__'
        #read_only_fields=('evenement',)

class SimpleSnapShotSerializer(serializers.ModelSerializer):
    image=serializers.ImageField()
    class Meta:
        model=SnapSnapShot
        exclude=('evenement',)
        
class SimpleENVSerializer(serializers.ModelSerializer):   
    class Meta:
        model=EvenementENV
        exclude=('evenement',)
    
class SimpleEPRSerializer(serializers.ModelSerializer): 
    class Meta:
        model=EvenementEPR
        exclude=('evenement',)

        
class SimpleSPRSerializer(serializers.ModelSerializer):
    nb=serializers.SerializerMethodField()
    def get_nb(self,obj):
        return "SSS %s next %s" % (obj.blockId,obj.nextBlockId)
    
    
    class Meta:
        model=EvenementSPR
        exclude=('evenement',)

class SimpleClasseSerializer(serializers.ModelSerializer):
    class Meta:
        model=Classe
        fields='__all__'
              
class VerySimpleEvenementSerializer(serializers.ModelSerializer):
    classe=serializers.SerializerMethodField()
    user_nom=serializers.SerializerMethodField()
    
    def get_user_nom(self,obj):
        return obj.user.username
    
    def get_classe(self,obj):
        serializer=SimpleClasseSerializer(obj.user.eleve.classe)
        return serializer.data
    class Meta:
        model=Evenement
        fields='__all__'
class ReperesEPRSerializer(serializers.ModelSerializer):
    #evenement=serializers.SlugRelatedField(read_only=True,slug_field='time')
    evenement=VerySimpleEvenementSerializer()
    snapshot=SimpleSnapShotSerializer(read_only=True) 
     
    class Meta:
        model=EvenementEPR
        fields=('evenement','type','detail','snapshot')        
        
class SimpleEvenementSerializer(serializers.ModelSerializer):
    evenementepr=SimpleEPRSerializer(many=True)
    evenementspr=SimpleSPRSerializer(many=True)
    environnement=SimpleENVSerializer(many=True)
    class Meta:
        model=Evenement
        fields='__all__'
        depth=0
        
    image=SimpleSnapShotSerializer(many=True,read_only=True)  
    isSpr=serializers.SerializerMethodField()
    
    def get_isSpr(self,obj):
        return obj.type=="SPR"            
    
    

class ResumeSessionSerializer(serializers.Serializer):
    session_key=serializers.CharField(max_length=40)
    nb_evts=user=serializers.IntegerField()
    #user=serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
    user=serializers.IntegerField()
    user_nom=serializers.CharField(source="user__username")
    debut=serializers.DateTimeField()
    fin=serializers.DateTimeField()
    classe_nom=serializers.CharField(source="user__eleve__classe__nom")
    classe_id=serializers.IntegerField(source="user__eleve__classe")