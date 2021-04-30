'''
Created on 16 déc. 2018

@author: duff
'''
from celery import shared_task,current_task
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

@shared_task
def reconstruit(session_key,save=False,load=False,nosend=False):
    """
    Reconstruit l'histoire du programme
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
        current_task.update_state(state='Chargement')
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

    current_task.update_state(state='Initialisation',
                                meta={'evt_traites': 0,'nb_evts':None})
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
                                      'detail':evtType.detail,
                                      'realtime':evt.time}
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
            listeBlocks.initDrop()
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
                elif evtPrec.type=='UNDROP' and evtPrec.blockId==env.valueInt:
                    #c'est un undrop+dropex, (donc annulation d'un duplic)
                    newBlock=listeBlocks.lastNode(env.valueInt, theTime)
                    newBlock.truc="me deleted undrop"
                    newBlock.deleted=True
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
            #traitement des undrops/redrop
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
                            if node.JMLid != newNode.JMLid:
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
                    ancienInput=listeBlocks.lastNode(dspr.blockId,s['time'],veryLast=deleted)
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
                          'spr':sprInfos['%s' % temps] if '%s' % temps in sprInfos else None,
                          'evt':evtTypeInfos['%s' % temps] if '%s' % temps in evtTypeInfos else None})
    #print('-----------------------------------------------------------------------------------------')
    #for i in listeBlocks.liste:
    #    print(i)
    #print('-----------------------------------------------------------------------------------------')
    #sauvegarde dans la base (avec écrasement)
    if save:
        #sauvegarde la reconstruction dans une base mongodb
        current_task.update_state(state='Sauvegarde')
        db=MongoClient().sierpinski_db
        collection=db.reconstructions
        p=collection.delete_many({'session_key':session_key})
        p=collection.insert_one({'user':user.username,'session_key':session_key,
                                 'date':datetime.utcnow(),
                                 "infos":InfoProgSerializer(infos).data,
                                 "scripts":listeBlocks.firstBlocks,
                                 "ticks":listeBlocks.ticks,
                                 })
        for c in commandes:
            #on enlève les éventuelles commandes vides (par exemple un DROP+DEL ne fera qu'un evenement)
            if c is None or c['evt'] is None:
                commandes.remove(c)
                
        commandes.sort(key=lambda c: c['evt']['realtime'] )
        cmds=collection.insert_many([{'session_key':session_key,
                                      'etape':i,
                                      'commandes':c} for i,c in enumerate(commandes)])

        print("sauvegarde %s: %s morceaux" %(p,len(cmds.inserted_ids)))
        created=True
    else:
        created=False
    current_task.update_state(state='Envoi')
    if nosend:
        return {"infos":infos,
                "session":session_key,
                "created":created,
            }
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

    #connection à la base mongodb
    db=MongoClient().sierpinski_db
    collection=db.reconstructions

    evtsBoucle=[]
    nb_evts=len(sessions)
    evt_traites=0
    percent_task=0
    for session_key in sessions:
        evtBoucle={}
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
            timeboucle=evt.evenement.time
            serializerSPR=SimpleSPRSerializer(evt,many=False)
            evts=Evenement.objects.filter(session_key=session_key,time__lte=evt.evenement.time)\
                    .prefetch_related('evenementspr','evenementepr','environnement','image','evenementspr__inputs','evenementspr__scripts')
            serializer=SimpleEvenementSerializer(evts,many=True)
            evtBoucle={'boucle':serializerSPR.data,'evts':serializer.data}
        else:
            evts=Evenement.objects.filter(session_key=session_key)\
                    .prefetch_related('evenementspr','evenementepr','environnement','image','evenementspr__inputs','evenementspr__scripts')
            timeboucle=evts.latest('time').time
            serializer=SimpleEvenementSerializer(evts,many=True)
            evtBoucle={'boucle':None,'evts':serializer.data}
        #on regarde si on a une sauvegarde de la reconstruction
        print("commandes")
        p=collection.find_one({"session_key":session_key,"commandes":{"$exists":False}})
        if p is not None:
            print("commandes tourv pour ",session_key,timeboucle)
            c=collection.find_one({"session_key":session_key,"etape":{"$lte":timeboucle}},sort=[('etape',pymongo.DESCENDING)])
            evtBoucle["commandes"]=[s for s in c['commandes']['snap']
                                                  if 'commande' in s and s['commande'] is not None and not s['deleted']]
        evtBoucle["session"]=session_key
        evtsBoucle.append(evtBoucle)
    return evtsBoucle

@shared_task
def celery_liste_reperes(sessions):
    current_task.update_state(state='Récupération repères',
                              meta={'evt_traites': 1,'nb_evts':5,
                                      'percent_task':1
                                })
    reperes=EvenementEPR.objects.filter(evenement__session_key__in=sessions,
                                            type__in=["LOAD","SAVE","NEW"])\
                                            .order_by('evenement__user','evenement__time')\
                                            .select_related('evenement',
                                                            'evenement__user',
                                                            'evenement__user__eleve',
                                                            'evenement__user__eleve__classe')

    evt_traites=0
    nb_evts=len(reperes)
    for e in reperes:
        evt_traites+=1
        current_task.update_state(state='Récupération snapshots',
                                meta={'evt_traites': evt_traites,'nb_evts':nb_evts,
                                      'percent_task':round(25*(1+evt_traites/nb_evts))
                                })

        #recherche du dernier snap
        try:

            snaps=SnapSnapShot.objects.filter(evenement__user=e.evenement.user,
                                              evenement__session_key=e.evenement.session_key,
                                              evenement__time__lt=e.evenement.time,
                                              evenement__type=Evenement.ETAT_PROGRAMME
                                              ).select_related('evenement').prefetch_related('evenement__evenementepr').order_by('-evenement__time')
            #on ne prend que les snaps de fin ou stop
            snaps=[s for s in snaps if s.evenement.getEvenementType().type=='SNP'
                                    and s.evenement.getEvenementType().detail[:3] in ["STO","FIN"]]
            #print ([s.evenement.getEvenementType() for s in snaps])
            e.snapshot=snaps[0]
            #print("snap",snaps[0])

        except IndexError:
            snap=None
            #print("pasnsap")
    current_task.update_state(state='Récupération lancements',
                                meta={'evt_traites': 3,'nb_evts':5,
                                      'percent_task':50
                                })
    lances=EvenementENV.objects.filter(evenement__session_key__in=sessions
                                            ,type__in=["LANCE","IMPORT","EXPORT"])\
                                            .order_by('evenement__user','evenement__time')\
                                            .select_related('evenement',
                                                            'evenement__user',
                                                            'evenement__user__eleve',
                                                            'evenement__user__eleve__classe')
    lasts=[]
    current_task.update_state(state='Récupération last',
                                meta={'evt_traites': 4,'nb_evts':5,
                                      'percent_task':75
                                })
    for session in sessions:
        last=Evenement.objects.filter(session_key=session)\
                                            .select_related('user',
                                                            'user__eleve',
                                                            'user__eleve__classe')\
                                            .latest('time')\
                                            .getEvenementType()
        if last not in reperes:
            lasts.append(last)
        #print("LAST",lasts)
    for e in lasts:
        #recherche du dernier snap
        try:
            snaps=SnapSnapShot.objects.filter(evenement__user=e.evenement.user,
                                              evenement__session_key=e.evenement.session_key,
                                              evenement__time__lte=e.evenement.time
                                              ).order_by('-evenement__time')
            e.snapshot=snaps[0]
            #print("snap",snaps[0])

        except IndexError:
            snap=None
                #print("pasnsap")
    current_task.update_state(state='Envoi',
                                meta={'evt_traites': 5,'nb_evts':5,
                                      'percent_task':100
                                })
    queryset=itertools.chain(lances,reperes,lasts)
    serializer=ReperesEPRSerializer(queryset,many=True)
    data=sorted(serializer.data,key= lambda x:x['evenement']['time'])
    return data