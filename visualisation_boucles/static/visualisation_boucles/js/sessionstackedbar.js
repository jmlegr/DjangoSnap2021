export {initSessionStackedBarChart}
var initSessionStackedBarChart = {
    draw: function(config) {
        var me = this,
        d3Ele = config.element,
        stackKey = config.key.sort(),
        data = config.data,
        boucles=config.boucles, //tableau des premières boucles trouvées par session
        sep=config.separator || '_', //separateur type_datatype passé en key
        liste=d3.map(config.liste,d=>d.session_key), //liste des infos de session, map de clef session_key
        margin = {top: 20, right: 20, bottom: 130, left: 50},
        parseDate = d3.timeParse("%m/%Y"),
        width = d3Ele.node().getBoundingClientRect().width - margin.left - margin.right,
        height = 600 - margin.top - margin.bottom,
        xScale = d3.scaleBand().range([0, width]).padding(0.1),
        yScale = d3.scaleLinear().range([height, 0]),
        //color = d3.scaleOrdinal(d3.schemeCategory10),        
        xAxis = d3.axisBottom(xScale).tickFormat(d=>liste.get(d).user_nom+' '+d.slice(0,1)),            
        yAxis =  d3.axisLeft(yScale)
        
        //calcul des couleurs, sur la base type_datatype
        //chaque type dans le même schemecolor
        //3 types prévus
        const reducer=(accumulator,currentValue)=>{
            if (accumulator[currentValue.split(sep)[0]])
                accumulator[currentValue.split(sep)[0]]+=1
            else
                accumulator[currentValue.split(sep)[0]]=1
            return accumulator
        }
        const nbType=stackKey.reduce(reducer,{})
        let blues=[], greens=[], purples=[] //blues pour ENV, greens EPR purples SPR
        for (var i=1;i<=nbType['ENV'];i++) blues.push(d3.interpolateBlues((i+5)/(nbType['ENV']+8)))
        for (var i=1;i<=nbType['EPR'];i++) greens.push(d3.interpolateGreens((i+5)/(nbType['EPR']+8)))
        for (var i=1;i<=nbType['SPR'];i++) purples.push(d3.interpolatePurples((i+5)/(nbType['SPR']+8)))
        blues=blues.reverse()
        greens=greens.reverse()
        purples=purples.reverse()
        /*
        var color=d3.scaleOrdinal()
        .unknown("#ccc")
        .domain(stackKey.sort())
        .range(d3.quantize(t => d3.interpolateSpectral(t * 0.8 + 0.1),stackKey.length).reverse())
        */
        var color=d3.scaleOrdinal(blues.concat(greens).concat(purples))
        d3Ele.attr("width", width + margin.left + margin.right+10)
            .attr("height", height + margin.top + margin.bottom+10)
        var svg = d3Ele.append("svg")
                .attr("width", width + margin.left + margin.right)
                .attr("height", height + margin.top + margin.bottom)
                .append("g")
                .attr("transform", "translate(" + margin.left + "," + margin.top + ")");
        //console.log('liste',liste)
        var ntx=crossfilter(data),
            sdim=ntx.dimension(d=>d.session_key), //session dimension
            countSession=sdim.group().reduceCount(), //nb d'evenements de chaque session
            tdim=ntx.dimension(d=>d.datatype), // type dimension
            countType=tdim.group().reduceCount(),// nombre d'evenement de type t sur toutes les sessions
            countBySession=sdim.group().reduce(
                    function(p, v) {//add
                        p[v.datatype]=(p[v.datatype]||0)+1                                     
                        return p;
                    },
                    function(p, v) {//remove
                        p[v.datatype]=(p[v.datatype]||0)-1
                        return p;
                    },
                    function(p) {//initial
                        p={};
                        return p;
                    }
            )
            
    var zdata=()=> countBySession.top(Infinity).map(d=>{
        var a={};
      a.session=d.key
      a.total=0
      for (var v in d.value) {
        a[v]=d.value[v]
        a.total+=d.value[v]
      }
      return a
      })
      
    //console.log('map',data,zdata(),stackKey)
   // console.log('boucles',boucles)
      //fonction de tracé du graphique
      const trace=svg1=>{
          //on  filtre l'affichage des types          
          tdim.filter(type=>svg1.selectAll("[notselected]").data().indexOf(type)==-1)
                    
          var stack = d3.stack()
          .keys(stackKey.sort())
          .order(d3.stackOrderNone)
          // .order(d3.stackOrderDescending)
          .offset(d3.stackOffsetNone);
  
          var layers= stack(zdata())
          //data.sort(function(a, b) { return b.s - a.s; });
          xScale.domain(zdata().map(function(d) { return d.session; }));          
          //recherche du y max
          var maxi=0
          layers.forEach(l=>{
              let m=d3.max(l,function(d){return d[1]?d[1]:0});             
              if (m>maxi) maxi=m})
          yScale.domain([0, maxi+1]).nice();
          
          svg1.select("#stackedchart").remove()
          
          var svg=svg1.append("g").attr("id","stackedchart")
          var layer = svg.selectAll(".layer")
              .data(layers)
              .enter().append("g")
              .attr("class", "layer")
              .style("fill", function(d, i) { return color(d.key); })
        
            var rectSel=layer.selectAll("g.evt")
                .data(function(d) { return d; })
                .enter()
                .append("g").attr("class",'evt')
                .classed('noboucle',d=>boucles[d.data.session]==null)
                .classed('boucle',d=>boucles[d.data.session]!=null)
            rectSel.append("rect")
                  //.classed('noboucle',d=>boucles[d.data.session]==null)
                  //.classed('boucle',d=>boucles[d.data.session]!=null)
                .attr("x", function(d) { return xScale(d.data.session); })
                .attr("y", function(d) { return yScale(d[1]); })
                .attr("height", function(d) { return yScale(d[0]) - yScale(d[1]); })
                .attr("width", xScale.bandwidth())
            rectSel.append("line")
                .attr("class","evtline")
                .attr("x1",d=>xScale(d.data.session))
                .attr("y1",d=>yScale(d[0]))
                .attr("x2",d=>xScale(d.data.session))
                .attr("y2",d=>yScale(d[1]))
                .attr("stroke-width",d=>d[1]>d[0]?Math.min(5,xScale.bandwidth()/5):0)
            var nb=svg.selectAll(".nb").data(layers)
                    .enter()
                    .append("text")
                    .attr("class","nb")
                    .text(d=>{console.log('lai',d); return "oi"})
          svg.selectAll(".layer").each(function(p,j,g){
              d3.select(this)
              .selectAll("rect")
              .each(function(d,e,f){
                  tippy(this,{content:
                      liste.get(d.data.session).user_nom+"<p>"+p.key+":"+(d[1]-d[0])+"</p>", arrow: true,})
                  }
              )            
          })
         
          var rectboucle=svg.selectAll(".rectboucle").data(zdata()).enter()
              .append("g")
              .attr("class",d=>"rectboucle "+ (boucles[d.session]?"boucle":"noboucle"))
              .attr("transform",function(d,i) {return "translate("+xScale(d.session)+","+(yScale(d.total)-15)+")"})
          rectboucle
              .append("rect")
              .attr("class",d=>"rectboucle "+ (boucles[d.session]?"boucle":"noboucle"))
              .attr("width",25)
              .attr("height",15)
          rectboucle
              .append("text")
              .attr("x",0)
              .attr("y",10)
              .text(d=>d.total)
          rectboucle
              .append("title").text(d=>{
                  if (boucles[d.session]) {
                      return "Boucle trouvée "+boucles[d.session].blockSpec+"\n"
                              +"total: "+d.total
                  }
                  return "total: "+d.total})
              
         tippy(".evtline", {content:"tipp",
             async onShow(tip) {
                 //console.log('tip',liste.get(d3.select(tip.reference).datum().data.session))
                 tip.setContent(liste.get(d3.select(tip.reference).datum().data.session).loads)
         }})
            
            
              svg.append("g")
              .attr("class", "axis axis--x")
              .attr("transform", "translate(0," + (height+5) + ")")
              .call(xAxis);

              svg.append("g")
              .attr("class", "axis axis--y")
              .attr("transform", "translate(0,0)")
              .call(yAxis);       
              
    
      }
      //tracé de la legende
             const defaultVisible=[
                 "ENV_DROPEX","ENV_DUPLIC","ENV_REDROP","ENV_UNDROP",
                 "SPR_DEL","SPR_DROP","SPR_NEW","SPR_UNDROP","SPR_VAL"                 
             ]
            const legend = svg => {
                const g = svg
                    .attr("font-family", "sans-serif")
                    .attr("font-size", 10)
                    .attr("text-anchor", "start")
                  .selectAll("g.legend")
                  .data(stackKey)
                  .enter().append("g").attr("class","legend")
                    //.attr("transform", (d, i) => `translate(${width},${i * 20})`);
                  .attr("transform", (d, i) => `translate(${Math.floor(i/5)*100},${height+30+(i%5) * 20})`);
                g.append("rect")
                    .attr("x", 0)
                    .attr("width", 19)
                    .attr("height", 19)
                    .attr("fill", color)
                    .attr("notselected",d=>defaultVisible.indexOf(d)>-1?null:1)
                    .on("click",function(d,i){
                        const el=d3.select(this)
                        el.attr("notselected",el.attr("notselected")?null:1)
                        trace(svg)
                        }
                    )

                g.append("text")
                    .attr("x", 24)
                    .attr("y", 9.5)
                    .attr("dy", "0.35em")
                    .text(d => d)
                    .attr("selected",true)
              }
            
            legend(svg)
            trace(svg)
    }
}