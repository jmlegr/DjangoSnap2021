'''
Created on 20 août 2018

@author: duff
'''
from snap import models, serializers
from rest_framework.decorators import api_view, renderer_classes
from rest_framework.renderers import JSONRenderer
from snap.models import EvenementENV, Evenement, EvenementSPR, EvenementEPR,\
    SnapSnapShot, ProgrammeBase, Document
import copy
import re 
from django.shortcuts import render
from rest_framework.response import Response
from django.contrib.auth.models import User
from django.db.models.aggregates import Min
from django.utils.datetime_safe import datetime
from lxml import etree


@api_view(('GET',))
@renderer_classes((JSONRenderer,))
def listesnaps(request,session_key=None):
    """renvoi les derniers snapshots
    """
    if session_key is None:
        u=User.objects.get(username='e1')
        sessions=Evenement.objects.filter(user=u).values('session_key')\
                    .order_by('session_key')\
                    .annotate(debut=Min('creation'))\
                    .order_by('-debut')
        session_key=sessions[0]['session_key']
    #snaps=SnapSnapShot.objects.filter(evenement__session_key=session_key)
    snaps=SnapSnapShot.objects.filter(evenement__user=u).select_related('evenement__user')
    evts=[s.evenement.evenementepr.all()[0] for s in snaps]
    #return Response(serializers.SnapSnapShotSerializer(snaps,many=True).data)
    #return render(request,"snapshots.html",
    return Response(
                  {"data":serializers.SnapSnapShotSerializer(snaps,many=True).data,
                  'evts':serializers.EvenementEPRSerializer(evts,many=True).data
                  })

@api_view(('GET',))
@renderer_classes((JSONRenderer,))
def listeblock(request,id=None):  
    
    def createNew(spr):
        """
        créé un nouveau block et ses inputs
        """
        newNode=listeBlocks.addSimpleBlock(JMLid=spr.blockId, 
                                  thetime=theTime,
                                  typeMorph=spr.typeMorph,
                                  blockSpec=spr.blockSpec,
                                  selector=spr.selector,
                                  category=spr.category,
                                  rang=spr.location,
                                  action=action
                                  )
        listeBlocks.setFirstBlock(newNode)
        for inp in spr.inputs.all():
            newInput=listeBlocks.addSimpleBlock(JMLid=inp.JMLid,
                                  thetime=theTime,
                                  typeMorph=inp.typeMorph,
                                  action=action,
                                  value=inp.contenu,
                                  rang=inp.rang
                                  )
            newNode.addInput(block=newInput)
            #si un input est un multiarg, il faut aller chercher dans les scripts
            #pas de récursion, c'est un ajout simple         
            if inp.typeMorph=='MultiArgMorph':
                for j in spr.scripts.get(JMLid=inp.JMLid).inputs.all():
                    inputMulti=listeBlocks.addSimpleBlock(JMLid=j.JMLid, 
                                  thetime=theTime,
                                  typeMorph=j.typeMorph,
                                  action=action,
                                  rang=j.rang,
                                  value=j.contenu
                                  )
                    newInput.addInput(inputMulti)
        return newNode
    
    #liste les derniers débuts de tous les élèves
    infos={}
    eprInfos={}
    debuts=EvenementEPR.objects.filter(type__in=['NEW','LOAD']).select_related('evenement','evenement__user').order_by('-evenement__creation')
    debut=debuts[0]
    user=debut.evenement.user
    infos['user']=user.username
    infos['date']=debut.evenement.creation
    asession=debut.evenement.session_key
    #on recupere soit un type 'LOBA', 'LOVER','NEW' ou 'LANCE'
    #evt=EvenementENV.objects.filter(evenement__session_key=asession,evenement__creation__lt=debut.evenement.creation).latest('evenement__creation')
    evt=debut
    listeBlocks=SimpleListeBlockSnap()
    if evt.type in ['NEW','LANCE']:
        #c'est un nouveau programme vide        
        infos['type']="Nouveau programme vide"
    elif evt.type in ['LOBA','LOVER']:
        #c'est un chargement de fichier
        #TODO: traiter import
        if evt.type=='LOBA':
            p=ProgrammeBase.objects.get(eleve__user=debut.evenement.user)
            f=p.file
            infos['type']='Programme de base: %s' %p.nom
            infos['tooltip']=p.description
        else:
            p=Document.objects.get(id=evt.detail)
            f=p.document
            infos['type']='Programme sauvegardé: %s' % p.description
            infos['tooltip']=p.uploaded_at
        #on reconstruit a partir du xml
        tree=etree.parse(f.path)
        root=tree.getroot()
        scripts=root.find('stage/sprites/sprite/scripts').findall('script')
        listeBlocks=SimpleListeBlockSnap()  
        for s in scripts:
            listeBlocks.addFromXML(s)
        #on suit tous les blocs non contenus
        for b in listeBlocks.liste:
            if b.typeMorph!='ScriptsMorph' and (b.parentBlockId is None or b.typeMorph=='CommentMorph'):
                listeBlocks.setFirstBlock(b)
    
    #evenements de cette partie:
    evs=Evenement.objects.filter(creation__gte=debut.evenement.creation).select_related('user').order_by('numero')
    
    #on traite les évènements
    for evt in evs:
        theTime=evt.time
        print('---- temps=',theTime)
        if evt.type=='EPR':            
            epr=evt.evenementepr.all()[0]
            print('EPR',epr)
            if epr.type in ['START','STOP','REPR','SNP','PAUSE']:                
                eprInfos['%s' % theTime]={'type':epr.type,'detail':epr.detail}                    
                if epr.type=='SNP':
                    #snp=SnapSnapShot.objects.get(id=epr.detail)
                    snp=evt.image.all()[0]
                    eprInfos['%s' % theTime]['snp']=serializers.SnapSnapShotSerializer(snp).data
                    listeBlocks.addTick(theTime)
            elif epr.type in ['ASK','ANSW']:
                #c'est une interaction avec l'utilisateur
                eprInfos['%s' % theTime]={'type':epr.type,'detail':epr.detail}
                listeBlocks.addTick(theTime)
        if evt.type=='ENV':
            env=evt.environnement.all()[0]
            action='ENV_%s' % env.type
            if env.type=='DUPLIC':
                """
                c'est une duplication, on crée et ajoute les copies
                les duplication sont sous la forme 'id1_init'-'id1_nouvelle';'id2_init'-'id2_nouvelle'; etc...
                """
                #on construit la liste des remplacements
                listeEquiv=env.detail[:-1].split(';')
                listeReplace={}
                for e in listeEquiv:
                    c=e.split('-')
                    listeReplace[c[0]]=c[1]                
                for b in listeReplace:
                    newBlock,copiedBlock=listeBlocks.lastNode(b,theTime).duplic(listeReplace,theTime,action)                    
                    listeBlocks.append(copiedBlock)
                    listeBlocks.append(newBlock)
                    if newBlock.parentBlockId is None:
                        listeBlocks.setFirstBlock(newBlock)
                    
                listeBlocks.addTick(theTime)
        if evt.type=='SPR':
            spr=evt.evenementspr.all()[0]      
            action='SPR_%s' % spr.type
            spr.aff(niv=3)        
            if spr.typeMorph in ['InputSlotMorph','ColorSlotMorph','BooleanSlotMorph']:
                #si on a créé un inp directement, la valeur est dans blockspec
                contenu=spr.blockSpec
                isSlot=True
            else:
                isSlot=False
                contenu=None
                #on ne prend pas en compte l'evènement de remplacement silencieux (qui précède un drop)

            #traitement NEW: il faut inclure les inputs,
            if spr.type=='NEW':
                newNode=createNew(spr)
                listeBlocks.addTick(theTime)
            elif spr.type=='VAL':
                #c'est une modification de la valeur (directe) d'un inputSlotMorph
                #on cherche l'input modifié (par le rang ou par le detail)
                if spr.location is None:
                    #c'est un CommentBlock (sans input). La valuer est blockSpec
                    inputNode=listeBlocks.lastNode(spr.detail,theTime).copy(theTime,action)
                    inputNode.changeValue(spr.blockSpec)
                    inputNode.blockSpec=spr.blockSpec
                    inputNode.action='VAL'                    
                    inputNode.change='changed'
                    listeBlocks.append(inputNode)  
                else:
                    inputBlock=spr.inputs.get(JMLid=spr.detail)
                    inputNode=listeBlocks.lastNode(spr.detail,theTime).copy(theTime,action)                      
                    inputNode.changeValue(inputBlock.contenu)
                    inputNode.action='VAL'
                    listeBlocks.append(inputNode)
                listeBlocks.addTick(theTime)
                #on pourrait faire un lien avec l'ancienne valeur
            elif spr.type=='NEWVAL':
                """
                c'est un reporter nouveau(NEW) déplacé dans un inputSlotMorph de l'element targetId,
                ou un nouveau inputSlot dans le cas d'un remplacement silencieux (isSlot=True)                    
                """
                if isSlot:
                    #c'est un remplacement silencieux
                    # blockid est le nouvel input, detail l'input remplacé, parentId le block parent
                    #on récupère le parent
                    parentNode=listeBlocks.lastNode(spr.targetId,theTime).copy(theTime,action)
                    listeBlocks.append(parentNode)
                    newInput=listeBlocks.addSimpleBlock(thetime=theTime,
                                                    JMLid=spr.blockId,
                                                    typeMorph=spr.typeMorph,
                                                    action=action,
                                                    value=spr.blockSpec                                                    
                                                    )
                    newInput.change='added'
                    #on récupère et modifie l'input modifié
                    oldInput=listeBlocks.lastNode(spr.detail,theTime).copy(theTime,action)
                    oldInput.change='replaced-silent'
                    oldInput.parentBlockId=None
                    oldInput.action='DROPPED'
                    if oldInput.typeMorph in ['InputSlotMorph','ColorSlotMorph','BooleanSlotMorph']:
                        listeBlocks.liste.append(oldInput)
                    else:
                        listeBlocks.liste.append(oldInput)
                        listeBlocks.setFirstBlock(oldInput)
                    #on ajuste le parent                
                    parentNode.addInput(block=newInput,rang=oldInput.rang)
                    listeBlocks.addTick(theTime)                
                else:
                    #on récupère le parent
                    parentNode=listeBlocks.lastNode(spr.targetId,theTime).copy(theTime,action)
                    listeBlocks.append(parentNode)
                    #on crée le nouveau block (et ajout dans la liste)
                    newInputNode=createNew(spr)
                    newInputNode.change='added'
                    #on récupère et modifie l'input modifié
                    oldInput=listeBlocks.lastNode(spr.detail,theTime).copy(theTime,action)
                    oldInput.change='replaced'
                    oldInput.parentBlockId=None
                    if oldInput.typeMorph in ['InputSlotMorph','ColorSlotMorph','BooleanSlotMorph']:
                        listeBlocks.liste.append(oldInput)
                    else:
                        listeBlocks.liste.append(oldInput)
                        listeBlocks.setFirstBlock(oldInput)
                    #on change l'input
                    parentNode.addInput(newInputNode)
                    listeBlocks.addTick(theTime)             
           
            elif spr.type=='DROPVAL':
                """
                c'est un reporter existant déplacé
                """
                #on récupère le parent                
                parentNode=listeBlocks.lastNode(spr.targetId,theTime).copy(theTime,action)
                listeBlocks.append(parentNode)                
                #on récupère le nouvel input
                newInputNode=listeBlocks.lastNode(spr.blockId, theTime).copy(theTime,action)
                newInputNode.change='added'
                listeBlocks.append(newInputNode)
                #on récupère et modifie l'input modifié
                oldInput=listeBlocks.lastNode(spr.detail,theTime).copy(theTime,action)
                oldInput.change='replaced'
                oldInput.parentBlockId=None
                oldInput.action="DROPPED"
                if oldInput.typeMorph in ['InputSlotMorph','ColorSlotMorph','BooleanSlotMorph']:
                    listeBlocks.append(oldInput)
                else:
                    listeBlocks.liste.append(oldInput)
                    listeBlocks.setFirstBlock(oldInput)
                #on change l'input
                parentNode.addInput(block=newInputNode,rang=oldInput.rang)
                listeBlocks.addTick(theTime)
            
            elif spr.type=='DROP' and spr.typeMorph=='ReporterBlockMorph':
                """
                c'est un reporter déplacé, éventuellement suite à un remplacement silencieux
                seules les modification de valeurs nous intéressent ici
                si c'est la suite d'un remplacement, le cas (drop) a déjà été traité,
                sinon c'est un simple déplacement
                """
                print('DROP déjà traité',spr)
                                
            elif spr.type=='DEL':
                """
                on supprime un bloc et ses descendants
                """
                newNode=listeBlocks.lastNode(spr.blockId, theTime).copy(theTime,action)
                newNode.change='deleted'
                #newNode.parentBlockId='deleted'        
                listeBlocks.append(newNode)
                listeBlocks.addTick(theTime)
                
            elif spr.type=='+IN':
                """
                c'est une nouvelle entrée d'un multiarg
                """
                newNode=listeBlocks.lastNode(spr.blockId, theTime).copy(theTime,action)
                inp=spr.inputs.get(JMLid=spr.detail)
                newInput=listeBlocks.addSimpleBlock(JMLid=inp.JMLid,
                                  thetime=theTime,
                                  typeMorph=inp.typeMorph,
                                  action=action,
                                  value=inp.contenu,
                                  rang=inp.rang
                                  )            
                newInput.change='added'
                newNode.addInput(newInput)
                listeBlocks.append(newNode)
                listeBlocks.addTick(theTime)
            elif spr.type=='-IN':
                """
                suppression du dernier input d'un multiarg
                """
                newNode=listeBlocks.lastNode(spr.blockId, theTime).copy(theTime,action)
                inputNodeId=newNode.inputs[spr.location] 
                #normalement inputNode=spr.detail
                assert inputNodeId==spr.detail
                del newNode.inputs[spr.location]
                oldInput=listeBlocks.lastNode(inputNodeId,theTime).copy(theTime,action)
                oldInput.change='replaced'
                oldInput.action='DROPPED'
                oldInput.parentBlockId=None
                if oldInput.typeMorph in ['InputSlotMorph','ColorSlotMorph','BooleanSlotMorph']:
                    listeBlocks.liste.append(oldInput)
                else:
                    listeBlocks.liste.append(oldInput)
                    listeBlocks.setFirstBlock(oldInput)
                listeBlocks.append(newNode)
                listeBlocks.addTick(theTime)
            
            
            
    #on parcours et on affiche les commandes
    commandes=[]
    for temps in listeBlocks.ticks:
        print('*********************')
        res=[]
        
        print('temps ',temps)
        for i in listeBlocks.firstBlocks:
            print('  traitement ',i)
            
            b=listeBlocks.lastNode(i,temps,veryLast=True)
            if b is None or b.parentBlockId is not None:
                res.append({'JMLid':i})
                print ('pas first')                    
            else:
                print('last:',b.time)
                resultat,nom,change=listeBlocks.parcoursBlock(i, temps, True)
                print('    resultat',resultat)
                print('    nom',nom)
                print('    change:',change)
                resultat['change']=change 
                if resultat['change'] is None and change is not None:
                    resultat['change']=change
                if resultat['change'] is not None:
                    resultat['change']='change '+resultat['change']
                res.append(resultat)
        commandes.append({'temps':temps,'snap':res,'epr':eprInfos['%s' % temps] if '%s' % temps in eprInfos else None})
    
    return Response({"commandes":commandes,
                     "scripts":listeBlocks.firstBlocks,
                     #"data":listeBlocks.toJson(),
                     "ticks":listeBlocks.ticks,
                     #'links':listeBlocks.links,
                     'etapes':{},#etapes,
                     #'actions':[a.toD3() for a in actions]
                      "infos":infos,
                     })
    """
    return render(request,'liste_entree.html',{"commandes":commandes,
                     "scripts":listeBlocks.firstBlocks,
                     #"data":listeBlocks.toJson(),
                     "ticks":listeBlocks.ticks,
                     #'links':listeBlocks.links,
                     'etapes':{},#etapes,
                     #'actions':[a.toD3() for a in actions]
                     "infos":infos,
                     })
    """
                            
"""
********************************************************
OBJETS
********************************************************
"""
def JMLID(block):
    """
    renvoie le JMLid, que block soit un blockSnap/Block/BlockInput, un dict ou une chaine/entier
    return string
    """
    if block is None:
        return None        
    if type(block)==dict:
        JMLid=block['JMLid'] if 'JMLid' in block else None
    elif type(block) in [SimpleBlockSnap,models.Block,models.BlockInput]:
        JMLid=block.JMLid        
    else:
        #on a passé l'id            
        JMLid=block
    return '%s' % JMLid


   
class SimpleBlockSnap:
    """
    Objet Block pour un temps donné
    le JMLid est forcé en string
    """    
    def __init__(self,JMLid,thetime,typeMorph,
               blockSpec=None,
               selector=None,
               category=None,
               action=None,
               rang=None,
               ):
        self.JMLid='%s' % JMLid    #JMLid du bloc, forcé en string
        self.time=thetime  #temps (Snap) de création du bloc        
        self.typeMorph=typeMorph
        self.blockSpec=blockSpec #BlockSpec du bloc
        self.selector=selector
        self.category=category # toujours à null, à vérifier ou supprimer?
        self.action=action #type d'action concernant ce block (type evenement+valeur)       
        self.nextBlockId=None      # id (string) block suivant (BlockSnap) s'il existe
        self.prevBlockId=None      # id block précédent s'il existe
        self.parentBlockId=None    # id block parent s'il existe (ie ce block est un input du parent
        self.lastModifBlockId=None      # id block temporellement précédent si une modification a eu lieu
        self.rang=rang           # rang du block dans les inputs de son parent
        self.conteneurBlockId=None # id block conteneur s'il existe (ie ce block est "wrapped"    
        self.inputs={}           # liste des id blocks inputs , sous la forme {rang:inputid}
        self.wrapped={}         # liste des ids des blocks commandes contenus, sous la forme {rang:commandid}
        self.contenu=None        # contenu du block(ie la valeur pour un InputSlotMorph)
        """
        type du changement: 
            changed pour une valeur changée
            added pour un bloc qui en remplace un autre
            deleted pour un bloc supprimé
            ...
        """        
        self.change=None
        
    
    def getId(self):
        return '%s_%s' % (self.JMLid,self.time)
    
    @classmethod
    def getJMLid(cls,block):
        """ renvoi le JMLid (string) correspondant à au block ou à l'id passée"""
        if type(block)==dict or type(block)==SimpleBlockSnap:
            return JMLID(block)            
        return block.split('_',1)[0]
    
    def setValue(self,value,init=True):
        self.contenu='%s' % value
        self.change='init' if init else 'changed'
            

    def changeValue(self,value):
        self.contenu=value
        self.change="changed"
        
    def getValue(self,toHtml=False):
        if self.typeMorph in ['InputSlotMorph','ColorSlotMorph','BooleanSlotMorph']:
            nom= "%s" % self.contenu if self.contenu is not None else None
        elif self.typeMorph in['ReporterBlockMorph',]:
            if toHtml:
                nom="<em>%s</em>" % self.blockSpec
            else:
                nom= "<%s>" %self.blockSpec
        else:
            nom= "(t)%s" % self.typeMorph        
        #return '(%s_%s)%s' %(self.JMLid,self.time,nom)
        return '%s' %(nom)
    
    def addInput(self,block=None,JMLid=None,rang=None):
        """ 
        met l'id du block en input et met le chanmps parent du block à jour
        (si block est donné)
        renvoie le JMLid de l'input remplacée         
        """
        
        if block is not None:
            inputNodeId=block.JMLid
            block.parentBlockId=self.JMLid
            if rang is not None:
                block.rang=rang
            else:
                rang=block.rang
        else:
            inputNodeId=JMLid        
        anc=self.inputs['%s' % rang] if rang in self.inputs else None        
        self.inputs['%s' %rang]=inputNodeId
        return anc
    def addWrapped(self,block=None,JMLid=None,rang=None):
        """
        met l'id du block en input et met le chanmps conteneur du block à jour
        (si block est donné)
        """
        if block is not None:
            wrappedNodeId=block.JMLid
            block.conteneurBlockId=self.JMLid
            if rang is not None:
                block.rang=rang
            else:
                rang=block.rang
        else:
            wrappedNodeId=JMLid        
        anc=self.wrapped['%s' % rang] if rang in self.wrapped else None        
        self.wrapped['%s' %rang]=wrappedNodeId
        return anc
    
    def copy(self,thetime,action):
        """ renvoie une copie complète en chabngeant time et action"""
        cp=copy.copy(self)
        cp.time=thetime
        cp.action=action
        cp.change=None
        cp.inputs={}
        for i in self.inputs:
            cp.inputs[i]=self.inputs[i]
        cp.wrapped={}
        for i in self.wrapped:
            cp.wrapped[i]=self.wrapped[i]
        return cp
    
    def duplic(self,liste,thetime,action):
        """ 
        duplique le block et remplace les différentes ids suivant la liste{id_depart:id_nouvelle}
        renvoie la version modifiée et la version copiée
        """
        
        def replace(init):
            return liste[init] if init in liste else None
        
        print('trateiemt,n',liste,self.JMLid)
        assert self.JMLid in liste
        blockOrig=self.copy(thetime,action)
        block=self.copy(thetime,action)
        block.JMLid=replace(block.JMLid)
        block.nextBlockId=replace(block.nextBlockId)
        block.prevBlockId=replace(block.prevBlockId)
        block.parentBlockId=replace(block.parentBlockId)
        block.lastModifBlockId=None
        block.conteneurBlockId=replace(block.conteneurBlockId)
        for i in block.inputs:
            block.inputs[i]=replace(block.inputs[i])
        for i in block.wrapped:
            block.wrapped[i]=replace(block.wrapped[i])
        block.change='copyfrom'
        blockOrig.change='copyto'
        return block,blockOrig
                
    def setNextBlock(self,block):
        """
        fixe le nextblock ,
        et ajuste le prevBlock de block
        """
        if block is not None:
            self.nextBlockId=block.JMLid
            block.prevBlockId=self.JMLid
        else:
            self.nextBlockId=None            
        return block
    
    def setPrevBlock(self,block):
        """
        fixe le prevBlock ,
        et ajuste le nextblock de block
        """
        if block is not None:
            self.prevBlockId=block.JMLid
            block.nextBlockId=self.JMLid
        else:
            self.prevBlockId=None
        return block
    
    def getNom(self):
        if self.rang is not None:
            rang=" (rang %s)" % self.rang
        else:
            rang=''
        if self.contenu:
            nom= "(c)%s" % self.contenu
        elif self.blockSpec:
            nom= "(s)%s" %self.blockSpec
        else:
            nom= "(t)%s" % self.typeMorph
        return '%s%s' %(nom,rang)
      
    def __str__(self):        
        return "%s_%s: %s (%s,%s)" % (self.JMLid,self.time,self.getNom(),self.action,self.change)
    def __repr__(self):
        return self.__str__()
    
class SimpleListeBlockSnap:
    """
    liste des simpleblockSnap au fil du temps    
    Les JMLid sont des strings
    """
    def __init__(self):
        self.liste=[]
        self.ticks=[0,] #liste des temps d'action
        self.firstBlocks=[] #premiers blocks des scripts
        self.links=[] #liens nextblocks, forme {source:id,target:id,type:string}        
    
        
    def addTick(self,time):
        if time not in self.ticks:
            self.ticks.append(time)
    
    def append(self,block):
        """ ajoute un block dans la liste """
        self.liste.append(block)
                
    def addSimpleBlock(self,thetime,block=None,
                       JMLid=None,typeMorph=None,
               blockSpec=None,
               selector=None,
               category=None,
               action=None,
               rang=None,
               value=None):
        """
        ajoute un nouveau  block avec temps modifié (si block donné)
        ou un nouveau block
        """
        if block is not None:
            print('creation',block)
            newb=SimpleBlockSnap(block=block,thetime=thetime)
            print('newb',newb)            
        else:
            newb=SimpleBlockSnap(JMLid=JMLid,thetime=thetime,
                                              blockSpec=blockSpec,
                                              typeMorph=typeMorph,
                                              selector=selector,
                                              category=category,
                                              rang=rang,                                              
                                              action=action)
        if value is not None:
            newb.setValue(value,init=True)
        self.liste.append(newb)
        return newb

    def setFirstBlock(self,block):
        if block.JMLid not in self.firstBlocks:
            self.firstBlocks.append(block.JMLid)
        
    def setNextBlock(self,source,destination,type='nextblock'):
        """
        (re)définit le nextBlock de source sur destination
        et met à jour les liens
        """
        source.setNextBlock(destination)
        if destination is not None:
            self.links.append({'source':source.getId(),
                           'target':destination.getId(),
                           'type':type})
    def setPrevBlock(self,source,destination,type='nextblock'):
        """
        (re)définit le prevBlock de source sur destination
        et met à jour les liens
        """
        if destination is not None:
            destination.setNextBlock(source)    
            self.links.append({'source':destination.getId(),
                           'target':source.getId(),
                           'type':type})
        
    def lastNode(self,JMLid,thetime,veryLast=False):
        """
        renvoie le dernier block (au sens du temps) de la liste
        max(temps)<=thetime si veryLast, sinon max(temps)<thetime
        """
        JMLid="%s" %JMLid
        if veryLast:
            blocks=[b for b in self.liste if b.JMLid==JMLid and b.time<=thetime]
        else:
            blocks=[b for b in self.liste if b.JMLid==JMLid and b.time<thetime]
        if len(blocks)>0:
            return sorted(blocks,key=lambda n: n.time,reverse=True)[0]
        return None
    
    def parcoursBlock(self,JMLid,thetime,toHtml=True):
        """
        reconstitue l'affiche du block au temps thetime
        """
        #traduction des mots clefs
        trad={'%clockwise':'à droite',
                  '%counterclockwise':'à gauche',
                  '%greenflag':'drapeau'}
        
        def traiteElement(block,elt,rang,resultat):
            """
            traite l'input correspondant au % elt de rang ranf
            """          
            rang='%s' %rang  
            inpId=block.inputs[rang]
            inputNode=self.lastNode(inpId,thetime,veryLast=True)  
            change=None                  
            if elt[1:] in ['c','cs','cl']: #c'est une commande
                #on ne prend que les valeurs, donc lào on ne traite pas, c'est une erreur    
                #raise ValueError("Une commande a été rencontrée alors qu'on s'attend à un input",inputNode)
                return '(commandes)',None                      
            else:
                #repl[e]=en.contenu
                if len(inputNode.inputs)>0:
                    res,repl,change=self.parcoursBlock(inputNode.JMLid,thetime,toHtml=toHtml)
                    repl='['+repl+']'
                    resultat+=res
                else:
                    #pas d'input, on récupère la valeur
                    repl=inputNode.getValue(toHtml=toHtml)                           
                if inputNode.change is not None and inputNode.time==thetime:
                    change='change '+inputNode.change
                    if inputNode.change=='init':
                        repl='*%s*' %repl
                    else:
                        #c'esrt un changement non traité
                        if toHtml:
                            repl='*<b>%s</b>*' % repl
                        else:
                            repl='*%s*' % repl
                
                if toHtml:
                    if inputNode and inputNode.time==thetime and inputNode.change is not None:                    
                        #return '(%s)%s' %(inputNode.change,repl)
                        return '<span class="%s" title="id:%s, chg:%s">%s</span>' % (inputNode.change,inputNode.JMLid,inputNode.change,repl),change 
                    else:
                        return '<span title="id:%s">%s</span>' % (inputNode.JMLid,repl),change
                return repl,change
            
        #on récupère le block
        block=self.lastNode(JMLid, thetime, veryLast=True)
        if block is None:
            print('pas de block')
            return [],''
        if block.typeMorph=='MultiArgMorph':
            #un multiarg n'est qu'une suite de %s
            block.blockSpec='|%s|'*len(block.inputs)
        nom=block.blockSpec    
        print('block ',nom)
        print('inputs ',block.inputs)
        #on cherche à remplacer les "%trucs" par les inputs 
        if block.action=='SPR_DEL' and block.time<thetime:                
                nom=''
                resultat={
                    'JMLid':block.JMLid,
                    'time':thetime,
                    'commande':nom,
                    'action':'DELETED'}
                return resultat,nom,'nochange deleted'
        
        if block.typeMorph!='CommentMorph':
            txt=re.findall(r'(%\w+)',block.blockSpec)
            repl={}
            resultat=[]
            change=None
            i=0 #rang du %truc traité
            for e in txt:
                if e in trad.keys():
                    # c'est un mot clef
                    nom=nom.replace(e,'%s' %trad[e],1)
                elif e[1:]!="words":
                    #cas général, sauf multiarg
                    repl,changed=traiteElement(block,e,i,resultat)
                    change=changed if changed is not None else change
                    nom=nom.replace(e,'%s' %repl,1)                    
                else:
                    #linput[0] est un multiarg, on parcours les inputs de ce multiarg
                    words=""
                    multiArgNode=self.lastNode(block.inputs['%s'%i],thetime,veryLast=True)
                    res,repl,changed=self.parcoursBlock(multiArgNode.JMLid,thetime,toHtml)
                    change=changed if changed is not None else change
                    words+="["+repl+"]"
                    nom=nom.replace(e,'%s' % words,1)
                i+=1
        else:
            #c'est un CommentMorph
            change=block.change if block.time==thetime else None
        resultat={'JMLid':block.JMLid,'time':thetime,'commande':nom,'action':block.action if block.time==thetime else '','change':block.change}
        #print('nom',nom,' résultat de niom',resultat)
        return resultat,nom,change
    
    def addFromXML(self,item,withScript=False):
        """
        rajoute (avec récursion) les blocks issus d'un fichier XML
        les place au temps 0
        Si withScript, on ajoute un block Script par script 
        """
        print('item',item.tag,item.items())
        if item.tag=='block' or item.tag=='custom-block':
            block=SimpleBlockSnap(item.get('JMLid'),0,item.get('typemorph'))
            if 'var' in item.attrib:
                block.contenu=item.get('var')
                block.blockSpec=item.get('var')
                self.append(block)
                return block
            
            #c'est un ['CommandBlockMorph', 'HatBlockMorph','ReporterBlockMorph'] avec blockSpec
            if item.tag=='custom-block':
                block.blockSpec=item.get('s')
            else:
                block.blockSpec=item.get('blockSpec')
            params=re.findall(r'(%\w+)',block.blockSpec)
            rang=0
            for e in params:
                if e in ['%inputs','%words','%exp','%scriptvars','%parms']:
                    #on a ttend un multiArgMorph
                    inp=self.addFromXML(item.getchildren()[rang])
                    inp.rang=rang
                    block.addInput(inp);                
                    rang+=1
                elif e in ['%c','%cs','%cl']:
                    #on attend un Cslotmorph(commandes)
                    inp=self.addFromXML(item.getchildren()[rang])
                    inp.rang=rang
                    block.addInput(inp);                
                    rang+=1                
                elif e not in ['%clockwise','%counterclockwise','%greenflag']:
                    #un seul input
                    inp=self.addFromXML(item.getchildren()[rang])
                    inp.rang=rang
                    block.addInput(inp);                
                    rang+=1
            #traitement des commentaires liés            
            for c in item.findall('comment'):
                commentBlock=SimpleBlockSnap(c.get('JMLid'),0,c.get('typemorph'))
                commentBlock.contenu=c.text
                commentBlock.blockSpec=c.text
                self.append(commentBlock)
                #TODO: peaufiner? ajouter un lien                
            self.append(block)
            return block   
        elif item.tag=='list':
            block=SimpleBlockSnap(item.get('JMLid'),0,item.get('typemorph'))
            # récupération des inputs
            for rang,inp in enumerate(item.getchildren()):
                block_in=self.addFromXML(inp)
                block_in.rang=rang
                block.addInput(block_in)
            self.append(block)
            return block
        elif item.tag=='l':
            block=SimpleBlockSnap(item.get('JMLid'),0,item.get('typemorph'))
            if len(item.getchildren())>0:
                #si c'est une 'option'
                block.contenu=item.getchildren()[0].text
            else:
                block.contenu=item.text
            self.append(block)
            return block
        elif item.tag=='color':
            block=SimpleBlockSnap(item.get('JMLid'),0,item.get('typemorph'))
            block.contenu=item.text
            self.append(block)
            return block
        elif item.tag=='script':            
            jmlid=item.get('JMLid','')
            if jmlid=='':
                #pas de jmlid, c'est un bloc de tete
                jmlid='SCRIPT_%s' % datetime.now().timestamp()
                #si pas de typeMorph, c'est que ce n'est pas un script
                #donc une variable ou opérateur etc
                block=SimpleBlockSnap(jmlid,0,item.get('typemorph','NoScriptsMorph'))
                block.blockSpec="Script_%s" % item.getparent().index(item)
                self.append(block)
                if withScript:
                    self.setFirstBlock(block)
            else:
                block=SimpleBlockSnap(jmlid,0,item.get('typemorph'))
                self.append(block)
            #on ajoute les blocks comme étant contenus
            prevblock=None
            rang=0
            #for b in item.findall('block'):
            for b in item.getchildren():
                if b.tag=='block' or b.tag=='custom-block':
                    child=self.addFromXML(b)
                    if prevblock is not None:
                        self.setNextBlock(prevblock,child)
                    block.addWrapped(block=child,rang=rang)                
                    prevblock=child                
                    rang+=1
                #block.addWrappedBlock(child)
                #TODO: liste.addWrappedBlock(block,child)
            return block
        elif item.tag=='comment':
            block=SimpleBlockSnap(item.get('JMLid'),0,item.get('typemorph'))
            block.contenu=item.text
            block.blockSpec=item.text
            self.append(block)
            return block
        
        


from snap.models import Evenement, EvenementEPR, ProgrammeBase, Document,\
    EvenementSPR, SnapSnapShot, EvenementENV
#from visualisation_boucles.models import Reconstitution
from visualisation_boucles.reconstitution import SimpleListeBlockSnap
from lxml import etree
from snap import serializers
from visualisation_boucles.serializers import SimpleSPRSerializer,\
    SimpleEvenementSerializer,InfoProgSerializer, ReperesEPRSerializer
from rest_framework.renderers import JSONRenderer
from rest_framework.utils import json
import itertools
from pymongo.mongo_client import MongoClient
from _datetime import datetime
import pymongo


affprint=False
def aff(*str):
    if affprint:
        print(*str)

def reconstruit(session_key,limit=None,save=False,load=False):
    """
    Reconstruit l'histoire du programme jusqu'au temps (depuis le départ) limite
    pour chanque block, on ajoute un attribut truc qui indique les changements:
        me: block modifié
        copyfrom: orginal d'un block (tous)
        me copyto: block copié (tous)
        me deleted: block supprimé (début)
        me deleted undrop: block supprimé (undrop d'un duplic)
    dans change (pour le parent) et truc (pour l'input) ajout de val_%s


    """

    def createNew(spr,theTime,action):
        """
        créé un nouveau block et ses inputs
        """
        newNode=listeBlocks.addSimpleBlock(JMLid=spr.blockId,
                                  thetime=theTime,
                                  typeMorph=spr.typeMorph,
                                  blockSpec=spr.blockSpec,
                                  selector=spr.selector,
                                  category=spr.category,
                                  rang=spr.location,
                                  action=action
                                  )
        
        listeBlocks.setFirstBlock(newNode) #a supprimer, on a listeJMLids
        for inp in spr.inputs.all():
            newInput=listeBlocks.addSimpleBlock(JMLid=inp.JMLid,
                                  thetime=theTime,
                                  typeMorph=inp.typeMorph,
                                  action=action,
                                  value=inp.contenu,
                                  rang=inp.rang
                                  )
            newNode.addInput(block=newInput)
            #si un input est un multiarg, il faut aller chercher dans les scripts
            #pas de récursion, c'est un ajout simple
            if inp.typeMorph=='MultiArgMorph':
                for j in spr.scripts.get(JMLid=inp.JMLid).inputs.all():
                    inputMulti=listeBlocks.addSimpleBlock(JMLid=j.JMLid,
                                  thetime=theTime,
                                  typeMorph=j.typeMorph,
                                  action=action,
                                  rang=j.rang,
                                  value=j.contenu
                                  )
                    newInput.addInput(inputMulti)
        return newNode


    #liste les derniers débuts de tous les élèves
    programme=None
    evts=[]
    if load:
        #chargement de la reconstruction (si elle existe) depuis une base mongodb
        db=MongoClient().sierpinski_db
        collection=db.reconstructions
        #on récupère les metadata (le document qui n'a pas de commandes)
        p=collection.find_one({"session_key":session_key,"commandes":{ "$exists": False}})
        if p is not None:
            #on ajoute les commandes
            liste=collection.find({"session_key":session_key,"commandes":{ "$exists": True}})
            p['commandes']=[c['commandes'] for c in liste]
            #on supprime l'ObjectId
            p.pop('_id')
            return p

    if session_key.isdigit():
        #on a envoyé une id d'évènement EPR
        epr=EvenementEPR.objects.get(id=session_key)
        debut=epr.evenement
        evts=Evenement.objects.filter(session_key=debut.session_key,creation__gte=debut.creation,time__gte=debut.time).order_by('time')
    else:
        evts=Evenement.objects.filter(session_key=session_key).order_by('time')
        debut=evts[0]
    nb_evts=evts.count()
    infos={'type':''}
    eprInfos={}
    sprInfos={}
    evtTypeInfos={}
    user=debut.user
    infos['user']=user.username
    infos['date']=debut.creation

    #on va parcourir les évènement
    drops=[]
    listeBlocks=SimpleListeBlockSnap()
    #on traite les évènements
    dtime=None
    evtPrec=None
    evt_traites=0
    for evt in evts:
        evt_traites+=1
        #print('evt',evt,evt.type,evt.id)
        if dtime is None:
            dtime=evt.time
            theTime=0
        theTime=evt.time-dtime
        evtType=evt.getEvenementType()
        evtTypeInfos['%s' % theTime]={'evenement':evt.id,
                                      'evenement_type':evt.type,
                                      'type':evtType.type,
                                      'detail':evtType.detail,
                                      'realtime':evt.time}
        history=None #memorise l'état undrop/nomove
        aff('---- temps=',theTime, evt.type,evtType)
        if evt.type=='ENV' and evtType.type in ['NEW','LANCE']:
            #c'est un nouveau programme vide
            infos['type']=" - ".join((infos['type'],"Nouveau programme vide"))
            #on précise que les blocks existants n'existent plus
            #theTime - 1 millisecond pour éviter la confusion avec la création des nouveaux blocs
            #on peut aussi faire la différence avec le numéro
            listeBlocks.initDrop()
            for i in listeBlocks.lastNodes(theTime):
                newi=listeBlocks.addSimpleBlock(theTime-1,block=i,action="DELETE")
                newi.deleted=True
            #if len(listeBlocks.liste)>0: listeBlocks.addTick(theTime-1)
            listeBlocks.addTick(theTime)
            evtPrec=evtType
        elif evt.type=='ENV' and evtType.type in ['LOBA','LOVER']:
            #c'est un chargement de fichier
            #TODO: traiter import
            if len(listeBlocks.lastNodes(theTime))>0:
                listeBlocks.lastNodes(theTime)
                for i in listeBlocks.lastNodes(theTime):
                    newi=listeBlocks.addSimpleBlock(theTime-1,block=i,action="DELETE")
                    newi.deleted=True

            if evtType.type=='LOBA':
                #on charge un programme de base
                if evtType.valueInt is not None:
                    p=ProgrammeBase.objects.get(id=evtType.valueInt) #detail contient le nom
                    f=p.file
                    infos['type']=" - ".join((infos['type'],'Programme de base: %s' %p.nom))
                    infos['tooltip']=p.description
                    try:
                        tree=etree.parse(f.path)
                        root=tree.getroot()
                        scripts=root.find('stage/sprites/sprite/scripts').findall('script')
                    except:
                        scripts=[]
                else:
                    #c'est un chargement de programme de base non existant
                    scripts=[]
            else:
                #on charge une sauvegarde
                p=Document.objects.get(id=evtType.detail)
                f=p.document
                infos['type']=" - ".join((infos['type'],'Programme sauvegardé: %s' % p.description))
                infos['tooltip']=p.uploaded_at
                #on reconstruit a partir du xml
                try:
                    tree=etree.parse(f.path)
                    root=tree.getroot()
                    scripts=root.find('stage/sprites/sprite/scripts').findall('script')
                except:
                    scripts=[]

            for s in scripts:
                listeBlocks.addFromXML(s,theTime=theTime)
            listeBlocks.initDrop() #on ne revient pas avant un chargement
            listeBlocks.addTick(theTime)

            #on suit tous les blocs non contenus
            for b in listeBlocks.liste:
                if b.time==theTime and b.typeMorph!='ScriptsMorph' and (b.parentBlockId is None or b.typeMorph=='CommentMorph'):
                    listeBlocks.setFirstBlock(b)
            evtPrec=evtType
        if evt.type=='EPR':
            #epr=evt.evenementepr.all()[0]
            epr=evtType
            aff('EPR',epr)
            if epr.type in ['START','STOP','FIN','REPR','SNP','PAUSE']:
                eprInfos['%s' % theTime]={'type':epr.type,'detail':epr.detail}
                if epr.type=='SNP':
                    eprInfos['%s' % theTime]={'type':epr.type,'detail':epr.detail}
                    #snp=SnapSnapShot.objects.get(id=epr.detail)
                    snp=evt.image.all()[0]
                    eprInfos['%s' % theTime]['snp']=serializers.SnapSnapShotSerializer(snp).data
                else:
                    eprInfos['%s' % theTime]={'type':epr.type,
                                              'detail':'{}({})'.format(epr.topBlockSelector,epr.topBlockId),
                                              'click':epr.click
                                              }
                listeBlocks.addTick(theTime)
            elif epr.type in ['ASK','ANSW']:
                #c'est une interaction avec l'utilisateur
                eprInfos['%s' % theTime]={'type':epr.type,'detail':epr.detail}
                listeBlocks.addTick(theTime)

            #evtPrec=evtType
        if evt.type=='ENV':
            #env=evt.environnement.all()[0]
            env=evtType
            action='ENV_%s' % env.type
            if env.type=='DUPLIC':
                """
                c'est une duplication, on crée et ajoute les copies
                les duplication sont sous la forme 'id1_init'-'id1_nouvelle';'id2_init'-'id2_nouvelle'; etc...
                """
                #on construit la liste des remplacements
                listeEquiv=env.detail[:-1].split(';')
                listeReplace={}
                for e in listeEquiv:
                    c=e.split('-')
                    listeReplace[c[0]]=c[1]
                for b in listeReplace:
                    bc=listeBlocks.lastNode(b,theTime)
                    if bc is None:
                        print("pas bon")
                    #on ne met pas d'action le premier bloc en aura une lors du drop
                    newBlock,copiedBlock=bc.duplic(listeReplace,theTime,None)
                    copiedBlock.truc="copyfrom"
                    newBlock.truc="copyto"
                    listeBlocks.append(copiedBlock)
                    listeBlocks.append(newBlock)
                    listeBlocks.setFirstBlock(newBlock)
                    #if newBlock.parentBlockId is None:
                    #    listeBlocks.setFirstBlock(newBlock)
                #listeBlocks.recordDrop(env,theTime)
                #listeBlocks.addTick(theTime)
                evtPrec=evtType
            if env.type=='DROPEX':
                if evtPrec.type=='DUPLIC':
                    #il faut tratier la suppression; pas besoin de vérfier, DUPLIC ne peut pas être tout seul
                    newBlock=listeBlocks.lastNode(env.valueInt, theTime)
                    newBlock.truc="me deleted"
                    newBlock.deleted=True
                    #listeBlocks.append(newBlock)
                elif evtPrec.type=='UNDROP' and evtPrec.blockId==env.valueInt:
                    #c'est un undrop+dropex, (donc annulation d'un duplic)
                    newBlock=listeBlocks.lastNode(env.valueInt, theTime)
                    newBlock.truc="me deleted undrop"
                    newBlock.deleted=True
                    #listeBlocks.append(newBlock)
                else:
                    #on ajoute l'évenement pour undrop, il sera traité conjointement avec DEL
                    #pour faire la différence avec DROP+DEL. Ainsi, soit DEL est précédé d'un DROPEX (et tout est à faire),
                    #soit il est précédé d'un DROP avec location=None, et il ne restera qu'à mettre deleted=True
                    listeBlocks.recordDrop(env,theTime)
                evtPrec=evtType
            if env.type=='AFFVAR':
                #evtTypeInfos['%s' % theTime]={'type':env.type,'detail':env.detail,'valueChar':env.valueChar,'valueBool':env.valueBool}
                evtTypeInfos['%s' % theTime]['valueChar']=env.valueChar
                evtTypeInfos['%s' % theTime]['valueBool']=env.valueBool
                listeBlocks.addTick(theTime)
            if env.type=='BUBBLE':
                #evtTypeInfos['%s' % theTime]={'type':env.type,'detail':env.detail,'valueChar':env.valueChar,'valueInt':env.valueInt}
                evtTypeInfos['%s' % theTime]['valueChar']=env.valueChar
                evtTypeInfos['%s' % theTime]['valueInt']=env.valueInt                
                listeBlocks.addTick(theTime)
            #on ne prend en compte que certains évnènements ENV, sinon souci par ex. pour undrop+dropex
            #evtPrec=evtType
        if evt.type=='SPR':
            #spr=evt.evenementspr.all()[0]
            spr=evtType            
            sprInfos['%s' % theTime]={
                'blockId':spr.blockId,
                'blockSpec':spr.blockSpec,
                'location':spr.location,
                'targetId':spr.targetId
                }
            action='SPR_%s' % spr.type
            spr.aff(niv=3)
            if spr.typeMorph in ['InputSlotMorph','ColorSlotMorph','BooleanSlotMorph']:
                #si on a créé un inp directement, la valeur est dans blockspec
                contenu=spr.blockSpec
                isSlot=True
            else:
                isSlot=False
                contenu=None
                #on ne prend pas en compte l'evènement de remplacement silencieux (qui précède un drop)
            #traitement des undrops/nomove
            if spr.type=="UNDROP":
                history="UNDROP"
                action+=" UNDROP"
                s=listeBlocks.undrop()
                if s['type']=="DROPEX":
                    dspr=EvenementENV.objects.get(id=s['spr'])
                else:
                    dspr=EvenementSPR.objects.get(id=s['spr'])
                aff("undrop de ",spr,s['time'])
                if dspr.type=="NEW":
                    #c'était une création insérée
                    #newNode=listeBlocks.getNode(spr.blockId,s['time']).copy(theTime,"UNDROPPED_DEL")
                    newNode=listeBlocks.lastNode(dspr.blockId,theTime,deleted=True).copy(theTime,action)
                    newNode.deleted=True
                    newNode.change="undrop new"
                    listeBlocks.append(newNode)
                    if newNode.conteneurBlockId is not None:
                        lastConteneur=listeBlocks.lastNode(newNode.conteneurBlockId,theTime).copy(theTime)
                        lastConteneur.setWrapped(None)
                        newNode.unwrap()
                        lastConteneur.truc="contenu"
                        listeBlocks.append(lastConteneur)
                    else:
                        lastConteneur=None
                    if newNode.prevBlockId is not None:
                        newPrevBlock=listeBlocks.lastNode(newNode.prevBlockId,theTime).copy(theTime)
                        newPrevBlock.change="uninsert"
                        newPrevBlock.truc="next"
                        newPrevBlock.setNextBlock(None)
                        listeBlocks.append(newPrevBlock)
                    else:
                        newPrevBlock=None
                    if newNode.nextBlockId is not None:
                        newNextBlock=listeBlocks.lastNode(newNode.nextBlockId,theTime).copy(theTime)
                        newNextBlock.change="uninsert"
                        newNextBlock.setPrevBlock(newPrevBlock)
                        newNextBlock.setConteneur(lastConteneur)
                        newNextBlock.truc="prev"
                        listeBlocks.append(newNextBlock)
                    else:
                        newNextBlock=None
                    if newNode.wrappedBlockId is not None:
                        #c'est un bloc contenant (donc ajouté avec wrap)
                        newNextBlock=listeBlocks.lastNode(newNode.wrappedBlockId,theTime).copy(theTime)
                        if newPrevBlock is not None:
                            newPrevBlock.setNextBlock(newNextBlock)
                        newNextBlock.unwrap()
                        newNextBlock.truc="conteneur"
                        listeBlocks.append(newNextBlock)

                elif dspr.type=="DROP" or dspr.type=="DEL":
                    #Un DEL est précédé d'un DROP (ou d'un ENV DROPEX), il faut traiter les deux d'un coup
                    #on récupère le block
                    if dspr.type=="DEL":
                        deleted=True
                        blockId=dspr.blockId
                        s=listeBlocks.undrop()
                        if s['type']!="DROPEX" and (s['blockId']!=blockId or s['location'] is not None):
                            raise Exception("PAS de drop (ou pas le bon) avant un del!")
                        else:
                            aff("                                     précédé de",s)
                            if (s['type']!='DROPEX'):
                                dspr=EvenementSPR.objects.get(id=s['spr'])
                                deleted=True
                            else:
                                deleted=False
                        newNode=listeBlocks.lastNode(dspr.blockId,theTime, deleted=True).copy(theTime,action)
                        newNode.deleted=False
                    else:
                        deleted=False                    
                        newNode=listeBlocks.lastNode(dspr.blockId,theTime).copy(theTime,action)
                    newNode.truc="me undrop"
                    #on traite le déplacement
                    listeBlocks.append(newNode)
                    if dspr.location=='bottom':
                        #on passe de target->newNode->...->finscript->nextnode (où nextnode.id=ancienTarget.next)
                        #à ancienprev(newnode)->newNode->...->finscript et target->nextNode
                        target=listeBlocks.lastNode(dspr.targetId,theTime).copy(theTime)
                        target.truc="next"
                        listeBlocks.append(target)
                        ancienTarget=listeBlocks.lastNode(dspr.targetId,s['time'],veryLast=deleted)
                        if ancienTarget.nextBlockId==newNode.JMLid:
                            # c'était un drop nomove
                            newNode.truc+=' nomove'
                        else:
                            nextNode=listeBlocks.lastNode(ancienTarget.nextBlockId,theTime)
                            if nextNode is not None:
                                nextNode=nextNode.copy(theTime)
                                nextNode.truc="prev"
                                listeBlocks.append(nextNode)
                                finScript=listeBlocks.lastNode(nextNode.prevBlockId,theTime).copy(theTime)
                                if finScript.JMLid!=newNode.JMLid:
                                    finScript.deleted=False
                                    listeBlocks.append(finScript)
                                    finScript.truc="lastnode m1"
                                else:
                                    finScript=newNode
                                    finScript.truc+=" lastnode m2"
                            else:
                                finScript=newNode
                                finScript.truc+=" lastnode m3"
        
                            ancienNode=listeBlocks.lastNode(dspr.blockId,s['time'],veryLast=deleted)
                            if ancienNode.prevBlockId is not None:
                                ancienPrevNode=listeBlocks.lastNode(ancienNode.prevBlockId,theTime,deleted=not deleted).copy(theTime)
                                ancienPrevNode.deleted=False
                                listeBlocks.append(ancienPrevNode)
                                ancienPrevNode.truc="next"
                                listeBlocks.setPrevBlock(newNode,ancienPrevNode)
                            else:
                                listeBlocks.setPrevBlock(newNode,None)
                            #on vérifie s'il n'était pas contenu
                            if ancienNode.conteneurBlockId is not None:
                                conteneur=listeBlocks.lastNode(ancienNode.conteneurBlockId,theTime).copy(theTime)
                                conteneur.truc="contenu"
                                conteneur.setWrapped(newNode)
                                listeBlocks.append(conteneur)
                            else:
                                newNode.unwrap()
        
                            if finScript.JMLid!=newNode.JMLid:
                                listeBlocks.setNextBlock(finScript,None)
                            listeBlocks.setNextBlock(target,nextNode)

                    elif dspr.location=='top':
                        #on passe de newNode->...->finscript->target
                        #à target(sans prev)  et ancienprevdenewnode->newNode->...->finScript
                        aff("                                     --------")
                        aff("                                     ",dspr.targetId)
                        target=listeBlocks.lastNode(dspr.targetId,theTime).copy(theTime)
                        target.truc="prev"
                        listeBlocks.append(target)
                        ancienNode=listeBlocks.lastNode(newNode.JMLid,s['time'],veryLast=deleted)
                        #normamelement, ça ne peut pas être un nomve (nomove à la même place)
                        newPrev=listeBlocks.lastNode(ancienNode.prevBlockId,theTime)
                        if newPrev is not None:
                            newPrev=newPrev.copy(theTime)
                            newPrev.truc="next"
                            listeBlocks.append(newPrev)
                        listeBlocks.setPrevBlock(newNode,newPrev)
                        finScript=listeBlocks.lastNode(target.prevBlockId,theTime).copy(theTime)
                        if finScript.JMLid!=newNode.JMLid:
                            listeBlocks.append(finScript)
                            finScript.truc="lastnode m5"
                            listeBlocks.setNextBlock(finScript,None)
                        else:
                            newNode.truc+=" lastnode m6"
                            listeBlocks.setNextBlock(newNode,None)
                        listeBlocks.setPrevBlock(target,None)
                    elif dspr.location=='slot':
                        conteneur=listeBlocks.lastNode(dspr.parentId,theTime).copy(theTime)
                        conteneur.truc="contenu"
                        listeBlocks.append(conteneur)
                        ancienNode=listeBlocks.lastNode(newNode.JMLid,s['time'],veryLast=deleted)
                        #if ancienNode.conteneurBlockId==newNode.targetId:
                        if ancienNode.conteneurBlockId==dspr.targetId:
                            #c'est un drop nomove
                            newNode.truc+=' nomove'
                        else:
                            if ancienNode.conteneurBlockId is not None:
                                newAncienNodeConteneur=listeBlocks.lastNode(ancienNode.conteneurBlockId,theTime).copy(theTime)
                                newAncienNodeConteneur.setWrapped(newNode)
                                newAncienNodeConteneur.truc="contenu"
                                listeBlocks.append(newAncienNodeConteneur)
                            else:
                                newNode.unwrap()
                            if ancienNode.prevBlockId is not None:
                                newAncienPrevBlock=listeBlocks.lastNode(ancienNode.prevBlockId,theTime).copy(theTime)
                                newAncienPrevBlock.truc="next"
                                listeBlocks.setNextBlock(newAncienPrevBlock,newNode)
                                listeBlocks.append(newAncienPrevBlock)
                            ancienConteneur=listeBlocks.lastNode(dspr.parentId,s['time']) #verLast=dleted?
                            if ancienConteneur.wrappedBlockId is not None:
                                contenu=listeBlocks.lastNode(ancienConteneur.wrappedBlockId,theTime).copy(theTime)
                                contenu.truc="conteneur"
                                #la fin du script droppé est le block précédent l'ancien contenu
                                finScript=listeBlocks.lastNode(contenu.prevBlockId,theTime)
                                if finScript.JMLid != newNode.JMLid:
                                    newFinScript=listeBlocks.addSimpleBlock(theTime,finScript)
                                    newFinScript.truc="lastnode m7"
                                    listeBlocks.setNextBlock(newFinScript,None)
                                else:
                                    newNode.truc+=" lastnode m8"
                                    listeBlocks.setNextBlock(newNode,None)
                                contenu.setPrevBlock(None)
                                listeBlocks.append(contenu)
                                conteneur.setWrapped(contenu)
                            else:
                                conteneur.setWrapped(None)
                                #newNode.unwrap()
                    elif dspr.location=='wrap':
                        #on remet le block conteneur a sa place (et donc maj de son prevBlock
                        # pas de nomove normalement
                        ancienNode=listeBlocks.lastNode(newNode.JMLid,s['time'],veryLast=deleted)
                        if newNode.wrappedBlockId is not None:
                            ancienContenu=listeBlocks.lastNode(newNode.wrappedBlockId,s['time']).copy(theTime)
                            contenu=listeBlocks.lastNode(newNode.wrappedBlockId,theTime).copy(theTime)
                            contenu.truc="conteneur"
                            contenu.unwrap()
                            listeBlocks.append(contenu)
                            newNode.setWrapped(None)
                        else:
                            ancienContenu=None
                        if ancienNode.prevBlockId is not None:
                            newPrevBlock=listeBlocks.lastNode(ancienNode.prevBlockId,theTime).copy(theTime)
                            newPrevBlock.truc="next"
                            newPrevBlock.setNextBlock(newNode)
                            listeBlocks.append(newPrevBlock)
                        else:
                            newPrevBlock=None
                        #on replace l'ancien prevBlock du bloc contenu
                        if ancienContenu is not None and ancienContenu.prevBlockId is not None:
                            newPrevBlock=listeBlocks.lastNode(ancienContenu.prevBlockId,theTime).copy(theTime)
                            newPrevBlock.truc="next"
                            contenu.truc+=" prev"
                            newPrevBlock.setNextBlock(contenu)
                            listeBlocks.append(newPrevBlock)

                    elif dspr.location==None:
                        #on récupère l'ancien node
                        ancienNode=listeBlocks.lastNode(newNode.JMLid,s['time'],deleted=deleted,veryLast=deleted)
                        if ancienNode.prevBlockId is None and ancienNode.conteneurBlockId is None:
                            #c'est un nomove
                            newNode.truc+=" nomove"
                        else:
                            if ancienNode.conteneurBlockId is not None:
                                newAncienNodeConteneur=listeBlocks.lastNode(ancienNode.conteneurBlockId,theTime).copy(theTime)
                                newAncienNodeConteneur.setWrapped(newNode)
                                newAncienNodeConteneur.truc="contenu"
                                listeBlocks.append(newAncienNodeConteneur)
                            else:
                                newNode.unwrap()
                            if ancienNode.prevBlockId is not None:
                                newAncienPrevBlock=listeBlocks.lastNode(ancienNode.prevBlockId,theTime,deleted=True).copy(theTime)
                                listeBlocks.setNextBlock(newAncienPrevBlock,newNode)
                                newAncienPrevBlock.truc="next"
                                listeBlocks.append(newAncienPrevBlock)
                            #on ressort tous les blocs suivants
                            #nextNode=ancienNode
                            nextNode=newNode
                            node=None
                            while nextNode.nextBlockId is not None:
                                node=nextNode
                                nextNode=listeBlocks.lastNode(nextNode.nextBlockId,theTime,deleted=True).copy(theTime)
                                listeBlocks.append(nextNode)
                                nextNode.deleted=False
                                nextNode.conteneurBlockId=None
                                listeBlocks.setNextBlock(node,nextNode)
                                if deleted: break
                            if nextNode.JMLid != newNode.JMLid:
                                nextNode.truc="prev"
                            if node is not None and node.JMLid != newNode.JMLid:
                                node.truc="lastnode m9"
                            else:
                                newNode.truc+=" lastnode m10"

                elif dspr.type=="NEWVAL":
                    #TODO Voir pour traitement silencieux et règel de undrop/nomove avec les reporter (pas correct sur snap)
                    if dspr.typeMorph in ['InputSlotMorph','ColorSlotMorph','BooleanSlotMorph']:
                        #si on a créé un inp directement, la valeur est dans blockspec
                        contenu=dspr.blockSpec
                        isSlot=True
                    else:
                        isSlot=False
                        contenu=None
                    #on récupère le parent
                    parentNode=listeBlocks.lastNode(dspr.targetId,theTime).copy(theTime,action)
                    listeBlocks.append(parentNode)
                    newInputNode=listeBlocks.lastNode(dspr.detail,theTime).copy(theTime)
                    newInputNode.change='val_newval'
                    listeBlocks.append(newInputNode)
                    #on récupère et modifie l'input modifié
                    oldInput=listeBlocks.lastNode(dspr.blockId,theTime).copy(theTime)
                    oldInput.change='val_replaced'
                    oldInput.parentBlockId=None
                    oldInput.deleted=True
                    if oldInput.typeMorph in ['InputSlotMorph','ColorSlotMorph','BooleanSlotMorph']:
                        listeBlocks.liste.append(oldInput)
                    else:
                        listeBlocks.liste.append(oldInput)
                        listeBlocks.setFirstBlock(oldInput)
                    #on change l'input
                    parentNode.addInput(newInputNode)
                elif dspr.type=="DROPVAL":
                    #on récupère le parent
                    parentNode=listeBlocks.lastNode(dspr.targetId,theTime).copy(theTime,action)
                    listeBlocks.append(parentNode)
                    newInputNode=listeBlocks.lastNode(dspr.detail,theTime).copy(theTime)
                    newInputNode.change='val_dropval'
                    listeBlocks.append(newInputNode)
                    #on récupère et modifie l'input modifié
                    oldInput=listeBlocks.lastNode(dspr.blockId,theTime).copy(theTime)
                    oldInput.change='val_replaced'
                    #on recherche s'il avait un parent
                    #ancienInput=listeBlocks.lastNode(dspr.blockId,s['time'],veryLast=deleted)
                    ancienInput=listeBlocks.lastNode(dspr.blockId,s['time'])
                    if ancienInput.parentBlockId is not None:
                        ancienParent=listeBlocks.lastNode(ancienInput.parentBlockId,theTime).copy(theTime)
                        ancienParent.addInput(oldInput)
                        listeBlocks.append(ancienParent)
                    else:
                        oldInput.parentBlockId=None

                    if oldInput.typeMorph in ['InputSlotMorph','ColorSlotMorph','BooleanSlotMorph']:
                        listeBlocks.append(oldInput)
                    else:
                        listeBlocks.append(oldInput)
                        listeBlocks.setFirstBlock(oldInput)
                    #on change l'input
                    parentNode.addInput(newInputNode)

                listeBlocks.addTick(theTime)
                        #soucis; faut il oprendre la derniere modification? la modif faite au temps du drop?
            elif spr.type=="REDROP":
                history="REDROP"
                action+=" REDROP"
                s=listeBlocks.redrop()
                spr=EvenementSPR.objects.get(id=s['spr'])
                aff("REdrop de ",spr,s['time'])
            #traitement NEW: il faut inclure les inputs,
            if spr.type=='NEW':               
                action+=" %s" % spr.location
                if history is None:                    
                    newNode=createNew(spr,theTime,action)
                    newNode.truc="me new"
                    listeBlocks.recordDrop(spr, theTime)
                else:
                    #c'est un nomove, on récupère la dernière version du noeud
                    action+=" %s" % history
                    newNode=listeBlocks.lastNode(spr.blockId,theTime,deleted=True).copy(theTime,action)
                    newNode.truc="me new nomove"
                    newNode.deleted=False
                    newNode.change=history
                    listeBlocks.append(newNode)
                newNode.truc+=" loc:%s" %spr.location
                if spr.location=="bottom":
                    #c'est un bloc ajouté à la suite d'un autre
                    prevBlock=listeBlocks.lastNode(spr.targetId,theTime)
                    newPrevBlock=listeBlocks.addSimpleBlock(theTime,
                                                            block=prevBlock
                                                            )
                    newPrevBlock.change='insert_%s' % spr.location
                    newPrevBlock.truc="next"
                    listeBlocks.setNextBlock(newPrevBlock, newNode)
                    nextBlock=listeBlocks.lastNode(prevBlock.nextBlockId,theTime)
                    if nextBlock is not None:
                        newNextBlock=listeBlocks.addSimpleBlock(theTime,
                                                                block=nextBlock)
                        newNextBlock.change='insert'
                        newNextBlock.truc="prev"
                        listeBlocks.setNextBlock(newNode,newNextBlock)
                    #on vérifie s'il n'était pas contenu
                    if newNode.conteneurBlockId is not None:
                        conteneur=listeBlocks.lastNode(newNode.conteneurBlockId,theTime).copy(theTime)
                        conteneur.setWrapped(None)
                        conteneur.truc="contenu"
                        listeBlocks.append(conteneur)
                        newNode.unwrap()
                elif spr.location=="top":
                    #c'est un block ajouté au dessus d'un autre
                    #NOTE: a priori, cela arrive seulement dans le cas où ou insère en tête de script
                    nextBlock=listeBlocks.lastNode(spr.targetId,theTime)
                    newNextBlock=listeBlocks.addSimpleBlock(theTime,
                                                            block=nextBlock
                                                            )
                    newNextBlock.change='insert_%s' % spr.location
                    newNextBlock.truc="prev"
                    listeBlocks.setNextBlock(newNode,newNextBlock)
                    #on ne vérifie pas si le next avait un prev, ça ne doit pas arriver
                elif spr.location=="slot":
                    #c'est un drop dans le CSLotMorph d'une boucle englobante
                    #parentId est le bloc englobant, targetId le CslotMorph
                    conteneurNode=listeBlocks.lastNode(spr.parentId,theTime).copy(theTime)
                    conteneurNode.truc="contenu"
                    listeBlocks.append(conteneurNode)
                    lastContenu=listeBlocks.lastNode(conteneurNode.wrappedBlockId,theTime)
                    if lastContenu is not None:
                        #l'ancien contenu devient le nextblock
                        lastContenu=lastContenu.copy(theTime)
                        lastContenu.unwrap()
                        lastContenu.truc="prev"
                        listeBlocks.append(lastContenu)
                        newNode.setNextBlock(lastContenu)
                    conteneurNode.setWrapped(newNode)
                elif spr.location=='wrap':
                    #c'est un conteneur qui vient englober les blocks à partir de targetId
                    #(et qui aura comme prevBlock parentId)
                    target=listeBlocks.lastNode(spr.targetId,theTime).copy(theTime)
                    #on recherche le parent
                    if target.prevBlockId is not None:
                        newPrevBlock=listeBlocks.lastNode(target.prevBlockId,theTime).copy(theTime)
                        newPrevBlock.setNextBlock(newNode)
                        newPrevBlock.truc="next"
                        listeBlocks.append(newPrevBlock)
                    #on se passe du cslot
                    #cslot=listeBlocks.lastNode(newNode.inputs['0'],theTime,veryLast=True)
                    #on met à jour la cible
                    target.setPrevBlock(None)
                    target.setConteneur(newNode)
                    newNode.truc="contenu"
                    target.truc="conteneur"
                    listeBlocks.append(target)


                listeBlocks.addTick(theTime)

            elif spr.type=='DROP' or spr.type=="DEL":
                #""" un DEL est soit précédé d'un DROP, soit d'un DROPEX (en ENV)
                #un DROPEX tout seul est un drop de la palette vers la palette
                #c'est une hésitation, mais pour l'instant on fait comme s'il ne sétait rien passé
                if (spr.type=="DEL" and evtPrec.type=="DROPEX"):
                    #on ne change rien, c'est comme un drop, il faudra rajouter deleted
                    action+=" DROPEX"
                    deleted=True
                else:
                    deleted=False
                if (spr.type=="DEL" and evtPrec.type=="DROP"):
                    # le DROP a déjà été traité, on modifie juste pour del
                    newNode=listeBlocks.lastNode(spr.blockId, theTime)
                    newNode.change=('' if history is None else history+' ')+'deleted'
                    newNode.action=action
                    #newNode.parentBlockId='deleted'
                    newNode.deleted=True
                    newNode.truc="me del drop"
                    listeBlocks.recordDrop(spr, theTime)
                    #attention, si le suivant est un newval sur un même bloc, c'est une suppresionn+silent-replaced
                elif (spr.type=="DROP" and evtPrec.type=="NEWVAL"):
                    #déplacement d'un input avec retour de l'ancien l'inputSlotMorph
                    print('OK NEXVAL')
                else:
                    if spr.location:
                        action+=' '+spr.location
                    if spr.typeMorph=='ReporterBlockMorph':
                        print('IOUPS')
                        """
                        c'est un reporter déplacé, éventuellement suite à un remplacement silencieux
                        seules les modification de valeurs nous intéressent ici
                        si c'est la suite d'un remplacement, le cas (drop) a déjà été traité,
                        sinon c'est un simple déplacement
                        """
                        aff('DROP déjà traité',spr)
                    nomove=False #passe à vrai si on fait un nomove (un drop à la même place)
                    if history is None:
                        listeBlocks.recordDrop(spr, theTime)
                    else:
                        action+=" %s" % history
                    #On récupère le block et on le recopie
                    if listeBlocks.lastNode(spr.blockId, theTime,deleted=True) is None:
                        assert (spr.typeMorph=="CommentMorph"),"Ne devrait pas arriver avec un non commentmorph %s %s"%(spr,spr.typeMorph)
                        #on ignore, c'est du au bug du comment supprimé mais non enlevé
                        continue
                    newNode=listeBlocks.lastNode(spr.blockId, theTime,deleted=True).copy(theTime,action)
                    newNode.deleted=False
                    newNode.truc="me drop loc:%s" % spr.location
                    #newNode.change="dropped"
                    #si ni le prevBlock ni le nextblock (ni wrapp?) ne change, c'est un simplement déplacement non pris en compte
                    #pour l'instant on le fait quand même
                    listeBlocks.append(newNode)
                    #on vérifie si le block déplacé n'était pas contenu
                    if newNode.conteneurBlockId is not None:
                        lastConteneur=listeBlocks.lastNode(newNode.conteneurBlockId,theTime).copy(theTime)
                        lastConteneur.change="etaitcontenu"
                        lastConteneur.setWrapped(None)
                        lastConteneur.truc="contenu"
                        newNode.unwrap()
                        listeBlocks.append(lastConteneur)
                    else:
                        lastConteneur=None
                        #newNode.setConteneur(None)
                    if spr.location=='bottom':
                        #c'est un bloc ajouté à la suite d'un autre
                        #on vérifie d'abord s'il n'a pas été remis à sa place
                        if newNode.prevBlockId=='%s' % spr.targetId:
                            nomove=True
                            newNode.truc+=" nomove reins"
                            newNode.change='(%s)reinserted_%s' % (spr.type,spr.location)
                            #décommenter si on veut prendre en compte quand même cet évènement (hésitation)
                            listeBlocks.addTick(theTime)
                        else:
                            newNode.change='(%s)inserted_%s' % (spr.type,spr.location)
                            #on recupere le prevblock  avant modif
                            lastPrevBlock=listeBlocks.lastNode(newNode.prevBlockId,theTime)
                            #s'il avait un prevBlock, il faut le mettre à None
                            if lastPrevBlock is not None:
                                newLastPrevBlock=lastPrevBlock.copy(theTime)
                                newLastPrevBlock.setNextBlock(None)
                                newLastPrevBlock.truc="next"
                                listeBlocks.append(newLastPrevBlock)                                
                            else:
                                newLastPrevBlock=None
                            #on configure le nouveau prevblock
                            newPrevBlock=listeBlocks.lastNode(spr.targetId,theTime).copy(theTime)
                            newPrevBlock.change="yaya"
                            #si on drop un contenu sous son conteneur, le lastconteneur est le newprevblock
                            if lastConteneur is not None:
                                if newPrevBlock.JMLid!=lastConteneur.JMLid:
                                    listeBlocks.append(newPrevBlock)
                                else:
                                    newPrevBlock=lastConteneur
                            else:
                                listeBlocks.append(newPrevBlock)
                            
                            #s'il avait un nextblock, c'est une insertion
                            if newPrevBlock.nextBlockId is not None:
                                #on prend le dernier block du script commençant par newNode (ce peut-être luui même)
                                lastFromNode=listeBlocks.lastFromBlock(theTime, newNode)
                                #print(lastFromNode.JMLid,newNode.JMLid,(lastFromNode.JMLid!=newNode.JMLid),('%s' % lastFromNode.JMLid!='%s' % newNode.JMLid))
                                assert (lastFromNode.JMLid==newNode.JMLid or '%s' % lastFromNode.JMLid!='%s' % newNode.JMLid),\
                                    "Pas le bon formt lst%s new%s" %(type(lastFromNode.JMLid),type(newNode.JMLid))
                                if lastFromNode.JMLid!=newNode.JMLid:
                                    #on insére un script newnode...lastnode
                                    lastFromNode=lastFromNode.copy(theTime)
                                    lastFromNode.truc="lastnode"
                                    listeBlocks.append(lastFromNode)
                                    newLastNextBlock=listeBlocks.lastNode(newPrevBlock.nextBlockId,theTime).copy(theTime)
                                    newLastNextBlock.truc="prev"
                                    if newLastPrevBlock is not None and newLastPrevBlock.JMLid==newLastNextBlock.JMLid:
                                        listeBlocks.setNextBlock(lastFromNode,newLastPrevBlock)
                                    else:                                    
                                        listeBlocks.append(newLastNextBlock)
                                        listeBlocks.setNextBlock(lastFromNode,newLastNextBlock)
                                else:
                                    #c'est un bloc seul
                                    newNode.truc+=" lastnode"
                                    newLastNextBlock=listeBlocks.lastNode(newPrevBlock.nextBlockId,theTime).copy(theTime)
                                    newLastNextBlock.truc="prev"
                                    if newLastPrevBlock is None or newLastNextBlock.JMLid!=newLastPrevBlock.JMLid:
                                        #la suite du script nest constituée que d'un bloc
                                        listeBlocks.append(newLastNextBlock)                                    
                                    listeBlocks.setNextBlock(newNode,newLastNextBlock)
                                #lastFromNode.truc+=" next"
                                
                            else:
                                #c'est un ajout en fin de script
                                #on prend le dernier block du script commençant par newNode (ce peut-être luui même)
                                lastFromNode=listeBlocks.lastFromBlock(theTime, newNode)
                                #print(lastFromNode.JMLid,newNode.JMLid,(lastFromNode.JMLid!=newNode.JMLid),('%s' % lastFromNode.JMLid!='%s' % newNode.JMLid))
                                assert (lastFromNode.JMLid==newNode.JMLid or '%s' % lastFromNode.JMLid!='%s' % newNode.JMLid),\
                                    "Pas le bon formt lst%s new%s" %(type(lastFromNode.JMLid),type(newNode.JMLid))
                                if lastFromNode.JMLid!=newNode.JMLid:
                                    #on insère un script
                                    lastFromNode=lastFromNode.copy(theTime)
                                    lastFromNode.truc="lastnode"
                                    listeBlocks.append(lastFromNode)
                                else:
                                    newNode.truc+=" lastnode"

                            #fin if newprevblock
                            newPrevBlock.truc="next"
                            listeBlocks.setNextBlock(newPrevBlock, newNode)
                            listeBlocks.addTick(theTime)
                    elif spr.location=='top':
                        #c'est un bloc ajouté avant d'un autre
                        #NOTE: a priori, cela arrive seulement dans le cas où ou insère en tête de script
                        #donc pas de nomove possible
                        listeBlocks.setFirstBlock(newNode)
                        newNode.change='(%s)inserted_%s' % (spr.type,spr.location)
                        #on récupère la cible
                        newNextBlock=listeBlocks.lastNode(spr.targetId,theTime).copy(theTime)
                        newNextBlock.change='insert_%s' % spr.location
                        newNextBlock.truc="prev"
                        listeBlocks.append(newNextBlock)
                        #on ne vérifie pas si le next avait un prev, ça ne doit pas arriver
                        #on va cherche le fin du script droppé (si c'en est un)
                        finBlock=listeBlocks.lastFromBlock(theTime,newNode)
                        if finBlock.JMLid!=newNode.JMLid:
                            newFinBlock=listeBlocks.addSimpleBlock(theTime,block=finBlock)
                            newFinBlock.change='insert'
                            newFinBlock.truc="lastnode"
                            listeBlocks.setNextBlock(newFinBlock,newNextBlock)
                        else:
                            newNode.truc+=" lastnode"
                            listeBlocks.setNextBlock(newNode,newNextBlock)
                        #on change le prevBlock
                        lastPrevBlock=listeBlocks.lastNode(newNode.prevBlockId,theTime)
                        if lastPrevBlock is not None:
                            if lastPrevBlock.JMLid!=newNextBlock.JMLid:
                                newLastPrevBlock=lastPrevBlock.copy(theTime)
                                newLastPrevBlock.setNextBlock(None)
                                newLastPrevBlock.truc="next"
                                listeBlocks.append(newLastPrevBlock)
                            else:
                                newNextBlock.setNextBlock(None)
                        newNode.setPrevBlock(None)
                        listeBlocks.addTick(theTime)
                    elif spr.location=="slot":
                        #c'est un drop dans le CSLotMorph d'une boucle englobante
                        #parentId est le bloc englobant, targetId le CslotMorph
                        newNode.truc+="conteneur"
                        newNode.change='wrapped'
                        conteneurNode=listeBlocks.lastNode(spr.parentId,theTime).copy(theTime)
                        conteneurNode.truc="contenu"
                        if lastConteneur and conteneurNode.JMLid==lastConteneur.JMLid:
                            '''
                            C'est un nomove dans le même slot
                            le conteneur est déj
                            '''
                            nomove=True
                            conteneurNode=lastConteneur
                            conteneurNode.truc+=' nomove'
                            newNode.truc+=" nomove"
                            lastContenu=newNode
                        else:                            
                            listeBlocks.append(conteneurNode)                            
                            lastContenu=listeBlocks.lastNode(conteneurNode.wrappedBlockId,theTime)
                            if lastContenu is not None:
                                if conteneurNode.wrappedBlockId!=lastContenu.JMLid: #comment est-ce possible?
                                    aff('lastcontenu',lastContenu)
                                    #l'ancien contenu devient le nextblock
                                    lastContenu=lastContenu.copy(theTime)
                                    lastContenu.unwrap()
                                    lastContenu.truc="prev"
                                    listeBlocks.append(lastContenu)
                                else:                                    
                                    #l'ancien contenu deviendra le nextblock
                                    pass
                                    #lastContenu=lastContenu.copy(theTime)
                                    #lastContenu.unwrap()
                                    #lastContenu.truc="prev"
                                    #listeBlocks.append(lastContenu)
                        """
                        conteneurNode=listeBlocks.lastNode(spr.parentId,theTime,veryLast=True)
                        if conteneurNode.time<theTime:
                            conteneurNode=conteneurNode.copy(theTime)
                            listeBlocks.append(conteneurNode)
                        """
                        #on recupere le prevblock avant modif
                        lastPrevBlock=listeBlocks.lastNode(newNode.prevBlockId,theTime)
                        #on ne prend en compte ce changement que s'il ne s'agit pas d'un simple déplacement
                        if lastPrevBlock is not None:
                            newNode.setPrevBlock(None)
                            if lastPrevBlock.JMLid!=conteneurNode.JMLid:
                                newLastPrevBlock=lastPrevBlock.copy(theTime)
                                newLastPrevBlock.setNextBlock(None)
                                newLastPrevBlock.truc="next"
                                listeBlocks.append(newLastPrevBlock)
                                if lastContenu is not None and lastContenu.JMLid==newLastPrevBlock.JMLid:
                                    #on remplace le haut du script
                                    lastContenu=newLastPrevBlock
                            else:
                                #le conteneur est l'ancien prev
                                conteneurNode.truc+=" next"
                                conteneurNode.setNextBlock(None)
                        else:
                            listeBlocks.setPrevBlock(newNode,None)

                        
                        #on va chercher le fin du script droppé (si c'en est un)
                        finBlock=listeBlocks.lastFromBlock(theTime,newNode)
                        if finBlock.JMLid!=newNode.JMLid:
                            newFinBlock=listeBlocks.addSimpleBlock(theTime,block=finBlock)
                            newFinBlock.change='insert'
                            newFinBlock.truc="lastnode"
                            if not nomove:
                                listeBlocks.setNextBlock(newFinBlock,lastContenu)
                            #sinon on ne change rien, le nextBlock de la fin du script ne change pas
                        else:
                            #une seule instruction
                            newNode.truc+=" lastnode"
                            if not nomove:
                                listeBlocks.setNextBlock(newNode,lastContenu)
                        conteneurNode.setWrapped(newNode)
                        aff('                                                                MMM',newNode.JMLid,newNode.conteneurBlockId,newNode.prevBlockId,'cont',conteneurNode.wrappedBlockId)
                        listeBlocks.addTick(theTime)
                    elif spr.location=='wrap':
                        #c'est un conteneur qui vient englober les blocks à partir de targetId
                        #(et qui aura comme prevBlock parentId)
                        #on recupere le prevblock avant modif
                        lastPrevBlock=listeBlocks.lastNode(newNode.prevBlockId,theTime)
                        #on ne prend en compte ce changement que s'il ne s'agit pas d'un simple déplacement
                        if lastPrevBlock is not None:
                            newNode.setPrevBlock(None)
                            newLastPrevBlock=lastPrevBlock.copy(theTime)
                            newLastPrevBlock.setNextBlock(None)
                            newLastPrevBlock.truc="next"
                            listeBlocks.append(newLastPrevBlock)
                        else:
                            listeBlocks.setPrevBlock(newNode,None)
                        target=listeBlocks.lastNode(spr.targetId,theTime).copy(theTime)
                        #on recherche le parent
                        if target.prevBlockId is not None:
                            newPrevBlock=listeBlocks.lastNode(target.prevBlockId,theTime).copy(theTime)
                            newPrevBlock.setNextBlock(newNode)
                            newPrevBlock.truc="next"
                            listeBlocks.append(newPrevBlock)
                        #on se passe du cslot
                        #cslot=listeBlocks.lastNode(newNode.inputs['0'],theTime,veryLast=True)
                        #on met à jour la cible
                        target.setPrevBlock(None)
                        target.setConteneur(newNode)
                        target.truc="conteneur"
                        listeBlocks.append(target)
                        listeBlocks.addTick(theTime)
                    elif spr.location is None:
                        #droppé tout seul, il devient bloc de tête
                        listeBlocks.setFirstBlock(newNode)
                        #on recupere le prevblock avant modif
                        lastPrevBlock=listeBlocks.lastNode(newNode.prevBlockId,theTime)
                        #on ne prend en compte ce changement que s'il ne s'agit pas d'un simple déplacement
                        if lastPrevBlock is not None:
                            newNode.change='(%s)inserted_%s' % (spr.type,spr.location)
                            #newNode.setPrevBlock(None)
                            #listeBlocks.append(newNode)
                            newLastPrevBlock=lastPrevBlock.copy(theTime)
                            newLastPrevBlock.setNextBlock(None)
                            newLastPrevBlock.truc="next"
                            listeBlocks.append(newLastPrevBlock)
                            if spr.detail=="DropDel":
                                #si c'est un drop précédent un del (dropdel), seul le bloc est déplacé,
                                #on ne modifie pas newNode.prevBlock, 
                                #il faut mettre à jour prevblock et nextblock
                                nextBlock=listeBlocks.lastNode(newNode.nextBlockId,theTime)
                                if nextBlock is not None:
                                    newNextBlock=nextBlock.copy(theTime)
                                    listeBlocks.append(newNextBlock)
                                    newNextBlock.truc="prev"
                                    newLastPrevBlock.setNextBlock(newNextBlock)
                            else:
                                #c'est un drop sans del après
                                newNode.setPrevBlock(None)
                        else:
                            #c'est un bloc de tête, on vérifie s'il n'était pas wrapped
                            if lastConteneur is not None:
                                #si c'est un simple drop, c'est déjà traité,
                                #sinon, il faut mettre le next du bloc enlevé dans le conteneur
                                if spr.detail=="DropDel":
                                    #si c'est un drop précédent un del (dropdel), seul le bloc est déplacé,
                                    #il faut mettre à jour le contenu et nextblock
                                    nextBlock=listeBlocks.lastNode(newNode.nextBlockId,theTime)
                                    if nextBlock is not None:
                                        newNextBlock=nextBlock.copy(theTime)
                                        newNextBlock.setPrevBlock(None)
                                        newNextBlock.truc="conteneur"
                                        listeBlocks.append(newNextBlock)
                                        lastConteneur.truc+=" wrap"
                                        lastConteneur.setWrapped(newNextBlock)
                            elif spr.detail=="DropDel":
                                #on met à jour l'éventuel nextblock en cas de dropdel
                                nextBlock=listeBlocks.lastNode(newNode.nextBlockId,theTime)
                                if nextBlock is not None:
                                    newNextBlock=nextBlock.copy(theTime)
                                    newNextBlock.setPrevBlock(None)
                                    newNextBlock.truc="prev"
                                    listeBlocks.append(newNextBlock)
                            else:
                                #c'est un bloc de tête juste déplacé
                                newNode.truc+=' nomove'
                        #on prend le dernier block du script commençant par newNode (ce peut-être luui même)
                        lastFromNode=listeBlocks.lastFromBlock(theTime, newNode)
                        #print(lastFromNode.JMLid,newNode.JMLid,(lastFromNode.JMLid!=newNode.JMLid),('%s' % lastFromNode.JMLid!='%s' % newNode.JMLid))
                        assert (lastFromNode.JMLid==newNode.JMLid or '%s' % lastFromNode.JMLid!='%s' % newNode.JMLid),\
                                "Pas le bon formt lst%s new%s" %(type(lastFromNode.JMLid),type(newNode.JMLid))
                        if lastFromNode.JMLid!=newNode.JMLid:
                            lastFromNode=lastFromNode.copy(theTime)
                            lastFromNode.truc="lastnode"
                            listeBlocks.append(lastFromNode)
                        else:
                            newNode.truc+=" lastnode"
                        if deleted:
                            newNode.deleted=True
                            newNode.action+=" DEL"
                            newNode.truc+=" DEL"
                            #on place tous ses next à deleted
                            #while newNode.nextBlockId is not None:
                            #    newNode=listeBlocks.lastNode(newNode.nextBlockId,theTime).copy(theTime)
                            #    newNode.deleted=True
                            #    listeBlocks.append(newNode)
                        listeBlocks.addTick(theTime)
                    if evtPrec.type=='DUPLIC':
                        #c'est suite à une duplication, on le précise
                        action+=' DUPLIC'
                        newNode.truc+=" duplic %s" % (evtPrec.evenement.time-dtime)
                        #on récupère les noeuds
                        nodes=listeBlocks.getNodes(evtPrec.evenement.time-dtime)
                        for n in nodes:
                            node=listeBlocks.lastNode(n.JMLid, theTime)
                            if node is not None:
                                #le noeud est aussi impacté à ce temps, on ne le rajoute pas
                                try:
                                    node.truc+=" %s" % n.truc
                                except AttributeError:
                                    node.truc=n.truc
                            else:
                                n.time=theTime
                        #spr.type=spr.type+'_DUPLIC'
            elif spr.type=='VAL':
                #c'est une modification de la valeur (directe) d'un inputSlotMorph
                #on cherche l'input modifié (par le rang ou par le detail)
                action+=' VAL'
                if spr.location is None:
                    #c'est un CommentBlock (sans input). La valuer est blockSpec
                    #si le commentaire est trop long (blockSpec limité à 50 car), le complément est dans detail
                    detail=spr.detail.split('(longBlockSpec)')
                    inputNode=listeBlocks.lastNode(detail[0],theTime).copy(theTime,action)
                    inputNode.changeValue(spr.blockSpec)
                    inputNode.blockSpec=detail[1] if (len(detail)>1) else spr.blockSpec
                    inputNode.action='VAL'
                    inputNode.change='val_changed <<%s>>' % inputNode.getValue()
                    inputNode.truc="val_changed"
                    listeBlocks.append(inputNode)
                else:
                    inputBlock=spr.inputs.get(JMLid=spr.detail)
                    inputNode=listeBlocks.lastNode(spr.detail,theTime).copy(theTime,action)
                    ancValue=inputNode.getValue()
                    inputNode.change='val_changed <<%s>>' % ancValue
                    inputNode.changeValue(inputBlock.contenu)
                    inputNode.action='VAL'                    
                    inputNode.truc="val_changed"
                    parentNode=listeBlocks.lastNode(spr.blockId, theTime).copy(theTime)
                    parentNode.truc="me val_inputChanged <<%s>>" % ancValue
                    listeBlocks.append(parentNode)
                    listeBlocks.append(inputNode)
                    
                listeBlocks.addTick(theTime)
                
                #on pourrait faire un lien avec l'ancienne valeur
            elif spr.type=='NEWVAL':
                """
                c'est un reporter nouveau(NEW) déplacé dans un inputSlotMorph de l'element targetId,
                ou un nouveau inputSlot dans le cas d'un remplacement silencieux (isSlot=True)
                """
                if isSlot:
                    #c'est un remplacement silencieux
                    if history is None:
                        listeBlocks.recordDrop(spr, theTime)
                        evtPrec=evtType
                    # blockid est le nouvel input, detail l'input remplacé, parentId le block parent
                    #on récupère le parent
                    parentNode=listeBlocks.lastNode(spr.parentId,theTime).copy(theTime,action)
                    listeBlocks.append(parentNode)
                    newInput=listeBlocks.addSimpleBlock(thetime=theTime,
                                                    JMLid=spr.blockId,
                                                    typeMorph=spr.typeMorph,
                                                    action=action,
                                                    value=spr.blockSpec
                                                    )
                    newInput.change='val_added'
                    parentNode.truc="me val_varinit"
                    #on récupère et modifie l'input modifié
                    print("NEWVAL SLOT",spr,spr.detail)
                    oldInput=listeBlocks.lastNode(spr.detail,theTime,deleted=True).copy(theTime,action)
                    oldInput.change='val_replaced-silent'
                    oldInput.parentBlockId=None
                    oldInput.action='DROPPED'
                    #assert (oldInput.deleted),"parent: %s, new:%s, oldrang:%s "%(parentNode,newInput,oldInput.rang)
                    if not oldInput.deleted:
                        if oldInput.typeMorph in ['InputSlotMorph','ColorSlotMorph','BooleanSlotMorph']:
                            #remplacement silencieux d'une valeur et non d'un bloc
                            listeBlocks.append(oldInput)
                        else:
                            listeBlocks.append(oldInput)
                            listeBlocks.setFirstBlock(oldInput)
                    else:
                        #on fixe le temps du DEL d'un input avec le replaced-silent (sinon on essaye de récupérer un input insexistant)
                        oldInput.time=theTime


                    #on ajuste le parent
                    #si targetID!=parentId c'est qu'on fait un remplacement silencieux au sein d'un multiarg
                    if spr.parentId==spr.targetId:
                        parentNode.addInput(block=newInput,rang=oldInput.rang)
                    else:
                        oldInputMulti=listeBlocks.lastNode(spr.targetId,theTime).copy(theTime,action)
                        listeBlocks.append(oldInputMulti)                        
                        oldInputMulti.addInput(block=newInput,rang=oldInput.rang)
                    listeBlocks.addTick(theTime)
                else:
                    if history is None:
                        #on crée le nouveau block (et ajout dans la liste)
                        newInputNode=createNew(spr,theTime,action)
                        newInputNode.change='val_added'
                        listeBlocks.recordDrop(spr, theTime)
                        evtPrec=evtType
                    else:
                        #c'est un nomove, on récupère la dernière version du noeud
                        action+=" %s" % history
                        newInputNode=listeBlocks.lastNode(spr.blockId,theTime,deleted=True).copy(theTime,action)
                        newInputNode.deleted=False
                        newInputNode.change=history
                        listeBlocks.append(newInputNode)
                    #on récupère le parent
                    parentNode=listeBlocks.lastNode(spr.targetId,theTime).copy(theTime)
                    listeBlocks.append(parentNode)
                    #on récupère et modifie l'input modifié
                    oldInput=listeBlocks.lastNode(spr.detail,theTime).copy(theTime)
                    oldInput.change='val_replaced'
                    oldInput.parentBlockId=None
                    if oldInput.typeMorph in ['InputSlotMorph','ColorSlotMorph','BooleanSlotMorph']:
                        listeBlocks.liste.append(oldInput)
                    else:
                        listeBlocks.liste.append(oldInput)
                        listeBlocks.setFirstBlock(oldInput)
                    #on change l'input
                    parentNode.addInput(newInputNode)
                    parentNode.truc="me val_varchange"
                    listeBlocks.addTick(theTime)

            elif spr.type=='DROPVAL' and spr.typeMorph!="CommentMorph":
                """
                c'est un reporter existant déplacé,
                si c'est un commentMorph, c'est un bug, sans doute changement de target, on ignore
                """
                if (evtPrec.type=="NEWVAL"):
                    #c'est un déplacement d'un input à un autre, 
                    #on ne traite cela que comme UN évènement (car le undrop le traite ainsi)
                    #on récupère la dernière modif du bloc
                    precNode=listeBlocks.lastNode(spr.blockId,theTime)
                    ancTime=precNode.time
                    #on récupère le parent
                    parentNode=listeBlocks.lastNode(spr.targetId,ancTime).copy(ancTime,action)
                    listeBlocks.append(parentNode)
                    #on récupère le nouvel input
                    newInputNode=precNode
                    newInputNode.deleted=False
                    newInputNode.change='val_added'
                    #listeBlocks.append(newInputNode)
                    #on récupère et modifie l'input modifié
                    #d=spr.detail.split('(longBlockSpec)')[0] #pour gérer le cas ou detail contient un longBlockSpec (pour CommentMorph)
                    #print("detail de dropval:",d)
                    oldInput=listeBlocks.lastNode(spr.detail,ancTime,deleted=True).copy(ancTime,action)
                    oldInput.change='val_replaced'
                    oldInput.parentBlockId=None
                    oldInput.action="DROPPED"
                    if oldInput.typeMorph in ['InputSlotMorph','ColorSlotMorph','BooleanSlotMorph']:
                        listeBlocks.append(oldInput)
                    else:
                        listeBlocks.liste.append(oldInput)
                        listeBlocks.setFirstBlock(oldInput)
                    #on change l'input
                    parentNode.addInput(block=newInputNode,rang=oldInput.rang)
                    parentNode.truc="me val_varchange"
                    #listeBlocks.addTick(theTime) 
                    #if history is None: listeBlocks.recordDrop(spr, theTime)
                else:
                    #on récupère le parent
                    parentNode=listeBlocks.lastNode(spr.targetId,theTime).copy(theTime,action)
                    listeBlocks.append(parentNode)
                    #on récupère le nouvel input
                    newInputNode=listeBlocks.lastNode(spr.blockId, theTime,deleted=True).copy(theTime,action)
                    newInputNode.deleted=False
                    newInputNode.change='val_added'
                    listeBlocks.append(newInputNode)
                    #on récupère et modifie l'input modifié
                    #d=spr.detail.split('(longBlockSpec)')[0] #pour gérer le cas ou detail contient un longBlockSpec (pour CommentMorph)
                    #print("detail de dropval:",d)
                    oldInput=listeBlocks.lastNode(spr.detail,theTime,deleted=True).copy(theTime,action)
                    oldInput.change='val_replaced'
                    oldInput.parentBlockId=None
                    oldInput.action="DROPPED"
                    if oldInput.typeMorph in ['InputSlotMorph','ColorSlotMorph','BooleanSlotMorph']:
                        listeBlocks.append(oldInput)
                    else:
                        listeBlocks.liste.append(oldInput)
                        listeBlocks.setFirstBlock(oldInput)
                    #on change l'input
                    parentNode.addInput(block=newInputNode,rang=oldInput.rang)
                    parentNode.truc="me val_varchange"
                    listeBlocks.addTick(theTime)
                    if history is None: listeBlocks.recordDrop(spr, theTime)

            elif spr.type=='+IN':
                """
                c'est une nouvelle entrée d'un multiarg
                """
                newNode=listeBlocks.lastNode(spr.blockId, theTime).copy(theTime,action)
                inp=spr.inputs.get(JMLid=spr.detail)
                newInput=listeBlocks.addSimpleBlock(JMLid=inp.JMLid,
                                  thetime=theTime,
                                  typeMorph=inp.typeMorph,
                                  action=action,
                                  value=inp.contenu,
                                  rang=inp.rang
                                  )
                newInput.change='val_added'
                newInput.truc="val_added"
                newNode.truc="me val_addinput"
                newNode.addInput(newInput)
                listeBlocks.append(newNode)
                listeBlocks.addTick(theTime)
            elif spr.type=='-IN':
                """
                suppression du dernier input d'un multiarg
                """
                newNode=listeBlocks.lastNode(spr.blockId, theTime).copy(theTime,action)
                inputNodeId=newNode.inputs[spr.location]
                #normalement inputNode=spr.detail
                assert inputNodeId==spr.detail
                del newNode.inputs[spr.location]
                oldInput=listeBlocks.lastNode(inputNodeId,theTime).copy(theTime,action)
                oldInput.change='val_replaced'
                oldInput.action='DROPPED'
                oldInput.parentBlockId=None
                if oldInput.typeMorph in ['InputSlotMorph','ColorSlotMorph','BooleanSlotMorph']:
                    listeBlocks.liste.append(oldInput)
                else:
                    listeBlocks.liste.append(oldInput)
                    listeBlocks.setFirstBlock(oldInput)
                listeBlocks.append(newNode)
                listeBlocks.addTick(theTime)


            evtPrec=evtType
        #if theTime in listeBlocks.ticks:
        #    print("XXXXXXXXXXXXXXXXXXXXXXXXXXX")
        #    print("ITICK",theTime)
        if limit is not None and theTime > limit:
            break
    #on parcours et on affiche les commandes
    commandes=[]
    nb_ticks=len(listeBlocks.ticks)
    ticks_traites=0
    for temps in listeBlocks.ticks:
        ticks_traites+=1
        #print('*********************')
        res=[]

        #print('temps ',temps)
        for i in listeBlocks.firstBlocks:

            b=listeBlocks.lastNode(i,temps,veryLast=True)
            aff('  traitement ',i,"b",listeBlocks.liste)
            if b is None or b.parentBlockId is not None or (b.deleted and not b.action):# or b.prevBlockId is not None:
                res.append({'JMLid':i})
                aff ('pas first')
            else:
                aff('last:',b.time)
                resultat,nom,change=listeBlocks.parcoursBlock(i, temps, True)
                aff('    resultat',resultat)
                aff('    nom',nom)
                aff('    change:',change)
                #resultat['change']=change
                if change:
                    resultat['change']='AAchangeAA '+resultat['change']+"AA"+change
                else:
                    if resultat['action']:
                        resultat['change']='AAchangeACTION'+ resultat["action"]
                    else:
                        resultat['change']='XXchangeXX '+resultat['change']+"XX"+change
                res.append(resultat)
        #les résultats ne sont pas dans l'ordre!
        #le client devra retouver les blocs de débuts (prevBlock=None et parent=None)
        #puis reconstruire
        commandes.append({'temps':temps,'snap':res,
                          'epr':eprInfos['%s' % temps] if '%s' % temps in eprInfos else None,
                          'spr':sprInfos['%s' % temps] if '%s' % temps in sprInfos else None,
                          'evt':evtTypeInfos['%s' % temps] if '%s' % temps in evtTypeInfos else None})
    #print('-----------------------------------------------------------------------------------------')
    #for i in listeBlocks.liste:
    #    print(i)
    #print('-----------------------------------------------------------------------------------------')
    #sauvegarde dans la base (avec écrasement)    
    return {"commandes":commandes,
                     "scripts":listeBlocks.firstBlocks,
                     #"data":listeBlocks.toJson(),
                     "ticks":listeBlocks.ticks,
                     #'links':listeBlocks.links,
                     'etapes':{},#etapes,
                     #'actions':[a.toD3() for a in actions]
                      "infos":infos,
                      "session":session_key,
                      #'infos':evtTypeInfos
                      "created":True,
                      }
