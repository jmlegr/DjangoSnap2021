
function TreeBlocks(options={}) {
  var width = options.width || 800,
    height = options.height || 400,
    barHeight = options.barHeight || 15,
    barWidth =options.barWidth ||  50,
    decalx = options.decalx|| 5, //decalage latéral pour un enfant
    _decalx= function(parentNode,inputNode) {
    					if (typeof decalx === "function") {
               return decalx(parentNode,inputNode)
              }   		
              return decalx
              },
    posx=options.posx || barWidth/2, // position x du label 
    classBloc = options.classBloc || "bloc",
    classScript=options.classScript || "script",
    classLabel = options.classLabel || "label",
    classLink = options.classLink || "link",
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
  var updateLabel, updateMove;
  var updateBlocks, updateLinks;
  var updateAll;
  var updateWidth;
  var dataObject,
  		links=[],
      ticks=[];
  var racines, blocs;
  
  var svg;
	function xpos(node) {
  	//renvoie la position à l'échelle du node, avec décalage
    if (node && typeof node==="object") {
    		return xscale(node.time)+node.dx
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
  function transforme(node) {
    //transforme un node avec id en node avec nodes
    function t(id) {
      nodeId = node[id]
      if (nodeId && typeof(nodeId) != "object") {
        cible = dataObject.find(d => d.id == nodeId)
        if (cible) node[id] = cible;
      }
    }

    t("parentBlock");
    t("conteneurBlock");
    t("prevBlock");
    t("nextBlock");
    if (node.inputs) node.inputs.forEach(function(i, index) {
      if (typeof(i) != "object") {
        n =dataObject.find(b => b.id == i)
        node.inputs[index] = n
      }
    })
    else node.inputs = []
    return node;
  }

  function prepareNodes() {
    //collecte les blocs "racine" à chaque temps, 
    //et transforme les blocsID en bloc
    dataObject.forEach(function(n) {
      transforme(n)
    });
    racines = {}
    ticks.forEach(function(temps) {
      racines[temps] = []
      dataObject.filter(d => d.time == temps).forEach(function(n) {
        //L3s blocs "racines" sont ceux n'ayant 
        // pas de parent, ni de conteneur, ni de précédent
        // ni de parent.conteneur.précedent d'un temps précédent
        isracine = n.parentBlock == null || n.parentBlock.time != n.time
        isracine &= n.conteneurBlock == null || n.conteneurBlock.time != n.time
        isracine &= n.prevBlock == null || n.prevBlock.time != n.time
        if (isracine) {
            racines[temps].push(n)            
        }
      })
    })
    // console.log("nodes",nodes,"racine",racines)
  }

  function positionneNodes(temps) {
    function t(node, dx, y, idBloc) {
      node.idBloc = classIdBloc + "_" + temps + "_" + idBloc
      node.dx = dx;
      node.y = y; //a changer pour bloc
      node.lasty = y + barHeight
      //traitement des intputs
         if (node.time!=temps) console.log("pas normal,",node)
      node.inputs.sort((a, b) => a.rang - b.rang)
        .forEach(function(i) {
          node.lasty = t(i, dx + _decalx(node,i), node.lasty, idBloc)
        });
      //on ne met le nextBlock que s'il est au même temps
      if (node.nextBlock && node.nextBlock.time==temps) {
        node.lasty = t(node.nextBlock, dx, node.lasty, idBloc)
      }
      return node.lasty;
    }
    //position les x et y des noeuds de la liste au temps temps
    //simultanément, construit les diféérents blocs de block 
    //avec idBloc=bloc_temps_n°dubloc (sert pour le déplacement)
    //console.log("traitement temps ",temps,racines[temps])
    var y = 10;
    var idBloc = 0
    racines[temps].forEach(function(n) {
      //x = 10 + ticks().indexOf(temps) * 100;
      
      var dx=1; //(x contient en fait le dacalage)
      y = t(n, dx, y, idBloc);
      y += 2 * barHeight;
      idBloc++;
    })
  }
	function createBloc(selection) {
  	//cré les blocs    
    selection.append("rect")
          .attr("id", "ther")
          .attr("height", barHeight)
          .attr("width", barWidth)
          .style("fill", color)
          .style("opacity", 0.9)         
          .append("title")
          .text(d => d.typeMorph+"( id"+d.JMLid+" temps "+d.time+")")
        //ajout du texte
        selection.append("text")
          .attr("class", classLabel)
          .attr("dx",typeof posx === 'function'? posx():posx)
          .attr("dy", barHeight / 2)
          .style("opacity", function(d) {
            if (!d.action) return 1;
            return d.action.indexOf('DEL') != -1 ?
              d.action.indexOf('_REPLACE') != -1 ?
              1 :
              0.2 :
              1;
          })
          .text(label);
          
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
     
      updateLabel = function() {
        svg.selectAll('.' + classLabel)
        	.attr("dx",typeof posx === 'function'? posx():posx)
          .attr("dy", barHeight / 2)
          .style("opacity", function(d) {
            if (!d.action) return 1;
            return d.action.indexOf('DEL') != -1 ?
              d.action.indexOf('_REPLACE') != -1 ?
              1 :
              0.2 :
              1;
          })
          .text(label);
      }
      updateMove = function() {
        //on ne fait que déplacer les "g", sans création/suppression
         var blocs = d3.nest()
                .key(d => d.time)
                //.key(d=> d.idBloc)
                .entries(dataObject)
       		svg.selectAll(".tousscripts")
        	.data(blocs,d=>d.key)
        	.attr("transform",d=> "translate("+xpos(d.key)+")")
          
        //ajustement des liens
        svg.selectAll('.' + classLink)
          .data(_links)
          .attr("x1", function(d) {
            return (d.type == "nextblock" || d.type=="inserted")
              ? xClippedPos(d.source)
              : xClippedPos(d.source,barWidth);
          })
          .attr("y1", function(d) {
          var a= getTranslate(svg.select("#"+classScript+"s_"+d.source.time))
            return d.source.y + barHeight / 2+a[1];
          })
          .attr("x2", function(d) {
            return d.type == "nextblock" ?
              xClippedPos(d.target):
               xClippedPos(d.target);
          })
          .attr("y2", function(d) {
          var a= getTranslate(svg.select("#"+classScript+"s_"+d.target.time))      
            return d.target.y + barHeight / 2+a[1];
          });
      }

      updateBlocks = function() {
       		/*
          * rassemblement des blocs
          * par temps puis par "script" (ie ensemble de blocs)
          * on aura un "g" par temps translate en x suivant l'échelle 
          * dans ce "g", un "g" par script, translaté en y
          * dans ce "g", un ensemble de bloc, translatés localement
          * en dx (décalage pour les enfants) et dy(séquence)
          */ 
          
          //création de la structure
          var blocs = d3.nest()
                .key(d => d.time)
                .key(d=> d.idBloc)
                .entries(dataObject)
  				//le pan pour les scripts
                   
          //création  des "g" scripts par temps
          var scripts=svg.selectAll(".tousscripts")
          	 .data(blocs,d=>d.key)            
          var scriptsG=scripts.enter()
          										.append("g")
                              .classed("tousscripts",true)
         
          //on ajoute le clippath entre 2 ticks
          scriptsG
             .append("clipPath")
             .attr("class","clipg")
             .attr("id",d=>"clip_"+d.key)
             .append("rect")
         scripts.selectAll(".clipg rect")             			
             	.attr("width",d=>widthTicks(+d.key)-1)
              .attr("height",height)
          //on ajoute le pan vertical sur les scripts
           var zoomScripts=d3.zoom()
                    .scaleExtent([1,1])
                    .on("zoom",function() {                   
                      //on cache le tooltip (si besoin)              
                      d3.select("#tooltip")
                      	.transition().duration(100)
                        .style("opacity", 0);
                     //on assigne le transform à l'étape correspondante (seulement en y)                              				
                  var s=svg                                        
                    	.select("#"+classScript+"s_" +this.getAttribute("id"));
                    s.attr("transform",d => 
                      "translate(0,"+d3.event.transform.y+")")                  
                  d3.select(this.parentElement).select(".clipg rect")
       		.attr("y",d => -getTranslate(s)[1])             
                    updateLinks()
                    })
                    
          scriptsG          		
          	.append("rect")
            .attr("class","zoomNS")
            .attr("id",d=>d.key) //pour retourver l'étape g correspondante  
            .call(zoomScripts)            
          svg.selectAll(".zoomNS")
          		.data(blocs,d=>d.key)    
           		.attr("width",function(d){ 
              		var n=svg.select("#"+classScript+"s_"+d.key).node()
                  if (n)
              		  return Math.min(widthTicks(+d.key)-10,n.getBBox().width)
                  return widthTicks(+d.key)-10
                  })
            	.attr("height",height)
           //on ajoute les scripts
            var scriptsEnter=scriptsG
          		.append("g")
             .attr("class",classScript+"s")
             .attr("id",d=>classScript+"s_"+d.key)
            .attr("clip-path",d=>"url(#clip_"+d.key+")")
            
          // pour chaque temps, création d'un "g" par script           
          blocs.forEach(function(n) {
          		svg.select("#"+classScript+"s_"+n.key)
              	.selectAll("."+classScript)
              	.data(n.values,d=>d.key)
                .enter()
                .append("g")
                .attr("class",classScript)
                .attr("id",d=>classScript+"_"+d.key)                
                 .on("click",function(d) {
             			//on place les scripts au premier plan                     
                  this.parentElement.appendChild(this)                 
                 var sc=svg.select("#"+classScript+"s_"+n.key)
                 sc.node().parentElement.parentElement.appendChild(sc.node().parentElement)
             })
                .on("mouseenter",function(){
                	//console.log("enter script de",n.key)
                  d3.select(this.parentElement).attr("clip-path","none" )  
                  updateLinks()
                  })
                .on("mouseleave",function() {
                	d3.select(this.parentElement).attr("clip-path",d=>"url(#clip_"+n.key+")")
                  updateLinks()
                })
              //on ajoute le Dnd
               .call(d3.drag()
               		.on("drag", function() {           
              			var dy = d3.event.dy,
                  			y=getTranslate(d3.select(this))[1]
            				d3.select(this).attr("transform","translate(0,"+(y+dy)+")")
            				updateLinks()
                    }))                 										

          	//pour chaque script , ajout des blocs
            n.values.forEach(function (b) {
            	var script=svg.select("#"+classScript+"_"+b.key)
                 .selectAll("."+classBloc)
                 .data(b.values,d=>d.id)
              var scriptEnter=script.enter()
              	.append("g").attr("class", d=>classBloc+" "+classBloc+"_"+d.JMLid )
                .attr("id",d=>classBloc+"_"+d.JMLid+"_"+d.time)
                //.on("mouseenter",function(){console.log("enter bloc")})
              	
            	//on cré le bloc
              scriptEnter.call(createBloc)
             
              script.attr("transform",d=>"translate("+d.dx+","+d.y+")")
             script.exit().remove();
             
            })
          })
          
          //update
          updateMove()
          //exit
          scripts.exit().remove();      
      }

      updateLinks = function() {
        var sel = svg.selectAll('.' + classLink).data(_links);
        //enter et update
        sel.enter()
          .append("line")
          .attr("class", d => classLink + " " + d.type)
          .merge(sel)
          //.transition().duration(duration)
          .attr("x1", function(d) {
          	var clippedNode= 	d3.select("#"+classScript+"_"+d.source.idBloc)
            										.attr("clip-path")!="none"
          	return (d.type == "nextblock" || d.type=="inserted")
            	? clippedNode?xClippedPos(d.source):xpos(d.source) 
              : clippedNode	?xClippedPos(d.source,barWidth) 	
              							:xpos(d.source)+barWidth;
          })
          .attr("y1", function(d) {
           	var a= getTranslate(svg.select("#"+classScript+"s_"+d.source.time))
            var b= getTranslate(svg.select("#"+classScript+"_"+d.source.idBloc))
            return d.source.y + barHeight / 2+a[1]+b[1];
          })
          .attr("x2", function(d) {
          var clippedNode= 	d3.select("#"+classScript+"_"+d.target.idBloc)
            										.attr("clip-path")!="none"
              return clippedNode
              	?xClippedPos(d.target)
                :xpos(d.target);
          })
          .attr("y2", function(d) {
          	var a= getTranslate(svg.select("#"+classScript+"s_"+d.target.time))      
            var b= getTranslate(svg.select("#"+classScript+"_"+d.target.idBloc))            
            return d.target.y + barHeight / 2+a[1]+b[1];
          });
        //exit
        sel.exit().remove();
      }
      updateAll = function() {
        prepareNodes();
        ticks.forEach(function(t) {
          positionneNodes(t)
        });
        _links = []
        //reconstruction des liens
        links.forEach(function(l) {
          var source = dataObject.find(b => b.id == l.source)
          var target = dataObject.find(b => b.id == l.target)
          if (target == undefined) { //soucis à règler
            console.log('undefined pour', l.source, '->', l.target)
          } else {
            _links.push({
              source: source,
              target: target,
              type: l.type
            })
          }
        });
        updateBlocks();
        updateLinks();
      }
      updateAll();

    })
  }
	chart.update =function(all=false) {
  	if (all && typeof updateAll==="function") updateAll();
    else {
    if (typeof updateBlocks==="function" && typeof updateLinks==="function") {
    	updateBlocks();
    	updateLinks();
      }
  }
  	};
  chart.move = function(value) {
    if (!arguments.length) return data;
    data = value;
    if (typeof updateMove === 'function') {
      updateMove();
    }
    return chart;
  };
  chart.data = function(value) {
    if (!arguments.length) return dataObject;
    dataObject = value;
    if (typeof updateAll === 'function') {
      updateAll();
    }
    return chart;
  };
  chart.links = function(value) {
    if (!arguments.length) return links;
    links = value;
    if (typeof updateAll === 'function') {
      updateAll();
    }
    return chart;
  };
  chart.ticks = function(value) {
    if (!arguments.length) return ticks;
    ticks = value.sort((a,b)=>a-b);
    if (typeof updateAll === 'function') {
      updateAll();
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
  if (typeof updateAll === 'function') {
      updateAll();
    }
    return chart;
  }  
	chart.svg=function() {
  	return svg;
  }
  return chart;
}