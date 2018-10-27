export {affActions}
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