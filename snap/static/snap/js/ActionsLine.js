function ActionsLine(options={}) {
  var width = options.width || 800,
    height = options.height || 200,
		dataObject=new Data().id(d=>d.d3id),
    ticks,
    classLine = options.classLine || "actionLine",
    classTooltip= options.classTooltip || classLine+"_tooltip",
    classDetail = options.classDetail || classLine+"_detail",
    xscale= options.xscale || d3.scaleLinear(),
    xAxis,// = d3.axisBottom(xscale)
    xAxisHeight=options.xAxisHeight || 0,
    xAxisPos= options.xAxisPos || "middle",
    tickValues;
	var updateActionLine, 
  		detail=function(selection) {return };
  var svg;
  function tooltip(selection,html,duration=200) {
    //affichage d'un tooltip sur la selection
    //usage: selection.call(tooltip,"texte html" [,durée])
    var divTooltip = d3.select("#"+classTooltip).style("opacity", 0);
    
     return selection.on(
         "mouseover",
         function (d) {
          var datum=d3.select(this).datum()
          html=datum.evenement.type_display +
                "<br/>" +
                datum.type_display +
                "<br/>" +
                datum.evenement.time;                
             divTooltip.transition()
                 .duration(duration).style("opacity", .9);
             divTooltip
                 .html(html)
                 .style("left", (d3.event.pageX) + "px")
                 .style("top", (d3.event.pageY - 28) + "px");
         }).on(
         "mouseout",
         function (d) {
             divTooltip.transition()
                 .duration(500).style("opacity", 0);
         });
}
function _getXaxisPos() {
	if (typeof xAxisPos === "function") return xAxisPos();
  if (typeof xAxisPos ==="string") {
  	switch (xAxisPos) {
  		case "up" : return 0+xAxisHeight;
    	case "down": return height-xAxisHeight;      
    	case "middle": return height/2;
      default: return height/2;
      }
  	}
  return xAxisPos;
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
      d3.select(this)
      	.append("div")
        .attr("id",classTooltip)
        .attr("class","tooltip "+classTooltip)
        .style("opacity",0)
      svg.append("g")
          .attr("class", "axis axis--x")           
      }
      
      updateActionLine = function() {
        var sel=svg.selectAll('.' + classLine)
        				.data(dataObject.data());
	      sel.enter()
  	       .append("line")
           .merge(sel)
        	 	.attr("class", d=>classLine+" " + d.evenement.type)           
        	 	.attr("x1",d=> xscale(d.evenement.time))
        	 	.attr("x2",d=>xscale(d.evenement.time))
        	 	.attr("y1", 0)
        	 	.attr("y2", height-xAxisHeight)
        	  .call(function (d) {
            //console.log("d=",d,d.datum())
            tooltip(d, d.datum().evenement.type_display +
                "<br/>" +
                d.datum().type_display +
                "<br/>" +
                d.datum().evenement.time +
                "(" 
            )
            });       
       
        //ajout d'un g pour les details (optionnels, avec rotation)
        var selDetail=svg.selectAll('.' + classDetail).data(dataObject.data())
        var sn=selDetail.enter()
        		.append("g")
          	.attr("class",classDetail)
        //selDetail.enter().call(function(n){console.log("on entre",n)})
        sn.call(detail)
        sn.merge(selDetail).attr("transform",d=>"translate("
          					+ xscale(d.evenement.time)
                    +","+_getXaxisPos()+")")
          //.transition().duration(5000)
        	.attr("transform",d=>"translate("
          					+ xscale(d.evenement.time)
                    +","+_getXaxisPos()+") rotate(-90)")
       
       selDetail.exit().remove()
       
        svg.select('.axis--x')        	         
          .attr("transform","translate(0," + _getXaxisPos()+")")
          .call(xAxis.tickValues(tickValues)) //.tickValues(ticks).tickFormat(d=>"+"+d+"+"))
          	//.selectAll("text")
            //.attr("dy", "-.9em")
            //.call(wrap,20)
          //
          /*
          .selectAll("text")	
            .style("text-anchor", "end")
            
            .attr("dy", ".15em")
            .attr("transform", function(d) {
                return "rotate(-65)" 
                });*/
        sel.exit().remove()
      }      
      //xAxis=d3.axisBottom(xscale.base()).tickValues(xscale.ticks())
      var tp=d3.timeFormat("%Hh %Mm %Ss");
      xAxis=d3.axisBottom(xscale).tickFormat(d=>tp(d))
      updateActionLine();
      })
   }
 
  chart.data = function(value) {  
    if (!arguments.length) return dataObject.data();    
    dataObject.data(value);   
    return chart;
  };
  
  chart.tickValues=function(value) {
  	if (!arguments.length) return tickValues;
    tickValues=value;
     if (typeof updateActionLine === 'function') {
      updateActionLine();
      }
      return chart;
  }
  chart.ticks=function(value) {
  	if (!arguments.length) return ticks;
    ticks=value;
    /**
    * ça c'est si on veut des ticks réguliers
    * mais ça pose soucis pour l'utilisation du brush
    **/ 
    xscale.domain(ticks)
    	.range(ticks.map((d,i)=>i*width/(ticks.length-1)))
    
     if (typeof updateActionLine === 'function') {
      updateActionLine();
    }
    return chart;
  }
  chart.linear=function(value) {
  	if (!arguments.length) return ticks;
    /**
    * ça c'est si on veut des ticks réguliers en temps
    * on enlève le temps 0 avant!
    **/ 
    ticks=value;
    xscale.domain(d3.extent(ticks))
    	.range([0,width])    
     if (typeof updateActionLine === 'function') {
      updateActionLine();
    }
    return chart;
  }
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
  chart.xAxisPos = function() {
  	return _getXaxisPos();
  }
  chart.detail =function(value) {
  	if (!arguments.length) return detail;
    detail=value;
     if (typeof updateActionLine === 'function') {
      updateActionLine();
    }
    return chart;
  }
  chart.scale=function(value) {
  if (!arguments.length) return xscale;
  xscale=value;
  if (typeof updateActionLine === 'function') {
      updateActionLine();
    }
    return chart;
  }
  chart.update=function() {
  	if (typeof updateActionLine === 'function') {
      updateActionLine();
    }
    return chart;
  }
  chart.svg=function() {
  	return svg;
  }
  return chart;
}
