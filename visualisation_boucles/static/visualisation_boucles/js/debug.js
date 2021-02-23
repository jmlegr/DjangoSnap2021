export {graphDebug}


import {parcoursCommande} from './programme.js'

/**
 * graphdebug: reconstitue les scripts pour chaque chaque 'tick'. On affiche un seul 'tick'
 * @param result les données reçues [{temps:1584,bloc_45:{evenement:'ENV',type:'LOBA',commandes:[]...}}]
 * @param div le div d'affichage
 */
const graphDebug = (result,div) => {
    /**
     * modifie l'objet reçu par SimpleEvenementSerializer
     * @param obj
     * @returns {*}
     */
    const setDataType=(obj)=>{

        switch (obj.type) {
            case "EPR":
                obj.data=obj.evenementepr[0];
                obj.toString=()=>{
                    return `EPR-${obj.data.type} (detail: ${obj.data.detail}, topBlock: ${obj.data.topBlockId})`
                }
                break;
            case "SPR":
                obj.data=obj.evenementspr[0];
                obj.toString=()=>{
                    let r=`SPR-${obj.data.type} Block: ${obj.data.blockId}`
                    r+=obj.data.location?` loc: ${obj.data.location}`:''
                    r+=obj.data.targetId?` target: ${obj.data.targetid}`:''
                    r+=obj.data.detail?` detail: ${obj.data.detail}}`:''
                    r+=obj.data.parentId?` parent: ${obj.data.parentId}`:''
                    r+=obj.data.nextBlockId?` next: ${obj.data.nextBlockId}`:''
                    r+=obj.data.inputs?' inputs: '+obj.data.inputs.join(';'):''
                    return r
                }
                break;
            case "ENV":
                obj.data=obj.environnement[0];
                obj.toString=()=>{
                    return `ENV-${obj.data.type} (detail: ${obj.data.detail})`
                }
                break;
            default: obj.data={}
        }
        delete obj["evenementepr"];
        delete obj["evenementspr"];
        delete obj["environnement"];
        obj.data.type=obj.data.type+"_"+obj.type
        return obj
    }
    /**
     * ajoute une icone suivant la modification
     * @param s
     * @returns {string}
     */
    const affModif=function(s) {
        if (s) {
            const tapTruc=[["next","⬇"],["prev","⬆"],["me","⇒"],
                ["contenu","⤵"],["conteneur","↖"],
                ["undrop","↩"],["redrop","↪"],
                ["lastnode","⇏"],["del","❌"],
                ["copyfrom","⇺"],["copyto","⇻"]
            ]
            const mapTruc=new Map(tapTruc)
            var ret=""
            s.split(" ").forEach(d=>ret+=(mapTruc.get(d)!=undefined?mapTruc.get(d):" "))
            return ret
        }
        return ""
    }
    /**
     * update: met à jour les affichages des scripts (sur changement du tick)
     * @param v: l'indice du tick dans le tableau des donnees
     */
    const divResult=div.select('#resultats')
    const divProgs=divResult.append('div').attr('class','prog')
    const state = {
        isFetching: false,
        canFetch: true
    }
    const update= v=> {
        div.select('#evt')
            .datum(donnees[v].infos)
            .text(e=>`${e.evt.evenement_type}-${e.evt.type}`)
        tippy('#evt', {
            maxWidth: 750,
            hideOnClick: true,
            trigger:'click',
            content: 'loading...',
            async onShow(instance) {
                let r = '',
                    d = d3.select(instance.reference).datum().evt,
                    k = d3.keys(d)
                k.forEach(e => r += `<p class="debug_tippy">${e}: ${d[e]}</p>`)
                if (d.type == 'SNP') {
                    if (state.isFetching || !state.canFetch) return
                    state.isFetching = true
                    state.canFetch = false
                    try {
                        const response = await fetch(d3.select(instance.reference).datum().epr.snp.image)
                        const blob = await response.blob()
                        const url = URL.createObjectURL(blob)
                        if (instance.state.isVisible) {
                            const img = new Image()
                            img.width = 300
                            img.height = 300
                            img.src = url
                            instance.setContent(img)
                        }
                    } catch (e) {
                        instance.setContent(`Fetch failed. ${e}`)
                    } finally {
                        state.isFetching = false
                    }
                } else {
                    fetch('/snap/testr/'+d.evenement)
                        .then(response => response.json())
                        .then(response => {
                            let rr=''
                            response.evts_proches.sort((a,b)=>d3.ascending(a.numero,b.numero)).forEach(e=>{
                                e=setDataType(e)
                                let dn=e.numero-response.n_evt
                                rr+=`<p class="debug_tippy dn_${dn}">[${dn}] n°${e.numero} id${e.id} `+e.toString()+'</p>'
                            })
                            instance.setContent(`</p>Évènement n°${response.n_evt}</p>`+rr)
                        })
                }
            },
            onHidden(tip) {
                state.canFetch = true
                tip.setContent("nothing")
            }
        })

        let blocks=d3.keys(donnees[v]).filter(d=>d!='temps' && d!='infos')
        if (blocks.length>0) {

            let divblocks=divProgs.selectAll('.blockcommands').data(blocks)
            divblocks.enter().append('div').attr('class',d=>`debug blockcommands ${d}`).text(d=>d)
            divblocks.exit().remove()
            blocks.forEach(block=>{
                let hasChanged=donnees[v][block].commandes.some(ez=>ez.change.includes("AAchange"))
                let b=divProgs.select(`.${block}`).classed("hasChanged",hasChanged)
                    .classed("notChanged",!hasChanged)
                    .selectAll('p.command')
                    .data(donnees[v][block].commandes)
                b.enter().append('p')
                    .merge(b)
                    .attr('class',d=>'debug command '
                            +(d.action?'action ':'')
                            +(d.typeMorph?d.typeMorph:'')
                            +(d.truc?` truc truc_${d.truc}`:'')
                    )
                    //.attr("title",d=>(d.action?(d.action+"\n"):"")+`id:${d.JMLid} `+(d.truc?`truc:${d.truc}`:''))
                    .html(d=>affModif(d.truc)+'......'.repeat(d.index)+d.commande)
                b.exit().remove()
            })
            /*
            le tippy doit être mis à jour à chaque affichage
             */
            tippy(".debug.command",{
                content:'...',
                onShow:function(tip){
                    var d=d3.select(tip.reference).datum()
                    let r=''
                    d3.keys(d).forEach(e=>{
                        r+=`<p>${e}: ${d[e]}</p>`
                    })
                    tip.setContent(r)
                }
            })
        } else {
            divProgs.selectAll('div').data([]).exit().remove()
            //div.select('#evt').text('rien')
        }
    }
    /**
     * initialisation et raz du contenu
     */
    div.select('#progTitle').append('span').text(`debug de ${result.infos.user} le ${result.infos.date} (${result.session})`)
    div.select('#fermerBtn').on('click',()=>{
        div.style('visibility','hidden')
        div.select('#progTitle').html(null)
        div.select('#divtete').html(null)
        div.select('#resultats').html(null)
    });
    /**
     * préparation des données (depuis programme.js granphNbstack)
     */
    let donnees=[], liste_tetes=[], tabTemps=[], last={}
    result.commandes.forEach(function(c) {
        tabTemps.push(""+c.temps)
        //on commence par rechercher les blocks de tête
        if (c.snap==null) console.log("erreur:",c)
        let tetes=c.snap.filter(d=>d.commande
            && ((d.conteneurBlock==null && d.prevBlock==null)
                ||
                (d.conteneurBlock!=null && d.conteneurBlock.indexOf('SCRIPT')!=-1 ))
        )

        //on récupère les infos du temps donné
        let infos=result.commandes.find(e=>e.temps==c.temps)
        //console.log('infos',infos)
        //on construit les données du temps
        //let elt={temps:c.temps,informas:'blo'}
        let elt={temps:c.temps,infos:infos}
        tetes.forEach(function(t){
            const cmds=parcoursCommande(c.snap,[],t,0)
            elt["Block_"+t.JMLid]={commandes:cmds,nb:cmds.length,nbPrev:last["Block_"+t.JMLid],
                                    evenement:c.evt.evenement_type,
                                    type:c.evt.type}
            last["Block_"+t.JMLid]=cmds.length
            if (liste_tetes.indexOf("Block_"+t.JMLid)==-1) liste_tetes.push("Block_"+t.JMLid)
        })
        donnees.push(elt)
    })
    /**
     * ajout du select pour les ticks
     */
    div.select("#divtete").append('select').on('change',()=>update(div.select('select').property('value')))
        .selectAll('option')
        .data(tabTemps)
        .enter().append('option').attr('value',(d,r)=>r).text(d=>d)
    /**
     * ajout configuration affichage     *
     */
    let divtete=div.select('#divtete')
    divtete.append('label').attr('for','taille-fonte').html('fonte')
    divtete.append('input').attr('type','number').attr('id','taille_fonte').attr('min',1).attr('value',6)
        .on('input',function(){
            d3.selectAll(".command").style('font-size',this.value)
        })
    divtete.append('label').attr('for','taille-block').html('blocks (%)')
    divtete.append('input').attr('type','number').attr('id','taille_blocks').attr('value',10)
        .on('input',function(){
            d3.selectAll(".blockcommands").style('width',this.value+'%')
        })

    divtete.append('div').attr('id','evt')

    update(0)
    console.log(donnees)
}
