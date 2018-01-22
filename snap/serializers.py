from django.contrib.auth.models import User, Group
from rest_framework import serializers, reverse
from snap.models import ProgrammeBase, Evenement,  EvenementEPR,\
    EvenementENV,Classe , EvenementSPR, BlockInput, \
    Block, Eleve, Classe
from django.core.serializers import _serializers


class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = ('url', 'username', 'email', 'groups')

class ClasseSerializer(serializers.ModelSerializer):
    class Meta:
        model=Classe 
        fields='__all__'
                  
class EleveSerializer(serializers.ModelSerializer):
    classe=serializers.StringRelatedField()
    class Meta:
        model=Eleve
        fields=('id','classe')
        
class EleveUserSerializer(serializers.ModelSerializer):
    eleve=EleveSerializer()
    class Meta:
        model = User
        fields = ('id', 'username', 'eleve')

class GroupSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Group
        fields = ('url', 'name')

    
        
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

class RecursiveField0(serializers.Serializer): #https://exceptionshub.com/django-rest-framework-nested-self-referential-objects.html
    def to_representation(self, value):
        serializer = self.parent.parent.__class__(value, context=self.context)
        return serializer.data
'''    
class RecursiveField(serializers.Serializer):

    """
    Can be used as a field within another serializer,
    to produce nested-recursive relationships. Works with
    through models, and limited and/or arbitrarily deep trees.
    """
    def __init__(self, **kwargs):
        self._recurse_through = kwargs.pop('through_serializer', None)
        self._recurse_max = kwargs.pop('max_depth', None)
        self._recurse_view = kwargs.pop('reverse_name', None)
        self._recurse_attr = kwargs.pop('reverse_attr', None)
        self._recurse_many = kwargs.pop('many', False)

        super(RecursiveField, self).__init__(**kwargs)

    def to_representation(self, value):
        parent = self.parent
        if isinstance(parent, serializers.ListSerializer):
            parent = parent.parent

        lvl = getattr(parent, '_recurse_lvl', 1)
        max_lvl = self._recurse_max or getattr(parent, '_recurse_max', None)

        # Defined within RecursiveField(through_serializer=A)
        serializer_class = self._recurse_through
        is_through = has_through = True

        # Informed by previous serializer (for through m2m)
        if not serializer_class:
            is_through = False
            serializer_class = getattr(parent, '_recurse_next', None)

        # Introspected for cases without through models.
        if not serializer_class:
            has_through = False
            serializer_class = parent.__class__

        if is_through or not max_lvl or lvl <= max_lvl: 
            serializer = serializer_class(
                value, many=self._recurse_many, context=self.context)

            # Propagate hereditary attributes.
            serializer._recurse_lvl = lvl + is_through or not has_through
            serializer._recurse_max = max_lvl

            if is_through:
                # Delay using parent serializer till next lvl.
                serializer._recurse_next = parent.__class__

            return serializer.data
        else:
            view = self._recurse_view or self.context['request'].resolver_match.url_name
            attr = self._recurse_attr or 'id'
            return reverse(view, args=[getattr(value, attr)],
                           request=self.context['request'])
                           
 '''  
from rest_framework_recursive.fields import RecursiveField
class BlockSerializer(serializers.ModelSerializer):
    #parent=RecursiveField(allow_null=True,required=False)
    nextBlock=RecursiveField(allow_null=True,required=False)
    #SerializerMethodField(read_only=True,method_name='get_truc')
    inputs=BlockInputSerializer(many=True,required=False)
    inputsBlock=RecursiveField(required=False, allow_null=True, many=True)
   
    #RecursiveField(many=True,required=False)
    class Meta:
        model=Block
        fields=('id','JMLid','selector','typeMorph','blockSpec',
                'parent','nextBlock','inputs',
                'inputsBlock',
                )
   
    
    def create(self,validated_data):
        parent=validated_data.pop('parent',None)
        blocks_data=validated_data.pop('inputsBlock',[])
        n_data=validated_data.pop('nextBlock',None)        
        inputs_data=validated_data.pop('inputs',[])
        
        #on traite le nextBlock, lien vers un autre block
        if n_data is not None:
            serBlock=BlockSerializer(data=n_data)
            if serBlock.is_valid():
                nextBlock=serBlock.save()                
        else:
            nextBlock=None
        #creation du block
        block=Block.objects.create(parent=parent,nextBlock=nextBlock,**validated_data)
        #on traite les entrées
        for input_data in inputs_data:
            inp=BlockInput.objects.create(**input_data)
            block.inputs.add(inp)
        #on traite les inputBlocks, lien vers d'autres blocks
        for bl in blocks_data:
            b=BlockSerializer(data=bl)
            if b.is_valid(raise_exception=True):
                i=b.save()
                block.inputsBlock.add(i)            
        return block 
        
 
class EvenementSPRSerializer(serializers.ModelSerializer):
    evenement=EvenementSerializer(required=False)    
    inputs=BlockInputSerializer(required=False, many=True)
    scripts=BlockSerializer(required=False,many=True)
    #structureScripts=serializers.PrimaryKeyRelatedField(read_only=True)
    class Meta:
        model=EvenementSPR
        fields='__all__'
        #read_only_fields=('evenement',)
    
    def create(self, validated_data):       
        evt_data=validated_data.pop('evenement')
        evt_data['type']='SPR'
        evt = Evenement.objects.create(user=self.context['request'].user,**evt_data)
        inputs_data=validated_data.pop('inputs',[])
        scripts_data=validated_data.pop('scripts',[])
        env=EvenementSPR.objects.create(evenement=evt,**validated_data)        
        for input_data in inputs_data:
            inp=BlockInput.objects.create(**input_data)
            env.inputs.add(inp)
        #on ajoute les scripts
        for scr_data in scripts_data:
            scr=BlockSerializer(data=scr_data)
            if scr.is_valid():
                s=scr.save()
                env.scripts.add(s)            
        return env


    