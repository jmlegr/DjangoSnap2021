function EtapeBlocks(options={}) {
/**
* reconstruit et affiche les scripts à chaque étape
*/
  var width = options.width || 800,
    height = options.height || 400,
    barHeight = options.barHeight || 15,
    barWidth =options.barWidth ||  50,
    decalFirst = 20, //premiere ligne
    decalx = options.decalx|| 5, //decalage latéral pour un enfant
    _decalx= function(parentNode,inputNode) {
    					if (typeof decalx === "function") {
               return decalx(parentNode,inputNode)
              }   		
              return decalx
              },
    posx=options.posx || barWidth/2, // position x du label 
    classEtape = options.classEtape || "etape",
    classBloc = options.classBloc || "bloc",
    classScript=options.classScript || "script",
    classLabel = options.classLabel || "label",
    classIdBloc = options.classIdBloc || classBloc, //forme classIdBloc_temps_n°
  	xscale=options.scale || d3.scaleLinear();
    
  var label = options.label || function(d) {
    return d.id
  }; //contenu du texte
  var color = options.color || function(d) { //
    switch (d.typeMorph) {
      case "InputSlotMorph":
        return "#fd8d3c";
      case "ReporterBlockMorph":
        return "green";
      case "CSlotMorph":
        return "#3182bd";
      case "CommandBlockMorph":
        return "#c6dbef";
      default:
        return "pink";
    }
  };
  
  var dataObject,
  		links=[],
      ticks=[];
  var racines, blocs;
  var update;
  var svg;
	function xpos(node) {
  	//renvoie la position à l'échelle du node, avec décalage
    if (node && typeof node==="object") {
    		return xscale(node.time)+(node.dx?node.dx:0)
        }
    if (node) {
    //c'est un temps
    return xscale(node)
    }
  }
  function widthTicks(node) {
   //calcule la largeur maxi disponible entre 2 ticks
		if (node) {
			if (typeof node ==="object")
   				return xpos(ticks[ticks.indexOf(+node.time)+1])-xpos(node.time)
      else
      		return xpos(ticks[ticks.indexOf(+node)+1])-xpos(node)
   }
  }
  
  function xClippedPos(node,decalage=0) {
  	//calcule la position en tenant compte du clipage    
    if (node && typeof node === "object")
    	return Math.min(xpos(node)+decalage,xpos(node.time)+widthTicks(node))
    return Math.min(xpos(node)+decalage,xpos(node)+widthTicks(node))
    }

  
	function createBloc(selection) {
  	//cré les blocs    
     // ajout du titre
     var tp=d3.timeFormat("%Mm:%Ss");
     selection.append("rect").attr("class","label").attr("width",250).attr("height",barHeight)
     selection.append("text").attr("class","label").attr("dy",barHeight/2).text(d=>tp(d.time))
     
       /*
       définition des gradients
       */
                    var gradientPair = svg.append(
                        "linearGradient").attr("y1", 0).attr("y2",
                        0).attr("x1", "0").attr("x2", "50").attr(
                        "id", "etapeGradientPair").attr("gradientUnits",
                        "userSpaceOnUse");
                    gradientPair.append("stop").attr("offset", "0")
                        .attr("stop-color", "green").attr(
                            "stop-opacity", "0.5");
                    gradientPair.append("stop").attr("offset", "1")
                        .attr("stop-opacity", "0");

                    var gradientImpair = svg.append(
                        "linearGradient").attr("y1", 0).attr("y2",
                        0).attr("x1", "0").attr("x2", "50").attr(
                        "id", "etapeGradientImpair").attr(
                        "gradientUnits", "userSpaceOnUse");
                    gradientImpair.append("stop").attr("offset", "0")
                        .attr("stop-color", "blue").attr(
                            "stop-opacity", "0.5");
                    gradientImpair.append("stop").attr("offset", "1")
                        .attr("stop-opacity", "0");
       //traitement du survol: on supprime le clippath
        selection.on("mouseenter",function(){
                	//console.log("enter script de",n.key)
                  d3.select(this).attr("clip-path","none" )  
                  update()
                  })
                .on("mouseleave",function() {
                	d3.select(this)
                    .attr("clip-path",d => "url(#" + classEtape +"_clip_"+d.time+")")
                  update()
                })
               
      //on ajoute la reconstruction des scripts
      selection.each(function(d,i){
      		var coms = d3.select(this)
          		.selectAll('.groupeetape')
              .data(d.commandes)
              .enter()
              .append("g")
              .attr("class", "groupeetape");
         coms.append("rect").attr(
              "class",function (d) {
                                    return ((d.index % 2 == 0) ? "pair" :
                                        "impair");
                                })
             .attr("y",function (d, j) {
                                    return j *barHeight + d.index *
                                        (barHeight / 2) +
                                        decalFirst
                                }).attr("x", function (d) {
                                return d.niveau * _decalx()
                            }).attr("width", 50).attr("height", barHeight)
                            //.attr("fill", "url(#gradient)");
                        coms.append('text').attr("class", "textetape ")
                            .attr("dy",
                                function (d, j) {
                                    return (j + 1) * barHeight +
                                        d.index *
                                        (barHeight / 2) +
                                        decalFirst
                                })
                             .attr("dx", function (d) {
                                return d.niveau * _decalx()
                            })
                            .text(function (e, j) {
                                return e.commande
                            })
      }
      )
    
          
  }
   
   function parent(el,classe) {
    //renvoi le parent dans le dom de classe "classe"
  			var element = el; // this points to the child element
  			while (!d3.select(element).classed(classe))
    						element = element.parentElement;
  			return element;
	}
  function getTranslate(selection) {
  	//renvoie les valeurs de translation [dx,dy]
    //ne fonctionne QUE s'il n'y a que une translation
    var s=selection.attr("transform")
    if (s ) {
   var r= s.substring(s.indexOf("(")+1, s.indexOf(")")).split(",");
   r[0]=+r[0]
   r[1]=+r[1]
   return r
   }
 return [0,0]
  }
  function chart(selection) {
    selection.each(function() {
    	if (!svg) {
      var typeSvg="svg"
     	if (d3.select(this).node().nodeName.toLowerCase()!="div") typeSvg="g"
      svg = d3.select(this)
        .append(typeSvg)
        .attr("width", width)
        .attr("height", height) 
      }    
      //préparation des scripts
      /*
      * 	on reconstruit les données sous la forme
      * 	[{time,action,commandes:[{index,scriptIt,numero,JMLid,niveau,commande}]}...]
      */
       var etapes = dataObject.etapes.map(function (d, index) {
                        a = []
                        for (var k in d.commandes) {
                            b = d.commandes[k]
                            for (var j in b) {
                                a.push({
                                    index: dataObject.scripts
                                        .indexOf(parseInt(k)),
                                    scriptId: parseInt(k),
                                    numero: j,
                                    id: b[j].id,
                                    niveau: b[j].niveau,
                                    commande: b[j].commande
                                })
                            }
                        }
                        return {
                            time: d.time,
                            action: d.action,
                            commandes: a
                        }
                    });
     
      //création  des "g" scripts par temps
      var scripts=svg.selectAll(".tousetapes")
          	 .data(etapes,d=>d.time)            
      var scriptsG=scripts.enter()
          								.append("g")
                          .classed("tousetapes",true)
     //on ajoute le clippath entre 2 ticks
     scriptsG
             .append("clipPath")
             .attr("class","clipg")
             .attr("id",d=>classEtape+"_clip_"+d.time)
             .append("rect")        			
             	//.attr("width",d=>widthTicks(+d.time)-1)
              .attr("width",30)
              .attr("height",height)
     //on ajoute le pan
    var zoomScripts=d3.zoom()
                    .scaleExtent([1,1])
                    .on("zoom",function() {                   
                      //on cache le tooltip (si besoin)              
                      d3.select("#tooltip")
                      	.transition().duration(100)
                        .style("opacity", 0);
                     //on assigne le transform à l'étape correspondante (seulement en y)    
                     var y=d3.event.transform.y;                     		
                    if (y<0) {
                    	//la dernière commande ne doit pas disparaitre
                      var  h= svg.select("#"+classEtape+"_"+this.getAttribute("id"))
                      				.node()
                              .getBBox().height //hauteur du bloc etape
                      var ty=Math.max((y),-(h-barHeight))
                      svg                                       
                    	.select("#"+classEtape+"_"+this.getAttribute("id"))   	                      
                      .attr("transform",d => 
                      "translate(0,"+ty+")")
                     } else {
                     //le titre ne doit pas disparaitre
                         var ty=Math.min((height-barHeight),(y))
                     svg                                       
                    	.select("#"+classEtape+"_"+this.getAttribute("id"))   	                      
                      .attr("transform",d => 
                      "translate(0,"+ty+")")                      
                     }
                    svg.select("#" + classEtape +"_clip_"+this.getAttribute("id")+" rect")
                         .attr("y",-ty)
                        
                    //svg.                        selectAll(".tousetapes").select(clipg rect")
          	           
                      //  .attr("y",-ty)
                                //return -getTranslate(d3.select(this))[1]
                                
                        //})

                    })
                    
          scriptsG          		
          	.append("rect")
            .attr("class","zoomNS")
            .attr("id",d=>d.time) //pour retourver l'étape g correspondante  
            .call(zoomScripts)            
          
    var etapeGEnter=scriptsG
        //.enter()
        .append("g")        
        .attr("class",classEtape)
        .attr("id",d=>classEtape+"_"+d.time)
        .attr("clip-path",d=>"url(#"+classEtape+"_clip_"+d.time+")")
			
      // creation des noeuds
      createBloc(etapeGEnter)
      
      update=function() {
       svg.selectAll(".tousetapes")
      	.data(etapes,d=> d.time)   .attr("transform",d=>"translate("+xpos(d)+",0)")
        svg.selectAll(".clipg rect")
          	 .data(etapes,d=>d.time)
             .attr("width",d=>widthTicks(+d.time)-10)
              .attr("height",height)
          
                    
        svg.selectAll(".zoomNS")
          		.data(etapes,d=>d.time)     
           		.attr("width",function(d){ 
              		var n=svg.select("#"+classEtape+"_"+d.time).node()
                  if (n)
              		  return Math.min(widthTicks(+d.time)-10,n.getBBox().width)
                  return widthTicks(+d.time)-10
                  })
            	.attr("height",height)
      }
      
      update()
     
  })
  }
	chart.update =function(all=false) {
  	if (typeof update==="function") update();    
  	}
  
  chart.data = function(value) {
    if (!arguments.length) return dataObject;
    dataObject = value;
    if (typeof update === 'function') {
      update();
    }
    return chart;
  };
  
  chart.ticks = function(value) {
    if (!arguments.length) return ticks;
    ticks = value.sort((a,b)=>a-b);
    if (typeof update === 'function') {
      update();
    }
    return chart;
  };
  
  chart.color = function(value) {
    if (!arguments.length) return color;
    color = value;
    //if (typeof color === 'function') color();
    return chart;
  };
  chart.width = function(value) {
    if (!arguments.length) return width;
    width = value;
    return chart;
  };
  chart.height = function(value) {
    if (!arguments.length) return height;
    height = value;
    return chart;
  };
  chart.label = function(value) {
    if (!arguments.length) return label;
    label = value;
    if (typeof updateLabel === 'function') updateLabel();
    return chart;
  };
  chart.posx = function(value) {
    if (!arguments.length) return posx;
    posx = value;
    if (typeof updateLabel === 'function') updateLabel();
    return chart;
  };
  chart.scale=function(value) {
  if (!arguments.length) return xscale;
  xscale=value;
  if (typeof update === 'function') {
      update();
    }
    return chart;
  }  
	chart.node=function() {
  	return svg;
  }
  return chart;
}