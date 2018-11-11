export {graphProgramme}

const parcoursCommande=function(commandes,data,snap,index) {
    console.log('tratieltme',snap.JMLid,index,snap.wrappedBlock,snap.nextBlock)
    let retour=snap
    retour.index=index
    data.push(retour)
    if (snap.wrappedBlock!=null) {
        //il y a des blocks contenus
        const wrap=commandes.filter(d=>d.JMLid==snap.wrappedBlock)[0]
        data=data.concat(parcoursCommande(commandes,[],wrap,index+1))      
    }
    if (snap.nextBlock!=null) {
        const next=commandes.filter(d=>d.JMLid==snap.nextBlock)[0]
        data=data.concat(parcoursCommande(commandes,[],next,index))
    }
    return data
}
const graphProgramme=function(donnees,div="graphSujet") {
    //reconstitue le graphe du programme donné en paramère
    //données={commandes,infos,ticks,scripts}

    
    donnees.commandes.forEach(function(c) {
        //on commence par rechercher les blocks de tête
        let tetes=c.snap.filter(d=>d.commande 
                        && ((d.conteneurBlock==null && d.prevBlock==null)
                            || 
                            (d.conteneurBlock!=null && d.conteneurBlock.indexOf('SCRIPT')!=-1 ))
                        )
        console.log("etape",c.temps,tetes)
        //on reconstruit
        let newData={}
        let divG=d3.select("#"+div).append("div").attr("class","blockcommands")
        
        if (c.epr==null) {
            tetes.forEach(function(t) {            
                newData[t.JMLid]=parcoursCommande(c.snap,[],t,0)
                let divCom=divG.append("div").attr("class","tete").html(c.temps+" "+c.evt.type)
                let enter=divCom.selectAll(".commande").data(newData[t.JMLid])
                enter.enter().append("p").attr("class","command").html(d=>'...'.repeat(d.index)+d.commande)
            })
            console.log(newData)
    }
        
        
        
    })
}