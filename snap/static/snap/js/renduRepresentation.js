var widthPpal = 1000,
    heightPpal = d3.select("#affichage").node()
    .getBoundingClientRect().height;

var divTooltip = d3.select("body").append("div").attr("class", "tooltip")
    .style("opacity", 0);
var affichageSvg = d3.select("#affichage").append("svg").attr("id",
        "affichageSvg").attr("width", widthPpal) // + margin.left + margin.right)
    .attr("height", heightPpal).attr("class", "graph-svg-component"), // l'affichage arbre+script
    arbreSvg, // afficahge arbre    
    actionSvg = d3.select("#actions").append("svg").attr("class", "actions").attr(
        "id", "actionSvg").attr("width", 1000).attr("height", 100), //affichage actions
    margin = {
        top: 0,
        right: 0,
        bottom: 0,
        left: 0
    }, //pour arbre
    margin2 = {
        top: 430,
        right: 0,
        bottom: 0,
        left: 0
    }, //pour scripts
    width = +affichageSvg.attr("width") - margin.left - margin.right,
    height = +affichageSvg
    .attr("height") -
    margin.top - margin.bottom,
    height2 = +affichageSvg.attr("height") -
    margin2.top - margin2.bottom,
    heightAction = +actionSvg
    .attr("height")
var x = d3.scaleLinear().range([0, width]),
    x2 = d3.scaleLinear().range(
	[0, width]);

var xAxis = d3.axisBottom(x),
    xAxis2 = d3.axisBottom(x2);

var brush = d3.brushX().extent([[0, 0], [width, heightAction]]).on(
    "brush end", brushed);

var zoom = d3.zoom().scaleExtent([1, Infinity]).translateExtent(
	[[0, 0], [width, height + height2]]).extent(
	[[0, 0], [width, height + height2]]).on("zoom", zoomed);

affichageSvg.append("defs").append("clipPath").attr("id", "clip")
    .append("rect").attr("width", width).attr("height", heightPpal + 20);
var affichageActionNode; //noeud avec les data
var zoomSvg=affichageSvg.append("rect")
    .attr("class", "zoom")
    .attr("width", width)
    .attr("height", height)
    .attr("transform", "translate(" + margin.left + "," +
        margin.top + ")")
    .call(zoom);
var arbreSvg = affichageSvg.append("g").attr("class", "arbre").attr(
    "transform", "translate(" + margin.left + "," + margin.top + ")")
var scriptSvg = affichageSvg.append("g") //affichage scripts 
    .attr("class", "scripts").attr("transform",
        "translate(" + margin2.left + "," + margin2.top + ")")
var ligneActionSvg = affichageSvg.append("g").attr("class","ligneAction")
initListeEleves();
// on initialise les axes le brush et le zoom (pour ne pas les rajouter à chaque chargement)
actionSvg.append("g").attr("class", "axis axis--x").attr("transform",
    "translate(0," + (actionSvg.attr("height") / 2) + ")").call(xAxis2);
actionSvg.append("g").attr("class", "brush actionNode").call(brush).call(
    brush.move, x.range());
affichageSvg.append("g").attr("class", "axis axis--x").attr("transform",
    "translate(0," + (heightPpal - 20) + ")").call(xAxis);


function initListeEleves() {
    console.log('initialiation')
    d3.json('spropen/users', function (error, data) {
        console.info("reception liste elveves");
        console.log("reception", data);
        data.unshift({
            id: 0
        })
        var el = d3.select('#selectEleves')
        el.selectAll("option").data(data).enter().append("option").attr(
            "value",
            function (d) {
                return d.id
            }).text(
            function (d) {
                return d.id == 0 ? "---" : (d.username + "(" +
                    (d.eleve ? d.eleve.classe : 'prof') + ")")
            })
        el.on("change", changeEleve)

    });
}

function changeEleve() {
    // var
    // selectedIndex=d3.select("#selectEleves").property('selectedOptions')[0].value
    var selectedValue = d3.select("#selectEleves").property('value')
    /*
     * var s=d3.select("#selectEleves").selectAll("option").filter(function
     * (d,i) { return d.id==selectedValue}), data=s.datum()
     * console.log('eke',data)
     */
    if (selectedValue != 0)
        d3.json('spropen/' + selectedValue + "/openUser",
            function (error, data) {
                console.log('data session', data);
                data.unshift({
                    id: 0
                })
                var session = d3.select('#selectSessions')
                session.selectAll("option").data(data, function (d) {
                    return d.id
                }).enter().append("option").attr("value", function (d) {
                    return d.id
                }).text(
                    function (d) {
                        return d.id == 0 ? "---" : ((new Date(
                                d.evenement.creation)).toUTCString() +
                            "(" + d.evenement.user + ")")
                    })
                session.on("change", changeSession)
                // session.selectAll("option").call(function(d){console.log('update',d)})
                session.selectAll("option").data(data, function (d) {
                    return d.id
                }).exit().remove()
            });
}

function changeSession() {
    var selectedValue = d3.select("#selectSessions").property('value')
    console.log('evnoi', selectedValue)
    getJson(selectedValue);
}

function getLastParentId(node) {
    // renvoie l'id du noeud parent s'il existe,
    // ou l'id du noeud parent temporellement précédent s'il existe
    // ou l'id de la racine
    nodeId = node.conteneurBlock == null ? node.parentBlock :
        node.conteneurBlock
    if (nodeId != null) {
        n = donnees.filter(
            function (d) {
                return d.time <= node.time &&
                    (d.id == nodeId || d.JMLid == nodeId.split('_',
                        1)[0])
            }).sort(function (a, b) {
            return a.time - b.time
        }).pop()
        return n == undefined ? 'racine' : n.id
    }
    return null
}

var ticks = {
    times: [],
    invert: function (d) {
        var r = this.times.indexOf(d);
        if (r != -1)
            return r;
        //c'est un ticks correspondant à un évènement autre que SPR
        for (i in this.times) {
            if (this.times[i] > d) {
                return (i - 1 + (d - this.times[i - 1]) / (this.times[i] - this.times[i - 1]))
            }
        }
        return this.length();
    },
    length: function () {
        return this.times.length
    }
}

function getJson(session) {
    if (session != 0) {
        console.log('session', session)
        d3
            .json(
                "tb/" + session,
                function (error, data) {
                    if (error) {
                        console.warn("error", error.type, ":",
                            error.target.statusText)
                        return

                    }
                    /*
                     * preparation des donnees: tous les blocks au temps 0, avec ajout
                     * d'une racine fictive ajouts des blocks contenus en enfant des
                     * blocks contenant
                     */
                    console.log('donnee recoes', data)
                    donnees = data.data
                    ticks.times = data.ticks
                    links = data.links
                    actions = data.actions
                    //extent=d3.extent(actions, function(d) { return d.evenement.time; })
                    //extent[1]+=10000
                    //x.domain(extent);
                    x.domain([0, ticks.length()])
                    x2.domain(x.domain());
                    //on chage pour tester: ordinal

                    // construction des axes
                    actionSvg.selectAll("g.axis").attr("class",
                        "axis axis--x").attr(
                        "transform",
                        "translate(0," + actionSvg.attr("height") /
                        2 + ")").call(xAxis2);
                    affichageSvg.selectAll("g.axis").attr("class",
                            "axis axis--x").attr("transform",
                            "translate(0," + (heightPpal - 20) + ")")
                        .call(xAxis);
                    //ici si besoin les modifs du rectangle de zoom
                    /**
                     *affichageSvg.selectAll("rect.zoom")
                     *    .attr("class", "zoom")
                     *    .attr("width", width)
                     *    .attr("height", height)
                     *    .attr("transform","translate(" + margin.left + "," +
                     *        margin.top + ")")
                     *    .call(zoom);
                     **/
                    //brush
                    actionSvg.selectAll("g.brush").attr("class",
                        "brush actionNode").call(brush).call(
                        brush.move, x.range());
                    // actions dans actionSvg
                    actionNode = actionSvg.selectAll(".actionLine")
                        .data(actions, function (d) {
                            return d.d3id;
                        })
                    actionNode
                        .enter()
                        .append("line")
                        .attr("class", function (d) {
                            return "actionLine " + d.evenement.type
                        })
                        .attr(
                            "x1",
                            function (d) {
                                return x2(ticks
                                    .invert(d.evenement.time))
                            })
                        .attr(
                            "x2",
                            function (d) {
                                return x2(ticks
                                    .invert(d.evenement.time))
                            })
                        .attr("y1", 0)
                        .attr("y2", actionSvg.attr("height"))
                        .on(
                            "mouseover",
                            function (d) {
                                divTooltip.transition()
                                    .duration(200).style(
                                        "opacity", .9);
                                divTooltip
                                    .html(
                                        d.evenement.type_display +
                                        "<br/>" +
                                        d.type_display +
                                        "<br/>" +
                                        d.evenement.time +
                                        "(" +
                                        ticks
                                        .invert(d.evenement.time) +
                                        ")")
                                    .style(
                                        "left",
                                        (d3.event.pageX) +
                                        "px")
                                    .style(
                                        "top",
                                        (d3.event.pageY - 28) +
                                        "px");
                            }).on(
                            "mouseout",
                            function (d) {
                                divTooltip.transition()
                                    .duration(500).style(
                                        "opacity", 0);
                            });
                    actionNode.exit().remove()
                    //actions dans affichage
                    affichageActionNode = ligneActionSvg
                        .selectAll(".actionNode")
                        .data(actions, function (d) {return d.d3id;})
                    affichageActionNodeEnter=affichageActionNode
                        .enter()
                        .append("g").attr("class","actionNode")
                    
                    affichageActionNodeEnter.append("line").attr(
                        "class",
                        function (d) {
                            return "actionLine " + d.evenement.type
                        }).attr("x1", function (d) {
                        return x(ticks.invert(d.evenement.time))
                    }).attr("x2", function (d) {
                        return x(ticks.invert(d.evenement.time))
                    }).attr("y1", 0).attr("y2",
                        affichageSvg.attr("height"))

                    affichageActionNode.exit().remove()
                    detail = ligneActionSvg
                        .selectAll(".detail")
                        .data(actions, function (d) {
                            //return d.id || (d.id = ++i)
                            //return d.evenement.id+'_'+d.id
                            return d.d3id;
                        });
                    detailEnter = affichageActionNodeEnter//.selectAll(".detail")
                        //.enter()
                        .append("g")
                        .attr("class", "detail")
                        .attr("id", function (d) {
                            return "detail_" + d.id
                        })
                        .on(
                            "mouseover",
                            function (d) {
                                divTooltip.transition()
                                    .duration(200).style(
                                        "opacity", .9);
                                divTooltip
                                    .html(
                                        d.evenement.type_display +
                                        "<br/>" +
                                        d.type_display +
                                        "<br/>" +
                                        d.evenement.time)
                                    .style(
                                        "left",
                                        (d3.event.pageX) +
                                        "px")
                                    .style(
                                        "top",
                                        (d3.event.pageY - 28) +
                                        "px");
                            }).on(
                            "mouseout",
                            function (d) {
                                divTooltip.transition()
                                    .duration(500).style(
                                        "opacity", 0);
                            });

                    detailEnter.append("rect").attr("class", function (d) {
                        return "actionrect " + d.evenement.type
                    }).attr("width", 100).attr("height", 20).attr(
                        "fill", "brown")
                    detailEnter.append("text").text(function (d) {
                        return d.type_display
                    }).attr("dy", 10).attr("dx", 5)

                    detailEnter.attr("transform", function (d) {
                        return "translate(" +
                            x(ticks.invert(d.evenement.time)) +
                            "," + affichageSvg.attr("height") +
                            ") rotate(-90)"
                    })
                    detail.exit().remove()
                    //préparation des scripts
                    /*
                     * 	on reconstruit les données sous la forme
                     * 	[{time,action,commandes:[{index,scriptIt,numero,JMLid,niveau,commande}]}...]
                     */
                    etapes = data.etapes.map(function (d, index) {
                        a = []
                        for (k in d.commandes) {
                            b = d.commandes[k]
                            for (j in b) {
                                a.push({
                                    index: data.scripts
                                        .indexOf(parseInt(k)),
                                    scriptId: parseInt(k),
                                    numero: j,
                                    id: b[j].id,
                                    niveau: b[j].niveau,
                                    commande: b[j].commande
                                })
                            }
                        }
                        return {
                            time: d.time,
                            action: d.action,
                            commandes: a
                        }
                    })
                    var idex = 0,
                        sizeHeight = 12,
                        decalageFirst = 20, //premiere ligne
                        decalageNiveau = 10, //decalge sur chaque niveau  (plutot que des caractères)  ,
                        etapesSvg = scriptSvg.selectAll(".etape").data(
                            etapes,
                            function (d) {
                                return d.id || (d.id = ++idex);
                            }),
                        /*etapesGroupe1 = etapesSvg
                        	.enter()
                        	.append("svg")
                        	.attr("id",function(d){return "ii"})    	    		
                        	.attr("width",20)
                         */
                        etapesGroupe = etapesSvg.enter().append("g").attr(
                            "class", "etape")
                    /*
                    définition des gradients
                     */
                    var gradientPair = scriptSvg.append(
                        "linearGradient").attr("y1", 0).attr("y2",
                        0).attr("x1", "0").attr("x2", "50").attr(
                        "id", "gradientPair").attr("gradientUnits",
                        "userSpaceOnUse");
                    gradientPair.append("stop").attr("offset", "0")
                        .attr("stop-color", "green").attr(
                            "stop-opacity", "0.5");
                    gradientPair.append("stop").attr("offset", "1")
                        .attr("stop-opacity", "0");

                    var gradientImpair = scriptSvg.append(
                        "linearGradient").attr("y1", 0).attr("y2",
                        0).attr("x1", "0").attr("x2", "50").attr(
                        "id", "gradientImpair").attr(
                        "gradientUnits", "userSpaceOnUse");
                    gradientImpair.append("stop").attr("offset", "0")
                        .attr("stop-color", "blue").attr(
                            "stop-opacity", "0.5");
                    gradientImpair.append("stop").attr("offset", "1")
                        .attr("stop-opacity", "0");

                    etapesGroupe.append("text").attr("class",
                        "timeetape").text(function (d) {
                        return "(" + d.id + ")" + d.time
                    }).attr("dy", sizeHeight - 1)
                    etapesGroupe.each(function (d, i) {
                        var coms = d3.select(this).selectAll(
                                '.groupeetape').data(d.commandes)
                            .enter().append("g")

                            .attr("class", "groupeetape");
                        coms.append("rect").attr(
                                "class",
                                function (d) {
                                    return ((d.index % 2 == 0) ? "pair" :
                                        "impair");
                                }).attr(
                                "y",
                                function (d, j) {
                                    return j * sizeHeight + d.index *
                                        (sizeHeight / 2) +
                                        decalageFirst
                                }).attr("x", function (d) {
                                return d.niveau * decalageNiveau
                            }).attr("width", 50).attr("height", sizeHeight)
                            .attr("fill", "url(#gradient)");
                        coms.append('text').attr("class", "textetape ")
                            .attr(
                                "dy",
                                function (d, j) {
                                    return (j + 1) * sizeHeight +
                                        d.index *
                                        (sizeHeight / 2) +
                                        decalageFirst
                                }).attr("dx", function (d) {
                                return d.niveau * decalageNiveau
                            }).text(function (e, j) {
                                return e.commande
                            })
                    })
                    scriptSvg
                        .selectAll(".etape")
                        .attr(
                            "transform",
                            function (d) {
                                return "translate(" +
                                    (x(ticks
                                        .invert(d.time)) + 10) +
                                    ",0)"
                            })

                    etapesSvg.selectAll(".etape").exit().remove()
                })
    }
}

function updateAffichageActions() {
    if (affichageActionNode) {
        console.log('sel', affichageSvg.selectAll(".actionLine"))
        affichageSvg.selectAll(".actionLine")
            .attr("x1", function (d) {
                console.log('cakc');
                return x(ticks.invert(d.evenement.time))
            }).attr("x2", function (d) {
                return x(ticks.invert(d.evenement.time))
            }).attr("y1", 0).attr("y2", affichageSvg.attr("height")).on(
                "mouseover",
                function (d) {
                    divTooltip.transition().duration(200).style("opacity", .9);
                    divTooltip.html(
                        d.evenement.type_display + "<br/>" + d.type_display +
                        "A<br/>" + d.evenement.time).style(
                        "left", (d3.event.pageX) + "px").style("top",
                        (d3.event.pageY - 28) + "px");
                })

        affichageSvg.selectAll(".detail").attr(
            "transform",
            function (d) {
                return "translate(" + x(ticks.invert(d.evenement.time)) +
                    "," + affichageSvg.attr("height") +
                    ") rotate(-90)"
            })
        scriptSvg.selectAll(".etape").attr("transform", function (d) {
            return "translate(" + (x(ticks.invert(d.time)) + 10) + ",0)"
        })
        scriptSvg.selectAll(".ii").attr("width", function (d) {
            return Math.floor((Math.random() * 25) + 1);
        })
    }
}

function brushed() {
    if (d3.event.sourceEvent && d3.event.sourceEvent.type === "zoom")
        return; // ignore brush-by-zoom
    var s = d3.event.selection || x2.range();
    x.domain(s.map(x2.invert, x2));
    //focus.select(".area").attr("d", area);   
    affichageSvg.select(".axis--x").call(xAxis);
    affichageSvg.select(".zoom").call(zoom.transform,
        d3.zoomIdentity.scale(width / (s[1] - s[0])).translate(-s[0], 0));
    updateAffichageActions()
}

function zoomed() {
    if (d3.event.sourceEvent && d3.event.sourceEvent.type === "brush")
        return; // ignore zoom-by-brush
    var t = d3.event.transform;
    x.domain(t.rescaleX(x2).domain());
    //focus.select(".area").attr("d", area);    
    affichageSvg.select(".axis--x").call(xAxis);
    actionSvg.select(".brush").call(brush.move, x.range().map(t.invertX, t));
    updateAffichageActions()
}