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
from snap.views import liste
from snap.reconstitution import listeblock

affprint=False
def aff(*str):
    if affprint:
        print(*str)

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
def listeblock(request,session_key=None):  
    
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
    aff("session",session_key)
    if session_key.isdigit():
        #on a envoyé une id d'évènement EPR
        epr=EvenementEPR.objects.get(id=session_key)
        debut=epr.evenement
        evts=Evenement.objects.filter(session_key=debut.session_key,creation__gte=debut.creation,time__gte=debut.time).order_by('time')
    else:
        evts=Evenement.objects.filter(session_key=session_key).order_by('time')
        debut=evts[0]
    infos={}
    eprInfos={}  
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
    for evt in evts:
        print('evt',evt,evt.type,evt.id)
        if dtime is None:
            dtime=evt.time
            theTime=0
        theTime=evt.time-dtime        
        
        evtType=evt.getEvenementType()
        evtTypeInfos['%s' % theTime]={'evenement':evt.id,
                                      'evenement_type':evt.type,
                                      'type':evtType.type}
        history=None #memorise l'état undrop/redrop
        aff('---- temps=',theTime, evt.type,evtType)
        if evt.type=='ENV' and evtType.type in ['NEW','LANCE']:
            #c'est un nouveau programme vide        
            infos['type']="Nouveau programme vide"
            #on précise que les blocks existants n'existent plus
            #theTime - 1 millisecond pour éviter la confusion avec la création des nouveaux blocs
            #on peut aussi faire la différence avec le numéro
            listeBlocks.initDrop()
            for i in listeBlocks.lastNodes(theTime):
                newi=listeBlocks.addSimpleBlock(theTime-1,block=i,action="DELETE")
                newi.deleted=True
            if len(listeBlocks.liste)>0: listeBlocks.addTick(theTime-1)
            evtPrec=evtType
        elif evt.type=='ENV' and evtType.type in ['LOBA','LOVER']:
            #c'est un chargement de fichier
            #TODO: traiter import
            for i in listeBlocks.lastNodes(theTime):
                newi=listeBlocks.addSimpleBlock(theTime-1,block=i,action="DELETE")
                newi.deleted=True
            listeBlocks.addTick(theTime-1)
            if evtType.type=='LOBA':
                p=ProgrammeBase.objects.get(id=evtType.valueInt) #detail contient le nom
                f=p.file
                infos['type']='Programme de base: %s' %p.nom
                infos['tooltip']=p.description
            else:
                p=Document.objects.get(id=evtType.detail)
                f=p.document
                infos['type']='Programme sauvegardé: %s' % p.description
                infos['tooltip']=p.uploaded_at
                #on reconstruit a partir du xml
            tree=etree.parse(f.path)
            root=tree.getroot()
            scripts=root.find('stage/sprites/sprite/scripts').findall('script')
          
            for s in scripts:
                listeBlocks.addFromXML(s,theTime=theTime)
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
            evtPrec=evtType
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
                    newBlock,copiedBlock=bc.duplic(listeReplace,theTime,action)                    
                    listeBlocks.append(copiedBlock)
                    listeBlocks.append(newBlock)
                    if newBlock.parentBlockId is None:
                        listeBlocks.setFirstBlock(newBlock)
                    
                listeBlocks.addTick(theTime)
            if env.type=="DROPEX":
                #on ajoute l'évenement pour undrop, il sera traité conjointement avec DEL
                #pour faire la différence avec DROP+DEL. Ainsi, soit DEL est précédé d'un DROPEX (et tout est à faire),
                #soit il est précédé d'un DROP avec location=None, et il ne restera qu'à mettre deleted=True
                listeBlocks.recordDrop(env,theTime)
            evtPrec=evtType
        if evt.type=='SPR':
            #spr=evt.evenementspr.all()[0]
            spr=evtType      
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
            #traitement des undrops/redrop
            if spr.type=="UNDROP":
                history="UNDROP"
                action+=" UNDROP"
                s=listeBlocks.undrop()
                dspr=EvenementSPR.objects.get(id=s['spr'])
                aff("undrop de ",spr,s['time'])
                if dspr.type=="NEW":
                    #c'était une création insérée
                    #newNode=listeBlocks.getNode(spr.blockId,s['time']).copy(theTime,"UNDROPPED_DEL") 
                    newNode=listeBlocks.lastNode(dspr.blockId,theTime,deleted=True).copy(theTime,action)
                    newNode.deleted=True
                    newNode.change="undrop delete"
                    listeBlocks.append(newNode)
                    if newNode.conteneurBlockId is not None:
                        lastConteneur=listeBlocks.lastNode(newNode.conteneurBlockId,theTime).copy(theTime)
                        lastConteneur.setWrapped(None)
                        newNode.unwrap()
                        listeBlocks.append(lastConteneur)
                    if newNode.prevBlockId is not None:
                        newPrevBlock=listeBlocks.lastNode(newNode.prevBlockId,theTime).copy(theTime)
                        newPrevBlock.change="uninsert"
                        newPrevBlock.setNextBlock(None)
                        listeBlocks.append(newPrevBlock)                        
                    if newNode.nextBlockId is not None:
                        newNextBlock=listeBlocks.lastNode(newNode.nextBlockId,theTime).copy(theTime)
                        newNextBlock.change="uninsert"
                        newNextBlock.setPrevBlock(None)
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
                    #on traite le déplacement                 
                    listeBlocks.append(newNode)
                    if dspr.location=='bottom':
                        #on passe de target->newNode->...->finscript->nextnode (où nextnode.id=ancienTarget.next)
                        #à ancienprev(newnode)->newNode->...->finscript et target->nextNode
                        target=listeBlocks.lastNode(dspr.targetId,theTime).copy(theTime)
                        listeBlocks.append(target)
                        ancienTarget=listeBlocks.lastNode(dspr.targetId,s['time'],veryLast=deleted)
                        nextNode=listeBlocks.lastNode(ancienTarget.nextBlockId,theTime)
                        if nextNode is not None:
                            nextNode=nextNode.copy(theTime)   
                            listeBlocks.append(nextNode)
                            finScript=listeBlocks.lastNode(nextNode.prevBlockId,theTime).copy(theTime)
                            if finScript.JMLid!=newNode.JMLid:
                                finScript.deleted=False
                                listeBlocks.append(finScript)
                            else:
                                finScript=newNode
                        else:
                            finScript=newNode
                        ancienNode=listeBlocks.lastNode(dspr.blockId,s['time'],veryLast=deleted)                        
                        if ancienNode.prevBlockId is not None:
                            ancienPrevNode=listeBlocks.lastNode(ancienNode.prevBlockId,theTime,deleted=not deleted).copy(theTime)
                            ancienPrevNode.deleted=False
                            listeBlocks.append(ancienPrevNode)
                            listeBlocks.setPrevBlock(newNode,ancienPrevNode)
                        else:
                            listeBlocks.setPrevBlock(newNode,None)
                        #on vérifie s'il n'était pas contenu
                        if ancienNode.conteneurBlockId is not None:
                            conteneur=listeBlocks.lastNode(ancienNode.conteneurBlockId,theTime).copy(theTime)
                            conteneur.setWrapped(newNode)
                            listeBlocks.append(conteneur)
                        else:
                            newNode.unwrap()
                        
                        listeBlocks.setNextBlock(finScript,None)
                        listeBlocks.setNextBlock(target,nextNode)
                        
                    elif dspr.location=='top':
                        #on passe de newNode->...->finscript->target 
                        #à target(sans prev)  et ancienprevdenewnode->newNode->...->finScript
                        aff("                                     --------")
                        aff("                                     ",dspr.targetId)    
                        target=listeBlocks.lastNode(dspr.targetId,theTime).copy(theTime)                        
                        listeBlocks.append(target)
                        ancienNode=listeBlocks.lastNode(newNode.JMLid,s['time'])
                        newPrev=listeBlocks.lastNode(ancienNode.prevBlockId,theTime)
                        if newPrev is not None:
                            newPrev=newPrev.copy(theTime)                            
                            listeBlocks.append(newPrev)
                        listeBlocks.setPrevBlock(newNode,newPrev)
                        finScript=listeBlocks.lastNode(target.prevBlockId,theTime).copy(theTime)                        
                        if finScript.JMLid!=newNode.JMLid:
                            listeBlocks.append(finScript)
                            listeBlocks.setNextBlock(finScript,None)
                        else:
                            listeBlocks.setNextBlock(newNode,None)
                        listeBlocks.setPrevBlock(target,None)
                    elif dspr.location=='slot':
                        conteneur=listeBlocks.lastNode(dspr.parentId,theTime).copy(theTime)
                        listeBlocks.append(conteneur)
                        ancienNode=listeBlocks.lastNode(newNode.JMLid,s['time'])
                        if ancienNode.conteneurBlockId is not None:
                            newAncienNodeConteneur=listeBlocks.lastNode(ancienNode.conteneurBlockId,theTime).copy(theTime)
                            newAncienNodeConteneur.setWrapped(newNode)
                            listeBlocks.append(newAncienNodeConteneur)
                        else:
                            newNode.unwrap()
                        if ancienNode.prevBlockId is not None:
                            newAncienPrevBlock=listeBlocks.lastNode(ancienNode.prevBlockId,theTime).copy(theTime)
                            listeBlocks.setNextBlock(newAncienPrevBlock,newNode)
                            listeBlocks.append(newAncienPrevBlock)                        
                        ancienConteneur=listeBlocks.lastNode(dspr.parentId,s['time'])
                        if ancienConteneur.wrappedBlockId is not None:
                            contenu=listeBlocks.lastNode(ancienConteneur.wrappedBlockId,theTime).copy(theTime)                            
                            #la fin du script droppé est le block précédent l'ancien contenu
                            finScript=listeBlocks.lastNode(contenu.prevBlockId,theTime)
                            if finScript.JMLid != newNode.JMLid:
                                newFinScript=listeBlocks.addSimpleBlock(theTime,finScript)
                                listeBlocks.setNextBlock(newFinScript,None)
                            else:
                                listeBlocks.setNextBlock(newNode,None)                                
                            contenu.setPrevBlock(None)                            
                            listeBlocks.append(contenu)
                            conteneur.setWrapped(contenu)
                        else:
                            conteneur.setWrapped(None)
                            newNode.unwrap()
                    elif dspr.location==None:
                        #on récupère l'ancien node
                        ancienNode=listeBlocks.lastNode(newNode.JMLid,s['time'])
                        if ancienNode.conteneurBlockId is not None:
                            newAncienNodeConteneur=listeBlocks.lastNode(ancienNode.conteneurBlockId,theTime).copy(theTime)
                            newAncienNodeConteneur.setWrapped(newNode)
                            listeBlocks.append(newAncienNodeConteneur)
                        else:
                            newNode.unwrap()
                        if ancienNode.prevBlockId is not None:
                            newAncienPrevBlock=listeBlocks.lastNode(ancienNode.prevBlockId,theTime,deleted=True).copy(theTime)
                            listeBlocks.setNextBlock(newAncienPrevBlock,newNode)
                            listeBlocks.append(newAncienPrevBlock)   
                        nextNode=ancienNode                     
                        while nextNode.nextBlockId is not None:
                            nextNode=listeBlocks.lastNode(nextNode.nextBlockId,theTime,deleted=True).copy(theTime)
                            listeBlocks.append(nextNode)
                            nextNode.deleted=False
                            listeBlocks.setNextBlock(newNode,nextNode)
                            newNode=nextNode                    
                
                elif dspr.type=="NEWVAL":
                    #TODO Voir pour traitement silencieux et règel de undrop/redrop avec les reporter (pas correct sur snap)
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
                    newInputNode.change='newval'
                    listeBlocks.append(newInputNode)
                    #on récupère et modifie l'input modifié
                    oldInput=listeBlocks.lastNode(dspr.blockId,theTime).copy(theTime)
                    oldInput.change='replaced'
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
                    newInputNode.change='dropval'
                    listeBlocks.append(newInputNode)
                    #on récupère et modifie l'input modifié
                    oldInput=listeBlocks.lastNode(dspr.blockId,theTime).copy(theTime)
                    oldInput.change='replaced'
                    #on recherche s'il avait un parent
                    ancienInput=listeBlocks.lastNode(dspr.blockId,s['time'])
                    if ancienInput.parentBlockId is not None:
                        ancienParent=listeBlocks.lastNode(ancienInput.parentBlockId,theTime).copy(theTime)
                        ancienParent.addInput(oldInput)
                        listeBlocks.append(ancienParent)
                    else:
                        oldInput.parentBlockId=None
                        
                    if oldInput.typeMorph in ['InputSlotMorph','ColorSlotMorph','BooleanSlotMorph']:
                        listeBlocks.liste.append(oldInput)
                    else:
                        listeBlocks.liste.append(oldInput)
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
                    listeBlocks.recordDrop(spr, theTime)
                else:
                    #c'est un redrop, on récupère la dernière version du noeud
                    action+=" %s" % history
                    newNode=listeBlocks.lastNode(spr.blockId,theTime,deleted=True).copy(theTime,action)
                    newNode.deleted=False
                    newNode.change=history
                    listeBlocks.append(newNode)
                if spr.location=="bottom":
                    
                    #c'est un bloc ajouté à la suite d'un autre
                    prevBlock=listeBlocks.lastNode(spr.targetId,theTime)
                    newPrevBlock=listeBlocks.addSimpleBlock(theTime, 
                                                            block=prevBlock 
                                                            )
                    newPrevBlock.change='insert_%s' % spr.location
                    listeBlocks.setNextBlock(newPrevBlock, newNode)
                    nextBlock=listeBlocks.lastNode(prevBlock.nextBlockId,theTime)                    
                    if nextBlock is not None:
                        newNextBlock=listeBlocks.addSimpleBlock(theTime,
                                                                block=nextBlock)
                        newNextBlock.change='insert'
                        listeBlocks.setNextBlock(newNode,newNextBlock)
                    #on vérifie s'il n'était pas contenu
                    if newNode.conteneurBlockId is not None:
                        conteneur=listeBlocks.lastNode(newNode.conteneurBlockId,theTime).copy(theTime)
                        conteneur.setWrapped(None)
                        newNode.unwrap()
                elif spr.location=="top":
                    #c'est un block ajouté au dessus d'un autre
                    #NOTE: a priori, cela arrive seulement dans le cas où ou insère en tête de script
                    nextBlock=listeBlocks.lastNode(spr.targetId,theTime)
                    newNextBlock=listeBlocks.addSimpleBlock(theTime, 
                                                            block=nextBlock 
                                                            )
                    newNextBlock.change='insert_%s' % spr.location
                    listeBlocks.setNextBlock(newNode,newNextBlock)
                    #on ne vérifie pas si le next avait un prev, ça ne doit pas arriver      
                elif spr.location=="slot":
                    #c'est un drop dans le CSLotMorph d'une boucle englobante
                    #parentId est le bloc englobant, targetId le CslotMorph
                    conteneurNode=listeBlocks.lastNode(spr.parentId,theTime).copy(theTime)
                    listeBlocks.append(conteneurNode)
                    lastContenu=listeBlocks.lastNode(conteneurNode.wrappedBlockId,theTime)
                    if lastContenu is not None:
                        #l'ancien contenu devient le nextblock
                        lastContenu=lastContenu.copy(theTime)
                        lastContenu.unwrap()
                        listeBlocks.append(lastContenu)
                        newNode.setNextBlock(lastContenu)
                    conteneurNode.setWrapped(newNode)                   
                     
                                 
                listeBlocks.addTick(theTime)
            
            elif spr.type=='DROP' or spr.type=="DEL":
                #""" un DEL est soit précédé d'un DROP, soit d'un DROPEX (en ENV)
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
                    listeBlocks.recordDrop(spr, theTime)
                else:  
                    if spr.location:
                        action+=' '+spr.location
                    if spr.typeMorph=='ReporterBlockMorph':
                        """
                        c'est un reporter déplacé, éventuellement suite à un remplacement silencieux
                        seules les modification de valeurs nous intéressent ici
                        si c'est la suite d'un remplacement, le cas (drop) a déjà été traité,
                        sinon c'est un simple déplacement
                        """
                        aff('DROP déjà traité',spr)                
                    
                    if history is None:
                        listeBlocks.recordDrop(spr, theTime)
                    else:
                        action+=" %s" % history
                    #On récupère le block et on le recopie
                    newNode=listeBlocks.lastNode(spr.blockId, theTime).copy(theTime,action)
                    #si ni le prevBlock ni le nextblock (ni wrapp?) ne change, c'est un simplement déplacement non pris en compte
                    #pour l'instant on le fait quand même                
                    listeBlocks.append(newNode)
                    #on vérifie si le block déplacé n'était pas contenu
                    if newNode.conteneurBlockId is not None:
                        lastConteneur=listeBlocks.lastNode(newNode.conteneurBlockId,theTime).copy(theTime)
                        lastConteneur.change="youyou"
                        lastConteneur.setWrapped(None)
                        newNode.unwrap()
                        listeBlocks.append(lastConteneur)
                        #newNode.setConteneur(None)
                    if spr.location=='bottom':                    
                        #c'est un bloc ajouté à la suite d'un autre
                        #on vérifie d'abord s'il n'a pas été remis à sa place
                        if newNode.prevBlockId=='%s' % spr.targetId:
                            newNode.change='(%s)reinserted_%s' % (spr.type,spr.location)
                            #décommenter si on veut prendre en compte quand même cet évènement (hésitation)
                            #listeBlocks.addTick(theTime)
                        else:                            
                            newNode.change='(%s)inserted_%s' % (spr.type,spr.location)
                            #on recupere le prevblock  avant modif
                            lastPrevBlock=listeBlocks.lastNode(newNode.prevBlockId,theTime)                    
                            #s'il avait un prevBlock, il faut le mettre à None                 
                            if lastPrevBlock is not None:
                                newLastPrevBlock=lastPrevBlock.copy(theTime)
                                newLastPrevBlock.setNextBlock(None)
                                listeBlocks.append(newLastPrevBlock)
                            #on configure le nouveau prevblock
                            newPrevBlock=listeBlocks.lastNode(spr.targetId,theTime).copy(theTime)
                            newPrevBlock.change="yaya"
                            listeBlocks.append(newPrevBlock)
                            #s'il avait un nextblock, c'est une insertion
                            if newPrevBlock.nextBlockId is not None:                        
                                #on prend le dernier block du script commençant par newNode (ce peut-être luui même)
                                lastFromNode=listeBlocks.lastFromBlock(theTime, newNode)
                                print(lastFromNode.JMLid,newNode.JMLid,(lastFromNode.JMLid!=newNode.JMLid),('%s' % lastFromNode.JMLid!='%s' % newNode.JMLid))
                                assert (lastFromNode.JMLid==newNode.JMLid or '%s' % lastFromNode.JMLid!='%s' % newNode.JMLid),\
                                    "Pas le bon formt lst%s new%s" %(type(lastFromNode.JMLid),type(newNode.JMLid))
                                if lastFromNode.JMLid!=newNode.JMLid:
                                    lastFromNode=lastFromNode.copy(theTime)
                                    listeBlocks.append(lastFromNode)
                                newLastNextBlock=listeBlocks.lastNode(newPrevBlock.nextBlockId,theTime).copy(theTime)
                                listeBlocks.append(newLastNextBlock)
                                listeBlocks.setNextBlock(lastFromNode,newLastNextBlock)
                            listeBlocks.setNextBlock(newPrevBlock, newNode)                    
                            listeBlocks.addTick(theTime)
                    elif spr.location=='top':
                        #c'est un bloc ajouté avant d'un autre
                        #NOTE: a priori, cela arrive seulement dans le cas où ou insère en tête de script
                        newNode.change='(%s)inserted_%s' % (spr.type,spr.location)
                        #on récupère la cible
                        nextBlock=listeBlocks.lastNode(spr.targetId,theTime)
                        newNextBlock=listeBlocks.addSimpleBlock(theTime, 
                                                                block=nextBlock 
                                                                )
                        newNextBlock.change='insert_%s' % spr.location
                        #on ne vérifie pas si le next avait un prev, ça ne doit pas arriver
                        #on va cherche le fin du script droppé (si c'en est un)
                        finBlock=listeBlocks.lastFromBlock(theTime,newNode)
                        if finBlock.JMLid!=newNode.JMLid:
                            newFinBlock=listeBlocks.addSimpleBlock(theTime,block=finBlock)
                            newFinBlock.change='insert'
                            listeBlocks.setNextBlock(newFinBlock,newNextBlock)
                        else:
                            listeBlocks.setNextBlock(newNode,newNextBlock)
                        listeBlocks.addTick(theTime)   
                    elif spr.location=="slot":
                        #c'est un drop dans le CSLotMorph d'une boucle englobante
                        #parentId est le bloc englobant, targetId le CslotMorph                  
                        newNode.change='wrapped'
                        conteneurNode=listeBlocks.lastNode(spr.parentId,theTime).copy(theTime)
                        listeBlocks.append(conteneurNode)
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
                            newLastPrevBlock=lastPrevBlock.copy(theTime)
                            newLastPrevBlock.setNextBlock(None)
                            listeBlocks.append(newLastPrevBlock) 
                        else:
                            listeBlocks.setPrevBlock(newNode,None)
                        
                        lastContenu=listeBlocks.lastNode(conteneurNode.wrappedBlockId,theTime)
                        if lastContenu is not None:
                            #l'ancien contenu devient le nextblock
                            lastContenu=lastContenu.copy(theTime)
                            lastContenu.unwrap()
                            listeBlocks.append(lastContenu)
                            #on va chercher le fin du script droppé (si c'en est un)
                            finBlock=listeBlocks.lastFromBlock(theTime,newNode)
                            if finBlock.JMLid!=newNode.JMLid:
                                newFinBlock=listeBlocks.addSimpleBlock(theTime,block=finBlock)
                                newFinBlock.change='insert'
                                listeBlocks.setNextBlock(newFinBlock,lastContenu)
                            else:
                                listeBlocks.setNextBlock(newNode,lastContenu)
                        conteneurNode.setWrapped(newNode)
                        aff('                                                                MMM',newNode.JMLid,newNode.conteneurBlockId,newNode.prevBlockId,'cont',conteneurNode.wrappedBlockId)
                        listeBlocks.addTick(theTime)
                    elif spr.location is None:
                        #droppé tout seul                                                             
                        #on recupere le prevblock avant modif
                        lastPrevBlock=listeBlocks.lastNode(newNode.prevBlockId,theTime)
                        #on ne prend en compte ce changement que s'il ne s'agit pas d'un simple déplacement
                        if lastPrevBlock is not None:
                            newNode.change='(%s)inserted_%s' % (spr.type,spr.location)
                            newNode.setPrevBlock(None)
                            #listeBlocks.append(newNode)
                            newLastPrevBlock=lastPrevBlock.copy(theTime)
                            newLastPrevBlock.setNextBlock(None)
                            listeBlocks.append(newLastPrevBlock)  
                        if deleted:
                            newNode.deleted=True
                            newNode.action+=" DEL"   
                            #on place tous ses next à deleted
                            #while newNode.nextBlockId is not None:
                            #    newNode=listeBlocks.lastNode(newNode.nextBlockId,theTime).copy(theTime)
                            #    newNode.deleted=True
                            #    listeBlocks.append(newNode)
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
                    if history is None:
                        listeBlocks.recordDrop(spr, theTime)
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
                    if history is None:
                        #on crée le nouveau block (et ajout dans la liste)
                        newInputNode=createNew(spr,theTime,action)
                        newInputNode.change='added'
                        listeBlocks.recordDrop(spr, theTime)
                    else:
                        #c'est un redrop, on récupère la dernière version du noeud
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
            
            
        evtPrec=evtType
    #on parcours et on affiche les commandes
    commandes=[]
    
    for temps in listeBlocks.ticks:
        print('*********************')
        res=[]
        
        print('temps ',temps)
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
                    resultat['change']='XXchangeXX '+resultat['change']+"XX"+change
                res.append(resultat)
        #les résultats ne sont pas dans l'ordre!
        #le client devra retouver les blocs de débuts (prevBlock=None et parent=None)
        #puis reconstruire
        commandes.append({'temps':temps,'snap':res,
                          'epr':eprInfos['%s' % temps] if '%s' % temps in eprInfos else None,
                          'evt':evtTypeInfos['%s' % temps] if '%s' % temps in evtTypeInfos else None})
    print('-----------------------------------------------------------------------------------------')
    for i in listeBlocks.liste:
        print(i)
    print('-----------------------------------------------------------------------------------------')
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
        self.wrappedBlockId=None #id du premier bloc contenu
        self.contenu=None        # contenu du block(ie la valeur pour un InputSlotMorph)
        self.deleted=False      # indique si le noeud a été supprimé
        
        """
        type du changement: 
            changed pour une valeur changée
            added pour un bloc qui en remplace un autre
            deleted pour un bloc supprimé
            ...
        """        
        self.change=''
        
    
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
        self.change+=' init' if init else ' changed'
            

    def changeValue(self,value):
        self.contenu=value
        self.change+=" changed"
        
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
    
    def setWrapped(self,block):
        """
        met l'id du block comme bloc contenu
        met à jour le bloc conteneur
        !!!ne met pas à jour l'ancien contenu!!! 
        """
        if block is not None:
            self.wrappedBlockId='%s' % block.JMLid
            block.conteneurBlockId='%s' % self.JMLid
            block.prevBlockId=None
        else:
            self.wrappedBlockId=None
    def unwrap(self):
        """
        sort le block de son conteneur
        !!! ne met pas à jour le conteneur!!!
        """
        self.conteneurBlockId=None
    
    def setConteneur(self,block):
        """ 
        met le block comme conteneur de self
        !!! ne met pas à jour l'ancien conteneur!!!
        """
        if block is not None:
            self.conteneurBlockId='%s' % block.JMLid
            block.setWrapped(self)
        else:
            self.conteneurBlockId=None
            
    '''
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
    '''
    def copy(self,thetime,action=None):
        """ renvoie une copie complète en chabngeant time et action"""
        cp=copy.copy(self)
        cp.time=thetime
        cp.action=action
        cp.change=''
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
        
        aff('trateiemt,n',liste,self.JMLid)
        assert self.JMLid in liste
        blockOrig=self.copy(thetime,action)
        block=self.copy(thetime,action)
        block.JMLid=replace(block.JMLid)
        block.nextBlockId=replace(block.nextBlockId)
        block.prevBlockId=replace(block.prevBlockId)
        block.parentBlockId=replace(block.parentBlockId)
        block.lastModifBlockId=None
        block.conteneurBlockId=replace(block.conteneurBlockId)
        block.wrappedBlockId=replace(block.wrappedBlockId)
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
        change=(self.nextBlockId!=block.JMLid  if block is not None else block)
        if change: self.change+=' nextchange'
        if block is not None:
            self.nextBlockId='%s' % block.JMLid
            block.prevBlockId='%s' % self.JMLid
            if change: block.change+=' prevchange'
        else:
            self.nextBlockId=None            
        return block
    
    def setPrevBlock(self,block):
        """
        fixe le prevBlock ,
        et ajuste le nextblock de block
        """
        change=(self.prevBlockId!=block.JMLid if block is not None else block)
        if change: self.change+=' prevchange'
        if block is not None:
            self.prevBlockId='%s' % block.JMLid
            block.nextBlockId='%s' % self.JMLid
            if change: block.change+=' nextchange'
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
        self.dropped=[] #liste des drop pour undrop/redrop
        self.idropped=-1 #index de l'historique des drop pour undrop/redrop
        
    def initDrop(self):
        self.idropped=-1
        self.dropped=[]
        
    def addTick(self,time):
        if time not in self.ticks:
            self.ticks.append(time)
    
    def append(self,block):
        """ ajoute un block dans la liste """
        #on vérifie s'il a déjà été ajouté
        ancBlocks=[b for b in self.liste if b.JMLid==block.JMLid and b.time==block.time]
        if len(ancBlocks)>0:
            print("ouilleleou")
        #assert (len(ancBlocks)==0), "Block déjà existant %s à %s" % (block.JMLid,block.time)            
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
            aff('creation',block)
            #newb=SimpleBlockSnap(block=block,thetime=thetime)
            """newb=SimpleBlockSnap(block.JMLid,thetime,
                                              blockSpec=block.blockSpec,
                                              typeMorph=block.typeMorph,
                                              selector=block.selector,
                                              category=block.category,
                                              rang=block.rang,                                              
                                              action=block.action)"""
            newb=block.copy(thetime,action)
            aff('newb',newb)            
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

    def lastFromBlock(self,thetime,block):
        """
        pour un ensemble de blocks ayant block comme block de tête,
        cherche  le block de fin
        """
        p=0
        while block.nextBlockId is not None:
            print(".",block.nextBlockId,block.JMLid)
            assert (block.nextBlockId != block.JMLid), "erreur nextBlock %s " % block
            block=self.lastNode(block.nextBlockId,thetime)
            p+=1
            if p>10:
                print("ouille")
        print('---')
        return block
    
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
        else:
            source.setPrevBlock(None)
        
    def getNode(self,JMLid,thetime):
        """
        renvoie le noeud au temps thetime, None si non existant
        """
        JMLid="%s" %JMLid
        blocks=[b for b in self.liste if b.JMLid==JMLid and b.time==thetime]
        if len(blocks)>0:
            return blocks[0]
        return None
    
    def lastNode(self,JMLid,thetime,veryLast=False,deleted=False):
        """
        renvoie le dernier block (au sens du temps) de la liste
        max(temps)<=thetime si veryLast, sinon max(temps)<thetime
        si deleted, on renvoie même si le dernier est effacé
        """
        JMLid="%s" %JMLid
        if veryLast:
            blocks=[b for b in self.liste if b.JMLid==JMLid and b.time<=thetime]
        else:
            blocks=[b for b in self.liste if b.JMLid==JMLid and b.time<thetime]
        if len(blocks)>0:
            retour=sorted(blocks,key=lambda n: n.time,reverse=True)[0]
            if deleted:
                return retour
            return None if retour.deleted else retour
        return None
            
    def listeJMLid(self,thetime,veryLast=False):
        """
        Renvoie la liste des JMLid existant avant ou au temps thetime
        TODO: prise en compte des DELETE
        """
        liste=[]
        if veryLast:
            for i in [l for l in self.liste if l.time<=thetime]:
                if i.JMLid not in liste:
                    liste.append(i.JMLid)
        else:
            for i in [l for l in self.liste if l.time<thetime]:
                if i.JMLid not in liste:
                    liste.append(i.JMLid)
        return liste
    
    def lastNodes(self,thetime,veryLast=False,deleted=False):
        """
        renvoie les derniers blocks (au sens du temps) de la liste
        max(temps)<=thetime si veryLast, sinon max(temps)<thetime
        """
        listeJMLid=self.listeJMLid(thetime, veryLast)
        liste=[]
        for jmlid in listeJMLid:
            last=self.lastNode(jmlid, thetime, veryLast,deleted=True)
            #if last.action not in ['SPR_DEL','DELETE']:
            if deleted or not last.deleted:
                liste.append(last)            
        return liste
    
    def recordDrop(self,spr,thetime):
        """
        ajoute l'action spr dans ll'historique des drops
        on ajoute aussi un ENV: si DROPEX
        """
        self.idropped+=1
        try:
            self.dropped.insert(self.idropped,{'spr':spr.id,'type':spr.type,'time':thetime,
                                           'blockId':spr.blockId,
                                           'targetId':spr.targetId,
                                           'location':spr.location
                                           })
        except AttributeError:
            #c'est un autre type
            self.dropped.insert(self.idropped,{'spr':spr.id,'type':spr.type,'time':thetime})
        #print('                                           **********')
        #print('                                            insert',self.idropped,self.dropped[self.idropped],spr.blockId,spr.blockSpec)
        #print('                                           **********')
        #print('avbant:',[i for i in self.dropped]) 
        #on efface le reste de la liste
        for j in range(self.idropped+1,len(self.dropped)):            
            self.dropped.pop()
        #print([print(i) for i in self.dropped])   
    def undrop(self):
        """
        récupère l'id et le temps du dernier spr drop
        """
        droppedspr=self.dropped[self.idropped]
        self.idropped-=1
        #print('                                           **********')
        #print('                                            undrop',self.idropped,droppedspr)
        #print('                                           **********')
        #print([print(i) for i in self.dropped])
        return droppedspr
        
    def redrop(self):
        self.idropped+=1
        #print('                                           **********')
        #print('                                            redrop',self.idropped,self.dropped[self.idropped])
        #print('                                           **********')
        #print([i for i in self.dropped])
        return self.dropped[self.idropped]
    
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
            change=''                 
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
                if inputNode.change!= '' and inputNode.time==thetime:
                    change=inputNode.change
                    if 'init' in inputNode.change:
                        repl='*%s*' %repl
                    else:
                        #c'esrt un changement non traité
                        if toHtml:
                            repl='*<b>%s</b>*' % repl
                        else:
                            repl='*%s*' % repl
                
                if toHtml:
                    if inputNode and inputNode.time==thetime and inputNode.change!='':                    
                        #return '(%s)%s' %(inputNode.change,repl)
                        return '<span class="%s" title="id:%s, chg:%s">%s</span>' % (inputNode.change,inputNode.JMLid,inputNode.change,repl),change 
                    else:
                        return '<span title="id:%s">%s</span>' % (inputNode.JMLid,repl),change
                return repl,change
            
        #on récupère le block
        block=self.lastNode(JMLid, thetime, veryLast=True)
        if block is None:
            aff('pas de block')
            return [],''
        if block.typeMorph=='MultiArgMorph':
            #un multiarg n'est qu'une suite de %s
            block.blockSpec='|%s|'*len(block.inputs)
        nom=block.blockSpec    
        aff('block ',nom)
        aff('inputs ',block.inputs)
        #on cherche à remplacer les "%trucs" par les inputs 
        #if block.action=='SPR_DEL' and block.time<thetime:
        if block.deleted and block.time<thetime:               
                nom=''
                resultat={
                    'JMLid':block.JMLid,
                    'time':thetime,
                    #'commande':nom,
                    'change':"",
                    'deleted':block.deleted,
                    #'action':'DELETED'
                }
                #return resultat,nom,'nochange deleted'
                return resultat,nom,''
        
        if block.typeMorph!='CommentMorph':
            txt=re.findall(r'(%\w+)',u'%s' % block.blockSpec)
            repl={}
            resultat=[]
            change=''
            i=0 #rang du %truc traité
            for e in txt:
                if e in trad.keys():
                    # c'est un mot clef
                    nom=nom.replace(e,'%s' %trad[e],1)
                elif e[1:]!="words":
                    #cas général, sauf multiarg
                    repl,changed=traiteElement(block,e,i,resultat)
                    change=changed if changed else change
                    nom=nom.replace(e,'%s' %repl,1)
                    i+=1                    
                else:
                    #linput[0] est un multiarg, on parcours les inputs de ce multiarg
                    words=""
                    multiArgNode=self.lastNode(block.inputs['%s'%i],thetime,veryLast=True)
                    res,repl,changed=self.parcoursBlock(multiArgNode.JMLid,thetime,toHtml)
                    change=changed if changed else change
                    words+="["+repl+"]"
                    nom=nom.replace(e,'%s' % words,1)
                    i+=1
        else:
            #c'est un CommentMorph
            change=block.change if block.time==thetime else 'r' #change
        resultat={'JMLid':block.JMLid,
                  'time':thetime,
                  'commande':nom,
                  'typeMorph':block.typeMorph,
                  'action':block.action if block.time==thetime else '',
                  'change': change,#block.change,
                  'deleted':block.deleted,
                  'nextBlock':block.nextBlockId,
                  'prevBlock':block.prevBlockId,
                  'conteneurBlock':block.conteneurBlockId,
                  'wrappedBlock':block.wrappedBlockId}
        #print('nom',nom,' résultat de niom',resultat)
        return resultat,nom,change
    
    def addFromXML(self,item,withScript=False,theTime=0):
        """
        rajoute (avec récursion) les blocks issus d'un fichier XML
        les place au temps theTime (0 par défaut)
        Si withScript, on ajoute un block Script par script 
        """
        aff('item',item.tag,item.items())
        if item.tag=='block' or item.tag=='custom-block':
            block=SimpleBlockSnap(item.get('JMLid'),theTime,item.get('typemorph'))
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
            params=re.findall(r'(%\w+)',u'%s' % block.blockSpec)
            rang=0
            for e in params:
                if e in ['%inputs','%words','%exp','%scriptvars','%parms']:
                    #on a ttend un multiArgMorph
                    inp=self.addFromXML(item.getchildren()[rang],theTime=theTime)
                    inp.rang=rang
                    block.addInput(inp);                
                    rang+=1
                elif e in ['%c','%cs','%cl']:
                    #on attend un Cslotmorph(commandes)
                    inp=self.addFromXML(item.getchildren()[rang],theTime=theTime)
                    inp.rang=rang
                    block.addInput(inp);                
                    rang+=1                
                elif e not in ['%clockwise','%counterclockwise','%greenflag']:
                    #un seul input
                    inp=self.addFromXML(item.getchildren()[rang],theTime=theTime)
                    inp.rang=rang
                    block.addInput(inp);                
                    rang+=1
            #traitement des commentaires liés            
            for c in item.findall('comment'):
                commentBlock=SimpleBlockSnap(c.get('JMLid'),theTime,c.get('typemorph'))
                commentBlock.contenu=c.text
                commentBlock.blockSpec=c.text
                self.append(commentBlock)
                #TODO: peaufiner? ajouter un lien                
            self.append(block)
            return block   
        elif item.tag=='list':
            block=SimpleBlockSnap(item.get('JMLid'),theTime,item.get('typemorph'))
            # récupération des inputs
            for rang,inp in enumerate(item.getchildren()):
                block_in=self.addFromXML(inp,theTime=theTime)
                block_in.rang=rang
                block.addInput(block_in)
            self.append(block)
            return block
        elif item.tag=='l':
            block=SimpleBlockSnap(item.get('JMLid'),theTime,item.get('typemorph'))
            if len(item.getchildren())>0:
                #si c'est une 'option'
                block.contenu=item.getchildren()[0].text
            else:
                block.contenu=item.text
            self.append(block)
            return block
        elif item.tag=='color':
            block=SimpleBlockSnap(item.get('JMLid'),theTime,item.get('typemorph'))
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
                block=SimpleBlockSnap(jmlid,theTime,item.get('typemorph','NoScriptsMorph'))
                block.blockSpec="Script_%s" % item.getparent().index(item)
                self.append(block)
                if withScript:
                    self.setFirstBlock(block)
            else:
                block=SimpleBlockSnap(jmlid,theTime,item.get('typemorph'))
                self.append(block)
            #on ajoute les blocks comme étant contenus
            prevblock=None
            rang=0
            #for b in item.findall('block'):
            for b in item.getchildren():
                if b.tag=='block' or b.tag=='custom-block':
                    child=self.addFromXML(b,theTime=theTime)
                    if prevblock is not None:
                        self.setNextBlock(prevblock,child)
                    else:
                        block.setWrapped(child)
                        #block.addWrapped(block=child,rang=rang)                                    
                    prevblock=child                
                    rang+=1
                #block.addWrappedBlock(child)
                #TODO: liste.addWrappedBlock(block,child)
            return block
        elif item.tag=='comment':
            block=SimpleBlockSnap(item.get('JMLid'),theTime,item.get('typemorph'))
            block.contenu=item.text
            block.blockSpec=item.text
            self.append(block)
            return block