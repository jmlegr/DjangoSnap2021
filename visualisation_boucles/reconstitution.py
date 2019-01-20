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
from visualisation_boucles import tasks


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
def reconstitution(request,session_key=None):
    if session_key is not None:
        g=tasks.reconstruit(session_key,noTask=True)
    else:
        g="pasbon"
    return Response({"data":g})
                            
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
    
    def getNom(self):
        if self.typeMorph in ['InputSlotMorph','ColorSlotMorph','BooleanSlotMorph']:
            nom= "%s" % self.contenu if self.contenu is not None else None
        elif self.typeMorph in['ReporterBlockMorph',]:
            nom= "<%s>" %self.blockSpec
        else:
            nom= "%s" % self.blockSpec        
        #return '(%s_%s)%s' %(self.JMLid,self.time,nom)
        return '%s' %(nom)
    
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
    
    def removeWrapped(self):
        """
        supprime le contenu (pas de maj)
        """
        self.wrappedBlockId=None
        
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
                                               'detail':spr.detail,
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
        pass
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
            #aff('params',params)
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
                    block.setWrapped(self.getNode(inp.wrappedBlockId,theTime))
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