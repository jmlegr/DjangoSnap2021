'''
Created on 16 nov. 2018

@author: duff
'''
'''
Created on 11 nov. 2018

@author: duff
'''
from snap.models import Evenement, EvenementSPR, EvenementENV, ProgrammeBase,\
    Document
from visualisation_boucles.reconstitution import SimpleListeBlockSnap
from lxml import etree

def liste(session):
    idsNew=[]
    listeNew=EvenementSPR.objects.filter(evenement__session_key=session,type='NEW').select_related('evenement','evenement__user').all()
    for i in listeNew:
        idsNew.append({'i':i.blockId,'b':i.blockSpec,'t':i.evenement.time})
    idsDrop=[]    
    listeDrop=EvenementSPR.objects.filter(evenement__session_key=session,type='DROP').select_related('evenement','evenement__user').all()
    for i in listeDrop:
        a={'i':i.blockId,'b':i.blockSpec}
        if a not in idsDrop:
            a['t']=i.evenement.time
            idsDrop.append(a)
    idsDrop.sort(key=lambda i: i['i'])
    idsDup=[]    
    listeDuplic=EvenementENV.objects.filter(evenement__session_key=session,type="DUPLIC").select_related('evenement','evenement__user').all()
    for i in listeDuplic:
        s=i.detail.split(";")[:-1]
        b=[j.split('-')[1] for j in s]
        #idsDup.extend(b)
        for j in b:
            idsDup.append({'i':j,'t':i.evenement.time})
    idsDup.sort(key=lambda j: j['i'])
    #return listeNew, listeDrop,listeDuplic
    return idsNew,idsDrop,idsDup

def verif(session_key):
    
    def createNew(spr,theTime,action=None):
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
    
    def setListe(temps,liste,typeEv):
        listes[-1]['time']=temps
        listes[-1]['liste']=liste
        #listes[-1]['type']=typeEv
        listes.append({'type':typeEv,'liste':None})
        
    listeBlocks=SimpleListeBlockSnap()
    evts=Evenement.objects.filter(session_key=session_key).order_by('time')
    dtime=None
    listes=[]
    alert=[]
    for evt in evts:
        print('evt',evt,evt.type,evt.id)
        if dtime is None:
            dtime=evt.time
            theTime=0
            listes=[{'type':"DEBUT"}]
        theTime=evt.time-dtime               
        evtType=evt.getEvenementType()
        if evt.type=='ENV' and evtType.type in ['NEW','LANCE']:
            setListe(theTime,listeBlocks,evtType.type)
            listeBlocks=SimpleListeBlockSnap()
        elif evt.type=='ENV' and evtType.type in ['LOBA','LOVER']:
            setListe(theTime,listeBlocks,evtType.type)
            listeBlocks=SimpleListeBlockSnap()
            if evtType.type=='LOBA':
                p=ProgrammeBase.objects.get(id=evtType.valueInt) #detail contient le nom
                f=p.file                
            else:
                p=Document.objects.get(id=evtType.detail)
                f=p.document
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
        elif evt.type=='SPR' and evtType.type=="NEW":
            spr=evt.evenementspr.all()[0]
            l=['%s' % spr.blockId]
            for i in spr.inputs.all():
                l.append('%s' %i.JMLid)
            
            findBlock=[b for b in listeBlocks.liste if '%s' % b.JMLid in l]
            newNode=createNew(spr,theTime)            
            if len(findBlock)>0:
                alert.append({'id':newNode.JMLid,'s1':findBlock[0].blockSpec,'s2':newNode.blockSpec,'time':theTime,'evt':evt.id,'type':evtType.type})
        elif evt.type=="ENV" and evtType.type=="DUPLIC":
            dp=evtType.detail.split(';')[:-1]
            ldp={}
            for i in dp:
                s=i.split('-')
                ldp[s[0]]=s[1]
                #findBlock=[b for b in listeBlocks.liste if b.JMLid==s[1]]
                findBlock=listeBlocks.lastNode(s[1],theTime)
                
                #if len(findBlock)>0:
                if findBlock is not None:
                    alert.append({'id':findBlock.JMLid,'s1':listeBlocks.lastNode(s[0], theTime).getNom(),'s2':findBlock.getNom(),'time':theTime,'evt':evt.id,'type':evtType.type})
            #ldp['time']=theTime
            #alert.append(ldp)
            print("-------------------------------------------duplic",ldp)
    setListe(theTime,listeBlocks,'FIN')    
    return listes,alert,dtime