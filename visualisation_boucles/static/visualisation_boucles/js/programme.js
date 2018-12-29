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
const graphProgramme=function(donnees,div) {
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
        let divG=div.append("div").attr("class","blockcommands")
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
            //traitement epr
            let start=(c.epr.type=="START")
            let startclic=(start && c.epr.click)
            let fin=(c.epr.type=="FIN")
            let arret=(c.epr.type=="STOP")
            let snp=(c.epr.type=="SNP")
            let ask=(c.epr.type=="ASK")
            let answ=(c.epr.type=="ANSW")
            let snpfin=(snp && c.epr.detail.substring(0,3)=='FIN')
            divG.classed("blockepr",true)
                .classed("start",start)
                .classed("startclic",startclic)
                .classed("end",fin || arret)
                .classed("snp",snp)
                .classed("ask",ask)
                .classed("answ",answ)
                .classed("snpstart",snp && !snpfin)
                .classed("snpfin",snpfin)
                .append("div").html(formatTimeToHMS(c.temps)+"\n"+c.evt.type)
                .append("p").html(c.evt.detail?`<span>${c.evt.detail}</span>`:c.epr.detail?`<span>${c.epr.detail}</span>`:'')
                .append("p").html(startclic?'CLICK':'')
            //divG.append("div").html(fin?"END":"START")
            if (snp) {

                const state = {
                        isFetching: false,
                        canFetch: true
                }
                tippy(divG.node(),{
                    theme:'light',                 
                    content:"belle image"+c.epr.snp.image,
                    placement:'right',
                    delay:200,
                    arrow:true,
                    arrowType: 'round',
                    size: 'large',
                    duration: 500,
                    animation: 'perspective',
                    async onShow(tip) {                     
                        if ( state.isFetching || !state.canFetch) return
                        state.isFetching = true
                        state.canFetch = false
                        try {
                            const response = await fetch(c.epr.snp.image)
                            const blob = await response.blob()
                            const url = URL.createObjectURL(blob)
                            if (tip.state.isVisible) {
                                const img = new Image()
                                img.width = 300
                                img.height = 300
                                img.src = url
                                tip.setContent(img)
                            }
                        } catch (e) {
                            tip.setContent(`Fetch failed. ${e}`)
                        } finally {
                            state.isFetching = false
                        }
                    },
                    onHidden(tip) {
                        state.canFetch = true
                        tip.setContent("nothing")
                    }
                })
            }
        }
        
        
        
    })
}