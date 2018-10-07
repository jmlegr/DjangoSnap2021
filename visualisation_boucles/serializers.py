'''
Created on 7 oct. 2018

@author: duff
'''
from rest_framework import serializers
from snap.models import ProgrammeBase,EvenementENV
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