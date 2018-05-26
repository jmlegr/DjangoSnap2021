function EPRBlocks(options={}) {
/**
* affiche une icone suivant le type EPR
*/
  var width = options.width || 800,
    height = options.height || 400,
    barHeight = options.barHeight || 15,
    barWidth =options.barWidth ||  50,
    classEPR = options.classEPR || "eprblock",
    
  	xscale=options.scale || d3.scaleLinear();
    
  var label = options.label || function(d) {
    var tp=d3.timeFormat("%Mm:%Ss");
    return tp(d.evenement.time);
  }; //contenu du texte
  var _label= function(d) {
  	if (typeof label==="function") return label(d)
    return label;
  }
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
  		ticks=[];
  var update,updateLabel;
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

  
	function createEPR(selection) {
  //définition des icones
  	var play="M5,5 L5,45 45,25 Z"
		var pause="M5,5 L5,45 20,45 20,5 z M 30,5 L30,45 45,45 45,5 z"
		var stop="M5,5 L5,45 45,45 45,5z"
		var halt="M5,10 L20,25 5,40 10,45 25,30 40,45 45,40 30,25 45,10 40,5 25,20 10,5 z"
		var ask="M0,20"+
				"C0,-5 50,-5 50,20 "+
        "C 50,30 28,25 28,40"+
				"L22,40"+
        "C 22,25 44,30 44,20"+
        "C 44,1 6,1 6,20 z"+
				"M25 47 m-3 0 a 3 3 0 1 1 6 0 a 3 3 0 1 1 -6 0"
		var enter="M35,5 L45,5 45,35 20,35 20,45 5,30 20,15 20,25 35,25 z"   

		var snapShot="M10,15 L40,15"+
				"a 5,-5 0 0,1 5,5"+
        "L45,40"+
        "a -5,5 0 0,1 -5,5"+
        "L10,45"+
        "a -5,-5 0 0,1 -5,-5"+
        "L5,20"+
        "a 5,-5 0 0,1 5,-5"+
        "M25,15 L25,5 37,5 37,15"+
        "M25,30 m -10,0"+
        "a 10,10 0 1,1 20,0"+
        "a 10,10 0 0,1 -20,0"
     var error="M20,20 L30,20 30,30 20,30 z" //à faire
     var nothing="M20,25 L40,25" 
     var motif=d3.scaleOrdinal().
     				domain( ['NEW','LOAD','SAVE',
            	'START','STOP','FIN','PAUSE','REPR',
              'ERR',
              'ASK','ANSW','SNP',
              'AUTRE'])
            .range([[nothing,20,"black"],[nothing,20,"black"],[nothing,20,"black"],
            	[play,20,"green"],[halt,30,"red"],[stop,30,"red"],[pause,30,"yellow"],[play,20,"yellow"],
              [error,20,"red"],
              [ask,50,"blue"],[enter,50,"blue"],[snapShot,50,"blue"],
              [nothing,20,"black"]])
  	//cré l'affichage'
     // ajout du titre
     var tp=d3.timeFormat("%Mm:%Ss");
     var sel=selection.append("g")
     					.attr("class",classEPR)
              .attr("id",d=>classEPR+"_"+d.id)
              .attr("transform",d=>"translate("+xscale(d.evenement.time)+")")
     
     sel.append("rect").attr("class","label").attr("width",barWidth).attr("height",barHeight)
     sel.append("text").attr("class","label").attr("dy",barHeight/2).text(d=>_label(d))
    
     sel.append("path")
     		.attr("d",d=>motif(d.type)[0])
        .style("opacity",0.5)
        .style("stroke-width",1)
        .style("fill",d=>motif(d.type)[2])
				.attr("transform",d=>"scale(0.5) translate(0,"+motif(d.type)[1]+")")      
    
          
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
       var actionsEPR=svg.selectAll("."+classEPR)
          	 .data(dataObject,d=>d.d3id)         
       
      // creation des noeuds
      createEPR(actionsEPR.enter())
     
      updateLabel=function() {
      	actionsEPR=svg.selectAll("."+classEPR)
          	 .data(dataObject,d=>d.d3id)
             .selectAll("text.label")
             .text(d=>_label(d))
      }
      update=function() {
        actionsEPR=svg.selectAll("."+classEPR)
          	 .data(dataObject,d=>d.d3id)
             .attr("transform",d=>"translate("+xscale(d.evenement.time)+")")
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