export {graphProgramme}

function formatTimeToHMS(num) {
    num=Math.floor(num/1000)
    var h = Math.floor(num / 3600);
    var m = Math.floor((num - h * 3600) / 60);
    var s = num - (h * 3600 + m * 60);
    return (h < 10 ? "0" + h : h) + "h" + (m < 10 ? "0" + m : m) + "m" + (s < 10 ? "0" + s : s)+"s";
}
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
        let firstTete=true
        console.log("etape",c.temps,tetes)
        //on reconstruit
        let newData={}
        let divG=d3.select("#"+div).append("div").attr("class","blockcommands")
        if (tetes.length==0 ) {
            let divCom=divG.append("div").attr("class","tete").html(c.temps+" "+c.evt.type+" "+(c.evt.detail?c.evt.detail:''))            
        }
        if (c.epr==null) {
            tetes.forEach(function(t) {            
                newData[t.JMLid]=parcoursCommande(c.snap,[],t,0)
                let divCom
                if (firstTete) {
                    divG.append("div").attr("class","tete").html(formatTimeToHMS(c.temps)+" "+c.evt.type+" "+(c.evt.detail?c.evt.detail:''))
                    firstTete=false
                } else {
                    divG.append("div").attr("class","separation").html('--')
                }
                let enter=divG.selectAll(".commande").data(newData[t.JMLid])
                enter.enter().append("p")
                    .attr("class",d=>"command "+(d.action?'action ':'')+(d.typeMorph?d.typeMorph:''))
                    .attr("title",d=>(d.action?(d.action+"\n"):"")+`id:${d.JMLid}`)
                    .html(d=>'...'.repeat(d.index)+d.commande)
            })
            console.log(newData)
        } else {
            //traitement snap
            let fin=(c.epr.detail.substring(0,3)=='FIN')
            divG.classed("blocksnap",true)
                .classed("start",!fin)
                .classed("fin",fin)
                .append("div").attr("class","tete").html(formatTimeToHMS(c.temps)+" "+c.evt.type+" "+(c.evt.detail?c.evt.detail:'')) 
            divG.append("div").html(fin?"END":"START")
        }
        
        
        
    })
}