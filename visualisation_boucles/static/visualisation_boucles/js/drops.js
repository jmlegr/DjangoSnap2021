export {affActions,truc}
import {locale} from './locale.js'

function formatSecondsToHMS(num) {
    var h = Math.floor(num / 3600);
    var m = Math.floor((num - h * 3600) / 60);
    var s = num - (h * 3600 + m * 60);
    return (h < 10 ? "0" + h : h) + ":" + (m < 10 ? "0" + m : m) + ":" + (s < 10 ? "0" + s : s);
}

const affActions=function(data,div="actionsDiv") {
    //cré une liste des actions dans le div
    var blocks=d3.select("#"+div)
    .selectAll(".block")
    .data(data, function(e){return e.id;}) 
   blocks
    .enter().append("p")
        .attr("class","block")
        .attr("data-tippy-content",function(d){
            var retour="<strong>"+d.data.type+"("+d.id+")</strong>";
            retour+="<p>"+formatSecondsToHMS(d.dtime/1000)+"</p>"
            retour+="<p>"+formatSecondsToHMS(Math.round(d.fromStart/1000))+"</p>"
            return retour})
        .text(function(d) {
            let evenement="("+d.numero+")"
            switch (d.type){
                case "EPR": evenement+="état  :"+d.data.type; break;
                case "SPR": evenement+="statut:"+d.data.type+"("+d.data.typeMorph+","+d.data.blockSpec+")"
                                 +(d.hindex==null?"-":d.hindex)+(d.duplicInfos==null?"/":d.duplicInfos); 
                        break;
                case "ENV": evenement+="env.  :"+d.data.type; break;
                default: "inconnu";            
            }
            return  evenement
        })
     const INITIAL_CONTENT = 'Loading...'

         const state = {
   isFetching: false,
   canFetch: true
    }
  
   tippy(".block",{    
   //trigger:"click",
   delay: 100,
   arrow: false,
   arrowType: 'round',
   size: 'large',
   duration: 500,
   animation: 'scale',
   placement:'top-start',
   interactive:true,
   onShown(tip) {
       var noimage=tip.reference.__data__.image.length==0
           if (!noimage) {
               var image=tip.reference.__data__.image[0].image
               s=tippy('.uneimage',{
               theme:'light',                 
               content:"belle image"+image,
               placement:'right',
               delay:200,
               arrow:true,
               arrowType: 'round',
               size: 'large',
               duration: 500,
               animation: 'perspective',
               async onShow(tip) {                     
                   if ( state.isFetching || !state.canFetch) return
                   state.isFetching = true
                   state.canFetch = false
                   try {
                     const response = await fetch(image)
                     const blob = await response.blob()
                     const url = URL.createObjectURL(blob)
                     if (tip.state.isVisible) {
                       const img = new Image()
                       img.width = 300
                       img.height = 300
                       img.src = url
                       tip.setContent(img)
                     }
                   } catch (e) {
                     tip.setContent(`Fetch failed. ${e}`)
                   } finally {
                     state.isFetching = false
                   }
                 },
                 onHidden(tip) {
                   state.canFetch = true
                   tip.setContent(INITIAL_CONTENT)
                 }
               })
           }
           
   },
  

 })


   blocks.text(function(d) {
       switch (d.type){
       case "EPR": return "UPDATEétat  :"+d.data.type; break;
       case "SPR": return "UPDATEstatut:"+d.data.type; break;
       case "ENV": return "UPDATEenv.  :"+d.data.type; break;
       default: return "UPDATEinconnu";
       }
   });
  blocks.exit().remove();
}

const truc=function(a,b,c){
    console.log("letest",a.data())
}
/*
var drops=d3.select("#mysvg")
.selectAll(".drops")
.data(newData.filter(e=>!Array.isArray(e)),function(e){return e.id;})
drops.enter().append("rect")
.attr("class",d=>"drops "+d.infos.category)            
.attr("width",18)
.attr("height",10)
.attr("x",function(d){return d.index*20})
.attr("data-tippy-content",function(d){
var tooltip=d3.select("#tippytooltipDrop")
var t=tooltip.selectAll(".drop").data([d],function(e){return e.id});
t.enter().append("div").attr("class","drop")
     .append("p").text(e=>e.infos.type+": "+e.duplicInfos+" bloc"+(e.duplicInfos>1?"s":""))
     .append("p").text(e=>e.infos.blockSpec+`(id:${e.infos.blockId})`)                  
t.exit().remove();   
return tooltip.html()
})
drops.exit().remove()
tippy(".drops",{placement:"bottom",size:'tiny',interactive:false,
//trigger:"click",
animation:'fade',      
onShow(tip){
//tip.setContent(d3.select("#tippytooltip").html())
//tip.setContent("<p>1</p><p>1</p><p>1</p><p>1</p><p>5</p>")
}})



var actions=d3.select("#mysvg")
.selectAll(".actions")
.data(newData.filter(e=>Array.isArray(e)),function(e){return e.id;})
actions.enter().append("circle")
.attr("class","actions")
.attr("r",d=>Math.min(8,2+d.length))
.attr("cx",function(d,i){return i*20})
.attr("cy",function(d){return 5})            
.attr("data-tippy-content",function(d){
var tooltip=d3.select("#tippytooltip");
var t=tooltip.selectAll(".tp").data(d);
t.enter().append("p").attr("class",e=>"tp "+(e.image.length>0?"hasimage":""))
        .attr("nb",(e,i)=>i) //index pour retrouver la donnée
     .html(e=>e.type+":"+e.infos.type)
t.text(e=>e.type+":"+e.infos.type)
t.exit().remove(); 
console.log(tooltip)
return tooltip.html()
})
actions.exit().remove();
tippy(".actions",{placement:"top",size:'tiny',interactive:true,
//trigger:"click",
distance:5,
delay:[100,100],
animation:'fade',      
onShown(tip) {

s=tippy('.hasimage',{
       theme:'light',                 
       placement:'right',
       delay:200,
       arrow:true,
       arrowType: 'round',
       size: 'large',
       duration: 500,
       animation: 'perspective',
       async onShow(ttip) {                     
           if ( state.isFetching || !state.canFetch) return
           state.isFetching = true
           state.canFetch = false
           try {
             var image=tip.reference.__data__[ttip.reference.getAttribute("nb")].image[0].image
             const response = await fetch(image)
             const blob = await response.blob()
             const url = URL.createObjectURL(blob)
             if (ttip.state.isVisible) {
               const img = new Image()
               img.width = 300
               img.height = 300
               img.src = url
               ttip.setContent(img)
             }
           } catch (e) {
             ttip.setContent(`Fetch failed. ${e}`)
           } finally {
             state.isFetching = false
           }
         },
         onHidden(ttip) {
           state.canFetch = true
           //ttip.setContent("juste une image")
         }
         
       })
}, 
})*/