import {
    data,
    xsend,
    url
} from './xsend.js'

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
                    d3.timeFormat("%x à %X")(d.heure) + `: ${d.data.length} mesure` + (d.data.length > 1 ? "s." : ".")
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
                        return d3.timeFormat("%x")(d.debut)
                    }
                },
                {
                    label: 'début',
                    format: d => d3.timeFormat("%X")(d.debut)
                },
                {
                    label: 'fin',
                    format: d => d3.timeFormat("%X")(d.fin)
                },
                /*{
                    label: 'session',
                    format: d => d.session_key
                },*/
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
    d3.select("#visualiser")
        .on("click", function () {
            var z = d3.select("#visualisation-type input:checked").node().value
            var liste = selectedCountChart.dimension().all()
            console.log("z", z, liste)
            //alert("chargement de " + z)
            xsend(url, csrf_token, {
                "type": z,
                "data": liste
            }, "POST").then(response => console.log('Sucscess:', response))
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
