export {reconstitution_batch}
import {urls} from "./xsend.js";

function getRandomInt(max) {
    return Math.floor(Math.random() * Math.floor(max));
}

let tab=[],max=5
let tasks=[]; //memorise les taskids en cours
//for (let i=0;i<100;i++) t.push(`nb_${i}`)
let nb=0
let stop=false; //si vrai on arrête tout
let notifSend=false
let tempsdepart=null,
    tempsfin=null,
    nbsessions=null

import {telegramBot} from "./codesBot.js";

const notifBot=(msg)=>{
    let headers=new Headers()
    headers.append( "Content-Type", "application/json")
    fetch('https://api.telegram.org/'+telegramBot.token+'/sendMessage',
            {
            method : 'POST',
            headers:headers,
            body : JSON.stringify({chat_id: telegramBot.chat_Id, text: msg})
        }).then((r)=>r.json())
        .catch(err=>console.log('erreuer',err))
}
function dateDiff(date1, date2){
    var diff = {}                           // Initialisation du retour
    var tmp = date1 - date2;

    tmp = Math.floor(tmp/1000);             // Nombre de secondes entre les 2 dates
    diff.sec = tmp % 60;                    // Extraction du nombre de secondes

    tmp = Math.floor((tmp-diff.sec)/60);    // Nombre de minutes (partie entière)
    diff.min = tmp % 60;                    // Extraction du nombre de minutes

    tmp = Math.floor((tmp-diff.min)/60);    // Nombre d'heures (entières)
    diff.hour = tmp % 24;                   // Extraction du nombre d'heures

    tmp = Math.floor((tmp-diff.hour)/24);   // Nombre de jours restants
    diff.day = tmp;

    return diff;
}
const affDateDiff=(diff)=>{
    return (diff.day!=0?`${diff.day} jours,`:'')
            + (diff.hour!=0?`${diff.hour}h ,`:'')
            + (diff.min!=0?`${diff.min}min `:'')
            + diff.sec+' s.'
}

const lancement=(overlay)=> {
    const res=overlay.select('#resultats')
    const x=getRandomInt(1000)
    const y=getRandomInt(1000)
    const n=getRandomInt(1000)*getRandomInt(100)
    const z=tab.pop()
    nb+=1
    return fetch(`http://localhost:8000/boucles/testadd?x=${x}&y=${y}&n=${n}`,
    ).then(r => r.json()).then(e => {
        const div=res.select('#encours').append('div')
            .attr('id',`task_${e.task_id}`)
            .style('display','inline-block')
            .style('width','300px')
            .style('height','40px')
            .style('margin-right','20px')
            .style('white-space','pre-wrap')
            .style('overflow-wrap','normal')
            .style('background','grey')
            .on('click',()=>cancel(e.task_id,overlay))
        div.append('label').attr('for','prg').text('n°:'+e.task_id)
        div.append('progress').attr('id','prg').attr('max',100).attr('value',0).text('0%')

        console.log(e,z);
        tasks.push(e.task_id)
        return e.task_id
    })
}

const updateProgress=(task_id,overlay,fun)=>{
    const res=overlay.select('#resultats')
    fetch(`http://localhost:8000/boucles/testadd?job=${task_id}`)
        .then(r=>r.json())
        .then(data=>{
            console.log(nb,tab.length,'update ',task_id,data.data.result)
            if (data.data.state!='SUCCESS') {
                res.select(`#task_${task_id}`).select('label')
                    .text(`${task_id}:${data.data.result.percent_task}%`)
                res.select(`#task_${task_id}`).select('progress').attr("value",data.data.result.percent_task)
                if (!stop) setTimeout(updateProgress,500,task_id,overlay,fun)
                //return Promise.reject('pas fini')
            }
            else {
                console.log('state:',data.data.state)
                fun(task_id,data.data,overlay)
            }

        }).catch(err=>{
        if (err!='pas fini') console.log('oula',err)
    })
}

const cancel=(task,overlay)=>{
    fetch(urls.task_cancel+'/'+task)
        .then(r=>r.json())
        .then(r=>{
            alert('tache '+task+ ' annulée: '+r)
            return r
        }).finally(()=>annule(task,overlay))

}
const annule=(task,overlay)=>{
    const res=overlay.select('#resultats')
    res.select(`#task_${task}`).remove()
    res.select('#fini').append('label')
        .style('display','inline-block')
        .style('margin-right','20px')
        .style('color','red')
        .text(`${task} annulée`)
    tasks=tasks.filter(d=>d!=task)
    nb-=1
    updatetete(overlay)
    notifBot(`Tache ${task} annulée le `+new Date().toLocaleString())
    if (tab.length>0 && nb<max && !stop) {
        lancement(overlay).then(t=>updateProgress(t,overlay,fini))
    }
}
const fini=(task,r,overlay)=>{
    const res =overlay.select('#resultats')
    console.log('resultats reçus:',tab,r)
    r=r.result
    res.select(`#task_${task}`).remove()
    res.select('#fini').append('label').style('display','inline-block').style('margin-right','20px').text(`${r.x}+${r.y}=${r.resultat}`)
    tasks=tasks.filter(d=>d!=task)
    nb-=1
    updatetete(overlay)
    if (tab.length>0 && nb<max && !stop) {
        lancement(overlay).then(t=>updateProgress(t,overlay,fini))
    } else if (tab.length==0 && !notifSend && nb>0) {
        notifSend=true
        tempsfin=new Date()

        notifBot("Rendu batch terminé le "+new Date().toLocaleString()
            +`\n${nbsessions} sessions en `+affDateDiff(dateDiff(tempsfin,tempsdepart)))

    } else if (stop && !notifSend) {
        notifSend=true
        notifBot("Rendu batch annulé le "+new Date().toLocaleString())
    }
}

function updatetete(overlay){
    const div=overlay.select('#divtete')
    div.select('label span').text(tab.length)
    div.select('progress').attr('value',tab.length)
}

function reconstitution_batch(sessions,overlay) {
    overlay.style('display','initial').style('visibility','visible')
    overlay.select('#progTitle').html(null)
    overlay.select('#divtete').html(null)
    overlay.select('#resultats').html(null)
    overlay.select('#fermerBtn').on('click',()=>{
        stop=true
        tasks.forEach(t=>{
            //on annule al tache
            fetch(urls.task_cancel+'/'+t).then(r=>console.log('tache '+t+' '+r))

        })
        overlay.style('visibility','hidden').style('display','none')
        overlay.select('#progTitle').html(null)
        overlay.select('#divtete').html(null)
        overlay.select('#resultats').html(null)

    });
    //overlay.select('#resultats').remove('*')
    let divresult=overlay.select('#resultats').append('div').attr('id','rbatch').style('display','flex').style('flex-direction','column')
        .attr('width','75%')
        .style('background-color','silver')
    divresult.append('div').attr("id",'encours')
    divresult.append('div').attr("id",'fini').style('display','flex').style('flex-wrap','wrap').attr('width','200px').style('background-color','#b2eafe')

    //tab=sessions
    console.log('session',sessions)

    for (let i=0;i<160;i++) tab.push(`nb_${i}`)
    nb=0
    stop=false
    notifSend=false
    tempsdepart=new Date()
    nbsessions=sessions.length
    let tete=overlay.select('#divtete')
    tete.append('label').attr('for','progress').html('Reste: <span>#</span>/'+tab.length)
    tete.append('progress').attr('id','progress').attr('max',tab.length).attr('value',0)
    notifBot(`Rendu batch de ${nbsessions} sessions lancé le `+tempsdepart.toLocaleString())
    for (let j = 0; j < max; j++) lancement(overlay).then(t => updateProgress(t,overlay, fini))
}
//lancement().then(t=>updateProgress(t)).then(r=>console.log('result',r))
/*
    ={'percent_task': process_percent,
    'evt_traites':i,
    'nb_evts':n})

 */