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
            inputs,nextBlocks=parcoursInput(b)
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
    
        def parcoursInput(b):
            inputs=[]
            nextBlocks=[]
            for inputB in b.inputs.all():          
                inputs.append({'id':inputB.id,'JMLid':inputB.JMLid, 'typeMorph':inputB.typeMorph,                               
                           'rang':inputB.rang,
                         'contenu':inputB.contenu,
                         'conteneur':b.JMLid,
                         'parent':b.JMLid,})                                    
            for inputBlock in b.inputsBlock.all():
            #recherche de l'input correspondant
                inputB=b.inputs.filter(JMLid=inputBlock.JMLid)            
                if inputB:
                    result,nextBlocks=parcoursBlock(inputBlock)
                    for r in result:
                        r['conteneur']=b.JMLid
                        r['typeInput']='block'
                    inputs[inputB[0].rang]['contenu']=result                    
                    #inputs[inputB[0].rang]['blockConteneur']=b.JMLid
            return inputs,nextBlocks
                        
        if pk is not None:        
            evo=EvenementSPR.objects.get(id=pk)
        else:
            evo=EvenementSPR.objects.filter(type='OPEN').latest('evenement__creation')
        block=evo.scripts.all()[0]
        liste,nextLiens=parcoursBlock(block)
        ret,inp,nodes,liens=self.renderOpen(liste)
        #aff(liste)
        return liste,nextLiens,ret,inp,nodes,liens
    
    @detail_route()
    def listeOpen(self,request,pk=None):
        liste,nextLiens,ret,inp,nodes,liens=self.constructionListeOpen(pk)
        return render(request,'liste_open.html',{'tdOpen':ret,'nodes':liste,'links':nextLiens})
    
    
    @classmethod
    def renderOpen(self,r,nbTd=1):
        
        def traiteBlock(b):
            print('BLOC TRAITE',b)
            nodes={}
            liens=[]
            if b['typeMorph']!='InputSlotMorph': #(ou 'blockSpec' in b)
                #c'est un block
                nodes[b['JMLid']]={
                    'JMLid':b['JMLid'],
                    'selector':b['selector'], 'blockSpec':'%s' % b['blockSpec'],
                    'typeMorph':b['typeMorph'], 
                    #TODO: pb category toujours à NONE?
                    'category':b['category'] if 'category' in b else None,
                    #'parent':'%s' %b['parent'] pb pour compound
                    'nextBlock': b['nextBlock'],
                    'valeur':b['blockSpec'],
                    'conteneur':b['conteneur'] if 'conteneur' in b else None                                          
                    }
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
                for i in b['inputs']:
                    if i['typeMorph'] in ['CommandBlockMorph','CSlotMorph','ReporterBlockMorph']: # pas la peine de tester les chapeaux?
                        pass
                        for r in i['contenu']:
                            n,l=traiteBlock(r)
                            #for nn in n:
                            #    nn['parent']=n['conteneur']
                            for nn in n:
                                nodes[nn]=n[nn]
                            liens+=l
                                #liens.append({'source':b['JMLid'],'target':i['contenu'][0]['JMLid'], 'type':'wrap'})
                    else:
                        n,l=traiteBlock(i)
                        for nn in n:
                            nodes[nn]=n[nn]
                        liens+=l
                        liens.append({'source':b['JMLid'],'target':i['JMLid'], 'type':'child'})
                        if 'contenu' in b and type(b['contenu'])==list:
                            for i in b['contenu']:
                                n,l=traiteBlock(i)
                                for nn in n:
                                    nodes[nn]=n[nn]
                                liens+=l
            return nodes,liens            
                        
        ret=[]
        inputs={}
        nodes={}
        liens=[]
        for i in r:
            n,l=traiteBlock(i)
            for nn in n:
                nodes[nn]=n[nn]
            liens+=l
        aff(nodes,'NODES')
        aff(liens,'LIENS')
        """
        for i in r:
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
        """
        return ret,inputs,nodes,liens
    
   
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
                    'blockSpec':r['blockSpec'] if 'blockSpec' in r else None,
                    'selector':r['selector'] if 'selector' in r else None,
                    'childs':{}}
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
            return result
        
        liste,nextLiens,ret,inp,nodes,liens=self.constructionListeOpen(pk)
        
        #print('retour:')
        #for i in ret: print(i)
        #print('inputs:')
        #for i in inp: print (i,':',inp[i])
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
        newNodes={}
        for n in nodes:
            newNodes[n]=[]
            nodes[n]['time']=0
            nodes[n]['JMLid']='%s_0' % nodes[n]['JMLid']
            if nodes[n]['conteneur']:
                nodes[n]['conteneur']='%s_0' %  nodes[n]['conteneur']
            if 'nextBlock' in nodes[n] and nodes[n]['nextBlock']:
                nodes[n]['nextBlock']='%s_0' % nodes[n]['nextBlock']
            newNodes[n]=[nodes[n]]
        #et on met à jour les liens : source-> source_0
        for l in liens:
            l['source']='%s_0' % l['source']
            l['target']='%s_0' % l['target']
        for l in nextLiens:
            l['source']='%s_0' % l['source']
            l['target']='%s_0' % l['target']
            #liens.append(l)
        
        #on ajoute pour chanque id de noeud l'action associée si elle existe
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
                             'typeAction':spr.type}
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
                                    
        return inp,liste,nextLiens,nodes,liens              
    
    
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
    
    liens=[{'source':'%s' % l['source'],
            'target':'%s' % l['target'],
            'type':l['type'],
            'color':'red',
            'arrow':'triangle'} for l in liens]
    liensN=[{'source':'%s' % l['source'],
            'target':'%s' % l['target'],
            'type':'nextblock',
            'color':'blue',
            'arrow':'none'} for l in nextliens]
    liens+=liensN
        
    #datanodes=[{'data':n} for n in nodes]
    nnodes=[]
    for inode in nodes:
        n=nodes[inode]
        nn={}        
        nn['id']='%s' % n['id'] if 'id' in n else '%s' % n['JMLid']
        nn['valeur']=n['valeur']
        nn['typeMorph']=n['typeMorph']
        nn['parent']='%s' % n['conteneur'] if 'conteneur' in n else None
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
    #return context
    return Response({"data":{"name":"mon reseau"},"elements":{'nodes':datanodes,'edges':dataedges}}) 

import base64
def testAjax(request):
    image_b64 = request.POST.get('image') # This is your base64 string image
    format, imgstr = image_b64.split(';base64,')
    ext = format.split('/')[-1]
    data = ContentFile(base64.b64decode(imgstr), name='temp.' + ext)
    print('ok,data fait')
    return 