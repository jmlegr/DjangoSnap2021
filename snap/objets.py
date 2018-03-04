'''
Objets pour la recréation des actions des élèves avec snap
Created on 25 févr. 2018

@author: duff
'''
from snap import models
import json
import copy
import re

def aff(r,message='JSON'):
    print(message)
    print(json.dumps(r,sort_keys=True,indent=3,))

class ListeBlockSnap:
    """
    liste des blockSnap au fil du temps
    sous la forme {JMLid: [{block tempsx},{block temps y}....]}
    """
    def __init__(self):
        self.liste={}
        self.ticks=[0,] #liste des temps d'action
        self.firstBlocks=[] #premiers blocks des scripts
        self.links=[] #liens nextblocks, forme {source:id,target:id,type:string}
        
    def addTick(self,time):
        if time not in self.ticks:
            self.ticks.append(time)
    def addFirstBlock(self,block):
        """
        ajoute la block dans liste des blocs de tête des scripts
        (et aussi dans la liste des blocks s'il n'y est pas déjà)
        """
        if block.JMLid not in self.firstBlocks:
            self.firstBlocks.append(block.JMLid)
        self.addBlock(block)
              
    def addBlock(self,block):
        """
        ajoute un blockSnap à la liste, s'il n'y est pas déjà
        """
        if block.JMLid not in self.liste:
            self.liste[block.JMLid]=[]
        if block not in self.liste[block.JMLid]:
            self.liste[block.JMLid].append(block)
    def addLink(self,sourceId,targetId,typeLien='changed'):
        self.links.append({'source':sourceId,
                           'target':targetId,
                           'type':typeLien})
          
    def lastBlock(self,block,time,veryLast=False,exact=False):
        """
        retourne le dernier block (avant time) 
        block est soit un objet BlockSnap ou Block ou BlockInput, 
        soit un JMLid
        si veryLast est vrai on cherche jusqu'à time compris, sinon avant
        """
        return ListeBlockSnap.lastBlockFromListe(self.liste, block, time, veryLast,exact)
        """if type(block)=='dict':
            JMLid=block.JMLid
        else:
            #on a passé l'id
            JMLid=block
        if JMLid in self.liste:
            bs=[n for n in self.liste[JMLid] 
                    if (n.time<=time if veryLast else n.time<time)]
            if bs:
                return sorted(bs,key=lambda n: n.time,reverse=True)[0]
        return None
        """
    @classmethod
    def lastBlockFromListe(cls,liste,block,time,veryLast=False, exact=False):
        #print('liste',[i for i in liste])        
        if type(block)==dict or type(block)==BlockSnap:
            JMLid=block.JMLid        
        else:
            #on a passé l'id            
            JMLid=int(block)
        if JMLid in liste:
            bs=[n for n in liste[JMLid] 
                    if (n.time==time if exact 
                        else n.time<=time if veryLast
                        else n.time<time)]
            if bs:
                return sorted(bs,key=lambda n: n.time,reverse=True)[0]
        
        return None
        
    def lastListe(self,time,veryLast=False):
        """
        renvoie les derniers (au sens de time) éléments de liste
        jusqu'à time si veryLast=True
        """
        liste=[]
        for jmlid in self.liste:
            liste.append(self.lastBlock(jmlid, time, veryLast))
        return liste
    
    def findBlock(self,block,liste):
        """
        renvoie le block de la liste (ie de même JMLid)
        """
        try:
            e=next(n for n in liste if n is not None and n.JMLid==block.JMLid)
        except:
            return None
        return e
        
                
    def snapAt(self,time):
        liste=None
        def afficheCommand(block):            
            """
        %br     - user-forced line break
    %s      - white rectangular type-in slot ("string-type")
    %txt    - white rectangular type-in slot ("text-type")
    %mlt    - white rectangular type-in slot ("multi-line-text-type")
    %code   - white rectangular type-in slot, monospaced font
    %n      - white roundish type-in slot ("numerical")
    %dir    - white roundish type-in slot with drop-down for directions
    %inst   - white roundish type-in slot with drop-down for instruments
    %ida    - white roundish type-in slot with drop-down for list indices
    %idx    - white roundish type-in slot for indices incl. "any"
    %obj    - specially drawn slot for object reporters
    %spr    - chameleon colored rectangular drop-down for object-names
    %col    - chameleon colored rectangular drop-down for collidables
    %dst    - chameleon colored rectangular drop-down for distances
    %cst    - chameleon colored rectangular drop-down for costume-names
    %eff    - chameleon colored rectangular drop-down for graphic effects
    %snd    - chameleon colored rectangular drop-down for sound names
    %key    - chameleon colored rectangular drop-down for keyboard keys
    %msg    - chameleon colored rectangular drop-down for messages
    %att    - chameleon colored rectangular drop-down for attributes
    %fun    - chameleon colored rectangular drop-down for math functions
    %typ    - chameleon colored rectangular drop-down for data types
    %var    - chameleon colored rectangular drop-down for variable names
    %shd    - Chameleon colored rectuangular drop-down for shadowed var names
    %lst    - chameleon colored rectangular drop-down for list names
    %b      - chameleon colored hexagonal slot (for predicates)
    %bool   - chameleon colored hexagonal slot (for predicates), static
    %l      - list icon
    %c      - C-shaped command slot, special form for primitives
    %cs     - C-shaped, auto-reifying, accepts reporter drops
    %cl     - C-shaped, auto-reifying, rejects reporters
    %clr    - interactive color slot
    %t      - inline variable reporter template
    %anyUE  - white rectangular type-in slot, unevaluated if replaced
    %boolUE - chameleon colored hexagonal slot, unevaluated if replaced
    %f      - round function slot, unevaluated if replaced,
    %r      - round reporter slot
    %p      - hexagonal predicate slot

    rings:

    %cmdRing    - command slotted ring with %ringparms
    %repRing    - round slotted ringn with %ringparms
    %predRing   - diamond slotted ring with %ringparms

    arity: multiple

    %mult%x      - where %x stands for any of the above single inputs
    %inputs      - for an additional text label 'with inputs'
    %words       - for an expandable list of default 2 (used in JOIN)
    %exp         - for a static expandable list of minimum 0 (used in LIST)
    %scriptVars  - for an expandable list of variable reporter templates
    %parms       - for an expandable list of formal parameters
    %ringparms   - the same for use inside Rings
    """
            nom=block.blockSpec            
            txt=re.findall(r'(%\w+)',block.blockSpec)
            repl={}
            i=0
            for e in txt:                
                t=e[1]
                #print(t,[inp.rang for inp in block.inputs])
                try:
                    en=next(inp for inp in block.inputs if inp.rang==i)
                    en=self.findBlock(en, liste)
                    if t=='c':
                        #print('Command',en.blockSpec)
                        repl[e]='['
                        print(en.inputs[0].typeMorph)
                        parcours(liste,self.findBlock(en.inputs[0], liste),'.')
                    else:
                        repl[e]=en.contenu
                        #print('rang %s (%s): %s' % (i,e,en.contenu))
                except:
                    repl[e]=e
                    #print(e,'??')
                nom=nom.replace(e,'['+repl[e]+']',1)
                i+=1
            
            return nom
                
        def parcours(l,block,decal):
            e=next(n for n in l if n is not None and n.JMLid==block.JMLid)
            decal=''
            while e is not None:
                #print(decal,e.JMLid,e.blockSpec,e.time,afficheCommand(e))
                print(decal,e.JMLid,afficheCommand(e))
                parcoursInput(l,e,decal+' ')
                nextblock=e.nextBlock
                if nextblock is not None:
                    e=next(n for n in l if n is not None and n.JMLid==nextblock.JMLid)
                else:
                    e=None
                    
        def parcoursInput(l,block,decal):
            for i in block.inputs:
                try:
                    e=next(n for n in l if n is not None and n.JMLid==i.JMLid)
                    # print(decal,e.JMLid,e.typeMorph,e.time)
                    parcours(l,e,decal+'.')
                except:
                    #print(i.JMLid,' non trouvé')
                    pass
                
        liste=self.lastListe(time, veryLast=True)
        for d in self.firstBlocks:
            #print('Debut',d,liste)
            try:
                e=next(n for n in liste if n is not None and n.JMLid==d)
                parcours(liste,e,'')
            except:
                pass

    def addFromBlock(self,block,time=None,action=''):
        
        """
        crée un nouveau block (et ses netx/inputs) 
        correspondant a un block de type models.Block, models.BlockInput ou BlockSnap
        """
        def parcours(b):
            """ parcours dans le cas d'un blockSnap, on ne prend pas les nextBlocks"""            
            b.time=time
            b.action=action
            for i in b.inputs:
                parcours(i)
            self.addBlock(b)
            create.append(b)
            
        create=[] #liste des BlockSnap créés
        if type(block)==models.BlockInput:
            newblock=BlockSnap(block.JMLid,time,block.typeMorph,action=action)
            newblock.rang=block.rang
            newblock.contenu=block.contenu
            create.append(newblock)
            self.addBlock(newblock)
        elif type(block)==models.Block:
            #c'est un Block normal
            newblock=BlockSnap(block.JMLid,time,block.typeMorph,
                     block.blockSpec,
                     block.selector,
                     block.category,
                     action=action
                     )
            create.append(newblock)
            self.addBlock(newblock)
            #récupération du block suivant
            if block.nextBlock is not None:
                #on construit le nextBlock                
                nextblock, created=self.addFromBlock(block.nextBlock, time,action=action)
                create+=created
                newblock.setNextBlock(nextblock)            
            #on parcourt les inputs "blocks" (et on les rajoute)
            for inputBlock in block.inputsBlock.all():
                newinput,created=self.addFromBlock(inputBlock,time,action=action)
                create+=created
                newblock.addInput(newinput)
            #récupération des entrées "de base" 
            for inputEl in block.inputs.all():
                #recherche de l'input correspondant
                try:
                    inputB=next((item for item in newblock.inputs if item.JMLid==inputEl.JMLid))
                    inputB.rang=inputEl.rang
                    inputB.contenu=inputEl.contenu                    
                except (KeyError,StopIteration):
                    #l'entrée n'existe pas, on la crée
                    newinput,created=self.addFromBlock(inputEl,time,action=action)
                    create+=created
                    newblock.addInput(newinput)     
            if block.typeMorph=='CSlotMorph':
                #c'est un conteneur, il n'a qu'un input
                #tous les blocks 'nextblocks' seront aussi contenus (et ils ont déjà été créés)
                bs=newblock.inputs[0]
                while bs is not None:
                    newblock.addWrappedBlock(bs)
                    bs=bs.nextBlock               
        elif type(block)==BlockSnap:            
            #c'est un BlockSnap inclus dans le SPR ou autre  
            #newblock=copy.deepcopy(block)
            newblock=block.copy(time,action,deep=True)
            parcours(newblock)
            #newblock.time=time       
            #newblock.action=action
            #create.append(newblock)
            #self.addBlock(newblock)
            
        else:
            print('on ne sait pas ce quest ',block)
        
        #print('nex',newblock,'create:',['%s_%s (%s)' % (b.JMLid,b.time,b.action) for b in create])                               
        return newblock, create    
    def toJson(self):
        """ renvoie sous la forme [{BlockSnap},{}]"""
        j=[]
        for JMLid in self.liste:
            #j[JMLid]=[]
            for n in self.liste[JMLid]:
                #j[JMLid].append(n.toJson())
                j.append(n.toJson())
        return j
class BlockSnap:
    """
    Objet Block
    """    
    def __init__(self,JMLid,time,typeMorph,
               blockSpec=None,
               selector=None,
               category=None,
               action=None
               ):
        self.JMLid=JMLid    #JMLid du bloc,
        self.time=time  #temps (Snap) de création du bloc        
        self.typeMorph=typeMorph
        self.blockSpec=blockSpec #BlockSpec du bloc
        self.selector=selector
        self.category=category # toujours à null, à vérifier ou supprimer?
        self.action=action #type d'action concernant ce block (type evenement+valeur)       
        self.nextBlock=None      # block suivant (BlockSnap) s'il existe
        self.prevBlock=None      # block précédent s'il existe
        self.parentBlock=None    # block parent s'il existe (ie ce block est un input du parent
        self.rang=None           # rang du block dans les inputs de son parent
        self.conteneurBlock=None # block conteneur s'il existe (ie ce block est "wrapped"    
        self.inputs=[]           # liste des blocks inputs
        self.childs=[]           # liste des blocks enfants 
        self.wraps=[]            # liste des blocks contenus
        self.contenu=None        # contenu du block(ie la valeur pour un InputSlotMorph)
        #print('BLOCK %s_%s: %s (%s) créé' % (self.JMLid,self.time,self.typeMorph,self.action))
    
    def getId(self):
        return '%s_%s' % (self.JMLid,self.time)
    @classmethod
    def getJMLid(cls,block):
        """ renvoi le JMLid correspondant à au block ou à l'id passée"""
        if type(block)=='dict':
            return block.JMLid            
        return int(block.split('_',1)[0])
    
    
    def copy(self,time,action='',deep=False):
        """ renvoie une copie du BlockSnap,        
        """
        def modif(b):
            b.time=time
            b.action=action
            for i in b.inputs:
                modif(i)
        
        if deep:
            #copie profonde, mais pas de rajout dans la liste!
            newblock=copy.deepcopy(self)
            modif(newblock)
        else:
            newblock=copy.copy(self)
        newblock.time=time   
        newblock.action=action
        return newblock
            
        
    def setNextBlock(self,nextBlock):
        """ définit le bloc nextBlock comme étant le suivant 
        (et modifie le prevBlock de nextblock)
        """
        self.nextBlock=nextBlock
        if nextBlock is not None:
            nextBlock.prevBlock=self
    def addWrappedBlock(self,block):
        """
        ajoute le block comme étant contenu dans self
        """
        self.wraps.append(block)
        block.conteneurBlock=self
    
    def setConteneur(self,block):    
        """
        définit le block comme étant le conteneur de self
        """
        block.addWrappedBlock(self)
    def addInput(self,block):
        """
        ajoute le block comme étant un input de self
        """
        self.inputs.append(block)
        block.parentBlock=self
    
    def setParent(self,block):
        """
        définit block comme étant le parent de self (ie self est input de block)
        """
        block.addInput(self)
    def replaceInput(self,rang,block):
        """
        remplace l'input de rang rang par le block
        """
        inputChanged=next((i for i in self.inputs if i.rang==rang))
        self.inputs.remove(inputChanged)
        block.rang=rang
        self.addInput(block)
        
    def toJson(self):                
        j={}
        j['id']=self.getId()
        j['JMLid']=self.JMLid    #JMLid du bloc,
        j['time']=self.time  #temps (Snap) de création du bloc
        j['typeMorph']=self.typeMorph
        j['blockSpec']=self.blockSpec #BlockSpec du bloc
        j['selector']=self.selector
        j['category']=self.category # toujours à null, à vérifier ou supprimer?       
        j['rang']=self.rang
        j['contenu']=self.contenu
        """
        j['nextBlock']=self.nextBlock.toJson() if self.nextBlock is not None else None
        j['prevBlock']=self.prevBlock.toJson() if self.prevBlock is not None else None
        j['parentBlock']=self.parentBlock.toJson() if self.parentBlock is not None else None
        j['conteneurBlock']=self.conteneurBlock.toJson() if self.conteneurBlock is not None else None
        """
        j['nextBlock']=self.nextBlock.getId()   if self.nextBlock is not None else None
        j['prevBlock']=self.prevBlock.getId() if self.prevBlock is not None else None
        j['parentBlock']=self.parentBlock.getId() if self.parentBlock is not None else None
        j['conteneurBlock']=self.conteneurBlock.getId() if self.conteneurBlock is not None else None
        j['action']=self.action      
        j['inputs']=[]           # liste des blocks inputs
        j['name']=self.getNom()
        for i in sorted(self.inputs,key=lambda inp: inp.rang):
            j['inputs'].append(i.getId())            
        return j
        #self.childs=[]           # liste des blocks enfants 
        #self.wraps=[]            # liste des blocks contenus
        #self.contenu=None        # co
        
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
       
    def aff(self,indent=0):
        for i in self.__dict__:
            print(' '*indent,'%s: %s' % (i,self.__dict__[i]))            
        if self.inputs:
            print(' '*indent,'INPUTS:')
            for i in self.inputs:
                i.aff(indent+2)
                print(' '*indent,'---')
        if self.nextBlock:
            print(' '*indent,'NEXTBLOCK:',self.nextBlock.JMLid)
            self.nextBlock.aff(indent)
            
    def __str__(self):
        if self.rang is not None:
            rang=" (rang %s)" % self.rang
        else:
            rang=''
        return "%s_%s: %s%s (%s)" % (self.JMLid,self.time,self.getNom(),rang,self.action)
    def __repr__(self):
        return self.__str__()

class CytoNode:
    """
    Objet noeud pour cytoscape
    """
    @classmethod
    def getCytoId(cls,block):
        """
        l'id du noeud est de la forme JMLid_time
        """
        if block is not None and block.JMLid is not None:
            return '%s_%s' % (block.JMLid,block.time)
        return None
    
    def __init__(self,blockSnap):
        """
         crée un noeud représentant le block blockSnap au temps time
        """
        self.id=self.getCytoId(blockSnap) #id du noeud
        self.JMLid=blockSnap.JMLid          #JMLid du bloc,
        self.blockSpec=blockSnap.blockSpec    #BlockSpec du bloc
        self.time=blockSnap.time
        self.selector=blockSnap.selector
        self.typeMorph=blockSnap.typeMorph
        self.category=blockSnap.category      # toujours à null, à vérifier ou supprimer?
        self.nextBlockId=CytoNode.getCytoId(blockSnap.nextBlock)     # id du noeud suivant  s'il existe        
        self.prevBlockId=CytoNode.getCytoId(blockSnap.prevBlock)      # id du noeud précédent s'il existe
        self.parentBlockId=CytoNode.getCytoId(blockSnap.parentBlock)    # id du noeud parent s'il existe (ie ce block est un input du parent
        self.conteneurBlockId=CytoNode.getCytoId(blockSnap.conteneurBlock) # id du noeud conteneur s'il existe (ie ce block est "wrapped"        
        self.inputs=[CytoNode.getCytoId(i) for i in blockSnap.inputs]
        self.rang=blockSnap.rang
        self.contenu=blockSnap.contenu
    
    def toTarget(self,block,typeLien='nextblock'):
        """
        ajoute un lien vers le block
        """
        return CytoEdge(self.id,block.id,typeLien)
    def fromSource(self,block,typeLien=None):
        """
        ajoute un lien depuis le block
        """
        return CytoEdge(block.id,self.id,typeLien)
    
    
    def toJson(self):
        j={}
        j['id']=self.id
        j['JMLid']=self.JMLid
        j['time']=self.time
        j['blockSpec']=self.blockSpec
        j['selector']=self.selector
        j['typeMorph']=self.typeMorph
        j['category']=self.category
        j['nexBlockId']=self.nextBlockId
        j['prevBlockId']=self.prevBlockId
        j['parentBlockId']=self.parentBlockId        
        j['conteneurBlockId']=self.conteneurBlockId
        j['inputs']=[i for i in self.inputs]
        j['rang']=self.rang
        j['contenu']=self.contenu
        j['parent']=self.parentBlockId if self.parentBlockId is not None else self.conteneurBlockId
        return j
    
class CytoEdge:
    """
    Objet lien pour cytoscape
    """
    
    def __init__(self,sourceId,targetId,typeLien=None,couleur=None):
        """
        crée un lien cytoscape entre les noeuds sourceId et targetId, de type typeLien
        """
        self.source=sourceId
        self.target=targetId
        self.type=typeLien
        self.couleur=couleur
        
    def setCouleur(self,couleur):
        """fixe la couleur du lien"""
        self.couleur=couleur
        
    def toJson(self):
        j={}
        j['source']=self.source
        j['target']=self.target
        j['type']=self.type
        j['couleur']=self.couleur
        return j
        
class CytoElements:
    """
    liste sous la forme nodes:[noeuds,],edges:[liens,]
    """
    def __init__(self):
        self.nodes=[]
        self.edges=[]
    
    @classmethod
    def constructFrom(cls,blockRoot):
        """
        construit la liste à partir du block blockRoot
        """
        elt=CytoElements()
        node=CytoNode(blockRoot)
        elt.nodes.append(node)
        if node.nextBlockId:
            elt.edges.append(CytoEdge(node.id,node.nextBlockId,'nextblock'))
            nextblockElts=CytoElements.constructFrom(blockRoot.nextBlock)
            elt.nodes+=nextblockElts.nodes
            elt.edges+=nextblockElts.edges
        for i in blockRoot.inputs:
            ###ajout des inputs
            inputsElts=CytoElements.constructFrom(i)
            elt.nodes+=inputsElts.nodes
            elt.edges+=inputsElts.edges
            elt.edges.append(CytoEdge(node.id,CytoNode(i).id,'input'))
        return elt
    def addFrom(self,blockRoot):
        """
        rajoute la liste contruite a partir de blockRoot
        """
        elt=CytoElements.constructFrom(blockRoot)
        self.nodes+=elt.nodes
        self.edges+=elt.edges
        return self
    
    def setChange(self,block):
        """
        cherche et ajoute un lien "change" lorsque qu'un même block est modifié
        """
        # b: dernier block de même JMLid
        bs=[n for n in self.nodes if n.JMLid==block.JMLid and n.time<block.time]
        b=sorted(bs,key=lambda n: n.time,reverse=True)[0]
        if b is not None:
            self.edges.append(CytoEdge(b.id,CytoNode.getCytoId(block),'change'))
        return self
       
    def toJson(self):
        return {'nodes':[{'data':n.toJson()} for n in self.nodes], 
                'edges':[{'data':n.toJson()} for n in self.edges]}

        