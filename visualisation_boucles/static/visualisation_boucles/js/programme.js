export {graphProgramme, graphNbCommandes}

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
    console.log('_>DAT',commandes)
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
                .attr("r", 2)                
                .on("mouseover", function(a, b, c) { 
                    console.log(a) 
                    d3.select(this).attr('class', 'focus')
                })
                .on("mouseout", function() {  })
        tippy('.dotcircle',{content:function(tip) {
                    let d=d3.select(tip).datum()
                    let jmlid=d3.select(tip.parentNode).datum().key
                    return `<p>id:${jmlid}</p><p>temps:${d.temps}</p><p>nb:<b>${d.nb}</b></p>`
                    }
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