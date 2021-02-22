export {graphDebug}


import {parcoursCommande} from './programme.js'

/**
 * graphdebug: reconstitue les scripts pour chaque chaque 'tick'. On affiche un seul 'tick'
 * @param result les données reçues [{temps:1584,bloc_45:{evenement:'ENV',type:'LOBA',commandes:[]...}}]
 * @param div le div d'affichage
 */
const graphDebug = (result,div) => {
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
    const update= v=> {
        let blocks=d3.keys(donnees[v]).filter(d=>d!='temps')
        if (blocks.length>0) {
            div.select('#evt').text(`${donnees[v][blocks[0]].evenement} - ${donnees[v][blocks[0]].type}`)
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
                    .attr("title",d=>(d.action?(d.action+"\n"):"")+`id:${d.JMLid} `+(d.truc?`truc:${d.truc}`:''))
                    .html(d=>affModif(d.truc)+'...'.repeat(d.index)+d.commande)
                b.exit().remove()
            })
        } else {
            divProgs.selectAll('div').data([]).exit().remove()
            div.select('#evt').text('rien')
        }
    }
    /**
     * initialisation et raz du contenu
     */
    div.select('#progTitle').append('span').text("en debug")
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
        let elt={temps:c.temps}

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
