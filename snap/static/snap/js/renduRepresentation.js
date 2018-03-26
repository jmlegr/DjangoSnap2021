var widthPpal=1000,
    heightPpal=500;
var divTooltip = d3.select("body").append("div")   
.attr("class", "tooltip")               
.style("opacity", 0);
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

var x=d3.scaleLinear().range([0,width]),
    x2=d3.scaleLinear().range([0,width]);

var xAxis=d3.axisBottom(x),
    xAxis2=d3.axisBottom(x2);
    
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

initListeEleves();
// on initialise les axes et le brush
actionSvg.append("g")
	.attr("class", "axis actionNode")
	.attr("transform", "translate(0," + 50 + ")")
	.call(xAxis2);
actionSvg
	.append("g")
	.attr("class", "brush actionNode")
	.call(brush)
	.call(brush.move, x.range());
function initListeEleves() {
    console.log('initialiation')
    d3.json('spropen/users', function (error, data) {
        console.info("reception liste elveves");
        console.log("reception", data);
        data.unshift({
            id: 0
        })
        var el = d3.select('#selectEleves')
        el.selectAll("option").data(data)
            .enter()
            .append("option")
            .attr("value", function (d) {
                return d.id
            })
            .text(function (d) {
                return d.id == 0 ? "---" : (d.username + "(" + (d.eleve ? d.eleve.classe : 'prof') + ")")
            })
        el.on("change", changeEleve)

    });
}

function changeEleve() {
    // var
    // selectedIndex=d3.select("#selectEleves").property('selectedOptions')[0].value
    var selectedValue = d3.select("#selectEleves").property('value')
    /*
     * var s=d3.select("#selectEleves").selectAll("option").filter(function
     * (d,i) { return d.id==selectedValue}), data=s.datum()
     * console.log('eke',data)
     */
    if (selectedValue != 0)
        d3.json('spropen/' + selectedValue + "/openUser", function (error, data) {
            console.log('data session', data);
            data.unshift({
                id: 0
            })
            var session = d3.select('#selectSessions')
            session.selectAll("option").data(data, function (d) {
                    return d.id
                })
                .enter()
                .append("option")
                .attr("value", function (d) {
                    return d.id
                })
                .text(function (d) {
                    return d.id == 0 ? "---" : ((new Date(d.evenement.creation)).toUTCString() + "(" + d.evenement.user + ")")
                })
            session.on("change", changeSession)
            // session.selectAll("option").call(function(d){console.log('update',d)})
            session.selectAll("option").data(data, function (d) {
                return d.id
            }).exit().remove()
        });
}

function changeSession() {
    var selectedValue = d3.select("#selectSessions").property('value')
    console.log('evnoi', selectedValue)
    getJson(selectedValue);
}

function getLastParentId(node) {
    // renvoie l'id du noeud parent s'il existe,
    // ou l'id du noeud parent temporellement précédent s'il existe
    // ou l'id de la racine
    nodeId = node.conteneurBlock == null ? node.parentBlock : node.conteneurBlock
    if (nodeId != null) {
        n = donnees
            .filter(function (d) {
                return d.time <= node.time && (d.id == nodeId || d.JMLid == nodeId.split('_', 1)[0])
            })
            .sort(function (a, b) {
                return a.time - b.time
            })
            .pop()
        return n == undefined ? 'racine' : n.id
    }
    return null
}

function getJson(session) {
    if (session != 0) {
        console.log('session', session)
        d3.json("tb/" + session, function (error, data) {
            if (error) {
                console.warn("error", error.type, ":", error.target.statusText)
                return
            }
            /*
             * preparation des donnees: tous les blocks au temps 0, avec ajout
             * d'une racine fictive ajouts des blocks contenus en enfant des
             * blocks contenant
             */
            console.log('donnee recoes', data)
            donnees = data.data            
            ticks = data.ticks
            links = data.links
            actions = data.actions
            x.domain(d3.extent(actions, function(d) { return d.evenement.time; }));
            x2.domain(x.domain());
           
            
            actionNode=actionSvg
    		.selectAll(".actionLine")
    		.data(actions, function (d) { return d.id || (d.id = ++i)})
    	    actionSvg.selectAll("g.axis")
    	    	.attr("class", "axis actionNode")
    	    	.attr("transform", "translate(0," + 50 + ")")
    	    	.call(xAxis2);
            
            actionNode
        	.enter()
        	.append("line")
        	.attr("class",function (d) {return "actionLine "+d.evenement.type})            	
        	.attr("x1",function(d) {return x2(d.evenement.time)})
        	.attr("x2",function(d) {return x2(d.evenement.time)})
        	.attr("y1",-100)
        	.attr("y2",actionSvg.attr("height"))
        	.on("mouseover", function(d) {      
        	    divTooltip.transition()        
        	    	.duration(200)      
        	    	.style("opacity", .9);      
        	    divTooltip.html(d.evenement.type_display + "<br/>"  + d.type_display)  
        	    	.style("left", (d3.event.pageX) + "px")     
        	    	.style("top", (d3.event.pageY - 28) + "px");    
        		})                  
        	.on("mouseout", function(d) {       
        	    divTooltip.transition()        
        	    	.duration(500)      
        	    	.style("opacity", 0);   
        	});
            actionNode.exit().remove()
            
            actionSvg
            	.selectAll("g.brush")
            	.attr("class", "brush actionNode")
            	.call(brush)
            	.call(brush.move, x.range());
            affichageSvg.append("rect")
            .attr("class", "zoom")
            .attr("width", width)
            .attr("height", height)
            .attr("transform", "translate(" + margin.left + "," + margin.top + ")")
            .call(zoom);
        })
    }
}

function brushed() {
    if (d3.event.sourceEvent && d3.event.sourceEvent.type === "zoom") return; // ignore brush-by-zoom
    var s = d3.event.selection || x2.range();
    x.domain(s.map(x2.invert, x2));
    //focus.select(".area").attr("d", area);
    //focus.select(".axis--x").call(xAxis);
    affichageSvg.select(".zoom").call(zoom.transform, d3.zoomIdentity
        .scale(width / (s[1] - s[0]))
        .translate(-s[0], 0));
  }


function zoomed() {
    if (d3.event.sourceEvent && d3.event.sourceEvent.type === "brush") return; // ignore zoom-by-brush
    var t = d3.event.transform;
    x.domain(t.rescaleX(x2).domain());
    //focus.select(".area").attr("d", area);
    //focus.select(".axis--x").call(xAxis);
    actionSvg.select(".brush").call(brush.move, x.range().map(t.invertX, t));
  }