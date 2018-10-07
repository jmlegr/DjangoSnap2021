'''
Created on 7 oct. 2018

@author: duff
'''
from rest_framework import serializers
from snap.models import ProgrammeBase,EvenementENV, EvenementEPR, EvenementSPR,\
    Evenement
from snap import serializers as snapserializers
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

class SimpleENVSerializer(serializers.ModelSerializer):
    class Meta:
        model=EvenementENV
        exclude=('evenement',)
    
class SimpleEPRSerializer(serializers.ModelSerializer):
    class Meta:
        model=EvenementEPR
        exclude=('evenement',)

class SimpleSPRSerializer(serializers.ModelSerializer):
    class Meta:
        model=EvenementSPR
        exclude=('evenement',)
class SimpleEvenementSerializer(serializers.ModelSerializer):
    evenementepr=SimpleEPRSerializer(many=True)
    evenementspr=SimpleSPRSerializer(many=True)
    environnement=SimpleENVSerializer(many=True)
    class Meta:
        model=Evenement
        fields='__all__'
        depth=0