var widthPpal =  d3.select("#affichage").node().getBoundingClientRect().width,
    heightPpal = d3.select("#affichage").node().getBoundingClientRect().height,
    heightAction = 100, //hauteur de la vue globale des actions (+actionSvg.attr("height"));
    heightArbre=350, //hateur de la vue arbre
    heightAxis=50;

var context, //le svg principal
    focus, //le svg global de zoom
    treeBlocks, //le svg pour l'affichage des spr
    etapeBlocks; //le svg pour les étapes

var brushX=d3.brushX();
var brush=brushX.extent([[0, 0], [widthPpal, 50]])
    .on("brush end", brushed);
 
var zoom = d3.zoom()
    .scaleExtent([1, Infinity])
    .translateExtent([[0, 0], [widthPpal, 300]])
    .extent([[0, 0], [widthPpal, 300]])
    .on("zoom", zoomed);   

initSvg();
initListeEleves();


function initSvg() {
    //initialise les svg de base
    context=ActionsLine(options={xAxisPos: "middle",width:widthPpal,height:heightAction});
    focus = ActionsLine(options={xAxisPos: "down",width:widthPpal,xAxisHeight:50,height:heightPpal})
    etapeBlocks=EtapeBlocks({height:((heightPpal-heightAxis)/2-10)});
    treeBlocks=TreeBlocks({height:((heightPpal-heightAxis)/2-10)})
    eprBlocks=EPRBlocks({height:((heightPpal-heightAxis)/2-10)})
    focus.detail(
	function (selection) {
  //ajout des gradients
  //console.log("sel",selection,this)
        var gradientPair = selection
        .append("linearGradient")
        .attr("y1", 0) //height-xAxisHeight
        .attr("y2", 0)
        .attr("x1", "0")
        .attr("x2", 150)
        .attr("id", "gradientPair")
        .attr("gradientUnits", "userSpaceOnUse");
    gradientPair
        .append("stop")
        .attr("offset", "0")
        .attr("stop-color", "green")
        .attr("stop-opacity", "0.7");
    gradientPair
        .append("stop")
        .attr("offset", "1")
        .attr("stop-opacity", "0");
  selection.append("rect")
  				.attr("class","gradient")
          .attr("width",150)
          .attr("height",20)
          .attr("opacity",0.5)
          //.attr("fill","brown")
        selection.append("text")
        	.attr("dy","1em")
          .attr("dx","0.5em")
        	.text(d=>d.type_display)
        selection.append("circle")
        	.attr("r",10)
          .attr("cy",10)
          .attr("opacity",0.5)
        selection.on("click",function(d) {console.log("click",d)})
  }
)
    
}

function initListeEleves() {
    //initialisation de la liste des élèves
    console.log('initialiation')
    d3.json('spropen/users', function (error, data) {
        console.log("reception", data);
        data.unshift({
            id: 0
        })
        var el = d3.select('#selectEleves')
        el.selectAll("option").data(data).enter().append("option").attr(
            "value",
            function (d) {
                return d.id
            }).text(
            function (d) {
                return d.id == 0 ? "---" : (d.username + "(" +
                    (d.eleve ? d.eleve.classe : 'prof') + ")")
            })        
        el.on("change", initSessions)
    });
}

function initSessions() {
    //récupération de la liste des sessions
    var selectedValue = d3.select("#selectEleves").property('value')
    if (selectedValue != 0)
        d3.json('spropen/' + selectedValue + "/openUser",
            function (error, data) {
                console.log('data session', data);
                data.unshift({
                    id: 0
                })
                var session = d3.select('#selectSessions')
                session.selectAll("option").data(data, function (d) {
                    return d.id
                }).enter().append("option").attr("value", function (d) {
                    return d.id
                }).text(
                    function (d) {
                        return d.id == 0 ? "---" : ((new Date(
                                d.evenement.creation)).toUTCString() +
                            "(" + d.evenement.user + ")")
                    })
                session.on("change", chargeSession)
                session.selectAll("option").data(data, d=>d.id).exit().remove()
            });
}

function chargeSession() {
    var selectedValue = d3.select("#selectSessions").property('value')
    getJson(selectedValue);
}

function tooltip(selection,html,duration=200) {
    //affichage d'un tooltip sur la selection
    //usage: selection.call(tooltip,"texte html" [,durée])
    var divTooltip = d3.select("#tooltip").attr("class", "tooltip").style("opacity", 0);
    console.log("html!",html,"select",selection)
     return selection.on(
         "mouseover",
         function (d) {
             divTooltip.transition()
                 .duration(duration).style("opacity", .9);
             divTooltip
                 .html(html)
                 .style("left", (d3.event.pageX) + "px")
                 .style("top", (d3.event.pageY - 28) + "px");
         }).on(
         "mouseout",
         "mouseout",
         function (d) {
             divTooltip.transition()
                 .duration(500).style("opacity", 0);
         });
}

var idex=0; //pour id data
function getJson(session) {
    if (session != 0) {
        console.log('session', session)
        d3
            .json(
                "tb/" + session,
                function (error, data) {
                    if (error) {
                        console.warn("error", error.type, ":",
                            error.target.statusText)
                        return

                    }
                    /* on prépare les ticks en enlevant le temps 0
  * et en rajoutant les temps min-5mn,max+5mn (300000 ms)
  */
  var ticks=data.ticks.filter(d=>d>0)
  var ex=d3.extent(ticks)
  ticks.push(ex[0]-300000,ex[1]+300000)
  
  context.data(data.actions)  		
  	.linear(ticks).tickValues(ticks)
  
  var sc=d3.scaleThreshold()
  	.domain()
  focus.data(data.actions)  		
  	.linear(ticks)
  
  data.ticks.forEach(function(n){console.log(n,"=>",context.scale()(n))})
  var svgFocus=d3.select("#affichage").append("svg")
  		.attr("width",widthPpal)
      .attr("height",heightPpal)
      .call(focus)
  var svgContext=d3.select("#actions").call(context)
  //console.log("context range", context.scale().range(),d3.extent( context.scale().range()))
  console.log("actions",data)
  treeBlocks.data(data.data)
  	.links(data.links)
    .ticks(ticks)
    .scale(focus.scale())
    .label(d => d.blockSpec?d.blockSpec:d.contenu).posx(0);  
 etapeBlocks.data(data)
    .ticks(ticks)
    .scale(focus.scale())
    .label(d => d.time).posx(0);    
 eprBlocks.data(data.actions.filter(d=>d.evenement.type=="EPR"))
    .ticks(data.actions.map(d=>d.evenement.time).filter(d=>d>0)) 
    .scale(focus.scale())
     
 var svgTb=svgFocus.append("svg")
 svgTb.call(treeBlocks)
 svgTb.call(eprBlocks)
 //focus.svg().call(treeBlocks)                    
 //svgTb.attr("transform","translate(0,200)")  
 var svgEt=svgFocus.append("svg")
 svgEt.call(etapeBlocks)
 svgTb.attr("transform","translate(0,"+((heightPpal-heightAxis)/2+20)+")")     
 
if (context.svg().select(".brush").empty()) {                
  context.svg()
      .append("g")
      .attr("class", "brush")  
      .call(brush)
      .call(brush.move, d3.extent( context.scale().range()));
   
  focus.svg().insert("rect",":first-child")//append("rect")
      .attr("class", "zoom")
      .attr("width", focus.width())
      .attr("height", focus.height())
      .call(zoom);
} else {
   context.svg().select("g.brush")
      .call(brush.move, d3.extent( context.scale().range()));
}
 
  window.setTimeout(function() {
    context.tickValues(null)
  }, 5000)
                    
})
    }
}



function brushed() {	
  if (d3.event.sourceEvent && d3.event.sourceEvent.type === "zoom") return; // ignore brush-by-zoom
  var s = d3.event.selection || d3.context.scale().range();	
  focus.scale().domain(s.map(context.scale().invert,context.scale()))
  treeBlocks.scale().domain(s.map(context.scale().invert,context.scale()))
  etapeBlocks.scale().domain(s.map(context.scale().invert,context.scale()))
  eprBlocks.scale().domain(s.map(context.scale().invert,context.scale()))
  focus.update();
  treeBlocks.update();
  etapeBlocks.update();
  eprBlocks.update();
  focus.svg().select(".zoom").call(zoom.transform, d3.zoomIdentity
      .scale(focus.width() / (s[1] - s[0]))
      .translate(-s[0], 0));
}

function zoomed() {
  if (d3.event.sourceEvent && d3.event.sourceEvent.type === "brush") return; // ignore zoom-by-brush  
  var t = d3.event.transform;
  focus.scale().domain(t.rescaleX(context.scale()).domain());
  focus.update();
  treeBlocks.scale().domain(t.rescaleX(context.scale()).domain());
  treeBlocks.update();
  etapeBlocks.scale().domain(t.rescaleX(context.scale()).domain());
  etapeBlocks.update();
  eprBlocks.scale().domain(t.rescaleX(context.scale()).domain());
  eprBlocks.update();
  context.svg().select(".brush").call(brush.move, focus.scale().range().map(t.invertX, t));
  
  
}