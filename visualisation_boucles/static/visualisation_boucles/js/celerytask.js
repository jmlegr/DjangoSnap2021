import {xsend} from './xsend.js'
export {CeleryTask}
var CeleryTask=function(config,callback) {
    /*
     * lance une tache celery avec affichage. 
     * en retour exécute callback avec comme parametres:
     *  le resultat,
     *  l'élément titre, (d3)
     *  l'élément d'affichage des résultats (d3)
     */
    
     this.callback=callback
     this.urlTask=config.urlTask //url de lancement de la tache
     this.urlCancel=config.urlCancel //url d'annulation de la tache
     this.urlStatus=config.urlStatus //url d'état de la tache
     //this.data=config.data //données envoyées à la tache
     this.delay=200 || config.delay //temps entre 2 requetes
     this.method=config.method || 'GET'  //methode pour lancement (cancel et status sont en GET)
     this.waittitle='En attente...' || config.waittitle //message titre en attendant la réponse
     CeleryTask.prototype.csrf_token=config.csrf_token
     this.overlay=config.overlay?d3.select("#"+config.overlay):d3.select("#overlayTask")
        
        this.task_id=null
        this.encours=false                       
    return this;
}
CeleryTask.prototype.lance=function(data) {
  //preparation de la fenetre
    var me=this
        this.overlay.select("#progTitle").html(this.waittitle)
        this.overlay.select("#resultats").selectAll("*").remove();
        this.overlay.style("visibility","visible")
        
        this.overlay.select("#fermerBtn")                        
                        .on("click",function() {
                            me.overlay.style("visibility","hidden")
                        })
                        
        // fonctions pour la reconstructions asynchrone
        
        let tr=0 //nombre de requetes (pour tests)
        let willstop = 0; //drapeau d'arret(1) ou d'annulation(2)
        
        var retour=null
        
        if (this.urlCancel) {
                /* bouton d'annulation */
                this.poll_cancel= function() {
                    return xsend('tolisteblock_cancel/'+this.task_id+'/',CeleryTask.prototype.csrf_token)
                    .then(response=>{
                        willstop = 2
                        console.log("cancel:",result)
                    })
                }
                this.overlay.select('#cancelBtn').style('visibility','visible');
                this.overlay.select('#cancelBtn').on('click',function() {
                    console.log('cancel')
                    this.poll_cancel()
                })
        } else {
            this.overlay.select('#cancelBtn').style('visibility','hidden');
            this.poll_cancel=function(){return null}
        }
        /* attente des resultats et maj de la barre de progression*/
        var poll=function() {
            tr+=1
            console.log('tr',tr,me.task_id,me.encours)
            me.overlay.select("#addProgress").style('visibility','visible')
                   
            xsend(me.urlStatus+'/'+me.task_id+"/", csrf_token, {                        
                        "data": {}
                    }, 'GET')
            .then(response => {
                    console.log("sessions",response)
                    if (response.task_id) me.task_id=response.task_id //plus nécessaire
                    if (response.data.state=="SUCCESS") {
                        me.result=response.data.result
                        willstop = 1;                            
                        me.overlay.select("#user-count").text("DONE");
                        me.overlay.select('#bar')
                            .style('width','100%')
                            .text(100 + '%');
                        me.overlay.select('#cancelBtn').style('visibility','hidden');
                        me.overlay.select('#result').text('reçu:'+me.result.x+'+'+me.result.y+'='+me.result.resultat)
                            
                        //on a reçu, on affiche les resultats
                        me.callback(me.result,me.overlay.select("#progTitle"),me.overlay.select("#resultats"))    
                        
                    } else if (response.data.state!="REVOKED") {
                        //c'est en cours
                        let result=response.data.result                            
                        //let process_percent=Math.round(result.evt_traites/result.nb_evts*100)                        
                        me.overlay.select('#bar')
                            .style('width',result.percent_task + '%')
                            .text(result.percent_task + '%');
                        me.overlay.select('#result').text('evts:'+result.evt_traites+'/'+result.nb_evts)
                        me.overlay.select("#user-count").text(me.task_id+': '+response.data.state);
                    } else {
                        //on annule
                         willstop = 2;     
                         me.overlay.select("#user-count").text("CANCELLED");                      
                         //d3.select('#returnBtn').style('visibility','visible');
                         me.overlay.select('#cancelBtn').style('visibility','hidden');
                    }
            })
        } //poll
                
        /* requete s */
        var requete=function() {
                    me.encours=true;
                    console.log('envoie de',data,me.method)
                    return xsend(me.urlTask, CeleryTask.prototype.csrf_token, {
                        "data": data
                    }, me.method).then(response=>{
                        console.log('recept(',response)                    
                        me.task_id=response.task_id                        
                        willstop=0
                        let refreshIntervalId = setInterval(function() {
                            poll()
                            if(willstop >= 1 ){
                                clearInterval(refreshIntervalId);  
                                me.task_id=null
                                me.overlay.select("#addProgress").style('visibility', 'hidden');                                
                            } 
                        },me.delay);
                    })
        } //requete()
        
        /* lancement */
        if (this.task_id==null) {
            if (!this.encours) requete()
            else {
                //une requete est déjà lancée mais on n'a pas encore la task_id
                this.overlay.select('#cancelBtn').style('visibility','hidden');
                var refreshTask=setInterval(function(){
                    if (this.task_id!=null) {
                        clearInterval(refreshTask)
                        this.poll_cancel().then(response=>{
                                this.task_id=null;
                                this.encours=false;
                                //maintenant on peut lancer
                                requete()
                                })
                    }
                   },this.delay)
            }
        } else {
            //c'est un nouveau lancement, on commence par annuler
            this.poll_cancel().then(response=>{
                    this.task_id=null; 
                    this.encours=false;
                    requete()
                    })
        }
}
CeleryTask.prototype.cancel=function() {
    return this.poll_cancel()
}
CeleryTask.prototype.csrf_token=null
