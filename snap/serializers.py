from django.contrib.auth.models import User, Group
from rest_framework import serializers
from snap.models import ProgrammeBase, Evenement,  EvenementEPR,\
    EvenementENV,Classe , EvenementSPR, BlockInput


class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = ('url', 'username', 'email', 'groups')


class GroupSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Group
        fields = ('url', 'name')

class ClasseSerializer(serializers.ModelSerializer):
    class Meta:
        model=Classe        
        
class ProgrammeBaseSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model=ProgrammeBase
        fields = '__all__'
        read_only_fields=('user',)
        
    def create(self, validated_data):        
        prg = ProgrammeBase.objects.create(user=self.context['request'].user,**validated_data)
        return prg
        
class ProgrammeBaseSuperuserSerializer(serializers.HyperlinkedModelSerializer):
    user=serializers.PrimaryKeyRelatedField(queryset=User.objects.all(),required=False)
    class Meta:
        model=ProgrammeBase
        fields = '__all__'
    
        
class EvenementSerializer(serializers.ModelSerializer):
    #type=serializers.SerializerMethodField()
    user=serializers.PrimaryKeyRelatedField(read_only=True)
    class Meta:
        model=Evenement
        fields='__all__'
        read_only_fields=('user',)
    """
    def get_type(self,obj):
        return obj.get_type_display()
    """
    def create(self, validated_data):        
        evt = Evenement.objects.create(user=self.context['request'].user,**validated_data)
        return evt
        
class EvenementEPRSerializer(serializers.ModelSerializer):
    evenement=EvenementSerializer(required=False)
    class Meta:
        model=EvenementEPR
        fields='__all__'
        #read_only_fields=('evenement',)
    
    def create(self, validated_data):       
        evt_data=validated_data.pop('evenement')
        evt_data['type']='EPR'
        evt = Evenement.objects.create(user=self.context['request'].user,**evt_data)
        epr=EvenementEPR.objects.create(evenement=evt,**validated_data)        
        return epr

class EvenementENVSerializer(serializers.ModelSerializer):
    evenement=EvenementSerializer(required=False)    
    class Meta:
        model=EvenementENV
        fields='__all__'
        #read_only_fields=('evenement',)
    
    def create(self, validated_data):    
        evt_data=validated_data.pop('evenement')
        evt_data['type']='ENV'
        evt = Evenement.objects.create(user=self.context['request'].user,**evt_data)
        env=EvenementENV.objects.create(evenement=evt,**validated_data)
        return env

class BlockInputSerializer(serializers.ModelSerializer):
    class Meta:
        model=BlockInput
        fields='__all__'
        
class EvenementSPRSerializer(serializers.ModelSerializer):
    evenement=EvenementSerializer(required=False)    
    inputs=BlockInputSerializer(required=False, many=True)
    class Meta:
        model=EvenementSPR
        fields='__all__'
        #read_only_fields=('evenement',)
    
    def create(self, validated_data):       
        evt_data=validated_data.pop('evenement')
        evt_data['type']='ENV'
        evt = Evenement.objects.create(user=self.context['request'].user,**evt_data)
        inputs_data=validated_data.pop('inputs',[])
        env=EvenementSPR.objects.create(evenement=evt,**validated_data)        
        for input_data in inputs_data:
            inp=BlockInput.objects.create(**input_data)
            env.inputs.add(inp)
        return env
