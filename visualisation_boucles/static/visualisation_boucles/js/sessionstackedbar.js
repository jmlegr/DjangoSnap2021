export {initSessionStackedBarChart}
var initSessionStackedBarChart = {
    draw: function(config) {
        var me = this,
        d3Ele = config.element,
        stackKey = config.key,
        data = config.data,
        boucles=config.boucles, //tableau des premières boucles trouvées par session
        liste=d3.map(config.liste,d=>d.session_key), //liste des infos de session, map de clef session_key
        margin = {top: 20, right: 20, bottom: 30, left: 50},
        parseDate = d3.timeParse("%m/%Y"),
        width = 960 - margin.left - margin.right,
        height = 500 - margin.top - margin.bottom,
        xScale = d3.scaleBand().range([0, width]).padding(0.1),
        yScale = d3.scaleLinear().range([height, 0]),
        color = d3.scaleOrdinal(d3.schemeCategory10),
        xAxis = d3.axisBottom(xScale).tickFormat(d=>liste.get(d).user_nom+'\n'+d.slice(0,5)),            
        yAxis =  d3.axisLeft(yScale)
        d3Ele.attr("width", width + margin.left + margin.right+10)
            .attr("height", height + margin.top + margin.bottom+10)
        var svg = d3Ele.append("svg")
                .attr("width", width + margin.left + margin.right)
                .attr("height", height + margin.top + margin.bottom)
                .append("g")
                .attr("transform", "translate(" + margin.left + "," + margin.top + ")");
        console.log('liste',liste)
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
    var zdata=countBySession.top(Infinity).map(d=>{
        var a={};
      a.session=d.key
      for (var v in d.value) {
        a[v]=d.value[v]
      }
      return a
      })
    //console.log('map',data,zdata,stackKey)
    //console.log('boucles',boucles)
        var stack = d3.stack()
            .keys(stackKey.sort())
            .order(d3.stackOrderNone)
            // .order(d3.stackOrderDescending)
            .offset(d3.stackOffsetNone);
    
        var layers= stack(zdata)
            //data.sort(function(a, b) { return b.s - a.s; });
            xScale.domain(zdata.map(function(d) { return d.session; }));
        console.log("layers",layers)
        //recherche du y max
        var maxi=0
        layers.forEach(l=>{let m=d3.max(l,function(d){return d[1]?d[1]:0}); if (m>maxi) maxi=m})
        yScale.domain([0, maxi]).nice();
        var layer = svg.selectAll(".layer")
            .data(layers)
            .enter().append("g")
            .attr("class", "layer")
            .style("fill", function(d, i) { return color(i); })
      
          var rect=layer.selectAll("rect")
              .data(function(d) { return d; })
            .enter().append("rect")
                .classed('noboucle',d=>boucles[d.data.session]==null)
                .classed('noboucle',d=>boucles[d.data.session]!=null)
              .attr("x", function(d) { return xScale(d.data.session); })
              .attr("y", function(d) { return yScale(d[1]); })
              .attr("height", function(d) { return yScale(d[0]) - yScale(d[1]); })
              .attr("width", xScale.bandwidth())
        
        svg.selectAll(".layer").each(function(p,j,g){
            d3.select(this)
            .selectAll("rect")
            .each(function(d,e,f){
                tippy(this,{content:p.key+":"+(d[1]-d[0]), arrow: true,})
            })
            
        })
      
            svg.append("g")
            .attr("class", "axis axis--x")
            .attr("transform", "translate(0," + (height+5) + ")")
            .call(xAxis);

            svg.append("g")
            .attr("class", "axis axis--y")
            .attr("transform", "translate(0,0)")
            .call(yAxis);                           
    }
}