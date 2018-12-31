export {initSessionStackedBarChart}
var initSessionStackedBarChart = {
    draw: function(config) {
        var me = this,
        domEle = config.element,
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
        //xAxis = d3.axisBottom(xScale).tickFormat(d3.timeFormat("%b")),
        xAxis = d3.axisBottom(xScale).tickFormat(d=>liste.get(d).user_nom+'\n'+d.slice(0,5)),            
        yAxis =  d3.axisLeft(yScale),
        svg = d3.select("#"+domEle).append("svg")
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
    console.log('map',data,zdata,stackKey)
    console.log('boucles',boucles)
        var stack = d3.stack()
            .keys(stackKey)
            .order(d3.stackOrderNone)
            .offset(d3.stackOffsetNone);
    
        var layers= stack(zdata);
    //console.log(layers)
            //data.sort(function(a, b) { return b.s - a.s; });
            xScale.domain(zdata.map(function(d) { return d.session; }));
      //console.log("xsca le",zdata.map(function(d) { return d.session; }))
      //xScale.domain(['a','b','c'])
            yScale.domain([0, d3.max(layers[layers.length - 1], function(d) { return d[0] + d[1]; }) ]).nice();
        console.log("stack",layers)
        var layer = svg.selectAll(".layer")
            .data(layers)
            .enter().append("g")
            .attr("class", "layer")
            .style("fill", function(d, i) { console.log('color',d.key,i);return color(i); })
        //layer.append("title").text((d,v,k)=>{console.log("d",d,v,k); return d.key+"("+d.index+")"})
    //layer.on("mouseover",function(d,v,k) {
    //  console.log("over",d,v,k)
    //})
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
            //.append("title").text(d=>p.key+":"+(d[1]-d[0]))        
        })
        
       //rect
        //.append("title").text((d,k,v)=>console.log("text",d[1]-d[0],d3.select(rect.parentElement).datum()))
       // .on("mouseover",function(d,v,k) {console.log("over",d[1]-d[0],d3.select(this.parentElement).datum()['key'])})
                //.append("title").text(d=>d3.select(this.parentElement).datum()['key']+": "+(d[1]-d[0]))
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