import {
    xsend,
    ysend,
    urls
} from './xsend.js'
import {
    isSujet,
    getSujet,
    graphSujet,
    graphSujets
} from './films.js'
import {
    graphProgramme, graphNbCommandes, graphStackNbCommandes
} from './programme.js'
import {locale} from './locale.js'
import {affActions,truc} from './drops.js'
import {initSessionStackedBarChart} from './sessionstackedbar.js'
import {CeleryTask} from './celerytask.js'

var margin = {
        top: 30,
        right: 40,
        bottom: 50,
        left: 50
},
width = window.innerWidth*0.9 - margin.left - margin.right,
height = 200 - margin.top - margin.bottom;
var tableChart = dc.dataTable('#dc-table-graph'),
countChart = dc.dataCount("#selectedClasse"),
selectedCountChart = dc.dataCount("#selectedLines"),
selectProgramme = dc.selectMenu('#selectProgramme'),
filterProgramme = dc.textFilterWidget("#filterProgramme"),
pieChart=dc.pieChart("#piechart")

var findSelected = function () {
    // renvoi la liste des sessions
    // correspondant aux classe/date
    // sélectionnées
    var s = d3.select("#classeDate").select("#sessionsChart"),
    sel = s.selectAll(".session .selected"),
    f = []
    sel.each(function (p, j) {
        p.data.forEach(function (e) {
            f.push(e.session_key)
        })
    })
    return f
}

var resetClasseDate = function () {
    // déselectionne toutes les classes/date
    // les sessions cachées ne sont plus sélectionnées,
    // mais elles le seront de nouveau en cas de selection de la classe/date
    var s = d3.select("#classeDate").select("#sessionsChart"),
    sel = s.selectAll(".session .selected")
    sel.each(function (p, j) {
        d3.select(this).classed("selected", false)
    })
    tableChart.dimension().filterAll()
    tableChart.dimension().filter("")
    selectedCountChart.dimension().remove();
    dc.redrawAll();
}

var selectAllClasseDate = function () {
    // sélectionne toutes les classes/date
    // les sessions précédemment cachées et sélectionnées le sont de nouveau
    var s = d3.select("#classeDate").select("#sessionsChart"),
    sel = s.selectAll(".session circle")
    sel.each(function (p, j) {
        d3.select(this).classed("selected", true)
    })
    var f = findSelected()
    tableChart.dimension().filterAll()
    tableChart.dimension().filter(d => f.indexOf(d) != -1)
    dc.redrawAll();
    // on reselectionne les éléments précédemment sélectionnés
    var newsel = []
    d3.select("#dc-table-graph").selectAll('.dc-table-row')
    .each(function (p, j) {
        d3.select(this).classed("selected", p.selected ? true : false)
        if (p.selected) newsel.push(p)
    })
    selectedCountChart.dimension().remove();
    selectedCountChart.dimension().add(newsel);
    selectedCountChart.redraw()
}

var resetSessions = function () {
    // déselectionne toutes les sessions visibles
    d3.select("#dc-table-graph")
    .selectAll('.dc-table-row')
    .each(function (p, v) {
        d3.select(this).classed("selected", false)
        p.selected = false
    })
    selectedCountChart.dimension().remove();
    dc.redrawAll()
}
var selectAllSessions = function () {
    // sélectionne toutes les sessions visibles
    var newsel = []
    d3.select("#dc-table-graph")
    .selectAll('.dc-table-row')
    .each(function (p, v) {
        d3.select(this).classed("selected", true)
        p.selected = true
        newsel.push(p)
    })
    selectedCountChart.dimension().remove();
    selectedCountChart.dimension().add(newsel)
    selectedCountChart.redraw()
    // dc.redrawAll()
}

var lance = function () {
    //d3.json("https://api.myjson.com/bins/gnn28").then(function (data) {
    d3.json("sessions").then(function (data) {
        data.forEach(function (e) {
            e.debut = new Date(e.debut);
            e.fin = new Date(e.fin);
            e.selected = false; // selectionné pour analyse
            e.programme=e.loads?e.loads.split(','):[]
        })
        console.log("recp",data)
        var sessionsClasse = d3.nest().key(d => d.classe_id).entries(data)
        // console.log("par classe",sessionsClasse)
        var sessionsHeures = d3.nest().key(d => `${d.classe_nom}(${d.classe_id})`).sortKeys(d3.ascending).key(d => d3.timeHour(d.debut)).sortKeys((a, b) => new Date(a) - new Date(b)).entries(data)
        // console.log("classe/heure",sessionsHeures,d3.map(sessionsHeures,d=>d.key).keys().sort())
        var sessionsLimites = d3.nest().key(d => `${d.classe_nom}(${d.classe_id})`).sortKeys(d3.ascending).key(d => d3.timeHour(d.debut)).sortKeys((a, b) => new Date(a) - new Date(b)).rollup(function (l) {
            return {
                "values": l,
                "min": d3.min(l, d => d.debut),
                "max": d3.max(l, d => d.fin),
                "fmin": d3.timeHour.floor(d3.min(l, d => d.debut)),
                "fmax": d3.timeHour.ceil(d3.max(l, d => d.fin)),
                "count": l.length
            }
        }).entries(data)

        // console.log("limites",sessionsLimites)

        var classes = d3.map(sessionsHeures, d => d.key).keys().sort()
        classes.push("")
        var heures = d3.nest().key(d => d3.timeHour(d.debut))
        .sortKeys((a, b) => new Date(a) - new Date(b))
        .entries(data)
        .map(d => new Date(d.key))
        var jours = d3.nest().key(d => d3.timeDay(d.debut))
        .sortKeys((a, b) => new Date(a) - new Date(b))
        .entries(data)
        .map(d => new Date(d.key))
        // console.log('classes,heures,jours',classes,heures,jours)

        // .tickValues(heures)


        var timeScale = d3.scaleTime()
        .domain([d3.timeDay.offset(d3.min(sessionsLimites, d => d3.min(d.values, e => e.value.fmin)), -1),
            d3.timeDay.offset(d3.max(sessionsLimites, d => d3.max(d.values, e => e.value.fmax)), 1)])
            .range([0, width]);
        var yScale = d3.scalePoint().domain(classes).range([0, height])
        var xAxis = d3.axisBottom()
        .scale(timeScale)
        .ticks(d3.timeDay)
        .tickValues(jours)
        .tickSize(20, 0, 0)
        .tickSizeOuter(10);
        var yAxis = d3.axisLeft()
        .scale(yScale)
        .ticks(classes)
        .tickFormat(d => d.split("(")[0]), // on remplace nom(id) par
        // nom
        ySize = yScale(classes[1]) - yScale(classes[0])

        var svg = d3.select("#classeDate")
        .append("svg:svg")
        .attr("width", width + margin.left + margin.right)
        .attr("height", height + margin.top + margin.bottom)
        .append("g")
        .attr("id", "sessionsChart")
        .attr("transform",
                "translate(" + margin.left + "," + margin.top + ")");

        svg.append("g").attr("class", "xaxis")
        .attr("transform", "translate(0," + height + ")")
        .call(xAxis)
        var yAxe = svg.append("g").call(yAxis).selectAll('text')
        .attr('transform', 'translate(0,' + (ySize / 2) + ')');

        var dataHeures = []
        sessionsHeures.forEach(function (d) {
            d.values.forEach(function (e) {
                dataHeures.push({
                    "classe": d.key,
                    "heure": new Date(e.key),
                    "data": e.values
                })
            })
        })
        var color = d3.scaleOrdinal(d3.schemeCategory10)
        .domain(classes);
        var sessionsSelected = [];

        var project = svg.append("g").selectAll(".session").data(dataHeures)
        var projectEnter = project.enter().append("g").attr("class", "session")
        projectEnter
        .append("rect")
        .attr("rx", 3).attr("ry", 3)
        .attr("x", (d, i) => timeScale(d.heure))
        .attr("y", (d, i) => yScale(d.classe))
        .attr("width", (d, i) => timeScale(d3.timeHour.offset(d.heure, 1)) - timeScale(d.heure))
        .attr("height", ySize - 4)
        .attr("fill", d => color(d.classe))
        projectEnter
        .append("circle")
        // .attr("class","session")
        .attr("r", 5)
        .attr("cx", (d, i) => timeScale(d.heure))
        .attr("cy", (d, i) => yScale(d.classe) + ySize / 2 - 2)
        .attr("fill", d => d3.hsl(color(d.classe)).darker())
        // .classed("notselected",true)
        .classed("selected", false)

        .on("click", function (d, i, j) {
            var c = d3.select(this)
            // c.classed("notselected",d=>!c.classed("notselected"))
            c.classed("selected", d => !c.classed("selected"))
            filterClasseSession()
            // d.selected=c.classed("selected");console.log("clicked",d,i,j,this)
        })
        .append("title")
        .text(function (d) {
            return "classe de " + d.classe.split("(")[0] + ":\n" +
            //d3.timeFormat("%x à %X")(d.heure) + `: ${d.data.length} mesure` + (d.data.length > 1 ? "s." : ".")
            locale.utcFormat("%x à %X")(d.heure) + `: ${d.data.length} mesure` + (d.data.length > 1 ? "s." : ".")
        })
        project.exit().remove()

        var ngx = crossfilter(data)
        var sngx = crossfilter([])
        var sessionDim = ngx.dimension(d => d.session_key)
        var selectedDim = sngx.dimension(d => d.selected)
        var programmeDim= ngx.dimension(d => d.programme,true) //c'est un array

        var bySession = sessionDim.group();

        var filterClasseSession = function () {
            // refiltre et ajuste la selection par classe/date
            var f = findSelected()
            sessionDim.filterAll()
            sessionDim.filter(d => f.indexOf(d) != -1)
            dc.renderAll()
            // on reselectionne les éléments précédemment sélectionnés
            var newsel = []
            d3.select("#dc-table-graph").selectAll('.dc-table-row')
            .each(function (p, j) {
                if (p.selected) {
                    d3.select(this).classed("selected", true)
                    newsel.push(p)
                }
            })
            sngx.remove()
            sngx.add(newsel)
            selectedCountChart.redraw()
        }

        var toggleSelect = function (elt) {
            // bascule la selection sur une session
            elt.classed("selected", d => !elt.classed("selected"))
            elt.datum().selected = elt.classed("selected")
            if (elt.classed("selected")) sngx.add([elt.datum()]);
            else sngx.remove((d, i) => i == data.indexOf(elt.datum()) == i)
            selectedCountChart.redraw()
        }

        // on demarre avec une selection vide
        sessionDim.filter("")

        //filtre par programme        
        selectProgramme
        .dimension(programmeDim)
        .group(programmeDim.group())
        .multiple(true)
        .title(d=> isNaN(d.key)?`BASE: ${d.key} (${d.value})`:`id: ${d.key} (${d.value})`)
        .order((a,b)=> isNaN(a.key) > isNaN(b.key) ? -1 
                : isNaN(b.key) > isNaN(a.key) ? 1 
                        : a.value > b.value ? -1 
                                : b.value > a.value ? 1 
                                        : 0)
                                        .promptText('Tous les programmes')
                                        filterProgramme.dimension(programmeDim)
                                        .on("postRender",function(){
                                            // on reinitialise le selectProgramme, et on décale le filtrage
                                            var s=d3.select("#filterProgramme input"), //elt input                
                                            f=s.on('input') //event function

                                            s.on('input.a',function() {
                                                if (selectProgramme.filters().length>0) selectProgramme.replaceFilter(null).redraw()
                                            })
                                            //nécessaire sinon on filtre avec le search avant d'annnuler tout filtrage
                                            s.on('input.b',f)
                                        })


                                        //.onClick(function(d){console.log('clic',d)})
                                        // creation de la table
                                        tableChart.dimension(sessionDim)
                                        .group(d => d.classe_nom)
                                        // .showGroups(false)
                                        .columns(['classe',
                                            {
                                            label: "user",
                                            format: function (d) {
                                                return d.user_nom
                                            }
                                            },
                                            {
                                                label: "date",
                                                format: function (d) {
                                                    return locale.utcFormat("%x")(d.debut)
                                                }
                                            },
                                            {
                                                label: 'début',
                                                format: d => locale.utcFormat("%X")(d.debut)
                                            },
                                            {
                                                label: 'fin',
                                                format: d => locale.utcFormat("%X")(d.fin)
                                            },
                                            {
                                                label: 'session',
                                                format: d => d.session_key
                                            },
                                            {
                                                label: 'evts',
                                                format: d => d.nb_evts
                                            },
                                            {
                                                label: 'env',
                                                format: d => d.nbEnv
                                            },
                                            {
                                                label: 'spr',
                                                format: d => d.nbSpr
                                            },
                                            {
                                                label: 'epr',
                                                format: d => d.nbEpr
                                            },
                                            {
                                                label: 'new',
                                                format: d => d.nbNew
                                            },
                                            {
                                                label: 'load',
                                                format: d => d.nbLoads
                                            },
                                            {
                                                label: 'prgs',
                                                format: d => d.loads
                                            },
                                            ])
                                            .sortBy(d => d.user)
                                            .size(Infinity) // ou ngx.size()
                                            .on("postRender", function (chart) {
                                                // on ajoute levenement sur clic de la ligne
                                                chart.selectAll(".dc-table-row").on("click", function (d) {
                                                    toggleSelect(d3.select(this))
                                                })
                                            })
                                            .on("postRedraw", function (chart) {
                                                chart.selectAll(".dc-table-row").on("click", function (d) {
                                                    toggleSelect(d3.select(this))
                                                })
                                            })
                                            //le piechart des evenements
                                            function regroup(dim, cols) {
            var _groupAll = dim.groupAll().reduce(
                    function(p, v) { // add
                        cols.forEach(function(c) {
                            p[c] += v[c];
                        });
                        return p;
                    },
                    function(p, v) { // remove
                        cols.forEach(function(c) {
                            p[c] -= v[c];
                        });
                        return p;
                    },
                    function() { // init
                        var p = {};
                        cols.forEach(function(c) {
                            p[c] = 0;
                        });
                        return p;
                    });
            return {
                all: function() {
                    // or _.pairs, anything to turn the object into an array
                    return d3.map(_groupAll.value()).entries();
                }
            };
        }
        var evtsDim=ngx.dimension(d=>d.nbEvts),
        evtsGroup=regroup(evtsDim,['nbEpr','nbSpr','nbEnv'])
        pieChart
        .width(200).height(200)
        .dimension(evtsDim)
        .group(evtsGroup)
        .label(d=>d.key+"("+d.value+")")
        //.onClick(function() {console.log('rine')})
        pieChart.filter = function() {};

        // creation des compteurs
        countChart.dimension(ngx).group(ngx.groupAll()) // classe/date
        selectedCountChart.dimension(sngx).group(sngx.groupAll()) // sessions
        // .html({some:"%filter-count sélectionné(s)"})
        dc.renderAll()
    })

    // choix de la visualisation
    var isPlan=function(user,nom,elt,reperes) {
        if (elt.detail==nom) return true
        //juste pour test
        let lastSave=undefined
        if (elt.type=="SAVE") lastSave=elt
        else lastSave=reperes.find(d=>d.evenement.user==user && d.type=="SAVE" && d.detail==elt.detail)
        //console.log("test",user,nom,elt,lastSave)
        if (lastSave==undefined) return false
        let index=reperes.indexOf(lastSave)
        if (index<=0) return false
        return isPlan(user,nom,reperes[index-1],reperes)         
    }

    const statsGraphSession=function(d) {
        const overlay=d3.select("#overlayDiv")
        overlay.style("visibility","visible")
        .html(e=>`Attente de ${d.sessions}...`)
        //.on("click",function() {d3.select("#overlayDiv").style("visibility","hidden")})

        xsend("/boucles/sessions/donnees/", csrf_token, {
            "type": "ii",
            "data": d.sessions
        }, "POST")
        .then(function(response) {
            response.sort((x,y)=>d3.ascending(x.time,y.time))
            overlay.html("réception de "+response.length+" données.")
            overlay.append("h2").html(d.user)
            overlay.append("h4").html(locale.utcFormat("%c")(new Date(d.creation)))
            //console.log("recu iuiu:",response)
            overlay.append("div")
            .attr("class","actions")
            .attr("id","actionsDiv")
            .style("height","300px")
            .style("width","30%")
            .style("overflow","auto")
            var duplicInfos=null; //infos de duplication
            var hindex=0; //index horizontal, change si drop/new
            var vindex=0; //index vertical pour non drop/new
            var newData=[],
            newNodes=null;
            const setDataType=function(obj) {
                switch (obj.type) {
                case "EPR": obj.data=obj.evenementepr[0];break;
                case "SPR": obj.data=obj.evenementspr[0];  break;
                case "ENV": obj.data=obj.environnement[0];break;
                default: obj.data={}                    
                }
                delete obj["evenementepr"]; 
                delete obj["evenementspr"];
                delete obj["environnement"]; 
                obj.data.type=obj.data.type+"_"+obj.type
                return obj
            }

            let dtime=null, fromStartTime=null
            response.forEach(function(d){                    
                d.dtime=dtime?(d.time-dtime):0
                        dtime=d.time
                        if (fromStartTime==null) fromStartTime=d.time
                        d.fromStart=d.time-fromStartTime
                        d=setDataType(d)
                        if (d.type=="ENV" && d.data.type=="DUPLIC") {
                            duplicInfos=d.data.detail.split(";").length;
                        }
                if (d.type=="SPR" && (d.data.type=="DROP" || d.data.type=="NEW")) {
                    d.hindex=hindex;
                    hindex+=1;
                    if (duplicInfos != null) {
                        d.duplicInfos=duplicInfos;
                        duplicInfos=null;
                    }
                    vindex=0;
                    if (newNodes!=null) {
                        newData.push(newNodes);
                        newNodes=null;
                    }
                    newData.push(d);        
                }
                else {
                    //changement de vindex sinon
                    d.hindex=hindex;
                    d.vindex=vindex;
                    vindex+=1;
                    if (newNodes==null) {
                        newNodes=[d];
                    } else {
                        newNodes.push(d);
                    }
                }
            })
            affActions(response)
            d3.select("#actionsDiv").call(truc)
            const ntx=crossfilter(response),
            typeDimension=ntx.dimension(d=>d.type),
            typeDataDimension=ntx.dimension(d=>d.data.type),
            countType=typeDimension.group().reduceCount(),
            countDataType=typeDataDimension.group().reduceCount(),
            countByDataType=typeDimension.group().reduce(
                    function(p, v) {//add
                        p[v.data.type]=(p[v.data.type]||0)+1                                     
                        return p;
                    },
                    function(p, v) {//remove
                        p[v.data.type]=(p[v.data.type]||0)-1
                        return p;
                    },
                    function(p) {//initial
                        p={};
                        return p;
                    }
            )
            d3.select("#overlayDiv").append("div").attr("id","statsDetail").attr("class","dc-chart")
            d3.select("#overlayDiv").append("div").attr("id","statsgen").attr("class","dc-chart")               
            var chart = dc.barChart('#statsgen');
            chart
            //.width("70%")
            //.width(600)
            .height(300)
            .margins({left: 20, top: 40, right: 10, bottom: 30})
            .x(d3.scaleBand())
            .xUnits(dc.units.ordinal)
            //.brushOn(false)
            .renderLabel(true)
            .xAxisLabel('Type d\'événement')
            .yAxisLabel('Nombre d\'événements')
            .dimension(typeDataDimension)
            //.barPadding(0.1)

            .outerPadding(0.5)
            .group(countDataType);


            var allTypes=countDataType.top(Infinity).map(d=>d.key)
            var gchart=dc.barChart("#statsDetail")
            gchart.width(500)
            .height(300)
            .margins({left: 100, top: 40, right: 10, bottom: 30})
            .colors( d3.scaleOrdinal(["#b80043",
                "#48c316",
                "#7b2bdb",
                "#ac9a00",
                "#0142e2",
                "#968c00",
                "#9159ff",
                "#2c7000",
                "#ee50ff",
                "#01b375",
                "#ad00c5",
                "#b1af42",
                "#6d00a0",
                "#007438",
                "#ff3bac",
                "#54bd96",
                "#ee0069",
                "#00b8be",
                "#ed6300",
                "#487bff",
                "#c96100",
                "#015dd2",
                "#f09550",
                "#0049aa",
                "#af000a",
                "#0061ac",
                "#a33c00",
                "#97a5fd",
                "#2c4900",
                "#b4007e",
                "#006d50",
                "#d60067",
                "#92b57b",
                "#621477",
                "#c4a85a",
                "#2a3284",
                "#fa8e68",
                "#004582",
                "#c10034",
                "#7d8cc1",
                "#843d00",
                "#be9ce7",
                "#4b4000",
                "#f087d6",
                "#d5a169",
                "#7d0060",
                "#e19989",
                "#3f3368",
                "#ff7873",
                "#804c71",
                "#ff6075",
                "#761228",
                "#ff639d",
                "#8e4c4d",
                "#a0004e"]))//d3.interpolateViridis(20))
                .x(d3.scaleBand())
                .xUnits(dc.units.ordinal)
                .brushOn(false)
                .renderLabel(true)
                .xAxisLabel('Type d\'événement')
                .yAxisLabel('Nombre d\'événements')
                .dimension(typeDataDimension)
                //.barPadding(0.1)
                .title(function(d) {
                    return this.layer+": " + d.value[this.layer];
                })
                .outerPadding(0.5)
                .group(countByDataType,allTypes[0],function(d){                        
                    return d.value[allTypes[0]] || 0
                });
            allTypes.forEach(function(i,j){
                if (j>0) {
                    gchart.stack(countByDataType,i,function(d){ 
                        return d.value[i] || 0
                    })
                }
            })
            gchart.legend(dc.legend())
            dc.renderAll();
            d3.select("#overlayDiv").append("button").attr("class","btn").text("Fermer")
            .on("click",function() {d3.select("#overlayDiv").style("visibility","hidden")})


        })     
    }
    var testcel=new CeleryTask({
            urlTask:'testadd',
            urlStatus:urls.task_status,
            urlCancel:urls.task_cancel,
            overlay:'overlayDiv2',
            csrf_token:csrf_token,
            method:'POST'
    },function(r,d,v) {console.log('recu',r,d,v)})
    
    var reconstructionTask=new CeleryTask({
            urlTask:urls.programmes,
            urlStatus:urls.task_status,
            urlCancel:urls.task_cancel,
            overlay:'overlayDiv2',
            csrf_token:csrf_token,       
            },function(result,elTitle,elResult) {
                elTitle                    
                    .html(`Utilisateur <b>${result.infos.user}</b>, programme "<b>${result.infos.type}</b>", `
                    +`le ${locale.utcFormat("%x à %X")(new Date(result.infos.date))}`)
                graphProgramme(result,elResult,false)        
            }
        )
    var reconstructionTaskForExport=new CeleryTask({
        urlTask:urls.programmes,
        urlStatus:urls.task_status,
        urlCancel:urls.task_cancel,
        overlay:'overlayDiv2',
        csrf_token:csrf_token,       
        },function(result,elTitle,elResult) {
            elTitle                    
                .html(`Utilisateur <b>${result.infos.user}</b>, programme "<b>${result.infos.type}</b>", `
                +`le ${locale.utcFormat("%x à %X")(new Date(result.infos.date))}
                (pour export)`
                )
            graphProgramme(result,elResult,true)        
        }
    )
   
    var reperesTask=new CeleryTask({
        urlTask:urls.celrep,
        urlStatus:urls.task_status,
        urlCancel:urls.task_cancel,
        overlay:'overlayDiv2',
        csrf_token:csrf_token,   
        method:'POST'
        },function(result,elTitle,elResult) {
            //console.log("repere",result,elResult)
            elTitle                    
                .html(`Repères de ${d3.map(result,d=>d.evenement.user_nom).keys()}`
                )       
            graphSujets({result:result,callback:statsGraphSession,element:elResult})
    })
    
    var graphbouclesTask=new CeleryTask({
        urlTask:urls.boucle,
        urlStatus:urls.task_status,
        urlCancel:urls.task_cancel,
        overlay:'overlayDiv2',
        csrf_token:csrf_token,
        method:'POST'
        },function(result,elTitel,elResult) {})
    
    var reconstruction=false, //vrai si on est en train de calculer la reconstruction du prg
    task_id
    d3.select("#visualiser")
    .on("click", function () {
        //on supprime les graphes
        d3.select("#graphSujet").selectAll("*").remove()
        var valueSplit = d3.select("#visualisation-type input:checked").node().value.split('_'),
            valueSelected=valueSplit[0],
            option=valueSplit.length>1?valueSplit[1]:null
                    
        // marche pas plus:var liste = JSON.parse(JSON.stringify(selectedCountChart.dimension().all()))
        let liste = selectedCountChart.dimension().all()
        var session_keys= selectedCountChart.dimension().all().map(d=>d.session_key)
        console.log("listenb",liste.length)
        let url="",data=null,method="POST"
            console.log("value", valueSelected,option, liste,liste[0])
            //alert("chargement de " + z)
            if (valueSelected=="Xreperes") {                
                url=urls.reperes               
                data=liste.map(d=>d.session_key)
                method="POST"
                    xsend(url, csrf_token, {
                        "type": valueSelected,
                        "data": data
                    }, method)
                    .then(response => {console.log("sessions",response)                
                        let users=d3.map(response,d=>d.evenement.user).keys()
                        console.log('rep',users)
                        //users.forEach(function(u){graphSujet(u,response,statsGraphSession)})                    
                    })        
            } else if (valueSelected=="reperes") {
                reperesTask.lance({
                    data:liste.map(d=>d.session_key)
                })            
            } else if (valueSelected=="reconstitution"){
                if (liste.length!=1) {
                    console.log("data",liste,liste.map(d=>d.session_key),{session_keys:liste.map(d=>d.session_key)})
                    alert("Sélectionner une et une seule session!")
                } else {
                    switch (option) {
                    case "normal": reconstructionTask.lance({
                                        data:liste.map(d=>d.session_key)[0],
                                        ajout_url:liste.map(d=>d.session_key)[0]+"/?load"
                                    }); break;
                    case "debug": xsend('tb/'+liste.map(d=>d.session_key)[0],csrf_token,{"truc":"bidule"},'GET')
                                    .then(response=> console.log("resp",response)); break;
                    case "save": reconstructionTask.lance({
                                    data:liste.map(d=>d.session_key)[0],
                                    ajout_url:liste.map(d=>d.session_key)[0]+"/?save"
                                    }); break;
                    case "export": reconstructionTaskForExport.lance({
                                    data:liste.map(d=>d.session_key)[0],
                                    ajout_url:liste.map(d=>d.session_key)[0]+'/?load'
                                    }); break;
                    default: alert("Option non reconnue ("+option+")");
                    }
                }                
            } else if (valueSelected=='boucle') {
                if (liste.length=0) {
                    alert("Sélectionner au moins une session!")
                } else {
                    console.log("data",session_keys,liste.map(d=>d.session_key),{session_keys:liste.map(d=>d.session_key)})
                    graphbouclesTask.lance({
                        data:{session_keys:session_keys},
                        callback:function(result,elTitle,elResult) {
                            let data=new Array()
                            let databoucles=[]
                            for (var session in result) {                           
                                    data=data.concat(result[session].evts)                                
                                    databoucles[session]=result[session].boucle                                
                            }
                            const setDataType=function(obj) {
                                switch (obj.type) {
                                case "EPR": obj.data=obj.evenementepr[0];break;
                                case "SPR": obj.data=obj.evenementspr[0];  break;
                                case "ENV": obj.data=obj.environnement[0];break;
                                default: obj.data={}                    
                                }
                                
                                if (obj.data) {
                                    obj.datatype=obj.type+"_"+obj.data.type
                                } else {
                                    obj.datatype=obj.type+"_ZZZ"
                                    console.error("ZARB",obj)
                                }
                                delete obj["evenementepr"]; 
                                delete obj["evenementspr"];
                                delete obj["environnement"]; 
                                return obj
                            }
                            data.forEach(d=>setDataType(d))
                            console.log('data',data,databoucles,elResult.node())
                            initSessionStackedBarChart.draw({
                                data:data,
                                boucles:databoucles,
                                liste:liste,
                                key:d3.map(data,function(d){return d.datatype}).keys(),
                                element:elResult
                            })                  
                        }
                    })
                }
                
                
            } else if (valueSelected=="evolution") {
                if (liste.length!=1) {
                    alert("Sélectionner une et une seule session!")
                } else {
                    reconstructionTask.lance({
                        data:liste.map(d=>d.session_key)[0],
                        ajout_url:liste.map(d=>d.session_key)[0]+"/?load",
                        callback:function(result,elTitle,elResult) {
                            elTitle                    
                            .html(`Utilisateur <b>${result.infos.user}</b>, programme "<b>${result.infos.type}</b>", `
                                    +`le ${locale.utcFormat("%x à %X")(new Date(result.infos.date))}: évolution`)
                                    graphStackNbCommandes({data:result,element:elResult})
                        }
                    })
                }
            }
    })

    d3.select("#selectAllClasseAnchor").on("click", function () {
        selectAllClasseDate()
    })
    d3.select("#resetClasseAnchor").on("click", function () {
        resetClasseDate()
    })
    d3.select("#selectAllSessionsAnchor").on("click", function () {
        selectAllSessions()
    })
    d3.select("#resetSessionsAnchor").on("click", function () {
        resetSessions()
    })
}
export {
    lance
}
