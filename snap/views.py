from django.shortcuts import render, render_to_response, get_object_or_404

# Create your views here.

from django.http import HttpResponse
import datetime
from django.contrib.auth.decorators import login_required
import json
from snap.models import InfoReceived, Document, Classe, Eleve, EvenementSPR
from snap.forms import DocumentForm

from django.template.loader import render_to_string
from django.core.files.storage import FileSystemStorage
#from wsgiref.util import FileWrapper
from rest_framework import viewsets, status, serializers
from snap.serializers import ProgrammeBaseSerializer, UserSerializer, GroupSerializer,\
            EvenementSerializer, ProgrammeBaseSuperuserSerializer,\
            EvenementEPRSerializer, EvenementENVSerializer, EvenementSPRSerializer,\
            BlockSerializer, EleveUserSerializer, EvenementSPROpenSerializer
from snap.models import ProgrammeBase, Evenement, EvenementEPR, EvenementENV,\
Block, SnapSnapShot
from django.contrib.auth.models import User, Group
from django.http.response import HttpResponseRedirect, JsonResponse
from django.urls.base import reverse
from django.db.models import Q
from rest_framework.decorators import list_route, detail_route, api_view,\
    renderer_classes
from rest_framework.response import Response
from textwrap import indent
from rest_framework.renderers import JSONRenderer
from django.core.files.base import ContentFile

import copy 
from snap.objets import BlockSnap, CytoElements, ListeBlockSnap

def aff(r,message='JSON'):
    print(message)
    print(json.dumps(r,sort_keys=True,indent=3,))

class UserViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = UserSerializer


class GroupViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows groups to be viewed or edited.
    """
    queryset = Group.objects.all()
    serializer_class = GroupSerializer

class ProgrammeBaseViewset(viewsets.ModelViewSet):
    """
    API Endpoint pour Programme de Base
    """
    queryset=ProgrammeBase.objects.all();
    #serializer_class=ProgrammeBaseSerializer
    def get_serializer_class(self):
        if self.request.user.is_superuser:
            return ProgrammeBaseSuperuserSerializer
        return ProgrammeBaseSerializer

class EvenementViewset(viewsets.ModelViewSet):
    """
    API Endpoint pour Evenement
    """
    queryset=Evenement.objects.all()
    serializer_class=EvenementSerializer

class EvenementEPRViewset(viewsets.ModelViewSet):
    """
    API Endpoint pour EvenementEPR (Evenement Etat du Programme)
    """
    queryset=EvenementEPR.objects.all()
    serializer_class=EvenementEPRSerializer

    def perform_create(self, serializer):
        '''
         création d'une image en cas d'evenement 'SNP'
        '''
        from rest_framework.exceptions import ValidationError

        data = self.request.data
        epr=serializer.save()
        if epr.type=='SNP':
            img=self.snapShot(epr.evenement,data.get('image64'),data.get('detail',''))
            epr.detail='%s' % img.id
            epr.save()        
        return epr
    
    def snapShot(self,evenement,image_b64,detail):        
        '''
        crée une image liée à l'évènement. image_b64 est la version string en base64 de l'image
        '''
        theformat, imgstr = image_b64.split(';base64,')
        ext = theformat.split('/')[-1]
        time=datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")+"_timesnap%s" % evenement.time
        #time=datetime.datetime.now()
        data = ContentFile(base64.b64decode(imgstr), 
                           name='snapshotuser_%s_%s_%s_%s.%s' %(evenement.user.id,
                                                          time,
                                                          evenement.id,
                                                          detail,
                                                          ext))
        img=SnapSnapShot.objects.create(evenement=evenement,image=data)
        return img
    
class EvenementENVViewset(viewsets.ModelViewSet):
    """
    API Endpoint pour EvenementENV (Evenement Changement de l'environnement)
    """
    queryset=EvenementENV.objects.all()
    serializer_class=EvenementENVSerializer
    
    @list_route()
    def users(self,request):
        """
        renvoie la liste des utilisateurs ayant lancé une session snap
        """        
        lst=EvenementENV.objects.filter(type='LANCE').values_list('evenement__user',flat=True)
        users=User.objects.filter(id__in=lst)
        #users=User.objects.all()
        print (users)
        page = self.paginate_queryset(users)
        if page is not None:
            serializer = EleveUserSerializer(page, many=True,context={'request': request})
            return self.get_paginated_response(serializer.data)

        serializer = EleveUserSerializer(users, many=True,context={'request': request})
        return Response(serializer.data)

    @list_route()
    def sessions(self,request):
        evs=EvenementENV.objects.filter(type='LANCE').order_by('-evenement__creation')
        page = self.paginate_queryset(evs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(evs, many=True)
        return Response(serializer.data)
    
    @detail_route()
    def sessionsUser(self,request,pk=None):
        if (pk is None) or (pk=='0'):
            return self.sessions(request)
        try:
            u=User.objects.get(id=pk)
        except:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        evs=EvenementENV.objects.filter(type='LANCE').filter(evenement__user=u).order_by('-evenement__creation')
        page = self.paginate_queryset(evs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(evs, many=True)
        return Response(serializer.data)
    
        

class EvenementSPROpenViewset(viewsets.ModelViewSet):
    """
    API Endpoint renvois les SPR "OPEN")
    """
    queryset=EvenementSPR.objects.filter(type='OPEN')
    serializer_class=EvenementSPROpenSerializer
    
    @list_route()
    def users(self,request):
        """
        renvoie la liste des utilisateurs ayant lancé une session snap
        """        
        lst=EvenementSPR.objects.filter(type='OPEN').values_list('evenement__user',flat=True)
        users=User.objects.filter(id__in=lst)
        #users=User.objects.all()
        print (users)
        page = self.paginate_queryset(users)
        if page is not None:
            serializer = EleveUserSerializer(page, many=True,context={'request': request})
            return self.get_paginated_response(serializer.data)

        serializer = EleveUserSerializer(users, many=True,context={'request': request})
        return Response(serializer.data)
    
    @list_route()
    def opens(self,request):
        evs=EvenementSPR.objects.filter(type='OPEN').order_by('-evenement__creation')
        page = self.paginate_queryset(evs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(evs, many=True)
        return Response(serializer.data)
    
    @detail_route()
    def openUser(self,request,pk=None):
        if (pk is None) or (pk=='0'):            
            return self.opens(request)
        try:
            u=User.objects.get(id=pk)
        except:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        evs=EvenementSPR.objects.filter(type='OPEN').filter(evenement__user=u).order_by('-evenement__creation')
        page = self.paginate_queryset(evs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(evs, many=True)
        return Response(serializer.data)
    
    @classmethod
    def constructionListeOpen(self,pk=None):
        """
        reconstitution du programme chargé
        """
        def traiteBlock(b):
            inputs,nextBlocks=copyLastInputs(b)
            resultat={
                'id':b.id, 'JMLid':b.JMLid,
                'selector':b.selector, 'blockSpec':b.blockSpec,
                'category':b.category,
                'typeMorph':b.typeMorph,
                'parent':b.parent,
                'inputs':inputs,                
                }
            #if b.nextBlock: nextBlock={'source':b.JMLid,'target':b.nextBlock.JMLid}
            if b.nextBlock: 
                nextBlocks.append({'source':b.JMLid,'target':b.nextBlock.JMLid,'type':'nextblock'})
                resultat['nextBlock']=b.nextBlock.JMLid
            else: 
                resultat['nextBlock']=None        
            return resultat, nextBlocks
        def parcoursBlock(b):
            """
        contruction de :
            liste: liste hiérarchisée des blocks avec
                "JMLid": JMLid du bloc,
                "blockSpec":
                "category": toujours à null, à vérifier ou supprimer?
                "id": id SQL
                "nextBlock": JMLid du block suivant s'il existe
                "parent": JMLid du block précédent ou?
                "selector":
                "typeMorph":
                "inputs": tableau des input cf listeInputs [
                     {
                        "JMLid": JMLid de l'input,
                        "conteneur": JMLid du block contenant l'input,
                        "contenu": contenu de l'input, 
                                    soit une valeur 
                                    soit une liste hiérarchisée des blocks,
                                    
                        "id": id SQL,
                        "parent": block précédent ou contenant,
                        "rang": rang de l'input dans la liste,
                        "typeMorph", 
                        "selector", "blockSpec" si c'est un block d'instruction
            nextBlocks: liste des liens {source,target,type=nextBlock}
        """ 
            liste=[]
            nextLiens=[]
            while True:
                res,nextBlocks=traiteBlock(b)
                liste.append(res)
                #if nextLien is not None: 
                #    nextLiens.append(nextLien)
                nextLiens+=nextBlocks
                if b.nextBlock:
                    b=b.nextBlock
                else:
                    break;        
            return liste,nextLiens
    
        def copyLastInputs(b):
            """
            renvoie une liste des inputs contenant
                soit un input de type valeur (le contenu n'est pas une liste)
                soit un input de type block (le contenu est alors ce block et ses suivants)
                -> le block est donc répété en début de contenu!
                -> on peut faire la différence car le block "juste input" ne contient pas de blockSpec ou selector
            """
            inputs=[]
            nextBlocks=[]
            #on parcourt tous les inputs
            for inputB in b.inputs.all():
                inputs.append({
                        'id':inputB.id,'JMLid':inputB.JMLid,
                        'typeMorph':inputB.typeMorph,                                                       
                        'rang':inputB.rang,
                        'contenu':inputB.contenu,
                        'conteneur':b.JMLid,
                        'parent':b.JMLid,})
            #on parcours les inputs "blocks" (et on les rajoute)
            for inputBlock in b.inputsBlock.all():
            #recherche de l'input correspondant
                inputB=b.inputs.filter(JMLid=inputBlock.JMLid)            
                if inputB:
                    #on traite le block
                    result,nextBlocks=parcoursBlock(inputBlock)
                    for r in result:
                        r['conteneur']=b.JMLid
                        r['typeInput']='block'
                    inputs[inputB[0].rang]['contenu']=result                    
                    #inputs[inputB[0].rang]['blockConteneur']=b.JMLid            
            return inputs,nextBlocks
                        
        #récupération de l'évènement correspondant à l'ouverture d'un fichier
        # (id donnée ou dernier)
        if pk is not None:        
            evo=EvenementSPR.objects.get(id=pk)
        else:
            evo=EvenementSPR.objects.filter(type='OPEN').latest('evenement__creation')
        #on récupère le block de tête
        block=evo.scripts.all()[0]
        #construction de la liste hiérarchisée des blocs et des liens "nextblock"
        liste,nextLiens=parcoursBlock(block)    
        #ret,inp,nodes,liens=self.renderOpen(liste)
        #préparation de la liste et création de tous les liens
        nodes,liens=self.renderOpen(liste)        
        #return liste,nextLiens,ret,inp,nodes,liens
        return nodes,liens
    
    @detail_route()
    def listeOpen(self,request,pk=None):
        liste,nextLiens,ret,inp,nodes,liens=self.constructionListeOpen(pk)
        return render(request,'liste_open.html',{'tdOpen':ret,'nodes':liste,'links':nextLiens})
    
    
    @classmethod
    def renderOpen(self,listePrgInitial,nbTd=1):
        """
        construit la liste des noeuds et des liens pour le rendu cytoscape du programme chargé
        listePrgInitial est la liste hiéarchisée représentant le programme chargé
        les noeuds sont dans un dictionnaire de clef JMLid 
        (pour traiter l'évolution du block au cours du temps, ultérieurement)
        chaque noeud est sous la même forme que listePrgInitial, avec en plus
         "valeur" : sera le label du noeud, 
             prend soit la valeur du contenu si c'est un inputSlotMorph,
             soit le nom du block
         "childs" contient le rang et l'id des tous les inputs ("vrai" ou wraps)
         "wraps" contient l'id des blocks wrappés dans le block en cours
         "trucs" devrait être toujours vide
        et en moins:
         "parent" est enlevé pour éviter les soucis de compound
         "id" SQL
         "inputs" et "contenu" qui sont intégrés comme noeuds et gérés avec les liens
        
         
        lies liens sont de type "child" pour un input, "typeNextblock" pour un nextblock et 
            "wrapin" pour un lien block contenu, block contenant 
        """
        
        def traiteBlock(b):
            #print('BLOC TRAITE',b)
            nodes={}
            liens=[]
            if b['typeMorph']!='InputSlotMorph': #(ou 'blockSpec' in b)
                #c'est un block
                nodes[b['JMLid']]={
                    'JMLid':b['JMLid'],
                    'selector':b['selector'] if 'selector' in b else None,
                     'blockSpec':'%s' % b['blockSpec'],
                    'typeMorph':b['typeMorph'], 
                    #TODO: pb category toujours à NONE?
                    'category':b['category'] if 'category' in b else None,
                    #'parent':'%s' %b['parent'] pb pour compound
                    'nextBlock': b['nextBlock'],
                    'valeur':b['blockSpec'],
                    'conteneur':b['conteneur'] if 'conteneur' in b else None  ,                                        
                    'rang':b['rang'] if 'rang' in b else None
                    }
                if b['nextBlock']:
                    liens.append({'source':b['JMLid'],'target':b['nextBlock'],'type':'typeNextblock'})
            else:
                #c'est inputSlotMorph
                nodes[b['JMLid']]={
                    'JMLid':b['JMLid'],
                    'typeMorph':b['typeMorph'],        

                    #spécifique
                    'conteneur':b['conteneur'],
                    'valeur':b['contenu'],
                    'rang':b['rang']                              
                    }
            if 'inputs' in b:
                nodes[b['JMLid']]['wraps']=[]
                nodes[b['JMLid']]['childs']={}
                nodes[b['JMLid']]['trucs']={}
                for i in b['inputs']:                    
                    if i['typeMorph'] in ['CommandBlockMorph','CSlotMorph','ReporterBlockMorph']: # pas la peine de tester les chapeaux?
                        #il y a des sous-blocks, on ne répète pas celui en cours
                        #mais on traite son contenu
                        nodes[b['JMLid']]['childs'][i['rang']]=i['JMLid']
                        for r in i['contenu']:
                            nodes[b['JMLid']]['wraps'].append(r['JMLid'])
                            n,l=traiteBlock(r)
                            #for nn in n:
                            #    nn['parent']=n['conteneur']
                            #on ajoute dans la liste
                            for nn in n:
                                nodes[nn]=n[nn]
                            liens+=l
                            liens.append({'target':b['JMLid'],'source':i['contenu'][0]['JMLid'], 'type':'wrapin'})
                    else:
                        #nodes[b['JMLid']]['childs'].append(i['JMLid'])
                        nodes[b['JMLid']]['childs'][i['rang']]=i['JMLid']
                        n,l=traiteBlock(i)
                        for nn in n:
                            nodes[nn]=n[nn]
                        liens+=l
                        liens.append({'source':b['JMLid'],'target':i['JMLid'], 'type':'child'})
                        if 'contenu' in b and type(b['contenu'])==list:
                            #ce n'est pas une valeur mais une liste de block
                            for i in b['contenu']:
                                nodes[b['JMLid']]['trucs'][i['rang']]=i['JMLid']
                                n,l=traiteBlock(i)
                                for nn in n:
                                    nodes[nn]=n[nn]
                                liens+=l
            return nodes,liens            
                        
        #ret=[]
        #inputs={}
        nodes={}
        liens=[]
        #aff(listePrgInitial,'INITI')
        for block in listePrgInitial:            
            n,l=traiteBlock(block)
            for nn in n:
                nodes[nn]=n[nn]
            liens+=l
        #aff(nodes,'NODES')
        #aff(liens,'LIENS')
        return nodes,liens
        """
        for i in listePrgInitial:
            if 'blockSpec' in i: ret.append(
                        {'nbTd':range(nbTd),
                         'id':i['id'], 'JMLid':i['JMLid'],
                         'selector':i['selector'], 'blockSpec':'%s' % i['blockSpec'],
                         'typeMorph':i['typeMorph'], 'parent':'%s' %i['parent']        
                         })
            else:
                ret.append({'nbTd':range(nbTd+1),'contenu': '%s' % i})
            if 'inputs' in i:
                #on range les inputs par JMLid, chaque élément contient un temps+liste des inputs(childs)
                inputs[i['JMLid']]=[{'time':0,'parent':i['parent'],
                                     'blockSpec':i['blockSpec'] if 'blockSpec' in i else None,
                                     'selector': i['selector'] if 'selector' in i else None,
                                     'nextBlock':i['nextBlock'] if 'nextBlock' in i else None,
                                     'conteneur': i['conteneur'] if 'conteneur' in i else None,
                                     'parent':i['parent'] if 'parent' in i else None,
                                     'childs':{}}]
                ipt=inputs[i['JMLid']][0]['childs']
                if 'selector' in i and i['selector']=='reportGetVar':
                    ipt[0]={'valeur':i['blockSpec'],'JMLid':None,
                            'id':i['JMLid'],
                            'type':i['typeMorph'],
                            'selector':i['selector'],
                            'parent':i['parent']}
                for inp in i['inputs']:
                    if inp['typeMorph'] in ['InputSlotMorph',]:
                        ipt[inp['rang']]={'valeur':inp['contenu'],'JMLid':None,
                                          'id':inp['JMLid'],
                                          'type':inp['typeMorph'],
                                          #'selector':inp['selector'] if 'selector' in inp else None,
                                          #'blockSpec':inp['blockSpec'] if 'blockSpec' in inp else None,
                                          'parent':inp['parent']}
                        rt,ip=self.renderOpen([inp['contenu']],nbTd+1)
                        inputs={**inputs,**ip}
                        ret+=rt
                                            
                    else:                       
                        #inputs[i['JMLid']][inp['rang']]={'valeur':inp['contenu'][0]['blockSpec'],'JMLid':inp['contenu'][0]['JMLid']}
                        ipt[inp['rang']]={'valeur':None,'JMLid':inp['contenu'][0]['JMLid'],
                                          'id':inp['JMLid'],
                                          'type':inp['typeMorph'],
                                          #'selector':inp['selector'] if 'selector' in inp else None,
                                          #'blockSpec':inp['blockSpec'] if 'blockSpec' in inp else None,
                                          'parent':inp['parent']}
                        rt,ip=self.renderOpen(inp['contenu'],nbTd+1)
                        inputs={**inputs,**ip}
                        ret+=rt
        #print ('inputs',inputs)
        return ret,inputs,nodes,liens
        """
       
    
   
    @classmethod
    def suivant(self,ev):
        try:
            suivant=EvenementSPR.objects.filter(type='OPEN',
                                            evenement__user=ev.evenement.user,
                                            evenement__creation__gt=ev.evenement.creation).earliest('evenement__creation')
        except:
            suivant=None
        return suivant
    @classmethod
    def precedent(self,ev):
        precedent=EvenementSPR.objects.filter(type='OPEN',
                                            evenement__user=ev.evenement.user,
                                            evenement__creation__lt=ev.evenement.creation).latest('evenement__creation')
    @classmethod
    def construireListeActions(self,pk):
        def copieInput(r,withChilds=True,temps=None):
            """
            copie une input
            """
            if r is None: return None if temps is None else {'time':temps,'childs':{}}
            result={'time':r['time'] if temps is None else temps,
                    'parent':r['parent'] if 'parent' in r else None,
                    'typeMorph':r['typeMorph'] if 'typeMorph' in r else None,
                    'blockSpec':r['blockSpec'] if 'blockSpec' in r else None,
                    'selector':r['selector'] if 'selector' in r else None,
                    'childs':{},
                    
                    'wraps':[],
                    }
            if withChilds:
                result['childs']=copy.copy(r['childs'])
                result['wraps']=copy.copy(r['wraps'])
                result['trucs']=copy.copy(r['trucs'])
            """ copie des childs lorsqu'une copie de l'objet est dans childs[]
            if withChilds and len(r['childs'])!=0:
                for c in r['childs']:
                    
                    rc=r['childs'][c]                    
                    result['childs'][c]={'valeur':rc['valeur'],
                                         'JMLid':rc['JMLid'],
                                         'id':rc['id'] if 'id' in rc else None,
                                         'type':rc['type'] if 'type' in rc else None,
                                         'parent':rc['parent'] if 'parent' in rc else None,
                                         'rang':rc['rang'] if 'rang' in rc else 'pasderang'
                                         }
            """
            return result
        
        #on récupère les actions
        #TODO: gérer le cas ou pas de prg n'est chargé, et si chargé + tard?
        ev=EvenementSPR.objects.get(id=pk)
        evs=self.suivant(ev)
        if evs is not None:
            actions=Evenement.objects.filter(user=ev.evenement.user,
                                         creation__gte=ev.evenement.creation,
                                         numero__gt=ev.evenement.numero,
                                         creation__lt=evs.evenement.creation).order_by('numero')
        else:
            #c'est le dernier OPen
            actions=Evenement.objects.filter(user=ev.evenement.user,
                                         creation__gte=ev.evenement.creation,
                                         numero__gt=ev.evenement.numero).order_by('numero')
        
        #on prepare la liste id->[node time x, node time y ...]
        #liste,nextLiens,ret,inp,nodes,liens=self.constructionListeOpen(pk) 
        #on construit les noeuds et les liens du programme initial  
        nodes,liens=self.constructionListeOpen(pk)  
        #première étape: ce sont les noeuds du temps 0   
        newNodes={}
        for n in nodes:
            print('trait',nodes[n])
            newNodes[n]=[]
            nodes[n]['time']=0
            nodes[n]['JMLid']='%s_0' % nodes[n]['JMLid']
            if nodes[n]['conteneur']:
                nodes[n]['conteneur']='%s_0' %  nodes[n]['conteneur']
            if 'nextBlock' in nodes[n] and nodes[n]['nextBlock']:
                nodes[n]['nextBlock']='%s_0' % nodes[n]['nextBlock']            
            if 'childs' in nodes[n]: 
                for i in nodes[n]['childs']:
                    nodes[n]['childs'][i]='%s_0' % nodes[n]['childs'][i]
            if 'wraps' in nodes[n]:
                for i in nodes[n]['wraps']:
                    i='%s_0' % i
            newNodes[n]=[nodes[n]]
        #et on met à jour les liens : source-> source_0
        for l in liens:
            l['source']='%s_0' % l['source']
            l['target']='%s_0' % l['target']
        #for l in nextLiens:
        #    l['source']='%s_0' % l['source']
        #    l['target']='%s_0' % l['target']
            #liens.append(l)
        #aff(newNodes)
        #on ajoute pour chaque id de noeud l'action associée si elle existe
        for a in actions:         
            #print('type:',a.type)   
            if a.type =='SPR':
                spr= a.evenementspr_set.all()[0]
                
                print('SPR',spr.type)
                print('temps:',a.time,':',spr.type,'block %s' % spr.blockId,
                          'detail %s' % spr.detail, 'location % s' %spr.location,
                          'childId %s' % spr.childId, 'ParentID %s' % spr.parentId,
                          'Targetid %s' % spr.targetId,'scripts %s' % spr.scripts.all().count())
                print ('entrée:',
                          ["%s - %s - %s - %s//" % (s.JMLid,s.typeMorph,s.rang,s.contenu) for s in spr.inputs.all()],
                          )                         
                newNode={'time':a.time,
                             'selector':spr.selector,
                             'blockSpec':spr.blockSpec,
                             'typeMorph':spr.typeMorph,
                             'category':spr.category,                             
                             'JMLid':'%s_%s' % (spr.blockId, a.time),
                             'typeAction':spr.type,
                             'childs':{},
                             'wraps':[],
                             'trucs':{}}
                if spr.type=='VAL':
                    #c'est une modification d'un truc qui existe , donc test suivant inutile                        
                    #if spr.blockId in inp:
                    val=newNodes[spr.blockId][-1:][0]
                    #c'est un changement de valeur, on recherche laquelle
                    
                    print('ici val',val)
                    #newval={'temps':a.time,'childs':{}}
                    #newval=copy.deepcopy(val)
                    #newval=copieInput(val, True, a.time)
                    #TODO: garder le JMLid et mettre id à JMLid_time
                    for i in spr.inputs.all():   
                        print('ri',i)
                        if i.typeMorph in ['CommandBlockMorph','CSlotMorph','ReporterBlockMorph']: # pas la peine de tester les chapeaux?
                            #normalement on ne devrait pas passer par la...
                            print('PPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPP',i)
                            newNode['childs'][i.rang]='%s_%s' % (i.JMLid,a.time)                       
                            newNode['wraps'].append('%s_%s' % (i.JMLid,a.time))
                        else:
                            newNode['childs'][i.rang]='%s_%s' % (i.JMLid,a.time)
                        #on compare avec le dernier child
                        source_id=int(val['childs'][i.rang].split('_')[0])
                        last_child=newNodes[source_id][-1:][0]
                        print('lasr',last_child)
                        if i.contenu != last_child['valeur']:
                            print('changement')
                            cp=copy.deepcopy(last_child)
                            cp['JMLid']='%s_%s' % (i.JMLid,a.time)
                            cp['time']=a.time
                            cp['parent']=newNode['JMLid']
                            newNodes[i.JMLid].append(cp)
                            liens.append({'source':last_child['JMLid'],
                                          'target':'%s_%s' % (i.JMLid,a.time),
                                          'type':'change',
                                          'color':'red'})                      
                    newNodes[spr.blockId].append(newNode)
                elif spr.type=='NEW':
                    #c'est un nouveau bloc, ses inputs éventuels aussi  
                    newNodes[spr.blockId]=[newNode]
                    for c in spr.inputs.all():
                        print('new',type(c),c)
                        newChild={'time':a.time,
                             #'selector':spr.selector,
                             #'blockSpec':spr.blockSpec,
                             'typeMorph':spr.typeMorph,
                             #'category':spr.category,                             
                             'JMLid':'%s_%s' % (c.JMLid, a.time),
                             'rang':c.rang,
                             'valeur':c.contenu
                             }
                        newNode['childs'][c.rang]=newChild['JMLid']
                        newChild['parent']=newNode['JMLid']
                        liens.append({"source":newNode['JMLid'],
                                      "target":newChild['JMLid'],
                                      'type':'child'})
                        newNodes[c.JMLid]=[newChild,]
                        """
                        if c.typeMorph in ['InputSlotMorph',]:
                            newval['childs'][c.rang]={'valeur':c.contenu,'JMLid':None,'id':c.JMLid,
                                                      'rang':c.rang}
                            newNode
                        else:
                            newval['childs'][c.rang]={'type':c.typeMorph,
                                                      'valeur':None,
                                                      'JMLid':c.JMLid,
                                                      'rang':c.rang
                                                      }
                        """
                '''
                if spr.type=='NEW':
                    #c'est un nouveau bloc, ses inputs éventuels aussi                  
                    newNodes[spr.blockId]=[newNode]
                    for c in spr.inputs.all():
                        if c.typeMorph in ['InputSlotMorph',]:
                            newval['childs'][c.rang]={'valeur':c.contenu,'JMLid':None,'id':c.JMLid,
                                                      'rang':c.rang}
                            newNode
                        else:
                            newval['childs'][c.rang]={'type':c.typeMorph,
                                                      'valeur':None,
                                                      'JMLid':c.JMLid,
                                                      'rang':c.rang
                                                      }
                    inp[spr.blockId]=[newval]
                elif spr.type=='VAL':
                    #c'est une modification d'un truc qui existe , donc test suivant inutile                        
                    #if spr.blockId in inp:
                    val=inp[spr.blockId][-1:][0]
                    #c'est un changement de valeur, on recherche laquelle
                    
                    print('ici val',val)
                    #newval={'temps':a.time,'childs':{}}
                    newval=copieInput(val, True, a.time)                        
                    for i in spr.inputs.all():   
                        #print('ri',i)                         
                        if i.typeMorph in ['InputSlotMorph',]:
                            newval['childs'][i.rang]={'valeur':i.contenu,'JMLid':None,
                                                      'id':i.JMLid,
                                                      'rang':i.rang}
                            if i.contenu!=val['childs'][i.rang]['valeur']:
                                newval['childs'][i.rang]['change']=True
                        else: #nécessaire?
                            newval['childs'][i.rang]={
                                'valeur':val['childs'][i.rang]['valeur'],
                                'JMLid':val['childs'][i.rang]['JMLid'],
                                'rang':i.rang}
                    inp[spr.blockId].append(newval)
                elif spr.type=='DROPVAL':
                    #c'est un reporter existant déplacé
                    #on  cherche le block qui a perdu son input
                    # c'est celui quia un JMLid d'un enfant = spr.blockid et qui est le plus récent
                    lasttime=-1
                    lastId=None
                    for i in inp:
                        val=inp[i][-1:][0]
                        for c in val['childs']:                            
                            if val['childs'][c]['JMLid']==spr.blockId:
                                if val['time']>lasttime: 
                                    lasttime=val['time']
                                    lastId=i
                    if lastId is not None:
                        ipt=inp[lastId][-1:][0]
                        val=copieInput(ipt, True,a.time)
                        #val['childs']={}
                        #for c in ipt['childs']:
                        #    val['childs'][c]={'valeur':ipt['childs'][c]['valeur'],
                        #                      'JMLid':ipt['childs'][c]['JMLid']}
                            #val['childs'][c]=ipt['childs'][c].copy()
                        for c in val['childs']:
                            if val['childs'][c]['JMLid']==spr.blockId:
                                val['childs'][c]['JMLid']=None                                
                        #print('lasrt',lastId,val,inp[lastId][-1:][0])
                        inp[lastId].append(val)
                    #on ajuste la nouvelle valeur
                    #newval=copieInput(ipt, True, a.time)
                    #newval={'temps':a.time,'childs':{}}
                    #for i in ipt['childs']:
                        #newval['childs'][i]={}
                        #newval['childs'][i]['valeur']=ipt['childs'][i]['valeur']
                        #newval['childs'][i]['JMLid']=ipt['childs'][i]['JMLid']
                        #newval['childs'][i]['ici']=True
                    #print('ipt:',ipt,'newal:',newval)
                    #print('drop:',newval)
                    if spr.targetId in inp: #normalement il l'est
                        newval=copieInput(inp[spr.targetId][-1:][0], True, a.time)
                        #on cherche l'entrée remplacée
                        for c in newval['childs']:
                            #print('-------------------')
                            #print('c',type(c),'child',type(newval['childs'][c]['id']),'detail',type(spr.detail))
                            if c==int(spr.detail) or newval['childs'][c]['id']==int(spr.detail):
                                #print('TOURVE************')                                
                                newval['childs'][c]={'JMLid':spr.blockId,
                                                     'id':spr.blockId,
                                                     'parent':spr.targetId,
                                                     'type':spr.typeMorph, 
                                                     'rang':c,                                                    
                                                     'valeur':None}
                                break;
                        inp[spr.targetId].append(newval)
                        #on change le parent 
                        newval=copieInput(inp[spr.blockId][-1:][0],True,a.time)
                        newval['parent']=spr.targetId
                        inp[spr.blockId].append(newval)                       
                        
                    else:
                        #normalement ça ne devrait pas se passer                        
                        newval={'time':a.time,'childs':{},'erreur':'DROPVAL avec valeur non existante'}
                        inp[spr.targetId]=[newval]
                
                #print('---')
                #for i in inp: print(i,inp[i])   
                '''
                if spr.blockId in newNodes:
                    newNodes[spr.blockId].append(newNode)
                else:
                    newNodes[spr.blockId]=[newNode,]
        """
        for a in actions:         
            #print('type:',a.type)   
            if a.type =='SPR':
                spr= a.evenementspr_set.all()[0]
                #print('SPR',spr.type)      
                #print('temps:',a.time,':',spr.type,'block %s' % spr.blockId,
                          #'detail %s' % spr.detail, 'location % s' %spr.location,
                          #'childId %s' % spr.childId, 'ParentID %s' % spr.parentId,
                          #'Targetid %s' % spr.targetId,'scripts %s' % spr.scripts.all().count())
                #print ('entrée:',
                          #["%s - %s - %s - %s//" % (s.JMLid,s.typeMorph,s.rang,s.contenu) for s in spr.inputs.all()],
                          #)                         
                #if spr.type in ['VAL','NEWVAL','DROPVAL']:
                if spr.type=='NEW':
                    newval={'time':a.time,'selector':spr.selector,'blockSpec':spr.blockSpec,'childs':{}}
                    for c in spr.inputs.all():
                        if c.typeMorph in ['InputSlotMorph',]:
                            newval['childs'][c.rang]={'valeur':c.contenu,'JMLid':None,'id':c.JMLid,
                                                      'rang':c.rang}
                        else:
                            newval['childs'][c.rang]={'type':c.typeMorph,
                                                      'valeur':None,
                                                      'JMLid':c.JMLid,
                                                      'rang':c.rang
                                                      }
                    inp[spr.blockId]=[newval]
                elif spr.type=='VAL':
                    #c'est une modification d'un truc qui existe , donc test suivant inutile                        
                    #if spr.blockId in inp:
                    val=inp[spr.blockId][-1:][0]
                    #c'est un changement de valeur, on recherche laquelle
                    
                    print('ici val',val)
                    #newval={'temps':a.time,'childs':{}}
                    newval=copieInput(val, True, a.time)                        
                    for i in spr.inputs.all():   
                        #print('ri',i)                         
                        if i.typeMorph in ['InputSlotMorph',]:
                            newval['childs'][i.rang]={'valeur':i.contenu,'JMLid':None,
                                                      'id':i.JMLid,
                                                      'rang':i.rang}
                            if i.contenu!=val['childs'][i.rang]['valeur']:
                                newval['childs'][i.rang]['change']=True
                        else: #nécessaire?
                            newval['childs'][i.rang]={
                                'valeur':val['childs'][i.rang]['valeur'],
                                'JMLid':val['childs'][i.rang]['JMLid'],
                                'rang':i.rang}
                    inp[spr.blockId].append(newval)
                elif spr.type=='DROPVAL':
                    #c'est un reporter existant déplacé
                    #on  cherche le block qui a perdu son input
                    # c'est celui quia un JMLid d'un enfant = spr.blockid et qui est le plus récent
                    lasttime=-1
                    lastId=None
                    for i in inp:
                        val=inp[i][-1:][0]
                        for c in val['childs']:                            
                            if val['childs'][c]['JMLid']==spr.blockId:
                                if val['time']>lasttime: 
                                    lasttime=val['time']
                                    lastId=i
                    if lastId is not None:
                        ipt=inp[lastId][-1:][0]
                        val=copieInput(ipt, True,a.time)
                        #val['childs']={}
                        #for c in ipt['childs']:
                        #    val['childs'][c]={'valeur':ipt['childs'][c]['valeur'],
                        #                      'JMLid':ipt['childs'][c]['JMLid']}
                            #val['childs'][c]=ipt['childs'][c].copy()
                        for c in val['childs']:
                            if val['childs'][c]['JMLid']==spr.blockId:
                                val['childs'][c]['JMLid']=None                                
                        #print('lasrt',lastId,val,inp[lastId][-1:][0])
                        inp[lastId].append(val)
                    #on ajuste la nouvelle valeur
                    #newval=copieInput(ipt, True, a.time)
                    #newval={'temps':a.time,'childs':{}}
                    #for i in ipt['childs']:
                        #newval['childs'][i]={}
                        #newval['childs'][i]['valeur']=ipt['childs'][i]['valeur']
                        #newval['childs'][i]['JMLid']=ipt['childs'][i]['JMLid']
                        #newval['childs'][i]['ici']=True
                    #print('ipt:',ipt,'newal:',newval)
                    #print('drop:',newval)
                    if spr.targetId in inp: #normalement il l'est
                        newval=copieInput(inp[spr.targetId][-1:][0], True, a.time)
                        #on cherche l'entrée remplacée
                        for c in newval['childs']:
                            #print('-------------------')
                            #print('c',type(c),'child',type(newval['childs'][c]['id']),'detail',type(spr.detail))
                            if c==int(spr.detail) or newval['childs'][c]['id']==int(spr.detail):
                                #print('TOURVE************')                                
                                newval['childs'][c]={'JMLid':spr.blockId,
                                                     'id':spr.blockId,
                                                     'parent':spr.targetId,
                                                     'type':spr.typeMorph, 
                                                     'rang':c,                                                    
                                                     'valeur':None}
                                break;
                        inp[spr.targetId].append(newval)
                        #on change le parent 
                        newval=copieInput(inp[spr.blockId][-1:][0],True,a.time)
                        newval['parent']=spr.targetId
                        inp[spr.blockId].append(newval)                       
                        
                    else:
                        #normalement ça ne devrait pas se passer                        
                        newval={'time':a.time,'childs':{},'erreur':'DROPVAL avec valeur non existante'}
                        inp[spr.targetId]=[newval]
                #print('---')
                #for i in inp: print(i,inp[i])   
           """        
        aff(newNodes)              
        #return inp,liste,nextLiens,nodes,liens
        #inp=newNodes              
        #return inp,liste,nextLiens,nodes,liens
        return newNodes,liens
    
    
    @detail_route()
    def listeActions(self,request,pk):
        """
        renvoie la liste des actions du début du chargement (SPR d'id pk) 
        à la fin de la session ou au début du chargement suivant
        """
        ev=EvenementSPR.objects.get(id=pk)
        evs=self.suivant(ev)
        eleve=Eleve.objects.get(user=ev.evenement.user)
        if evs is not None:
            actions=Evenement.objects.filter(user=ev.evenement.user,
                                         creation__gte=ev.evenement.creation,
                                         numero__gt=ev.evenement.numero,
                                         creation__lt=evs.evenement.creation).order_by('numero')
        else:
            #c'est le dernier OPen
            actions=Evenement.objects.filter(user=ev.evenement.user,
                                         creation__gte=ev.evenement.creation,
                                         numero__gt=ev.evenement.numero).order_by('numero')
        return render(request,'liste_simple.html',{'evenements':actions,'eleve':eleve})
        #return Response(EvenementSerializer(actions,many=True).data)
                                   
    
class EvenementSPRViewset(viewsets.ModelViewSet):
    """
    API Endpoint pour EvenementENV (Evenement Changement de l'environnement)
    """
    queryset=EvenementSPR.objects.all()
    serializer_class=EvenementSPRSerializer

class BlockViewSet(viewsets.ModelViewSet):
    queryset=Block.objects.all()
    serializer_class=BlockSerializer
    
def current_datetime(request):
    now = datetime.datetime.now()
    html = "<html><body>It is now %s.</body></html>" % now
    return HttpResponse(html)

@login_required(login_url='/accounts/login/')
def testsnap(request):
    return render(request,'snap/snap.html')



def pageref(request):
    return render_to_response('refresh.html', {'value':'test'})
def pagedon(request):
    obj=InfoReceived.objects.all()
    if not obj.exists():
        return HttpResponse('.')
    else:
        html_result=render_to_string('don.html', {'autre':obj.count(),'data':obj})
        obj.delete()
        #return render_to_response(html_result)
        return HttpResponse(html_result)

def simple_upload(request):
    if request.method == 'POST' and request.FILES['myfile']:
        myfile = request.FILES['myfile']
        fs = FileSystemStorage()
        filename = fs.save(myfile.name, myfile)
        uploaded_file_url = fs.url(filename)
        return render(request, 'simple_upload.html', {
            'uploaded_file_url': uploaded_file_url
        })
    return render(request, 'simple_upload.html')

def model_form_upload(request):
    if request.method == 'POST':
        form = DocumentForm(request.POST, request.FILES)
        if form.is_valid():
            instance=form.save(commit=False)
            instance.user=request.user
            instance.save()
            return HttpResponse(json.dumps({'success': True,'id':instance.id}), content_type="application/json")
    #else:
    #    form = DocumentForm()
    #return render(request, 'model_form_upload.html', {
    #    'form': form
    #})

def return_fichier(request):
    if request.method == 'GET':
        eleve = get_object_or_404(Eleve, user=request.user)
        if eleve.prg is None:
                    return HttpResponse(json.dumps({'success': False, 'id':request.user.username}), content_type="application/json", status=status.HTTP_404_NOT_FOUND)
        # wrapper = FileWrapper(open('media/documents/sierpinski-programme1.xml'))
        wrapper = eleve.prg.file
        # content_type = mimetypes.guess_type(filename)[0]
        response = HttpResponse(wrapper, content_type='text/xml')
        # response['Content-Length'] = os.path.getsize(filename)
        response['Content-Disposition'] = "attachment; filename=%s" % 'gi'
        return response
def return_fichier_eleve(request,file_id):
    #print('ok',file_id)
    if request.method=='GET':
        doc=Document.objects.get(id=file_id);
        #wrapper = FileWrapper(open('media/documents/sierpinski-programme1.xml'))
        #wrapper = FileWrapper(open('media/%s' %doc.document))
        wrapper=doc.document
        #content_type = mimetypes.guess_type(filename)[0]
        response = HttpResponse(wrapper, content_type='text/xml')
        #response['Content-Length'] = os.path.getsize(filename)
        response['Content-Disposition'] = "attachment; filename=%s" % 'doc.description'
        return response
def return_files(request):
    if request.user.is_staff:
        fics=Document.objects.filter(Q(user=request.user) | Q(user__groups__name__in=['eleves',])).order_by('-uploaded_at')
        return render(request,'file_user_prof.html',{'files':fics});
    else:
        fics=Document.objects.filter(user=request.user).order_by('-uploaded_at')
        return render(request,'file_user.html',{'files':fics});
    

@login_required()
def login_redirect(request):
    if request.user.is_authenticated:
        ugroups = request.user.groups.values_list('name', flat=True)
        print('users',ugroups)
        if request.user.is_superuser:
            return HttpResponseRedirect(reverse("admin:index"))
        elif "prof" in ugroups:
            return HttpResponseRedirect(reverse("admin:index"))
        elif "eleves" in ugroups:
            return HttpResponseRedirect(reverse("snaptest"))

def liste(request,nom=None):
    if nom is not None:
        user=User.objects.get(username=nom)
        ev=EvenementENV.objects.filter(type='LANCE',evenement__user=user).latest('evenement__creation')
        ev1=EvenementENV.objects.filter(type='LANCE',evenement__user=user,evenement__creation__lt=ev.evenement.creation).latest('evenement__creation')
    else:
        ev=EvenementENV.objects.filter(type='LANCE').latest('evenement__creation')
        user=ev.evenement.user
        ev1=EvenementENV.objects.filter(type='LANCE',evenement__user=user,evenement__creation__lt=ev.evenement.creation).latest('evenement__creation')
    eleve=user.eleve
    evs=Evenement.objects.filter(user=user,creation__gte=ev1.evenement.creation).order_by('time')
    
    return render(request,'liste_simple.html',{'evenements':evs,'eleve':eleve})

def session(request,id=None):
    if id is not None:
        ev=EvenementENV.objects.get(id=id)
        evs=Evenement.objects.filter(id=ev.evenement.id) | Evenement.objects.filter(user=ev.evenement.user,
                                     creation__gt=ev.evenement.creation,
                                     numero__gt=1).order_by('time')
                                     
        return render(request,'liste_simple.html',{'evenements':evs})
    return HttpResponse()
def listeSessions(request):
    return render(request,'liste_sessions.html')  

def listeOpens(request):
    return render(request,'liste_opens.html')


def essai(liste,liens):
    def recurs(jmlid,b):
        nodes={}
        liensInputs=[]
        print(b)
        data={'id':'%s_init' % jmlid}
        data['temps']=b['temps'] if 'temps' in 'b' else None
        if 'type' in b and b['type']=='InputSlotMorph':
            data['valeur']=b['valeur']            
        else:
            
            data['valeur']=b['blockSpec'] if 'blockSpec' in b else b['valeur']
        if 'parent' in b and b['parent'] is not None:
                    data['parent']='%s' % b['parent']              
        nodes[jmlid]=data
        #nodes.append({'data':data})
        if 'childs' in b:
            for c in b['childs']:
                ch=b['childs'][c]                
                ch['rang']=c
                
                liensInputs.append({'id':'%s_init-%s_init' % (jmlid,ch['JMLid'] if ch['JMLid'] is not None else ch['id']),
                                    'source':'%s_init' % jmlid,
                                    'target':'%s_init' % (ch['JMLid'] if ch['JMLid'] is not None else ch['id']), 
                                    'type':'child' if 'rang' in b else 'input'
                                    })
                ret,liens=recurs(ch['JMLid'] if ch['JMLid'] is not None else ch['id'],ch)
                for i in ret:
                    if i not in nodes:
                        nodes[i]={}
                    for k in ret[i]:                        
                        nodes[i][k]=ret[i][k]
                liensInputs+=liens
        return nodes,liensInputs
    
    data={}
    liensInputs=[{'id':'%s-%s' % (i['source'],i['target']),
                  'source':'%s_init' % i['source'],
                  'target':'%s_init' % i['target'],
                  'type':'next'
                  } for i in liens]
    for b in liste:
        nodes,liens=recurs(b,liste[b][0])
        for i in nodes:
            if i not in data:
                data[i]={}
            for k in nodes[i]:                        
                data[i][k]=nodes[i][k]
        liensInputs+=liens
    
    return data,liensInputs
        
    
def cyto2(request,id=277):
    inp,liste,nextliens=EvenementSPROpenViewset.construireListeActions(pk=id)
    #on prépare la liste des liens 'next':
    liens=[{'source':'%s_0' % l['source'],
            'target':'%s_0' % l['target'],
            'type':'nextblock',
            'color':'blue',
            'arrow':'none'} for l in nextliens]
    nodes=[]
    liensChanged=[]
    maxtime=0
    firstime=0
    y=10
    for i in inp:
        newListe=[]
        x=10
        y+=50        
        for b in inp[i]:
            x+=150
            data={'x':x,'y':y}
            data['time']=b['time'] if 'time' in b else -1
            if firstime==0 and data['time']>0: firstime=data['time']
            if data['time']>maxtime: maxtime=data['time']
            data['id']='%s_%s' % (i,data['time'])
            if 'type' in b and b['type']=='InputSlotMorph':
                data['valeur']=b['valeur']            
            else:            
                data['valeur']=b['blockSpec'] if 'blockSpec' in b else b['valeur']
            newListe.append(data)
            ind=inp[i].index(b)
            if ind>0:
                #c'est un changement
                liensChanged.append({'source':newListe[ind-1]['id'],
                                     'target':data['id'],
                                     'type':'changed',
                                     'color':'#C99966',
                                     'arrow':'tee'
                                     })   
        nodes+=newListe
    liens+=liensChanged
    #preparation pour cuto
    datanodes=[{'data':n} for n in nodes]
    dataedges=[{'data':n} for n in liens]
    
    context={'nodes':json.dumps(datanodes),'edges':json.dumps(dataedges),
             'maxtime':maxtime, 'firstime':firstime,
             }
    #return context
    return render(request, 'testcyto.html',context=context) 

def cyto(request,id=277):
    def parcours(b,x,y,i,index,newListe,firstime,maxtime):
        print('BBBBBBBBBBBBBBBBBBB',b)
        liensChanged=[]
        data={'x':x,'y':y}
        data['time']=b['time'] if 'time' in b else -1
        if firstime==0 and data['time']>0: firstime=data['time']
        if data['time']>maxtime: maxtime=data['time']
        data['id']='%s_%s' % (i,data['time'])
        data['type']=b['type'] if 'type' in b else 'NoType'
        if 'type' in b and b['type']=='InputSlotMorph':
            data['valeur']=b['valeur']       
        else:            
            data['valeur']=b['blockSpec'] if 'blockSpec' in b else b['valeur']
        data['valeur']='%s-%s' % (data['valeur'],i)  
        if 'parent' in b and b['parent'] is not None:
            data['parent']='%s_%sch' %(b['parent'],data['time']) 
            data['genre']='Lien'
        newListe.append(data)        
        if index>0:
            #c'est un changement
            liensChanged.append({'source':newListe[index-1]['id'],
                                     'target':data['id'],
                                     'type':'changed',
                                     'color':'#C99966',
                                     'arrow':'triangle'
                                     })   
        if 'childs' in b:
            for i in b['childs']:
                d={}
                ch=b['childs'][i]
                print('child',i,b['childs'][i])
                
                d['time']=data['time']
                id=ch['id'] if 'id' in ch else ch['JMLid']
                d['id']='%s_%sch' % (id,d['time'])
                v=ch['valeur'] if ch['valeur'] is not None else ch['type'] if 'type' in ch else 'Rien'
                d['valeur']='%s (%s) %s' %(v,ch['id'] if 'id' in ch else '%s JML' % ch['JMLid'],d['time'])
                d['x']=x+50
                d['y']=y+(50*i)
                d['parent']=data['id']
                newListe.append(d)
        return newListe,liensChanged,firstime,maxtime
    
    inp,liste,nextliens,nodes,liens=EvenementSPROpenViewset.construireListeActions(pk=id)
    """
        liste: 
            liste du fil principal des blocks du scripts (ie les nextblocks)
            contient: 
                id (sql), JMLid (snap), blockSpec (None sur CSlotMorph), selector, typeMorph, 
                nextBlock : JMLid du nextBlock
                parent: JMLid du previous block, sauf si conteneur existe. Dans ce cas, parent=conteneur
                    et désigne le block dont l'élément courant est un input
                inputs: 
                    rang, JMLid, parent, typeMorph
                    contenu: 
                            si val -> contenu final (inputslotmorph), 
                            si [vals] contenus blocks comme liste, avec reprise block
                        
        inp:
            liste indexée sur le JMLid
            contient:
                blockSpec, parent, time, parfois selector, childs
                    childs:
                        JMLid (None si valeur (inputSlotMorph ou reporterSlotMorph), id(en fait JMLid initial) 
                        type (typeMorph serait mieux), parent, valeur,
                        blockSpec (None si CSlotMoprh)
    """
    """
    #on prépare la liste des liens 'next':
    liens=[{'source':'%s_0' % l['source'],
            'target':'%s_0' % l['target'],
            'type':'nextblock',
            'color':'blue',
            'arrow':'none'} for l in nextliens]
    nodes=[]
    liensChanged=[]
    maxtime=0
    firstime=0
    y=10
    for i in inp:
        newListe=[]
        x=10
        y+=50        
        for b in inp[i]:
            x+=150
            newListe,liensC,firstime,maxtime=parcours(b,x,y,i,inp[i].index(b),newListe,firstime,maxtime)
            liensChanged+=liensC
        nodes+=newListe
    liens+=liensChanged
    #preparation pour cuto
    """
    
    liensN=[{'source':'%s' % l['source'],
            'target':'%s' % l['target'],
            'type':'nextblock',
            'color':'blue',
            'arrow':'none'} for l in nextliens]
    liens+=liensN
        
    #datanodes=[{'data':n} for n in nodes]
    for n in nodes:
        nodes[n]['id']=nodes[n]['JMLid']
        nodes[n]['parent']=nodes[n]['conteneur']
    datanodes=[{'data':nodes[n]} for n in nodes]
    dataedges=[{'data':n} for n in liens]
    #l0=[i['data'] for i in datanodes if i['data']['time']==0]
    #for i in l0: print(i)
    aff(datanodes,'NODES')
    context={'nodes':json.dumps(datanodes),'edges':json.dumps(dataedges),
             #'maxtime':maxtime, 'firstime':firstime,
             }
    #return context
    return render(request, 'testcyto.html',context=context) 

@api_view(('GET',))
@renderer_classes((JSONRenderer,))
def cyto3(request,id=277):
    def parcours(b,x,y,i,index,newListe,firstime,maxtime):
        print('CCCC',b)
        liensChanged=[]
        data={'x':x,'y':y}
        data['time']=b['time'] if 'time' in b else -1
        if firstime==0 and data['time']>0: firstime=data['time']
        if data['time']>maxtime: maxtime=data['time']
        data['id']='%s_%s' % (i,data['time'])
        data['type']=b['type'] if 'type' in b else 'NoType'
        if 'type' in b and b['type']=='InputSlotMorph':
            data['valeur']=b['valeur']       
        else:            
            data['valeur']=b['blockSpec'] if 'blockSpec' in b else b['valeur']
        data['valeur']='%s-%s' % (data['valeur'],i)  
        if 'parent' in b and b['parent'] is not None:
            data['parent']='%s_%sch' %(b['parent'],data['time']) 
            data['genre']='Lien'
        newListe.append(data)        
        if index>0:
            #c'est un changement
            liensChanged.append({'source':newListe[index-1]['id'],
                                     'target':data['id'],
                                     'type':'changed',
                                     'color':'#C99966',
                                     'arrow':'triangle'
                                     })   
        if 'childs' in b:
            for i in b['childs']:
                d={}
                ch=b['childs'][i]
                print('child',i,b['childs'][i])
                
                d['time']=data['time']
                id=ch['id'] if 'id' in ch else ch['JMLid']
                d['id']='%s_%sch' % (id,d['time'])
                v=ch['valeur'] if ch['valeur'] is not None else ch['type'] if 'type' in ch else 'Rien'
                d['valeur']='%s (%s) %s' %(v,ch['id'] if 'id' in ch else '%s JML' % ch['JMLid'],d['time'])
                d['x']=x+50
                d['y']=y+(50*i)
                d['parent']=data['id']
                newListe.append(d)
        return newListe,liensChanged,firstime,maxtime
    
    #inp,liste,nextliens,nodes,liens=EvenementSPROpenViewset.construireListeActions(pk=id)
    nodes,liens=EvenementSPROpenViewset.construireListeActions(pk=id)
    """
        liste: 
            liste du fil principal des blocks du scripts (ie les nextblocks)
            contient: 
                id (sql), JMLid (snap), blockSpec (None sur CSlotMorph), selector, typeMorph, 
                nextBlock : JMLid du nextBlock
                parent: JMLid du previous block, sauf si conteneur existe. Dans ce cas, parent=conteneur
                    et désigne le block dont l'élément courant est un input
                inputs: 
                    rang, JMLid, parent, typeMorph
                    contenu: 
                            si val -> contenu final (inputslotmorph), 
                            si [vals] contenus blocks comme liste, avec reprise block
                        
        inp:
            liste indexée sur le JMLid
            contient:
                blockSpec, parent, time, parfois selector, childs
                    childs:
                        JMLid (None si valeur (inputSlotMorph ou reporterSlotMorph), id(en fait JMLid initial) 
                        type (typeMorph serait mieux), parent, valeur,
                        blockSpec (None si CSlotMoprh)
    """
    """
    #on prépare la liste des liens 'next':
    liens=[{'source':'%s_0' % l['source'],
            'target':'%s_0' % l['target'],
            'type':'nextblock',
            'color':'blue',
            'arrow':'none'} for l in nextliens]
    
    nodes=[]
    liensChanged=[]
    maxtime=0
    firstime=0
    y=10
    for i in inp:
        newListe=[]
        x=10
        y+=50        
        for b in inp[i]:
            x+=150
            newListe,liensC,firstime,maxtime=parcours(b,x,y,i,inp[i].index(b),newListe,firstime,maxtime)
            liensChanged+=liensC
        nodes+=newListe
    liens+=liensChanged
    #preparation pour cuto
    """
    
    liens=[{'source':'%s' % l['source'],
            'target':'%s' % l['target'],
            'type':l['type'],
            #'color':'red',
            'arrow':'triangle'} for l in liens]
    #liensN=[{'source':'%s' % l['source'],
    #        'target':'%s' % l['target'],
    #        'type':'nextblock',
    #        'color':'blue',
    #        'arrow':'none'} for l in nextliens]
    #liens+=liensN
        
    #datanodes=[{'data':n} for n in nodes]
    #contruction des noeuds cytoscape
    nnodes=[]
    
    for inode in nodes:
        #on récupère les actions liées à un block d'id inode        
        nodes_actions=nodes[inode]
        prec_node_id=None #l'id du noeud précédent
        #et on cré les noeuds et liens
        for i,n in enumerate(nodes_actions):
            print(i,':',n)
            nn={}        
            nn['id']='%s' % n['id'] if 'id' in n else '%s' % n['JMLid']
            nn['valeur']=n['valeur'] if 'valeur' in n else n['blockSpec']
            nn['typeMorph']=n['typeMorph']
            nn['time']=n['time']
            nn['rang']=n['rang'] if 'rang' in n else None
            nn['parent']='%s' % n['conteneur'] if 'conteneur' in n else None
            if prec_node_id is not None:
                liens.append({'source':prec_node_id,'target':nn['id'],'type':'action','color':'green'})
            prec_node_id=nn['id']
            nnodes.append(nn)
    datanodes=[{'data':n} for n in nnodes]
    dataedges=[{'data':n} for n in liens]
    #dataedges=[]
    #l0=[i['data'] for i in datanodes if i['data']['time']==0]
    #for i in l0: print(i)
    aff(datanodes,'NODES')
    context={'nodes':json.dumps(datanodes),'edges':json.dumps(dataedges),
             #'maxtime':maxtime, 'firstime':firstime,
             }
    return render(request, 'testcyto.html',context=context) 
    #return Response({"data":{"name":"mon resea"},"elements":{'nodes':datanodes,'edges':dataedges}}) 



from snap import objets
import time
@api_view(('GET',))
@renderer_classes((JSONRenderer,))
def testblock(request,id=277):
    ev=EvenementSPR.objects.get(id=id)
    try:
        suivant=EvenementSPR.objects.filter(type='OPEN',
                                            evenement__user=ev.evenement.user,
                                            evenement__creation__gt=ev.evenement.creation).earliest('evenement__creation')
    except:
        suivant=None
    if suivant is not None:
        actions=Evenement.objects.filter(user=ev.evenement.user,
                                         creation__gte=ev.evenement.creation,
                                         numero__gte=ev.evenement.numero,
                                         creation__lt=suivant.evenement.creation).order_by('numero')
    else:
        #c'est le dernier OPen
        actions=Evenement.objects.filter(user=ev.evenement.user,
                                         creation__gte=ev.evenement.creation,
                                         numero__gte=ev.evenement.numero).order_by('numero')
       
    #on prepare la liste id->[node time x, node time y ...]
    #liste,nextLiens,ret,inp,nodes,liens=self.constructionListeOpen(pk) 
    #on construit les noeuds et les liens du programme initial  
    #on récupère le block de tête
    #blockRoot=BlockSnap.newBlock(ev.scripts.all()[0],0)
    print("liste ",ev.scripts.all())
    listeBlocks=objets.ListeBlockSnap()  
    for script in ev.scripts.all():  
        #firstBlock,created=listeBlocks.addFromBlock(ev.scripts.all()[0],ev.evenement.time, 'OPEN')#TODO: time à timer du open, et ajout autres scripts
        firstBlock,created=listeBlocks.addFromBlock(script,ev.evenement.time, 'OPEN')
        #création des liens nextblocks
        for b in created:
            if b.prevBlock is not None:
                listeBlocks.addLink(b.prevBlock.getId(),b.getId(),'nextblock')
        listeBlocks.addFirstBlock(firstBlock)
    #cyto=CytoElements.constructFrom(blockRoot)
    
    for a in actions:         
            #print('type:',a.type)   
            #pour l'instant on ne s'occupe que de SPR
            if a.type =='SPR':    
                listeBlocks.addTick(a.time)            
                spr= a.evenementspr_set.all()[0]
                action='SPR_%s' % spr.type
                print('mod id:',spr.id,spr.type,spr.blockId,spr.blockSpec,spr.detail)
                print('loc:%s parentId:%s next:%s child:%s target:%s'
                    % (spr.location,spr.parentId,spr.nextBlockId,spr.childId,spr.targetId))
                print('inputs',[i for i in spr.inputs.all()])
                print('--')
                newNode=BlockSnap(spr.blockId, 
                                  a.time,
                                  spr.typeMorph,
                                  spr.blockSpec,
                                  spr.selector,
                                  spr.category,
                                  action=action
                                  )               
                if spr.type=='DEL':
                    #c'est une suppression d'au moins un bloc et ses inputs
                    #on ajoute dans la liste, avec les inputs (comme "NEW")
                    cible=listeBlocks.lastBlock(spr.blockId,a.time) #cible supprimée
                    """
                    listeBlocks.addBlock(newNode)
                    for c in spr.inputs.all():
                        inputNode,created=listeBlocks.addFromBlock(c,a.time,action=action)
                        newNode.addInput(inputNode)
                    """
                    if cible.rang is not None:
                        #c'est donc un input, on le remplace
                        newNode.rang=cible.rang 
                        #newNode.setParent(parent)
                        listeBlocks.copyLastParentBlockandReplace(cible, a.time, action, None)
                    """tratiement suppression a voir
                    notamment pour ne plus prendre ne compte si firstblock, ou nouveau firstblock
                    """
                if spr.type=='DROP':
                    if spr.location=='bottom':
                        #c'est un bloc ajouté à la suite d'un autre
                        #On récupère le block et on le recopie
                        lastBlock=listeBlocks.lastBlock(spr.blockId, a.time)
                        newLastBlock,create=listeBlocks.addFromBlock(lastBlock,time=a.time,action='inserted_%s' % spr.location)
                        #si il a un precBlock, il faut le mettre à None
                        lastPrevBlock=listeBlocks.lastBlock(lastBlock.prevBlock, a.time)
                        if lastPrevBlock is not None:
                            newLastPrevBlock=lastPrevBlock.copy(a.time)                            
                            newLastPrevBlock.setNextBlock(None)
                            listeBlocks.addBlock(newLastPrevBlock)
                            listeBlocks.addLink(lastPrevBlock.getId(),newLastPrevBlock.getId())                            
                            newLastBlock.setPrevBlock(None)                        
                        prevBlock=listeBlocks.lastBlock(spr.targetId, a.time)
                        newPrevBlock, create=listeBlocks.addFromBlock(prevBlock,time=a.time,action='inserted_%s' % spr.location)
                        listeBlocks.addLink(prevBlock.getId(), newPrevBlock.getId())                        
                        listeBlocks.addLink(lastBlock.getId(), newLastBlock.getId(),"moved")
                        listeBlocks.setNextBlock(newPrevBlock,newLastBlock,'inserted')                        
                        nextBlock=listeBlocks.lastBlock(prevBlock.nextBlock, a.time)
                        if nextBlock is not None:                        
                            newNextBlock, create=listeBlocks.addFromBlock(nextBlock,time=a.time,action='inserted_%s' % spr.location)
                            listeBlocks.setNextBlock(newLastBlock,newNextBlock)                        
                    elif spr.location=='top':
                        #c'est un bloc ajouté au dessus d'un autre                        
                        #listeBlocks.addBlock(newNode)
                        lastBlock=listeBlocks.lastBlock(spr.blockId, a.time)
                        newLastBlock,create=listeBlocks.addFromBlock(lastBlock,time=a.time,action='inserted_%s' % spr.location)
                        #si il a un precBlock, il faut le mettre à None
                        lastPrevBlock=listeBlocks.lastBlock(lastBlock.prevBlock, a.time)
                        if lastPrevBlock is not None:
                            newLastPrevBlock=lastPrevBlock.copy(a.time)                            
                            newLastPrevBlock.setNextBlock(None)
                            listeBlocks.addBlock(newLastPrevBlock)
                            listeBlocks.addLink(lastPrevBlock.getId(),newLastPrevBlock.getId())
                            newLastBlock.setPrevBlock(None)                        
                        nextBlock=listeBlocks.lastBlock(spr.targetId, a.time)
                        newNextBlock, create=listeBlocks.addFromBlock(nextBlock,time=a.time,action='inserted_%s' % spr.location)
                        listeBlocks.addLink(nextBlock.getId(), newNextBlock.getId())
                        listeBlocks.addLink(lastBlock.getId(), newLastBlock.getId(),"moved")
                        listeBlocks.setNextBlock(newLastBlock,newNextBlock,'inserted')                        
                        prevBlock=listeBlocks.lastBlock(nextBlock.prevBlock, a.time)
                        if prevBlock is not None:                        
                            newPrevBlock, create=listeBlocks.addFromBlock(prevBlock,time=a.time,action='inserted_%s' % spr.location)
                            listeBlocks.setNextBlock(newPrevBlock,newLastBlock)
                        else:
                            #c'est un bloc de tête
                            listeBlocks.setFirstBlock(newLastBlock)  
                    elif spr.location=='wrap':
                        #c'est un bloc englobant, le parentId est le bloc précédent, target est englobé
                        lastBlock=listeBlocks.lastBlock(spr.blockId, a.time)
                        newLastBlock,create=listeBlocks.addFromBlock(lastBlock,time=a.time,action='inserted_%s' % spr.location)
                        #s'il a un précédent, il faut lemettre à None
                        lastPrevBlock=listeBlocks.lastBlock(lastBlock.prevBlock, a.time)
                        if lastPrevBlock is not None:
                            newLastPrevBlock=lastPrevBlock.copy(a.time)                            
                            newLastPrevBlock.setNextBlock(None)
                            listeBlocks.addBlock(newLastPrevBlock)
                            listeBlocks.addLink(lastPrevBlock.getId(),newLastPrevBlock.getId())
                            newLastBlock.setPrevBlock(None)                        
                        #le bloc précédent va pointer son nextBlock sur newNode
                        prevBlock=listeBlocks.lastBlock(spr.parentId, a.time)
                        newPrevBlock, create=listeBlocks.addFromBlock(prevBlock,time=a.time,action='inserted_%s' % spr.location)
                        listeBlocks.addLink(prevBlock.getId(), newPrevBlock.getId())                        
                        listeBlocks.addLink(lastBlock.getId(), newLastBlock.getId(),"moved")
                        listeBlocks.setNextBlock(newPrevBlock,newNode,'inserted')                        
                        #le wrap englobe jusqu'àla fin, donc le nextBlock est forcément None                      
                        listeBlocks.setNextBlock(newNode,None)                        
                        #on traite maintenant les blocks wrappés
                        wrapBlock=listeBlocks.lastBlock(spr.targetId,a.time)
                        newWrapBlock,create=listeBlocks.addFromBlock(wrapBlock,time=a.time,action='wrapped')
                        for i in newNode.inputs:
                            if i.typeMorph=='CSlotMorph':
                                newWrapBlock.rang=0
                                i.addInput(newWrapBlock)        
                    elif spr.location=='slot':
                        #c'est un drop dans le CSLotMorph d'une boucle englobante
                        #parentId est le bloc englobant, targetId le CslotMorph    
                        lastBlock=listeBlocks.lastBlock(spr.blockId, a.time)
                        newLastBlock,create=listeBlocks.addFromBlock(lastBlock,time=a.time,action='inserted_%s' % spr.location)
                        listeBlocks.addLink(lastBlock.getId(),newLastBlock.getId(),'moved')                      
                        #on récupère le parent et on le recopie
                        parentBlock=listeBlocks.lastBlock(spr.parentId,a.time)
                        newParentBlock,create=listeBlocks.addFromBlock(parentBlock,time=a.time,action='inserted_%s' % spr.location)
                        
                        #on fixe le nouveau contenu
                        #newSlotBlock,create=listeBlocks.addFromBlock(slotBlock,time=a.time,action='inserted_%s' % spr.location)
                        #newSlotBlock.inputs[0]=newLastBlock
                        for i in newParentBlock.inputs:
                            if i.typeMorph=='CSlotMorph':
                                #le contenu devient le block suivant (on le rajoute ou pas?->on le copy ou pas)
                                listeBlocks.setNextBlock(newLastBlock,i.inputs[0])
                                i.inputs[0]=newLastBlock  
                                
                        #si le bloc déplacé a un précédent, il faut lemettre à None
                        #on fait ça après les modifs du parent, car le parent est petu-être l eprécédent...
                        lastPrevBlock=listeBlocks.lastBlock(lastBlock.prevBlock, a.time)
                        if lastPrevBlock is not None:
                            #cas où le parent est aussi le précédent
                            if lastPrevBlock==parentBlock:
                                listeBlocks.setNextBlock(newParentBlock, None)                                
                            else:
                                newLastPrevBlock=lastPrevBlock.copy(a.time)                            
                                newLastPrevBlock.setNextBlock(None)
                                listeBlocks.addBlock(newLastPrevBlock)
                                listeBlocks.addLink(lastPrevBlock.getId(),newLastPrevBlock.getId())
                                newLastBlock.setPrevBlock(None)                         
                        
                    else:
                        #il est droppé tout seul
                        #on ajoute le block et ses enfants
                        #listeBlocks.addFirstBlock(newNode)
                        lastBlock=listeBlocks.lastBlock(spr.blockId, a.time)
                        newLastBlock,create=listeBlocks.addFromBlock(lastBlock,time=a.time,action='dropped')
                        newLastBlock.setParent(None)
                        lastPrevBlock=listeBlocks.lastBlock(lastBlock.prevBlock, a.time)
                        if lastPrevBlock is not None:
                            newLastPrevBlock=lastPrevBlock.copy(a.time)                            
                            newLastPrevBlock.setNextBlock(None)
                            listeBlocks.addBlock(newLastPrevBlock)
                            listeBlocks.addLink(lastPrevBlock.getId(),newLastPrevBlock.getId())                            
                            newLastBlock.setPrevBlock(None)                          
                        listeBlocks.setFirstBlock(newLastBlock) 
                    """
                    for c in spr.inputs.all():
                        inputNode,created=listeBlocks.addFromBlock(c,a.time,action=action)
                        newNode.addInput(inputNode)
                    """
                    #soit c'est un input déplacé, soit c'est un block qui change de palce 
                    #donc possiblement de bloc suivant/précédant
                    #on recherche la dernière occurence du bloc
                    inputB=listeBlocks.lastBlock(spr.blockId,a.time)
                    if inputB.parentBlock is not None:
                        #c'est un input supprimé
                        parentInputB=listeBlocks.lastBlock(inputB.parentBlock,a.time)
                        inputA=next(b for b in parentInputB.inputs if b.JMLid==inputB.JMLid) #input supprimé
                        #On modifie le parent d'inputB :
                        # 1) copier les inputs 
                        # 2) remplacer l'inputB par un InputSlotMorph inconnu
                        listeBlocks.copyLastParentBlockandReplace(inputB, a.time, action)
                    
                if spr.type=='VAL':
                    #c'est une modification d'un truc qui existe
                    for i in spr.inputs.all():                           
                        
                        if i.JMLid==int(spr.detail):
                            inputNode,created=listeBlocks.addFromBlock(i, a.time,action=action)
                            inputNode.lastModifBlock=listeBlocks.lastBlock(spr.detail, a.time)
                            newNode.addInput(inputNode)
                            if inputNode.lastModifBlock is None:
                                #on ne le trouve pas, c'est sans doute parce que c'est un InputSlotMorph qui a été créé
                                parentInputA=listeBlocks.lastBlock(spr.blockId,a.time)
                                nb=0
                                print('pare,nt',parentInputA)
                                for i in parentInputA.inputs:
                                    print('a passe',i)
                                    if (i.JMLid>100000 
                                            and spr.location is not None 
                                            and i.rang==int(spr.location)):
                                        id=i.JMLid
                                        print('on en a trouvé un',i.JMLid, 'de rang ',i.rang, 
                                              'et loc=',spr.location,i.rang==int(spr.location),
                                              ' -> ',spr.detail)
                                        nb+=1
                                        inputA=i
                                if nb!=1:
                                    raise ValueError('Ce block n\'existe pas et son parent supposé a %s enfants' %nb,spr.detail,spr.parentId)
                                #on renumérote le JMLid après avoir ajouté le lien
                                listeBlocks.addLink(
                                    inputA.getId(),
                                    inputNode.getId(),
                                'changed')  
                                listeBlocks.changeJMLid(inputA.JMLid,spr.detail)
                                           
                            else:
                                #c'est l'input changé
                                listeBlocks.addLink(
                                    inputNode.lastModifBlock.getId(),
                                    inputNode.getId(),
                                    'changed')
                        else:
                            #c'est un input inchangé, on recopie
                            b=listeBlocks.lastBlock(i.JMLid,a.time)
                            inputNode,created=listeBlocks.addFromBlock(b,a.time,action=action)
                            newNode.addInput(inputNode)
                elif spr.type=='NEW':
                    #c'est un nouveau bloc, ses inputs éventuels aussi
                    #on crée les inputs
                    for c in spr.inputs.all():
                        inputNode,created=listeBlocks.addFromBlock(c,a.time,action=action)
                        newNode.addInput(inputNode) 
                    if spr.location=='bottom':
                        #c'est un bloc ajouté à la suite d'un autre
                        listeBlocks.addBlock(newNode)
                        prevBlock=listeBlocks.lastBlock(spr.targetId, a.time)
                        newPrevBlock, create=listeBlocks.addFromBlock(prevBlock,time=a.time,action='inserted_%s' % spr.location)
                        listeBlocks.addLink(prevBlock.getId(), newPrevBlock.getId())
                        listeBlocks.setNextBlock(newPrevBlock,newNode,'inserted')                        
                        nextBlock=listeBlocks.lastBlock(prevBlock.nextBlock, a.time)
                        if nextBlock is not None:                        
                            newNextBlock, create=listeBlocks.addFromBlock(nextBlock,time=a.time,action='inserted_%s' % spr.location)
                            listeBlocks.setNextBlock(newNode,newNextBlock)                        
                    elif spr.location=='top':
                        #c'est un bloc ajouté au dessus d'un autre                        
                        listeBlocks.addBlock(newNode)
                        nextBlock=listeBlocks.lastBlock(spr.targetId, a.time)
                        newNextBlock, create=listeBlocks.addFromBlock(nextBlock,time=a.time,action='inserted_%s' % spr.location)
                        listeBlocks.addLink(nextBlock.getId(), newNextBlock.getId())
                        listeBlocks.setNextBlock(newNode,newNextBlock,'inserted')                        
                        prevBlock=listeBlocks.lastBlock(nextBlock.prevBlock, a.time)
                        if prevBlock is not None:                        
                            newPrevBlock, create=listeBlocks.addFromBlock(prevBlock,time=a.time,action='inserted_%s' % spr.location)
                            listeBlocks.setNextBlock(newPrevBlock,newNode)
                        else:
                            #c'est un bloc de tête
                            listeBlocks.setFirstBlock(newNode) 
                    elif spr.location=='wrap':
                        #c'est un bloc englobant, le parentId est le bloc précédent, target est englobé
                        listeBlocks.addBlock(newNode)
                        #le bloc précédent va pointer son nextBlock sur newNode
                        prevBlock=listeBlocks.lastBlock(spr.parentId, a.time)
                        newPrevBlock, create=listeBlocks.addFromBlock(prevBlock,time=a.time,action='inserted_%s' % spr.location)
                        listeBlocks.addLink(prevBlock.getId(), newPrevBlock.getId())
                        listeBlocks.setNextBlock(newPrevBlock,newNode,'inserted')                        
                        #le wrap englobe jusqu'àla fin, donc le nextBlock est forcément None                      
                        listeBlocks.setNextBlock(newNode,None)                        
                        #on traite maintenant les blocks wrappés
                        wrapBlock=listeBlocks.lastBlock(spr.targetId,a.time)
                        newWrapBlock,create=listeBlocks.addFromBlock(wrapBlock,time=a.time,action='wrapped')
                        for i in newNode.inputs:
                            if i.typeMorph=='CSlotMorph':
                                newWrapBlock.rang=0
                                i.addInput(newWrapBlock)
                    else:                       
                        #soit un wrap? soit une tête de script
                        #pour test:
                        #raise ValueError('pas de location (%s) connue' % spr.location,spr.blockId)                            
                        listeBlocks.addFirstBlock(newNode) 
                    
                elif spr.type=='DROPVAL' or spr.type=='NEWVAL':                    
                    """
                    #c'est un reporter existant(DROP) ou nouveau(NEW) déplacé dans un inputSlotMorph                    
                    """
                    inputA=listeBlocks.lastBlock(spr.detail,a.time) #cible remplacée
                    if spr.type=='NEWVAL':
                        #on ajoute dans la liste, avec les inputs (comme "NEW")
                        listeBlocks.addBlock(newNode)
                        for c in spr.inputs.all():
                            inputNode,created=listeBlocks.addFromBlock(c,a.time,action=action)
                            newNode.addInput(inputNode)
                        #inputB=listeBlocks.lastBlock(spr.blockId,a.time,exact=True)
                        inputB=newNode
                        inputB.rang=inputA.rang if inputA is not None else None                   
                    else:
                        inputB=listeBlocks.lastBlock(spr.blockId,a.time) # block(s) déplacé, seulement inputs
                        
                    if inputA is None:
                        #normalement, c'est parceque c'est un inpuSlotMorph qui a été créé suite à un précédent DROPVAL
                        #on vérifie:
                        parentInputA=listeBlocks.lastBlock(spr.parentId,a.time)
                        print('nin',parentInputA)
                        nb=0
                        for i in parentInputA.inputs:
                            if (i.JMLid>100000 
                                and spr.location is not None 
                                and i.rang==int(spr.location)):
                                id=i.JMLid
                                print('on en a trouvé un',i.JMLid, 'de rang ',i.rang, 'et loc=',spr.location,i.rang==int(spr.location))
                                nb+=1
                                inputA=i
                        if nb!=1:
                            raise ValueError('Ce block n\'existe pas et son parent supposé a %s enfants' %nb,spr.detail,spr.parentId)
                        #on renumérote le JMLid
                        listeBlocks.changeJMLid(inputA.JMLid,spr.detail)                        
                        inputB.rang=inputA.rang
                        listeBlocks.addBlock(inputA)
                        #del listeBlocks.liste[id]
                        #print('removesd')
                        #parentInputA.inputs.filter()
                    #On recherche si parentA existe, et dans ce cas il faudra
                    # 1) copier les inputs 
                    # 2) remplacer l'inputA par une copie de inputB
                    # 3) une copie de l'inputA devient un block indépendant
                    listeBlocks.copyLastParentBlockandReplace(inputA, a.time, action, inputB)
                    #On recherche si parentB existe, et dans ce cas il faudra
                    # 1) copier les inputs 
                    # 2) remplacer l'inputB par un InputSlotMorph inconnu
                    if spr.type=='DROPVAL':
                        listeBlocks.copyLastParentBlockandReplace(inputB, a.time, action)
                
            if a.type=="ENV":
                env= a.environnement.all()[0]
                action='ENV_%s' % env.type
                print("ENV",env.type)
                if env.type=="DUPLIC":
                    #on duplique les blocs donnés (liste ancien-nouveau;ancien-nouveau; etc...)
                    replacement={}
                    l=[]
                    for i in env.detail.split(";"):
                        m=i.split("-")
                        if (len(m)==2):
                            print("aa",m)                        
                            blockA=listeBlocks.lastBlock(m[0],a.time)
                            blockB=blockA.copy(time=a.time)
                            blockB.JMLid=int(m[1])
                            l.append(blockA)                            
                            replacement[int(m[0])]={'id':int(m[1]),'block':blockB}
                    #modification des liens
                    firstBlock=None
                    for i in l:
                        block=replacement[i.JMLid]["block"]
                        if i.nextBlock is not None:
                            block.nextBlock=replacement[i.nextBlock.JMLid]["block"]
                        elif i.typeMorph=="CommandBlockMorph":
                            #c'est le dernier dupliqué (hors inputs)
                            listeBlocks.addLink(i.getId(),block.getId(),"dupli_fin")                         
                        if i.prevBlock is not None:
                            if i.prevBlock.JMLid in replacement:
                                block.prevBlock=replacement[i.prevBlock.JMLid]["block"]
                            else:
                                #le bloc précédent ne fait pas partie de la liste dupliquée,
                                #ce block est donc le premier
                                listeBlocks.setFirstBlock(block)
                                firstBlock=block   
                                listeBlocks.addLink(i.getId(),block.getId(),"dupli_deb")                             
                        if i.parentBlock is not None:
                            block.parentBlock=replacement[i.parentBlock.JMLid]["block"]
                        if i.lastModifBlock is not None:
                            block.lastModifBlock=replacement[i.lastModifBlock.JMLid]["block"]
                        if i.conteneurBlock is not None:
                            block.conteneurBlock=replacement[i.conteneurBlock.JMLid]["block"] 
                        if len(i.inputs)>0:
                            block.inputs=[]
                            for inp in i.inputs:
                                block.inputs.append(replacement[inp.JMLid]["block"])
                        if len(i.childs)>0:
                            block.childs=[]
                            for inp in i.childs:
                                block.childs.append(replacement[inp.JMLid]["block"])
                        if len(i.wraps)>0:
                            block.wraps=[]
                            for inp in i.wraps:
                                block.wraps.append(replacement[inp.JMLid]["block"])
                        listeBlocks.addBlock(block)
                    
    """
    datanodes=[{'data':n.toJson()} for n in cyto.nodes]
    dataedges=[{'data':n.toJson()} for n in cyto.edges]
    context={'nodes':json.dumps(datanodes),'edges':json.dumps(dataedges),
             #'maxtime':maxtime, 'firstime':firstime,
             }
    #context=s.toJson()
    return render(request, 'testcyto.html',context=context) 
    #return Response(cyto.toJson())
    """
    """
    for i in listeBlocks.ticks:
        print('temps',i)
        listeBlocks.snapAt(i)
        print('-----')
    """
    print('liste temps:',listeBlocks.ticks)
    print('liste first:',listeBlocks.firstBlocks)
    etapes=[]
    for t in listeBlocks.ticks:
        
        action=[a for a in actions if a.time==t]
        if len(action)>0:
            action=action[0].numero
        else:
            action=None
        
        etapes.append({'time':t, 'commandes':listeBlocks.snapAt(t),'action':action})
        print('XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXxx')
    
    return Response({
                     "scripts":listeBlocks.firstBlocks,
                     "data":listeBlocks.toJson(),
                     "ticks":listeBlocks.ticks,
                     'links':listeBlocks.links,
                     'etapes':etapes,
                     'actions':[a.evenementspr_set.all()[0].toD3() if a.type=='SPR'
                                            else a.environnement.all()[0].toD3() if a.type=='ENV'
                                            else a.evenementepr_set.all()[0].toD3() if a.type=='EPR' else None
                                 for a in actions]
                     })
    
             

import base64
def testAjax(request):
    image_b64 = request.POST.get('image') # This is your base64 string image
    format, imgstr = image_b64.split(';base64,')
    ext = format.split('/')[-1]
    data = ContentFile(base64.b64decode(imgstr), name='temp.' + ext)
    print('ok,data fait')
    return 