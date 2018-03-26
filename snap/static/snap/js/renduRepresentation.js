var widthPpal=1000,
    heightPpal=500;

var affichageSvg=d3.select("#affichage").append("svg")        
		.attr("id", "affichageSvg")
		.attr("width", widthPpal) // + margin.left + margin.right)
		.attr("height", heightPpal)
		.attr("class", "graph-svg-component"),     // l'affichage arbre+script
    arbreSvg, // afficahge arbre
    
    actionSvg=d3.select("#actions").append("svg")
    	.attr("class","actions")
	.attr("id","actionSvg")
	.attr("width",1000)
	.attr("height",100), //affichage actions
    margin = {top: 20, right: 20, bottom: 110, left: 40}, //pour arbre
    margin2 = {top: 430, right: 20, bottom: 30, left: 40}, //pour scripts
    width = +affichageSvg.attr("width") - margin.left - margin.right,
    height = +affichageSvg.attr("height") - margin.top - margin.bottom,
    height2 = +affichageSvg.attr("height") - margin2.top - margin2.bottom;

var x=d3.scaleTime().range([0,width]),
    x2=d3.scaleTime().range([0,width]);

var xaxis=d3.axisBottom(x),
    xaxis2=d3.axisBottom(x2);
    
var brush = d3.brushX()
    .extent([[0, 0], [width, height2]])
    .on("brush end", brushed);

var zoom = d3.zoom()
.scaleExtent([1, Infinity])
.translateExtent([[0, 0], [width, height]])
.extent([[0, 0], [width, height]])
.on("zoom", zoomed);

affichageSvg.append("defs").append("clipPath")
	.attr("id", "clip")
	.append("rect")
	.attr("width", width)
	.attr("height", height);

var arbreSvg = affichageSvg.append("g")
	.attr("class", "arbre")
	.attr("transform", "translate(" + margin.left + "," + margin.top + ")")
var scriptSvg=affichageSvg.append("g") //affichage scripts 
	.attr("class", "scripts")
	.attr("transform", "translate(" + margin2.left + "," + margin2.top + ")")





function brushed() {
    if (d3.event.sourceEvent && d3.event.sourceEvent.type === "zoom") return; // ignore brush-by-zoom
    var s = d3.event.selection || x2.range();
    x.domain(s.map(x2.invert, x2));
    focus.select(".area").attr("d", area);
    focus.select(".axis--x").call(xAxis);
    svg.select(".zoom").call(zoom.transform, d3.zoomIdentity
        .scale(width / (s[1] - s[0]))
        .translate(-s[0], 0));
  }

  function zoomed() {
    if (d3.event.sourceEvent && d3.event.sourceEvent.type === "brush") return; // ignore zoom-by-brush
    var t = d3.event.transform;
    x.domain(t.rescaleX(x2).domain());
    focus.select(".area").attr("d", area);
    focus.select(".axis--x").call(xAxis);
    context.select(".brush").call(brush.move, x.range().map(t.invertX, t));
  }