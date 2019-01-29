'''
Created on 16 déc. 2018

@author: duff
'''
from celery import shared_task,current_task
from snap.models import Evenement, EvenementEPR, ProgrammeBase, Document,\
    EvenementSPR
from visualisation_boucles.models import Reconstitution
from visualisation_boucles.reconstitution import SimpleListeBlockSnap
from lxml import etree
from snap import serializers
from visualisation_boucles.serializers import SimpleSPRSerializer,\
    SimpleEvenementSerializer,InfoProgSerializer
from rest_framework.renderers import JSONRenderer


affprint=False
def aff(*str):
    if affprint:
        print(*str)

@shared_task
def reconstruit(session_key):    
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
    
    current_task.update_state(state='Initialisation',
                                meta={'evt_traites': 0,'nb_evts':None})
    #liste les derniers débuts de tous les élèves
    programme=None
    evts=[]
    if session_key.isdigit():
        #on a envoyé une id d'évènement EPR
        epr=EvenementEPR.objects.get(id=session_key)
        debut=epr.evenement
        evts=Evenement.objects.filter(session_key=debut.session_key,creation__gte=debut.creation,time__gte=debut.time).order_by('time')
    else:
        evts=Evenement.objects.filter(session_key=session_key).order_by('time')
        debut=evts[0]
    nb_evts=evts.count()
    current_task.update_state(state='Initialisation',
                                meta={'evt_traites': 0,'nb_evts':nb_evts,'percent_task':0})
    infos={'type':''}
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
    evt_traites=0
    for evt in evts:
        evt_traites+=1
        if (evt_traites % 10 == 0):
            current_task.update_state(state='Traitement',
                                meta={'evt_traites': evt_traites,'nb_evts':nb_evts,
                                      'percent_task':round(evt_traites/nb_evts*50)
                                })
        #print('evt',evt,evt.type,evt.id)
        if dtime is None:
            dtime=evt.time
            theTime=0
        theTime=evt.time-dtime        
        
        evtType=evt.getEvenementType()
        evtTypeInfos['%s' % theTime]={'evenement':evt.id,
                                      'evenement_type':evt.type,
                                      'type':evtType.type,
                                      'detail':evtType.detail}
        history=None #memorise l'état undrop/redrop
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
            if len(listeBlocks.liste)>0: listeBlocks.addTick(theTime-1)
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
                p=ProgrammeBase.objects.get(id=evtType.valueInt) #detail contient le nom
                f=p.file
                infos['type']=" - ".join((infos['type'],'Programme de base: %s' %p.nom))
                infos['tooltip']=p.description
            else:
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
                    listeBlocks.setFirstBlock(newBlock)
                    #if newBlock.parentBlockId is None:
                    #    listeBlocks.setFirstBlock(newBlock)
                #listeBlocks.recordDrop(env,theTime)   
                #listeBlocks.addTick(theTime)
            if env.type=='DROPEX':
                if evtPrec.type=='DUPLIC':
                    #il faut tratier la suppression; pas besoin de vérfier, DUPLIC ne peut pas être tout seul
                    newBlock=listeBlocks.lastNode(env.valueInt, theTime)
                    newBlock.deleted=True
                elif evtPrec.type=='UNDROP' and evtPrec.blockId==env.valueInt:
                    #c'est un undrop+dropex, (donc annulation d'un duplic)
                    newBlock=listeBlocks.lastNode(env.valueInt, theTime)
                    newBlock.deleted=True
                else:
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
                    newNode.change="undrop new"
                    listeBlocks.append(newNode)
                    if newNode.conteneurBlockId is not None:
                        lastConteneur=listeBlocks.lastNode(newNode.conteneurBlockId,theTime).copy(theTime)
                        lastConteneur.setWrapped(None)
                        newNode.unwrap()
                        listeBlocks.append(lastConteneur)
                    else:
                        lastConteneur=None
                    if newNode.prevBlockId is not None:
                        newPrevBlock=listeBlocks.lastNode(newNode.prevBlockId,theTime).copy(theTime)
                        newPrevBlock.change="uninsert"                        
                        newPrevBlock.setNextBlock(None)
                        listeBlocks.append(newPrevBlock)
                    else:
                        newPrevBlock=None                        
                    if newNode.nextBlockId is not None:
                        newNextBlock=listeBlocks.lastNode(newNode.nextBlockId,theTime).copy(theTime)
                        newNextBlock.change="uninsert"
                        newNextBlock.setPrevBlock(newPrevBlock)
                        newNextBlock.setConteneur(lastConteneur)
                        listeBlocks.append(newNextBlock)
                    else:
                        newNextBlock=None
                    if newNode.wrappedBlockId is not None:
                        #c'est un bloc contenant (donc ajouté avec wrap)
                        newNextBlock=listeBlocks.lastNode(newNode.wrappedBlockId,theTime).copy(theTime)
                        if newPrevBlock is not None:
                            newPrevBlock.setNextBlock(newNextBlock)
                        newNextBlock.unwrap()
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
                        
                        if finScript.JMLid!=newNode.JMLid:
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
                    elif dspr.location=='wrap':
                        #on remet le block conteneur a sa place (et donc maj de son prevBlock
                        ancienNode=listeBlocks.lastNode(newNode.JMLid,s['time'])
                        if newNode.wrappedBlockId is not None:
                            ancienContenu=listeBlocks.lastNode(newNode.wrappedBlockId,s['time']).copy(theTime)
                            contenu=listeBlocks.lastNode(newNode.wrappedBlockId,theTime).copy(theTime)
                            contenu.unwrap()
                            listeBlocks.append(contenu)
                            newNode.setWrapped(None)
                        else:
                            ancienContenu=None
                        if ancienNode.prevBlockId is not None:
                            newPrevBlock=listeBlocks.lastNode(ancienNode.prevBlockId,theTime).copy(theTime)
                            newPrevBlock.setNextBlock(newNode)
                            listeBlocks.append(newPrevBlock)
                        else:
                            newPrevBlock=None
                        #on replace l'ancien prevBlock du bloc contenu
                        if ancienContenu is not None and ancienContenu.prevBlockId is not None:
                            newPrevBlock=listeBlocks.lastNode(ancienContenu.prevBlockId,theTime).copy(theTime)
                            newPrevBlock.setNextBlock(contenu)
                            listeBlocks.append(newPrevBlock)
                            
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
                            nextNode.conteneurBlockId=None
                            listeBlocks.setNextBlock(newNode,nextNode)
                            newNode=nextNode                   
                            if deleted: break
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
                elif spr.location=='wrap':
                    #c'est un conteneur qui vient englober les blocks à partir de targetId 
                    #(et qui aura comme prevBlock parentId)
                    target=listeBlocks.lastNode(spr.targetId,theTime).copy(theTime)
                    #on recherche le parent
                    if target.prevBlockId is not None:
                        newPrevBlock=listeBlocks.lastNode(target.prevBlockId,theTime).copy(theTime)
                        newPrevBlock.setNextBlock(newNode)
                        listeBlocks.append(newPrevBlock)
                    #on se passe du cslot
                    #cslot=listeBlocks.lastNode(newNode.inputs['0'],theTime,veryLast=True)
                    #on met à jour la cible                    
                    target.setPrevBlock(None)
                    target.setConteneur(newNode)
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
                    listeBlocks.recordDrop(spr, theTime)
                else:  
                    if evtPrec.type=='DUPLIC':
                        #c'est suite à une duplication, on le précise
                        action+=' DUPLIC'
                        #spr.type=spr.type+'_DUPLIC'
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
                    newNode=listeBlocks.lastNode(spr.blockId, theTime,deleted=True).copy(theTime,action)
                    newNode.deleted=False
                    #newNode.change="dropped"
                    #si ni le prevBlock ni le nextblock (ni wrapp?) ne change, c'est un simplement déplacement non pris en compte
                    #pour l'instant on le fait quand même                
                    listeBlocks.append(newNode)
                    #on vérifie si le block déplacé n'était pas contenu
                    if newNode.conteneurBlockId is not None:
                        lastConteneur=listeBlocks.lastNode(newNode.conteneurBlockId,theTime).copy(theTime)
                        lastConteneur.change="etaitcontenu"
                        lastConteneur.setWrapped(None)
                        newNode.unwrap()
                        listeBlocks.append(lastConteneur)
                    else:
                        lastConteneur=None
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
                                #print(lastFromNode.JMLid,newNode.JMLid,(lastFromNode.JMLid!=newNode.JMLid),('%s' % lastFromNode.JMLid!='%s' % newNode.JMLid))
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
                        listeBlocks.setFirstBlock(newNode)
                        newNode.change='(%s)inserted_%s' % (spr.type,spr.location)
                        #on récupère la cible
                        newNextBlock=listeBlocks.lastNode(spr.targetId,theTime).copy(theTime)                        
                        newNextBlock.change='insert_%s' % spr.location
                        listeBlocks.append(newNextBlock)
                        #on ne vérifie pas si le next avait un prev, ça ne doit pas arriver
                        #on va cherche le fin du script droppé (si c'en est un)
                        finBlock=listeBlocks.lastFromBlock(theTime,newNode)
                        if finBlock.JMLid!=newNode.JMLid:
                            newFinBlock=listeBlocks.addSimpleBlock(theTime,block=finBlock)
                            newFinBlock.change='insert'
                            listeBlocks.setNextBlock(newFinBlock,newNextBlock)
                        else:
                            listeBlocks.setNextBlock(newNode,newNextBlock)
                        #on change le prevBlock                        
                        lastPrevBlock=listeBlocks.lastNode(newNode.prevBlockId,theTime)
                        if lastPrevBlock is not None:
                            if lastPrevBlock.JMLid!=newNextBlock.JMLid:                            
                                newLastPrevBlock=lastPrevBlock.copy(theTime)
                                newLastPrevBlock.setNextBlock(None)
                                listeBlocks.append(newLastPrevBlock)
                            else:
                                newNextBlock.setNextBlock(None)
                        newNode.setPrevBlock(None)
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
                            if lastPrevBlock.JMLid!=conteneurNode.JMLid:
                                newLastPrevBlock=lastPrevBlock.copy(theTime)
                                newLastPrevBlock.setNextBlock(None)
                                listeBlocks.append(newLastPrevBlock)
                            else:
                                #le conteneur est l'ancien prev 
                                conteneurNode.setNextBlock(None)
                        else:
                            listeBlocks.setPrevBlock(newNode,None)
                        
                        lastContenu=listeBlocks.lastNode(conteneurNode.wrappedBlockId,theTime)
                        if lastContenu is not None:
                            aff('lastcontenu',lastContenu)
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
                            listeBlocks.append(newLastPrevBlock) 
                        else:
                            listeBlocks.setPrevBlock(newNode,None)
                        target=listeBlocks.lastNode(spr.targetId,theTime).copy(theTime)
                        #on recherche le parent
                        if target.prevBlockId is not None:
                            newPrevBlock=listeBlocks.lastNode(target.prevBlockId,theTime).copy(theTime)
                            newPrevBlock.setNextBlock(newNode)
                            listeBlocks.append(newPrevBlock)
                        #on se passe du cslot
                        #cslot=listeBlocks.lastNode(newNode.inputs['0'],theTime,veryLast=True)
                        #on met à jour la cible                    
                        target.setPrevBlock(None)
                        target.setConteneur(newNode)
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
                            newNode.setPrevBlock(None)
                            #listeBlocks.append(newNode)
                            newLastPrevBlock=lastPrevBlock.copy(theTime)
                            newLastPrevBlock.setNextBlock(None)
                            listeBlocks.append(newLastPrevBlock)  
                            if spr.detail=="DropDel":
                                #si c'est un drop précédent un del (dropdel), seul le bloc est déplacé, 
                                #il faut mettre à jour prevblock et nextblock
                                nextBlock=listeBlocks.lastNode(newNode.nextBlockId,theTime)
                                if nextBlock is not None:
                                    newNextBlock=nextBlock.copy(theTime)
                                    listeBlocks.append(newNextBlock)
                                    newLastPrevBlock.setNextBlock(newNextBlock)
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
                                        listeBlocks.append(newNextBlock)
                                        lastConteneur.setWrapped(newNextBlock)                                        
                            elif spr.detail=="DropDel":
                                #on met à jour l'éventuel nextblock en cas de dropdel
                                nextBlock=listeBlocks.lastNode(newNode.nextBlockId,theTime)
                                if nextBlock is not None:
                                    newNextBlock=nextBlock.copy(theTime)
                                    newNextBlock.setPrevBlock(None)
                                    listeBlocks.append(newNextBlock)
                                    
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
                action+=' VAL'
                if spr.location is None:
                    #c'est un CommentBlock (sans input). La valuer est blockSpec
                    #si le commentaire est trop long (blockSpec limité à 50 car), le complément est dans detail
                    detail=spr.detail.split('(longBlockSpec)')
                    inputNode=listeBlocks.lastNode(detail[0],theTime).copy(theTime,action)
                    inputNode.changeValue(spr.blockSpec)
                    inputNode.blockSpec=detail[1] if (len(detail)>1) else spr.blockSpec
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
    nb_ticks=len(listeBlocks.ticks)
    ticks_traites=0
    for temps in listeBlocks.ticks:
        ticks_traites+=1
        #print('*********************')
        res=[]
        
        #print('temps ',temps)
        if ticks_traites%10==0:
            current_task.update_state(state='Reconstruction',
                                meta={'evt_traites': ticks_traites,'nb_evts':nb_ticks,
                                      'percent_task':round(ticks_traites/nb_ticks*50+50)
                                })
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
                          'evt':evtTypeInfos['%s' % temps] if '%s' % temps in evtTypeInfos else None})
    #print('-----------------------------------------------------------------------------------------')
    #for i in listeBlocks.liste:
    #    print(i)
    #print('-----------------------------------------------------------------------------------------')
    #sauvegarde dans la base (avec écrasement)
    current_task.update_state(state='Sauvegarde')
    prog,created=Reconstitution.objects.get_or_create(
        session_key=session_key,
        user=user)
    prog.programme=infos['type'],
    prog.detail_json={"commandes":commandes,
                     "scripts":listeBlocks.firstBlocks,
                     #"data":listeBlocks.toJson(),
                     "ticks":listeBlocks.ticks,
                     #'links':listeBlocks.links,
                     'etapes':{},#etapes,
                     #'actions':[a.toD3() for a in actions]
                      "infos":InfoProgSerializer(infos).data,                     
                      "session":session_key,
                      #'infos':evtTypeInfos
                      }
    prog.save()
    current_task.update_state(state='Envoi')
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
                      "created":created,
                      }
    
@shared_task
def add(x,y,n):
    for i in range(n):
        if(i%30 == 0):
            process_percent = int(100 * float(i) / float(n))
            current_task.update_state(state='PROGRESS',
                                meta={'percent_task': process_percent,
                                      'evt_traites':i,
                                      'nb_evts':n})
        a = x+y
    return {'x':x,'y':y,'resultat':x+y}

@shared_task
def celery_graph_boucles(sessions,only=None):
    '''
    Recherche la premiere occurence d'une boucle ('doUntil','doForever','doRepeat')    
    et renvoi l'enselbe des évènements la précédent
    data:liste des session_key
    only: si présent, tableau de recherche (défaut:['doUntil','doForever','doRepeat']
    '''
    if only is not None:
        tabBoucles=only
    else:
        tabBoucles=['doUntil','doForever','doRepeat']

    evtsBoucle={}
    nb_evts=len(sessions)
    evt_traites=0
    percent_task=0
    for session_key in sessions:
        evt_traites+=1
        current_task.update_state(state='En cours',
                                meta={'evt_traites': evt_traites,'nb_evts':nb_evts,
                                      'percent_task':round(evt_traites/nb_evts*100)
                                })
        
        #on recherche une création de boucle
        evt=EvenementSPR.objects.filter(evenement__session_key=session_key,type='NEW',selector__in=tabBoucles)\
                .select_related('evenement')\
                .order_by('evenement__time').first()
        if evt is not None:
            serializerSPR=SimpleSPRSerializer(evt,many=False)
            evts=Evenement.objects.filter(session_key=session_key,time__lte=evt.evenement.time)\
                    .prefetch_related('evenementspr','evenementepr','environnement','image','evenementspr__inputs','evenementspr__scripts')                    
            serializer=SimpleEvenementSerializer(evts,many=True)
            evtsBoucle[session_key]={'boucle':serializerSPR.data,'evts':serializer.data}
        else:            
            evts=Evenement.objects.filter(session_key=session_key)\
                    .prefetch_related('evenementspr','evenementepr','environnement','image','evenementspr__inputs','evenementspr__scripts')                    
            serializer=SimpleEvenementSerializer(evts,many=True)
            evtsBoucle[session_key]={'boucle':None,'evts':serializer.data}
    return evtsBoucle
