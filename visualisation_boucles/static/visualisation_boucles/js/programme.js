export {graphProgramme, graphNbCommandes, graphStackNbCommandes}

function formatTimeToHMS(num) {
    num=Math.floor(num/1000)
    var h = Math.floor(num / 3600);
    var m = Math.floor((num - h * 3600) / 60);
    var s = num - (h * 3600 + m * 60);
    return (h < 10 ? "0" + h : h) + "h" + (m < 10 ? "0" + m : m) + "m" + (s < 10 ? "0" + s : s)+"s";
}
const parcoursCommande=function(commandes,data,snap,index) {
    //console.log('tratieltme',snap.JMLid,index,snap.wrappedBlock,snap.nextBlock)
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

const graphStackNbCommandes=function(config) {
    var me = this,
    d3Ele = config.element,
    data = config.data,
    margin = {top: 20, right: 20, bottom: 20, left: 50},
    parseDate = d3.timeParse("%m/%Y"),
    width = d3Ele.node().getBoundingClientRect().width - margin.left - margin.right,
    height = 600 - margin.top - margin.bottom,
    xScale1 = d3.scaleLinear().range([0, width]),
    xScale2 = d3.scalePoint().range([0, width]),
    yScale = d3.scaleLinear().range([height, 0]),    
    //color = d3.scaleOrdinal(d3.schemeCategory10),        
    xAxis1 = d3.axisBottom(xScale1),            
    xAxis2 = d3.axisBottom(xScale2),
    yAxis =  d3.axisLeft(yScale),
    color
    
    console.log('tratiement',data)
    
    const ordinal=true; //traitement par temps ou par evenement
    
    /**
     * préparation des données
     */
    var donnees=[], liste_tetes=[], tabTemps=[], last={}
    data.commandes.forEach(function(c) {
        tabTemps.push(""+c.temps)
        //on commence par rechercher les blocks de tête
        if (c.snap==null) console.log("erreur:",c)
        let tetes=c.snap.filter(d=>d.commande 
                        && ((d.conteneurBlock==null && d.prevBlock==null)
                            || 
                            (d.conteneurBlock!=null && d.conteneurBlock.indexOf('SCRIPT')!=-1 ))
                    )
        let elt={temps:c.temps}             
        
        tetes.forEach(function(t){
             const cmds=parcoursCommande(c.snap,[],t,0)
             elt["Block_"+t.JMLid]={commandes:cmds,nb:cmds.length,nbPrev:last["Block_"+t.JMLid]}
             last["Block_"+t.JMLid]=cmds.length
             if (liste_tetes.indexOf("Block_"+t.JMLid)==-1) liste_tetes.push("Block_"+t.JMLid)
            })
        donnees.push(elt)
    })
    //console.log("-->donnees",donnees,liste_tetes,tabTemps)    
    //on recherche le nombre maxi de commandes (cumulées)
    var maxNbs = d3.max(donnees, function(d){        
        var vals = d3.keys(d).map(function(key){ return key !== "temps" ? (d[key]?d[key].nb : 0):0 });
        return d3.sum(vals);
    });
    //console.log('max',maxNbs)
    //définition des échelles
    xScale1.domain([0,d3.max(donnees,d=>d.temps)])
    xScale2.domain(tabTemps)
    yScale.domain([0,maxNbs+1]).nice()
   
    //definition des couleurs
    var color=d3.scaleOrdinal(d3.schemeSet3).domain(liste_tetes)
    
    //constitution des stacks
    var stack=d3.stack()
                 .keys(liste_tetes)
                 .value((d,key)=>{
                      if (d[key]) return d[key].nb
                      else return 0
                 })
    var series=stack(donnees)
    var area = d3.area()
                .x(d=>ordinal? xScale2(""+d.data.temps): xScale1(d.data.temps))
                .y0(function(d) { return yScale(d[0]); })
                .y1(function(d) { return yScale(d[1]); })
                .curve(d3.curveLinear)
    //console.log('serie',series)
    
    /**
     * preparation du svg
     */
    d3Ele.attr("width", width + margin.left + margin.right+10)
        .attr("height", height + margin.top + margin.bottom+10)
    var svg = d3Ele.append("svg")
        .attr("width", width + margin.left + margin.right)
        .attr("height", height + margin.top + margin.bottom)
        .append("g")
        .attr("transform", "translate(" + margin.left + "," + margin.top + ")");
    
    /**
     * tracage des axes
     */    
    const echelle=svg=>{        
        svg.append("g")
        .attr("class", "axis axis--x")
        .attr("transform", "translate(0," + (height+5) + ")")
        .call(ordinal?xAxis2:xAxis1);

        svg.append("g")
        .attr("class", "axis axis--y")
        .attr("transform", "translate(0,0)")
        .call(yAxis);       
    }
    
    /**
     * traçage des areas
     */
    const traceArea=svg=>{
        const dataPath=svg.selectAll(".nbcommandes-path")
            .data(series)
            .enter()
            .append("g")
            .attr("class","nbcommandes-path")
        const line=dataPath
                    .append('path')
                    .attr('class', 'area')
                    .attr('d', area)  
                    .attr("fill",d=>color(d.key));
    }
    
    /**
     * tracage des points
     */
    const tracePoints=svg=>{
        let s=svg.selectAll(".dot")
            .data(series,d=>d.key)
            .enter()
                .append("g")
                .attr("class", "dot") // Assign a class for styling
        s.selectAll(".circle")
            .data((d,i)=>d.filter(z=>{
                //on ne marque que les changements (des instructions ou du nombre d'intructions)
                let hasChanged=z.data[series[i].key]?z.data[series[i].key].commandes.some(ez=>ez.change.includes("AAchange")):false
                let hasChangedNb=z.data[series[i].key]?(z.data[series[i].key].nb!==z.data[series[i].key].nbPrev):false
                return hasChanged || hasChangedNb
                }))
            .enter()
            .append("circle") // Uses the enter().append() method
                .attr("class","dotcircle")
                .attr("cx", function(d) { return xScale2(d.data.temps) })
                .attr("cy", function(d) { return yScale(d[1]) })
                .attr("fill",function(d) {return d3.color(color(d3.select(this.parentNode).datum().key)).darker(1)})
                .attr("r", 2)                
                .on("mouseover", function(a, b, c) { 
                    //console.log(a) 
                    d3.select(this).classed('focus',true)
                })
                .on("mouseout", function() { d3.select(this).classed('focus',false) })
                
        //ajout d'un tippy
          tippy('.dotcircle',{content:function(tip) {
                    var d=d3.select(tip).datum()
                    let jmlid=d3.select(tip.parentNode).datum().key
                    return `<p>id:${jmlid}</p><p>temps:${d.temps}</vp><p>nb:<b>${d.nb}</b></p>`                    
                    },
                    placement:'left',
                    
                    onShown: function(tip) {                        
                        let datum=d3.select(tip.reference).datum()
                        let jmlid=d3.select(tip.reference.parentNode).datum().key
                        let div=d3.select("#overlayDiv2").append("div")//.attr("class","progs").html("ici")
                        //console.log("youy",datum,jmlid)    
                        div.append("div").html(`<p>id:${jmlid}</p>
                                                <p>temps:${datum.data.temps}</p>
                                                <p>nb:<b>${datum.data[jmlid].nb}</b></p>`)
                        div.selectAll("p.command").data(datum.data[jmlid].commandes)
                            .enter().append("p")
                        .attr("class",d=>"command "+(d.action?'action ':'')+(d.typeMorph?d.typeMorph:''))
                        .attr("title",d=>(d.action?(d.action+"\n"):"")+`id:${d.JMLid}`)
                        .html(d=>'...'.repeat(d.index)+d.commande)
                        tip.setContent(div.node())
                    },
                    
                    /*async onHide(tip) {
                        d3.select("#overlayDiv2").selectAll(".progs").remove()
                    }*/
        })
    }
    
    /**
     * traçage des epr     
     */
    const traceEvenements=svg=> {
        let evts=data.commandes.filter(d=>d.evt != null).map(function(d){return {temps:d.temps,evt:d.evt}})
        console.log("evts",evts)
        svg.selectAll(".dotEvts").data(evts)
            .enter()
            .append("circle")
            //.attr("class",function(d){return "dotEvts "+d.evt.evenement_type})
            .attr("class",function(d) {return "dotEvts "+d.evt.evenement_type})
            .attr("cx", function(d) { return xScale2(d.temps) })
            .attr("cy", function(d) { return yScale(0) })
            .attr("r", 3)
            .on("mouseover",function(a,b,c) {
                console.log("az",a,b,c,this)
               svg
                    .append("line")
                    .attr("id","lignetemps")
                    .attr("x1",xScale2(a.temps))
                    .attr("y1",yScale(0))
                    .attr("x2",xScale2(a.temps))
                    .attr("y2",yScale(maxNbs))
                    .style("stroke-width",2)
                    .style("stroke","grey")
            })
            .on("mouseout",function() {
                svg.select("#lignetemps").remove()
            })
        tippy(".dotEvts",{
            content:function(tip){                
                var d=d3.select(tip).datum()
                return `<p>temps: ${d.temps}</p>
                <p>${d.evt.evenement_type}</p>
                <p>${d.evt.type} ${d.evt.detail?d.evt.detail:""}</p>  `
            }
        })
    }
    /**
     * traçage
     */
    echelle(svg)
    traceArea(svg)
    tracePoints(svg)
    traceEvenements(svg)
}
const graphNbCommandes=function(config) {
        var me = this,
        d3Ele = config.element,
        data = config.data,
        margin = {top: 20, right: 20, bottom: 20, left: 50},
        parseDate = d3.timeParse("%m/%Y"),
        width = d3Ele.node().getBoundingClientRect().width - margin.left - margin.right,
        height = 600 - margin.top - margin.bottom,
        xScale = d3.scaleLinear().range([0, width]),
        yScale = d3.scaleLinear().range([height, 0]),
        //color = d3.scaleOrdinal(d3.schemeCategory10),        
        xAxis = d3.axisBottom(xScale),            
        yAxis =  d3.axisLeft(yScale)
        
    console.log('tratiement',data)
    
    var toutesTetes=data.commandes.map(d=>d.snap.map(i=>i.JMLid))
                        .reduce((a,c)=>{c.forEach(i=>{if (a.indexOf(i)==-1) a.push(i)}); return a},[]).sort()
    var color=d3.scaleOrdinal(d3.schemeCategory10).domain(toutesTetes)
    console.log("test",toutesTetes)
    //toutesTetes.forEach(d=>console.log(d,color(d)))
    var commandes=[]
    data.commandes.forEach(function(c) {
        //on commence par rechercher les blocks de tête
        if (c.snap==null) console.log("erreur:",c)
        let tetes=c.snap.filter(d=>d.commande 
                        && ((d.conteneurBlock==null && d.prevBlock==null)
                            || 
                            (d.conteneurBlock!=null && d.conteneurBlock.indexOf('SCRIPT')!=-1 ))
                        )
        let firstTete=true
        console.log("etape",c.temps,tetes)
        //on reconstruit
        let newData=[]
        if (c.epr==null) {
            tetes.forEach(function(t) {            
                newData.push({JMLid:t.JMLid,commande:parcoursCommande(c.snap,[],t,0)})                
            })
            console.log('->',newData.length,newData)
            
            commandes.push({temps:c.temps,commandes:newData,nb:newData.length})
        }
    })
    console.log('_>DAT',commandes,newData)
    //on remanie sous la forme JMLid=>[{temps,nb,cmds}...]
  
    var donnees=commandes.reduce((a,c)=>{
        c.commandes.forEach(d=>{
            if (!a[d.JMLid]) a[d.JMLid]=[];
            a[d.JMLid].push({temps:c.temps, nb:d.commande.length,cmds:d.commande})
            })
          return a
        },{})
    //console.log("donnees",donnees,d3.keys(donnees),d3.values(donnees),d3.entries(donnees))
    var values=d3.values(donnees)
    //console.log("entries",values)
    var total=d3.merge(values).reduce((a,c)=>{
        if (!a[c.temps]) a[c.temps]=c.nb
        else a[c.temps]+=c.nb
        return a
      },{})
      
      xScale.domain([0,d3.max(commandes,d=>d.temps)])
      yScale.domain([0,d3.max(d3.values(total))])
    console.log("total",total,d3.entries(total))
    d3Ele.attr("width", width + margin.left + margin.right+10)
        .attr("height", height + margin.top + margin.bottom+10)
     var svg = d3Ele.append("svg")
        .attr("width", width + margin.left + margin.right)
        .attr("height", height + margin.top + margin.bottom)
        .append("g")
        .attr("transform", "translate(" + margin.left + "," + margin.top + ")");
    var line = (xacc,yacc)=>
            d3.line()
        .x(function(d, i) {return xScale(xacc(d)); }) // set the x values for the line generator
        .y(function(d) { return yScale(yacc(d)); }) // set the y values for the line generator 
        .curve(d3.curveMonotoneX)// apply smoothing to the line
    
    
    const traceLine=svg=>{        
        svg.selectAll(".linenbcommandes").data(d3.entries(donnees),d=>d.key).enter()
            .append("path")
            //.datum(d=>d.value) // 10. Binds data to the line 
            .attr("class", "linenbcommandes") // Assign a class for styling 
            .style("stroke",(d,i)=>color(d.key))
            .attr("d", d=>line(d=>d.temps,d=>d.nb)(d.value));
    }
    const traceTotal=svg=>{
        svg.append('path')
      //.datum(d=>d.value) // 10. Binds data to the line 
            .attr("class", "linenbtotalcommandes") // Assign a class for styling            
            .attr("d", line(d=>d.key,d=>d.value)(d3.entries(total)));
        
    }
    const tracePoints=svg=>{
        let s=svg.selectAll(".dot")
            .data(d3.entries(donnees),d=>d.key)
            .enter().append("g").attr("class", "dot") // Assign a class for styling
        s.selectAll(".circle").data(d=>d.value)
            .enter()
            .append("circle") // Uses the enter().append() method
                .attr("class","dotcircle")
                .attr("cx", function(d, i) { return xScale(d.temps) })
                .attr("cy", function(d) { return yScale(d.nb) })
                .attr("fill",function(d,i){
                    //la clef (JMLid) est dans le datum du parent
                    return color(d3.select(this.parentNode).datum().key)
                })
                .attr("r", 4)                
                .on("mouseover", function(a, b, c) { 
                    console.log(a) 
                    d3.select(this).attr('class', 'focus')
                })
                .on("mouseout", function() {  })
        tippy('.dotcircle',{content:function(tip) {
                    var d=d3.select(tip).datum()
                    let jmlid=d3.select(tip.parentNode).datum().key
                    return `<p>id:${jmlid}</p><p>temps:${d.temps}</vp><p>nb:<b>${d.nb}</b></p>`                    
                    },
                    placement:'left',
                    onShown: function(tip) {
                        //console.log("youy",d3.select(tip.reference).datum())
                        let datum=d3.select(tip.reference).datum()
                        let jmlid=d3.select(tip.reference.parentNode).datum().key
                        let div=d3.select("#overlayDiv2").append("div")//.attr("class","progs").html("ici")
                            
                        div.append("div").html(`<p>id:${jmlid}</p>
                                                <p>temps:${datum.temps}</p>
                                                <p>nb:<b>${datum.nb}</b></p>`)
                        div.selectAll("p.command").data(datum.cmds)
                            .enter().append("p")
                        .attr("class",d=>"command "+(d.action?'action ':'')+(d.typeMorph?d.typeMorph:''))
                        .attr("title",d=>(d.action?(d.action+"\n"):"")+`id:${d.JMLid}`)
                        .html(d=>'...'.repeat(d.index)+d.commande)
                        tip.setContent(div.node())
                    },
                    /*async onHide(tip) {
                        d3.select("#overlayDiv2").selectAll(".progs").remove()
                    }*/
        })
    }
    const echelle=svg=>{
        
        svg.append("g")
        .attr("class", "axis axis--x")
        .attr("transform", "translate(0," + (height+5) + ")")
        .call(xAxis);

        svg.append("g")
        .attr("class", "axis axis--y")
        .attr("transform", "translate(0,0)")
        .call(yAxis);       
    }
    echelle(svg)
    traceLine(svg)
    traceTotal(svg)
    tracePoints(svg)
    
}
const graphProgramme=function(donnees,div,forExport=false) {
    const affTruc=function(s) {
        if (s) {
            const tapTruc=[["next","⬇"],["prev","⬆"],["me","⇒"],
                ["contenu","⤵"],["conteneur","↖"],
                ["undrop","↩"],["redrop","↪"],
                ["lastnode","⇏"],["del","❌"],
                ["copyfrom","⇺"],["copyto","⇻"]
            ]
            const mapTruc=new Map(tapTruc)
            var ret=""
            s.split(" ").forEach(d=>ret+=(mapTruc.get(d)!=undefined?mapTruc.get(d):" "))
            return ret
        }
        return ""
    }
    //reconstitue le graphe du programme donné en paramère
    //données={commandes,infos,ticks,scripts}
    
    //ajout d'un checkbox pour n'afficher que les scripts ayant changé
    div.append("div")
        .append("label").attr("for","onlysScriptChanged").text("Seulement les scripts modifiés")
        .append("input").attr("type","checkbox")
            .property("checked",false)
            .attr("id","onlysScriptChanged")        
            .on("change",function(cb,j){
                const checked=d3.select(this).property("checked")
                console.log("checked",checked,d3.selectAll(".script.notChanged"))
                d3.selectAll(".script.notChanged,.tetescript.notChanged")
                    .style("display",checked?"none":"inline-block")
                })
      
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
            console.log("c=",c)
            let divCom=divG.append("div")
                    .attr("class","tete")
                    .attr("title","--")
                    .html(c.temps+" "+c.evt.type+" "+(c.evt.detail?c.evt.detail:''))
                    
        }
        if (c.epr==null) {
            tetes.forEach(function(t) {            
                newData[t.JMLid]=parcoursCommande(c.snap,[],t,0)
                
                if (firstTete) {
                    divG.append("div")
                        .attr("class","tete")
                        .html(formatTimeToHMS(c.temps)+" "+c.evt.type+" "+(c.evt.detail?c.evt.detail:''))
                        .attr("title","évènement: "+c.evt.evenement)
                    firstTete=false
                } /*else {
                    divG.append("div").attr("class","separation").html('--')
                }*/
                let hasChanged=newData[t.JMLid].some(ez=>ez.change.includes("AAchange"))
                divG.append("div").attr("class","separation").append("span")
                        .attr("class","tetescript")
                        .classed("notChanged",!hasChanged)
                        .html(t.JMLid)
                let divScript=divG.append("div")
                                    .attr("class","script")
                                    .classed("hasChanged",hasChanged)
                                    .classed("notChanged",!hasChanged)
                let enter=divScript.selectAll(".commande").data(newData[t.JMLid])
                enter.enter().append("p")
                    .attr("class",d=>"command "+(d.action?'action ':'')+(d.typeMorph?d.typeMorph:''))
                    .attr("title",d=>(d.action?(d.action+"\n"):"")+`id:${d.JMLid} truc:${d.truc}`)
                    .html(d=>'...'.repeat(d.index)+affTruc(d.truc)+ d.commande)
            })
            //console.log(newData)
        } else {
            //traitement epr
            let start=(c.epr.type=="START")
            let startclic=(start && c.epr.click)
            let fin=(c.epr.type=="FIN")
            let arret=(c.epr.type=="STOP")
            let snp=(c.epr.type=="SNP")
            let ask=(c.epr.type=="ASK")
            let answ=(c.epr.type=="ANSW")
            if (snp) console.info("detail",c.epr.detail)
            let pause=(c.epr.type=='PAUSE')
            let repr=(c.epr.type=='REPR')
            divG.classed("blockepr",true)
                .classed("start",start)
                .classed("startclic",startclic)
                .classed("end",fin || arret)
                .classed("snp",snp)
                .classed("ask",ask)
                .classed("answ",answ)
                .classed("snpstart",snp && c.epr.detail.substring(0,5)=='START')
                .classed("snpfin",snp && c.epr.detail.substring(0,3)=='FIN')
                .classed("snpstop",snp && c.epr.detail.substring(0,4)=='STOP')
                .classed("snppause",snp && c.epr.detail.substring(0,5)=='PAUSE')
                .classed("snprepr",snp && c.epr.detail.substring(0,4)=='REPR')
                .classed("pause",pause)
                .classed("reprise",repr)
                .append("div").html(formatTimeToHMS(c.temps)+"\n"+c.evt.type)
                .append("p").html(c.evt.detail?`<span>${c.evt.detail}</span>`:c.epr.detail?`<span>${c.epr.detail}</span>`:'')
                .append("p").html(startclic?'CLICK':'')
            //divG.append("div").html(fin?"END":"START")
            if (snp) {
                if (forExport) {
                    divG.append("img")
                        .attr("class","snapimageforexport")
                        .attr("src",c.epr.snp.image)
                } else {
                    divG.append("img")
                        .attr("class","snapimage")
                        .attr("src",c.epr.snp.image)
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
        }
        
        
        
    })
}