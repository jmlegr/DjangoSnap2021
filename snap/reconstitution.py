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
    """
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